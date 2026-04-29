from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from  db.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    content = Column(String)
    sender_type = Column(String)  # "user" or "agent"
    created_at = Column(DateTime, default=datetime.utcnow)