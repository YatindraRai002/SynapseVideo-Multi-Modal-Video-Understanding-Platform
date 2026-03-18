"""
Vector store service using Qdrant.
Handles storage and retrieval of embeddings.
"""

from typing import List, Dict, Any, Optional
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
import numpy as np

from app.config import settings


class VectorStore:
    """Manages vector storage and retrieval with Qdrant."""
    
    def __init__(self):
        self.transcript_collection = settings.qdrant_collection_transcripts
        self.frame_collection = settings.qdrant_collection_frames
        self._client = None
        self._connected = False
    
    @property
    def client(self):
        """Lazy connection to Qdrant with timeout."""
        if self._client is None:
            try:
                self._client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                    timeout=5  # 5 second timeout
                )
                # Test connection
                self._client.get_collections()
                self._connected = True
                print("[+] Connected to Qdrant")
            except Exception as e:
                print(f"[WARN] Qdrant not available: {e}")
                self._connected = False
                self._client = None  # So next request retries connection
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if Qdrant is available."""
        if self._client is None:
            _ = self.client  # Try to connect
        return self._connected
    
    def init_collections(self):
        """Initialize Qdrant collections if they don't exist."""
        if not self.is_connected:
            print("[WARN] Skipping collection init - Qdrant not connected")
            return
            
        # Transcript embeddings (384-dim for all-MiniLM-L6-v2)
        self._create_collection_if_not_exists(
            self.transcript_collection,
            vector_size=384
        )
        
        # Frame embeddings (512-dim for CLIP)
        self._create_collection_if_not_exists(
            self.frame_collection,
            vector_size=512
        )
    
    def get_collection_count(self, collection_name: str) -> int:
        """Return point count for a collection, or 0 if not connected or error."""
        if not self.is_connected or self.client is None:
            return 0
        try:
            info = self.client.get_collection(collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def _create_collection_if_not_exists(self, name: str, vector_size: int):
        """Create a collection if it doesn't exist."""
        if not self.is_connected:
            return
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == name for c in collections):
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"Created collection: {name}")
        except Exception as e:
            print(f"Failed to create collection {name}: {e}")
    
    async def add_transcript_embeddings(
        self,
        video_id: str,
        embeddings: np.ndarray,
        segments: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store transcript segment embeddings.
        
        Args:
            video_id: ID of the source video
            embeddings: numpy array of embeddings
            segments: List of segment metadata dicts
            
        Returns:
            List of generated point IDs
        """
        point_ids = [str(uuid.uuid4()) for _ in segments]

        if not self.is_connected or self.client is None:
            print("[WARN] Qdrant not available - skipping transcript embedding storage")
            return point_ids

        points = []
        for point_id, (embedding, segment) in zip(point_ids, zip(embeddings, segments)):
            points.append(PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    "video_id": video_id,
                    "segment_id": segment.get("id"),
                    "text": segment.get("text"),
                    "start_time": segment.get("start_time"),
                    "end_time": segment.get("end_time"),
                    "speaker": segment.get("speaker")
                }
            ))
        
        try:
            self.client.upsert(
                collection_name=self.transcript_collection,
                points=points
            )
        except Exception as e:
            print(f"[WARN] Failed to upsert transcript embeddings: {e}")
        
        return point_ids
    
    async def add_frame_embeddings(
        self,
        video_id: str,
        embeddings: np.ndarray,
        frames: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store frame embeddings.
        
        Args:
            video_id: ID of the source video
            embeddings: numpy array of CLIP embeddings
            frames: List of frame metadata dicts
            
        Returns:
            List of generated point IDs
        """
        point_ids = [str(uuid.uuid4()) for _ in frames]

        if not self.is_connected or self.client is None:
            print("[WARN] Qdrant not available - skipping frame embedding storage")
            return point_ids

        points = []
        for point_id, (embedding, frame) in zip(point_ids, zip(embeddings, frames)):
            points.append(PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    "video_id": video_id,
                    "frame_id": frame.get("id"),
                    "timestamp": frame.get("timestamp"),
                    "frame_path": frame.get("frame_path"),
                    "caption": frame.get("caption")
                }
            ))
        
        try:
            self.client.upsert(
                collection_name=self.frame_collection,
                points=points
            )
        except Exception as e:
            print(f"[WARN] Failed to upsert frame embeddings: {e}")
        
        return point_ids
    
    async def search_transcripts(
        self,
        query_embedding: np.ndarray,
        video_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search transcript embeddings.
        
        Args:
            query_embedding: Query vector
            video_id: Optional filter by video
            limit: Max results
            
        Returns:
            List of matching segments with scores
        """
        if not self.is_connected or self.client is None:
            return []
        filter_condition = None
        if video_id:
            filter_condition = Filter(
                must=[FieldCondition(
                    key="video_id",
                    match=MatchValue(value=video_id)
                )]
            )
        try:
            print(f"[DEBUG] Searching transcripts for query (embedding shape: {len(query_embedding.tolist())})")
            response = self.client.query_points(
                collection_name=self.transcript_collection,
                query=query_embedding.tolist(),
                query_filter=filter_condition,
                limit=limit
            )
            results = response.points
            print(f"[DEBUG] Found {len(results)} transcript results")
            if results:
                print(f"[DEBUG] First result score: {results[0].score}, text: {results[0].payload.get('text', 'N/A')[:50]}")
            return [
                {"id": r.id, "score": r.score, **r.payload}
                for r in results
            ]
        except Exception as e:
            print(f"[WARN] transcript search failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def search_frames(
        self,
        query_embedding: np.ndarray,
        video_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search frame embeddings using CLIP text embedding.
        
        Args:
            query_embedding: CLIP text embedding
            video_id: Optional filter by video
            limit: Max results
            
        Returns:
            List of matching frames with scores
        """
        if not self.is_connected or self.client is None:
            return []
        filter_condition = None
        if video_id:
            filter_condition = Filter(
                must=[FieldCondition(
                    key="video_id",
                    match=MatchValue(value=video_id)
                )]
            )
        try:
            response = self.client.query_points(
                collection_name=self.frame_collection,
                query=query_embedding.tolist(),
                query_filter=filter_condition,
                limit=limit
            )
            results = response.points
            return [
                {"id": r.id, "score": r.score, **r.payload}
                for r in results
            ]
        except Exception as e:
            print(f"[WARN] frame search failed: {e}")
            return []

    async def delete_video_embeddings(self, video_id: str):
        """Delete all embeddings for a video."""
        if not self.is_connected or self.client is None:
            print("[WARN] Qdrant not available - skipping embedding deletion")
            return

        filter_condition = Filter(
            must=[FieldCondition(
                key="video_id",
                match=MatchValue(value=video_id)
            )]
        )
        
        try:
            self.client.delete(
                collection_name=self.transcript_collection,
                points_selector=filter_condition
            )
            self.client.delete(
                collection_name=self.frame_collection,
                points_selector=filter_condition
            )
        except Exception as e:
            print(f"[WARN] Failed to delete embeddings: {e}")
