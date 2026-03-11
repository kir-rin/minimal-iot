"""Domain utilities and business rules package."""

from src.domain.batch_policy import build_noop_batch_decision, resolve_ingest_mode, summarize_atomic_result, summarize_partial_result
from src.domain.status import evaluate_health_status, evaluate_telemetry_status
from src.domain.timestamp import parse_and_normalize_timestamp
from src.domain.types import BatchDecision, HealthStatus, IngestMode, Mode, NormalizedReading, RecordValidationResult, TelemetryStatus, TopLevelValidationResult, ValidationError
from src.domain.validation import normalize_payload_to_records, validate_reading, validate_top_level_payload

__all__ = [
    "BatchDecision",
    "HealthStatus",
    "IngestMode",
    "Mode",
    "NormalizedReading",
    "RecordValidationResult",
    "TelemetryStatus",
    "TopLevelValidationResult",
    "ValidationError",
    "build_noop_batch_decision",
    "evaluate_health_status",
    "evaluate_telemetry_status",
    "normalize_payload_to_records",
    "parse_and_normalize_timestamp",
    "resolve_ingest_mode",
    "summarize_atomic_result",
    "summarize_partial_result",
    "validate_reading",
    "validate_top_level_payload",
]
