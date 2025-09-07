"""
Shared connection pool service for LangGraph checkpointers.

This service provides a single AsyncConnectionPool instance that all
checkpointers can share, eliminating connection pool proliferation.
"""

from typing import Optional
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from config import settings
from services.engine_service import get_shared_pg_engine

# Global shared pool instance
_shared_async_pool: Optional[AsyncConnectionPool] = None


async def get_shared_async_pool() -> AsyncConnectionPool:
    """
    Get shared AsyncConnectionPool instance for all checkpointers.

    This creates a single AsyncConnectionPool instance that all checkpointers
    can share, eliminating the need for multiple connection pools.

    Returns:
        AsyncConnectionPool: Shared pool instance

    Raises:
        RuntimeError: If pool creation fails
    """
    global _shared_async_pool

    if _shared_async_pool is None:
        try:
            # Use the same connection string as shared engine
            connection_string = _get_connection_string()

            print("[SHARED_POOL_SERVICE] Creating shared AsyncConnectionPool")

            # Create single pool instance with optimized settings for shared usage
            # Use open=False to prevent deprecated automatic opening in constructor
            _shared_async_pool = AsyncConnectionPool(
                conninfo=connection_string,
                max_size=15,  # Increased for shared usage across multiple workflows
                min_size=3,  # Keep some connections ready
                timeout=30,  # Connection timeout
                max_idle=600,  # Keep connections alive longer
                kwargs={"autocommit": True, "row_factory": dict_row},
                open=False,  # Prevent automatic opening in constructor (deprecated)
            )

            print(
                f"[SHARED_POOL_SERVICE] Created shared AsyncConnectionPool with max_size=15, min_size=3"
            )
            print(
                f"[SHARED_POOL_SERVICE] Using connection: {connection_string.split('@')[1] if '@' in connection_string else 'unknown'}"
            )

            # Open the pool to establish connections - CRITICAL for proper operation
            print(f"[SHARED_POOL_SERVICE] Opening AsyncConnectionPool...")
            await _shared_async_pool.open()
            print(f"[SHARED_POOL_SERVICE] AsyncConnectionPool opened successfully")

        except Exception as e:
            print(
                f"[SHARED_POOL_SERVICE] Failed to create shared AsyncConnectionPool: {str(e)}"
            )
            raise RuntimeError(f"Failed to create shared AsyncConnectionPool: {str(e)}")

    print(
        f"[SHARED_POOL_SERVICE] Returning shared pool (pool_id: {id(_shared_async_pool)})"
    )
    return _shared_async_pool


def _get_connection_string() -> str:
    """
    Get PostgreSQL connection string for the shared pool.

    Uses the same connection parameters as the shared engine.

    Returns:
        str: Connection string for PostgreSQL pool
    """
    try:
        # Get the shared engine and extract its connection string
        shared_engine = get_shared_pg_engine()

        # Extract connection info from the shared engine
        # This ensures we use the same connection parameters
        url = (
            str(shared_engine._engine.url)
            if hasattr(shared_engine, "_engine")
            else settings.DATABASE_URL
        )

        # Convert to proper PostgreSQL format for psycopg
        # PostgreSQL pools expect: postgresql://user:password@host:port/database
        if url.startswith("postgresql+psycopg://"):
            return url.replace("postgresql+psycopg://", "postgresql://")
        else:
            return url

    except Exception as e:
        print(f"[SHARED_POOL_SERVICE] Failed to get connection string: {str(e)}")
        # Fallback to original database URL
        return settings.DATABASE_URL


def reset_shared_pool():
    """
    Reset the shared pool (useful for testing or reconnection).

    This will force recreation of the pool on next get_shared_async_pool() call.
    """
    global _shared_async_pool

    if _shared_async_pool is not None:
        try:
            # Close the existing pool
            _shared_async_pool.close()
            print("[SHARED_POOL_SERVICE] Closed existing shared pool")
        except Exception as e:
            print(f"[SHARED_POOL_SERVICE] Error closing pool: {str(e)}")

    _shared_async_pool = None
    print("[SHARED_POOL_SERVICE] Reset shared pool")


def get_pool_stats() -> dict:
    """
    Get statistics about the shared pool.

    Returns:
        dict: Pool statistics including size, available connections, etc.
    """
    if _shared_async_pool is None:
        return {"status": "not_initialized"}

    try:
        # AsyncConnectionPool doesn't have get_size() method
        # Use available attributes and methods
        return {
            "status": "active",
            "pool_info": {
                "max_size": _shared_async_pool.max_size,
                "min_size": _shared_async_pool.min_size,
                "timeout": _shared_async_pool.timeout,
                "max_idle": _shared_async_pool.max_idle,
            },
            "connection_info": "AsyncConnectionPool statistics available",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
