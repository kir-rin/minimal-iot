"""HTTP Transport implementation for sensor communication."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.clock import Clock
from src.domain.types import IngestMode, Mode
from src.services.ingestion_service import IngestionService
from src.services.mode_service import ModeService
from src.services.query_service import QueryService
from src.transports.sensor_transport import (
    IngestResult,
    ModeChangeResult,
    SensorStatusResult,
    SensorTransport,
)


class HttpSensorTransport(SensorTransport):
    """HTTP implementation of SensorTransport.
    
    This transport wraps Service layer calls and returns protocol-independent
    result objects. HTTP-specific transformations (status codes, JSON responses)
    are handled by the HTTP Router.
    
    Future MQTT Note:
    MqttTransport will implement the same interface but use MQTT client
    for publishing/subscribing instead of HTTP request/response.
    """

    def __init__(
        self,
        session: AsyncSession,
        clock: Clock,
        ingestion_service: IngestionService | None = None,
        mode_service: ModeService | None = None,
        query_service: QueryService | None = None,
    ):
        self._session = session
        self._clock = clock
        self._ingestion_service = ingestion_service or IngestionService(session, clock)
        self._mode_service = mode_service or ModeService(session, clock)
        self._query_service = query_service or QueryService(session)

    async def ingest_data(
        self,
        payload: Any,
        ingest_mode: str,
    ) -> IngestResult:
        """Ingest sensor data via Service layer.
        
        Returns protocol-independent result. HTTP Router converts this to
        appropriate HTTP status codes and JSON response.
        
        Args:
            payload: Raw data (single reading dict or list)
            ingest_mode: "ATOMIC" or "PARTIAL"
            
        Returns:
            IngestResult with success status, counts, and errors
        """
        mode = IngestMode(ingest_mode)
        batch_result = await self._ingestion_service.ingest(payload, mode)

        # Convert domain errors to transport-agnostic format
        errors = []
        for error in batch_result.errors:
            errors.append({
                "index": error.index if error.index is not None else 0,
                "field": error.field,
                "reason": error.reason,
            })

        return IngestResult(
            success=batch_result.success,
            ingest_mode=batch_result.ingest_mode.value,
            accepted_count=batch_result.accepted_count,
            rejected_count=batch_result.rejected_count,
            errors=errors,
            is_request_level_error=batch_result.is_request_level_error,
        )

    async def request_mode_change(
        self,
        serial_number: str,
        mode: str,
    ) -> ModeChangeResult:
        """Request mode change via Service layer.
        
        Args:
            serial_number: Sensor serial number
            mode: Target mode ("NORMAL" or "EMERGENCY")
            
        Returns:
            ModeChangeResult with request status
            
        Raises:
            ValueError: If mode is invalid (caught by Router for HTTP 422)
        """
        # Validate and convert mode
        try:
            mode_enum = Mode(mode)
        except ValueError as e:
            valid_modes = [m.value for m in Mode]
            raise ValueError(f"Invalid mode: {mode}. Valid modes: {valid_modes}") from e

        result = await self._mode_service.request_mode_change(serial_number, mode_enum)

        return ModeChangeResult(
            success=result.success,
            sensor_known=result.sensor_known,
            requested_mode=result.requested_mode,
            requested_at=result.requested_at,
            message=result.message,
        )

    async def get_sensor_status(
        self,
        serial_number: str | None = None,
        health_status: str | None = None,
    ) -> SensorStatusResult:
        """Get sensor status via Service layer.
        
        Args:
            serial_number: Filter by specific sensor (None for all)
            health_status: Filter by health status (None for all)
            
        Returns:
            SensorStatusResult with list of sensor statuses
        """
        result = await self._query_service.query_sensor_status(
            serial_number=serial_number,
            health_status=health_status,
        )

        # Convert to transport-agnostic format
        # result is SensorStatusResponse with 'data' attribute
        sensors = []
        for status in result.data:
            sensors.append({
                "serial_number": status.serial_number,
                "health_status": status.health_status,
                "telemetry_status": status.telemetry_status,
                "current_mode": status.last_reported_mode,
                "last_sensor_timestamp": status.last_sensor_timestamp,
                "last_server_received_at": status.last_server_received_at,
                "latest_reading_id": status.last_reading_id,
            })

        return SensorStatusResult(
            sensors=sensors,
            total_count=len(sensors),
        )
