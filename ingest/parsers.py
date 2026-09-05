import os
import re
import csv
import io
import logging
from typing import List, Dict, Any, Union

logger = logging.getLogger(__name__)


def parse_csv(file_content: Union[str, bytes], filename: str = "") -> List[Dict[str, Any]]:
    """Parse CSV text/bytes into a list of raw dict items."""
    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8", errors="replace")
    
    reader = csv.DictReader(io.StringIO(file_content))
    items = []
    for row in reader:
        # Filter out completely empty rows
        if any(v.strip() for v in row.values() if isinstance(v, str)):
            items.append({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k})
    return items


def parse_pdf(file_path_or_bytes: Union[str, bytes]) -> List[Dict[str, Any]]:
    """Parse text and tables from a PDF file using pypdf or pdfplumber."""
    extracted_text = ""
    tables = []
    
    # Try pdfplumber first if available
    try:
        import pdfplumber
        if isinstance(file_path_or_bytes, bytes):
            pdf_file = io.BytesIO(file_path_or_bytes)
        else:
            pdf_file = file_path_or_bytes
            
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
                extracted_tables = page.extract_tables()
                for table in extracted_tables:
                    if table and len(table) > 1:
                        headers = [str(c or "").strip() for c in table[0]]
                        for row in table[1:]:
                            if len(row) == len(headers):
                                item = {headers[i]: str(row[i] or "").strip() for i in range(len(headers)) if headers[i]}
                                tables.append(item)
    except Exception as e:
        logger.warning(f"pdfplumber parse fallback to pypdf: {e}")
        # Fallback to pypdf
        try:
            import pypdf
            if isinstance(file_path_or_bytes, bytes):
                reader = pypdf.PdfReader(io.BytesIO(file_path_or_bytes))
            else:
                reader = pypdf.PdfReader(file_path_or_bytes)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    extracted_text += t + "\n"
        except Exception as pypdf_err:
            logger.error(f"Failed PDF parsing: {pypdf_err}")

    if tables:
        return tables

    # Parse unstructured text lines into product chunks if tables weren't present
    return parse_unstructured_text(extracted_text)


def parse_web_url(url: str) -> List[Dict[str, Any]]:
    """Scrape product catalog details from a web page URL using BeautifulSoup."""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {"User-Agent": "MerchantAICatalogAgent/1.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        
        # Look for OpenGraph tags or Schema.org JSON-LD
        import json
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict) and obj.get("@type") in ["Product", "IndividualProduct"]:
                            items.append(obj)
                elif isinstance(data, dict) and data.get("@type") in ["Product", "IndividualProduct"]:
                    items.append(data)
            except Exception:
                continue

        # If JSON-LD found, return items
        if items:
            return items

        # Fallback to HTML product cards / elements
        product_cards = soup.select(".product, .product-item, .product-card, article")
        for card in product_cards:
            name_el = card.select_one(".name, .title, h2, h3, .product-title")
            price_el = card.select_one(".price, .cost, .amount")
            desc_el = card.select_one(".description, p, .desc")
            
            if name_el:
                items.append({
                    "name": name_el.get_text(strip=True),
                    "price": price_el.get_text(strip=True) if price_el else "0",
                    "description": desc_el.get_text(strip=True) if desc_el else ""
                })
                
        if not items:
            # Full text fallback
            items = parse_unstructured_text(soup.get_text(separator="\n"))

        return items
    except Exception as e:
        logger.error(f"Error fetching web URL {url}: {e}")
        return []


def parse_unstructured_text(text: str) -> List[Dict[str, Any]]:
    """Parse unstructured catalog text using block splitting / regex heuristics."""
    blocks = re.split(r'\n\s*\n', text)
    items = []
    
    for idx, block in enumerate(blocks):
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            continue
            
        # Try finding price (e.g. ₹1299, Rs 500, INR 300)
        price_match = re.search(r'(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)|([\d,]+)\s*(?:rupees|rs|inr)', block, re.IGNORECASE)
        price_val = 0.0
        if price_match:
            raw_p = price_match.group(1) or price_match.group(2)
            try:
                price_val = float(raw_p.replace(',', ''))
            except ValueError:
                pass
                
        name = lines[0]
        desc = " ".join(lines[1:]) if len(lines) > 1 else name
        
        # Only add if line looks like a product (has name and length > 3)
        if len(name) > 3 and not name.lower().startswith(("table of", "page ", "catalog", "index")):
            items.append({
                "product_id": f"P{idx+1:03d}",
                "product_name": name,
                "description": desc,
                "price": price_val
            })
            
    return items
