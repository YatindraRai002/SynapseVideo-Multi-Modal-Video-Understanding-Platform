"""
Transcription service using OpenAI Whisper.
Provides timestamped speech-to-text conversion.
"""

from pathlib import Path
from typing import List
import whisper
import torch

from app.config import settings


class TranscriptionSegment:
    """Represents a segment of transcribed text with timestamps."""
    
    def __init__(self, text: str, start: float, end: float, words: List[dict] = None):
        self.text = text
        self.start = start
        self.end = end
        self.words = words or []


class Transcriber:
    """Handles audio transcription using Whisper."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize Whisper model.
        
        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
        """
        self.model_name = model_name or settings.whisper_model
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def _load_model(self):
        """Lazy load the Whisper model."""
        if self.model is None:
            import os
            from static_ffmpeg import run
            ffmpeg_path, _ = run.get_or_fetch_platform_executables_else_raise()
            ffmpeg_dir = str(Path(ffmpeg_path).parent)
            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
                
            print(f"Loading Whisper model '{self.model_name}' on {self.device}...")
            self.model = whisper.load_model(self.model_name, device=self.device)
            print("Whisper model loaded!")
    
    async def transcribe(self, audio_path: Path, language: str = None) -> List[TranscriptionSegment]:
        """
        Transcribe audio file with timestamps.
        Try Groq API first for speed, fallback to local Whisper.
        """
        # Try Groq first if API key is available
        if settings.groq_api_key:
            try:
                from groq import Groq
                print(f"[*] Using Groq API for transcription: {audio_path.name}")
                client = Groq(api_key=settings.groq_api_key)
                
                with open(audio_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(audio_path.name, file.read()),
                        model="whisper-large-v3",
                        response_format="verbose_json",
                        language=language
                    )
                
                segments = []
                # Handle both dict and object responses from groq client
                segments_data = getattr(transcription, 'segments', [])
                if not segments_data and isinstance(transcription, dict):
                    segments_data = transcription.get('segments', [])
                
                for seg in segments_data:
                    # Handle if seg is a dict or object
                    if isinstance(seg, dict):
                        segment = TranscriptionSegment(
                            text=seg.get("text", "").strip(),
                            start=seg.get("start", 0.0),
                            end=seg.get("end", 0.0)
                        )
                    else:
                        segment = TranscriptionSegment(
                            text=getattr(seg, "text", "").strip(),
                            start=getattr(seg, "start", 0.0),
                            end=getattr(seg, "end", 0.0)
                        )
                    segments.append(segment)
                
                print(f"[+] Groq transcription complete: {len(segments)} segments")
                return segments
                
            except Exception as e:
                print(f"[!] Groq transcription failed: {e}. Falling back to local Whisper...")

        # Local Fallback
        self._load_model()
        
        print(f"[*] Using local Whisper for transcription: {audio_path.name}")
        # Transcribe with word-level timestamps
        result = self.model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
            verbose=False
        )
        
        segments = []
        for seg in result.get("segments", []):
            segment = TranscriptionSegment(
                text=seg["text"].strip(),
                start=seg["start"],
                end=seg["end"],
                words=seg.get("words", [])
            )
            segments.append(segment)
        
        return segments
    
    def chunk_segments(
        self,
        segments: List[TranscriptionSegment],
        chunk_duration: float = None
    ) -> List[TranscriptionSegment]:
        """
        Combine segments into larger chunks for embedding.
        
        Args:
            segments: Original transcription segments
            chunk_duration: Target duration per chunk in seconds
            
        Returns:
            List of combined segments
        """
        chunk_duration = chunk_duration or settings.transcript_chunk_size
        
        if not segments:
            return []
        
        chunks = []
        current_texts = []
        current_start = segments[0].start
        current_end = segments[0].start
        
        for seg in segments:
            if seg.start - current_start >= chunk_duration and current_texts:
                # Create chunk
                chunks.append(TranscriptionSegment(
                    text=" ".join(current_texts),
                    start=current_start,
                    end=current_end
                ))
                current_texts = []
                current_start = seg.start
            
            current_texts.append(seg.text)
            current_end = seg.end
        
        # Add remaining text
        if current_texts:
            chunks.append(TranscriptionSegment(
                text=" ".join(current_texts),
                start=current_start,
                end=current_end
            ))
        
        return chunks
