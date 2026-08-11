"""
Modèle Conversation pour les discussions entre deux utilisateurs.
"""
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.message import Message

class Conversation(Base):
    """Conversation entre deux utilisateurs."""
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="uq_conversation_users"),
        Index("idx_conversation_user1", "user1_id"),
        Index("idx_conversation_user2", "user2_id"),
        Index("idx_conversation_updated", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user1_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relations
    user1: Mapped["User"] = relationship("User", foreign_keys=[user1_id], lazy="selectin")
    user2: Mapped["User"] = relationship("User", foreign_keys=[user2_id], lazy="selectin")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", lazy="selectin")
