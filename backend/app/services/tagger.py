"""
Visual captioning service using Groq Vision API.
Generates natural language descriptions for video frames quickly.
"""

from pathlib import Path
from typing import List
import base64

from app.config import settings

class VisualTagger:
    """
    Uses Groq's Vision LLM to generate descriptive captions for video frames.
    Significantly faster than local BLIP models.
    """
    
    def __init__(self):
        self.client = None
        if settings.groq_api_key:
            try:
                from groq import AsyncGroq
                self.client = AsyncGroq(api_key=settings.groq_api_key)
            except ImportError:
                print("[!] groq package not installed, visual tagging will use fallback.")
    
    def _encode_image(self, image_path: Path) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def generate_caption(self, image_path: Path) -> str:
        """
        Generate a descriptive caption for a single image using Groq API.
        """
        if not self.client:
            return "Visual content available in frame"
            
        try:
            base64_image = self._encode_image(image_path)
            
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image in a brief sentence. Focus on key actions and objects."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
                model="llama-3.2-11b-vision-preview",
                temperature=0.2,
                max_tokens=50
            )
            
            caption = chat_completion.choices[0].message.content.strip()
            return caption
            
        except Exception as e:
            print(f"[ERROR] Groq Vision Captioning failed for {image_path}: {e}")
            return "Visual content available in frame"

    async def tag_frame(self, image_path: Path) -> List[str]:
        """
        Wrapper returning the caption as a single-item list.
        """
        caption = await self.generate_caption(image_path)
        return [caption]

visual_tagger = VisualTagger()
