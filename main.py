from contextlib import asynccontextmanager
from datetime import datetime
import math
from fastapi import FastAPI
from src.mvg_api.v2.api import AsyncApi
from src.mqtt_client import MQTTClient
from src.awtrix import AwtrixDisplay

api = AsyncApi()
mqtt_client: MQTTClient | None = None
awtrix_display: AwtrixDisplay | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and connect MQTT client
    global mqtt_client, awtrix_display
    mqtt_client = MQTTClient(
        host="192.168.178.110",  # TODO: Configure MQTT broker host
        port=1883,  # TODO: Configure MQTT broker port
    )
    mqtt_client.connect()

    # Initialize Awtrix display controller
    awtrix_display = AwtrixDisplay(mqtt_client, topic_prefix="awtrix_5442b8")

    yield
    # Shutdown: Disconnect MQTT client
    if mqtt_client:
        mqtt_client.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/departures")
async def get_departures():
    """Get departures for station with globalId=de:09162:1602"""
    departures_tram = await api.get_departures("de:09162:1602", transport_types="TRAM")
    departures_ubahn = await api.get_departures("de:09162:280", transport_types="UBAHN")

    # extract the first departure for line 19 and "stopPointGlobalId": "de:09162:1602:2:1"
    departures_tram = [
        departure
        for departure in departures_tram
        if departure.stopPointGlobalId == "de:09162:1602:2:1"
    ]

    # next two departures, in ceil minutes from now
    next_departures_tram = sorted(
        departures_tram, key=lambda x: x.minutes_until_departure
    )[:2]

    departures_ubahn = [
        departure
        for departure in departures_ubahn
        if departure.stopPointGlobalId == "de:09162:280:51:52"
    ]
    next_departures_ubahn = sorted(
        departures_ubahn, key=lambda x: x.minutes_until_departure
    )[:2]

    # Send raw draw message to Awtrix display
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
        awtrix_display.send_raw_message("custom/mvg", draw_payload)

    return next_departures_tram + next_departures_ubahn


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
