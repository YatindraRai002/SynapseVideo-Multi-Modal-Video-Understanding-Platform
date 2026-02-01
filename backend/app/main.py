"""
ClipCompass - Video-Context Search Engine
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.core.database import init_db
from app.api.routes import videos, search, clips, asr


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    print("[*] Starting ClipCompass...")
    
    # Initialize database
    init_db()
    print("[+] Database initialized")
    
    # Create data directories
    for directory in [settings.upload_dir, settings.frames_dir, settings.audio_dir]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    print("[+] Data directories ready")
    
    yield
    
    # Shutdown
    print("[*] Shutting down ClipCompass...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Multi-modal video search engine with AI-powered transcript and frame analysis.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving frames
app.mount("/static/frames", StaticFiles(directory=str(settings.frames_dir)), name="frames")
app.mount("/static/videos", StaticFiles(directory=str(settings.upload_dir)), name="videos")

# Include API routes
app.include_router(videos.router, prefix=f"{settings.api_prefix}/videos", tags=["Videos"])
app.include_router(search.router, prefix=f"{settings.api_prefix}/search", tags=["Search"])
app.include_router(clips.router, prefix=f"{settings.api_prefix}/clips", tags=["Clips"])
app.include_router(asr.router, prefix=f"{settings.api_prefix}/asr", tags=["ASR (Speech-to-Text)"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
