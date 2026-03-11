from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.timestamp import parse_and_normalize_timestamp


def test_parse_utc_timestamp() -> None:
    result = parse_and_normalize_timestamp("2024-05-23T08:30:00Z")

    assert result == datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)


def test_parse_kst_timestamp_to_utc() -> None:
    result = parse_and_normalize_timestamp("2024-05-23T17:30:00+09:00")

    assert result == datetime(2024, 5, 23, 8, 30, tzinfo=timezone.utc)


def test_mixed_timezone_values_normalize_to_same_canonical_time() -> None:
    utc_value = parse_and_normalize_timestamp("2024-05-23T08:30:00Z")
    kst_value = parse_and_normalize_timestamp("2024-05-23T17:30:00+09:00")

    assert utc_value == kst_value


@pytest.mark.parametrize(
    "raw_timestamp",
    [
        "2024-05-23T08:30:00",
        "not-a-timestamp",
        "",
    ],
)
def test_invalid_timestamp_is_rejected(raw_timestamp: str) -> None:
    with pytest.raises(ValueError):
        parse_and_normalize_timestamp(raw_timestamp)
