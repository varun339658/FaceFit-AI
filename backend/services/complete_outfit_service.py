"""
complete_outfit_service.py — FaceFit Complete Outfit AI Service
===============================================================
Core logic:
  1. Detect uploaded clothing items via Groq Vision
  2. Determine what's missing to complete the outfit
  3. Match from user's closet (wardrobe)
  4. Fetch product recommendations for missing items
  5. Score color compatibility
  6. Generate outfit variations (casual / smart / premium)
  7. Learn from user feedback
"""

import os, uuid, json, re, requests
from datetime import datetime
from pymongo import MongoClient
from langchain_groq import ChatGroq

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority",
)
_client = MongoClient(MONGO_URI)
_db     = _client["facefit_ai"]
_closet = _db["wardrobe"]
_saved_outfits = _db["complete_outfits"]
_feedback      = _db["outfit_feedback"]
_preferences   = _db["outfit_preferences"]

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SERPER_KEYS  = [
    os.getenv("SERPER_API_KEY_1", "4155943b29f00e53da61bc5c94bb9e7192ae8ef4"),
    os.getenv("SERPER_API_KEY_2", "f6110be0a8db43231ccb3d7760579ba5a01132aa"),
]

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.4,
    groq_api_key=GROQ_API_KEY,
)

GROQ_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]

# ── Complete outfit categories by occasion ────────────────────────────────────
OUTFIT_CATEGORIES = {
    "casual":    ["shirt", "pants", "shoes"],
    "office":    ["shirt", "pants", "shoes", "watch"],
    "wedding":   ["ethnic", "shoes", "accessories"],
    "party":     ["shirt", "pants", "shoes", "accessories"],
    "gym":       ["gym_tshirt", "track_pants", "sports_shoes"],
    "beach":     ["beach_shirt", "swim_shorts", "flip_flops"],
    "date":      ["shirt", "pants", "shoes", "watch"],
    "college":   ["shirt", "pants", "shoes"],
    "festival":  ["ethnic", "shoes", "accessories"],
    "interview": ["shirt", "pants", "shoes", "watch"],
    "dinner":    ["shirt", "pants", "shoes", "accessories"],
    "brunch":    ["shirt", "pants", "shoes"],
    "concert":   ["shirt", "pants", "shoes"],
}

CATEGORY_MAP = {
    "t-shirt": "shirt", "tshirt": "shirt", "shirt": "shirt",
    "polo": "shirt", "kurta": "ethnic", "blouse": "shirt", "top": "shirt",
    "kurti": "ethnic", "sherwani": "ethnic", "lehenga": "ethnic", "saree": "ethnic",
    "pant": "pants", "pants": "pants", "trouser": "pants", "jeans": "pants",
    "chino": "pants", "shorts": "pants", "legging": "pants",
    "track pant": "track_pants", "jogger": "track_pants",
    "shoe": "shoes", "shoes": "shoes", "sneaker": "shoes", "boot": "shoes",
    "sandal": "shoes", "loafer": "shoes", "sports shoe": "sports_shoes",
    "watch": "watch", "bracelet": "accessories", "necklace": "accessories",
    "sunglasses": "accessories", "earring": "accessories",
    "gym tshirt": "gym_tshirt", "dry fit": "gym_tshirt",
    "swim short": "swim_shorts", "beach shirt": "beach_shirt",
    "flip flop": "flip_flops",
}

