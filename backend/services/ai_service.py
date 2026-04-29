import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from agent.agent import Agent
from models.message import Message
from models.conversation import Conversation
from services.summarize_conversation import update_summary_if_needed, get_cached_summary
from services.get_conversation import get_or_create_conversation
from services.get_user import get_or_create_user

load_dotenv()

agent = Agent(openrouter_api_key=os.getenv("OPENROUTER_API_KEY"))

# Constants for message types
MESSAGE_TYPE_FIRST_TIME = "first_time"
MESSAGE_TYPE_GUARDRAIL_REJECT = "guardrail_reject"
MESSAGE_TYPE_REGULAR = "regular"


def _save_message(db: Session, conversation_id: int, sender: str, content: str) -> Message:
    msg = Message(conversation_id=conversation_id, sender_type=sender, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def _get_message_count(db: Session, conversation_id: int) -> int:
    """Get total message count for this conversation."""
    return db.query(Message).filter(Message.conversation_id == conversation_id).count()


def _determine_message_type(db: Session, conversation: Conversation, guardrail_result: dict) -> str:
    """
    Determine what type of message this is.
    """
    message_count = _get_message_count(db, conversation.id)
    
    # First message from this user
    if message_count == 1:  # Only the user message we just saved
        return MESSAGE_TYPE_FIRST_TIME
    
    # Failed guardrails
    if not guardrail_result.get("is_valid"):
        return MESSAGE_TYPE_GUARDRAIL_REJECT
    
    # Regular message
    return MESSAGE_TYPE_REGULAR


def build_context(db, conversation, tool_data=None):
    """Build context from conversation history and tool data."""
    last_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(5)
        .all()
    )

    chat_history = "\n".join(
        f"{m.sender_type}: {m.content}" for m in reversed(last_messages)
    )

    summary = get_cached_summary(conversation)

    return agent.build_agent_context(summary, chat_history, tool_data)


def fetch_tool_data(db, tool_name: str, message: str, user):
    """
    Execute the selected tool to fetch data.
    """
    if tool_name == "order_lookup":
        from tools.order_tool import execute_order_lookup
        return execute_order_lookup(db, message, user)
    
    elif tool_name == "product_search":
        from tools.product_tool import search_products
        return search_products(db, message)
    
    elif tool_name == "refund_processor":
        # TODO: Implement refund tool
        return {"type": "refund", "found": False, "message": "Refund processing tool coming soon"}
    
    elif tool_name == "payment_info":
        # TODO: Implement payment tool
        return {"type": "payment", "found": False, "message": "Payment info tool coming soon"}
    
    return None


def get_default_response(reason: str) -> str:
    """
    Return default response based on guardrail rejection reason.
    """
    responses = {
        "Security": (
            "⛔ I cannot process that request as it appears to contain harmful content. "
            "Please contact us with legitimate store-related queries only."
        ),
        "Out of scope": (
            "I'm here to help with store-related queries only! 🏪\n\n"
            "I can assist with:\n"
            "📦 Order tracking & status\n"
            "🛍️ Product information\n"
            "💳 Payment & billing\n"
            "↩️ Refunds & returns\n"
            "🔧 Technical support\n\n"
            "What can I help you with today?"
        ),
    }
    return responses.get(reason, "I can only help with store-related queries. Please try again with a store-related question!")


def handle_message(db: Session, sender_phone: str, user_message: str) -> str:
    """
    Main message handler implementing the full workflow:
    
    1. GUARDRAIL LAYER - Check if message is valid
    2. FIRST-TIME GREETING - If first message, send static greeting
    3. ROUTER - Classify intent
    4. TOOL SELECTOR - Select appropriate tool
    5. DB TOOL EXECUTION - Fetch data
    6. CONTEXT BUILDER - Build structured context
    7. LLM RESPONSE GENERATOR - Generate response with leading questions
    """
    
    # Get or create user and conversation
    user = get_or_create_user(db, sender_phone)
    conversation = get_or_create_conversation(db, user.id)
    
    # Save the user message
    _save_message(db, conversation.id, "user", user_message)
    
    # ==========================================
    # [1] GUARDRAIL LAYER (STRICT FILTERING)
    # ==========================================
    guardrail_result = agent.apply_guardrails(user_message)
    
    # ==========================================
    # [2] DETERMINE MESSAGE TYPE
    # ==========================================
    message_type = _determine_message_type(db, conversation, guardrail_result)
    
    # ==========================================
    # [2A] FIRST-TIME GREETING (NO LLM)
    # ==========================================
    if message_type == MESSAGE_TYPE_FIRST_TIME:
        reply = agent.get_first_message_greeting()
        _save_message(db, conversation.id, "agent", reply)
        return reply
    
    # ==========================================
    # [2B] GUARDRAIL REJECTION
    # ==========================================
    if message_type == MESSAGE_TYPE_GUARDRAIL_REJECT:
        reply = get_default_response(guardrail_result.get("reason"))
        _save_message(db, conversation.id, "agent", reply)
        return reply
    
    # ==========================================
    # [3] ROUTER (INTENT CLASSIFICATION)
    # ==========================================
    intent = agent.classify_intent(user_message)
    
    # Update conversation with current intent
    if conversation.intent != intent:
        conversation.intent = intent
        db.commit()
    
    # ==========================================
    # [4] TOOL SELECTOR
    # ==========================================
    tool_selection = agent.select_tool(intent, user_message)
    
    # ==========================================
    # [5] DB TOOL EXECUTION (with caching)
    # ==========================================
    tool_data = None
    if tool_selection.get("needs_db"):
        tool_data = fetch_tool_data(
            db,
            tool_selection.get("tool"),
            user_message,
            user
        )
    
    # ==========================================
    # [6] CONTEXT BUILDER (STRUCTURED DATA)
    # ==========================================
    # Update summary if needed
    update_summary_if_needed(db, conversation, agent)
    
    # Build context with conversation history + tool data
    context = build_context(db, conversation, tool_data)
    
    # ==========================================
    # [7] LLM RESPONSE GENERATOR
    # ==========================================
    reply = agent.generate_response(
        message=user_message,
        context=context,
        intent=intent
    )
    
    # ==========================================
    # SAVE RESPONSE
    # ==========================================
    _save_message(db, conversation.id, "agent", reply)
    
    return reply
