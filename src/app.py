"""FastAPI application setup and lifecycle management."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from src.config import settings
from src.mqtt_client import MQTTClient
from src.awtrix import AwtrixDisplay
from src.mvg_api.v2.api import AsyncApi
from src.tasks import periodic_update_task
from src.routes import router

# Global instances
api = AsyncApi()
mqtt_client: MQTTClient | None = None
awtrix_display: AwtrixDisplay | None = None
background_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global mqtt_client, awtrix_display, background_task
    
    # Startup
    logger.info("Starting application...")
    logger.info(
        f"Connecting to MQTT broker at {settings.mqtt_broker_host}:{settings.mqtt_broker_port}"
    )
    mqtt_client = MQTTClient(
        host=settings.mqtt_broker_host,
        port=settings.mqtt_broker_port,
    )
    mqtt_client.connect()

    # Initialize Awtrix display controller
    logger.info(
        f"Initializing Awtrix display with topic prefix: {settings.awtrix_topic_prefix}"
    )
    awtrix_display = AwtrixDisplay(
        mqtt_client, topic_prefix=settings.awtrix_topic_prefix
    )

    # Start background task for periodic updates
    logger.info(
        f"Starting periodic update task (interval: {settings.update_interval_seconds}s)"
    )
    background_task = asyncio.create_task(
        periodic_update_task(api, awtrix_display, mqtt_client)
    )

    yield

    # Shutdown
    logger.info("Shutting down application...")
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    if mqtt_client:
        mqtt_client.disconnect()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MVG Awtrix Display",
        description="Service to display MVG departures on Awtrix display",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(router)

    return app


# Create app instance
app = create_app()
