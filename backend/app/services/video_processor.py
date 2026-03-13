"""
Video processing service.
Handles video download, metadata extraction, and orchestrates the processing pipeline.
"""

import subprocess
import json
from pathlib import Path
from typing import Optional
import uuid
import sys
from static_ffmpeg import run

from app.config import settings


import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
import json

from app.models.video import Video, VideoStatus, TranscriptSegment, Frame
from app.services.audio_extractor import AudioExtractor
from app.services.transcriber import Transcriber
from app.services.frame_extractor import FrameExtractor
from app.services.embedder import Embedder
from app.services.vector_store import VectorStore
from app.services.tagger import visual_tagger


class VideoProcessor:
    """Handles video ingestion, processing, and metadata extraction."""
    
    def __init__(self):
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize sub-services
        self.audio_extractor = AudioExtractor()
        self.transcriber = Transcriber()
        self.frame_extractor = FrameExtractor()
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        
        # Initialize binaries
        self.ffmpeg_path, self.ffprobe_path = run.get_or_fetch_platform_executables_else_raise()
    
    async def download_youtube(self, url: str, video_id: str) -> Path:
        """
        Download video from YouTube using yt-dlp.
        
        Args:
            url: YouTube video URL
            video_id: UUID for the video
            
        Returns:
            Path to downloaded video file
        """
        output_path = self.upload_dir / f"{video_id}.mp4"
        
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "--merge-output-format", "mp4",
            "-o", str(output_path),
            "--ffmpeg-location", self.ffmpeg_path,
            url
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            raise Exception(f"Failed to download video: {process.stderr}")
        
        return output_path
    
    def get_video_metadata(self, video_path: Path) -> dict:
        """
        Extract video metadata using FFprobe.
        
        Returns:
            dict with duration, width, height, fps, etc.
        """
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to get video metadata: {result.stderr}")
        
        data = json.loads(result.stdout)
        
        # Extract video stream info
        video_stream = next(
            (s for s in data.get("streams", []) if s["codec_type"] == "video"),
            {}
        )
        
        # Parse FPS (e.g., "30/1" -> 30.0)
        fps_str = video_stream.get("avg_frame_rate", "0/1")
        try:
            num, den = map(int, fps_str.split("/"))
            fps = num / den if den > 0 else 0
        except:
            fps = 0
        
        return {
            "duration_seconds": float(data.get("format", {}).get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": fps,
            "file_size_bytes": int(data.get("format", {}).get("size", 0)),
            "codec": video_stream.get("codec_name", "unknown")
        }
    
    async def process_video(self, db: Session, video: Video):
        """
        Main processing pipeline orchestrator.
        
        1. Extract audio
        2. Transcribe with Whisper
        3. Extract frames & Tag
        4. Generate embeddings
        5. Store in vector database
        """
        video_id = video.id
        
        # Robust path resolution
        if not video.file_path:
             raise Exception(f"Video file path is empty in database for video: {video.title}")
             
        video_path = Path(video.file_path)
        
        if not video_path.exists() or video_path.is_dir():
            raise Exception(f"Video file not found or is a directory: {video_path}")
        
        print(f"[*] Starting processing for: {video.title}")
        
        try:
            # Step 1: Extract audio
            await self._update_status(db, video, VideoStatus.EXTRACTING_AUDIO, 10)
            audio_path = await self.audio_extractor.extract_audio(video_path, video_id)
            print(f"[+] Audio extracted: {audio_path}")
            
            # Step 2: Transcribe
            await self._update_status(db, video, VideoStatus.TRANSCRIBING, 30)
            segments = await self.transcriber.transcribe(audio_path)
            chunked_segments = self.transcriber.chunk_segments(segments)
            await self._save_transcript_segments(db, video, chunked_segments)
            print(f"[+] Transcribed: {len(chunked_segments)} segments")
            
            # Step 3: Extract frames
            await self._update_status(db, video, VideoStatus.EXTRACTING_FRAMES, 50)
            frames = await self.frame_extractor.extract_frames_fixed_interval(
                video_path, video_id
            )
            
            # Step 3.5: Visual tagging (Transfer Learning)
            print(f"[*] Auto-tagging {len(frames)} frames with ResNet50...")
            for frame in frames:
                tags = await visual_tagger.tag_frame(frame.path)
                frame.tags = json.dumps(tags)  # Store as JSON string
                
            await self._save_frames(db, video, frames)
            print(f"[+] Extracted & Tagged: {len(frames)} frames")
            
            # Step 4: Generate embeddings
            await self._update_status(db, video, VideoStatus.EMBEDDING, 70)
            await self._generate_and_store_embeddings(db, video)
            print(f"[+] Embeddings generated and indexed")
            
            # Step 5: Complete
            video.status = VideoStatus.READY.value
            video.processing_progress = 100
            video.processed_at = datetime.utcnow()
            db.commit()
            
            print(f"[+] Processing complete for: {video.title}")
            
        except Exception as e:
            # Note: caller should handle exception logging/db update if needed, 
            # but we can do a partial update here if we want to be safe,
            # or rely on the caller (pipeline task wrapper) to catch and mark failed.
            # Here we just re-raise to let the wrapper handle the failure state.
            raise e

    async def _update_status(
        self,
        db: Session,
        video: Video,
        status: VideoStatus,
        progress: float
    ):
        """Update video processing status."""
        video.status = status.value
        video.processing_progress = progress
        db.commit()
    
    async def _save_transcript_segments(
        self,
        db: Session,
        video: Video,
        segments
    ):
        """Save transcript segments to database."""
        for i, seg in enumerate(segments):
            segment = TranscriptSegment(
                video_id=video.id,
                segment_index=i,
                start_time=seg.start,
                end_time=seg.end,
                text=seg.text
            )
            db.add(segment)
        db.commit()
    
    async def _save_frames(
        self,
        db: Session,
        video: Video,
        frames
    ):
        """Save extracted frames to database."""
        for frame in frames:
            frame_record = Frame(
                video_id=video.id,
                frame_index=frame.index,
                timestamp=frame.timestamp,
                file_path=str(frame.path),
                tags=getattr(frame, "tags", None)  # Save tags if present
            )
            db.add(frame_record)
        db.commit()
    
    async def _generate_and_store_embeddings(
        self,
        db: Session,
        video: Video
    ):
        """Generate embeddings and store in vector database."""
        # Initialize vector store collections
        self.vector_store.init_collections()
        
        # Get transcript segments
        segments = db.query(TranscriptSegment).filter(
            TranscriptSegment.video_id == video.id
        ).all()
        
        if segments:
            # Generate text embeddings
            texts = [seg.text for seg in segments]
            embeddings = await self.embedder.embed_text(texts)
            
            # Store in vector DB
            segment_data = [
                {
                    "id": seg.id,
                    "text": seg.text,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "speaker": seg.speaker
                }
                for seg in segments
            ]
            
            point_ids = await self.vector_store.add_transcript_embeddings(
                video.id, embeddings, segment_data
            )
            
            # Update segments with embedding IDs
            for seg, point_id in zip(segments, point_ids):
                seg.embedding_id = point_id
            db.commit()
        
        # Get frames
        frames = db.query(Frame).filter(Frame.video_id == video.id).all()
        
        if frames:
            # Generate image embeddings (in batches)
            batch_size = 32
            all_point_ids = []
            
            for i in range(0, len(frames), batch_size):
                batch_frames = frames[i:i + batch_size]
                image_paths = [Path(f.file_path) for f in batch_frames]
                embeddings = await self.embedder.embed_images(image_paths)
                
                frame_data = [
                    {
                        "id": f.id,
                        "timestamp": f.timestamp,
                        "frame_path": f.file_path,
                        "caption": f.caption
                    }
                    for f in batch_frames
                ]
                
                point_ids = await self.vector_store.add_frame_embeddings(
                    video.id, embeddings, frame_data
                )
                all_point_ids.extend(point_ids)
            
            # Update frames with embedding IDs
            for frame, point_id in zip(frames, all_point_ids):
                frame.embedding_id = point_id
            db.commit()


# Global instance
video_processor = VideoProcessor()
