"""
Checkpointer service for managing LangGraph conversation persistence.

This service handles the creation and management of checkpointers for
LangGraph workflows, with PostgreSQL as primary and memory as fallback.

Uses proper PostgreSQL checkpointer patterns from LangGraph documentation.
Uses shared connection pool to prevent pool proliferation.
"""

from typing import Optional, Union
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings
from app.ai.services.engine_service import get_shared_pg_engine
from app.ai.services.shared_pool_service import get_shared_async_pool


class CheckpointerService:
    """
    Service for managing LangGraph checkpointers.

    Handles PostgreSQL checkpointer creation with graceful fallback
    to memory checkpointer when database is unavailable.

    Supports both sync and async checkpointers based on usage requirements.
    Uses proper PostgreSQL checkpointer patterns from LangGraph documentation.
    Uses shared connection pool to prevent pool proliferation.
    """

    # Singleton pattern to prevent multiple instances
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initialize checkpointer service with optional database session.
        """
        if self._initialized:
            return

        self._postgres_available = None
        self._initialized = True

        print("[CHECKPOINTER_SERVICE] Initialized singleton CheckpointerService")

    async def create_checkpointer(
        self, async_mode: bool = False
    ) -> Union["PostgresSaver", "AsyncPostgresSaver", "MemorySaver"]:
        """
        Create a checkpointer instance with PostgreSQL preferred, memory fallback.

        Args:
            async_mode: If True, create AsyncPostgresSaver, else PostgresSaver

        Returns:
            PostgresSaver/AsyncPostgresSaver if database available, MemorySaver as fallback
        """

        print(
            f"[CHECKPOINTER_SERVICE] Creating {'async' if async_mode else 'sync'} PostgreSQL checkpointer"
        )

        # Try PostgreSQL checkpointer first
        if async_mode:
            checkpointer = await self._create_async_postgres_checkpointer()
        else:
            checkpointer = self._create_postgres_checkpointer()

        if not checkpointer:
            # Fallback to memory checkpointer
            print(
                "[CHECKPOINTER_SERVICE] PostgreSQL not available, using memory checkpointer"
            )
            checkpointer = self._create_memory_checkpointer()

        return checkpointer

    async def _create_async_postgres_checkpointer(
        self,
    ) -> Optional["AsyncPostgresSaver"]:
        """
        Create AsyncPostgresSaver with proper async setup.

        Returns:
            AsyncPostgresSaver if successful, None if failed
        """
        try:
            # Check if PostgreSQL is available
            if not settings.DATABASE_URL:
                print(
                    "[CHECKPOINTER_SERVICE] DATABASE_URL not configured, using memory checkpointer"
                )
                return None

            print("[CHECKPOINTER_SERVICE] Creating async PostgreSQL checkpointer")

            # Import async version
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            # Use shared pool instead of creating new one
            print("[CHECKPOINTER_SERVICE] Getting shared async pool...")
            shared_pool = await get_shared_async_pool()
            print(
                "[CHECKPOINTER_SERVICE] Got shared async pool, creating AsyncPostgresSaver..."
            )
            checkpointer = AsyncPostgresSaver(shared_pool)

            print(
                "[CHECKPOINTER_SERVICE] AsyncPostgresSaver created successfully with shared pool"
            )

            # Setup the checkpointer (create tables) - REQUIRED by LangGraph
            try:
                print(
                    "[CHECKPOINTER_SERVICE] Starting AsyncPostgresSaver setup() call..."
                )

                # Add timeout to prevent indefinite hanging
                import asyncio

                async def setup_with_logging():
                    print("[CHECKPOINTER_SERVICE] Calling checkpointer.setup()...")
                    await checkpointer.setup()
                    print("[CHECKPOINTER_SERVICE] checkpointer.setup() completed")

                # Use asyncio.wait_for with timeout
                await asyncio.wait_for(setup_with_logging(), timeout=30.0)

                print(
                    "[CHECKPOINTER_SERVICE] AsyncPostgresSaver setup completed successfully"
                )
            except asyncio.TimeoutError:
                print(
                    "[CHECKPOINTER_SERVICE] AsyncPostgresSaver setup timed out after 30 seconds"
                )
                # Still return the checkpointer, setup can be tried again later
            except Exception as e:
                print(
                    f"[CHECKPOINTER_SERVICE] AsyncPostgresSaver setup failed: {str(e)}"
                )
                # Still return the checkpointer, setup can be tried again later

            self._postgres_available = True
            return checkpointer

        except Exception as e:
            print(
                f"[CHECKPOINTER_SERVICE] Async PostgreSQL checkpointer failed: {str(e)}"
            )
            self._postgres_available = False
            return None

    def _create_postgres_checkpointer(self) -> Optional["PostgresSaver"]:
        """
        Create PostgreSQL checkpointer using proper patterns from LangGraph documentation.

        Returns:
            PostgresSaverinstance or None if creation fails
        """
        try:
            # Check if we have a valid database URL
            if not settings.DATABASE_URL:
                print(
                    "[CHECKPOINTER_SERVICE] DATABASE_URL not configured, using memory checkpointer"
                )
                return None

            # Import sync version
            from langgraph.checkpoint.postgres import PostgresSaver

            # Get connection string for sync checkpointer
            connection_string = self._get_postgres_connection_string()

            # Create sync checkpointer using proper context manager pattern
            # We need to enter the context to get the actual checkpointer
            context_manager = PostgresSaver.from_conn_string(connection_string)

            # Enter the context to get the actual checkpointer
            # This is what the documentation shows: with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
            checkpointer = context_manager.__enter__()

            print("[CHECKPOINTER_SERVICE] PostgresSaver created successfully")

            # Setup the checkpointer (create tables) - REQUIRED by LangGraph
            try:
                checkpointer.setup()
                print(
                    "[CHECKPOINTER_SERVICE] PostgresSaver setup completed successfully"
                )
            except Exception as e:
                print(f"[CHECKPOINTER_SERVICE] PostgresSaver setup failed: {str(e)}")
                # Still return the checkpointer, setup can be tried again later

            self._postgres_available = True
            return checkpointer

        except Exception as e:
            print(f"[CHECKPOINTER_SERVICE] PostgreSQL checkpointer failed: {str(e)}")
            self._postgres_available = False
            return None

    def _get_postgres_connection_string(self) -> str:
        """
        Get PostgreSQL connection string for checkpointer.

        Returns:
            str: Connection string for PostgreSQL checkpointer
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

            # Convert to proper PostgreSQL format
            # PostgreSQL checkpointers expect: postgresql://user:password@host:port/database
            if url.startswith("postgresql+psycopg://"):
                return url.replace("postgresql+psycopg://", "postgresql://")
            else:
                return url

        except Exception as e:
            print(
                f"[CHECKPOINTER_SERVICE] Failed to get PostgreSQL connection string: {str(e)}"
            )
            # Fallback to original database URL
            return settings.DATABASE_URL

    def _create_memory_checkpointer(self) -> "MemorySaver":
        """
        Create memory checkpointer as fallback.

        Returns:
            MemorySaver instance
        """
        try:
            print("[CHECKPOINTER_SERVICE] Creating memory checkpointer (fallback)")

            checkpointer = MemorySaver()

            print("[CHECKPOINTER_SERVICE] Memory checkpointer created successfully")
            return checkpointer

        except Exception as e:
            print(
                f"[CHECKPOINTER_SERVICE] Failed to create memory checkpointer: {str(e)}"
            )
            raise RuntimeError(f"Cannot create any checkpointer: {str(e)}")

    async def delete_postgres_checkpointer(self, thread_id: str) -> None:
        """
        Delete all LangGraph checkpoint rows for a given thread_id.

        This clears persisted conversation history for that thread.

        Returns True on success, False if PostgreSQL is not configured or an error occurs.
        """
        try:
            if not settings.DATABASE_URL:
                # MemorySaver has no persistent store to clear
                print(
                    "[CHECKPOINTER_SERVICE] DATABASE_URL not configured. Nothing to clear."
                )
                return None

            pool = await get_shared_async_pool()
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    # Match LangGraph postgres schema table names
                    await cur.execute(
                        'DELETE FROM "checkpoint_writes" WHERE "thread_id" = %s',
                        (thread_id,),
                    )
                    await cur.execute(
                        'DELETE FROM "checkpoint_blobs" WHERE "thread_id" = %s',
                        (thread_id,),
                    )
                    await cur.execute(
                        'DELETE FROM "checkpoints" WHERE "thread_id" = %s',
                        (thread_id,),
                    )

            print(
                f"[CHECKPOINTER_SERVICE] Deleted checkpoints for thread_id: {thread_id}"
            )
        except Exception as e:
            print(
                f"[CHECKPOINTER_SERVICE] Failed to delete checkpoints for thread_id {thread_id}: {str(e)}"
            )

    def is_postgres_available(self) -> Optional[bool]:
        """
        Check if PostgreSQL checkpointer is available.

        Returns:
            True if available, False if not, None if not tested yet
        """
        return self._postgres_available

    def get_checkpointer_type(self, checkpointer) -> str:
        """
        Get the type of checkpointer for logging/debugging.

        Args:
            checkpointer: Checkpointer instance

        Returns:
            String describing checkpointer type
        """
        checkpointer_type = type(checkpointer).__name__
        if "PostgresSaver" in checkpointer_type:
            return "PostgreSQL"
        elif "MemorySaver" in checkpointer_type:
            return "Memory"
        else:
            return "Unknown"