# ── Color compatibility matrix (subset) ──────────────────────────────────────
COLOR_PAIRS = {
    ("white", "black"): 3, ("black", "white"): 3,
    ("white", "navy"): 3, ("navy", "white"): 3,
    ("white", "blue"): 3, ("blue", "white"): 3,
    ("beige", "brown"): 3, ("brown", "beige"): 3,
    ("beige", "navy"): 3, ("navy", "beige"): 3,
    ("grey", "white"): 3, ("white", "grey"): 3,
    ("grey", "black"): 3, ("black", "grey"): 3,
    ("mustard", "black"): 3, ("black", "mustard"): 3,
    ("mustard", "navy"): 3, ("navy", "mustard"): 3,
    ("mustard", "brown"): 3, ("brown", "mustard"): 3,
    ("olive", "cream"): 3, ("cream", "olive"): 3,
    ("olive", "camel"): 3, ("camel", "olive"): 3,
    ("burgundy", "beige"): 3, ("beige", "burgundy"): 3,
    ("teal", "white"): 3, ("white", "teal"): 3,
    ("navy", "grey"): 3, ("grey", "navy"): 3,
    ("black", "red"): 3, ("red", "black"): 3,
    ("cream", "navy"): 3, ("navy", "cream"): 3,
    ("emerald", "black"): 3, ("black", "emerald"): 3,
    ("coral", "white"): 3, ("white", "coral"): 3,
    ("electric blue", "black"): 3, ("black", "electric blue"): 3,
    ("saffron", "white"): 3, ("white", "saffron"): 3,
    ("terracotta", "beige"): 3, ("beige", "terracotta"): 3,
    ("lavender", "white"): 3, ("white", "lavender"): 3,
    ("maroon", "beige"): 3, ("beige", "maroon"): 3,
    ("rust", "cream"): 3, ("cream", "rust"): 3,
    ("khaki", "navy"): 3, ("navy", "khaki"): 3,
    ("camel", "white"): 3, ("white", "camel"): 3,
}


def _color_score(c1: str, c2: str) -> int:
    if not c1 or not c2: return 1
    c1, c2 = c1.lower().strip(), c2.lower().strip()
    if c1 == c2: return 1
    direct = COLOR_PAIRS.get((c1, c2)) or COLOR_PAIRS.get((c2, c1))
    if direct: return direct
    for (a, b), score in COLOR_PAIRS.items():
        if (a in c1 or c1 in a) and (b in c2 or c2 in b): return score
        if (a in c2 or c2 in a) and (b in c1 or c1 in b): return score
    return 1


def _parse_json(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    try: return json.loads(text)
    except Exception: pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except Exception: pass
    return {}


# ── Vision: detect clothing item ─────────────────────────────────────────────
import base64

def _img_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


DETECTION_PROMPT = """You are a clothing recognition AI. Analyze this clothing item image.

Return ONLY valid JSON (no markdown):
{
  "category": "shirt",
  "item_name": "navy blue slim fit polo shirt",
  "color": "navy blue",
  "style": "slim fit polo",
  "formality": "smart casual",
  "pattern": "solid",
  "fabric_guess": "cotton"
}

CATEGORY — choose ONE: shirt, pants, shoes, accessories, ethnic, dress, watch, gym_tshirt, track_pants, sports_shoes, swim_shorts, beach_shirt, flip_flops
COLOR — be specific: "navy blue", "off white", "forest green", "electric blue"
item_name — 4-7 words describing the exact item"""

def _detect_item(image_path: str) -> dict:
    if not GROQ_API_KEY:
        return {"category": "shirt", "item_name": "clothing item", "color": "unknown", "style": "", "formality": "casual"}

    b64  = _img_b64(image_path)
    ext  = image_path.rsplit(".", 1)[-1].lower()
    mime = f"image/{ext}" if ext in ("jpg", "jpeg", "png", "webp") else "image/jpeg"

    for model in GROQ_VISION_MODELS:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        {"type": "text", "text": DETECTION_PROMPT},
                    ]}],
                    "max_tokens": 250, "temperature": 0.1,
                },
                timeout=25,
            )
            if resp.status_code == 200:
                raw  = resp.json()["choices"][0]["message"]["content"]
                data = _parse_json(raw)
                if data.get("category") and data.get("color"):
                    return data
        except Exception as e:
            print(f"Vision detect error [{model}]: {e}")

    return {"category": "shirt", "item_name": "clothing item", "color": "unknown", "style": "", "formality": "casual"}


