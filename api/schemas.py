from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryCatalogRequest(BaseModel):
    merchant_id: str = Field(default="rzp_merchant_001", description="Merchant unique ID")
    query: str = Field(..., description="Natural language or structured query string")
    max_results: int = Field(default=5, ge=1, le=20, description="Max product items to return")
    max_price: Optional[float] = Field(default=None, description="Max budget cap filter in INR")
    min_price: Optional[float] = Field(default=None, description="Min price filter in INR")
    category: Optional[str] = Field(default=None, description="Product category filter")
    cod_only: bool = Field(default=False, description="Filter only COD eligible items")
    in_stock_only: bool = Field(default=False, description="Filter only items currently in stock")


class ProductResult(BaseModel):
    product_id: str
    name: str
    description: str
    price: float
    category: str
    stock: int
    variants: Dict[str, Any] = {}
    cod_available: bool = True
    dispatch_time: str = "1-2 business days"
    confidence_score: float = Field(default=0.90, description="Relevance score (0.0 to 1.0)")
    checkout_url: str


class QueryCatalogResponse(BaseModel):
    status: str = "success"
    merchant_id: str
    query: str
    count: int
    results: List[ProductResult]
    agent_notes: str


class AvailabilityResponse(BaseModel):
    product_id: str
    name: str
    available: bool
    stock: int
    variants: Dict[str, Any] = {}
    cod_available: bool = True
    message: str


class InitiateCheckoutRequest(BaseModel):
    merchant_id: str = Field(default="rzp_merchant_001")
    product_id: str
    quantity: int = Field(default=1, ge=1)
    variant_selection: Optional[Dict[str, str]] = None
    buyer_name: str = Field(default="AI Agent Buyer")
    buyer_email: str = Field(default="buyer@agentic-commerce.ai")
    buyer_phone: str = Field(default="+919876543210")


class InitiateCheckoutResponse(BaseModel):
    status: str
    order_id: str
    amount: float
    currency: str = "INR"
    payment_link: str
    product_name: str
    agent_notes: str
    audit_event_id: str
