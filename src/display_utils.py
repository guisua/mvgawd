"""Utilities for fetching departures and updating the Awtrix display."""
from loguru import logger
from src.config import settings
from src.mvg_api.v2.api import AsyncApi
from src.awtrix import AwtrixDisplay
from src.mqtt_client import MQTTClient


async def update_departures_display(
    api: AsyncApi,
    awtrix_display: AwtrixDisplay | None,
    mqtt_client: MQTTClient | None,
) -> list:
    """
    Fetch departures and send to Awtrix display.
    
    Args:
        api: MVG API instance
        awtrix_display: Awtrix display controller instance
        mqtt_client: MQTT client instance
        
    Returns:
        List of next departures (tram + ubahn)
    """
    try:
        logger.debug(f"Fetching TRAM departures for station {settings.station_id_tram}")
        departures_tram = await api.get_departures(
            settings.station_id_tram, transport_types="TRAM"
        )
        logger.debug(
            f"Fetching UBAHN departures for station {settings.station_id_ubahn}"
        )
        departures_ubahn = await api.get_departures(
            settings.station_id_ubahn, transport_types="UBAHN"
        )

        # Extract departures for the configured stop point
        departures_tram = [
            departure
            for departure in departures_tram
            if departure.stopPointGlobalId == settings.stop_point_id_tram
        ]

        # Next two departures, in ceil minutes from now
        next_departures_tram = sorted(
            departures_tram, key=lambda x: x.minutes_until_departure
        )[:2]

        departures_ubahn = [
            departure
            for departure in departures_ubahn
            if departure.stopPointGlobalId == settings.stop_point_id_ubahn
        ]
        next_departures_ubahn = sorted(
            departures_ubahn, key=lambda x: x.minutes_until_departure
        )[:2]

        # Send raw draw message to Awtrix display if connected
        if awtrix_display and mqtt_client and mqtt_client.is_connected:
            draw_payload = {
                "draw": [
                    {"df": [0, 2, 16, 5, "FF0000"]},
                    {"df": [1, 1, 14, 7, "FF0000"]},
                    {
                        "dt": [
                            1,
                            2,
                            "'".join(
                                [
                                    str(departure.minutes_until_departure)
                                    for departure in next_departures_tram
                                ]
                            ),
                            "FFFFFF",
                        ]
                    },
                    {"df": [16, 2, 16, 5, "915900"]},
                    {"df": [17, 1, 14, 7, "915900"]},
                    {
                        "dt": [
                            18,
                            2,
                            "'".join(
                                [
                                    str(departure.minutes_until_departure)
                                    for departure in next_departures_ubahn
                                ]
                            ),
                            "FFFFFF",
                        ]
                    },
                ]
            }
            awtrix_display.send_raw_message(
                settings.awtrix_raw_message_subtopic, draw_payload
            )
            logger.debug(
                f"Sent departures to Awtrix: TRAM {[d.minutes_until_departure for d in next_departures_tram]}, "
                f"UBAHN {[d.minutes_until_departure for d in next_departures_ubahn]}"
            )

        return next_departures_tram + next_departures_ubahn
    except Exception:
        logger.exception("Error updating departures display")
        return []
