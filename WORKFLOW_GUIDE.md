# WhatsApp Customer Support Bot - Updated AI Workflow

## Overview

The AI service has been completely restructured to implement a robust, guardrailed customer support workflow with 7 distinct layers of processing.

---

## Workflow Architecture

### Message Processing Flow

```
User Message
   ↓
[1] GUARDRAIL LAYER (IMPORTANT)
   ├─ Security check (block harmful patterns)
   └─ Store-relevance check
   ↓
[2] FIRST-TIME GREETING HANDLER (NO LLM)
   ├─ Detect if user's first message
   └─ Send static greeting with category options
   ↓
[3] ROUTER - INTENT CLASSIFICATION
   ├─ Classify into: order_query | product_query | refund_query
   │  payment_query | technical_query | general_support
   └─ Fast keyword-based routing
   ↓
[4] TOOL SELECTOR (LLM-Ready)
   ├─ Map intent to tool type
   ├─ Determine if DB fetch needed
   └─ Select: order_lookup | product_search | refund_processor, etc.
   ↓
[5] DB TOOL EXECUTION
   ├─ Execute selected tool (order lookup, product search, etc.)
   ├─ Fetch & structure data from database
   └─ Cache results for context building
   ↓
[6] CONTEXT BUILDER (STRUCTURED DATA)
   ├─ Combine: conversation summary + chat history + tool data
   ├─ Format data for LLM readability
   └─ Build rich context for next step
   ↓
[7] LLM RESPONSE GENERATOR
   ├─ Pass context to LLM with enhanced system prompt
   ├─ LLM generates response with leading questions
   └─ Response guides user to next action
   ↓
WhatsApp Reply (via Twilio)
```

---

## Implementation Details

### 1. Guardrail Layer

**File:** `agent.py` → `apply_guardrails(message: str)`

**Functionality:**
- Blocks harmful content (hack, crack, attack, virus, malware)
- Checks if message is store-related using keyword matching
- Returns: `{"is_valid": bool, "reason": str}`

**Rejection Reasons:**
- `"Security"` - Harmful content detected
- `"Out of scope"` - Not store-related

**Example:**
```python
result = agent.apply_guardrails("Can you help me hack something?")
# Returns: {"is_valid": False, "reason": "Security"}

result = agent.apply_guardrails("What's the weather today?")
# Returns: {"is_valid": False, "reason": "Out of scope"}
```

### 2. First-Time Greeting Handler

**File:** `agent.py` → `get_first_message_greeting()`

**Functionality:**
- Detects if this is the user's first message
- Sends static greeting (no LLM call)
- Presents category options

**Categories Presented:**
- 📦 Order - Track order, check status, delivery info
- 🛍️ Product - Browse products, check availability, pricing
- 💳 Payment - Payment issues, invoices, billing
- ↩️ Refund/Return - Process refunds, returns, exchanges
- 🔧 Technical Issue - App problems, account issues
- ❓ General Support - Any other questions

### 3. Intent Classification Router

**File:** `agent.py` → `classify_intent(message: str)`

**Intent Categories:**
```python
"order_query"        # Track orders, check status, delivery
"product_query"      # Product info, pricing, availability
"refund_query"       # Refunds, returns, exchanges
"payment_query"      # Payment, invoices, billing
"technical_query"    # App issues, account problems
"general_support"    # Fallback for other queries
```

**Routing Rules (Fast Path):**
- Keywords trigger specific intents
- No LLM overhead - fast keyword matching
- Fallback to `general_support` if no keywords match

### 4. Tool Selector

**File:** `agent.py` → `select_tool(intent: str, message: str)`

**Tool Mapping:**

| Intent | Tool | Needs DB | Purpose |
|--------|------|----------|---------|
| order_query | order_lookup | ✓ | Retrieve order details |
| product_query | product_search | ✓ | Search products |
| refund_query | refund_processor | ✓ | Handle refund requests |
| payment_query | payment_info | ✓ | Get payment/billing info |
| technical_query | technical_support | ✗ | Provide guidance |
| general_support | general_qa | ✗ | General Q&A |

**Returns:**
```python
{
    "tool": "order_lookup",
    "needs_db": True,
    "description": "Retrieve order details from database"
}
```

### 5. DB Tool Execution

**File:** `ai_service.py` → `fetch_tool_data(db, tool_name, message, user)`

**Supported Tools:**
- `order_lookup` → `order_tool.execute_order_lookup()`
- `product_search` → `product_tool.search_products()`
- `refund_processor` → *Coming soon*
- `payment_info` → *Coming soon*

**Caching Strategy:**
- Tool results are cached in the context
- No duplicate DB queries for same user in same conversation
- Results formatted for LLM readability

### 6. Context Builder

**File:** `ai_service.py` → `build_context(db, conversation, tool_data)`

**Context Structure:**
```
=== CONVERSATION CONTEXT ===
SUMMARY:
{Cached conversation summary}

CHAT HISTORY:
{Last 5 messages}

=== DATABASE RESULTS ===
{Formatted tool data}
```

**Data Formatting:**
- `Order` - Show order code, status, total, items
- `Product` - Show name, price, category, availability
- Rich formatting for LLM readability

### 7. LLM Response Generator

**File:** `agent.py` → `generate_response(message, context, intent)`

**Features:**
- System prompt emphasizes context-only responses
- Forbids hallucination
- Includes intent for prompt tuning
- Temperature: 0.3 (low creativity, factual)
- Max tokens: 512
- **Leading Questions:** Automatically includes 1-2 follow-up questions

