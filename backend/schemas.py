from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    public_key: str

class UserOut(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    sender_id: int
    recipient_id: int
    encrypted_content: str
    encrypted_session_key: str
    encrypted_session_key_sender: Optional[str] = None
    iv: str
    integrity_hash: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None

class MessageOut(MessageCreate):
    id: int
    sent_at: datetime
    class Config:
        from_attributes = True
