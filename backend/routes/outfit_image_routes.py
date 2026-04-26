"""
outfit_image_routes.py — FIXED: Better image generation with correct prompts
Uses Pollinations.ai with improved prompts for accurate fashion photography
"""
import os
import requests
import uuid
import time
import urllib.parse
import re
import json
from flask import Blueprint, request, jsonify
from langchain_groq import ChatGroq

outfit_image_bp = Blueprint("outfit_image", __name__)
GROQ_API_KEY    = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.3,
    groq_api_key=GROQ_API_KEY,
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SERPER_KEYS = [
    os.getenv("SERPER_API_KEY_1", "4155943b29f00e53da61bc5c94bb9e7192ae8ef4"),
    os.getenv("SERPER_API_KEY_2", "f6110be0a8db43231ccb3d7760579ba5a01132aa"),
]

# ── Build descriptive outfit prompt ──────────────────────────────────────────

def _build_outfit_prompt(outfit: dict, gender: str, skin_tone: str, event: str) -> tuple:
    items = outfit.get("items", {})
    if not items:
        items = {k: v for k, v in outfit.items() if isinstance(v, dict) and v.get("item_name")}

    item_descs = []
    color_list = []
    for slot, item in items.items():
        if not item:
            continue
        color = item.get("color", "")
        name  = item.get("item_name", slot)
        style = item.get("style", "")
        if color:
            color_list.append(color)
        desc = f"{color} {name}".strip()
        if style:
            desc += f" ({style})"
        item_descs.append(desc)

    if not item_descs:
        item_descs = ["stylish casual Indian outfit"]

    gl = "man" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "woman"
    items_text = ", ".join(item_descs[:5])  # limit to 5 items max

    # Skin tone description
    skin_desc = {
        "dark": "deep brown dark-skinned",
        "medium": "medium brown wheatish-skinned",
        "light": "fair light-skinned",
    }.get(skin_tone.lower(), "medium-skinned")

    # Build highly specific fashion photography prompt
    prompt = (
        f"Professional fashion photography, Indian {skin_desc} {gl} model, "
        f"wearing: {items_text}. "
        f"Occasion: {event}. "
        f"Full body shot, neutral white/cream studio background, "
        f"soft professional studio lighting, sharp focus, editorial magazine style, "
        f"4K high resolution, photorealistic, fashion lookbook style."
    )

    negative = (
        "cartoon, anime, illustration, sketch, painting, drawing, ugly, deformed, "
        "text, watermark, blurry, nsfw, low quality, bad anatomy, extra limbs, "
        "multiple people, crowd, busy background"
    )

    return prompt, negative


# ── Generator 1: Pollinations.ai (free, no key) ───────────────────────────────

def _pollinations_generate(prompt: str, seed: int = None) -> str | None:
    try:
        if seed is None:
            import random
            seed = random.randint(1, 9999)

        encoded = urllib.parse.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=512&height=768&seed={seed}&nologo=true&model=flux"
            f"&enhance=true"
        )
        print(f"🎨 Pollinations request (seed={seed}): {url[:120]}...")
        resp = requests.get(url, timeout=90, stream=True)
        if resp.status_code == 200 and "image" in resp.headers.get("content-type", ""):
            fname = f"outfit_gen_{uuid.uuid4().hex}.jpg"
            path  = os.path.join(UPLOAD_FOLDER, fname)
            with open(path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            size = os.path.getsize(path)
            if size > 10000:  # at least 10KB = real image
                print(f"✅ Pollinations success: {fname} ({size} bytes)")
                return f"/uploads/{fname}"
            else:
                os.remove(path)
                print(f"⚠️ Pollinations returned tiny file ({size} bytes)")
        else:
            print(f"⚠️ Pollinations HTTP {resp.status_code}")
    except Exception as e:
        print(f"Pollinations error: {e}")
    return None


# ── Generator 2: Fashion image search from Serper ────────────────────────────

def _serper_fashion_image(outfit: dict, gender: str, skin_tone: str, event: str) -> str | None:
    """
    Search Google Images for an accurate fashion reference image.
    Returns a direct image URL.
    """
    items   = outfit.get("items", {})
    gl      = "men" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "women"

    # Build specific query from outfit items
    colors  = [v.get("color", "") for v in items.values() if v and v.get("color")]
    item_names = [v.get("item_name", "") for v in items.values() if v and v.get("item_name")]
    color_q = colors[0] if colors else ""
    item_q  = item_names[0] if item_names else "outfit"

    # Build a specific fashion search query
    query = f"{color_q} {item_q} {gl} India {event} outfit fashion editorial"

    for key in SERPER_KEYS:
        try:
            resp = requests.post(
                "https://google.serper.dev/images",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": query, "gl": "in", "hl": "en", "num": 10},
                timeout=10,
            )
            if resp.status_code == 200:
                images = resp.json().get("images", [])
                # Prefer trusted fashion CDNs
                trusted_domains = ["myntra", "ajio", "nykaa", "amazon", "flipkart",
                                   "fashionista", "vogue", "myntassets", "rukminim"]
                for img in images:
                    url = img.get("imageUrl", "")
                    if url and url.startswith("https") and any(d in url for d in trusted_domains):
                        print(f"✅ Serper fashion image found: {url[:80]}")
                        return url
                # Any image fallback
                for img in images:
                    url = img.get("imageUrl", "")
                    if url and url.startswith("https"):
                        return url
        except Exception as e:
            print(f"Serper image error: {e}")

    return None


# ── Route ─────────────────────────────────────────────────────────────────────

@outfit_image_bp.route("/closet/outfit-image", methods=["POST"])
def generate_outfit_image():
    data      = request.json or {}
    outfit    = data.get("outfit", {})
    gender    = data.get("gender", "male")
    skin_tone = data.get("skin_tone", "medium")
    event     = data.get("event", "casual")

    if not outfit:
        return jsonify({"error": "outfit object is required"}), 400

    try:
        prompt, negative = _build_outfit_prompt(outfit, gender, skin_tone, event)
        print(f"🎨 Outfit prompt: {prompt[:150]}...")

        # Try Pollinations with 2 different seeds for best result
        image_url = None
        source = "pollinations"

        for attempt in range(2):
            import random
            seed = random.randint(100, 9999)
            image_url = _pollinations_generate(prompt, seed=seed)
            if image_url:
                break
            time.sleep(1)

        # Fallback: real fashion image from Google Images
        if not image_url:
            print("Pollinations failed, using fashion image search fallback...")
            image_url = _serper_fashion_image(outfit, gender, skin_tone, event)
            source = "fashion_search"

        if not image_url:
            return jsonify({
                "error": "Image generation temporarily unavailable. Try again in a moment.",
                "prompt": prompt,
            }), 503

        return jsonify({
            "image_url": image_url,
            "prompt":    prompt,
            "source":    source,
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500