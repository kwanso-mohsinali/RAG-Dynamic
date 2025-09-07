from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.core.config import settings, setup_logging
from app.api.v1.api import api_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    logger.info("Creating FastAPI application...")
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
    )

    # CORS middleware
    if settings.ALLOWED_HOSTS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_HOSTS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Debug mode: {settings.DEBUG}")
        logger.info(f"Log level: {settings.LOG_LEVEL}")

    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.VERSION,
            "docs": f"{settings.API_V1_STR}/docs",
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}


    return app


app = create_application()
