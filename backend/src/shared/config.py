import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATA_DIR: str = "/data"
    
    GROQ_API_KEY: str = ""
    GEMINI_API_KEYS: str = ""  # Comma-separated list of Gemini API keys for rotation
    ADMIN_SECRET: str = "super_secret_admin_token"
    YOUTUBE_API_KEY: str = ""
    SERPAPI_KEY: str = ""
    
    reddit_intent_queries: dict = {}
    reddit_subreddits: list = []
    
    youtube_intent_queries: dict = {}

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def CHROMA_DIR(self) -> str:
        return os.path.join(self.DATA_DIR, "chroma")

    @property
    def SQLITE_PATH(self) -> str:
        return os.path.join(self.DATA_DIR, "engine.db")

config = Settings()
