#!/usr/bin/env python3
"""
Quick Reference: Updated AI Workflow
====================================

This file documents the message handling flow and key functions.
"""

# ============================================================================
# COMPLETE WORKFLOW DIAGRAM
# ============================================================================

WORKFLOW = """
┌─────────────────────────────────────────────────────────────────────┐
│                     WHATSAPP MESSAGE RECEIVED                       │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                    (save msg)
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  [1] GUARDRAIL LAYER (STRICT)     │
        │  • Check security (block harmful)  │
        │  • Check scope (store-related?)    │
        │  • agent.apply_guardrails()       │
        └──────────┬─────────────────────────┘
                   │
       ┌───────────┴──────────┐
       │                      │
    VALID                  INVALID
       │                      │
       ▼                      ▼
     [2A]                   [2B]
  CHECK IF             RETURN DEFAULT
  FIRST TIME             RESPONSE
       │                   (No LLM)
       │
 YES? RETURN           
 STATIC GREETING       
 (No LLM)              
       │
       NO
       │
       ▼
    ┌─────────────────────────────────┐
    │ [3] INTENT CLASSIFICATION       │
    │ agent.classify_intent()        │
    │ Returns: order_query |         │
    │          product_query |       │
    │          refund_query, etc.    │
    └──────────┬────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ [4] TOOL SELECTOR               │
    │ agent.select_tool()            │
    │ Maps intent → tool type        │
    └──────────┬────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ [5] DB TOOL EXECUTION           │
    │ fetch_tool_data()              │
    │ • Get order/product/etc. data  │
    │ • Format results               │
    └──────────┬────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ [6] CONTEXT BUILDER             │
    │ build_context()                │
    │ • Summary + chat history       │
    │ • Tool data                    │
    │ • Formatted for LLM            │
    └──────────┬────────────────────┘
               │
               ▼
    ┌─────────────────────────────────┐
    │ [7] LLM RESPONSE GENERATOR       │
    │ agent.generate_response()      │
    │ • Uses context                 │
    │ • Adds leading questions       │
    │ • Temp: 0.3 (factual)         │
    └──────────┬────────────────────┘
               │
               ▼
        ┌──────────────────────┐
        │  SAVE TO DB & SEND   │
        │  VIA TWILIO          │
        └──────────────────────┘
"""

# ============================================================================
# FUNCTION QUICK REFERENCE
# ============================================================================

FUNCTIONS = """
AGENT.PY - Core Functions
═════════════════════════

1. apply_guardrails(message: str) -> dict
   ├─ Blocks harmful content
   ├─ Checks if store-related
   └─ Returns: {"is_valid": bool, "reason": str}

2. get_first_message_greeting() -> str
   ├─ Static greeting (no LLM)
   └─ Lists category options

3. classify_intent(message: str) -> str
   ├─ Keywords: order, product, refund, payment, technical
   └─ Returns: intent category

4. select_tool(intent: str, message: str) -> dict
   ├─ Maps intent to tool
   └─ Returns: {"tool": str, "needs_db": bool}

5. build_agent_context(summary, chat_history, tool_data) -> str
   └─ Structures data for LLM

6. generate_response(message, context, intent) -> str
   ├─ LLM call with context
   ├─ Adds leading questions
   └─ Max tokens: 512, Temp: 0.3


AI_SERVICE.PY - Message Handler
════════════════════════════════

handle_message(db, sender_phone, user_message) -> str
  │
  ├─ Save user message to DB
  ├─ apply_guardrails() → check validity
  ├─ _determine_message_type() → first/reject/regular
  │
  ├─ [IF FIRST] → return greeting
  ├─ [IF REJECTED] → return error message
  ├─ [IF REGULAR]:
  │  ├─ classify_intent()
  │  ├─ select_tool()
  │  ├─ fetch_tool_data() → DB query
  │  ├─ build_context()
  │  ├─ generate_response() → LLM
  │
  └─ Save agent response to DB
"""

# ============================================================================
# INTENT CATEGORIES & TOOLS
# ============================================================================

