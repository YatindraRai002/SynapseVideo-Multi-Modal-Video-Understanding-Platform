"""
Custom exception classes for SynapseVideo application.
"""


class SynapseVideoException(Exception):
    """Base exception class for SynapseVideo."""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class VideoProcessingError(SynapseVideoException):
    """Raised when video processing fails."""
    pass


class AudioExtractionError(SynapseVideoException):
    """Raised when audio extraction fails."""
    pass


class TranscriptionError(SynapseVideoException):
    """Raised when transcription fails."""
    pass


class FrameExtractionError(SynapseVideoException):
    """Raised when frame extraction fails."""
    pass


class EmbeddingError(SynapseVideoException):
    """Raised when embedding generation fails."""
    pass


class VectorStoreError(SynapseVideoException):
    """Raised when vector database operations fail."""
    pass


class VideoNotFoundError(SynapseVideoException):
    """Raised when a requested video doesn't exist."""
    pass


class InvalidVideoFormatError(SynapseVideoException):
    """Raised when video format is not supported."""
    pass


class VideoDownloadError(SynapseVideoException):
    """Raised when YouTube/URL video download fails."""
    pass


class SearchError(SynapseVideoException):
    """Raised when search operation fails."""
    pass


class DatabaseError(SynapseVideoException):
    """Raised when database operation fails."""
    pass