# ── Products search ───────────────────────────────────────────────────────────
def _serper_products(query: str, max_results: int = 4) -> list:
    url = "https://google.serper.dev/shopping"
    for key in SERPER_KEYS:
        if not key: continue
        try:
            resp = requests.post(
                url,
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": f"{query} India", "gl": "in", "hl": "en", "num": 10},
                timeout=12,
            )
            if resp.status_code in (402, 429): continue
            if resp.status_code != 200: continue
            products = []
            for item in resp.json().get("shopping", []):
                link = item.get("link") or item.get("productLink", "")
                if not link or "http" not in link: continue
                title = item.get("title", "").strip()
                if not title: continue
                image = None
                for f in ("thumbnailUrl", "imageUrl", "image"):
                    v = item.get(f)
                    if v and isinstance(v, str) and v.startswith("http"):
                        image = v; break
                products.append({
                    "title": title,
                    "price": item.get("price", "Check price") or "Check price",
                    "image": image,
                    "link":  link,
                    "source": item.get("source", "myntra.com"),
                })
                if len(products) >= max_results: break
            if products: return products
        except Exception as e:
            print(f"Serper error: {e}")
    return []


def _build_product_query(category: str, detected_items: list, gender: str, skin_tone: str, occasion: str) -> str:
    gl = "men" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "women"

    # Build a color suggestion based on existing items
    existing_colors = [i.get("color", "") for i in detected_items if i.get("color") and i.get("color") != "unknown"]

    SKIN_COLORS = {
        "dark":   ["electric blue", "emerald green", "saffron yellow", "coral", "magenta"],
        "medium": ["mustard", "teal", "burgundy", "forest green", "terracotta"],
        "light":  ["pastel blue", "mint green", "lavender", "sage green", "soft pink"],
    }
    suggested_colors = SKIN_COLORS.get(skin_tone.lower(), SKIN_COLORS["medium"])

    # Choose a color that complements existing items
    chosen_color = suggested_colors[0]
    for sc in suggested_colors:
        for ec in existing_colors:
            if _color_score(sc, ec) >= 2:
                chosen_color = sc
                break

    CAT_QUERIES = {
        "shirt":       f"{chosen_color} slim fit shirt polo tshirt {gl} {occasion}",
        "pants":       f"slim fit chino jeans trousers {gl} {occasion} versatile",
        "shoes":       f"leather loafer sneakers {gl} {occasion} clean",
        "ethnic":      f"{chosen_color} kurta ethnic wear {gl} {occasion} festive",
        "accessories": f"watch bracelet {gl} {occasion} accessories",
        "watch":       f"analog watch {gl} minimalist classic",
        "gym_tshirt":  f"dry fit gym t-shirt athletic {chosen_color} {gl}",
        "track_pants": f"track pants jogger athletic training {gl}",
        "sports_shoes":f"running sports training shoes {gl} Nike Adidas",
        "swim_shorts": f"swim shorts beach quick dry {gl} summer",
        "beach_shirt": f"linen beach shirt floral relaxed {gl} summer",
        "flip_flops":  f"beach flip flops sandals comfortable {gl}",
        "dress":       f"{chosen_color} dress {gl} {occasion} elegant",
    }
    return CAT_QUERIES.get(category, f"{category} {gl} {occasion} India fashion")


# ── Closet matching ───────────────────────────────────────────────────────────
def _find_closet_match(user_id: str, category: str, detected_items: list) -> dict | None:
    items = list(_closet.find({"user_id": user_id, "category": category}, {"_id": 0}))
    if not items: return None

    existing_colors = [i.get("color", "") for i in detected_items if i.get("color") and i.get("color") != "unknown"]
    if not existing_colors:
        return items[0]  # just return first if no color info

    # Score each closet item
    best, best_score = None, -1
    for item in items:
        score = 0
        for ec in existing_colors:
            score += _color_score(item.get("color", ""), ec)
        if score > best_score:
            best_score, best = score, item
    return best


