import os
import json
import logging
from typing import Dict, Any, List

from agent.tools import (
    tool_search_catalog,
    tool_check_availability,
    tool_initiate_checkout,
    tool_get_order_status
)
from audit.logger import audit_logger

logger = logging.getLogger(__name__)


class AIBuyerAgent:
    """
    AI Buyer Agent for agentic commerce.
    Executes buyer intent: Intent → catalog query → shortlist → stock check → checkout → audit.
    """

    def __init__(self, merchant_id: str = "rzp_merchant_001"):
        self.merchant_id = merchant_id
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    def process_intent(self, intent_text: str, buyer_email: str = "buyer@agentic-commerce.ai") -> Dict[str, Any]:
        """Process user purchase intent end-to-end with reasoning & tool execution."""
        logger.info(f"Processing agent buyer intent: '{intent_text}'")
        
        step_logs = []

        # Step 1: Execute Catalog Query Tool
        step_logs.append({
            "step": 1,
            "action": "search_catalog",
            "description": f"Searching catalog for query extracted from intent: '{intent_text}'"
        })
        
        search_res = tool_search_catalog(
            query=intent_text,
            merchant_id=self.merchant_id,
            max_results=3
        )
        
        matches = search_res.get("results", [])
        if not matches:
            audit_logger.log_event(
                event_type="AGENT_DECISION",
                tool_name="process_intent",
                inputs={"intent": intent_text},
                outputs={"matched": False},
                reasoning="No product matches found in catalog. Terminated purchase workflow gracefully.",
                status="NO_MATCH",
                merchant_id=self.merchant_id
            )
            return {
                "status": "failed",
                "message": f"Sorry, no products matched your query: '{intent_text}'.",
                "steps": step_logs,
                "matches": []
            }

        top_product = matches[0]
        step_logs.append({
            "step": 2,
            "action": "select_top_match",
            "selected_product": top_product["name"],
            "product_id": top_product["product_id"],
            "price": top_product["price"],
            "confidence_score": top_product.get("confidence_score", 0.90)
        })

        # Step 2: Real-time Availability Check
        avail_res = tool_check_availability(
            product_id=top_product["product_id"],
            merchant_id=self.merchant_id
        )

        step_logs.append({
            "step": 3,
            "action": "check_availability",
            "available": avail_res.get("available", False),
            "stock": avail_res.get("stock", 0)
        })

        # Handle Out-of-Stock Edge Case
        if not avail_res.get("available", False) or avail_res.get("stock", 0) <= 0:
            # Check for alternative match in remaining search results
            alt_product = None
            if len(matches) > 1:
                for m in matches[1:]:
                    if m.get("stock", 0) > 0:
                        alt_product = m
                        break

            msg = f"The selected item '{top_product['name']}' is currently out of stock."
            if alt_product:
                msg += f" Suggested alternative in stock: '{alt_product['name']}' (₹{alt_product['price']})."

            audit_logger.log_event(
                event_type="AGENT_DECISION",
                tool_name="process_intent",
                inputs={"intent": intent_text, "product_id": top_product["product_id"]},
                outputs={"out_of_stock": True, "alternative": alt_product["name"] if alt_product else None},
                reasoning="Primary product out of stock. Agent handled failure mode gracefully.",
                status="OUT_OF_STOCK_HANDLED",
                merchant_id=self.merchant_id
            )

            return {
                "status": "out_of_stock",
                "message": msg,
                "out_of_stock_item": top_product,
                "alternative_item": alt_product,
                "steps": step_logs
            }

        # Step 3: Initiate Razorpay Checkout with Guardrails
        checkout_res = tool_initiate_checkout(
            product_id=top_product["product_id"],
            quantity=1,
            merchant_id=self.merchant_id,
            buyer_email=buyer_email
        )

        step_logs.append({
            "step": 4,
            "action": "initiate_checkout",
            "checkout_status": checkout_res.get("status"),
            "order_id": checkout_res.get("order_id"),
            "payment_link": checkout_res.get("payment_link")
        })

        if checkout_res.get("status") == "rejected_by_guardrail":
            return {
                "status": "blocked_by_guardrail",
                "guardrail": checkout_res.get("guardrail"),
                "message": checkout_res.get("message"),
                "steps": step_logs
            }

        # Step 4: Verify Order Status Confirmation
        order_id = checkout_res.get("order_id")
        status_res = tool_get_order_status(order_id)
        
        step_logs.append({
            "step": 5,
            "action": "get_order_status",
            "order_status": status_res.get("status")
        })

        return {
            "status": "confirmed",
            "message": f"Order for '{top_product['name']}' (₹{top_product['price']}) initiated successfully!",
            "order_id": order_id,
            "payment_link": checkout_res.get("payment_link"),
            "product": top_product,
            "steps": step_logs,
            "audit_trail_recorded": True
        }


buyer_agent = AIBuyerAgent()
