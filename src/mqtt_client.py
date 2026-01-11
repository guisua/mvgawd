from typing import Optional, Callable, Any
import paho.mqtt.client as mqtt
from loguru import logger


class MQTTClient:
    """
    A simple abstraction over paho-mqtt client for connecting to MQTT brokers
    and publishing messages to topics.
    """

    def __init__(
        self,
        host: str,
        port: int = 1883,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        keepalive: int = 60,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
        on_publish: Optional[Callable] = None,
    ):
        """
        Initialize MQTT client.

        :param host: MQTT broker hostname or IP address
        :param port: MQTT broker port (default: 1883)
        :param client_id: Optional client ID. If None, paho-mqtt will generate one
        :param username: Optional username for authentication
        :param password: Optional password for authentication
        :param keepalive: Keepalive interval in seconds (default: 60)
        :param on_connect: Optional callback function called when connected
        :param on_disconnect: Optional callback function called when disconnected
        :param on_publish: Optional callback function called when message is published
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.keepalive = keepalive
        self._client: Optional[mqtt.Client] = None
        self._connected = False

        # Set up callbacks
        self._on_connect_callback = on_connect
        self._on_disconnect_callback = on_disconnect
        self._on_publish_callback = on_publish

    def _on_connect(
        self, client: mqtt.Client, userdata: Any, flags: dict, rc: int
    ) -> None:
        """Internal callback for when the client connects."""
        if rc == 0:
            self._connected = True
            logger.info(f"Connected to MQTT broker at {self.host}:{self.port}")
        else:
            self._connected = False
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")

        if self._on_connect_callback:
            self._on_connect_callback(client, userdata, flags, rc)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Internal callback for when the client disconnects."""
        self._connected = False
        if rc == 0:
            logger.info("Disconnected from MQTT broker")
        else:
            logger.warning(
                f"Unexpected disconnection from MQTT broker. Return code: {rc}"
            )

        if self._on_disconnect_callback:
            self._on_disconnect_callback(client, userdata, rc)

    def _on_publish(self, client: mqtt.Client, userdata: Any, mid: int) -> None:
        """Internal callback for when a message is published."""
        if self._on_publish_callback:
            self._on_publish_callback(client, userdata, mid)

    def connect(self) -> None:
        """Connect to the MQTT broker."""
        if self._client is not None and self._connected:
            logger.warning("Already connected to MQTT broker")
            return

        self._client = mqtt.Client(
            client_id=self.client_id,
            protocol=mqtt.MQTTv311,
        )

        # Set callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish = self._on_publish

        # Set authentication if provided
        if self.username and self.password:
            self._client.username_pw_set(self.username, self.password)

        try:
            self._client.connect(self.host, self.port, self.keepalive)
            self._client.loop_start()
            logger.info(f"Connecting to MQTT broker at {self.host}:{self.port}...")
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client is None:
            logger.warning("No active MQTT client to disconnect")
            return

        if not self._connected:
            logger.warning("Not connected to MQTT broker")
            return

        try:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            logger.info("Disconnected from MQTT broker")
        except Exception as e:
            logger.error(f"Error disconnecting from MQTT broker: {e}")
            raise

    def publish(
        self,
        topic: str,
        payload: str | bytes,
        qos: int = 0,
        retain: bool = False,
    ) -> Optional[mqtt.MQTTMessageInfo]:
        """
        Publish a message to a topic.

        :param topic: The topic to publish to
        :param payload: The message payload (string or bytes)
        :param qos: Quality of Service level (0, 1, or 2). Default: 0
        :param retain: Whether to retain the message. Default: False
        :return: MQTTMessageInfo object if successful, None otherwise
        """
        if self._client is None or not self._connected:
            raise RuntimeError("Not connected to MQTT broker. Call connect() first.")

        try:
            if isinstance(payload, str):
                payload = payload.encode("utf-8")

            result = self._client.publish(topic, payload, qos=qos, retain=retain)
            logger.debug(f"Published message to topic '{topic}'")
            return result
        except Exception as e:
            logger.error(f"Error publishing message to topic '{topic}': {e}")
            raise

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected to the broker."""
        return self._connected

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
