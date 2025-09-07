from langchain_postgres import PGEngine
from config import settings

# Global shared engine instance
_shared_pg_engine = None


def get_shared_pg_engine() -> PGEngine:
    """
    Get shared PGEngine instance for all AI services.

    This creates a single PGEngine instance that all services can share,
    eliminating connection pool proliferation.

    Returns:
        PGEngine: Shared engine instance

    Raises:
        RuntimeError: If engine creation fails
    """
    global _shared_pg_engine

    if _shared_pg_engine is None:
        try:
            # Use DATABASE_URL directly from .env file
            database_url = settings.DATABASE_URL
            if not database_url:
                raise RuntimeError("DATABASE_URL is not configured")

            # Convert URL for psycopg3 compatibility (only psycopg3 is installed)
            if database_url.startswith("postgres://"):
                # Heroku uses postgres://, convert to postgresql+psycopg:// for psycopg3
                langchain_url = database_url.replace(
                    "postgres://", "postgresql+psycopg://"
                )
            elif database_url.startswith("postgresql://"):
                # Convert standard postgresql:// to psycopg3 format
                langchain_url = database_url.replace(
                    "postgresql://", "postgresql+psycopg://"
                )
            else:
                langchain_url = database_url

            print(f"[ENGINE_SERVICE] Creating PGEngine with psycopg3 driver")

            # Create single PGEngine instance
            _shared_pg_engine = PGEngine.from_connection_string(url=langchain_url)

            print("[ENGINE_SERVICE] Successfully created shared PGEngine instance")

        except Exception as e:
            print(f"[ENGINE_SERVICE] Failed to create shared PGEngine: {str(e)}")
            raise RuntimeError(f"Failed to create shared PGEngine: {str(e)}")

    return _shared_pg_engine


def reset_shared_engine():
    """
    Reset the shared engine (useful for testing or reconnection).

    This will force recreation of the engine on next get_shared_pg_engine() call.
    """
    global _shared_pg_engine
    _shared_pg_engine = None
    print("[ENGINE_SERVICE] Reset shared engine")
