from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class MessageBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class MessageCreate(MessageBase):
    conversation_id: int

class MessageResponse(MessageBase):
    id: int
    sender_id: int
    conversation_id: int
    read: bool
    created_at: datetime
