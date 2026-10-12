"""Application configuration using Pydantic Settings."""
import re
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MQTT Broker Configuration
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883

    # Awtrix Display Configuration
    awtrix_topic_prefix: str = "awtrix"
    awtrix_raw_message_subtopic: str = "custom/mvg"

    # MVG Stop Configuration (two stops, left and right on the display)
    # Colors are hex RGB values (RRGGBB) for the badge background and text
    # Lines optionally restrict departures to the given line labels,
    # comma-separated (e.g. "54,N27"); empty shows all lines
    # Destinations optionally restrict departures to those whose destination
    # contains any of the given names, comma-separated; empty shows all
    stop_1_id: str = "de:09162:1602:2:1"
    stop_1_lines: Annotated[list[str], NoDecode] = []
    stop_1_destinations: Annotated[list[str], NoDecode] = []
    stop_1_bg_color: str = "FF0000"
    stop_1_fg_color: str = "FFFFFF"
    stop_2_id: str = "de:09162:280:51:52"
    stop_2_lines: Annotated[list[str], NoDecode] = []
    stop_2_destinations: Annotated[list[str], NoDecode] = []
    stop_2_bg_color: str = "915900"
    stop_2_fg_color: str = "FFFFFF"

    # Update Interval
    update_interval_seconds: int = 10

    @field_validator(
        "stop_1_bg_color", "stop_1_fg_color", "stop_2_bg_color", "stop_2_fg_color"
    )
    @classmethod
    def validate_color(cls, value: str) -> str:
        color = value.strip().lstrip("#").upper()
        if not re.fullmatch(r"[0-9A-F]{6}", color):
            raise ValueError(f"Invalid hex RGB color: {value!r}")
        return color

    @field_validator(
        "stop_1_lines",
        "stop_1_destinations",
        "stop_2_lines",
        "stop_2_destinations",
        mode="before",
    )
    @classmethod
    def split_list(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            value = value.split(",")
        return [line.strip().upper() for line in value if line.strip()]

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


settings = Settings()
