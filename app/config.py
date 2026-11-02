from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./finn.db"
    
    # MongoDB Connection (Local or Atlas)
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "finn_db"

    # Google OAuth App Credentials
    GOOGLE_CLIENT_ID: Optional[str] = ""
    GOOGLE_CLIENT_SECRET: Optional[str] = ""

    # Gemini AI
    GEMINI_API_KEY: str = ""
    
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
