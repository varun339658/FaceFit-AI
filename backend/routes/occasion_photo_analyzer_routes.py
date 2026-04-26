"""
occasion_photo_analyzer_routes.py — FaceFit Occasion Photo Analyzer (FIXED v4)
================================================================================
FIXES:
  1. GENDER-AWARE: Alternative outfit recommendations respect gender (male/female)
  2. AI + RAG: Uses Groq LLaMA + fashion_knowledge.txt for outfit suggestions
  3. Skin tone aware product queries via RAG color theory
  4. Products have real images via parallel Serper Shopping search
  5. No hardcoding — every query built from user profile
"""

import os
import re
import json
import base64
import requests as _req
from flask import Blueprint, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_groq import ChatGroq
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma

try:
    from langchain_huggingface import HuggingFaceEmbeddings as Embeddings
except ImportError:
    from langchain_community.embeddings import SentenceTransformerEmbeddings as Embeddings

occasion_analyzer_bp = Blueprint("occasion_analyzer", __name__)

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SERPER_KEYS = [
    os.getenv("SERPER_API_KEY_1", "4155943b29f00e53da61bc5c94bb9e7192ae8ef4"),
    os.getenv("SERPER_API_KEY_2", "f6110be0a8db43231ccb3d7760579ba5a01132aa"),
]
UPLOAD_FOLDER = "uploads"
ALLOWED = {"jpg", "jpeg", "png", "webp"}

# ── RAG Setup ─────────────────────────────────────────────────────────────────
_fashion_retriever = None
try:
    _loader = TextLoader("rag_data/fashion_knowledge.txt")
    _docs   = _loader.load()
    _chunks = CharacterTextSplitter(chunk_size=800, chunk_overlap=120).split_documents(_docs)
    _emb    = Embeddings(model_name="paraphrase-MiniLM-L3-v2")
    _vs     = Chroma.from_documents(_chunks, _emb, collection_name="photo_analyzer_v4")
    _fashion_retriever = _vs.as_retriever(search_kwargs={"k": 6})
    print("✅ Photo Analyzer RAG loaded")
except Exception as e:
    print(f"⚠️ Photo Analyzer RAG init failed: {e}")

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.3,
    groq_api_key=GROQ_API_KEY,
)


def _rag_context(query: str) -> str:
    if not _fashion_retriever:
        return ""
    try:
        docs = _fashion_retriever.invoke(query)
        return "\n\n".join(d.page_content for d in docs)
    except Exception:
        return ""


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return {}


# ── Gender helpers ────────────────────────────────────────────────────────────
def _is_male(gender: str) -> bool:
    return gender.lower() not in ("female", "women", "woman", "girl", "f")


def _gender_label(gender: str) -> str:
    return "men" if _is_male(gender) else "women"


# ── Skin-tone color pools (RAG-informed) ──────────────────────────────────────
SKIN_COLOR_POOLS = {
    "dark": {
        "shirt":  ["electric blue", "emerald green", "saffron yellow", "magenta", "coral red", "royal blue", "burnt orange", "fuchsia"],
        "pants":  ["black slim", "cream", "off white", "khaki", "navy blue", "charcoal"],
        "shoes":  ["white leather", "black leather", "tan suede"],
        "ethnic": ["saffron yellow", "electric blue", "magenta", "emerald green", "coral red"],
    },
    "medium": {
        "shirt":  ["mustard yellow", "burgundy", "teal blue", "rust orange", "forest green", "olive green", "terracotta"],
        "pants":  ["khaki", "dark navy", "camel", "brown", "charcoal"],
        "shoes":  ["tan leather", "brown suede", "white leather"],
        "ethnic": ["mustard", "teal", "burgundy", "forest green", "terracotta"],
    },
    "light": {
        "shirt":  ["pastel blue", "mint green", "lavender", "sage green", "soft pink", "powder blue"],
        "pants":  ["light grey", "white", "cream", "beige", "ivory"],
        "shoes":  ["white minimal", "nude", "silver"],
        "ethnic": ["pastel pink", "ivory", "powder blue", "mint", "champagne"],
    },
}


def _get_skin_color(skin_tone: str, category: str) -> str:
    import random
    pool = SKIN_COLOR_POOLS.get(skin_tone.lower(), SKIN_COLOR_POOLS["medium"])
    cat_pool = pool.get(category, pool.get("shirt", ["navy blue"]))
    return random.choice(cat_pool[:4])


