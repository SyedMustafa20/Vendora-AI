from sqlalchemy.orm import Session

from models.agent import AgentConfig
from schemas.agent import AgentConfigUpdate

DEFAULT_INTENT_PROMPT = (
    "You are a customer support intent classifier. "
    "Given a user message, classify it into exactly one of: "
    "order_query, product_query, refund_query, payment_query, technical_query, general_support. "
    "Respond with ONLY the intent label, nothing else."
)

DEFAULT_GENERATIVE_PROMPT = """You are a professional ecommerce customer support agent.

INSTRUCTIONS:
1. Use ONLY the provided context if available
2. Be concise, helpful, and accurate
3. Do NOT hallucinate or make up data
4. At the end, ask 1-2 leading questions to clarify the customer's need or suggest next steps
5. Be friendly and professional

RESPONSE GUIDELINES:
- Answer their question directly
- If data is missing, ask for clarification
- End with helpful follow-up questions
- Keep response under 150 words"""

DEFAULT_AGENT_SETTINGS = {
    "agent_type": "support_bot",
    "agent_behavior_type": "generative",
    "model_name": "groq",
    "model_version": "llama-3.1-8b-instant",
    "temperature": 0.3,
}


def create_default_agent(db: Session, admin_id: int) -> AgentConfig:
    config = AgentConfig(
        admin_id=admin_id,
        intent_prompt=DEFAULT_INTENT_PROMPT,
        generative_prompt=DEFAULT_GENERATIVE_PROMPT,
        **DEFAULT_AGENT_SETTINGS,
    )
    db.add(config)
    return config


def get_agent(db: Session, admin_id: int) -> AgentConfig | None:
    return db.query(AgentConfig).filter(AgentConfig.admin_id == admin_id).first()


def update_agent(db: Session, admin_id: int, data: AgentConfigUpdate) -> AgentConfig:
    config = get_agent(db, admin_id)
    if config is None:
        raise ValueError(f"No agent config found for admin {admin_id}")

    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return config
