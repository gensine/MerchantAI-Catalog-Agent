import sys
import os
import time
import argparse
import json
import logging

from ingest.parsers import parse_csv, parse_pdf, parse_web_url, parse_unstructured_text
from ingest.normalizer import normalize_catalog
from ingest.vector_store import catalog_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def ingest_catalog(source: str, merchant_id: str = "rzp_merchant_001") -> dict:
    """
    Ingests catalog file or URL into vector database for a given merchant_id.
    Returns summary stats dict.
    """
    start_time = time.time()
    raw_items = []

    logger.info(f"Starting catalog ingestion from source: {source} for merchant: {merchant_id}")

    if source.startswith("http://") or source.startswith("https://"):
        raw_items = parse_web_url(source)
    elif os.path.exists(source):
        ext = os.path.splitext(source)[1].lower()
        if ext == ".csv":
            with open(source, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            raw_items = parse_csv(content, filename=source)
        elif ext in [".pdf"]:
            with open(source, "rb") as f:
                content = f.read()
            raw_items = parse_pdf(content)
        else:
            with open(source, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            raw_items = parse_unstructured_text(text)
    else:
        # Check if source string is inline CSV or JSON text
        if "," in source and "\n" in source:
            raw_items = parse_csv(source)
        else:
            raw_items = parse_unstructured_text(source)

    if not raw_items:
        logger.warning(f"No product items extracted from source: {source}")
        return {
            "status": "error",
            "merchant_id": merchant_id,
            "product_count": 0,
            "elapsed_seconds": round(time.time() - start_time, 3),
            "message": "No valid products found in source."
        }

    # Normalize extracted products
    normalized_products = normalize_catalog(raw_items)

    # Add to Vector Store
    catalog_store.add_products(merchant_id=merchant_id, products=normalized_products)

    elapsed = round(time.time() - start_time, 3)
    logger.info(f"Successfully ingested {len(normalized_products)} products in {elapsed} seconds.")

    return {
        "status": "success",
        "merchant_id": merchant_id,
        "product_count": len(normalized_products),
        "elapsed_seconds": elapsed,
        "products_preview": normalized_products[:3]
    }


def main():
    parser = argparse.ArgumentParser(description="MerchantAI Catalog Ingestion Pipeline")
    parser.add_argument("--source", required=True, help="Path to CSV/PDF file or web URL")
    parser.add_argument("--merchant_id", default="rzp_merchant_001", help="Merchant Identifier")
    args = parser.parse_args()

    result = ingest_catalog(source=args.source, merchant_id=args.merchant_id)
    print("\n--- Ingestion Result ---")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