# ── Color compatibility analysis ──────────────────────────────────────────────
def _analyze_color_compatibility(items: list) -> dict:
    colors = [i.get("color", "") for i in items if i.get("color") and i.get("color") != "unknown"]
    if len(colors) < 2:
        return {"score": 3, "label": "✦ Looks great", "explanation": "Only one item — hard to judge, but it's a good start!", "pairs": []}

    pairs = []
    total_score = 0
    count = 0
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            s = _color_score(colors[i], colors[j])
            label = {3: "Perfect match", 2: "Good combo", 1: "Neutral / Wearable"}.get(s, "Neutral")
            pairs.append({"color1": colors[i], "color2": colors[j], "score": s, "label": label})
            total_score += s
            count += 1

    avg = round(total_score / count, 1) if count else 2
    overall_label = "✦ Perfect Harmony" if avg >= 2.7 else "✓ Good Combination" if avg >= 2.0 else "~ Wearable" if avg >= 1.5 else "⚠ Color Clash"
    explanation = (
        "These colors work beautifully together — a cohesive, polished look!" if avg >= 2.7 else
        "Good color pairing — these pieces complement each other well." if avg >= 2.0 else
        "Wearable combination — consider adding a neutral to tie it together." if avg >= 1.5 else
        "These colors clash. Try swapping one piece for a more neutral shade."
    )
    return {"score": round(avg, 1), "label": overall_label, "explanation": explanation, "pairs": pairs}


# ── AI outfit completion logic ─────────────────────────────────────────────────
def _ai_complete_outfit(detected_items: list, missing_categories: list, gender: str,
                         skin_tone: str, occasion: str, user_preferences: dict) -> dict:
    gl         = "men" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "women"
    items_desc = ", ".join([f"{i.get('color','')} {i.get('item_name','item')}" for i in detected_items])
    missing    = ", ".join(missing_categories)
    prefs_note = ""
    if user_preferences.get("liked_styles"):
        prefs_note = f"User likes: {', '.join(user_preferences['liked_styles'][:3])}."
    if user_preferences.get("disliked_styles"):
        prefs_note += f" User dislikes: {', '.join(user_preferences['disliked_styles'][:3])}."

    prompt = f"""You are a world-class Indian fashion stylist completing an outfit.

UPLOADED ITEMS: {items_desc}
MISSING ITEMS TO COMPLETE OUTFIT: {missing}
CLIENT: {skin_tone} skin tone | {gl} | occasion: {occasion}
{prefs_note}

For each missing item, suggest the PERFECT completing piece.
Consider: color harmony, occasion, skin tone, and style cohesion.

Return ONLY valid JSON:
{{
  "outfit_name": "Smart Casual Evening Look",
  "style_vibe": "confident and polished",
  "completions": {{
    "<category>": {{
      "item_name": "specific descriptive name",
      "color": "specific color",
      "style": "style description",
      "why_it_works": "one sentence"
    }}
  }},
  "overall_tip": "One powerful styling tip",
  "outfit_score": 8
}}

Only include categories from: {missing}"""

    try:
        resp = llm.invoke(prompt)
        raw  = resp.content if hasattr(resp, "content") else str(resp)
        data = _parse_json(raw)
        if data and "completions" in data:
            return data
    except Exception as e:
        print(f"AI outfit complete error: {e}")

    # Fallback
    FALLBACK_COLORS = {
        "dark":   {"shirt": "electric blue", "pants": "black", "shoes": "white", "accessories": "gold"},
        "medium": {"shirt": "mustard", "pants": "navy", "shoes": "tan", "accessories": "silver"},
        "light":  {"shirt": "lavender", "pants": "cream", "shoes": "white", "accessories": "rose gold"},
    }
    colors = FALLBACK_COLORS.get(skin_tone.lower(), FALLBACK_COLORS["medium"])
    completions = {}
    for cat in missing_categories:
        col = colors.get(cat, "versatile neutral")
        completions[cat] = {
            "item_name": f"{col} {cat.replace('_', ' ')}",
            "color": col,
            "style": "versatile and stylish",
            "why_it_works": f"Complements the existing pieces and suits {skin_tone} skin tone.",
        }
    return {
        "outfit_name":  f"Curated {occasion.title()} Look",
        "style_vibe":   "balanced and stylish",
        "completions":  completions,
        "overall_tip":  "Layer accessories last — they tie the whole look together.",
        "outfit_score": 7,
    }


