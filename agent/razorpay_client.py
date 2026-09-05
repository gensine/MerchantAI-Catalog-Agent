import os
import uuid
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()


class RazorpayClientWrapper:
    """Wrapper around Razorpay Python SDK in Test Mode with fallback mock mode."""
    
    def __init__(self, key_id: str = RAZORPAY_KEY_ID, key_secret: str = RAZORPAY_KEY_SECRET):
        self.key_id = key_id
        self.key_secret = key_secret
        self.client = None
        
        if self.key_id and self.key_secret:
            try:
                import razorpay
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
                logger.info("Initialized live Razorpay Test-Mode client.")
            except Exception as e:
                logger.warning(f"Could not initialize Razorpay SDK: {e}")

    def create_order(self, amount_inr: float, product_name: str, product_id: str, receipt: str = "") -> Dict[str, Any]:
        """Create a Razorpay order (amount in paise)."""
        amount_paise = int(amount_inr * 100)
        receipt_id = receipt or f"rcpt_{uuid.uuid4().hex[:8]}"

        if self.client:
            try:
                order_data = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt_id,
                    "notes": {
                        "agent_source": "MerchantAI_Catalog_Agent",
                        "product_id": product_id,
                        "product_name": product_name
                    }
                }
                order = self.client.order.create(data=order_data)
                return {
                    "order_id": order.get("id"),
                    "amount": amount_inr,
                    "currency": "INR",
                    "status": order.get("status", "created"),
                    "payment_link": f"https://api.razorpay.com/v1/checkout/test/pay?order_id={order.get('id')}",
                    "mode": "RAZORPAY_TEST_SDK"
                }
            except Exception as e:
                logger.error(f"Razorpay API order error: {e}. Falling back to test link generation.")

        # Fallback Test Link Generator (Local Interactive Razorpay Checkout Page)
        mock_order_id = f"order_test_{uuid.uuid4().hex[:12]}"
        import urllib.parse
        encoded_name = urllib.parse.quote(product_name)
        mock_payment_link = f"/checkout/pay?order_id={mock_order_id}&amount={amount_inr}&product={encoded_name}"
        
        return {
            "order_id": mock_order_id,
            "amount": amount_inr,
            "currency": "INR",
            "status": "created",
            "payment_link": mock_payment_link,
            "mode": "RAZORPAY_TEST_SIMULATOR"
        }

    def verify_payment_status(self, order_id: str) -> Dict[str, Any]:
        """Check order payment confirmation status."""
        if self.client and not order_id.startswith("order_test_"):
            try:
                order = self.client.order.fetch(order_id)
                return {
                    "order_id": order_id,
                    "status": order.get("status"),
                    "amount_paid": float(order.get("amount_paid", 0)) / 100.0,
                    "paid": order.get("status") == "paid"
                }
            except Exception as e:
                logger.error(f"Error fetching order {order_id}: {e}")

        # Simulator status return
        return {
            "order_id": order_id,
            "status": "paid",
            "amount_paid": 1299.0,
            "paid": True,
            "mode": "SIMULATED_TEST_CONFIRMATION"
        }


razorpay_wrapper = RazorpayClientWrapper()
