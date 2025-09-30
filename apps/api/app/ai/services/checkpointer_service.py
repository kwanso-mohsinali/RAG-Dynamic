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
import logging

logger = logging.getLogger(__name__)

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

        logger.info("[CHECKPOINTER_SERVICE] Initialized singleton CheckpointerService")

    async def _check_checkpointer_tables_exist(self) -> bool:
        """
        Check if LangGraph checkpointer tables already exist in the database.

        This prevents hanging setup() calls on Heroku by checking if tables
        were created in previous runs.

        Returns:
            bool: True if all required tables exist, False otherwise
        """
        try:
            # Get shared async pool
            logger.info(
                "[CHECKPOINTER_SERVICE] Getting shared async pool for table check...")
            shared_pool = await get_shared_async_pool()
            logger.info(
                "[CHECKPOINTER_SERVICE] Got shared async pool, checking tables...")

            # Check if all required tables exist
            async with shared_pool.connection() as conn:
                logger.info(
                    "[CHECKPOINTER_SERVICE] Database connection established")

                async with conn.cursor() as cursor:
                    logger.info(
                        "[CHECKPOINTER_SERVICE] Cursor created, checking tables...")

                    # Check for all four required tables
                    tables_to_check = [
                        'checkpoints',
                        'checkpoint_blobs',
                        'checkpoint_migrations',
                        'checkpoint_writes'
                    ]

                    for table_name in tables_to_check:
                        logger.info(
                            f"[CHECKPOINTER_SERVICE] Checking table: {table_name}")

                        try:
                            await cursor.execute("""
                                SELECT EXISTS (
                                    SELECT FROM information_schema.tables 
                                    WHERE table_schema = 'public' 
                                    AND table_name = %s
                                )
                            """, (table_name,))

                            exists = await cursor.fetchone()
                            logger.info(
                                f"[CHECKPOINTER_SERVICE] Table '{table_name}' exists: {exists}")

                            # Handle both dict and tuple return types from different psycopg versions
                            if isinstance(exists, dict):
                                # psycopg3 with dict_row factory
                                exists_value = exists.get('exists', False)
                            else:
                                # psycopg2 or other drivers return tuples
                                exists_value = exists[0] if exists else False

                            logger.info(
                                f"[CHECKPOINTER_SERVICE] Table '{table_name}' exists value: {exists_value}")

                            if not exists_value:
                                logger.info(
                                    f"[CHECKPOINTER_SERVICE] Table '{table_name}' does not exist")
                                return False

                        except Exception as table_check_error:
                            logger.error(
                                f"[CHECKPOINTER_SERVICE] Error checking table '{table_name}': {str(table_check_error)}")
                            return False

                    logger.info(
                        "[CHECKPOINTER_SERVICE] All checkpointer tables already exist")
                    return True

        except Exception as e:
            logger.error(
                f"[CHECKPOINTER_SERVICE] Error checking table existence: {str(e)}")
            logger.error(f"[CHECKPOINTER_SERVICE] Error type: {type(e)}")
            import traceback
            logger.error(
                f"[CHECKPOINTER_SERVICE] Traceback: {traceback.format_exc()}")
            
             # CRITICAL: Reset pool on timeout to prevent deadlock
            if "couldn't get a connection" in str(e).lower():
                logger.warning("[CHECKPOINTER_SERVICE] Pool timeout detected, resetting pool...")
                from app.ai.services.shared_pool_service import reset_shared_pool
                reset_shared_pool()
            # If we can't check, assume tables don't exist and proceed with setup
            return False

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

        logger.info(
            f"[CHECKPOINTER_SERVICE] Creating {'async' if async_mode else 'sync'} PostgreSQL checkpointer"
        )

        # Try PostgreSQL checkpointer first
        if async_mode:
            checkpointer = await self._create_async_postgres_checkpointer()
        else:
            checkpointer = self._create_postgres_checkpointer()

        if not checkpointer:
            # Fallback to memory checkpointer
            logger.info(
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
                logger.warning(
                    "[CHECKPOINTER_SERVICE] DATABASE_URL not configured, using memory checkpointer")
                return None

            logger.info(
                "[CHECKPOINTER_SERVICE] Creating async PostgreSQL checkpointer")

            # Import async version
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            # Use shared pool instead of creating new one
            logger.info(
                "[CHECKPOINTER_SERVICE] Getting shared async pool...")
            shared_pool = await get_shared_async_pool()
            logger.info(
                "[CHECKPOINTER_SERVICE] Got shared async pool, creating AsyncPostgresSaver...")
            checkpointer = AsyncPostgresSaver(shared_pool)

            logger.info(
                "[CHECKPOINTER_SERVICE] AsyncPostgresSaver created successfully with shared pool")

            # Check if tables already exist before calling setup()
            logger.info(
                "[CHECKPOINTER_SERVICE] Checking if checkpointer tables already exist...")

            if await self._check_checkpointer_tables_exist():
                logger.info(
                    "[CHECKPOINTER_SERVICE] Tables already exist, skipping setup() call")
            else:
                logger.info(
                    "[CHECKPOINTER_SERVICE] Tables don't exist, calling setup() to create them...")


            # Setup the checkpointer (create tables) - REQUIRED by LangGraph
            try:
                logger.info(
                    "[CHECKPOINTER_SERVICE] Starting AsyncPostgresSaver setup() call..."
                )

                # Add timeout to prevent indefinite hanging
                import asyncio

                async def setup_with_logging():
                    logger.info("[CHECKPOINTER_SERVICE] Calling checkpointer.setup()...")
                    await checkpointer.setup()
                    logger.info("[CHECKPOINTER_SERVICE] checkpointer.setup() completed")

                # Use asyncio.wait_for with timeout
                await asyncio.wait_for(setup_with_logging(), timeout=30.0)

                logger.info(
                    "[CHECKPOINTER_SERVICE] AsyncPostgresSaver setup completed successfully"
                )
            except asyncio.TimeoutError:
                logger.info(
                    "[CHECKPOINTER_SERVICE] AsyncPostgresSaver setup timed out after 30 seconds"
                )
                # Still return the checkpointer, setup can be tried again later
            except Exception as e:
                logger.error(
                    f"[CHECKPOINTER_SERVICE] AsyncPostgresSaver setup failed: {str(e)}"
                )
                # Still return the checkpointer, setup can be tried again later

            self._postgres_available = True
            return checkpointer

        except Exception as e:
            logger.error(
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
                logger.warning(
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

            logger.info("[CHECKPOINTER_SERVICE] PostgresSaver created successfully")

            # Setup the checkpointer (create tables) - REQUIRED by LangGraph
            try:
                checkpointer.setup()
                logger.info(
                    "[CHECKPOINTER_SERVICE] PostgresSaver setup completed successfully"
                )
            except Exception as e:
                logger.error(f"[CHECKPOINTER_SERVICE] PostgresSaver setup failed: {str(e)}")
                # Still return the checkpointer, setup can be tried again later

            self._postgres_available = True
            return checkpointer

        except Exception as e:
            logger.error(f"[CHECKPOINTER_SERVICE] PostgreSQL checkpointer failed: {str(e)}")
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
            logger.error(
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
            logger.info("[CHECKPOINTER_SERVICE] Creating memory checkpointer (fallback)")

            checkpointer = MemorySaver()

            logger.info("[CHECKPOINTER_SERVICE] Memory checkpointer created successfully")
            return checkpointer

        except Exception as e:
            logger.error(
                f"[CHECKPOINTER_SERVICE] Failed to create memory checkpointer: {str(e)}"
            )
            raise RuntimeError(f"Cannot create any checkpointer: {str(e)}")

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

    async def debug_checkpointer_tables(self) -> dict:
        """
        Debug method to check the status of all checkpointer tables.

        Returns:
            dict: Status of each table and overall status
        """
        try:
            logger.info(
                "[CHECKPOINTER_SERVICE] Debug: Getting shared async pool...")
            shared_pool = await get_shared_async_pool()
            logger.info(
                "[CHECKPOINTER_SERVICE] Debug: Got shared pool, testing connection...")

            # Test basic connection first
            try:
                async with shared_pool.connection() as conn:
                    logger.info(
                        "[CHECKPOINTER_SERVICE] Debug: Connection established successfully")

                    # Test a simple query
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                        result = await cursor.fetchone()
                        logger.info(
                            f"[CHECKPOINTER_SERVICE] Debug: Simple query result: {result}")

                        if result and result[0] == 1:
                            logger.info(
                                "[CHECKPOINTER_SERVICE] Debug: Basic database connectivity confirmed")
                        else:
                            logger.error(
                                "[CHECKPOINTER_SERVICE] Debug: Basic query failed")
                            return {"error": "Basic query failed", "status": "error"}

                    # Now check tables
                    async with conn.cursor() as cursor:
                        tables_to_check = [
                            'checkpoints',
                            'checkpoint_blobs',
                            'checkpoint_migrations',
                            'checkpoint_writes'
                        ]

                        table_status = {}
                        all_exist = True

                        for table_name in tables_to_check:
                            logger.info(
                                f"[CHECKPOINTER_SERVICE] Debug: Checking table {table_name}")

                            try:
                                await cursor.execute("""
                                    SELECT EXISTS (
                                        SELECT FROM information_schema.tables 
                                        WHERE table_schema = 'public' 
                                        AND table_name = %s
                                    )
                                """, (table_name,))

                                exists = await cursor.fetchone()

                                # Handle both dict and tuple return types
                                if isinstance(exists, dict):
                                    exists_value = exists.get('exists', False)
                                else:
                                    exists_value = exists[0] if exists else False

                                table_status[table_name] = exists_value
                                logger.info(
                                    f"[CHECKPOINTER_SERVICE] Debug: Table {table_name} exists: {table_status[table_name]}")

                                if not exists_value:
                                    all_exist = False

                            except Exception as table_error:
                                logger.error(
                                    f"[CHECKPOINTER_SERVICE] Debug: Error checking table {table_name}: {str(table_error)}")
                                table_status[table_name] = False
                                all_exist = False

                        return {
                            "tables": table_status,
                            "all_tables_exist": all_exist,
                            "status": "ready" if all_exist else "missing_tables",
                            "connection": "working"
                        }

            except Exception as conn_error:
                logger.error(
                    f"[CHECKPOINTER_SERVICE] Debug: Connection error: {str(conn_error)}")
                return {"error": f"Connection failed: {str(conn_error)}", "status": "error"}

        except Exception as e:
            logger.error(
                f"[CHECKPOINTER_SERVICE] Debug: General error: {str(e)}")
            return {
                "error": str(e),
                "status": "error"
            }

    async def test_database_connection(self) -> dict:
        """
        Simple method to test basic database connectivity.

        Returns:
            dict: Connection test results
        """
        try:
            logger.info(
                "[CHECKPOINTER_SERVICE] Testing basic database connection...")

            # Get shared pool
            shared_pool = await get_shared_async_pool()
            logger.info("[CHECKPOINTER_SERVICE] Got shared pool")

            # Test connection
            async with shared_pool.connection() as conn:
                logger.info("[CHECKPOINTER_SERVICE] Connection established")

                # Test simple query
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT version()")
                    version = await cursor.fetchone()
                    logger.info(
                        f"[CHECKPOINTER_SERVICE] PostgreSQL version: {version}")

                    return {
                        "status": "connected",
                        "version": str(version[0]) if version else "unknown",
                        "message": "Database connection successful"
                    }

        except Exception as e:
            logger.error(
                f"[CHECKPOINTER_SERVICE] Connection test failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "message": "Database connection failed"
            }