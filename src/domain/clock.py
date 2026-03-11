from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass
class FixedClock:
    current: datetime

    def __post_init__(self) -> None:
        if self.current.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")

    def now(self) -> datetime:
        return self.current

    def set(self, current: datetime) -> None:
        if current.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self.current = current

    def advance(self, *, seconds: int = 0, minutes: int = 0) -> None:
        self.current = self.current + timedelta(seconds=seconds, minutes=minutes)
