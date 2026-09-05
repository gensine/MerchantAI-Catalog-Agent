import os
import pytest
from ingest.ingest import ingest_catalog
from ingest.normalizer import normalize_product
from ingest.vector_store import catalog_store

SAMPLE_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demo", "sample_catalog.csv")


def test_catalog_ingestion_performance():
    res = ingest_catalog(source=SAMPLE_CSV, merchant_id="test_merchant_001")
    assert res["status"] == "success"
    assert res["product_count"] >= 15
    assert res["elapsed_seconds"] < 10.0  # Must ingest in < 10 seconds benchmark


def test_product_normalizer():
    raw_item = {
        "title": "Chambray Casual Shirt",
        "MRP": "₹ 1,499.00",
        "stock": "In Stock",
        "size": "M, L",
        "COD": "yes"
    }
    norm = normalize_product(raw_item, index=4)
    assert norm["name"] == "Chambray Casual Shirt"
    assert norm["price"] == 1499.0
    assert norm["stock"] == 10
    assert norm["cod_available"] is True
    assert norm["variants"]["sizes"] == ["M", "L"]


def test_hybrid_vector_query():
    # Pre-ingest
    ingest_catalog(source=SAMPLE_CSV, merchant_id="test_merchant_001")
    
    # Query for kurta
    results = catalog_store.query(merchant_id="test_merchant_001", query_text="blue kurta", max_results=3)
    assert len(results) > 0
    top_name = results[0]["name"].lower()
    assert "kurta" in top_name or "cotton" in top_name
