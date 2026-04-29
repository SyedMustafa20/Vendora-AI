from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text
from datetime import datetime
from db.database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    intent = Column(String, nullable=True)
    conversation_summary = Column(Text, nullable=True)