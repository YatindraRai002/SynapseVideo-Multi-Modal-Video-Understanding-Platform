

import subprocess
import sys
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import json
from static_ffmpeg import run

from app.config import settings


class VideoDownloader:
   
    
    def __init__(self):
        self.download_dir = settings.upload_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path, _ = run.get_or_fetch_platform_executables_else_raise()
    
    async def download(
        self,
        url: str,
        video_id: str = None,
        format: str = "mp4"
    ) -> Dict[str, Any]:
        """
        Download video from URL.
        
        Args:
            url: Video URL (YouTube, Vimeo, etc.)
            video_id: Optional ID for the output file
            format: Output format (mp4, webm)
            
        Returns:
            Dict with video info including file_path, title, duration
        """
        video_id = video_id or str(uuid.uuid4())
        output_path = self.download_dir / f"{video_id}.{format}"
        
        # yt-dlp command
        cmd = [
            sys.executable, "-m", "yt_dlp",
            url,
            "-o", str(output_path),
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", format,
            "--no-playlist",  # Don't download playlists
            "--print-json",   # Output video info as JSON
            "--no-simulate",  # Actually download
            "--ffmpeg-location", self.ffmpeg_path
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            raise Exception(f"Download failed: {process.stderr}")
        
        # Parse video info from yt-dlp output
        try:
            # yt-dlp outputs JSON on the last line
            json_lines = [l for l in process.stdout.strip().split('\n') if l.startswith('{')]
            if json_lines:
                info = json.loads(json_lines[-1])
            else:
                info = {}
        except json.JSONDecodeError:
            info = {}
        
        # Find the actual downloaded file (might have different extension)
        actual_file = None
        for ext in [format, 'mp4', 'webm', 'mkv']:
            potential_file = self.download_dir / f"{video_id}.{ext}"
            if potential_file.exists():
                actual_file = potential_file
                break
        
        if not actual_file:
            # Check for any file starting with video_id
            for f in self.download_dir.glob(f"{video_id}*"):
                if f.is_file():
                    actual_file = f
                    break
        
        if not actual_file or not actual_file.exists():
            raise Exception("Download completed but file not found")
        
        return {
            "file_path": str(actual_file),
            "title": info.get("title", "Downloaded Video"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "description": info.get("description"),
            "uploader": info.get("uploader"),
            "width": info.get("width"),
            "height": info.get("height"),
        }
    
    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video info without downloading.
        
        Args:
            url: Video URL
            
        Returns:
            Dict with video metadata
        """
        cmd = [
            sys.executable, "-m", "yt_dlp",
            url,
            "--dump-json",
            "--no-download",
            "--no-playlist",
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            raise Exception(f"Failed to get video info: {process.stderr}")
        
        try:
            info = json.loads(process.stdout)
            return {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
                "description": info.get("description"),
                "uploader": info.get("uploader"),
                "url": url,
            }
        except json.JSONDecodeError:
            raise Exception("Failed to parse video info")
    
    def is_supported_url(self, url: str) -> bool:
        """Check if URL is supported by yt-dlp."""
        supported_domains = [
            "youtube.com", "youtu.be",
            "vimeo.com",
            "dailymotion.com",
            "twitch.tv",
            "facebook.com",
            "twitter.com", "x.com",
            "instagram.com",
            "tiktok.com",
        ]
        return any(domain in url.lower() for domain in supported_domains)


# Global downloader instance
video_downloader = VideoDownloader()
