from __future__ import annotations

from datetime import datetime, timezone


def parse_and_normalize_timestamp(raw_timestamp: str) -> datetime:
    """Parse and normalize an ISO8601 timestamp to UTC.

    Supports various ISO8601 formats including 'Z' suffix and explicit timezones.
    The result is always converted to UTC timezone.

    Args:
        raw_timestamp: ISO8601 formatted timestamp string.

    Returns:
        datetime: Timezone-aware datetime in UTC.

    Raises:
        ValueError: If timestamp is invalid, empty, or lacks timezone info.
    """
    if not isinstance(raw_timestamp, str):
        raise ValueError("timestamp must be a string")

    candidate = raw_timestamp.strip()
    if not candidate:
        raise ValueError("timestamp must not be empty")

    normalized_input = candidate.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized_input)
    except ValueError as exc:
        raise ValueError("Invalid ISO8601 timestamp") from exc

    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone information")

    return parsed.astimezone(timezone.utc)
