import os
import time
from typing import Dict, Any, Tuple
from audit.logger import audit_logger

SPEND_LIMIT_CAP = float(os.getenv("SPEND_LIMIT_CAP", "5000.0"))

# In-memory record of recent checkouts for idempotency checking (product_id + buyer -> timestamp)
RECENT_CHECKOUTS: Dict[str, float] = {}
IDEMPOTENCY_WINDOW_SECONDS = 300  # 5 minutes


class GuardrailException(Exception):
    """Exception raised when an agent guardrail policy is violated."""
    pass


def check_spend_limit(amount: float, quantity: int = 1, cap: float = SPEND_LIMIT_CAP) -> Tuple[bool, str]:
    """Ensure total checkout amount does not exceed the allowed spend limit cap."""
    total_value = amount * quantity
    if total_value > cap:
        msg = f"Order total ₹{total_value:.2f} exceeds spend limit cap of ₹{cap:.2f}. Human confirmation required."
        audit_logger.log_event(
            event_type="SPEND_GUARDRAIL",
            tool_name="check_spend_limit",
            inputs={"amount": amount, "quantity": quantity, "total_value": total_value, "cap": cap},
            outputs={"passed": False, "message": msg},
            reasoning="Total order value exceeds auto-approval spending cap",
            status="BLOCKED"
        )
        return False, msg
        
    return True, f"Order total ₹{total_value:.2f} is within cap limit ₹{cap:.2f}."


def verify_stock_gate(product: Dict[str, Any], requested_qty: int = 1) -> Tuple[bool, str]:
    """Verify stock availability immediately before checkout initiation."""
    current_stock = product.get("stock", 0)
    if current_stock < requested_qty:
        msg = (
            f"Stock check failed for '{product.get('name')}'. "
            f"Requested: {requested_qty}, Available: {current_stock}."
        )
        audit_logger.log_event(
            event_type="AVAILABILITY_CHECK",
            tool_name="verify_stock_gate",
            inputs={"product_id": product.get("product_id"), "requested_qty": requested_qty},
            outputs={"passed": False, "available_stock": current_stock, "message": msg},
            reasoning="Stock availability gate rejected out-of-stock item checkout",
            status="BLOCKED"
        )
        return False, msg

    return True, f"Stock verified: {current_stock} available."


def check_idempotency(product_id: str, buyer_id: str = "guest_buyer") -> Tuple[bool, str]:
    """Prevent duplicate orders for the same product + buyer within idempotency window."""
    key = f"{buyer_id}:{product_id}"
    now = time.time()
    
    if key in RECENT_CHECKOUTS:
        last_time = RECENT_CHECKOUTS[key]
        if now - last_time < IDEMPOTENCY_WINDOW_SECONDS:
            remaining = int(IDEMPOTENCY_WINDOW_SECONDS - (now - last_time))
            msg = f"Duplicate checkout detected for item {product_id}. Please wait {remaining} seconds before re-ordering."
            audit_logger.log_event(
                event_type="IDEMPOTENCY_GUARD",
                tool_name="check_idempotency",
                inputs={"product_id": product_id, "buyer_id": buyer_id},
                outputs={"passed": False, "message": msg},
                reasoning="Idempotency guard detected duplicate order attempt in 5 min window",
                status="BLOCKED"
            )
            return False, msg

    # Record checkout timestamp
    RECENT_CHECKOUTS[key] = now
    return True, "Idempotency check passed."


def verify_price_match(catalog_price: float, checkout_price: float) -> Tuple[bool, str]:
    """Ensure catalog display price matches actual checkout charge."""
    if abs(catalog_price - checkout_price) > 0.01:
        msg = f"Price mismatch alert! Catalog price (₹{catalog_price}) != Checkout price (₹{checkout_price})."
        audit_logger.log_event(
            event_type="PRICE_GUARDRAIL",
            tool_name="verify_price_match",
            inputs={"catalog_price": catalog_price, "checkout_price": checkout_price},
            outputs={"passed": False, "message": msg},
            reasoning="Price integrity check aborted payment due to price mismatch",
            status="BLOCKED"
        )
        return False, msg

    return True, "Price match verified."
