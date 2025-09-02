from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Project Information
    PROJECT_NAME: str = "Rag-Dynamic"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "A scalable FastAPI backend"

    # API Configuration
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # CORS - Updated for separate frontend deployment
    ALLOWED_HOSTS: List[str] = [
        "http://localhost:4200",  # Local development
        "http://localhost:3000",  # Alternative local port
        "https://ai-agent-portal-staging.herokuapp.com",  # Your frontend Heroku app
        "*",  # Allow all origins for now (you can restrict this later)
    ]

    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Redis (for caching/sessions)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    # External APIs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        case_sensitive = True
        env_file = "apps/api/.env"


settings = Settings()