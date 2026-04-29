from sqlalchemy.orm import Session

from models.conversation import Conversation
from models.message import Message
from models.users import User


def get_conversations_page(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Paginated conversations, each containing its full message list.
    Uses two batch queries (users + messages) to avoid N+1.
    """
    offset = (page - 1) * page_size
    total = db.query(Conversation).count()
    pages = max(1, (total + page_size - 1) // page_size)

    convs: list[Conversation] = (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    if not convs:
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "items": [],
        }

    # Batch-load users (avoids per-row SELECT)
    user_ids = list({c.user_id for c in convs if c.user_id is not None})
    users: dict[int, User] = {
        u.id: u
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    }

    # Batch-load all messages for this page's conversations
    conv_ids = [c.id for c in convs]
    all_messages: list[Message] = (
        db.query(Message)
        .filter(Message.conversation_id.in_(conv_ids))
        .order_by(Message.created_at.asc())
        .all()
    )
    msgs_by_conv: dict[int, list[Message]] = {}
    for m in all_messages:
        msgs_by_conv.setdefault(m.conversation_id, []).append(m)

    items = []
    for conv in convs:
        user = users.get(conv.user_id)
        msgs = msgs_by_conv.get(conv.id, [])
        last = msgs[-1] if msgs else None

        items.append({
            "id": conv.id,
            "user_phone": (user.phone if user and user.phone else "—"),
            "intent": conv.intent,
            "summary": conv.conversation_summary,
            "message_count": len(msgs),
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "last_message_at": (
                last.created_at.isoformat() if last and last.created_at else None
            ),
            "messages": [
                {
                    "id": m.id,
                    "content": m.content,
                    "sender_type": m.sender_type,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msgs
            ],
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "items": items,
    }