# ── Outfit variations (casual / smart / premium) ──────────────────────────────
def _generate_variations(detected_items: list, gender: str, skin_tone: str, occasion: str) -> list:
    gl         = "men" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "women"
    items_desc = ", ".join([f"{i.get('color','')} {i.get('item_name','')}" for i in detected_items])

    prompt = f"""World-class stylist. Client has: {items_desc}
Gender: {gl}, Skin tone: {skin_tone}, Occasion base: {occasion}

Create 3 DISTINCT outfit variations using these items as the anchor:

Return ONLY valid JSON array:
[
  {{
    "variation_name": "Casual Cool",
    "occasion": "casual",
    "additions": ["white chunky sneakers", "black beaded bracelet", "cap"],
    "styling_tip": "Roll up the sleeves for a relaxed look",
    "vibe": "effortless casual",
    "formality": "casual"
  }},
  {{
    "variation_name": "Smart Professional",
    "occasion": "office",
    "additions": ["leather loafers", "minimalist watch", "slim blazer"],
    "styling_tip": "Tuck in the shirt and add the blazer for instant authority",
    "vibe": "polished professional",
    "formality": "smart casual"
  }},
  {{
    "variation_name": "Evening Statement",
    "occasion": "dinner/date",
    "additions": ["leather boots", "silver watch", "dark slim trousers"],
    "styling_tip": "Switch to dark trousers and boots for a night-ready elevation",
    "vibe": "sophisticated evening",
    "formality": "semi-formal"
  }}
]"""

    try:
        resp = llm.invoke(prompt)
        raw  = resp.content if hasattr(resp, "content") else str(resp)
        raw  = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)
        if isinstance(data, list) and data:
            return data[:3]
    except Exception as e:
        print(f"Variations error: {e}")

    return [
        {"variation_name": "Casual Day", "occasion": "casual", "additions": ["white sneakers", "bracelet"], "styling_tip": "Keep it relaxed and comfortable.", "vibe": "casual", "formality": "casual"},
        {"variation_name": "Smart Casual", "occasion": "office/brunch", "additions": ["loafers", "watch", "blazer"], "styling_tip": "Add a blazer for instant polish.", "vibe": "smart casual", "formality": "smart casual"},
        {"variation_name": "Evening Look", "occasion": "dinner/party", "additions": ["leather boots", "watch"], "styling_tip": "Switch to dark pants and boots for the evening.", "vibe": "evening", "formality": "semi-formal"},
    ]


# ── User preferences ──────────────────────────────────────────────────────────
def _get_user_preferences(user_id: str) -> dict:
    doc = _preferences.find_one({"user_id": user_id}, {"_id": 0})
    return doc or {"liked_styles": [], "disliked_styles": [], "liked_colors": [], "disliked_colors": []}


