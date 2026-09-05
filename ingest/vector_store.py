import os
import json
import logging
import math
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Simple in-memory / local disk Vector Store fallback if ChromaDB is initializing or optional
class LocalVectorStore:
    """Lightweight in-memory vector store with TF-IDF / keyword similarity and metadata filtering."""
    def __init__(self):
        self.catalogs: Dict[str, List[Dict[str, Any]]] = {}

    def add_products(self, merchant_id: str, products: List[Dict[str, Any]]):
        self.catalogs[merchant_id] = products
        logger.info(f"[LocalVectorStore] Saved {len(products)} products for merchant {merchant_id}")

    def _ensure_merchant_loaded(self, merchant_id: str):
        if merchant_id not in self.catalogs or not self.catalogs[merchant_id]:
            # Auto-ingest sample catalog if available
            sample_csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), "demo", "sample_catalog.csv")
            if os.path.exists(sample_csv):
                from ingest.ingest import ingest_catalog
                ingest_catalog(source=sample_csv, merchant_id=merchant_id)

    def query(
        self, 
        merchant_id: str, 
        query_text: str, 
        max_results: int = 5,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        category: Optional[str] = None,
        cod_only: bool = False,
        in_stock_only: bool = False
    ) -> List[Dict[str, Any]]:
        self._ensure_merchant_loaded(merchant_id)
        products = self.catalogs.get(merchant_id, [])

        if not products:
            # Check if any merchant exists, fallback
            all_prods = []
            for m_prods in self.catalogs.values():
                all_prods.extend(m_prods)
            products = all_prods

        query_words = set(query_text.lower().split())
        scored_products = []

        for p in products:
            # Metadata filtering
            if max_price is not None and p["price"] > max_price:
                continue
            if min_price is not None and p["price"] < min_price:
                continue
            if category and category.lower() not in p["category"].lower():
                continue
            if cod_only and not p.get("cod_available", True):
                continue
            if in_stock_only and p.get("stock", 0) <= 0:
                continue

            # Calculate match score based on keyword frequency & field weights
            name_text = p["name"].lower()
            desc_text = p["description"].lower()
            cat_text = p["category"].lower()
            var_text = str(p.get("variants", {})).lower()

            score = 0.0
            for word in query_words:
                if len(word) < 2:
                    continue
                if word in name_text:
                    score += 3.0
                if word in cat_text:
                    score += 2.0
                if word in var_text:
                    score += 2.0
                if word in desc_text:
                    score += 1.0

            # Normalize confidence score between 0.50 and 0.99 for matches
            confidence = min(0.99, max(0.50, round(0.50 + (score / (len(query_words) * 3.0 + 1e-5)) * 0.49, 2)))
            
            # If query has words and score > 0 or query is empty/broad
            if score > 0 or len(query_words) == 0:
                scored_products.append({
                    "product": p,
                    "score": score,
                    "confidence_score": confidence
                })

        # Sort by match score descending, then price
        scored_products.sort(key=lambda x: (x["score"], -x["product"]["price"]), reverse=True)
        
        # If no scored items matched the exact words, return all candidates under filters with default score
        if not scored_products and products:
            for p in products:
                if max_price is not None and p["price"] > max_price:
                    continue
                if min_price is not None and p["price"] < min_price:
                    continue
                scored_products.append({
                    "product": p,
                    "score": 0.1,
                    "confidence_score": 0.60
                })
            scored_products.sort(key=lambda x: x["product"]["price"])

        results = []
        for item in scored_products[:max_results]:
            prod_copy = dict(item["product"])
            prod_copy["confidence_score"] = item["confidence_score"]
            results.append(prod_copy)

        return results

    def get_all(self, merchant_id: str) -> List[Dict[str, Any]]:
        self._ensure_merchant_loaded(merchant_id)
        return self.catalogs.get(merchant_id, [])

    def get_by_id(self, merchant_id: str, product_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_merchant_loaded(merchant_id)
        products = self.catalogs.get(merchant_id, [])
        for p in products:
            if p["product_id"].lower() == product_id.lower():
                return p
        # Check all merchants fallback
        for m_prods in self.catalogs.values():
            for p in m_prods:
                if p["product_id"].lower() == product_id.lower():
                    return p
        return None


# Global Store Instance
catalog_store = LocalVectorStore()


# Try loading ChromaDB if available
class ChromaVectorStore:
    """ChromaDB wrapper when chroma is installed."""
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.chroma_client = None
        self.collection = None
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.chroma_client.get_or_create_collection(name="merchant_products")
            logger.info("ChromaDB initialized successfully.")
        except Exception as e:
            logger.warning(f"ChromaDB initialization fallback: {e}")

    def add_products(self, merchant_id: str, products: List[Dict[str, Any]]):
        catalog_store.add_products(merchant_id, products)
        if not self.collection:
            return
            
        ids = [f"{merchant_id}_{p['product_id']}" for p in products]
        documents = [f"{p['name']} - {p['description']} - Category: {p['category']} - Price: {p['price']}" for p in products]
        metadatas = [
            {
                "merchant_id": merchant_id,
                "product_id": p["product_id"],
                "price": float(p["price"]),
                "category": p["category"],
                "stock": int(p["stock"]),
                "cod_available": bool(p["cod_available"])
            }
            for p in products
        ]
        try:
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
        except Exception as e:
            logger.error(f"Error adding products to ChromaDB: {e}")

    def query(self, merchant_id: str, query_text: str, max_results: int = 5, **kwargs) -> List[Dict[str, Any]]:
        # Delegates to store with fallback logic
        return catalog_store.query(merchant_id, query_text, max_results, **kwargs)


def get_vector_store():
    return catalog_store
