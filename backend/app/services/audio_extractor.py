

import subprocess
import sys
from pathlib import Path
import uuid
from static_ffmpeg import run

from app.config import settings


class AudioExtractor:
    def __init__(self):
        self.audio_dir = Path(settings.audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path, self.ffprobe_path = run.get_or_fetch_platform_executables_else_raise()
    
    async def extract_audio(
        self,
        video_path: Path,
        video_id: str,
        format: str = "wav"
    ) -> Path:
       
        output_path = self.audio_dir / f"{video_id}.{format}"
        
        
        if format == "wav":
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                str(output_path),
                "-y"  # Overwrite if exists
            ]
        else:
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-vn",
                "-q:a", "0",  # Best quality
                str(output_path),
                "-y"
            ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            raise Exception(f"Audio extraction failed: {process.stderr}")
        
        return output_path
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(audio_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return 0.0
        
        try:
            return float(result.stdout.strip())
        except:
            return 0.0
