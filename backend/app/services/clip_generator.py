
import subprocess
import sys
from pathlib import Path
import uuid
from static_ffmpeg import run

from app.config import settings


class ClipGenerator:
    
    def __init__(self):
        self.clips_dir = Path(settings.base_data_dir) / "clips"
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path, _ = run.get_or_fetch_platform_executables_else_raise()
    
    async def generate_clip(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        output_name: str = None,
        include_captions: bool = False
    ) -> Path:
       
        clip_id = output_name or str(uuid.uuid4())
        output_path = self.clips_dir / f"{clip_id}.mp4"
        
        duration = end_time - start_time
        
        # FFmpeg command for clip extraction
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path),
            "-ss", str(start_time),
            "-t", str(duration),
            "-c", "copy",  # Copy streams without re-encoding (fast)
            "-avoid_negative_ts", "1",
            str(output_path),
            "-y"  # Overwrite if exists
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            # If copy fails, try re-encoding
            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-ss", str(start_time),
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "aac",
                str(output_path),
                "-y"
            ]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0:
                raise Exception(f"Clip generation failed: {process.stderr}")
        
        return output_path
    
    async def generate_clip_with_captions(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        captions: list,
        output_name: str = None
    ) -> Path:
        """
        Generate a clip with burned-in captions.
        
        Args:
            video_path: Path to source video
            start_time: Start timestamp in seconds
            end_time: End timestamp in seconds
            captions: List of caption dicts with text, start, end
            output_name: Optional output filename
            
        Returns:
            Path to generated clip with captions
        """
        clip_id = output_name or str(uuid.uuid4())
        output_path = self.clips_dir / f"{clip_id}.mp4"
        srt_path = self.clips_dir / f"{clip_id}.srt"
        
        # Generate SRT file
        srt_content = self._generate_srt(captions, start_time)
        srt_path.write_text(srt_content)
        
        duration = end_time - start_time
        
        # FFmpeg with subtitle filter
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path),
            "-ss", str(start_time),
            "-t", str(duration),
            "-vf", f"subtitles='{str(srt_path)}'",
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            str(output_path),
            "-y"
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up SRT file
        srt_path.unlink(missing_ok=True)
        
        if process.returncode != 0:
            raise Exception(f"Clip generation with captions failed: {process.stderr}")
        
        return output_path
    
    def _generate_srt(self, captions: list, offset: float) -> str:
        """Generate SRT subtitle file content."""
        srt_lines = []
        
        for i, cap in enumerate(captions, 1):
            start = cap.get("start", 0) - offset
            end = cap.get("end", start + 1) - offset
            text = cap.get("text", "")
            
            if start < 0:
                continue
            
            start_str = self._seconds_to_srt_time(start)
            end_str = self._seconds_to_srt_time(end)
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(text)
            srt_lines.append("")
        
        return "\n".join(srt_lines)
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def get_clip_path(self, clip_id: str) -> Path:
        """Get the path to a generated clip."""
        return self.clips_dir / f"{clip_id}.mp4"
    
    def clip_exists(self, clip_id: str) -> bool:
        """Check if a clip exists."""
        return self.get_clip_path(clip_id).exists()


# Global clip generator instance
clip_generator = ClipGenerator()
