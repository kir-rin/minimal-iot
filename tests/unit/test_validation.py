from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.types import Mode
from src.domain.validation import normalize_payload_to_records, validate_reading, validate_top_level_payload


def build_valid_record() -> dict:
    return {
        "serial_number": "SENSOR-001",
        "timestamp": "2024-05-23T08:30:00Z",
        "mode": "NORMAL",
        "temperature": 21.5,
        "humidity": 45.2,
        "pressure": 1013.1,
        "location": {"lat": 37.5665, "lng": 126.9780},
        "air_quality": 42,
    }


def test_validate_top_level_payload_accepts_object() -> None:
    payload = build_valid_record()

    result = validate_top_level_payload(payload)

    assert result.is_valid is True
    assert result.records == [payload]


def test_validate_top_level_payload_accepts_array() -> None:
    payload = [build_valid_record()]

    result = validate_top_level_payload(payload)

    assert result.is_valid is True
    assert result.records == payload


def test_validate_top_level_payload_rejects_invalid_type() -> None:
    result = validate_top_level_payload("invalid")

    assert result.is_valid is False
    assert result.errors[0].field == "payload"


def test_normalize_payload_to_records_preserves_empty_array() -> None:
    assert normalize_payload_to_records([]) == []


def test_validate_top_level_payload_accepts_empty_array() -> None:
    """Test that empty array is a valid payload (no-op success)."""
    result = validate_top_level_payload([])

    assert result.is_valid is True
    assert result.records == []
    assert result.errors == []


def test_validate_reading_accepts_valid_record() -> None:
    result = validate_reading(build_valid_record())

    assert result.accepted is True
    assert result.reading is not None
    assert result.reading.serial_number == "SENSOR-001"
    assert result.reading.mode == Mode.NORMAL
    assert result.reading.sensor_timestamp == datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("field_name", "expected_field"),
    [
        ("serial_number", "serial_number"),
        ("timestamp", "timestamp"),
        ("mode", "mode"),
        ("temperature", "temperature"),
        ("humidity", "humidity"),
        ("pressure", "pressure"),
        ("location", "location"),
        ("air_quality", "air_quality"),
    ],
)
def test_validate_reading_rejects_missing_required_field(field_name: str, expected_field: str) -> None:
    payload = build_valid_record()
    payload.pop(field_name)

    result = validate_reading(payload)

    assert result.accepted is False
    assert result.error is not None
    assert result.error.field == expected_field


def test_validate_reading_rejects_invalid_mode() -> None:
    payload = build_valid_record()
    payload["mode"] = "INVALID"

    result = validate_reading(payload)

    assert result.accepted is False
    assert result.error is not None
    assert result.error.field == "mode"


def test_validate_reading_rejects_invalid_timestamp() -> None:
    payload = build_valid_record()
    payload["timestamp"] = "2024-05-23 08:30:00"

    result = validate_reading(payload)

    assert result.accepted is False
    assert result.error is not None
    assert result.error.field == "timestamp"


def test_validate_reading_rejects_invalid_location_structure() -> None:
    payload = build_valid_record()
    payload["location"] = "seoul"

    result = validate_reading(payload)

    assert result.accepted is False
    assert result.error is not None
    assert result.error.field == "location"


@pytest.mark.parametrize(
    ("lat", "lng", "expected_field"),
    [
        (91, 126.9780, "location.lat"),
        (-91, 126.9780, "location.lat"),
        (37.5665, 181, "location.lng"),
        (37.5665, -181, "location.lng"),
    ],
)
def test_validate_reading_rejects_out_of_range_coordinates(lat: float, lng: float, expected_field: str) -> None:
    payload = build_valid_record()
    payload["location"] = {"lat": lat, "lng": lng}

    result = validate_reading(payload)

    assert result.accepted is False
    assert result.error is not None
    assert result.error.field == expected_field


@pytest.mark.parametrize(
    ("lat", "lng"),
    [
        (90, 126.9780),    # Max valid latitude
        (-90, 126.9780),   # Min valid latitude
        (37.5665, 180),    # Max valid longitude
        (37.5665, -180),   # Min valid longitude
    ],
)
def test_validate_reading_accepts_boundary_coordinates(lat: float, lng: float) -> None:
    """Test that exact boundary values (-90, 90, -180, 180) are accepted."""
    payload = build_valid_record()
    payload["location"] = {"lat": lat, "lng": lng}

    result = validate_reading(payload)

    assert result.accepted is True
    assert result.reading is not None
    assert result.reading.latitude == lat
    assert result.reading.longitude == lng


def test_validate_reading_rejects_non_numeric_coordinates() -> None:
    payload = build_valid_record()
    payload["location"] = {"lat": "north", "lng": 126.9780}

    result = validate_reading(payload)

    assert result.accepted is False
    assert result.error is not None
    assert result.error.field == "location.lat"


def test_validate_reading_rejects_non_integer_air_quality() -> None:
    payload = build_valid_record()
    payload["air_quality"] = 42.5

    result = validate_reading(payload)

    assert result.accepted is False
    assert result.error is not None
    assert result.error.field == "air_quality"


def test_validate_reading_rejects_non_object_record() -> None:
    result = validate_reading("invalid")

    assert result.accepted is False
    assert result.error is not None
    assert result.error.field == "record"