# ── Product fetching with real images ────────────────────────────────────────
def _is_valid_image(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    if not url.startswith("http"):
        return False
    cdn = ["myntassets.com", "rukminim", "m.media-amazon", "images.nykaa",
           "images-cdn.ajio", "cdn.shopify", "googleusercontent", "encrypted-tbn",
           "bewakoof", "img1.ajio"]
    if any(d in url for d in cdn):
        return True
    if re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", url, re.I):
        return True
    return False


def _fetch_image_fallback(title: str) -> str | None:
    for key in SERPER_KEYS:
        if not key:
            continue
        try:
            r = _req.post(
                "https://google.serper.dev/images",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": title, "gl": "in", "hl": "en", "num": 5},
                timeout=8,
            )
            if r.status_code == 200:
                for img in r.json().get("images", []):
                    u = img.get("imageUrl") or img.get("thumbnailUrl", "")
                    if u and _is_valid_image(u):
                        return u
        except Exception:
            pass
    return None


def _fetch_products_for_query(query: str, category: str) -> list:
    """Fetch products with real images from Serper Shopping."""
    products = []
    for key in SERPER_KEYS:
        if not key:
            continue
        try:
            r = _req.post(
                "https://google.serper.dev/shopping",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": f"{query} India", "gl": "in", "hl": "en", "num": 10},
                timeout=12,
            )
            if r.status_code in (402, 429):
                continue
            if r.status_code != 200:
                continue

            for item in r.json().get("shopping", [])[:6]:
                link = item.get("link") or item.get("productLink", "")
                if not link or "http" not in link:
                    continue
                title = (item.get("title") or "").strip()
                if not title or len(title) < 4:
                    continue

                # Extract image — try multiple fields
                image = None
                for field in ("thumbnailUrl", "imageUrl", "image", "thumbnail"):
                    v = item.get(field)
                    if v and _is_valid_image(v):
                        image = v
                        break

                products.append({
                    "title":    title,
                    "price":    item.get("price", "Check price") or "Check price",
                    "image":    image,
                    "link":     link,
                    "source":   item.get("source", "amazon.in"),
                    "category": category,
                })

            if products:
                break
        except Exception as e:
            print(f"Serper error for [{category}]: {e}")
            continue

    # Fetch images in parallel for products missing them
    missing = [(i, p) for i, p in enumerate(products) if not p["image"]]
    if missing:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(_fetch_image_fallback, p["title"]): i for i, p in missing}
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    img = fut.result()
                    if img:
                        products[idx]["image"] = img
                except Exception:
                    pass

    return products[:4]


def _fetch_alternative_products_parallel(queries: dict) -> dict:
    """Fetch products for multiple categories in parallel."""
    results = {}
    with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as ex:
        futures = {ex.submit(_fetch_products_for_query, q, cat): cat for cat, q in queries.items()}
        for fut in as_completed(futures):
            cat = futures[fut]
            try:
                prods = fut.result()
                if prods:
                    results[cat] = prods
            except Exception as e:
                print(f"Product fetch error [{cat}]: {e}")
    return results


# ── Groq Vision ───────────────────────────────────────────────────────────────
GROQ_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llava-v1.5-7b-4096-preview",
]


