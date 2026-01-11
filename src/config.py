"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings


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
        "env_file": ".env",
        "case_sensitive": False,
    }


settings = Settings()
