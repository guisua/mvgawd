"""Utilities for fetching departures and updating the Awtrix display."""
from loguru import logger
from src.config import settings
from src.mvg_api.v2.api import AsyncApi
from src.awtrix import AwtrixDisplay
from src.mqtt_client import MQTTClient


def station_id_from_stop_id(stop_id: str) -> str:
    """
    Derive the station id from a stop point id.

    Stop point ids are prefixed by their station id, e.g. stop
    de:09162:1602:2:1 belongs to station de:09162:1602.
    """
    return ":".join(stop_id.split(":")[:3])


async def get_next_departures(
    api: AsyncApi,
    stop_id: str,
    lines: list[str],
    destinations: list[str],
    count: int = 2,
) -> list:
    """
    Fetch the next departures for a stop point.

    Args:
        api: MVG API instance
        stop_id: Global stop point id
        lines: Line labels to keep, all lines if empty
        destinations: Destination names to keep (partial match), all if empty
        count: Number of departures to return

    Returns:
        List of the next departures, soonest first
    """
    station_id = station_id_from_stop_id(stop_id)
    logger.debug(f"Fetching departures for stop {stop_id} (station {station_id})")
    departures = await api.get_departures(station_id)

    # Extract departures for the configured stop point, lines and destinations
    departures = [
        departure
        for departure in departures
        if departure.stopPointGlobalId == stop_id
        and (not lines or departure.label.upper() in lines)
        and (
            not destinations
            or any(
                destination in departure.destination.upper()
                for destination in destinations
            )
        )
    ]

    # Next departures, in ceil minutes from now
    return sorted(departures, key=lambda x: x.minutes_until_departure)[:count]


def draw_stop(
    x: int, text_x: int, departures: list, bg_color: str, fg_color: str
) -> list:
    """Build the Awtrix draw commands for one stop, starting at column x."""
    return [
        {"df": [x, 2, 16, 5, bg_color]},
        {"df": [x + 1, 1, 14, 7, bg_color]},
        {
            "dt": [
                text_x,
                2,
                "'".join(
                    [str(departure.minutes_until_departure) for departure in departures]
                ),
                fg_color,
            ]
        },
    ]


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
        List of next departures (stop 1 + stop 2)
    """
    try:
        next_departures_1 = await get_next_departures(
            api,
            settings.stop_1_id,
            settings.stop_1_lines,
            settings.stop_1_destinations,
        )
        next_departures_2 = await get_next_departures(
            api,
            settings.stop_2_id,
            settings.stop_2_lines,
            settings.stop_2_destinations,
        )

        # Send raw draw message to Awtrix display if connected
        if awtrix_display and mqtt_client and mqtt_client.is_connected:
            draw_payload = {
                "draw": draw_stop(
                    0,
                    1,
                    next_departures_1,
                    settings.stop_1_bg_color,
                    settings.stop_1_fg_color,
                )
                + draw_stop(
                    16,
                    18,
                    next_departures_2,
                    settings.stop_2_bg_color,
                    settings.stop_2_fg_color,
                )
            }
            awtrix_display.send_raw_message(
                settings.awtrix_raw_message_subtopic, draw_payload
            )
            logger.debug(
                f"Sent departures to Awtrix: stop 1 {[d.minutes_until_departure for d in next_departures_1]}, "
                f"stop 2 {[d.minutes_until_departure for d in next_departures_2]}"
            )

        return next_departures_1 + next_departures_2
    except Exception:
        logger.exception("Error updating departures display")
        return []