# ── MAIN: complete outfit from uploaded items ─────────────────────────────────
def complete_outfit_from_items(
    uploaded_items: list,
    user_id: str,
    gender: str,
    skin_tone: str,
    face_shape: str,
    occasion: str,
    body_shape: str,
) -> dict:
    # Step 1: Detect each uploaded item
    detected_items = []
    for uploaded in uploaded_items:
        detection = _detect_item(uploaded["path"])
        detection["image_url"] = uploaded["url"]
        detected_items.append(detection)

    print(f"✅ Detected {len(detected_items)} items: {[(i['color'], i['item_name']) for i in detected_items]}")

    # Step 2: Determine what categories are uploaded vs missing
    uploaded_categories = set()
    for item in detected_items:
        raw_cat = item.get("category", "")
        normalized = CATEGORY_MAP.get(raw_cat.lower(), raw_cat)
        item["category"] = normalized
        uploaded_categories.add(normalized)

    required_categories = OUTFIT_CATEGORIES.get(occasion, OUTFIT_CATEGORIES["casual"])
    missing_categories  = [c for c in required_categories if c not in uploaded_categories]

    print(f"📦 Uploaded: {uploaded_categories} | Missing: {missing_categories}")

    # Step 3: Color compatibility of uploaded items
    color_analysis = _analyze_color_compatibility(detected_items)

    # Step 4: Get user preferences (learned)
    user_prefs = _get_user_preferences(user_id)

    # Step 5: AI completion suggestions
    ai_completion = _ai_complete_outfit(
        detected_items=detected_items,
        missing_categories=missing_categories,
        gender=gender,
        skin_tone=skin_tone,
        occasion=occasion,
        user_preferences=user_prefs,
    )

    # Step 6: For each missing item — find from closet AND fetch products
    closet_completions  = {}
    product_completions = {}

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def fetch_for_category(cat):
        closet_match = _find_closet_match(user_id, cat, detected_items)
        ai_suggestion = ai_completion.get("completions", {}).get(cat, {})
        query = _build_product_query(cat, detected_items, gender, skin_tone, occasion)
        # Use AI-suggested color in query if available
        if ai_suggestion.get("color"):
            query = f"{ai_suggestion['color']} {query}"
        products = _serper_products(query, max_results=4)
        return cat, closet_match, products

    with ThreadPoolExecutor(max_workers=min(len(missing_categories), 4)) as ex:
        futures = {ex.submit(fetch_for_category, cat): cat for cat in missing_categories}
        for future in as_completed(futures):
            cat, closet_match, products = future.result()
            if closet_match:
                closet_completions[cat] = closet_match
            product_completions[cat] = products

    # Step 7: Generate outfit variations
    variations = _generate_variations(detected_items, gender, skin_tone, occasion)

    # Step 8: Build final outfit with all items
    full_outfit = {}
    for item in detected_items:
        full_outfit[item["category"]] = {
            "item_name": item.get("item_name", ""),
            "color":     item.get("color", ""),
            "style":     item.get("style", ""),
            "image_url": item.get("image_url", ""),
            "source":    "uploaded",
        }
    for cat, closet_item in closet_completions.items():
        full_outfit[cat] = {
            "item_name": closet_item.get("item_name", ""),
            "color":     closet_item.get("color", ""),
            "style":     closet_item.get("style", ""),
            "image_url": closet_item.get("image_url", ""),
            "source":    "closet",
        }

    # Color score of the full outfit
    full_color_analysis = _analyze_color_compatibility(list(full_outfit.values()))

    return {
        "outfit_id":          uuid.uuid4().hex,
        "detected_items":     detected_items,
        "uploaded_categories": list(uploaded_categories),
        "missing_categories": missing_categories,
        "color_analysis":     color_analysis,
        "ai_completion":      ai_completion,
        "closet_completions": closet_completions,
        "product_completions": product_completions,
        "full_outfit":        full_outfit,
        "full_color_analysis": full_color_analysis,
        "variations":         variations,
        "occasion":           occasion,
        "gender":             gender,
        "skin_tone":          skin_tone,
        "outfit_score":       ai_completion.get("outfit_score", 7),
        "outfit_name":        ai_completion.get("outfit_name", "Complete Look"),
        "overall_tip":        ai_completion.get("overall_tip", ""),
        "style_vibe":         ai_completion.get("style_vibe", ""),
    }


