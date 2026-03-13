"""
Visual captioning service using BLIP (Bootstrapping Language-Image Pre-training).
Generates natural language descriptions for video frames.
"""

import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
from pathlib import Path
from typing import List, Optional

class VisualTagger:
    """
    Uses Salesforce/blip-image-captioning-base to generate 
    descriptive captions for video frames.
    """
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = None
        self.model = None
    
    def _load_model(self):
        """Lazy load BLIP model."""
        if self.model is None:
            print(f"[*] Loading BLIP model on {self.device}...")
            model_id = "Salesforce/blip-image-captioning-base"
            
            self.processor = BlipProcessor.from_pretrained(model_id)
            self.model = BlipForConditionalGeneration.from_pretrained(model_id).to(self.device)
            self.model.eval()
            
            print("[+] BLIP model loaded successfully")

    async def generate_caption(self, image_path: Path) -> str:
        """
        Generate a descriptive caption for a single image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            String description of the image content.
        """
        try:
            self._load_model()
        except Exception as e:
            print(f"[ERROR] Captioning failed for {image_path}: Model load error: {e}")
            return "Visual content available"
        
        try:
            image = Image.open(image_path).convert("RGB")
            
            # Prepare inputs
            inputs = self.processor(image, return_tensors="pt").to(self.device)
            
            # Generate caption
            with torch.no_grad():
                out = self.model.generate(**inputs, max_new_tokens=50)
            
            caption = self.processor.decode(out[0], skip_special_tokens=True)
            return caption
            
        except Exception as e:
            print(f"[ERROR] Captioning failed for {image_path}: {e}")
            return "Visual content available"

    async def tag_frame(self, image_path: Path) -> List[str]:
        """
        Legacy wrapper for compatibility with existing pipeline.
        In Elite mode, we return the caption as a single-item list.
        """
        caption = await self.generate_caption(image_path)
        return [caption]

visual_tagger = VisualTagger()
