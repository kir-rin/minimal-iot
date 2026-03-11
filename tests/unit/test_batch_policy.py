from __future__ import annotations

from src.domain.batch_policy import build_noop_batch_decision, resolve_ingest_mode, summarize_atomic_result, summarize_partial_result
from src.domain.types import IngestMode
from src.domain.validation import validate_reading


def build_valid_record(serial_number: str) -> dict:
    return {
        "serial_number": serial_number,
        "timestamp": "2024-05-23T08:30:00Z",
        "mode": "NORMAL",
        "temperature": 21.5,
        "humidity": 45.2,
        "pressure": 1013.1,
        "location": {"lat": 37.5665, "lng": 126.9780},
        "air_quality": 42,
    }


def test_resolve_ingest_mode_defaults_to_atomic() -> None:
    ingest_mode, error = resolve_ingest_mode(None)

    assert ingest_mode == IngestMode.ATOMIC
    assert error is None


def test_resolve_ingest_mode_rejects_invalid_value() -> None:
    ingest_mode, error = resolve_ingest_mode("invalid")

    assert ingest_mode is None
    assert error is not None
    assert error.field == "ingest_mode"


def test_atomic_succeeds_when_all_records_are_valid() -> None:
    results = [
        validate_reading(build_valid_record("SENSOR-001")),
        validate_reading(build_valid_record("SENSOR-002")),
    ]

    decision = summarize_atomic_result(results)

    assert decision.success is True
    assert decision.accepted_count == 2
    assert decision.rejected_count == 0


def test_atomic_rejects_entire_batch_when_any_record_fails() -> None:
    invalid_record = build_valid_record("SENSOR-002")
    invalid_record["timestamp"] = "invalid"
    results = [
        validate_reading(build_valid_record("SENSOR-001")),
        validate_reading(invalid_record),
    ]

    decision = summarize_atomic_result(results)

    assert decision.success is False
    assert decision.accepted_count == 0
    assert decision.rejected_count == 2
    assert len(decision.errors) == 1


def test_partial_accepts_valid_records_and_returns_errors() -> None:
    invalid_record = build_valid_record("SENSOR-002")
    invalid_record["mode"] = "INVALID"
    results = [
        validate_reading(build_valid_record("SENSOR-001")),
        validate_reading(invalid_record),
    ]

    decision = summarize_partial_result(results)

    assert decision.success is True
    assert decision.accepted_count == 1
    assert decision.rejected_count == 1
    assert len(decision.errors) == 1


def test_partial_is_unsuccessful_when_all_records_fail() -> None:
    invalid_record = build_valid_record("SENSOR-001")
    invalid_record["mode"] = "INVALID"
    results = [validate_reading(invalid_record)]

    decision = summarize_partial_result(results)

    assert decision.success is False
    assert decision.accepted_count == 0
    assert decision.rejected_count == 1


def test_noop_batch_returns_success_for_empty_array() -> None:
    atomic_decision = build_noop_batch_decision(IngestMode.ATOMIC)
    partial_decision = build_noop_batch_decision(IngestMode.PARTIAL)

    assert atomic_decision.success is True
    assert atomic_decision.accepted_count == 0
    assert atomic_decision.rejected_count == 0
    assert partial_decision.success is True
    assert partial_decision.accepted_count == 0
    assert partial_decision.rejected_count == 0
