import os
import time
import logging
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1"
)

# Single model ONLY (no fallback chain)
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "meta-llama/llama-3.1-8b-instruct:free"
)

_OR_REFERER = os.getenv("OPENROUTER_REFERER")
_OR_TITLE = os.getenv("OPENROUTER_APP_TITLE")

_default_headers = {}
if _OR_REFERER:
    _default_headers["HTTP-Referer"] = _OR_REFERER
if _OR_TITLE:
    _default_headers["X-Title"] = _OR_TITLE


class Agent:
    def __init__(self, openrouter_api_key: str):
        self.client = OpenAI(
            api_key=openrouter_api_key,
            base_url=OPENROUTER_BASE_URL,
            default_headers=_default_headers or None,
        )

    def _call(self, messages, temperature=0.3, max_tokens=512):
        """
        Minimal retry logic (ONLY one model).
        """
        for attempt in range(3):
            try:
                res = self.client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return res.choices[0].message.content or ""

            except RateLimitError:
                wait = 2 ** attempt
                logger.warning("Rate limited. retrying in %ds", wait)
                time.sleep(wait)

        raise RuntimeError("LLM temporarily unavailable")

    # ========================================
    # [1] GUARDRAIL LAYER (STRICT FILTERING)
    # ========================================
    def apply_guardrails(self, message: str) -> dict:
        """
        Check if the message is store-related.
        Returns: {"is_valid": bool, "reason": str}
        """
        store_keywords = [
            "order", "product", "price", "refund", "cancel", "track", "status",
            "delivery", "shipping", "payment", "invoice", "warranty", "return",
            "exchange", "stock", "available", "discount", "buy", "purchase",
            "payment", "support", "help", "complaint", "issue"
        ]
        
        msg_lower = message.lower().strip()
        
        # Block harmful/invalid queries
        harmful_patterns = ["hack", "crack", "attack", "virus", "malware"]
        if any(pattern in msg_lower for pattern in harmful_patterns):
            return {
                "is_valid": False,
                "reason": "Security"
            }
        
        # Check if message is store-related
        is_store_related = any(keyword in msg_lower for keyword in store_keywords)
        
        if not is_store_related:
            return {
                "is_valid": False,
                "reason": "Out of scope"
            }
        
        return {
            "is_valid": True,
            "reason": "Approved"
        }
    
    # ========================================
    # [2] FIRST-TIME GREETING HANDLER
    # ========================================
    def get_first_message_greeting(self) -> str:
        """
        Static greeting for first-time users.
        No LLM call needed.
        """
        return (
            "👋 Welcome to our customer support!\n\n"
            "How can we help you today? Please select or describe your query:\n\n"
            "📦 **Order** - Track your order, check status, delivery info\n"
            "🛍️ **Product** - Browse products, check availability, pricing\n"
            "💳 **Payment** - Payment issues, invoices, billing\n"
            "↩️ **Refund/Return** - Process refunds, returns, exchanges\n"
            "🔧 **Technical Issue** - App problems, account issues\n"
            "❓ **General Support** - Any other questions\n\n"
            "Just describe your query and we'll assist you!"
        )
    
    # ========================================
    # [3] INTENT CLASSIFICATION (ROUTER)
    # ========================================
    def classify_intent(self, message: str) -> str:
        """
        Classify user intent into categories.
        Uses keyword matching + LLM for better accuracy.
        Returns: "order_query" | "product_query" | "refund_query" | 
                 "payment_query" | "technical_query" | "general_support"
        """
        msg_lower = message.lower()
        
        # Rule-based routing (fast path)
        if any(k in msg_lower for k in ["order", "track", "status", "delivery", "shipping"]):
            return "order_query"
        
        if any(k in msg_lower for k in ["product", "price", "available", "stock", "buy"]):
            return "product_query"
        
        if any(k in msg_lower for k in ["refund", "return", "exchange", "money back"]):
            return "refund_query"
        
        if any(k in msg_lower for k in ["payment", "pay", "invoice", "billing", "charge"]):
            return "payment_query"
        
        if any(k in msg_lower for k in ["bug", "crash", "error", "app", "account", "login"]):
            return "technical_query"
        
        return "general_support"
    
    # ========================================
    # [4] TOOL SELECTOR (LLM + RULES)
    # ========================================
    def select_tool(self, intent: str, message: str) -> dict:
        """
        Select appropriate tool based on intent.
        Returns: {"tool": str, "needs_db": bool, "description": str}
        """
        tool_map = {
            "order_query": {
                "tool": "order_lookup",
                "needs_db": True,
                "description": "Retrieve order details from database"
            },
            "product_query": {
                "tool": "product_search",
                "needs_db": True,
                "description": "Search products in database"
            },
            "refund_query": {
                "tool": "refund_processor",
                "needs_db": True,
                "description": "Get refund/return policy and process"
            },
            "payment_query": {
                "tool": "payment_info",
                "needs_db": True,
                "description": "Retrieve payment and billing info"
            },
            "technical_query": {
                "tool": "technical_support",
                "needs_db": False,
                "description": "Provide technical guidance"
            },
            "general_support": {
                "tool": "general_qa",
                "needs_db": False,
                "description": "General question answering"
            }
        }
        
        return tool_map.get(intent, tool_map["general_support"])
    
    # ========================================
    # [5] CONTEXT BUILDER (WITH GUARDRAILS)
    # ========================================
    def build_agent_context(self, summary: str, chat_history: str, tool_data: dict = None) -> str:
        """
        Build structured context for LLM.
        Includes summary, chat history, and tool data.
        """
        context = f"""
                    === CONVERSATION CONTEXT ===
                    SUMMARY:
                    {summary}

                    CHAT HISTORY:
                    {chat_history}
                    """
                    
        if tool_data:
            context += f"""
                        === DATABASE RESULTS ===
                        {self._format_tool_data(tool_data)}
                        """
        
        return context
    
    def _format_tool_data(self, tool_data: dict) -> str:
        """Format tool data for readability."""
        if tool_data.get("type") == "order":
            if not tool_data.get("found"):
                return tool_data.get("message", "No order found")
            
            order = tool_data.get("order", {})
            items = tool_data.get("items", [])
            
            formatted = f"""
                Order ID: {order.get('order_code')}
                Status: {order.get('status')}
                Total: ${order.get('total')}
                Created: {order.get('created_at')}

                Items:
                """
            for item in items:
                formatted += f"  - {item['product_name']} x{item['quantity']} @ ${item['price']}\n"
            
            return formatted
        
        elif tool_data.get("type") == "product":
            if not tool_data.get("found"):
                return tool_data.get("message", "No products found")
            
            suggestions = tool_data.get("suggestions", [])
            formatted = "Products Found:\n"
            for prod in suggestions:
                formatted += f"  - {prod['name']} (${prod['price']}) - {prod['category']}\n"
            
            return formatted
        
        return str(tool_data)
    
    # ========================================
    # [6] RESPONSE GENERATOR (WITH LEADING QUESTIONS)
    # ========================================
    def generate_response(self, message: str, context: str = "", intent: str = "general_support") -> str:
        """
        Generate LLM response with context and leading questions.
        """
        system_prompt = f"""You are a professional ecommerce customer support agent.

                            INSTRUCTIONS:
                            1. Use ONLY the provided context if available
                            2. Be concise, helpful, and accurate
                            3. Do NOT hallucinate or make up data
                            4. At the end, ask 1-2 leading questions to clarify their need or suggest next steps
                            5. Be friendly and professional
                            6. Current intent: {intent}

                            Context available:
                            {context if context else "No specific data found. Provide general support."}

                            RESPONSE GUIDELINES:
                            - Answer their question directly
                            - If data is missing, ask for clarification
                            - End with helpful follow-up questions
                            - Keep response under 150 words
                            """
        
        return self._call([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ])