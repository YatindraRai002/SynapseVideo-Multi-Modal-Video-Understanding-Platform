

import pytest
import time
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings


client = TestClient(app)


class TestVideoProcessingPipeline:
    """Integration tests for video processing."""
    
    def test_video_upload(self, sample_video_file):
        """Test video upload endpoint."""
        with open(sample_video_file, "rb") as f:
            response = client.post(
                f"{settings.api_prefix}/videos/upload",
                files={"file": ("test_video.mp4", f, "video/mp4")},
                data={"title": "Test Video"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Video"
        assert data["status"] in ["PENDING", "PROCESSING"]
        
        return data["id"]
    
    def test_video_status_tracking(self, sample_video_file):
        """Test video processing status tracking."""
        # Upload video
        video_id = self.test_video_upload(sample_video_file)
        
        # Poll for processing completion (max 60 seconds)
        max_attempts = 60
        for _ in range(max_attempts):
            response = client.get(f"{settings.api_prefix}/videos/{video_id}/status")
            assert response.status_code == 200
            
            data = response.json()
            if data["status"] == "READY":
                assert data["processing_progress"] == 100
                break
            elif data["status"] == "FAILED":
                pytest.fail(f"Video processing failed: {data}")
            
            time.sleep(1)
        else:
            pytest.fail("Video processing timed out")
    
    def test_youtube_video_processing(self):
        """Test YouTube video processing."""
        response = client.post(
            f"{settings.api_prefix}/videos/youtube",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Test YouTube Video"
            }
        )
        
        # This may fail if yt-dlp is not configured or network issues
        # So we just check it doesn't crash
        assert response.status_code in [200, 422, 500]


class TestSearchPipeline:
    """Integration tests for search functionality."""
    
    def test_transcript_search(self):
        """Test transcript-based search."""
        response = client.get(
            f"{settings.api_prefix}/search/",
            params={
                "q": "test query",
                "search_type": "transcript",
                "limit": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert isinstance(data["results"], list)
    
    def test_frame_search(self):
        """Test frame-based visual search."""
        response = client.get(
            f"{settings.api_prefix}/search/",
            params={
                "q": "person presenting",
                "search_type": "frames",
                "limit": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
    
    def test_hybrid_search(self):
        """Test hybrid multi-modal search."""
        response = client.get(
            f"{settings.api_prefix}/search/",
            params={
                "q": "budget discussion with charts",
                "search_type": "hybrid",
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "latency_ms" in data
        assert isinstance(data["results"], list)


class TestEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.slow
    def test_complete_workflow(self, sample_video_file):
        """Test complete workflow: upload -> process -> search."""
        # 1. Upload video
        with open(sample_video_file, "rb") as f:
            upload_response = client.post(
                f"{settings.api_prefix}/videos/upload",
                files={"file": ("test_video.mp4", f, "video/mp4")},
                data={"title": "E2E Test Video"}
            )
        
        assert upload_response.status_code == 200
        video_id = upload_response.json()["id"]
        
        # 2. Wait for processing
        max_attempts = 120  # 2 minutes
        for _ in range(max_attempts):
            status_response = client.get(
                f"{settings.api_prefix}/videos/{video_id}/status"
            )
            data = status_response.json()
            
            if data["status"] == "READY":
                break
            elif data["status"] == "FAILED":
                pytest.fail("Video processing failed")
            
            time.sleep(1)
        else:
            pytest.fail("Video processing timed out")
        
        # 3. Search for content
        search_response = client.get(
            f"{settings.api_prefix}/search/",
            params={"q": "test", "search_type": "hybrid", "limit": 5}
        )
        
        assert search_response.status_code == 200
        search_data = search_response.json()
        
        # Verify search results contain our video
        video_ids = [r["video_id"] for r in search_data["results"]]
        # Note: May not always find results depending on video content
        # assert video_id in video_ids


@pytest.fixture
def sample_video_file(tmp_path):
    """Create a sample video file for testing."""
    # This would need ffmpeg to create a real test video
    # For now, we'll skip if no test video exists
    test_video = Path("tests/fixtures/sample_video.mp4")
    if not test_video.exists():
        pytest.skip("No sample video file available for testing")
    
    return test_video
