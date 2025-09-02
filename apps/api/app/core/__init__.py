from pydantic_settings import BaseSettings
from typing import List, Optional
import os
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme


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

    # Google Cloud Configuration
    GOOGLE_CLOUD_PROJECT_ID: Optional[str] = os.getenv(
        "GOOGLE_CLOUD_PROJECT_ID")
    GOOGLE_CLOUD_STORAGE_BUCKET: Optional[str] = os.getenv(
        "GOOGLE_CLOUD_STORAGE_BUCKET")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS_JSON")
    GOOGLE_SEARCH_API_KEY: Optional[str] = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_SEARCH_ENGINE_ID: Optional[str] = os.getenv(
        "GOOGLE_SEARCH_ENGINE_ID")

    # Email Configuration
    SENDGRID_API_KEY: Optional[str] = os.getenv("SENDGRID_API_KEY")

    # Langfuse Configuration
    LANGFUSE_HOST: Optional[str] = os.getenv("LANGFUSE_HOST")
    LANGFUSE_SECRET_KEY: Optional[str] = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_PUBLIC_KEY: Optional[str] = os.getenv("LANGFUSE_PUBLIC_KEY")

    # AI Configuration
    LANGGRAPH_CHECKPOINT_SCHEMA: str = os.getenv(
        "LANGGRAPH_CHECKPOINT_SCHEMA", "langgraph_checkpoints")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")

    class Config:
        case_sensitive = True
        env_file = "apps/api/.env"


settings = Settings()


def setup_logging():
    """Configure beautiful colored logging with Rich."""

    # Create custom theme for log levels
    custom_theme = Theme({
        "logging.level.debug": "yellow",
        "logging.level.info": "green",
        "logging.level.warning": "orange3",
        "logging.level.error": "red",
        "logging.level.critical": "bold red",
        "logging.keyword": "cyan",
        "logging.string": "magenta",
        "logging.number": "bright_blue"
    })

    # Create console with custom theme
    console = Console(theme=custom_theme, force_terminal=True)

    # Create Rich handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_level=True,
        show_path=True,
        enable_link_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        locals_max_length=10,
        locals_max_string=80,
        keywords=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
    )

    # Configure rich handler format
    rich_handler.setFormatter(logging.Formatter(
        fmt="[%(name)s] %(message)s",
        datefmt="[%X]"
    ))

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Add rich handler
    root_logger.addHandler(rich_handler)

    # Configure specific loggers with appropriate levels
    loggers_config = {
        # AI module loggers - detailed logging
        "app.ai": logging.INFO,
        "app.ai.services": logging.INFO,
        "app.ai.chains": logging.INFO,
        "app.ai.nodes": logging.INFO,
        "app.ai.tools": logging.INFO,
        "app.ai.workflows": logging.INFO,

        # Core application loggers
        "app.services": logging.INFO,
        "app.api": logging.INFO,
        "app.core": logging.INFO,

        # Third-party libraries - less verbose
        "langchain": logging.WARNING,
        "openai": logging.WARNING,
        "httpx": logging.WARNING,
        "urllib3": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "alembic": logging.INFO,
        "uvicorn": logging.INFO,
        "uvicorn.access": logging.WARNING,  # Reduce HTTP request spam
        "fastapi": logging.INFO,

        # PDF processing libraries - silence debug spam
        "pdfminer": logging.WARNING,
        "pdfminer.pdfinterp": logging.ERROR,
        "pdfminer.pdfpage": logging.WARNING,
        "pdfminer.converter": logging.WARNING,
        "unstructured": logging.WARNING,
        "PIL": logging.WARNING,  # Pillow image processing
        "pytesseract": logging.WARNING,  # OCR library

        # Vector database
        "langchain_postgres": logging.WARNING,
        "psycopg": logging.WARNING,

        # Google Cloud
        "google": logging.WARNING,
        "google.cloud": logging.WARNING,
    }

    # Apply logger configurations
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = True  # Ensure messages propagate to root logger

    # Log the setup completion
    setup_logger = logging.getLogger("app.core.config")
    setup_logger.info(
        "🎨 [bold green]Rich colored logging configured![/bold green]")
    setup_logger.info(
        f"📊 Log level: [bold cyan]{settings.LOG_LEVEL}[/bold cyan]")
    setup_logger.info(
        f"🔧 Environment: [bold yellow]{settings.ENVIRONMENT}[/bold yellow]")
