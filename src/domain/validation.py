from __future__ import annotations

from typing import Any

from src.domain.timestamp import parse_and_normalize_timestamp
from src.domain.types import Mode, NormalizedReading, RecordValidationResult, TopLevelValidationResult, ValidationError

REQUIRED_FIELDS = (
    "serial_number",
    "timestamp",
    "mode",
    "temperature",
    "humidity",
    "pressure",
    "location",
    "air_quality",
)


def validate_top_level_payload(payload: Any) -> TopLevelValidationResult:
    """Validate that the payload is either an object or array of records.

    Args:
        payload: The incoming request payload (dict or list).

    Returns:
        TopLevelValidationResult: Validation result with records or error.
    """
    if isinstance(payload, dict):
        return TopLevelValidationResult.success([payload])

    if isinstance(payload, list):
        return TopLevelValidationResult.success(payload)

    return TopLevelValidationResult.failure(
        ValidationError(
            field="payload",
            reason="payload must be an object or array",
            code="INVALID_PAYLOAD",
        )
    )


def normalize_payload_to_records(payload: Any) -> list[Any]:
    """Normalize payload to a list of record objects.

    Args:
        payload: The incoming request payload.

    Returns:
        list: List of record dictionaries.

    Raises:
        ValueError: If payload is not a valid object or array.
    """
    result = validate_top_level_payload(payload)
    if not result.is_valid:
        raise ValueError(result.errors[0].reason)
    return result.records


def validate_reading(record: Any) -> RecordValidationResult:
    """Validate a single sensor reading record.

    Validates all required fields, data types, and value ranges.

    Args:
        record: A dictionary containing sensor reading data.

    Returns:
        RecordValidationResult: Contains accepted reading or validation error.
    """
    if not isinstance(record, dict):
        return RecordValidationResult.failure(
            ValidationError(
                field="record",
                reason="record must be an object",
                code="VAL_RECORD_TYPE",
            )
        )

    for field_name in REQUIRED_FIELDS:
        if field_name not in record:
            return RecordValidationResult.failure(
                ValidationError(
                    field=field_name,
                    reason="required field is missing",
                    code=f"VAL_{field_name.upper()}_REQUIRED",
                )
            )

    serial_number = record["serial_number"]
    if not isinstance(serial_number, str) or not serial_number.strip():
        return RecordValidationResult.failure(
            ValidationError(
                field="serial_number",
                reason="serial_number must be a non-empty string",
                code="VAL_SERIAL_EMPTY",
            )
        )

    raw_mode = record["mode"]
    try:
        mode = Mode(raw_mode)
    except ValueError:
        return RecordValidationResult.failure(
            ValidationError(
                field="mode",
                reason="Unsupported mode value",
                code="VAL_MODE_INVALID",
            )
        )

    location = record["location"]
    if not isinstance(location, dict):
        return RecordValidationResult.failure(
            ValidationError(
                field="location",
                reason="location must be an object",
                code="VAL_LOCATION_TYPE",
            )
        )

    lat_error = _validate_numeric_field(location, "lat", min_value=-90, max_value=90)
    if lat_error is not None:
        return RecordValidationResult.failure(lat_error)

    lng_error = _validate_numeric_field(location, "lng", min_value=-180, max_value=180)
    if lng_error is not None:
        return RecordValidationResult.failure(lng_error)

    for field_name in ("temperature", "humidity", "pressure"):
        if not _is_number(record[field_name]):
            return RecordValidationResult.failure(
                ValidationError(
                    field=field_name,
                    reason=f"{field_name} must be numeric",
                    code=f"VAL_{field_name.upper()}_TYPE",
                )
            )

    air_quality = record["air_quality"]
    if not _is_integer(air_quality):
        return RecordValidationResult.failure(
            ValidationError(
                field="air_quality",
                reason="air_quality must be an integer",
                code="VAL_AIR_QUALITY_TYPE",
            )
        )

    raw_timestamp = record["timestamp"]
    try:
        sensor_timestamp = parse_and_normalize_timestamp(raw_timestamp)
    except ValueError:
        return RecordValidationResult.failure(
            ValidationError(
                field="timestamp",
                reason="Invalid ISO8601 timestamp",
                code="VAL_TIMESTAMP_INVALID",
            )
        )

    return RecordValidationResult.success(
        NormalizedReading(
            serial_number=serial_number.strip(),
            raw_timestamp=raw_timestamp,
            sensor_timestamp=sensor_timestamp,
            mode=mode,
            temperature=record["temperature"],
            humidity=record["humidity"],
            pressure=record["pressure"],
            latitude=location["lat"],
            longitude=location["lng"],
            air_quality=air_quality,
            original_record=record,
        )
    )


def _validate_numeric_field(
    payload: dict[str, Any],
    field_name: str,
    *,
    min_value: float,
    max_value: float,
) -> ValidationError | None:
    qualified_name = f"location.{field_name}"
    if field_name not in payload:
        return ValidationError(
            field=qualified_name,
            reason="required field is missing",
            code=f"VAL_{field_name.upper()}_REQUIRED",
        )

    value = payload[field_name]
    if not _is_number(value):
        return ValidationError(
            field=qualified_name,
            reason=f"{qualified_name} must be numeric",
            code=f"VAL_{field_name.upper()}_TYPE",
        )

    if value < min_value or value > max_value:
        return ValidationError(
            field=qualified_name,
            reason=f"{qualified_name} is out of range",
            code=f"VAL_{field_name.upper()}_RANGE",
        )

    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