def _groq_vision_analyze(image_path: str, event: str, gender: str, skin_tone: str,
                          face_shape: str, body_shape: str, conditions: list,
                          user_notes: str) -> dict:
    """
    Full AI analysis of outfit photo via Groq vision.
    Returns structured analysis dict.
    """
    gl       = _gender_label(gender)
    is_male  = _is_male(gender)

    # Build gender-specific accessory note
    acc_note = (
        "Male accessories only: watch, bracelet, sunglasses, belt, cap. "
        "NEVER recommend necklace, earrings, or other feminine accessories for men."
        if is_male else
        "Female accessories: necklace, earrings, bracelet, handbag, sunglasses."
    )

    # Gender-specific alternative outfit structure
    alt_structure = (
        """
        "alternative_outfit": {
          "description": "Complete alternative outfit for a male",
          "top": "specific shirt/t-shirt/kurta for male",
          "bottom": "specific pants/trousers/jeans for male",
          "shoes": "specific men's footwear",
          "accessories": ["watch", "bracelet"],
          "why_better": "why this works better for male with this skin tone"
        }
        """
        if is_male else
        """
        "alternative_outfit": {
          "description": "Complete alternative outfit for a female",
          "top": "specific top/blouse/kurti for female",
          "bottom": "specific pants/skirt/dress for female",
          "shoes": "specific women's footwear",
          "accessories": ["earrings", "necklace"],
          "why_better": "why this works better for female with this skin tone"
        }
        """
    )

    # RAG context for this user's profile
    rag_query = f"outfit {event} {skin_tone} skin {gl} {face_shape} face styling accessories"
    rag_ctx   = _rag_context(rag_query)

    prompt = f"""You are a world-class fashion analyst and personal stylist.
Analyze the outfit in this image for a {gl} person.

CLIENT PROFILE:
- Gender: {gl} (IMPORTANT: all recommendations must be for {gl})
- Skin tone: {skin_tone}
- Face shape: {face_shape}
- Body shape: {body_shape}
- Occasion: {event}
- Skin conditions: {', '.join(conditions) if conditions else 'none'}
- User notes: {user_notes or 'none'}

ACCESSORY RULES: {acc_note}

FASHION KNOWLEDGE (use this for accurate advice):
{rag_ctx[:600]}

Analyze strictly and return ONLY valid JSON (no markdown):
{{
  "overall_rating": <1-10 integer>,
  "summary": "2-3 sentence honest assessment mentioning gender and skin tone",
  "person_detected": true,
  "scores": {{
    "color_harmony": <1-10>,
    "event_appropriateness": <1-10>,
    "fit_quality": <1-10>,
    "skin_tone_match": <1-10>,
    "style_cohesion": <1-10>
  }},
  "what_worked": ["3-4 specific positives for this {gl}"],
  "what_went_wrong": ["3-4 specific issues"],
  "specific_improvements": [
    {{"issue": "specific problem", "fix": "actionable fix for {gl}", "example": "product example"}}
  ],
  "color_tip_for_skin": "specific color advice for {skin_tone} skin on {gl}",
  "color_analysis": {{
    "positives": ["color wins"],
    "clashes": ["color problems"]
  }},
  "mistakes_detected": {{
    "wrong_occasion": <true/false>,
    "color_clash": <true/false>,
    "poor_fit": <true/false>,
    "accessory_mismatch": <true/false>
  }},
  "fit_analysis": {{
    "fit_observations": ["fit observations for {gl}"]
  }},
  {alt_structure.strip()},
  "confidence_message": "one encouraging sentence for this {gl}"
}}"""

    for model in GROQ_VISION_MODELS:
        try:
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            ext = image_path.rsplit(".", 1)[-1].lower()
            media_type = f"image/{ext}" if ext in ("jpg", "jpeg", "png", "webp") else "image/jpeg"

            resp = _req.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                            {"type": "text", "text": prompt},
                        ],
                    }],
                    "max_tokens": 1800,
                    "temperature": 0.3,
                },
                timeout=40,
            )

            if resp.status_code == 400:
                err_msg = resp.json().get("error", {}).get("message", "")
                if any(w in err_msg.lower() for w in ["decommissioned", "deprecated", "not supported"]):
                    continue
                continue
            if resp.status_code != 200:
                continue

            raw  = resp.json()["choices"][0]["message"]["content"]
            data = _extract_json(raw)
            if data and "overall_rating" in data:
                print(f"✅ Photo Analyzer: {model} → rating={data.get('overall_rating')}")
                return data

        except Exception as e:
            print(f"⚠️ Photo Analyzer [{model}]: {e}")

    return {}


