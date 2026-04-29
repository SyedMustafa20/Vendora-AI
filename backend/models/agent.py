from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime
from datetime import datetime, timezone
from db.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(
        Integer,
        ForeignKey("admins.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    agent_type = Column(String(50), nullable=False, default="support_bot")
    # support_bot | recommendation_agent | sales_agent

    agent_behavior_type = Column(String(30), nullable=False, default="generative")
    # deterministic | generative | creative

    intent_prompt = Column(Text, nullable=False)
    generative_prompt = Column(Text, nullable=False)

    model_name = Column(String(100), nullable=False, default="groq")
    model_version = Column(String(50), nullable=False, default="llama-3.1-8b-instant")

    temperature = Column(Float, nullable=False, default=0.3)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
