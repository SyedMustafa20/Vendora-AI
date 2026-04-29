from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class StatsSummary(BaseModel):
    """Overview stats card"""
    total_conversations: int
    total_messages: int
    total_users: int


class IntentCount(BaseModel):
    """Intent distribution item"""
    intent: str
    count: int


class MessagePerDay(BaseModel):
    """Daily message count for graph"""
    date: str  # "2026-04-29"
    count: int


class RecentConversation(BaseModel):
    """Recent conversation in activity feed"""
    id: int
    user_phone: str
    intent: Optional[str]
    message_count: int
    created_at: str
    last_message_at: Optional[str]


class DashboardResponse(BaseModel):
    """Complete dashboard data response"""
    timestamp: str
    stats: StatsSummary
    intent_distribution: List[IntentCount]
    messages_per_day: List[MessagePerDay]
    recent_conversations: List[RecentConversation]