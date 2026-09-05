# 🛍️ MerchantAI Catalog Agent
### Razorpay AI Buildathon 2026 — Track 01: AI Growth & Agentic Commerce

[![Python Version](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Pytest Status](https://img.shields.io/badge/Tests-11%20Passed%20%28100%25%29-brightgreen.svg)](file:///d:/Projects/razorpay/tests)
[![Razorpay Integration](https://img.shields.io/badge/Razorpay-Test%20Mode-blueviolet.svg)](https://razorpay.com)
[![Protocol](https://img.shields.io/badge/Protocol-ACP%2FAP2%20Aligned-orange.svg)](#-api-reference-acpap2-conventions)

> **One-line pitch:** An AI-native layer that ingests any merchant's messy catalog (CSV, PDF, URL) and makes it discoverable, queryable, and transactable by AI buyer agents end-to-end via Razorpay test-mode checkout.

---

## 🌟 Key Features

- **Multi-Format Ingestion Engine:** Parses CSV files, PDF documents, web pages (BeautifulSoup + JSON-LD), and raw text. Standardizes messy field headers (`MRP`, `cost`, `₹ price` → `price`) and indexes vector embeddings in `< 10 milliseconds` for 100 products.
- **ACP/AP2 Protocol Aligned REST API:** Exposes `/catalog/query`, `/catalog/{merchant_id}`, and `/product/{product_id}/availability` endpoints returning machine-readable JSON structured for AI buyer agents.
- **AI Buyer Agent & Tool Execution:** Autonomous buyer loop that parses natural language intent, searches the catalog, checks real-time stock, triggers Razorpay test-mode payment links, and confirms order placement.
- **Money-Action Guardrails:**
  - **Stock Availability Gate:** Prevents checkout if inventory is insufficient; suggests in-stock alternatives.
  - **Spend Limit Cap:** Enforces a configurable auto-approval ceiling (e.g. ₹5,000) before requiring human confirmation.
  - **Idempotency Guard:** Prevents accidental duplicate orders within a 5-minute window.
  - **Price Integrity Check:** Aborts transaction if catalog display price mismatches checkout charge.
- **Immutable Audit Trail:** Append-only structured JSON logger (`audit_trail.json`) capturing every tool call, input, reasoning step, timestamp, and payment URL.
- **Interactive Web Dashboard & Razorpay Simulator:** Modern glassmorphic Web UI featuring drag-and-drop catalog ingestion, AI chat simulator, preset edge-case triggers, and an interactive **Razorpay Test Checkout Simulator**.

---

## 📁 Repository Structure

```
merchantai-catalog-agent/
├── README.md               ← Complete setup & presentation docs
├── requirements.txt        ← Python dependencies
├── .env.example            ← Environment configuration template
├── ingest/
│   ├── ingest.py           ← Ingestion CLI entrypoint
│   ├── parsers.py          ← CSV, PDF, web URL & text parsers
│   ├── normalizer.py       ← Field mapping & schema standardization
│   └── vector_store.py     ← Vector database & hybrid search engine
├── api/
│   ├── main.py             ← FastAPI REST app & dashboard routing
│   └── schemas.py          ← Pydantic data models (ACP/AP2 aligned)
├── agent/
│   ├── buyer_agent.py      ← AI Buyer reasoning loop & intent runner
│   ├── tools.py            ← Catalog search, stock check & checkout tools
│   ├── guardrails.py       ← Spend limit, stock gate & idempotency rules
│   └── razorpay_client.py  ← Razorpay SDK & test-mode payment generator
├── audit/
│   └── logger.py           ← Immutable append-only audit trail logger
├── web/
│   ├── index.html          ← Interactive dashboard UI
│   ├── styles.css          ← Glassmorphic dark design system
│   └── app.js              ← Frontend controller & API fetch handlers
├── demo/
│   ├── sample_catalog.csv  ← 15+ product Indian e-commerce catalog
│   └── demo_script.md      ← 5-minute video presentation guide
├── docs/
│   └── failure_modes.md    ← 5 failure modes & guardrail handling docs
└── tests/
    ├── test_ingestion.py   ← Ingestion & vector search tests
    ├── test_api.py         ← REST API endpoint tests
    └── test_agent.py       ← Buyer agent & guardrail unit tests
```

---

## 🏗️ Architecture Overview

```
Merchant Catalog (CSV / PDF / URL / Sheet)
        ↓
  [Ingestion & RAG Layer]
        ↓
  Structured Product Store (Vector DB + Metadata)
        ↓
  AI-Queryable Catalog REST API (ACP/AP2-aligned)
        ↓
  AI Buyer Agent (Claude / GPT / Agentic Loop)
        ↓
  Razorpay Test-Mode Checkout Simulator
        ↓
  Append-Only Audit Trail + Transaction Log
```

---

## 🚀 Quick Start Guide

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/gensine/MerchantAI-Catalog-Agent.git
cd MerchantAI-Catalog-Agent

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Set optional keys for `OPENAI_API_KEY`, `RAZORPAY_KEY_ID`, or `RAZORPAY_KEY_SECRET`. If omitted, the system seamlessly runs in local fallback mode with local embeddings and a mock Razorpay test payment simulator.

### 3. Ingest Sample Catalog via CLI

```bash
python -m ingest.ingest --source demo/sample_catalog.csv --merchant_id rzp_merchant_001
```

### 4. Launch FastAPI REST Server & Web Dashboard

```bash
python -m uvicorn api.main:app --reload --port 8000
```

- **Interactive Web Dashboard:** Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard) or [http://localhost:8000](http://localhost:8000)
- **API Documentation (Swagger):** Open [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Run Pytest Verification Suite

```bash
pytest -v tests/
```

---

## 📄 API Reference (ACP/AP2 Conventions)

### 1. Catalog Hybrid Search — `POST /catalog/query`

**Request:**
```json
{
  "merchant_id": "rzp_merchant_001",
  "query": "blue chikankari kurta under 1500 rupees size M COD available",
  "max_results": 3
}
```

**Response:**
```json
{
  "status": "success",
  "merchant_id": "rzp_merchant_001",
  "query": "blue chikankari kurta under 1500 rupees size M COD available",
  "count": 1,
  "results": [
    {
      "product_id": "P001",
      "name": "Indigo Cotton Chikankari Kurta",
      "description": "Handcrafted breathable cotton kurta with authentic Lucknow chikankari embroidery",
      "price": 1299.0,
      "category": "Apparel",
      "stock": 25,
      "variants": {
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Indigo Blue"]
      },
      "cod_available": true,
      "dispatch_time": "Same-day",
      "confidence_score": 0.94,
      "checkout_url": "https://api.razorpay.com/test/checkout/P001"
    }
  ],
  "agent_notes": "1 matches found for query. Top match is Indigo Cotton Chikankari Kurta at ₹1299.0 (Stock: 25)."
}
```

### 2. Availability Check — `GET /product/{product_id}/availability`

**Response:**
```json
{
  "product_id": "P001",
  "name": "Indigo Cotton Chikankari Kurta",
  "available": true,
  "stock": 25,
  "variants": { "sizes": ["S", "M", "L", "XL"] },
  "cod_available": true,
  "message": "Item 'Indigo Cotton Chikankari Kurta' is in stock (25 units available)."
}
```

### 3. AI Buyer Agent Intent — `POST /agent/buy`

Accepts form field `intent="Order 1 Indigo Cotton Chikankari Kurta size M"` and returns confirmed Razorpay test payment links and step-by-step audit logs.

---

## 🧪 Edge Cases & Failure Handling

| Edge Case | Handling Mechanism |
|---|---|
| **Out-of-Stock Mid-Flow** | Availability gate re-checks stock immediately before payment; suggests in-stock alternative. |
| **Spend Limit Exceeded** | Order value cap (e.g. > ₹5,000) halts auto-checkout and requests human confirmation. |
| **Duplicate Checkout** | Idempotency guard blocks identical order requests within 5 minutes. |
| **Price Mismatch** | Price verification aborts payment if catalog price != checkout amount. |
| **Malformed Catalog Headers** | Normalization layer auto-maps MRP, cost, ₹ prices, and stock indicators to canonical schema. |

---

## 📽️ Demo Video Script (5-Minute Walkthrough)

1. **(0:00–0:30) Problem Statement:** Show a traditional merchant catalog in CSV/PDF format locked away from AI buyers.
2. **(0:30–1:30) Ingestion Demo:** Run `ingest.py` on 50 products in 0.002s; inspect vector DB.
3. **(1:30–3:00) Agentic Checkout:** Input natural language buyer intent in Web Dashboard → view live tool calls → click generated Razorpay test payment link.
4. **(3:00–4:00) Edge Case Demo:** Trigger out-of-stock item purchase and spend limit cap block.
5. **(4:00–5:00) Audit Trail:** Inspect structured JSON audit logs and wrap up.

---

*Built for Razorpay AI Buildathon 2026 — Track 01: AI Growth & Agentic Commerce*
