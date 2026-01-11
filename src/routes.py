"""FastAPI routes."""
from fastapi import APIRouter
from loguru import logger
from src.display_utils import update_departures_display

router = APIRouter()


def get_app_instances():
    """Get application instances from app module to avoid circular imports."""
    from src.app import api, awtrix_display, mqtt_client
    return api, awtrix_display, mqtt_client


@router.get("/departures")
async def get_departures():
    """Get departures for configured stations and update Awtrix display."""
    logger.debug("Departures endpoint called")
    api, awtrix_display, mqtt_client = get_app_instances()
    departures = await update_departures_display(api, awtrix_display, mqtt_client)
    return departures
