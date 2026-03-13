"""
SynapseVideo - Multi-Modal Video Understanding Platform
FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pathlib import Path
import time
from collections import defaultdict

from app.config import settings
from app.core.database import init_db
from app.core.logger import get_logger
from app.core.exceptions import GroqSightException
from app.api.routes import videos, search, clips, asr

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    logger.info("Starting SynapseVideo...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Create data directories
    for directory in [settings.upload_dir, settings.frames_dir, settings.audio_dir]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    logger.info("Data directories ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SynapseVideo...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Multi-modal video search engine with AI-powered transcript and frame analysis.",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 100  # Number of requests
RATE_LIMIT_WINDOW = 60      # Window in seconds
client_requests = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple in-memory rate limiting middleware."""
    client_ip = request.client.host
    current_time = time.time()
    
    # Filter out old requests
    client_requests[client_ip] = [t for t in client_requests[client_ip] if current_time - t < RATE_LIMIT_WINDOW]
    
    if len(client_requests[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "RateLimitExceeded", "message": "Too many requests. Please try again later."}
        )
    
    client_requests[client_ip].append(current_time)
    response = await call_next(request)
    return response

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


# Exception handlers
@app.exception_handler(SynapseVideoException)
async def synapsevideo_exception_handler(request: Request, exc: SynapseVideoException):
    """Handle custom application exceptions."""
    logger.error(f"Application error: {exc.message}", extra={"details": exc.details})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.debug else "Contact support for assistance"
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    logger.debug("Root endpoint accessed")
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check endpoint accessed")
    return {"status": "healthy"}
