"""
Test suite for SynapseVideo API endpoints.
Run with: pytest
"""

import pytest
from httpx import AsyncClient
from app.main import app
from app.core.exceptions import SynapseVideoException


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint returns correct info."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "SynapseVideo"
        assert "status" in data
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_search_endpoint_requires_query():
    """Test search endpoint validates required query parameter."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/search/")
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_search_endpoint_with_query():
    """Test search endpoint accepts valid query."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/search/?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total_results" in data
        assert "latency_ms" in data
        assert data["query"] == "test"


@pytest.mark.asyncio
async def test_search_with_limit():
    """Test search respects limit parameter."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/search/?q=test&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5


@pytest.mark.asyncio
async def test_search_status_endpoint():
    """Test search status diagnostic endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/search/status")
        assert response.status_code == 200
        data = response.json()
        assert "qdrant_connected" in data
        assert "transcript_embeddings" in data
        assert "frame_embeddings" in data
        assert "videos" in data


@pytest.mark.asyncio
async def test_video_list_endpoint():
    """Test video listing endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/videos")
        assert response.status_code == 200
        data = response.json()
        assert "videos" in data
        assert "total" in data
        assert isinstance(data["videos"], list)


@pytest.mark.asyncio
async def test_video_upload_invalid_url():
    """Test video URL upload validation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/videos/url",
            json={"url": ""}  # Empty URL
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_suggestions_endpoint():
    """Test search suggestions endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/search/suggestions?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)


@pytest.mark.asyncio
async def test_clip_generation_invalid_video():
    """Test clip generation with non-existent video."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/clips/generate",
            json={
                "video_id": "nonexistent-id",
                "start_time": 0,
                "end_time": 10
            }
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_clip_generation_invalid_times():
    """Test clip generation with invalid timestamps."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a mock video first (this would fail in real scenario)
        response = await client.post(
            "/api/v1/clips/generate",
            json={
                "video_id": "test-id",
                "start_time": 10,
                "end_time": 5  # End before start
            }
        )
        # Should return 404 (video not found) or 400 (invalid times)
        assert response.status_code in [400, 404]


@pytest.mark.asyncio
async def test_search_types():
    """Test different search types."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        for search_type in ["transcript", "frames", "hybrid"]:
            response = await client.get(
                f"/api/v1/search/?q=test&search_type={search_type}"
            )
            assert response.status_code == 200


# Unit tests for services
def test_timestamp_format():
    """Test timestamp formatting utility."""
    from app.services.video_processor import VideoProcessor
    # Add utility function tests here


# Integration tests
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_search_pipeline():
    """
    Integration test for full search pipeline.
    Requires Qdrant to be running.
    """
    # This test would:
    # 1. Upload a video
    # 2. Wait for processing
    # 3. Perform search
    # 4. Verify results
    pass


# Fixtures
@pytest.fixture
def sample_video_data():
    """Fixture providing sample video data for tests."""
    return {
        "title": "Test Video",
        "duration": 120.0,
        "url": "https://example.com/video.mp4"
    }


@pytest.fixture
def sample_transcript():
    """Fixture providing sample transcript data."""
    return [
        {"text": "Hello world", "start": 0.0, "end": 2.0},
        {"text": "This is a test", "start": 2.0, "end": 5.0}
    ]
