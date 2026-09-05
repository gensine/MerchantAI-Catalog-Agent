# 5 Failure Modes & How the MerchantAI Catalog Agent Handles Each

This document details the 5 explicit failure modes and money-action guardrail mechanisms built into the MerchantAI Catalog Agent.

---

## 1. Out-of-Stock Item Requested Mid-Flow
- **Scenario:** An AI buyer requests a product that went out of stock after initial search indexing (e.g. `P008` Ceramic Coffee Mugs).
- **Handling:** Immediately before checkout initiation, the agent invokes `tool_check_availability()`. If `stock <= 0`, the stock gate blocks checkout, logs a `BLOCKED` event to the audit trail, and scans the remaining search results for in-stock alternatives to recommend to the user.

## 2. Order Total Exceeds Spend Limit Cap
- **Scenario:** An agent attempts to auto-checkout an expensive order (e.g., 2x Handloom Silk Sarees = ₹9,998) exceeding the configured cap (₹5,000).
- **Handling:** `check_spend_limit()` evaluates total order value (`price * quantity`). If it exceeds `SPEND_LIMIT_CAP`, execution is halted, status is set to `rejected_by_guardrail`, and human confirmation is requested.

## 3. Duplicate Order Attempt (Idempotency Violation)
- **Scenario:** Network retry or agent bug submits the same product purchase intent for the same buyer twice within 5 minutes.
- **Handling:** `check_idempotency()` tracks buyer + product hashes and timestamps. Subsequent requests within 300 seconds are rejected with a warning to wait before re-ordering.

## 4. Price Mismatch Between Catalog & Checkout API
- **Scenario:** The catalog display price shows ₹1,299, but checkout payload attempts to charge ₹1,499.
- **Handling:** `verify_price_match()` compares catalog item price with total payload amount. If discrepancy > ₹0.01, payment generation is aborted immediately and logged as `BLOCKED`.

## 5. Malformed Input / Unstructured Catalog Formats
- **Scenario:** Merchant uploads a PDF or CSV with non-standard column headers (e.g. "Item Name", "Cost Price", "MRP", "Rupees").
- **Handling:** `normalizer.py` uses heuristic matching to standardize heterogeneous field names into canonical `price`, `stock`, `variants`, and `cod_available` schema fields.
