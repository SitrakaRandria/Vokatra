"""
Modèle pour les tokens de notification push.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class NotificationToken(Base):
    __tablename__ = "notification_tokens"
    __table_args__ = (
        Index("idx_notification_token_user", "user_id"),
        Index("idx_notification_token_active", "is_active"),
        Index("idx_notification_token_device", "device_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    token: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    device_type: Mapped[str] = mapped_column(String(20), nullable=False)  # web, ios, android
    device_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
