from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    agent_type = Column(String(50), nullable=False)
    # e.g. support_bot, recommendation_agent, sales_agent

    agent_behavior_type = Column(String(30), nullable=False, default="generative")
    """
    Values:
        deterministic → rule-based / fixed responses / classification
        generative → balanced LLM responses (default chat mode)
        creative → high randomness / storytelling / brainstorming
    """

    intent_prompt = Column(Text, nullable=False)
    generative_prompt = Column(Text, nullable=False)

    model_name = Column(String(100))
    model_version = Column(String(50))

    temperature = Column(Float, default=0.7)

    tokens_used = Column(Integer)
    latency_ms = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)