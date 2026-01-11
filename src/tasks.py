"""Background tasks for the application."""
import asyncio
from loguru import logger
from src.config import settings
from src.display_utils import update_departures_display
from src.mvg_api.v2.api import AsyncApi
from src.awtrix import AwtrixDisplay
from src.mqtt_client import MQTTClient


async def periodic_update_task(
    api: AsyncApi,
    awtrix_display: AwtrixDisplay | None,
    mqtt_client: MQTTClient | None,
):
    """
    Background task that updates departures periodically.
    
    Args:
        api: MVG API instance
        awtrix_display: Awtrix display controller instance
        mqtt_client: MQTT client instance
    """
    while True:
        try:
            await update_departures_display(api, awtrix_display, mqtt_client)
            await asyncio.sleep(settings.update_interval_seconds)
        except asyncio.CancelledError:
            logger.info("Periodic update task cancelled")
            break
        except Exception:
            logger.exception("Error in periodic update task")
            await asyncio.sleep(settings.update_interval_seconds)
