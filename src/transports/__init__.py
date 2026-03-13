"""Transport layer for sensor communication adapters.

This module provides transport abstractions that allow the same business logic
(Services) to be used by different protocols (HTTP, MQTT, etc.).
"""

from src.transports.http_transport import HttpSensorTransport
from src.transports.sensor_transport import SensorTransport

__all__ = ["SensorTransport", "HttpSensorTransport"]
