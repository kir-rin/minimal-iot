from __future__ import annotations

from .readings_router import router as readings_router
from .sensors_router import router as sensors_router

__all__ = ["readings_router", "sensors_router"]