**System Prompt Template:**
```
You are a professional ecommerce customer support agent.

INSTRUCTIONS:
1. Use ONLY the provided context if available
2. Be concise, helpful, and accurate
3. Do NOT hallucinate or make up data
4. At the end, ask 1-2 leading questions to clarify their need or suggest next steps
5. Be friendly and professional
6. Current intent: {intent}

[Context provided here]

RESPONSE GUIDELINES:
- Answer their question directly
- If data is missing, ask for clarification
- End with helpful follow-up questions
- Keep response under 150 words
```

---

## Message Type Detection

**File:** `ai_service.py` → `_determine_message_type()`

### First-Time Message
- Detected when `message_count == 1` (only user message just saved)
- Response: Static greeting with categories
- No LLM involved

### Guardrail Rejection
- When `guardrail_result["is_valid"] == False`
- Response: Default message based on rejection reason
- No further processing

### Regular Message
- All other cases
- Full workflow: Intent → Tool → Context → LLM

---

## Error Handling

### Graceful Degradation
- **Tool data missing?** → LLM provides general guidance
- **LLM timeout?** → Returns FALLBACK_REPLY to user
- **Invalid intent?** → Falls back to `general_support`

### Fallback Reply
```
"Sorry, I'm having trouble right now. Please try again in a moment."
```

---

## Integration Points

### Existing Systems (No Changes Required)
- ✓ `models/` - No schema changes needed
- ✓ `api/webhook.py` - Already calls `process_whatsapp_message`
- ✓ `tasks/message_tasks.py` - Already uses `handle_message()`
- ✓ Twilio integration - Already sends replies

### New Features Added
- ✓ Guardrail layer with security checks
- ✓ First-time greeting detection
- ✓ Multi-category intent classification
- ✓ Tool selector framework
- ✓ Structured context building
- ✓ Enhanced LLM prompting with leading questions

---

## Example Flow: Order Query

### User sends: "Where is my order ORD123"

**Step 1: Guardrails**
```
Message: "Where is my order ORD123"
Guardrails check: "order" keyword found ✓
Result: is_valid = True
```

**Step 2: First-time check**
```
Message count > 1: False (skip greeting)
```

**Step 3: Intent Classification**
```
Keywords: "order" found
Intent: "order_query"
```

**Step 4: Tool Selection**
```
Intent: "order_query"
Tool selected: "order_lookup"
Needs DB: Yes
```

**Step 5: DB Execution**
```
Tool: execute_order_lookup()
Result: Order data found (status, items, total)
```

**Step 6: Context Building**
```
Summary: "Customer asking about orders"
Chat History: "User: Where is my order ORD123"
Database Result: [Order details formatted]
```

**Step 7: LLM Response**
```
System: "Use context, include follow-up questions"
User: "Where is my order ORD123"
Context: [Formatted order data]
Response: "Your order ORD123 is in transit. 
Expected delivery: tomorrow. 
Would you like tracking updates, or do you have concerns about the delivery?"
```

**Reply sent to user:**
```
Your order ORD123 is in transit. Expected delivery: tomorrow. 
Would you like tracking updates, or do you have concerns about the delivery?
```

---

## Example Flow: Out-of-Scope Query

### User sends: "What's the meaning of life?"

**Step 1: Guardrails**
```
Message: "What's the meaning of life?"
Keywords: No store-related keywords found
Result: is_valid = False, reason = "Out of scope"
```

**Step 2: Rejection Handling**
```
Type: GUARDRAIL_REJECT
Reply: "I'm here to help with store-related queries only! 🏪
         I can assist with: [categories list]"
```

**No LLM involved - instant response**

---

## Configuration & Customization

### Guardrail Keywords
Edit in `agent.py` → `apply_guardrails()`:
```python
store_keywords = [
    "order", "product", "price", "refund", "cancel", ...
]
harmful_patterns = ["hack", "crack", "attack", ...]
```

### Intent Categories
Edit in `agent.py` → `classify_intent()` method to add new categories.

### Tool Selection
Edit in `agent.py` → `select_tool()` to map new tools.

### LLM Behavior
Edit in `agent.py` → `generate_response()` system prompt.

---

## Performance Considerations

### No LLM for:
- ✓ First-time greetings (saves API calls)
- ✓ Guardrail rejections (saves API calls)
- ✓ Intent classification (keyword-based)
- ✓ Tool selection (rule-based)

### LLM Only for:
- ✓ Final response generation (once per valid message)

### DB Caching:
- Tool results cached in context
- No duplicate queries
- Summary cached in conversation model

---

## Testing Checklist

- [ ] Test first-time user greeting
- [ ] Test guardrail with off-topic query
- [ ] Test order lookup flow
- [ ] Test product search flow
- [ ] Test LLM response with leading questions
- [ ] Test error handling (DB down)
- [ ] Test Celery task execution
- [ ] Test message persistence

---

## Future Enhancements

1. **Advanced Intent Classifier** - Use LLM for complex intent detection
2. **Multi-turn Conversations** - Track conversation state across turns
3. **Tool Chaining** - Chain multiple tools for complex queries
4. **Refund Tool** - Implement refund_processor
5. **Payment Tool** - Implement payment_info
6. **User Feedback Loop** - Track response quality
7. **Analytics Dashboard** - Monitor support metrics