# ── Replace a specific item ───────────────────────────────────────────────────
def replace_outfit_item(outfit: dict, replace_category: str, user_id: str,
                         occasion: str, gender: str, skin_tone: str) -> dict:
    # Get all other items except the one to replace
    other_items = [v for k, v in outfit.get("full_outfit", {}).items() if k != replace_category]

    # Try closet first
    closet_match = _find_closet_match(user_id, replace_category, other_items)

    # AI suggestion for replacement
    gl = "men" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "women"
    other_desc = ", ".join([f"{i.get('color','')} {i.get('item_name','')}" for i in other_items if i])
    prompt = f"""Stylist replacing one item. Existing outfit: {other_desc}.
Replace: {replace_category}. Gender: {gl}, Skin: {skin_tone}, Occasion: {occasion}.
Suggest the perfect replacement.
Return JSON: {{"item_name": "...", "color": "...", "style": "...", "why_it_works": "..."}}"""
    ai_suggestion = {}
    try:
        resp = llm.invoke(prompt)
        ai_suggestion = _parse_json(resp.content if hasattr(resp, "content") else str(resp))
    except Exception: pass

    # Products for replacement
    query    = _build_product_query(replace_category, other_items, gender, skin_tone, occasion)
    if ai_suggestion.get("color"):
        query = f"{ai_suggestion['color']} {query}"
    products = _serper_products(query, max_results=6)

    # Update outfit
    updated_outfit = dict(outfit)
    if closet_match:
        updated_outfit.setdefault("full_outfit", {})[replace_category] = {
            **closet_match, "source": "closet"
        }
    elif ai_suggestion:
        updated_outfit.setdefault("full_outfit", {})[replace_category] = {
            **ai_suggestion, "source": "ai_suggestion", "image_url": ""
        }

    return {
        "updated_outfit":     updated_outfit,
        "replacement_closet": closet_match,
        "replacement_products": products,
        "ai_suggestion":      ai_suggestion,
        "replaced_category":  replace_category,
    }


# ── Save / load outfits ───────────────────────────────────────────────────────
def save_completed_outfit(user_id: str, outfit: dict, name: str) -> dict:
    doc = {
        "user_id":    user_id,
        "outfit_id":  outfit.get("outfit_id") or uuid.uuid4().hex,
        "name":       name,
        "outfit":     outfit,
        "created_at": datetime.utcnow(),
    }
    _saved_outfits.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "outfit_id": doc["outfit_id"]}


def get_outfit_variations(user_id: str) -> list:
    docs = list(_saved_outfits.find({"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)]).limit(20))
    return docs


# ── Feedback / learning ───────────────────────────────────────────────────────
def record_outfit_feedback(user_id: str, outfit_id: str, action: str, items: list):
    _feedback.insert_one({
        "user_id":   user_id,
        "outfit_id": outfit_id,
        "action":    action,  # accept | reject
        "items":     items,
        "created_at": datetime.utcnow(),
    })

    # Update preferences
    styles  = [i.get("style", "") for i in items if i.get("style")]
    colors  = [i.get("color", "") for i in items if i.get("color")]

    if action == "accept":
        _preferences.update_one(
            {"user_id": user_id},
            {"$addToSet": {
                "liked_styles": {"$each": styles[:3]},
                "liked_colors": {"$each": colors[:3]},
            }, "$set": {"updated_at": datetime.utcnow()}},
            upsert=True,
        )
    elif action == "reject":
        _preferences.update_one(
            {"user_id": user_id},
            {"$addToSet": {
                "disliked_styles": {"$each": styles[:3]},
                "disliked_colors": {"$each": colors[:3]},
            }, "$set": {"updated_at": datetime.utcnow()}},
            upsert=True,
        )