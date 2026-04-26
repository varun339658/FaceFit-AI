"""
budget_brand_service.py — FIXED: Budget + Brand filters actually applied
"""

import os
import re
from pymongo import MongoClient
from datetime import datetime

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority",
)
_client  = MongoClient(MONGO_URI)
_db      = _client["facefit_ai"]
_brands  = _db["user_brands"]
_budgets = _db["user_budgets"]


def get_user_brands(user_id: str) -> list:
    doc = _brands.find_one({"userId": user_id}, {"_id": 0})
    return doc.get("brands", []) if doc else []


def save_user_brands(user_id: str, brands: list) -> dict:
    existing = get_user_brands(user_id)
    combined = list({b.strip().lower().title() for b in (existing + brands) if b.strip()})
    _brands.update_one(
        {"userId": user_id},
        {"$set": {"userId": user_id, "brands": combined, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"brands": combined, "total": len(combined)}


def remove_user_brand(user_id: str, brand: str) -> dict:
    existing = get_user_brands(user_id)
    normalized = brand.strip().lower().title()
    updated = [b for b in existing if b.lower().title() != normalized]
    _brands.update_one(
        {"userId": user_id},
        {"$set": {"brands": updated, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"brands": updated}


def get_user_budget(user_id: str) -> dict:
    doc = _budgets.find_one({"userId": user_id}, {"_id": 0})
    if doc:
        return {"min_price": doc.get("min_price", 0) or 0, "max_price": doc.get("max_price", None)}
    return {"min_price": 0, "max_price": None}


def save_user_budget(user_id: str, min_price: int = 0, max_price: int = None) -> dict:
    _budgets.update_one(
        {"userId": user_id},
        {"$set": {"userId": user_id, "min_price": min_price, "max_price": max_price, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"min_price": min_price, "max_price": max_price}


def inject_brands_into_query(query: str, user_id: str, max_brands: int = 2) -> str:
    """Append up to max_brands favourite brands to the search query."""
    brands = get_user_brands(user_id)
    if not brands:
        return query
    q_lower = query.lower()
    new_brands = [b for b in brands[:max_brands] if b.lower() not in q_lower]
    if not new_brands:
        return query
    brand_str = " OR ".join(new_brands)
    return f"{query} {brand_str}"


def parse_price_from_string(price_str: str) -> float | None:
    if not price_str or not isinstance(price_str, str):
        return None
    cleaned = re.sub(r"[₹$£€Rs.,\s]", "", price_str.strip())
    if "-" in cleaned:
        cleaned = cleaned.split("-")[0]
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def filter_products_by_budget(products: list, min_price: float = 0, max_price: float = None) -> list:
    """Filter product list by price range. Keeps products with unparseable prices."""
    if not products:
        return products
    if min_price == 0 and max_price is None:
        return products

    filtered = []
    for p in products:
        price_val = parse_price_from_string(p.get("price", ""))
        if price_val is None:
            filtered.append(p)
        elif min_price <= price_val <= (max_price if max_price else float("inf")):
            filtered.append(p)

    return filtered if filtered else products


def apply_budget_brand_to_queries(queries: dict, user_id: str, min_price: float = 0, max_price: float = None) -> dict:
    result = {}
    for cat, q in queries.items():
        result[cat] = inject_brands_into_query(q, user_id)
    return result


def filter_all_products_by_budget(products_dict: dict, min_price: float = 0, max_price: float = None) -> dict:
    """Apply budget filter to a dict of {category: [products]}."""
    if min_price == 0 and max_price is None:
        return products_dict
    return {
        cat: filter_products_by_budget(prods, min_price, max_price)
        for cat, prods in products_dict.items()
    }