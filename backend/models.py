from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from .database import Base
import datetime

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    public_key = Column(Text, nullable=False)  # RSA Public Key PEM
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    recipient_id = Column(Integer, ForeignKey('users.id'))
    encrypted_content = Column(Text, nullable=False)
    encrypted_session_key = Column(Text, nullable=False)
    encrypted_session_key_sender = Column(Text, nullable=True) # RSA-encrypted key for sender
    iv = Column(Text, nullable=False)
    integrity_hash = Column(String(64), nullable=False)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
