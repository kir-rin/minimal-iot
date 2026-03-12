from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base


class ModeChangeRequest(Base):
    """모드 변경 요청 모델"""
    
    __tablename__ = "mode_change_requests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    serial_number: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    requested_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<ModeChangeRequest(id={self.id}, serial={self.serial_number}, mode={self.requested_mode})>"
