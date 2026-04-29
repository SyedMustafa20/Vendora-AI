from pydantic import BaseModel
from typing import List, Optional


class MessageItem(BaseModel):
    id: int
    content: str
    sender_type: str  # "user" | "agent"
    created_at: Optional[str]


class ConversationItem(BaseModel):
    id: int
    user_phone: str
    intent: Optional[str]
    summary: Optional[str]
    message_count: int
    created_at: Optional[str]
    last_message_at: Optional[str]
    messages: List[MessageItem]


class ConversationsPage(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: List[ConversationItem]
