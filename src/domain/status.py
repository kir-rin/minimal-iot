from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.domain.types import HealthStatus, Mode, TelemetryStatus


@dataclass
class StatusThresholds:
    """Thresholds for health and telemetry status evaluation."""

    normal_health: timedelta = timedelta(minutes=12)
    emergency_health: timedelta = timedelta(seconds=30)
    delayed: timedelta = timedelta(minutes=2)
    clock_skew: timedelta = timedelta(seconds=30)

    @classmethod
    def from_settings(cls, threshold_settings) -> "StatusThresholds":
        """Create thresholds from application settings.
        
        Args:
            threshold_settings: ThresholdSettings from src.config.settings
        """
        return cls(
            normal_health=timedelta(seconds=threshold_settings.normal_health_threshold_seconds),
            emergency_health=timedelta(seconds=threshold_settings.emergency_health_threshold_seconds),
            delayed=timedelta(seconds=threshold_settings.delayed_threshold_seconds),
            clock_skew=timedelta(seconds=threshold_settings.clock_skew_threshold_seconds),
        )


def evaluate_health_status(
    last_mode: str | Mode | None,
    last_server_received_at: datetime | None,
    now: datetime,
    thresholds: StatusThresholds | None = None,
) -> HealthStatus:
    """Evaluate the health status of a sensor based on elapsed time.

    Args:
        last_mode: The last known mode of the sensor.
        last_server_received_at: When the server last received data from the sensor.
        now: Current time for evaluation.
        thresholds: Custom thresholds. Uses defaults if None.

    Returns:
        HealthStatus: HEALTHY, FAULTY, or UNKNOWN.
    """
    if last_server_received_at is None:
        return HealthStatus.UNKNOWN

    mode = _coerce_mode(last_mode)
    if mode is None:
        return HealthStatus.UNKNOWN

    threshold_config = thresholds or StatusThresholds()
    elapsed = _as_utc(now) - _as_utc(last_server_received_at)
    threshold = threshold_config.normal_health if mode == Mode.NORMAL else threshold_config.emergency_health

    if elapsed > threshold:
        return HealthStatus.FAULTY

    return HealthStatus.HEALTHY


def evaluate_telemetry_status(
    sensor_timestamp: datetime,
    server_received_at: datetime,
    last_sensor_timestamp: datetime | None = None,
    thresholds: StatusThresholds | None = None,
) -> TelemetryStatus:
    """Evaluate the telemetry status of a reading.

    Args:
        sensor_timestamp: The timestamp from the sensor.
        server_received_at: When the server received the reading.
        last_sensor_timestamp: The previous sensor timestamp for out-of-order detection.
        thresholds: Custom thresholds. Uses defaults if None.

    Returns:
        TelemetryStatus: FRESH, DELAYED, CLOCK_SKEW, or OUT_OF_ORDER.
    """
    threshold_config = thresholds or StatusThresholds()
    canonical_sensor_timestamp = _as_utc(sensor_timestamp)
    canonical_received_at = _as_utc(server_received_at)
    canonical_last_sensor = _as_utc(last_sensor_timestamp) if last_sensor_timestamp else None

    if (
        canonical_last_sensor is not None
        and canonical_sensor_timestamp < canonical_last_sensor
    ):
        return TelemetryStatus.OUT_OF_ORDER

    if canonical_sensor_timestamp > canonical_received_at + threshold_config.clock_skew:
        return TelemetryStatus.CLOCK_SKEW

    if canonical_received_at - canonical_sensor_timestamp > threshold_config.delayed:
        return TelemetryStatus.DELAYED

    return TelemetryStatus.FRESH


def _coerce_mode(last_mode: str | Mode | None) -> Mode | None:
    if isinstance(last_mode, Mode):
        return last_mode

    if isinstance(last_mode, str):
        try:
            return Mode(last_mode)
        except ValueError:
            return None

    return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc)
