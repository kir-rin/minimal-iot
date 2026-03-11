from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.domain.status import evaluate_health_status, evaluate_telemetry_status
from src.domain.types import HealthStatus, Mode, TelemetryStatus


def test_normal_mode_is_healthy_at_12_minute_boundary() -> None:
    now = datetime(2024, 5, 23, 8, 42, tzinfo=timezone.utc)
    last_received_at = now - timedelta(minutes=12)

    result = evaluate_health_status(Mode.NORMAL, last_received_at, now)

    assert result == HealthStatus.HEALTHY


def test_normal_mode_becomes_faulty_after_12_minutes() -> None:
    now = datetime(2024, 5, 23, 8, 42, 1, tzinfo=timezone.utc)
    last_received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_health_status(Mode.NORMAL, last_received_at, now)

    assert result == HealthStatus.FAULTY


def test_emergency_mode_is_healthy_at_30_second_boundary() -> None:
    now = datetime(2024, 5, 23, 8, 30, 30, tzinfo=timezone.utc)
    last_received_at = now - timedelta(seconds=30)

    result = evaluate_health_status(Mode.EMERGENCY, last_received_at, now)

    assert result == HealthStatus.HEALTHY


def test_emergency_mode_becomes_faulty_after_30_seconds() -> None:
    now = datetime(2024, 5, 23, 8, 30, 31, tzinfo=timezone.utc)
    last_received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_health_status(Mode.EMERGENCY, last_received_at, now)

    assert result == HealthStatus.FAULTY


def test_unknown_health_status_when_mode_is_not_supported() -> None:
    now = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_health_status("INVALID", now, now)

    assert result == HealthStatus.UNKNOWN


def test_telemetry_status_is_fresh_for_recent_in_order_record() -> None:
    sensor_timestamp = datetime(2024, 5, 23, 8, 29, 30, tzinfo=timezone.utc)
    received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_telemetry_status(sensor_timestamp, received_at)

    assert result == TelemetryStatus.FRESH


def test_telemetry_status_is_delayed_when_older_than_two_minutes() -> None:
    sensor_timestamp = datetime(2024, 5, 23, 8, 27, 59, tzinfo=timezone.utc)
    received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_telemetry_status(sensor_timestamp, received_at)

    assert result == TelemetryStatus.DELAYED


def test_telemetry_status_is_fresh_at_exact_clock_skew_boundary() -> None:
    """Test that exactly 30 seconds ahead is still FRESH (not CLOCK_SKEW)."""
    sensor_timestamp = datetime(2024, 5, 23, 8, 30, 30, tzinfo=timezone.utc)
    received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_telemetry_status(sensor_timestamp, received_at)

    assert result == TelemetryStatus.FRESH


def test_telemetry_status_is_clock_skew_when_sensor_time_is_more_than_30_seconds_ahead() -> None:
    """Test that more than 30 seconds ahead triggers CLOCK_SKEW."""
    sensor_timestamp = datetime(2024, 5, 23, 8, 30, 31, tzinfo=timezone.utc)
    received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_telemetry_status(sensor_timestamp, received_at)

    assert result == TelemetryStatus.CLOCK_SKEW


def test_telemetry_status_is_fresh_at_exact_delayed_boundary() -> None:
    """Test that exactly 2 minutes difference is still FRESH (not DELAYED)."""
    sensor_timestamp = datetime(2024, 5, 23, 8, 28, tzinfo=timezone.utc)
    received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_telemetry_status(sensor_timestamp, received_at)

    assert result == TelemetryStatus.FRESH


def test_telemetry_status_is_delayed_when_exactly_two_minutes_old() -> None:
    """Test that exactly 2 minutes difference triggers DELAYED."""
    sensor_timestamp = datetime(2024, 5, 23, 8, 27, 59, tzinfo=timezone.utc)
    received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_telemetry_status(sensor_timestamp, received_at)

    assert result == TelemetryStatus.DELAYED


def test_telemetry_status_is_fresh_when_less_than_two_minutes_old() -> None:
    """Test that less than 2 minutes difference is FRESH."""
    sensor_timestamp = datetime(2024, 5, 23, 8, 28, 1, tzinfo=timezone.utc)
    received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)

    result = evaluate_telemetry_status(sensor_timestamp, received_at)

    assert result == TelemetryStatus.FRESH


def test_telemetry_status_is_out_of_order_when_older_than_last_sensor_timestamp() -> None:
    sensor_timestamp = datetime(2024, 5, 23, 8, 29, tzinfo=timezone.utc)
    received_at = datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)
    last_sensor_timestamp = datetime(2024, 5, 23, 8, 29, 30, tzinfo=timezone.utc)

    result = evaluate_telemetry_status(sensor_timestamp, received_at, last_sensor_timestamp)

    assert result == TelemetryStatus.OUT_OF_ORDER
