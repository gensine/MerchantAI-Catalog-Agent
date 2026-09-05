import re
import uuid
from typing import Dict, Any, List


def normalize_product(raw: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    """
    Standardize raw item dictionary into canonical product object schema:
    - product_id (str)
    - name (str)
    - description (str)
    - price (float)
    - category (str)
    - stock (int)
    - variants (dict)
    - cod_available (bool)
    - dispatch_time (str)
    - checkout_url (str)
    """
    # 1. Product ID
    raw_keys = {str(k).lower().strip(): v for k, v in raw.items()}
    
    product_id = (
        raw_keys.get("product_id") or 
        raw_keys.get("id") or 
        raw_keys.get("sku") or 
        f"P{index+1:03d}"
    )
    product_id = str(product_id).strip()

    # 2. Name
    name = (
        raw_keys.get("product_name") or 
        raw_keys.get("name") or 
        raw_keys.get("title") or 
        raw_keys.get("item") or 
        f"Product {index+1}"
    )
    name = str(name).strip()

    # 3. Description
    description = (
        raw_keys.get("description") or 
        raw_keys.get("desc") or 
        raw_keys.get("details") or 
        raw_keys.get("summary") or 
        name
    )
    description = str(description).strip()

    # 4. Price normalization (handles ₹, Rs., INR, comma separators)
    price_val = 0.0
    raw_price = (
        raw_keys.get("price_inr") or 
        raw_keys.get("price") or 
        raw_keys.get("mrp") or 
        raw_keys.get("cost") or 
        raw_keys.get("amount") or 
        0
    )
    
    if isinstance(raw_price, (int, float)):
        price_val = float(raw_price)
    else:
        price_str = str(raw_price)
        match = re.search(r'[\d,]+(?:\.\d+)?', price_str)
        if match:
            try:
                price_val = float(match.group(0).replace(',', ''))
            except ValueError:
                price_val = 0.0

    # 5. Category
    category = (
        raw_keys.get("category") or 
        raw_keys.get("type") or 
        raw_keys.get("department") or 
        "General"
    )
    category = str(category).strip()

    # 6. Stock
    stock_val = 10  # default assumption if missing
    raw_stock = (
        raw_keys.get("stock_quantity") or 
        raw_keys.get("stock") or 
        raw_keys.get("quantity") or 
        raw_keys.get("qty") or 
        raw_keys.get("availability")
    )
    
    if raw_stock is not None:
        if isinstance(raw_stock, (int, float)):
            stock_val = int(raw_stock)
        elif isinstance(raw_stock, str):
            if raw_stock.lower() in ["out of stock", "no", "false", "0", "unavailable"]:
                stock_val = 0
            elif raw_stock.lower() in ["in stock", "yes", "true", "available"]:
                stock_val = 10
            else:
                stock_match = re.search(r'\d+', raw_stock)
                if stock_match:
                    stock_val = int(stock_match.group(0))

    # 7. Variants (Sizes, Colors)
    variants = {}
    sizes = raw_keys.get("sizes") or raw_keys.get("size")
    colors = raw_keys.get("colors") or raw_keys.get("color")
    
    if sizes:
        variants["sizes"] = [s.strip() for s in str(sizes).split(",") if s.strip()]
    if colors:
        variants["colors"] = [c.strip() for c in str(colors).split(",") if c.strip()]

    # 8. COD Availability
    raw_cod = raw_keys.get("cod_available") or raw_keys.get("cod")
    cod_available = True
    if raw_cod is not None:
        if isinstance(raw_cod, bool):
            cod_available = raw_cod
        elif isinstance(raw_cod, str):
            cod_available = raw_cod.lower() in ["true", "1", "yes", "y", "available"]

    # 9. Dispatch / Delivery
    dispatch_time = raw_keys.get("dispatch_time") or raw_keys.get("delivery") or "1-3 business days"

    return {
        "product_id": product_id,
        "name": name,
        "description": description,
        "price": price_val,
        "category": category,
        "stock": stock_val,
        "variants": variants,
        "cod_available": cod_available,
        "dispatch_time": str(dispatch_time),
        "checkout_url": f"https://api.razorpay.com/test/checkout/{product_id}"
    }


def normalize_catalog(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize a list of raw parsed dictionary items."""
    return [normalize_product(item, idx) for idx, item in enumerate(raw_items)]
