import asyncio
from contextlib import asynccontextmanager
from pydantic_settings import BaseSettings
from fastapi import FastAPI
from src.mvg_api.v2.api import AsyncApi
from src.mqtt_client import MQTTClient
from src.awtrix import AwtrixDisplay


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MQTT Broker Configuration
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883

    # Awtrix Display Configuration
    awtrix_topic_prefix: str = "awtrix"
    awtrix_raw_message_subtopic: str = "custom/mvg"

    # MVG Station Configuration
    station_id_tram: str = "de:09162:1602"
    station_id_ubahn: str = "de:09162:280"
    stop_point_id_tram: str = "de:09162:1602:2:1"
    stop_point_id_ubahn: str = "de:09162:280:51:52"

    # Update Interval
    update_interval_seconds: int = 10

    model_config = {
        "case_sensitive": False,
    }


settings = Settings()

api = AsyncApi()
mqtt_client: MQTTClient | None = None
awtrix_display: AwtrixDisplay | None = None
background_task: asyncio.Task | None = None


async def update_departures_display():
    """Fetch departures and send to Awtrix display. Returns the next departures."""
    try:
        departures_tram = await api.get_departures(
            settings.station_id_tram, transport_types="TRAM"
        )
        departures_ubahn = await api.get_departures(
            settings.station_id_ubahn, transport_types="UBAHN"
        )

        # extract departures for the configured stop point
        departures_tram = [
            departure
            for departure in departures_tram
            if departure.stopPointGlobalId == settings.stop_point_id_tram
        ]

        # next two departures, in ceil minutes from now
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

        return next_departures_tram + next_departures_ubahn
    except Exception as e:
        print(f"Error updating departures display: {e}")
        return []


async def periodic_update_task():
    """Background task that updates departures periodically."""
    while True:
        try:
            await update_departures_display()
            await asyncio.sleep(settings.update_interval_seconds)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in periodic update task: {e}")
            await asyncio.sleep(settings.update_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and connect MQTT client
    global mqtt_client, awtrix_display, background_task
    mqtt_client = MQTTClient(
        host=settings.mqtt_broker_host,
        port=settings.mqtt_broker_port,
    )
    mqtt_client.connect()

    # Initialize Awtrix display controller
    awtrix_display = AwtrixDisplay(
        mqtt_client, topic_prefix=settings.awtrix_topic_prefix
    )

    # Start background task for periodic updates
    background_task = asyncio.create_task(periodic_update_task())

    yield
    # Shutdown: Cancel background task and disconnect MQTT client
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
    if mqtt_client:
        mqtt_client.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/departures")
async def get_departures():
    """Get departures for station with globalId=de:09162:1602"""
    departures = await update_departures_display()
    return departures


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
