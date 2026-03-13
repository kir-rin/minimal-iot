"""Sensor transport abstraction for protocol-independent operations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class IngestResult:
    """Protocol-independent ingestion result."""
    success: bool
    ingest_mode: str
    accepted_count: int
    rejected_count: int
    errors: list[dict]  # {"index": int, "field": str, "reason": str}
    is_request_level_error: bool = False


@dataclass
class ModeChangeResult:
    """Protocol-independent mode change result."""
    success: bool
    sensor_known: bool
    requested_mode: str
    requested_at: datetime
    message: str


@dataclass
class SensorStatusResult:
    """Protocol-independent sensor status result."""
    sensors: list[dict]  # List of sensor status dictionaries
    total_count: int


class SensorTransport(ABC):
    """Abstract base class for sensor communication transport.
    
    This interface abstracts the communication protocol (HTTP, MQTT, etc.)
    from the business logic. Implementations handle protocol-specific details
    while providing a uniform interface to the application layer.
    
    Future MQTT Implementation Notes:
    - MqttTransport will implement the same interface
    - MQTT handlers will call these methods instead of HTTP routers
    - Results are protocol-independent dataclasses (no HTTP-specific codes)
    """

    @abstractmethod
    async def ingest_data(
        self,
        payload: Any,
        ingest_mode: str,
    ) -> IngestResult:
        """Ingest sensor data.
        
        Args:
            payload: Raw data payload (single reading or list)
            ingest_mode: "ATOMIC" or "PARTIAL"
            
        Returns:
            IngestResult with protocol-independent result data
            
        Note:
            HTTP Router: Converts to JSONResponse with appropriate status code
            MQTT Handler: Converts to MQTT message on result topic
        """
        pass

    @abstractmethod
    async def request_mode_change(
        self,
        serial_number: str,
        mode: str,
    ) -> ModeChangeResult:
        """Request mode change for a sensor.
        
        Args:
            serial_number: Sensor serial number
            mode: Target mode ("NORMAL" or "EMERGENCY")
            
        Returns:
            ModeChangeResult with protocol-independent result data
            
        Note:
            HTTP Router: Returns JSON with 200/422 status
            MQTT Handler: Publishes result to sensors/{sn}/mode/status
        """
        pass

    @abstractmethod
    async def get_sensor_status(
        self,
        serial_number: str | None = None,
        health_status: str | None = None,
    ) -> SensorStatusResult:
        """Get sensor status information.
        
        Args:
            serial_number: Filter by specific sensor (None for all)
            health_status: Filter by health status (None for all)
            
        Returns:
            SensorStatusResult with protocol-independent status data
            
        Note:
            HTTP Router: Returns JSON list
            MQTT Handler: Publishes to sensors/{sn}/status (retain=True)
        """
        pass
