import logging
import asyncio
import os
from typing import Optional, List
from groq import AsyncGroq
from groq import RateLimitError as GroqRateLimitError
from groq import InternalServerError as GroqServerError
from groq import APIConnectionError as GroqConnectionError
from google import genai
from pydantic import BaseModel

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
            self.groq_client = AsyncGroq(api_key=config.GROQ_API_KEY, max_retries=0)
        
        # Parse comma-separated Gemini API keys and create a client pool
        self.gemini_clients: List[genai.Client] = []
        raw_keys = config.GEMINI_API_KEYS
        if raw_keys:
            keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
            for key in keys:
                self.gemini_clients.append(genai.Client(api_key=key))
            logger.info(f"Initialized {len(self.gemini_clients)} Gemini API key(s) for rotation.")

        # Round-robin index
        self._gemini_idx = 0

    async def _groq_call(self, system: str, user: str) -> LLMResponse:
        if not self.groq_client:
            raise ValueError("Groq API key not configured")
        
        response = await self.groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else 0
        return LLMResponse(content=content, llm_used="groq", tokens_used=tokens)

    async def _gemini_call_with_client(self, client: genai.Client, system: str, user: str) -> LLMResponse:
        loop = asyncio.get_event_loop()
        
        def run_gemini():
            response = client.models.generate_content(
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

    async def _gemini_call(self, system: str, user: str) -> LLMResponse:
        """Try each Gemini key in round-robin order. If one hits a rate limit, rotate to the next."""
        if not self.gemini_clients:
            raise ValueError("No Gemini API keys configured")
        
        n = len(self.gemini_clients)
        last_error = None
        
        for attempt in range(n):
            idx = (self._gemini_idx + attempt) % n
            client = self.gemini_clients[idx]
            try:
                result = await self._gemini_call_with_client(client, system, user)
                # Success — advance the index for next call (round-robin)
                self._gemini_idx = (idx + 1) % n
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Gemini key #{idx + 1}/{n} failed: {type(e).__name__}. Trying next key...")
        
        # All keys exhausted — advance index anyway so next call starts from a different key
        self._gemini_idx = (self._gemini_idx + 1) % n
        raise last_error  # type: ignore

    async def complete(self, system: str, user: str) -> LLMResponse:
        """Tries all Gemini keys first (with rotation), falls back to Groq on failure."""
        try:
            return await self._gemini_call(system, user)
        except Exception as e:
            logger.warning(f"All Gemini keys failed: {e}. Falling back to Groq.")
            try:
                return await self._groq_call(system, user)
            except Exception as groq_e:
                logger.error(f"Both Gemini and Groq failed. Gemini error: {e}, Groq error: {groq_e}")
                raise

# Singleton instance
llm_client = LLMClient()

