from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Mode(str, Enum):
    NORMAL = "NORMAL"
    EMERGENCY = "EMERGENCY"


class IngestMode(str, Enum):
    ATOMIC = "atomic"
    PARTIAL = "partial"


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    FAULTY = "FAULTY"
    UNKNOWN = "UNKNOWN"


class TelemetryStatus(str, Enum):
    FRESH = "FRESH"
    DELAYED = "DELAYED"
    CLOCK_SKEW = "CLOCK_SKEW"
    OUT_OF_ORDER = "OUT_OF_ORDER"


@dataclass
class ValidationError:
    field: str
    reason: str
    index: int | None = None
    code: str | None = None


@dataclass
class NormalizedReading:
    serial_number: str
    raw_timestamp: str
    sensor_timestamp: datetime
    mode: Mode
    temperature: float | int
    humidity: float | int
    pressure: float | int
    latitude: float | int
    longitude: float | int
    air_quality: int
    original_record: dict[str, Any] = field(repr=False)


@dataclass
class TopLevelValidationResult:
    is_valid: bool
    records: list[Any] = field(default_factory=list)
    errors: list[ValidationError] = field(default_factory=list)

    @classmethod
    def success(cls, records: list[Any]) -> TopLevelValidationResult:
        return cls(is_valid=True, records=records, errors=[])

    @classmethod
    def failure(cls, error: ValidationError) -> TopLevelValidationResult:
        return cls(is_valid=False, records=[], errors=[error])


@dataclass
class RecordValidationResult:
    accepted: bool
    reading: NormalizedReading | None = None
    error: ValidationError | None = None

    @classmethod
    def success(cls, reading: NormalizedReading) -> RecordValidationResult:
        return cls(accepted=True, reading=reading, error=None)

    @classmethod
    def failure(cls, error: ValidationError) -> RecordValidationResult:
        return cls(accepted=False, reading=None, error=error)


@dataclass
class BatchDecision:
    success: bool
    ingest_mode: IngestMode
    accepted_count: int
    rejected_count: int
    errors: list[ValidationError] = field(default_factory=list)
    accepted_records: list[NormalizedReading] = field(default_factory=list)
