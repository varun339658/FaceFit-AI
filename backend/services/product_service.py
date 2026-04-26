"""
product_service.py — FIXED: Correct Serper keys + Budget/Brand filters
"""

import requests
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import time

SERPER_KEYS = [
    os.getenv("SERPER_API_KEY_1", "4155943b29f00e53da61bc5c94bb9e7192ae8ef4"),
    os.getenv("SERPER_API_KEY_2", "f6110be0a8db43231ccb3d7760579ba5a01132aa"),
]

SITE_MAP = {
    "shirt": "myntra.com", "pants": "ajio.com", "shoes": "flipkart.com",
    "watch": "amazon.in", "bracelet": "amazon.in", "sunglasses": "myntra.com",
    "top": "myntra.com", "necklace": "amazon.in", "earrings": "amazon.in",
    "topwear": "myntra.com", "bottomwear": "ajio.com", "footwear": "flipkart.com",
    "accessories": "amazon.in", "dress": "myntra.com", "jacket": "myntra.com",
    "blazer": "myntra.com", "ethnic": "myntra.com",
    "gym_tshirt": "myntra.com", "track_pants": "myntra.com",
    "sports_shoes": "flipkart.com", "gym_shorts": "myntra.com",
    "swim_shorts": "myntra.com", "beach_shirt": "myntra.com", "flip_flops": "amazon.in",
    "cleanser": "nykaa.com", "toner": "nykaa.com", "serum_day": "nykaa.com",
    "serum_night": "nykaa.com", "moisturizer": "nykaa.com", "sunscreen": "nykaa.com",
    "eye_cream": "nykaa.com", "spot_treatment": "nykaa.com",
    "brightening_serum": "nykaa.com", "face_oil": "nykaa.com",
}

_CACHE: dict = {}
_CACHE_TTL = 300


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time() - entry[1]) < _CACHE_TTL:
        return entry[0]
    return None


def _cache_set(key: str, value):
    _CACHE[key] = (value, time())
    if len(_CACHE) > 200:
        oldest = sorted(_CACHE.keys(), key=lambda k: _CACHE[k][1])[:50]
        for k in oldest:
            _CACHE.pop(k, None)


def _is_valid_image_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    if not url.startswith("http"):
        return False
    if "encrypted-tbn" in url or "googleusercontent" in url:
        return True
    cdn_domains = [
        "assets.myntassets.com", "rukminim", "m.media-amazon",
        "images.nykaa", "images-cdn.ajio", "images.meesho.com",
        "gloimg", "lh3.googleusercontent", "static.nike",
        "images.bewakoof", "img1.ajio", "cdn.shopify",
    ]
    if any(d in url for d in cdn_domains):
        return True
    if re.search(r"\.(jpg|jpeg|png|webp|gif)(\?|$)", url, re.I):
        return True
    return False


def _extract_image_from_item(item: dict) -> str | None:
    for field in ("thumbnailUrl", "imageUrl", "image", "thumbnail", "imgUrl", "img", "imageLink"):
        val = item.get(field)
        if val and _is_valid_image_url(val):
            return val
    for field in ("product", "listing"):
        nested = item.get(field, {})
        if isinstance(nested, dict):
            for img_field in ("imageUrl", "thumbnailUrl", "image"):
                val = nested.get(img_field)
                if val and _is_valid_image_url(val):
                    return val
    return None


def _serper_request(endpoint: str, payload: dict) -> dict:
    cache_key = f"{endpoint}:{str(sorted(payload.items()))}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    url = f"https://google.serper.dev/{endpoint}"
    for idx, key in enumerate(SERPER_KEYS):
        headers = {"X-API-KEY": key, "Content-Type": "application/json"}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in (402, 429):
                print(f"Serper key {idx+1} exhausted (HTTP {resp.status_code})")
                continue
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                continue
            print(f"Serper key {idx+1} OK for '{endpoint}:{payload.get('q','')[:30]}'")
            _cache_set(cache_key, data)
            return data
        except Exception as e:
            print(f"Serper key {idx+1} failed: {e}")
    return {}


def _fetch_image_for_title(title: str) -> str | None:
    cache_key = f"img:{title[:60]}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    data = _serper_request("images", {"q": title, "gl": "in", "hl": "en", "num": 3})
    for img in data.get("images", []):
        u = img.get("imageUrl") or img.get("thumbnailUrl")
        if u and _is_valid_image_url(u):
            _cache_set(cache_key, u)
            return u
    _cache_set(cache_key, None)
    return None


