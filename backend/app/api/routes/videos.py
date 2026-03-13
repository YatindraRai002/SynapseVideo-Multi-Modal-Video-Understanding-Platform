"""
Video management API routes.
Handles video upload, processing status, and metadata.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import shutil
from pathlib import Path
import asyncio

from app.core.database import get_db
from app.config import settings
from app.models.video import Video, VideoStatus
from app.models.schemas import (
    VideoUploadRequest,
    VideoResponse,
    VideoStatusResponse,
    VideoListResponse,
    TranscriptResponse,
    TranscriptSegmentResponse,
)
from app.workers.pipeline import process_video_task

router = APIRouter()


# Removed run_async_task helper - utilizing native BackgroundTasks


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Upload a video file for processing.
    The video will be processed in the background.
    """
    # Validate file type
    allowed_types = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Validate file size (e.g., 500MB limit)
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    # We check the size by seeking to the end or using the file descriptor if available
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is 500MB."
        )
    
    # Generate unique ID and file path
    video_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    file_path = settings.upload_dir / f"{video_id}{file_extension}"
    
    # Save uploaded file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create database record
    video = Video(
        id=video_id,
        title=title or file.filename,
        file_path=str(file_path),
        status=VideoStatus.PENDING.value
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    background_tasks.add_task(process_video_task, video_id)
    
    return video


@router.post("/url", response_model=VideoResponse)
async def upload_video_url(
    request: VideoUploadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Download and process a video from URL (YouTube, Vimeo, etc.).
    
    Supported platforms: YouTube, Vimeo, Dailymotion, Twitch, Facebook, 
    Twitter/X, Instagram, TikTok, and many more.
    """
    from app.services.video_downloader import video_downloader
    
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    video_id = str(uuid.uuid4())
    
    # Create database record with pending status
    video = Video(
        id=video_id,
        title=request.title or "Downloading...",
        source_url=request.url,
        file_path="",
        status=VideoStatus.PENDING.value
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    # Queue background download and processing
    async def download_and_process():
        from app.core.database import SessionLocal
        db_session = SessionLocal()
        try:
            # Update status to downloading
            v = db_session.query(Video).filter(Video.id == video_id).first()
            v.status = "downloading"
            db_session.commit()
            
            # Download video
            info = await video_downloader.download(request.url, video_id)
            
            # Update video record with downloaded info
            v.file_path = info["file_path"]
            v.title = request.title or info.get("title", "Downloaded Video")
            v.duration_seconds = info.get("duration")
            v.status = VideoStatus.PENDING.value
            db_session.commit()
            
            # Start processing pipeline
            await process_video_task(video_id)
            
        except Exception as e:
            v = db_session.query(Video).filter(Video.id == video_id).first()
            v.status = VideoStatus.FAILED.value
            v.error_message = str(e)
            db_session.commit()
        finally:
            db_session.close()
    
    background_tasks.add_task(download_and_process)
    
    return video


@router.get("/", response_model=VideoListResponse)
async def list_videos(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List all uploaded videos."""
    videos = db.query(Video).offset(skip).limit(limit).all()
    total = db.query(Video).count()
    
    return VideoListResponse(videos=videos, total=total)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str, db: Session = Depends(get_db)):
    """Get video by ID."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(video_id: str, db: Session = Depends(get_db)):
    """Get video processing status."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return VideoStatusResponse(
        id=video.id,
        status=video.status,
        progress=video.processing_progress,
        error_message=video.error_message
    )


@router.get("/{video_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(video_id: str, db: Session = Depends(get_db)):
    """Get full transcript for a video."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.status != VideoStatus.READY.value:
        raise HTTPException(status_code=400, detail="Video is not fully processed")
    
    segments = [
        TranscriptSegmentResponse.model_validate(seg)
        for seg in video.transcript_segments
    ]
    
    return TranscriptResponse(
        video_id=video_id,
        segments=segments,
        total_duration=video.duration_seconds or 0
    )


@router.delete("/{video_id}")
async def delete_video(video_id: str, db: Session = Depends(get_db)):
    """Delete a video and all associated data."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete files
    if video.file_path:
        Path(video.file_path).unlink(missing_ok=True)
    
    # Delete from database (cascades to segments and frames)
    db.delete(video)
    db.commit()
    
    return {"message": "Video deleted successfully"}


@router.get("/{video_id}/frames")
async def get_frames(video_id: str, db: Session = Depends(get_db)):
    """Get extracted frames for a video."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.status != VideoStatus.READY.value:
        raise HTTPException(status_code=400, detail="Video is not fully processed")
    
    frames = [
        {
            "timestamp": frame.timestamp,
            "file_path": frame.file_path,
            "caption": frame.caption,
            "tags": frame.tags
        }
        for frame in video.frames
    ]
    
    return {"video_id": video_id, "frames": frames}


@router.post("/{video_id}/retry", response_model=VideoResponse)
async def retry_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Retry processing for a failed video."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Reset status
    video.status = VideoStatus.PENDING.value
    video.processing_progress = 0
    video.error_message = None
    db.commit()
    db.refresh(video)
    
    # Trigger processing
    background_tasks.add_task(process_video_task, video_id)
    
    return video