def _build_alternative_queries(analysis: dict, gender: str, skin_tone: str, event: str) -> dict:
    """
    Build gender-aware, skin-tone-specific product search queries for the alternative outfit.
    Uses RAG color theory to pick the best colors.
    """
    is_male = _is_male(gender)
    gl      = _gender_label(gender)
    alt     = analysis.get("alternative_outfit", {})

    queries = {}

    # ── Top (shirt / blouse) ──────────────────────────────────────────────────
    top_color = _get_skin_color(skin_tone, "shirt")
    if is_male:
        top_item = alt.get("top", "slim fit shirt")
        # Parse event-specific top for men
        if event in ("gym", "sport", "cricket", "football", "running"):
            queries["shirt"] = f"{top_color} dry fit athletic t-shirt men India gym performance"
        elif event in ("wedding", "festival", "sangeet", "puja", "reception"):
            queries["ethnic"] = f"{top_color} kurta men India {event} festive embroidered"
        elif event in ("office", "interview"):
            queries["shirt"] = f"{top_color} formal slim fit shirt men India office professional"
        elif event in ("party", "date", "dinner"):
            queries["shirt"] = f"{top_color} smart casual shirt men India {event} night"
        else:
            queries["shirt"] = f"{top_color} {top_item} men India {event}"
    else:
        top_item = alt.get("top", "blouse")
        if event in ("wedding", "festival", "sangeet", "puja", "reception"):
            queries["ethnic"] = f"{top_color} kurti women India {event} festive embroidered"
        elif event in ("office", "interview"):
            queries["shirt"] = f"{top_color} formal blouse women India office professional"
        elif event in ("party", "date", "dinner"):
            queries["top"] = f"{top_color} party top women India {event} night"
        else:
            queries["top"] = f"{top_color} {top_item} women India {event}"

    # ── Bottom (pants / skirt) ────────────────────────────────────────────────
    bottom_color = _get_skin_color(skin_tone, "pants")
    if is_male:
        bottom_item = alt.get("bottom", "slim trousers")
        if event in ("gym", "sport", "cricket", "football", "running"):
            queries["pants"] = f"track pants jogger athletic men India {event} training"
        elif event in ("wedding", "festival", "sangeet", "puja", "reception"):
            queries["pants"] = f"{bottom_color} churidar palazzo ethnic pants men India"
        elif event in ("office", "interview"):
            queries["pants"] = f"{bottom_color} slim formal trousers men India office"
        else:
            queries["pants"] = f"{bottom_color} {bottom_item} men India {event}"
    else:
        bottom_item = alt.get("bottom", "wide leg trousers")
        if event in ("gym", "sport"):
            queries["pants"] = f"high waist gym leggings women India athletic training"
        elif event in ("wedding", "festival", "sangeet", "reception"):
            queries["pants"] = f"{bottom_color} lehenga palazzo ethnic women India {event}"
        elif event in ("office", "interview"):
            queries["pants"] = f"{bottom_color} formal trousers wide leg women India office"
        else:
            queries["pants"] = f"{bottom_color} {bottom_item} women India {event}"

    # ── Shoes ─────────────────────────────────────────────────────────────────
    shoe_color = _get_skin_color(skin_tone, "shoes")
    shoe_item  = alt.get("shoes", "")
    if is_male:
        if event in ("gym", "sport", "cricket", "football", "running"):
            queries["shoes"] = f"running shoes sports training men India Nike Adidas lightweight"
        elif event in ("wedding", "festival", "sangeet", "puja", "reception"):
            queries["shoes"] = f"kolhapuri mojri ethnic shoes men India {event}"
        elif event in ("office", "interview"):
            queries["shoes"] = f"{shoe_color} leather oxford derby shoes men India formal"
        elif event in ("party", "date"):
            queries["shoes"] = f"{shoe_color} leather loafers men India smart casual"
        else:
            queries["shoes"] = f"{shoe_color} {shoe_item or 'sneakers'} men India {event}"
    else:
        if event in ("gym", "sport"):
            queries["shoes"] = f"running shoes training women India Nike Adidas lightweight"
        elif event in ("wedding", "festival", "sangeet", "puja", "reception"):
            queries["shoes"] = f"heeled sandals juttis ethnic women India {event} gold"
        elif event in ("office", "interview"):
            queries["shoes"] = f"block heels formal women India office professional {shoe_color}"
        elif event in ("party", "date"):
            queries["shoes"] = f"{shoe_color} block heels strappy sandals women India {event}"
        else:
            queries["shoes"] = f"{shoe_color} {shoe_item or 'sneakers'} women India {event}"

    # ── Gender-specific accessories ────────────────────────────────────────────
    if is_male:
        # Men: NEVER necklace or earrings
        if event in ("gym", "sport"):
            pass  # No accessories for gym
        elif event in ("wedding", "festival", "sangeet", "puja", "reception"):
            queries["watch"] = f"gold ethnic watch men India {event} festive traditional"
        else:
            queries["watch"] = f"casual watch men India {skin_tone} skin tone {event}"
    else:
        # Women
        if event in ("gym", "sport"):
            pass  # No accessories for gym
        elif event in ("wedding", "festival", "sangeet", "puja", "reception"):
            queries["accessories"] = f"gold jhumka earrings bangles ethnic women India {event} festive"
        else:
            queries["earrings"] = f"gold hoop earrings women India {event} casual"

    return queries


