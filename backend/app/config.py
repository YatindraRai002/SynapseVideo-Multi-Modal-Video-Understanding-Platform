"""
Configuration settings for ClipCompass backend.
Uses pydantic-settings for environment variable management.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "SynapseVideo"
    debug: bool = False
    api_prefix: str = "/api/v1"
    
    # Database (run backend from project root or backend/ for consistent DB location)
    database_url: str = "sqlite:///./clipcompass.db"
    
    # Qdrant Vector Database
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_transcripts: str = "transcript_embeddings"
    qdrant_collection_frames: str = "frame_embeddings"
    
    # Storage Paths - Use absolute paths
    # Resolve to backend/data regardless of where python is run from
    base_data_dir: Path = Path(__file__).resolve().parent.parent.parent / "data"
    upload_dir: Path = base_data_dir / "videos"
    frames_dir: Path = base_data_dir / "frames"
    audio_dir: Path = base_data_dir / "audio"
    
    # AI Models
    whisper_model: str = "small"  # tiny, base, small, medium, large
    clip_model: str = "ViT-B/32"
    text_embedding_model: str = "all-MiniLM-L6-v2"
    groq_api_key: str | None = None
    
    # Processing Settings
    frame_extraction_fps: float = 1.0  # frames per second
    max_video_duration_minutes: int = 60
    transcript_chunk_size: int = 10  # seconds per chunk
    
    # Optional: YouTube API
    youtube_api_key: str | None = None
    
    # Redis/Celery
    redis_url: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
