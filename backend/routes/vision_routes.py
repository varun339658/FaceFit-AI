from flask import Blueprint, request, jsonify
from services.vision_service import detect_skin_issues
import os
import uuid
import base64
import requests
from services.vision_service import (
    detect_face,
    detect_face_landmarks,
    detect_face_shape,
    detect_skin_tone,
    draw_face_landmarks,
)

vision_bp = Blueprint("vision", __name__)
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

SERPER_KEYS = [
    os.getenv("SERPER_API_KEY_1", "934bbbbd208f870ef93ae78c798fedd3f2932c57"),
    os.getenv("SERPER_API_KEY_2", "79c419e528ed79f27dd65d6c36bba5055a202058"),
]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(path)
    return path


def handle_vision_request(processor_fn, *extra_args):
    if "image" not in request.files:
        return jsonify({"error": "No image field in request"}), 400
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 415
    path = save_uploaded_file(file)
    try:
        result = processor_fn(path, *extra_args)
    except Exception as exc:
        return jsonify({"error": f"Processing failed: {str(exc)}"}), 500
    finally:
        if os.path.exists(path):
            os.remove(path)
    return jsonify(result), 200


# ── Standard Vision Routes ───────────────────────────────────────────────────

@vision_bp.route("/detect-face", methods=["POST"])
def detect_face_api():
    return handle_vision_request(detect_face)


@vision_bp.route("/face-landmarks", methods=["POST"])
def face_landmarks_api():
    return handle_vision_request(detect_face_landmarks)


@vision_bp.route("/face-shape", methods=["POST"])
def face_shape_api():
    return handle_vision_request(detect_face_shape)


@vision_bp.route("/skin-tone", methods=["POST"])
def skin_tone_api():
    return handle_vision_request(detect_skin_tone)


@vision_bp.route("/draw-landmarks", methods=["POST"])
def draw_landmarks_api():
    if "image" not in request.files:
        return jsonify({"error": "No image field in request"}), 400
    file = request.files["image"]
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 415
    path = save_uploaded_file(file)
    try:
        output_path = draw_face_landmarks(path)
    except Exception as exc:
        return jsonify({"error": f"Processing failed: {str(exc)}"}), 500
    finally:
        if os.path.exists(path):
            os.remove(path)
    if output_path is None:
        return jsonify({"error": "No face detected in image"}), 422
    return jsonify({"image_path": output_path}), 200


@vision_bp.route("/detect-skin", methods=["POST"])
def detect_skin_api():
    return handle_vision_request(detect_skin_issues)


# ── NEW: Upload & Search Outfit ──────────────────────────────────────────────

def _image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _describe_outfit_with_groq(image_path: str) -> str:
    """
    Use Groq's vision model (llava) to describe the clothing item in the image.
    Falls back to Anthropic API if Groq vision isn't available.
    Returns a concise product search query.
    """
    b64 = _image_to_base64(image_path)
    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type = f"image/{ext}" if ext in ("jpg", "jpeg", "png", "webp") else "image/jpeg"

    # Try Groq vision (llava-v1.5-7b-4096-preview)
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llava-v1.5-7b-4096-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{b64}"},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Look at this clothing/fashion item image. "
                                "Describe it as a specific product search query for Indian e-commerce (Myntra, Amazon, Flipkart). "
                                "Include: color, style/cut, garment type, gender if visible. "
                                "Output ONLY the search query, nothing else. "
                                "Example outputs: "
                                "'electric blue oversized graphic t-shirt men India', "
                                "'saffron yellow embroidered linen kurta men India', "
                                "'emerald green off-shoulder crop top women India', "
                                "'black slim fit cargo pants men India'"
                            ),
                        },
                    ],
                }
            ],
            "max_tokens": 80,
            "temperature": 0.3,
        }
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20,
        )
        if resp.status_code == 200:
            result = resp.json()
            query = result["choices"][0]["message"]["content"].strip()
            # Clean up — remove quotes if present
            query = query.strip('"\'')
            print(f"👁️ GROQ VISION QUERY: {query}")
            return query
        else:
            print(f"⚠️ Groq vision failed: {resp.status_code} — {resp.text[:200]}")
    except Exception as e:
        print(f"⚠️ Groq vision error: {e}")

    # Hard fallback (Groq-only — no Anthropic API)
    return "fashion clothing India"


def _serper_shopping_search(query: str) -> list:
    """Search Google Shopping via Serper and return product list."""
    url = "https://google.serper.dev/shopping"
    for idx, key in enumerate(SERPER_KEYS):
        headers = {"X-API-KEY": key, "Content-Type": "application/json"}
        try:
            resp = requests.post(
                url,
                headers=headers,
                json={"q": f"{query}", "gl": "in", "hl": "en", "num": 10},
                timeout=12,
            )
            if resp.status_code in (402, 429):
                continue
            resp.raise_for_status()
            data = resp.json()
            products = []
            for item in data.get("shopping", [])[:8]:
                link = item.get("link") or item.get("productLink", "")
                if not link or "http" not in link:
                    continue
                image = None
                for field in ("imageUrl", "thumbnailUrl", "image", "thumbnail"):
                    val = item.get(field)
                    if val and isinstance(val, str) and val.startswith("http"):
                        image = val
                        break
                products.append({
                    "title":  item.get("title", query),
                    "price":  item.get("price", "Check price"),
                    "image":  image,
                    "link":   link,
                    "source": item.get("source", "amazon.in"),
                })
                if len(products) >= 6:
                    break
            if products:
                print(f"✅ Serper key {idx+1} found {len(products)} products for: {query}")
                return products
        except Exception as e:
            print(f"Serper key {idx+1} error: {e}")
            continue

    # Organic fallback
    for idx, key in enumerate(SERPER_KEYS):
        headers = {"X-API-KEY": key, "Content-Type": "application/json"}
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers=headers,
                json={"q": f"{query} site:myntra.com OR site:amazon.in", "gl": "in", "hl": "en", "num": 6},
                timeout=12,
            )
            if resp.status_code == 200:
                data = resp.json()
                products = []
                for item in data.get("organic", [])[:6]:
                    link = item.get("link", "")
                    if not link or "http" not in link:
                        continue
                    products.append({
                        "title":  item.get("title", query),
                        "price":  "Check price",
                        "image":  None,
                        "link":   link,
                        "source": "myntra.com",
                    })
                if products:
                    return products
        except Exception:
            continue

    return [{
        "title":  f"Search: {query}",
        "price":  "",
        "image":  None,
        "link":   f"https://www.myntra.com/search?rawQuery={query.replace(' ', '+')}",
        "source": "myntra.com",
    }]


@vision_bp.route("/search-outfit", methods=["POST"])
def search_outfit_by_image():
    """
    Upload a clothing item image → AI describes it → Search Google Shopping → Return products.
    
    Request: multipart/form-data with 'image' field
    Response: { "query": str, "products": list }
    """
    if "image" not in request.files:
        return jsonify({"error": "No image field in request"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 415

    path = save_uploaded_file(file)

    try:
        # Step 1: AI vision describes the clothing item
        query = _describe_outfit_with_groq(path)
        print(f"🔍 OUTFIT SEARCH QUERY: {query}")

        # Step 2: Search Google Shopping
        products = _serper_shopping_search(query)

        return jsonify({
            "query":    query,
            "products": products,
        }), 200

    except Exception as e:
        print(f"❌ search-outfit error: {e}")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500

    finally:
        if os.path.exists(path):
            os.remove(path)