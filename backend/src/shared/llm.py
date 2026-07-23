import logging
import asyncio
import os
from typing import Optional
from groq import AsyncGroq
from groq import RateLimitError as GroqRateLimitError
from groq import InternalServerError as GroqServerError
from groq import APIConnectionError as GroqConnectionError
from google import genai
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from src.shared.config import config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class LLMResponse(BaseModel):
    content: str
    llm_used: str
    tokens_used: int

class LLMClient:
    def __init__(self):
        self.groq_client = None
        if config.GROQ_API_KEY:
            self.groq_client = AsyncGroq(api_key=config.GROQ_API_KEY)
            
        self.gemini_client = None
        if config.GEMINI_API_KEY:
            self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _groq_call(self, system: str, user: str) -> LLMResponse:
        if not self.groq_client:
            raise ValueError("Groq API key not configured")
        
        response = await self.groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0
        )
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        return LLMResponse(content=content, llm_used="groq", tokens_used=tokens)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _gemini_call(self, system: str, user: str) -> LLMResponse:
        if not self.gemini_client:
            raise ValueError("Gemini API key not configured")
            
        loop = asyncio.get_event_loop()
        
        def run_gemini():
            response = self.gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=user,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.0
                )
            )
            return response
            
        response = await loop.run_in_executor(None, run_gemini)
        
        tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            tokens = getattr(response.usage_metadata, 'total_token_count', 0)
            
        return LLMResponse(content=response.text, llm_used="gemini", tokens_used=tokens)

    async def complete(self, system: str, user: str) -> LLMResponse:
        """Tries Gemini first, falls back to Groq on failure."""
        try:
            return await self._gemini_call(system, user)
        except Exception as e:
            logger.warning(f"Gemini failed: {e}. Falling back to Groq.")
            try:
                return await self._groq_call(system, user)
            except Exception as groq_e:
                logger.error(f"Both Gemini and Groq failed. Gemini error: {e}, Groq error: {groq_e}")
                raise

# Singleton instance
llm_client = LLMClient()
