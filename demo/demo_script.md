# Pitch Video Demo Script — MerchantAI Catalog Agent
### Razorpay AI Buildathon 2026 — Track 01

## Video Duration: 5 Minutes

---

### Step 1 — Problem Statement (0:00–0:30)
- **Visual:** Show `demo/sample_catalog.csv` opened in Excel or VS Code.
- **Narrative:** "Millions of merchants on Razorpay have product catalogs locked inside CSVs, PDFs, or Google Sheets. These catalogs are invisible to AI buyers like Claude or GPT. If an AI buyer wants to discover, evaluate, and purchase products from these merchants, it currently can't."

---

### Step 2 — Ingestion & Vector RAG Demo (0:30–1:30)
- **Visual:** Run CLI ingestion command:
  ```bash
  python -m ingest.ingest --source demo/sample_catalog.csv --merchant_id rzp_merchant_001
  ```
- **Narrative:** "With MerchantAI Catalog Agent, a merchant uploads their catalog in any format. Our parser extracts products, normalizes messy headers, and embeds them into ChromaDB in under 10 milliseconds."
- **Visual:** Open Web Dashboard at `http://localhost:8000/dashboard` and switch to the **Catalog Ingestion & RAG** tab to view the live product grid.

---

### Step 3 — End-to-End AI Buyer Agent Checkout (1:30–3:00)
- **Visual:** Click **🤖 AI Buyer Agent** tab. Click preset trigger: *"Order 1 Indigo Cotton Chikankari Kurta for me"*.
- **Narrative:** "Now watch an AI buyer agent interact with this merchant catalog in natural language. The agent calls `search_catalog()`, selects the top match, checks availability via `check_availability()`, and initiates a test-mode Razorpay checkout."
- **Visual:** Show the green Razorpay Test Payment link button. Click the link to view the Razorpay checkout simulator.

---

### Step 4 — Edge Cases & Guardrails Demo (3:00–4:00)
- **Visual:** Click preset trigger: *"Buy Ceramic Coffee Mug Set of 2"*.
- **Narrative:** "What happens when an item is out of stock? The agent's stock gate detects 0 stock and suggests an in-stock alternative without crashing."
- **Visual:** Click preset trigger: *"Order 2 Handloom Silk Sarees"*.
- **Narrative:** "What if an agent tries to spend too much? Our spend limit cap blocks transactions exceeding ₹5,000 and requires human approval."

---

### Step 5 — Immutable Audit Trail & Wrap-up (4:00–5:00)
- **Visual:** Switch to **🛡️ Audit Trail & Guardrails** tab. Show the structured table of logs.
- **Narrative:** "Every single tool call, decision, stock check, and payment link is appended to an immutable JSON audit log. Razorpay merchants get complete transparency, control, and security as agentic commerce becomes a reality."
