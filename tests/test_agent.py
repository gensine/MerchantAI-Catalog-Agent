import pytest
from agent.buyer_agent import buyer_agent
from agent.tools import tool_initiate_checkout
from audit.logger import audit_logger


def test_agent_intent_success_flow():
    intent = "Order 1 Indigo Cotton Chikankari Kurta for me"
    res = buyer_agent.process_intent(intent_text=intent, buyer_email="test_buyer@agent.ai")
    assert res["status"] == "confirmed"
    assert "order_id" in res
    assert "payment_link" in res
    assert len(res["steps"]) >= 4


def test_agent_out_of_stock_graceful_handling():
    # Item P008 (Ceramic Coffee Mug) has stock=0 in sample catalog
    intent = "Buy Ceramic Coffee Mug Set of 2"
    res = buyer_agent.process_intent(intent_text=intent, buyer_email="test_buyer@agent.ai")
    assert res["status"] == "out_of_stock"
    assert "out_of_stock_item" in res
    assert res["out_of_stock_item"]["stock"] == 0


def test_spend_limit_cap_guardrail():
    # Attempting to order high value item exceeding default 5000 limit
    res = tool_initiate_checkout(
        product_id="P003",
        quantity=2,  # 4999 * 2 = 9998 > 5000 cap
        merchant_id="rzp_merchant_001",
        buyer_email="high_spender@agent.ai"
    )
    assert res["status"] == "rejected_by_guardrail"
    assert res["guardrail"] == "SPEND_LIMIT_CAP"


def test_audit_trail_logging():
    logs = audit_logger.get_all_logs()
    assert isinstance(logs, list)
    assert len(logs) > 0
    latest = logs[-1]
    assert "event_id" in latest
    assert "timestamp" in latest
    assert "event_type" in latest
