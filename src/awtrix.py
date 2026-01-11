import json
from typing import Optional, Dict, Any
from loguru import logger
from src.mqtt_client import MQTTClient


class AwtrixDisplay:
    """
    Utility class to control an Awtrix display via MQTT.

    Based on Awtrix3 MQTT API documentation:
    https://blueforcer.github.io/awtrix3/#/api?id=custom-apps-and-notifications
    """

    def __init__(
        self,
        mqtt_client: MQTTClient,
        topic_prefix: str = "awtrix",
    ):
        """
        Initialize Awtrix display controller.

        :param mqtt_client: An instance of MQTTClient to use for communication
        :param topic_prefix: MQTT topic prefix (default: "awtrix")
        """
        self.mqtt_client = mqtt_client
        self.topic_prefix = topic_prefix

    def send_custom_app(
        self,
        app_name: str,
        text: str,
        icon: Optional[str] = None,
        duration: int = 5,
        repeat: int = 1,
        push_icon: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Send a custom app to the Awtrix display.

        :param app_name: Name of the custom app
        :param text: Text to display
        :param icon: Icon ID or name (optional)
        :param duration: Duration in seconds (default: 5)
        :param repeat: Number of times to repeat (default: 1)
        :param push_icon: Whether to push the icon (default: True)
        :param kwargs: Additional parameters to include in the payload
        """
        topic = f"{self.topic_prefix}/custom/{app_name}"
        payload: Dict[str, Any] = {
            "text": text,
            "duration": duration,
            "repeat": repeat,
            "pushIcon": push_icon,
        }

        if icon is not None:
            payload["icon"] = icon

        # Add any additional parameters
        payload.update(kwargs)

        message = json.dumps(payload)
        self.mqtt_client.publish(topic, message)
        logger.info(f"Sent custom app '{app_name}' to Awtrix display")

    def send_notification(
        self,
        text: str,
        icon: Optional[str] = None,
        duration: int = 5,
        repeat: int = 1,
        push_icon: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Send a notification to the Awtrix display.

        :param text: Text to display in the notification
        :param icon: Icon ID or name (optional)
        :param duration: Duration in seconds (default: 5)
        :param repeat: Number of times to repeat (default: 1)
        :param push_icon: Whether to push the icon (default: True)
        :param kwargs: Additional parameters to include in the payload
        """
        topic = f"{self.topic_prefix}/notify"
        payload: Dict[str, Any] = {
            "text": text,
            "duration": duration,
            "repeat": repeat,
            "pushIcon": push_icon,
        }

        if icon is not None:
            payload["icon"] = icon

        # Add any additional parameters
        payload.update(kwargs)

        message = json.dumps(payload)
        self.mqtt_client.publish(topic, message)
        logger.info("Sent notification to Awtrix display")

    def send_raw_message(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        Send a raw MQTT message to the Awtrix display.

        :param topic: Full MQTT topic (will be prefixed with topic_prefix if not absolute)
        :param payload: Dictionary payload to send as JSON
        """
        if not topic.startswith(self.topic_prefix):
            topic = f"{self.topic_prefix}/{topic.lstrip('/')}"

        message = json.dumps(payload)
        self.mqtt_client.publish(topic, message)
        logger.debug(f"Sent raw message to topic '{topic}'")
