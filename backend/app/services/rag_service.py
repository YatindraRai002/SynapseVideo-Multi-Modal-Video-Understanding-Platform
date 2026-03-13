"""
RAG (Retrieval-Augmented Generation) service.
Generates natural language answers based on retrieved video context.
"""
import logging
from typing import List, Dict, Any
from groq import Groq

from app.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    """
    RAG Service for synthesizing search results into answers.
    Uses Groq for fast LLM inference.
    """
    
    def __init__(self):
        self.api_key = settings.groq_api_key
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found in settings. RAG answers will be disabled.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)
    
    async def generate_answer(self, query: str, context: List[Any]) -> str:
        """
        Synthesize search results into a concise answer using Groq.
        """
        if not self.client:
            return "RAG engine is unavailable (API key missing)."
            
        if not context:
            return "No relevant video context found to answer your query."

        # Construct prompt
        context_str = self._format_context(context)
        
        prompt = f"""
        You are a helpful video search assistant. Answer the user's query based ONLY on the provided video context.
        The context includes partial transcripts and frame descriptions from specific timestamps.
        
        USER QUERY: {query}
        
        VIDEO CONTEXT:
        {context_str}
        
        INSTRUCTIONS:
        1. Be concise and direct. Use natural language.
        2. Mention specific timestamps (e.g., [01:23]) when citing information.
        3. If the context doesn't contain the answer, say "I couldn't find the answer in the video content."
        4. Focus on what is explicitly seen or heard in the video.
        
        ANSWER:
        """
        
        try:
            # We use a thread-safe way to call the sync client or use async if supported
            # For simplicity, we'll call the groq client
            completion = self.client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": "You are a concise video assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.1
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            return "Error generating answer from AI provider."

    def _format_context(self, context: List[Any]) -> str:
        """Format retrieved snapshots/segments into a readable block."""
        formatted = []
        for i, item in enumerate(context[:8], 1):  # Use top 8 results for better context
            timestamp = getattr(item, 'timestamp', 0)
            text = ""
            
            # Extract text from either transcript or frame caption
            if hasattr(item, 'transcript_snippet') and item.transcript_snippet:
                text += f"Spoken: \"{item.transcript_snippet}\" "
            if hasattr(item, 'frame_caption') and item.frame_caption:
                text += f"Visual: {item.frame_caption}"
            
            time_str = f"{int(timestamp // 60):02d}:{int(timestamp % 60):02d}"
            formatted.append(f"[{i}] Time @ {time_str}: {text}")
                
        return "\n".join(formatted)

# Global instance
rag_service = RAGService()
