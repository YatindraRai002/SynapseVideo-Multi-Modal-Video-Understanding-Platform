"""
Embedding service for text and images.
Uses CLIP for image embeddings and sentence-transformers for text.
"""

from pathlib import Path
from typing import List, Union
import torch
from PIL import Image
import numpy as np

from app.config import settings


class Embedder:
    """Generates embeddings for text and images."""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._clip_model = None
        self._clip_processor = None
        self._text_model = None
    
    def _load_clip(self):
        """Lazy load CLIP model."""
        if self._clip_model is None:
            from transformers import CLIPProcessor, CLIPModel
            
            print(f"Loading CLIP model '{settings.clip_model}'...")
            model_name = f"openai/clip-vit-base-patch32"
            self._clip_model = CLIPModel.from_pretrained(model_name).to(self.device)
            self._clip_processor = CLIPProcessor.from_pretrained(model_name)
            print("CLIP model loaded!")
    
    def _load_text_model(self):
        """Lazy load sentence-transformers model."""
        if self._text_model is None:
            from sentence_transformers import SentenceTransformer
            
            print(f"Loading text embedding model '{settings.text_embedding_model}'...")
            self._text_model = SentenceTransformer(
                settings.text_embedding_model,
                device=self.device
            )
            print("Text model loaded!")
    
    async def embed_text(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for text using sentence-transformers.
        
        Args:
            texts: List of text strings
            
        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        self._load_text_model()
        
        embeddings = self._text_model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        return embeddings
    
    async def embed_images(self, image_paths: List[Path]) -> np.ndarray:
        """
        Generate CLIP embeddings for images.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            numpy array of shape (len(images), 512)
        """
        self._load_clip()
        
        images = [Image.open(p).convert("RGB") for p in image_paths]
        
        inputs = self._clip_processor(
            images=images,
            return_tensors="pt"
        ).to(self.device)
        
        with torch.no_grad():
            image_features = self._clip_model.get_image_features(**inputs)
        
        # Handle output from model
        if hasattr(image_features, 'pooler_output'):
            image_features = image_features.pooler_output
        elif hasattr(image_features, 'last_hidden_state'):
            image_features = image_features.last_hidden_state[:, 0, :]  # Take CLS token
            
        # Convert to numpy
        if hasattr(image_features, 'cpu'):
            embeddings = image_features.cpu().numpy()
        else:
            embeddings = np.array(image_features)
            
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        return embeddings
    
    async def embed_text_clip(self, texts: List[str]) -> np.ndarray:
        """
        Generate CLIP text embeddings (for image-text similarity).
        
        Args:
            texts: List of text strings
            
        Returns:
            numpy array of shape (len(texts), 512)
        """
        self._load_clip()
        
        inputs = self._clip_processor(
            text=texts,
            return_tensors="pt",
            padding=True,
            truncation=True
        ).to(self.device)
        
        with torch.no_grad():
            text_features = self._clip_model.get_text_features(**inputs)
        
        # Handle output from model
        if hasattr(text_features, 'pooler_output'):
            text_features = text_features.pooler_output
        elif hasattr(text_features, 'last_hidden_state'):
            text_features = text_features.last_hidden_state[:, 0, :]
            
        if hasattr(text_features, 'cpu'):
            embeddings = text_features.cpu().numpy()
        else:
            embeddings = np.array(text_features)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        return embeddings
    
    async def generate_caption(self, image_path: Path) -> str:
        """
        Generate a text caption for an image using BLIP.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Generated caption string
        """
        try:
            # Load BLIP model lazily
            if not hasattr(self, '_blip_processor') or self._blip_processor is None:
                from transformers import BlipProcessor, BlipForConditionalGeneration
                
                print("Loading BLIP captioning model...")
                model_name = "Salesforce/blip-image-captioning-base"
                self._blip_processor = BlipProcessor.from_pretrained(model_name)
                self._blip_model = BlipForConditionalGeneration.from_pretrained(model_name).to(self.device)
                print("BLIP model loaded!")
            
            # Load and process image
            image = Image.open(image_path).convert("RGB")
            inputs = self._blip_processor(image, return_tensors="pt").to(self.device)
            
            # Generate caption
            with torch.no_grad():
                out = self._blip_model.generate(**inputs, max_length=50)
            
            caption = self._blip_processor.decode(out[0], skip_special_tokens=True)
            return caption.strip()
            
        except Exception as e:
            print(f"Caption generation error: {e}")
            # Return a generic caption on error
            return "Frame from video"
