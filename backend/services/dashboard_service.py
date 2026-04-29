"""
Dashboard statistics service.
Aggregates metrics for admin dashboard.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.conversation import Conversation
from models.message import Message
from models.users import User


def get_total_stats(db: Session) -> dict:
    """
    Get basic statistics:
    - Total conversations
    - Total messages
    - Total users (clients only)
    """
    total_conversations = db.query(Conversation).count()
    total_messages = db.query(Message).count()
    total_users = db.query(User).filter(User.user_type == "client").count()
    
    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_users": total_users,
    }


def get_intent_distribution(db: Session) -> list:
    """
    Get count of conversations per intent.
    Returns: [{"intent": "order_query", "count": 42}, ...]
    """
    results = (
        db.query(
            Conversation.intent,
            func.count(Conversation.id).label("count")
        )
        .filter(Conversation.intent.isnot(None))
        .group_by(Conversation.intent)
        .all()
    )
    
    return [
        {"intent": intent, "count": count}
        for intent, count in results
    ]


def get_messages_per_day(db: Session, days: int = 30) -> list:
    """
    Get count of messages per day for last N days (for chart).
    Returns: [{"date": "2026-03-30", "count": 12}, ...]
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    results = (
        db.query(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count")
        )
        .filter(
            Message.sender_type == "agent",
            Message.created_at >= start_date
        )
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
        .all()
    )
    
    return [
        {"date": str(date), "count": count}
        for date, count in results
    ]


def get_recent_conversations(db: Session, limit: int = 10) -> list:
    """
    Get recent conversations for activity feed.
    """
    from models.users import User as UserModel
    
    results = (
        db.query(
            Conversation.id,
            UserModel.phone,
            Conversation.intent,
            func.count(Message.id).label("message_count"),
            Conversation.created_at,
            func.max(Message.created_at).label("last_message_at")
        )
        .join(UserModel, Conversation.user_id == UserModel.id)
        .join(Message, Conversation.id == Message.conversation_id)
        .group_by(
            Conversation.id,
            UserModel.phone,
            Conversation.intent,
            Conversation.created_at
        )
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": conv_id,
            "user_phone": phone,
            "intent": intent,
            "message_count": msg_count,
            "created_at": created_at.isoformat(),
            "last_message_at": last_msg.isoformat() if last_msg else None
        }
        for conv_id, phone, intent, msg_count, created_at, last_msg in results
    ]


def get_dashboard_data(db: Session) -> dict:
    """Main dashboard data aggregator."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "stats": get_total_stats(db),
        "intent_distribution": get_intent_distribution(db),
        "messages_per_day": get_messages_per_day(db, days=30),
        "recent_conversations": get_recent_conversations(db, limit=10),
    }