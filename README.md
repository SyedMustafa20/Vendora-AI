# Vendora AI — WhatsApp AI Customer Support System

Vendora AI is a **production-style AI customer support and ecommerce automation system** that integrates WhatsApp messaging with intelligent AI agents, tool-based reasoning, and a simulated ecommerce backend.

It demonstrates how modern LLM-based systems are built using **FastAPI, Celery, Redis, PostgreSQL, and OpenRouter LLMs**, combined with a real-world conversational workflow.

---

# Features

## 🤖 AI Customer Support Agent
- Handles WhatsApp customer queries via Twilio
- Understands intent using structured classification
- Uses tool-based reasoning before responding
- Generates human-like responses using LLM

---

## Smart Agent Workflow
The system follows a strict multi-stage pipeline:

1. **Guardrail Layer**
   - Filters irrelevant / unsafe queries
   - Ensures only ecommerce-related messages are processed

2. **Intent Understanding**
   - Detects:
     - Order queries
     - Product inquiries
     - Refund/cancellation requests
     - General queries

3. **Tool Selection Layer**
   - AI selects appropriate backend tool:
     - Order lookup tool
     - Product search tool

4. **Database Retrieval**
   - Fetches structured data from PostgreSQL:
     - Orders
     - Products
     - Customer info

5. **Context Injection**
   - Cached + structured data is injected into prompt

6. **LLM Response Generation**
   - OpenRouter LLM generates final response
   - Response is contextual and data-grounded

---

## Ecommerce Simulation System
This project simulates a real ecommerce backend with:

- Products table (catalog)
- Orders table (customer orders)
- Order items table
- Users/customers table

Used to simulate real-world store operations without external APIs.

---

## Asynchronous Architecture
- Celery handles background processing
- Redis is used for:
  - Task queue
  - Conversation caching
- Prevents webhook blocking (Twilio-safe architecture)

---

## WhatsApp Integration
- Twilio WhatsApp API used for messaging
- Incoming messages trigger backend pipeline
- Responses are automatically sent back to user

---

## Admin Dashboard
Built with Vite + React + Tailwind

Admins can:
- View conversations in real-time
- Adjust AI behavior:
  - System prompt
  - Temperature
  - Response style
- Monitor customer interactions

---

## Authentication System
- Custom JWT authentication system
- Role-based access:
  - Admin
  - Client (store owner)
- Secure API access for dashboard operations

---

# System Architecture

```text
WhatsApp User
     ↓
Twilio Webhook (FastAPI)
     ↓
Redis Queue
     ↓
Celery Worker
     ↓
AI Guardrails Layer
     ↓
Intent Detection Layer
     ↓
Tool Selection (AI-assisted routing)
     ↓
PostgreSQL Data Fetch
     ↓
Redis Context Cache
     ↓
OpenRouter LLM
     ↓
Final Response
     ↓
Twilio → WhatsApp User

---
#  Tech Stack

## Backend
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Redis
- Celery
- Custom JWT Authentication

## AI Layer
- OpenRouter LLM API
- Prompt-engineered agent system
- Tool-based execution pipeline
- Temperature-controlled generation

## Frontend
- React (Vite)
- Tailwind CSS
- Admin dashboard UI

## Messaging
- Twilio WhatsApp API

---
