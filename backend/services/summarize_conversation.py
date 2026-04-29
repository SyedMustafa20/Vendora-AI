from sqlalchemy.orm import Session

from agent.agent import Agent
from models.message import Message
from models.conversation import Conversation
from core.cache import cache_set, cache_get, summary_key

SUMMARY_CACHE_TTL = 3600
SUMMARY_EVERY_N_MESSAGES = 5


def _summarize(agent: Agent, old_summary: str, new_messages: str) -> str:
    prompt = f"""
    Existing summary:
    {old_summary}

    New messages:
    {new_messages}

    Update the summary to include important details like:
    - user preferences
    - issues
    - order details
    - intent

    Keep it concise.
    """
    res = agent.openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content


def get_cached_summary(conversation: Conversation) -> str:
    cached = cache_get(summary_key(conversation.id))
    if cached is not None:
        return cached
    summary = conversation.conversation_summary or ""
    cache_set(summary_key(conversation.id), summary, ttl=SUMMARY_CACHE_TTL)
    return summary


def update_summary_if_needed(db: Session, conversation: Conversation, agent: Agent) -> None:
    """
    Only re-summarize every N messages to avoid an OpenAI call on every turn.
    """
    total = db.query(Message).filter(Message.conversation_id == conversation.id).count()
    if total == 0 or total % SUMMARY_EVERY_N_MESSAGES != 0:
        return

    recent = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(SUMMARY_EVERY_N_MESSAGES)
        .all()
    )
    combined = "\n".join(m.content for m in reversed(recent))
    new_summary = _summarize(agent, conversation.conversation_summary or "", combined)

    conversation.conversation_summary = new_summary
    db.commit()
    cache_set(summary_key(conversation.id), new_summary, ttl=SUMMARY_CACHE_TTL)
