import os
import time
import logging
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


class Agent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=GROQ_BASE_URL,
        )

    def _call(self, messages, temperature=0.3, max_tokens=512):
        for attempt in range(3):
            try:
                res = self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return res.choices[0].message.content or ""
            except RateLimitError:
                wait = 2 ** attempt
                logger.warning("Groq rate limited (attempt %d) — retrying in %ds", attempt + 1, wait)
                time.sleep(wait)
            except Exception as exc:
                logger.error("Groq call failed: %s", exc)
                raise

        raise RuntimeError("Groq LLM temporarily unavailable")

    # ========================================
    # [1] GUARDRAIL LAYER (STRICT FILTERING)
    # ========================================
    def apply_guardrails(self, message: str) -> dict:
        """
        Two-stage check:
          1. Fast keyword block for clearly harmful content (no LLM needed).
          2. LLM decides whether the message is ecommerce-related.
        Returns: {"is_valid": bool, "reason": str}
        """
        msg_lower = message.lower().strip()

        # Stage 1 — block harmful content without an LLM call
        harmful_patterns = ["hack", "crack", "attack", "virus", "malware", "exploit", "ddos"]
        if any(pattern in msg_lower for pattern in harmful_patterns):
            return {"is_valid": False, "reason": "Security"}

        # Stage 2 — LLM decides relevance so brand names, slang, and short
        # product fragments ("air max", "size 10", "where's my stuff") all pass.
        system = (
            "You are a strict content filter for an ecommerce customer support chatbot. "
            "Decide whether the user message is related to shopping, products, orders, "
            "payments, deliveries, refunds, or general store support. "
            "Reply with exactly one word: YES or NO."
        )
        try:
            verdict = self._call(
                [{"role": "system", "content": system},
                 {"role": "user", "content": message}],
                temperature=0.0,
                max_tokens=5,
            ).strip().upper()
        except Exception:
            # If the LLM call fails, fail open so the conversation continues.
            verdict = "YES"

        if verdict.startswith("YES"):
            return {"is_valid": True, "reason": "Approved"}
        return {"is_valid": False, "reason": "Out of scope"}
    
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
    def generate_response(
        self,
        message: str,
        context: str = "",
        intent: str = "general_support",
        base_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        if base_prompt is None:
            base_prompt = (
                "You are a professional ecommerce customer support agent.\n\n"
                "INSTRUCTIONS:\n"
                "1. Use ONLY the provided context if available\n"
                "2. Be concise, helpful, and accurate\n"
                "3. Do NOT hallucinate or make up data\n"
                "4. At the end, ask 1-2 leading questions to clarify their need or suggest next steps\n"
                "5. Be friendly and professional\n\n"
                "RESPONSE GUIDELINES:\n"
                "- Answer their question directly\n"
                "- If data is missing, ask for clarification\n"
                "- End with helpful follow-up questions\n"
                "- Keep response under 150 words"
            )

        system_prompt = (
            f"{base_prompt}\n\n"
            f"Current intent: {intent}\n\n"
            f"Context:\n{context if context else 'No specific data found. Provide general support.'}"
        )

        return self._call(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=temperature,
        )