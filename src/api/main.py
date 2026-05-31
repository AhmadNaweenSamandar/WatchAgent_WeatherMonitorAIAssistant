import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.db.database import initialize_database, get_db_connection
from src.core.poller import weather_polling_loop
from src.api.routes import router

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global reference to our background task
poller_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the FastAPI application.
    Executes startup logic (DB init, background tasks) and graceful teardown.
    """
    global poller_task
    
    # 1. Initialize Database Schema
    logger.info("Initializing database schema...")
    await initialize_database()
    
    # 2. Start the Poller Daemon
    logger.info("Starting background poller task...")
    # We use an async generator manually here to pass a single connection to the loop
    db_gen = get_db_connection()
    db_connection = await anext(db_gen)
    poller_task = asyncio.create_task(weather_polling_loop(db_connection))
    
    yield  # The FastAPI application runs while yielded
    
    # 3. Graceful Shutdown
    logger.info("Shutting down application...")
    if poller_task:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            logger.info("Poller task successfully cancelled.")
            
    # Close the lingering database connection
    try:
        await anext(db_gen)
    except StopAsyncIteration:
        pass

# Initialize the core application
app = FastAPI(
    title="WatchAgent: Weather Monitor & AI Assistant",
    description="Autonomous meteorological event detection system.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)