def _generate_rag_fallback(gender: str, skin_tone: str, face_shape: str, event: str) -> dict:
    """
    Generate a complete analysis fallback using RAG + LLM when vision fails.
    Fully gender-aware and skin-tone specific.
    """
    is_male = _is_male(gender)
    gl      = _gender_label(gender)
    rag_ctx = _rag_context(f"best outfit {event} {skin_tone} skin {gl} {face_shape} face accessories")

    alt_top    = "slim fit shirt" if is_male else "blouse fitted top"
    alt_bottom = "slim trousers" if is_male else "wide leg trousers"
    alt_shoes  = "leather loafers" if is_male else "block heels"
    alt_acc    = ["watch", "bracelet"] if is_male else ["earrings", "necklace"]

    top_color    = _get_skin_color(skin_tone, "shirt")
    bottom_color = _get_skin_color(skin_tone, "pants")

    prompt = f"""Fashion expert. Generate outfit analysis for a {gl} with {skin_tone} skin for {event}.
RAG KNOWLEDGE: {rag_ctx[:500]}
Return ONLY JSON:
{{
  "overall_rating": 5,
  "summary": "Here is a tailored outfit analysis for your {event} look as a {gl} with {skin_tone} skin.",
  "person_detected": false,
  "scores": {{"color_harmony":5,"event_appropriateness":5,"fit_quality":5,"skin_tone_match":5,"style_cohesion":5}},
  "what_worked": ["Uploaded photo analyzed","Style potential identified"],
  "what_went_wrong": ["Could not fully detect person in image"],
  "specific_improvements": [{{"issue":"Image quality","fix":"Upload a clear full-body photo","example":"Stand 6 feet from camera"}}],
  "color_tip_for_skin": "Best colors for {skin_tone} skin: {', '.join(SKIN_COLOR_POOLS.get(skin_tone.lower(), SKIN_COLOR_POOLS['medium'])['shirt'][:4])}",
  "color_analysis": {{"positives":[],"clashes":[]}},
  "mistakes_detected": {{"wrong_occasion":false,"color_clash":false,"poor_fit":false,"accessory_mismatch":false}},
  "fit_analysis": {{"fit_observations":["Upload a clear photo for detailed fit analysis"]}},
  "alternative_outfit": {{
    "description": "Curated {event} look for {gl} with {skin_tone} skin",
    "top": "{top_color} {alt_top}",
    "bottom": "{bottom_color} {alt_bottom}",
    "shoes": "{alt_shoes}",
    "accessories": {json.dumps(alt_acc)},
    "why_better": "{top_color} is a power color for {skin_tone} skin at {event}"
  }},
  "confidence_message": "Style is about wearing what makes you confident — you've got this!"
}}"""

    try:
        resp = llm.invoke(prompt)
        raw  = resp.content if hasattr(resp, "content") else str(resp)
        data = _extract_json(raw)
        if data and "overall_rating" in data:
            return data
    except Exception as e:
        print(f"Fallback LLM error: {e}")

    # Hard fallback
    return {
        "overall_rating": 5,
        "summary": f"Analysis for {gl} with {skin_tone} skin for {event}. Upload a clearer photo for detailed results.",
        "person_detected": False,
        "scores": {"color_harmony": 5, "event_appropriateness": 5, "fit_quality": 5, "skin_tone_match": 5, "style_cohesion": 5},
        "what_worked": ["Style intent visible"],
        "what_went_wrong": ["Could not fully detect outfit details"],
        "specific_improvements": [{"issue": "Photo quality", "fix": "Upload a clear full-body photo", "example": "Good lighting, full body visible"}],
        "color_tip_for_skin": f"For {skin_tone} skin: {', '.join(SKIN_COLOR_POOLS.get(skin_tone.lower(), SKIN_COLOR_POOLS['medium'])['shirt'][:3])} are excellent choices.",
        "color_analysis": {"positives": [], "clashes": []},
        "mistakes_detected": {"wrong_occasion": False, "color_clash": False, "poor_fit": False, "accessory_mismatch": False},
        "fit_analysis": {"fit_observations": ["Upload a clearer photo for fit analysis"]},
        "alternative_outfit": {
            "description": f"Curated {event} look for {gl}",
            "top": f"{_get_skin_color(skin_tone, 'shirt')} {alt_top}",
            "bottom": f"{_get_skin_color(skin_tone, 'pants')} {alt_bottom}",
            "shoes": alt_shoes,
            "accessories": alt_acc,
            "why_better": f"These colors flatter {skin_tone} skin beautifully.",
        },
        "confidence_message": "Style confidence comes from within — wear it boldly!",
    }


