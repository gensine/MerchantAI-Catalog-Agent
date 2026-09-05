import os
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from api.schemas import (
    QueryCatalogRequest,
    QueryCatalogResponse,
    AvailabilityResponse,
    InitiateCheckoutRequest,
    InitiateCheckoutResponse,
    ProductResult
)
from ingest.ingest import ingest_catalog
from ingest.vector_store import catalog_store
from agent.tools import (
    tool_search_catalog,
    tool_check_availability,
    tool_initiate_checkout,
    tool_get_order_status
)
from agent.buyer_agent import buyer_agent
from audit.logger import audit_logger

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    sample_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demo", "sample_catalog.csv")
    if os.path.exists(sample_path):
        ingest_catalog(source=sample_path, merchant_id="rzp_merchant_001")
    yield

app = FastAPI(
    title="MerchantAI Catalog Agent API",
    description="ACP/AP2 aligned catalog ingestion, hybrid query, and agentic checkout REST API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "MerchantAI Catalog Agent", "version": "1.0.0"}


@app.post("/ingest", summary="Ingest catalog CSV, PDF, or URL")
async def ingest_endpoint(
    merchant_id: str = Form("rzp_merchant_001"),
    source_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """Upload catalog CSV/PDF file or provide URL for automated ingestion & vector indexing."""
    if file:
        file_bytes = await file.read()
        filename = file.filename or "upload.csv"
        # Save temp file
        temp_path = os.path.join(os.path.dirname(__file__), f"temp_{filename}")
        with open(temp_path, "wb") as f:
            f.write(file_bytes)
        try:
            res = ingest_catalog(source=temp_path, merchant_id=merchant_id)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        return res
    elif source_url:
        return ingest_catalog(source=source_url, merchant_id=merchant_id)
    else:
        raise HTTPException(status_code=400, detail="Either file upload or source_url must be provided.")


@app.post("/catalog/query", response_model=QueryCatalogResponse, summary="ACP/AP2 Aligned Hybrid Vector Catalog Search")
def query_catalog(payload: QueryCatalogRequest):
    """Execute natural language or structured search query across indexed merchant catalog."""
    res = tool_search_catalog(
        query=payload.query,
        merchant_id=payload.merchant_id,
        max_results=payload.max_results,
        max_price=payload.max_price,
        category=payload.category,
        cod_only=payload.cod_only,
        in_stock_only=payload.in_stock_only
    )
    return QueryCatalogResponse(**res)


@app.get("/catalog/{merchant_id}", summary="Get Full Machine-Readable Catalog")
def get_full_catalog(merchant_id: str):
    """Retrieve full product list for a specific merchant."""
    products = catalog_store.get_all(merchant_id=merchant_id)
    return {
        "status": "success",
        "merchant_id": merchant_id,
        "count": len(products),
        "products": products
    }


@app.get("/product/{product_id}/availability", response_model=AvailabilityResponse, summary="Real-time Availability & Stock Gate")
def check_product_availability(product_id: str, merchant_id: str = Query("rzp_merchant_001")):
    """Check stock level and variant options before purchase initiation."""
    res = tool_check_availability(product_id=product_id, merchant_id=merchant_id)
    return AvailabilityResponse(**res)


@app.post("/checkout/initiate", response_model=InitiateCheckoutResponse, summary="Initiate Razorpay Test Checkout")
def initiate_checkout_endpoint(payload: InitiateCheckoutRequest):
    """Trigger Razorpay test checkout with money-action guardrail checks."""
    res = tool_initiate_checkout(
        product_id=payload.product_id,
        quantity=payload.quantity,
        merchant_id=payload.merchant_id,
        buyer_name=payload.buyer_name,
        buyer_email=payload.buyer_email
    )
    if res.get("status") == "rejected_by_guardrail":
        raise HTTPException(status_code=422, detail=res)
    if res.get("status") == "failed":
        raise HTTPException(status_code=404, detail=res)
    return InitiateCheckoutResponse(**res)


@app.post("/agent/buy", summary="AI Buyer Agent Intent Completion")
def agent_buy_intent(
    intent: str = Form(...),
    merchant_id: str = Form("rzp_merchant_001"),
    buyer_email: str = Form("buyer@agentic-commerce.ai")
):
    """Run AI Buyer Agent loop: Intent -> Search -> Stock Gate -> Razorpay Test Checkout -> Audit."""
    buyer_agent.merchant_id = merchant_id
    res = buyer_agent.process_intent(intent_text=intent, buyer_email=buyer_email)
    return res


@app.get("/checkout/pay", response_class=HTMLResponse, summary="Interactive Razorpay Test Checkout Page")
def razorpay_checkout_page(order_id: str = "order_test_123", amount: float = 1299.0, product: str = "Indigo Cotton Kurta"):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Razorpay Test Checkout Simulator</title>
        <style>
            body {{
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                background: #0f172a;
                color: #f8fafc;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
            }}
            .checkout-box {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 16px;
                width: 420px;
                box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);
                overflow: hidden;
            }}
            .box-header {{
                background: linear-gradient(135deg, #0284c7, #2563eb);
                padding: 20px;
                text-align: center;
            }}
            .box-header h2 {{ margin: 0; font-size: 18px; color: #fff; }}
            .box-header p {{ margin: 4px 0 0; font-size: 12px; opacity: 0.9; color: #e0f2fe; }}
            .test-banner {{
                background: #f59e0b;
                color: #78350f;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                text-align: center;
                padding: 4px;
                letter-spacing: 0.5px;
            }}
            .box-body {{ padding: 24px; }}
            .price-tag {{
                font-size: 28px;
                font-weight: 800;
                color: #38bdf8;
                margin: 12px 0;
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                font-size: 13px;
                margin-bottom: 8px;
                color: #94a3b8;
            }}
            .detail-value {{ color: #f1f5f9; font-weight: 600; }}
            .btn-pay {{
                width: 100%;
                padding: 14px;
                background: #10b981;
                border: none;
                border-radius: 8px;
                color: #fff;
                font-size: 15px;
                font-weight: 700;
                cursor: pointer;
                margin-top: 16px;
                transition: background 0.2s;
            }}
            .btn-pay:hover {{ background: #059669; }}
            .success-screen {{
                display: none;
                text-align: center;
                padding: 20px 0;
            }}
            .checkmark {{
                width: 60px;
                height: 60px;
                background: #10b981;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 32px;
                margin: 0 auto 16px;
            }}
        </style>
    </head>
    <body>
        <div class="checkout-box">
            <div class="test-banner">⚠️ Razorpay Test Mode Simulator</div>
            <div class="box-header">
                <h2>MerchantAI Store</h2>
                <p>Razorpay AI Buildathon 2026 Test Gateway</p>
            </div>
            <div class="box-body">
                <div id="payment-form">
                    <div style="font-size: 13px; color: #94a3b8;">Paying for:</div>
                    <div style="font-size: 16px; font-weight: 700; margin-top: 2px;">{product}</div>
                    
                    <div class="price-tag">₹{amount:,.2f}</div>

                    <div style="border-top: 1px solid #334155; padding-top: 12px; margin-top: 12px;">
                        <div class="detail-row">
                            <span>Order ID:</span>
                            <span class="detail-value" style="font-family: monospace;">{order_id}</span>
                        </div>
                        <div class="detail-row">
                            <span>Payment Methods:</span>
                            <span class="detail-value">UPI / Cards / NetBanking</span>
                        </div>
                        <div class="detail-row">
                            <span>Status:</span>
                            <span class="detail-value" style="color: #f59e0b;">Pending Payment</span>
                        </div>
                    </div>

                    <button class="btn-pay" onclick="completePayment()">Simulate Successful Razorpay Payment →</button>
                </div>

                <div id="success-screen" class="success-screen">
                    <div class="checkmark">✓</div>
                    <h3 style="color: #34d399; margin-bottom: 8px;">Payment Successful!</h3>
                    <p style="font-size: 13px; color: #94a3b8;">Razorpay Payment ID: <code style="color: #fff;">pay_test_{order_id[-8:]}</code></p>
                    <p style="font-size: 12px; color: #64748b; margin-top: 12px;">Transaction logged to MerchantAI Audit Trail.</p>
                    <button class="btn-pay" style="background: #3b82f6; margin-top: 16px;" onclick="window.close()">Close Window</button>
                </div>
            </div>
        </div>

        <script>
            function completePayment() {{
                document.getElementById('payment-form').style.display = 'none';
                document.getElementById('success-screen').style.display = 'block';
            }}
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/audit/logs", summary="View Structured Audit Trail Logs")
def get_audit_logs():
    """Retrieve append-only audit trail logs for transparency and auditing."""
    logs = audit_logger.get_all_logs()
    summary = audit_logger.generate_summary()
    return {
        "status": "success",
        "log_count": len(logs),
        "logs": logs,
        "summary": summary
    }


# Mount Static Web Directory
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(WEB_DIR):
    app.mount("/dashboard", StaticFiles(directory=WEB_DIR, html=True), name="web")

@app.get("/", response_class=HTMLResponse)
def root_redirect():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>MerchantAI Catalog Agent API</h1><p>Visit <a href='/docs'>/docs</a> for API documentation or <a href='/dashboard'>/dashboard</a> for Web UI.</p>"
