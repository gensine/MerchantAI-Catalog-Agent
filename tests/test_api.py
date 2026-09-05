import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_catalog_query_api():
    payload = {
        "merchant_id": "rzp_merchant_001",
        "query": "headphones noise cancelling",
        "max_results": 3
    }
    resp = client.post("/catalog/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert len(data["results"]) > 0
    assert "headphones" in data["results"][0]["name"].lower()


def test_product_availability_api():
    # Test availability for existing item P001
    resp = client.get("/product/P001/availability?merchant_id=rzp_merchant_001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == "P001"
    assert data["available"] is True
    assert data["stock"] > 0


def test_full_catalog_api():
    resp = client.get("/catalog/rzp_merchant_001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 15