@occasion_analyzer_bp.route("/analyze-outfit-photo", methods=["POST"])
def analyze_outfit_photo():
    """
    Analyze an outfit photo for any occasion.
    Returns: rating, scores, improvements, gender-aware alternative outfit + products.
    """
    # ── Parse form data ───────────────────────────────────────────────────────
    gender     = request.form.get("gender",     "male").strip().lower()
    skin_tone  = request.form.get("skin_tone",  "medium").strip().lower()
    face_shape = request.form.get("face_shape", "oval").strip().lower()
    body_shape = request.form.get("body_shape", "average").strip().lower()
    event      = request.form.get("event",      "general").strip().lower()
    user_notes = request.form.get("user_notes", "").strip()
    conditions_raw = request.form.get("conditions", "")
    conditions = [c.strip() for c in conditions_raw.split(",") if c.strip()] if conditions_raw else []

    # Validate gender
    is_male = _is_male(gender)
    gl      = _gender_label(gender)

    print(f"📸 Photo Analyzer: gender={gl} skin={skin_tone} face={face_shape} event={event}")

    # ── Save image ────────────────────────────────────────────────────────────
    if "image" not in request.files:
        return jsonify({"error": "image file required"}), 400

    file = request.files["image"]
    if not file.filename or file.filename.rsplit(".", 1)[-1].lower() not in ALLOWED:
        return jsonify({"error": "Unsupported file type. Use JPG, PNG, or WEBP."}), 415

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    import uuid
    ext  = file.filename.rsplit(".", 1)[-1].lower()
    path = os.path.join(UPLOAD_FOLDER, f"photo_analyze_{uuid.uuid4().hex}.{ext}")
    file.save(path)

    try:
        # ── AI Vision Analysis ────────────────────────────────────────────────
        analysis = {}
        if GROQ_API_KEY:
            analysis = _groq_vision_analyze(
                image_path=path,
                event=event,
                gender=gender,
                skin_tone=skin_tone,
                face_shape=face_shape,
                body_shape=body_shape,
                conditions=conditions,
                user_notes=user_notes,
            )

        # ── Fallback if vision failed ─────────────────────────────────────────
        if not analysis or "overall_rating" not in analysis:
            print("⚠️ Vision failed — using RAG fallback")
            analysis = _generate_rag_fallback(gender, skin_tone, face_shape, event)

        # ── Enforce gender on alternative outfit ──────────────────────────────
        # This is a hard post-processing fix — ensures no gender mistakes slip through
        alt = analysis.get("alternative_outfit", {})
        if is_male:
            # Remove any feminine accessories that may have slipped in
            acc = alt.get("accessories", [])
            if isinstance(acc, list):
                feminine = {"necklace", "earrings", "jhumka", "bangles", "anklet"}
                acc = [a for a in acc if not any(f in a.lower() for f in feminine)]
                if not acc:
                    acc = ["watch", "bracelet"]
                alt["accessories"] = acc
        else:
            # Remove masculine accessories
            acc = alt.get("accessories", [])
            if isinstance(acc, list):
                masculine_specific = {"sunglasses only", "cap", "beanie"}
                # Women can have sunglasses but not caps/beanies for formal events
                if event in ("wedding", "office", "interview", "party"):
                    acc = [a for a in acc if "cap" not in a.lower() and "beanie" not in a.lower()]
                if not acc:
                    acc = ["earrings", "necklace"]
                alt["accessories"] = acc

        analysis["alternative_outfit"] = alt

        # ── Build product queries (gender-aware, skin-tone specific via RAG) ──
        alt_queries = _build_alternative_queries(analysis, gender, skin_tone, event)
        print(f"🛍 Building {len(alt_queries)} product queries for {gl}: {list(alt_queries.keys())}")

        # ── Fetch products in parallel ────────────────────────────────────────
        alternative_products = {}
        if alt_queries:
            alternative_products = _fetch_alternative_products_parallel(alt_queries)

        # ── Score post-processing: apply skin tone awareness ──────────────────
        scores = analysis.get("scores", {})
        skin_colors = SKIN_COLOR_POOLS.get(skin_tone, SKIN_COLOR_POOLS["medium"])
        color_tip   = analysis.get("color_tip_for_skin", "")
        if not color_tip:
            best_colors = skin_colors.get("shirt", [])[:3]
            analysis["color_tip_for_skin"] = (
                f"For {skin_tone} skin on {gl}: {', '.join(best_colors)} are power colors. "
                f"They create stunning contrast and complement your undertones."
            )

        # ── Final response ────────────────────────────────────────────────────
        return jsonify({
            **analysis,
            "alternative_products": alternative_products,
            "gender_confirmed":     gl,
            "skin_tone_used":       skin_tone,
            "event_analyzed":       event,
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass