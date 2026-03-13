"""
Frame extraction service.
Extracts frames from videos using FFmpeg with scene detection.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np
from static_ffmpeg import run

from app.config import settings


class ExtractedFrame:
    """Represents an extracted video frame."""
    
    def __init__(self, path: Path, timestamp: float, index: int):
        self.path = path
        self.timestamp = timestamp
        self.index = index


class FrameExtractor:
    """Handles frame extraction from videos."""
    
    def __init__(self):
        self.frames_dir = Path(settings.frames_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.fps = settings.frame_extraction_fps
        self.ffmpeg_path, _ = run.get_or_fetch_platform_executables_else_raise()
    
    async def extract_frames_fixed_interval(
        self,
        video_path: Path,
        video_id: str,
        fps: float = None
    ) -> List[ExtractedFrame]:
        """
        Extract frames at fixed intervals using FFmpeg.
        
        Args:
            video_path: Path to video file
            video_id: UUID for organizing output
            fps: Frames per second to extract (default from settings)
            
        Returns:
            List of ExtractedFrame objects
        """
        fps = fps or self.fps
        output_dir = self.frames_dir / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # FFmpeg command for frame extraction
        output_pattern = str(output_dir / "frame_%05d.jpg")
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path),
            "-vf", f"fps={fps}",
            "-q:v", "2",  # High quality JPEG
            output_pattern,
            "-y"  # Overwrite
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            raise Exception(f"Frame extraction failed: {process.stderr}")
        
        # Collect extracted frames
        frames = []
        for i, frame_path in enumerate(sorted(output_dir.glob("frame_*.jpg"))):
            timestamp = i / fps
            frames.append(ExtractedFrame(
                path=frame_path,
                timestamp=timestamp,
                index=i
            ))
        
        return frames
    
    async def extract_frames_scene_detection(
        self,
        video_path: Path,
        video_id: str,
        threshold: float = 30.0
    ) -> List[ExtractedFrame]:
        """
        Extract frames at scene changes using OpenCV.
        
        Args:
            video_path: Path to video file
            video_id: UUID for organizing output
            threshold: Scene change threshold (higher = fewer frames)
            
        Returns:
            List of ExtractedFrame objects
        """
        output_dir = self.frames_dir / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        frames = []
        prev_frame = None
        frame_idx = 0
        extracted_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to grayscale for comparison
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect scene change
            is_scene_change = False
            if prev_frame is None:
                is_scene_change = True  # First frame
            else:
                diff = cv2.absdiff(prev_frame, gray)
                mean_diff = np.mean(diff)
                if mean_diff > threshold:
                    is_scene_change = True
            
            if is_scene_change:
                timestamp = frame_idx / fps
                frame_path = output_dir / f"frame_{extracted_idx:05d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                
                frames.append(ExtractedFrame(
                    path=frame_path,
                    timestamp=timestamp,
                    index=extracted_idx
                ))
                extracted_idx += 1
            
            prev_frame = gray
            frame_idx += 1
        
        cap.release()
        return frames
    
    async def extract_keyframes(
        self,
        video_path: Path,
        video_id: str
    ) -> List[ExtractedFrame]:
        """
        Extract only I-frames (keyframes) from video.
        Most efficient but may miss important moments.
        """
        output_dir = self.frames_dir / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_pattern = str(output_dir / "frame_%05d.jpg")
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path),
            "-vf", "select='eq(pict_type,I)'",
            "-vsync", "vfr",
            "-q:v", "2",
            output_pattern,
            "-y"
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            raise Exception(f"Keyframe extraction failed: {process.stderr}")
        
        # Need to get actual timestamps for keyframes
        # This is more complex - simplified version
        frames = []
        for i, frame_path in enumerate(sorted(output_dir.glob("frame_*.jpg"))):
            frames.append(ExtractedFrame(
                path=frame_path,
                timestamp=0,  # Would need to extract from video
                index=i
            ))
        
        return frames