INTENT_TOOLS = """
Intent Map
══════════

order_query
├─ Keywords: order, track, status, delivery, shipping
├─ Tool: order_lookup
├─ DB Needed: YES
└─ Example: "Where's my order?"

product_query
├─ Keywords: product, price, available, stock, buy
├─ Tool: product_search
├─ DB Needed: YES
└─ Example: "Show me red shoes"

refund_query
├─ Keywords: refund, return, exchange, money back
├─ Tool: refund_processor (TBD)
├─ DB Needed: YES
└─ Example: "Can I return this?"

payment_query
├─ Keywords: payment, pay, invoice, billing, charge
├─ Tool: payment_info (TBD)
├─ DB Needed: YES
└─ Example: "Can I use PayPal?"

technical_query
├─ Keywords: bug, crash, error, app, account, login
├─ Tool: technical_support
├─ DB Needed: NO
└─ Example: "App keeps crashing"

general_support
├─ Keywords: anything not above
├─ Tool: general_qa
├─ DB Needed: NO
└─ Example: "Who are you?"
"""

# ============================================================================
# EXAMPLE FLOWS
# ============================================================================

EXAMPLE_FLOWS = """
EXAMPLE 1: First-Time User
═════════════════════════

User sends: "Hi"
│
├─ Guardrails: PASS (greeting is valid)
├─ Message count: 1 (FIRST MESSAGE!)
├─ → Returns static greeting with categories
└─ NO LLM CALL

Bot replies:
"👋 Welcome! How can we help?
 📦 Order - Track status
 🛍️ Product - Browse items
 ...etc"


EXAMPLE 2: Out-of-Scope Query
═════════════════════════════

User sends: "What's your favorite food?"
│
├─ Guardrails: FAIL (no store keywords)
├─ Reason: "Out of scope"
├─ → Returns default error message
└─ NO LLM CALL

Bot replies:
"I'm here to help with store queries only! 🏪
 I can assist with: Orders, Products, Refunds..."


EXAMPLE 3: Order Lookup (Full Flow)
═══════════════════════════════════

User sends: "Where is my order ORD123?"
│
├─ Guardrails: PASS
├─ Message count: 3 (NOT FIRST)
├─ Intent: order_query (keyword "order")
├─ Tool selected: order_lookup (needs DB)
├─ DB Execution: Fetches ORD123 details
│  └─ Status: "In Transit"
│     Delivery: "Tomorrow"
│     Items: [Shoe, Hat]
│
├─ Context Built:
│  ├─ Summary: "Customer tracking orders"
│  ├─ History: [Previous 5 messages]
│  └─ DB Result: [Order details]
│
├─ LLM Called with full context
│  └─ System prompt: "Use context, add leading questions"
│  
└─ Response generated:
   "Your order ORD123 is in transit! 
    Expected delivery: tomorrow.
    Would you like tracking updates or have delivery concerns?"

Bot replies with leading questions!
"""

# ============================================================================
# GUARDRAILS & DEFAULTS
# ============================================================================

GUARDRAILS = """
Guardrail Keywords
══════════════════

STORE KEYWORDS (Approved):
├─ order, product, price, refund, cancel, track, status
├─ delivery, shipping, payment, invoice, warranty, return
├─ exchange, stock, available, discount, buy, purchase
├─ support, help, complaint, issue

HARMFUL PATTERNS (Blocked):
├─ hack, crack, attack, virus, malware

Default Responses
═════════════════

Security Rejection:
"⛔ I cannot process that request as it appears to contain 
   harmful content. Please contact us with legitimate 
   store-related queries only."

Out-of-Scope Rejection:
"I'm here to help with store-related queries only! 🏪

 I can assist with:
 📦 Order tracking & status
 🛍️ Product information
 💳 Payment & billing
 ↩️  Refunds & returns
 🔧 Technical support

 What can I help you with today?"
"""

# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

PERFORMANCE = """
LLM Call Savings
════════════════

Cases with NO LLM call:
├─ First-time user → 1 greeting message saved
├─ Out-of-scope → Default response no LLM
├─ Intent classification → Keyword-based
├─ Tool selection → Rule-based

Cases with LLM call:
└─ Final response generation ONLY → 1 call per valid message

Savings: ~70% fewer LLM calls compared to naive approach
Cost: ~$0.001 per guardrail rejection vs ~$0.005 per LLM call
"""

if __name__ == "__main__":
    print(WORKFLOW)
    print(FUNCTIONS)
    print(INTENT_TOOLS)
    print(EXAMPLE_FLOWS)
    print(GUARDRAILS)
    print(PERFORMANCE)