def _fetch_images_parallel(products_needing_images: list) -> dict:
    results = {}
    if not products_needing_images:
        return results
    with ThreadPoolExecutor(max_workers=min(len(products_needing_images), 5)) as executor:
        futures = {
            executor.submit(_fetch_image_for_title, p["title"]): i
            for i, p in enumerate(products_needing_images)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception:
                results[idx] = None
    return results


EVENT_CATEGORY_GUARDS = {
    "college":   {"forbidden_words": ["kurta","sherwani","ethnic","blazer","formal","suit"],   "required_words": ["casual","streetwear","jeans","tshirt","sneakers"]},
    "gym":       {"forbidden_words": ["kurta","jeans","formal","blazer","ethnic","chino"],      "required_words": ["athletic","dry fit","gym","training","sport"]},
    "office":    {"forbidden_words": ["gym","jogger","athletic","graphic tee","oversized"],     "required_words": ["formal","professional"]},
    "beach":     {"forbidden_words": ["kurta","formal","suit","blazer"],                        "required_words": ["beach","summer","linen","casual"]},
    "interview": {"forbidden_words": ["jogger","graphic tee","ethnic","kurta","oversized"],     "required_words": ["formal","professional","slim fit"]},
}


def _sanitize_query_for_event(query: str, category: str, event: str = None) -> str:
    if not event or event not in EVENT_CATEGORY_GUARDS:
        return query
    guard = EVENT_CATEGORY_GUARDS[event]
    q_low = query.lower()
    for word in guard.get("forbidden_words", []):
        q_low = q_low.replace(word, "")
    has_required = any(w in q_low for w in guard.get("required_words", []))
    if not has_required and guard.get("required_words"):
        q_low = guard["required_words"][0] + " " + q_low
    return " ".join(q_low.split())


def _inject_brands(query: str, user_id: str) -> str:
    if not user_id:
        return query
    try:
        from services.budget_brand_service import inject_brands_into_query
        return inject_brands_into_query(query, user_id, max_brands=2)
    except Exception:
        return query


def _parse_price(price_str: str) -> float | None:
    if not price_str or not isinstance(price_str, str):
        return None
    cleaned = re.sub(r"[₹$£€Rs.,\s]", "", price_str.strip())
    if "-" in cleaned:
        cleaned = cleaned.split("-")[0]
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _apply_budget_filter(products: list, min_price: float = 0, max_price: float = None) -> list:
    if min_price == 0 and max_price is None:
        return products
    filtered = []
    for p in products:
        price_val = _parse_price(p.get("price", ""))
        if price_val is None:
            filtered.append(p)
        elif min_price <= price_val <= (max_price if max_price else float("inf")):
            filtered.append(p)
    return filtered if filtered else products


def _get_user_budget(user_id: str) -> tuple:
    try:
        from services.budget_brand_service import get_user_budget
        b = get_user_budget(user_id)
        return b.get("min_price", 0) or 0, b.get("max_price") or None
    except Exception:
        return 0, None


def get_product_recommendations(
    query:     str,
    category:  str   = None,
    event:     str   = None,
    user_id:   str   = None,
    min_price: float = 0,
    max_price: float = None,
) -> list:
    site = SITE_MAP.get(category, "amazon.in")

    # Brand injection
    query = _inject_brands(query, user_id)

    # Event sanitization
    if event:
        query = _sanitize_query_for_event(query, category or "", event)

    if "india" not in query.lower():
        query = query + " India"

    products = []

    # Pass 1: Google Shopping
    shopping_data = _serper_request("shopping", {"q": query, "gl": "in", "hl": "en", "num": 10})
    needs_image = []

    for item in shopping_data.get("shopping", []):
        link = item.get("link") or item.get("productLink", "")
        if not link or "http" not in link:
            continue
        title = item.get("title", "").strip()
        if not title or len(title) < 4:
            continue
        if event and event in EVENT_CATEGORY_GUARDS:
            forbidden = EVENT_CATEGORY_GUARDS[event].get("forbidden_words", [])
            if any(w in title.lower() for w in forbidden):
                continue
        price = item.get("price", "Check price") or "Check price"
        src   = item.get("source", site)
        image = _extract_image_from_item(item)
        prod  = {"title": title, "price": price, "image": image, "link": link, "source": src, "_needs_image": image is None}
        products.append(prod)
        if image is None:
            needs_image.append((len(products) - 1, prod))
        if len(products) >= 8:
            break

    # Pass 2: Parallel image fetch
    if needs_image:
        items_needing = [item for _, item in needs_image]
        image_results = _fetch_images_parallel(items_needing)
        for local_idx, (prod_idx, prod) in enumerate(needs_image):
            img = image_results.get(local_idx)
            if img:
                products[prod_idx]["image"] = img
                print(f"Got image for: {prod['title'][:50]}")

    for p in products:
        p.pop("_needs_image", None)

    # Pass 3: Organic fallback
    if not products:
        print(f"Shopping empty for '{query}' — trying organic")
        organic_data = _serper_request("search", {"q": f"{query} buy online", "gl": "in", "hl": "en", "num": 6})
        for item in organic_data.get("organic", [])[:6]:
            link = item.get("link", "")
            if not link or "http" not in link:
                continue
            title = item.get("title", query).strip()
            image = _extract_image_from_item(item)
            products.append({"title": title, "price": "Check price", "image": image, "link": link, "source": site})
        organic_no_img = [p for p in products if not p.get("image")]
        if organic_no_img:
            img_map = _fetch_images_parallel(organic_no_img)
            for i, p in enumerate(organic_no_img):
                p["image"] = img_map.get(i)

    # Budget filter
    effective_min = min_price
    effective_max = max_price
    if user_id and effective_min == 0 and effective_max is None:
        effective_min, effective_max = _get_user_budget(user_id)

    if effective_min > 0 or effective_max is not None:
        products = _apply_budget_filter(products, effective_min, effective_max)
        print(f"Budget filter ₹{effective_min}–₹{effective_max}: {len(products)} products remain")

    if not products:
        return [{"title": f"Search: {query}", "price": "", "image": None,
                 "link": f"https://www.{site}/search?q={query.replace(' ', '+')}", "source": site}]

    return products[:6]


def get_multiple_categories_parallel(
    queries:  dict,
    event:    str = None,
    user_id:  str = None,
) -> dict:
    results = {}

    def fetch_one(cat, query):
        try:
            prods = get_product_recommendations(query, cat, event, user_id)
            return cat, prods
        except Exception as e:
            print(f"Error fetching {cat}: {e}")
            return cat, []

    with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as executor:
        futures = {executor.submit(fetch_one, cat, q): cat for cat, q in queries.items()}
        for future in as_completed(futures):
            try:
                cat, prods = future.result()
                if prods:
                    results[cat] = prods
            except Exception as e:
                print(f"Parallel fetch error: {e}")

    return results