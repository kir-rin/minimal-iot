from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from .reading import Reading
from .sensor_status import SensorCurrentStatus
from .mode_request import ModeChangeRequest

__all__ = [
    "Base",
    "Reading",
    "SensorCurrentStatus",
    "ModeChangeRequest",
]
