import json
from typing import Dict, Any, List, Optional
from ingest.vector_store import catalog_store
from agent.guardrails import check_spend_limit, verify_stock_gate, check_idempotency, verify_price_match
from agent.razorpay_client import razorpay_wrapper
from audit.logger import audit_logger


def tool_search_catalog(
    query: str,
    merchant_id: str = "rzp_merchant_001",
    max_results: int = 5,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    cod_only: bool = False,
    in_stock_only: bool = False
) -> Dict[str, Any]:
    """Search catalog for product matches using vector similarity + metadata filters."""
    results = catalog_store.query(
        merchant_id=merchant_id,
        query_text=query,
        max_results=max_results,
        max_price=max_price,
        category=category,
        cod_only=cod_only,
        in_stock_only=in_stock_only
    )

    audit_logger.log_event(
        event_type="QUERY",
        tool_name="search_catalog",
        inputs={"merchant_id": merchant_id, "query": query, "max_results": max_results},
        outputs={"match_count": len(results), "top_matches": [r["name"] for r in results[:3]]},
        reasoning=f"Agent executed catalog query for '{query}'. Found {len(results)} matches.",
        status="SUCCESS",
        merchant_id=merchant_id
    )

    agent_notes = f"{len(results)} matches found for '{query}'."
    if results:
        top = results[0]
        agent_notes += f" Top match is '{top['name']}' at ₹{top['price']} (Stock: {top['stock']})."

    return {
        "status": "success",
        "merchant_id": merchant_id,
        "query": query,
        "count": len(results),
        "results": results,
        "agent_notes": agent_notes
    }


def tool_check_availability(product_id: str, merchant_id: str = "rzp_merchant_001") -> Dict[str, Any]:
    """Check stock and variant availability for a specific product."""
    product = catalog_store.get_by_id(merchant_id=merchant_id, product_id=product_id)
    if not product:
        res = {
            "product_id": product_id,
            "name": "Unknown",
            "available": False,
            "stock": 0,
            "message": f"Product ID '{product_id}' not found in merchant catalog."
        }
        audit_logger.log_event(
            event_type="AVAILABILITY_CHECK",
            tool_name="check_availability",
            inputs={"product_id": product_id},
            outputs=res,
            reasoning="Product lookup returned 404 Not Found",
            status="NOT_FOUND",
            merchant_id=merchant_id
        )
        return res

    is_available = product.get("stock", 0) > 0
    msg = f"Item '{product['name']}' is in stock ({product['stock']} units available)." if is_available else f"Item '{product['name']}' is currently out of stock."

    res = {
        "product_id": product["product_id"],
        "name": product["name"],
        "available": is_available,
        "stock": product["stock"],
        "price": product["price"],
        "variants": product.get("variants", {}),
        "cod_available": product.get("cod_available", True),
        "message": msg
    }

    audit_logger.log_event(
        event_type="AVAILABILITY_CHECK",
        tool_name="check_availability",
        inputs={"product_id": product_id},
        outputs=res,
        reasoning=f"Verified availability for {product['name']}: {is_available} (Stock: {product['stock']})",
        status="SUCCESS",
        merchant_id=merchant_id
    )

    return res


def tool_initiate_checkout(
    product_id: str,
    quantity: int = 1,
    merchant_id: str = "rzp_merchant_001",
    buyer_name: str = "AI Buyer",
    buyer_email: str = "buyer@agentic-commerce.ai"
) -> Dict[str, Any]:
    """Trigger Razorpay test checkout with money action guardrails (spend limit, stock gate, idempotency)."""
    # 1. Product Lookup
    product = catalog_store.get_by_id(merchant_id=merchant_id, product_id=product_id)
    if not product:
        return {
            "status": "failed",
            "error": "PRODUCT_NOT_FOUND",
            "message": f"Product ID {product_id} not found."
        }

    # 2. Guardrail 1: Stock Availability Gate
    stock_passed, stock_msg = verify_stock_gate(product, requested_qty=quantity)
    if not stock_passed:
        return {
            "status": "rejected_by_guardrail",
            "guardrail": "STOCK_GATE",
            "message": stock_msg
        }

    # 3. Guardrail 2: Spend Limit Cap Check
    total_amount = product["price"] * quantity
    spend_passed, spend_msg = check_spend_limit(product["price"], quantity=quantity)
    if not spend_passed:
        return {
            "status": "rejected_by_guardrail",
            "guardrail": "SPEND_LIMIT_CAP",
            "message": spend_msg
        }

    # 4. Guardrail 3: Idempotency Check
    idem_passed, idem_msg = check_idempotency(product_id=product_id, buyer_id=buyer_email)
    if not idem_passed:
        return {
            "status": "rejected_by_guardrail",
            "guardrail": "IDEMPOTENCY_GUARD",
            "message": idem_msg
        }

    # 5. Create Razorpay Test Order
    rzp_res = razorpay_wrapper.create_order(
        amount_inr=total_amount,
        product_name=product["name"],
        product_id=product_id
    )

    # 6. Log Audit Trail Event
    log_record = audit_logger.log_event(
        event_type="CHECKOUT",
        tool_name="initiate_checkout",
        inputs={
            "merchant_id": merchant_id,
            "product_id": product_id,
            "quantity": quantity,
            "buyer_name": buyer_name,
            "buyer_email": buyer_email
        },
        outputs={
            "order_id": rzp_res["order_id"],
            "amount": total_amount,
            "payment_link": rzp_res["payment_link"]
        },
        reasoning=f"Initiated Razorpay test checkout for {quantity}x {product['name']} = ₹{total_amount:.2f}",
        status="SUCCESS",
        merchant_id=merchant_id
    )

    return {
        "status": "success",
        "order_id": rzp_res["order_id"],
        "amount": total_amount,
        "currency": "INR",
        "payment_link": rzp_res["payment_link"],
        "product_name": product["name"],
        "agent_notes": f"Razorpay test payment link created for {product['name']}. Order ID: {rzp_res['order_id']}",
        "audit_event_id": log_record["event_id"]
    }


def tool_get_order_status(order_id: str) -> Dict[str, Any]:
    """Poll for order status and payment confirmation."""
    status_res = razorpay_wrapper.verify_payment_status(order_id)
    audit_logger.log_event(
        event_type="ORDER_STATUS_POLL",
        tool_name="get_order_status",
        inputs={"order_id": order_id},
        outputs=status_res,
        reasoning=f"Polled Razorpay order status for {order_id}: {status_res['status']}",
        status="SUCCESS"
    )
    return status_res
