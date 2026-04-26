"""
body_shape_routes.py — FIXED: Better product recommendations based on body shape + correct Serper key
"""
import os
import uuid
import cv2
import numpy as np
import mediapipe as mp
import json
import re
from flask import Blueprint, request, jsonify
from langchain_groq import ChatGroq

body_shape_bp = Blueprint("body_shape", __name__)
UPLOAD_FOLDER = "uploads"
ALLOWED = {"jpg", "jpeg", "png", "webp"}
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.3, groq_api_key=GROQ_API_KEY)
mp_pose = mp.solutions.pose

# Body-shape-specific product queries — HIGHLY SPECIFIC for each shape
BODY_SHAPE_PRODUCT_QUERIES = {
    "hourglass": {
        "male": {
            "shirt":  "fitted slim fit polo shirt men India highlights physique",
            "pants":  "straight leg slim fit trousers men India balanced",
            "ethnic": "fitted kurta men India defines waist traditional",
        },
        "female": {
            "shirt":  "wrap top fitted waist women India hourglass figure",
            "pants":  "high waist straight trousers women India hourglass",
            "ethnic": "wrap kurti saree embroidered women India festive",
        },
    },
    "rectangle": {
        "male": {
            "shirt":  "layered bomber jacket double layer men India adds definition",
            "pants":  "slim straight trousers men India adds structure",
            "ethnic": "kurta with jacket men India adds depth definition",
        },
        "female": {
            "shirt":  "peplum top ruffled waist women India creates curves",
            "pants":  "A-line flared skirt women India creates curves",
            "ethnic": "A-line anarkali women India creates silhouette",
        },
    },
    "pear": {
        "male": {
            "shirt":  "structured shoulder wide blazer men India balances hips",
            "pants":  "dark straight slim trousers men India minimizes hips",
            "ethnic": "structured bandhgala nehru jacket men India broad shoulders",
        },
        "female": {
            "shirt":  "off shoulder structured top women India broad shoulder emphasis",
            "pants":  "dark straight leg trousers women India slimming hips",
            "ethnic": "embroidered blouse saree women India boat neckline",
        },
    },
    "apple": {
        "male": {
            "shirt":  "V-neck slim fit shirt men India vertical line slimming",
            "pants":  "straight cut palazzo wide leg trousers men India",
            "ethnic": "V-neck kurta men India vertical line slimming",
        },
        "female": {
            "shirt":  "empire waist flowy tunic women India V-neckline slimming",
            "pants":  "palazzo wide leg pants women India empire waist",
            "ethnic": "empire waist anarkali kurti women India flowy",
        },
    },
    "inverted_triangle": {
        "male": {
            "shirt":  "slim fit V-neck shirts for men India soft shoulders",
            "pants":  "dark wash straight leg pants for men India wider base",
            "ethnic": "slim fit kurta pyjama for men India bottom balance",
        },
        "female": {
            "shirt":  "flared A-line skirt top women India widens hips",
            "pants":  "wide leg flared trousers women India balances shoulders",
            "ethnic": "anarkali skirt lehenga women India widens lower body",
        },
    },
}


def _allowed(f):
    return "." in f and f.rsplit(".", 1)[1].lower() in ALLOWED


def _save_file(file):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    name = f"body_{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, name)
    file.save(path)
    return path, f"/uploads/{name}"


def _detect_body_measurements(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return {"error": "Could not read image"}
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w = image.shape[:2]
    with mp_pose.Pose(static_image_mode=True, model_complexity=2, min_detection_confidence=0.4) as pose:
        results = pose.process(rgb)
    if not results.pose_landmarks:
        return {"pose_detected": False}
    lm = results.pose_landmarks.landmark
    try:
        ls, rs = lm[11], lm[12]
        lh, rh = lm[23], lm[24]
        le, re_ = lm[13], lm[14]
        if any(pt.visibility < 0.3 for pt in [ls, rs, lh, rh]):
            return {"pose_detected": True, "error": "Low confidence — use a clear full-body photo"}
        sw = abs(ls.x - rs.x) * w
        hw = abs(lh.x - rh.x) * w
        ww = (sw + hw) / 2 * 0.82
        bw = sw * 1.05
        return {
            "pose_detected": True,
            "shoulder_width": round(sw, 1),
            "hip_width": round(hw, 1),
            "waist_width": round(ww, 1),
            "bust_width": round(bw, 1),
            "shoulder_hip_ratio": round(sw / hw, 3) if hw > 0 else 1.0,
            "waist_hip_ratio": round(ww / hw, 3) if hw > 0 else 0.8,
            "waist_shoulder_ratio": round(ww / sw, 3) if sw > 0 else 0.8,
        }
    except Exception as e:
        return {"pose_detected": True, "error": str(e)}


def _classify_body_shape(m):
    s_h = m.get("shoulder_hip_ratio", 1.0)
    w_s = m.get("waist_shoulder_ratio", 0.8)
    w_h = m.get("waist_hip_ratio", 0.8)
    if s_h > 1.15:
        return "inverted_triangle"
    if s_h < 0.90:
        return "pear"
    if w_h > 0.88:
        return "apple"
    if w_s < 0.76 and 0.90 <= s_h <= 1.10:
        return "hourglass"
    return "rectangle"


def _get_shape_outfit_advice(shape, gender, skin_tone, measurements):
    gl = "male" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "female"
    descs = {
        "hourglass": "balanced shoulders and hips with a defined waist",
        "rectangle": "similar shoulder, waist, and hip measurements",
        "pear": "hips wider than shoulders",
        "apple": "broader midsection with narrower hips",
        "inverted_triangle": "broad shoulders tapering to narrower hips",
    }
    prompt = f"""Top Indian fashion stylist. Client: {shape} body ({descs.get(shape, shape)}), {gl}, {skin_tone} skin, s/h ratio: {measurements.get('shoulder_hip_ratio', 1.0)}.

Return ONLY valid JSON:
{{
  "shape_label": "{shape.replace('_', ' ').title()}",
  "shape_description": "2 sentences about this shape",
  "what_works": ["5 outfit recommendations that flatter this shape for {gl}"],
  "what_to_avoid": ["3 things that don't work"],
  "key_pieces": ["Top","Bottom","Ethnic/Dress","Shoes","Accessory"],
  "styling_hack": "One powerful tip",
  "search_queries": {{
    "shirt": "specific {gl} {shape} body top query India",
    "pants": "specific {gl} {shape} body pants query India",
    "ethnic": "specific {gl} {shape} ethnic wear India"
  }}
}}"""
    try:
        resp = llm.invoke(prompt)
        raw = resp.content.strip() if hasattr(resp, "content") else str(resp)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"Body shape LLM error: {e}")

    FALLBACK = {
        "hourglass": {"what_works": ["Wrap dresses", "Fitted kurtas", "High-waist pants", "Belt-cinched outfits", "Bodycon styles"]},
        "rectangle": {"what_works": ["Layered looks", "Peplum tops", "A-line skirts", "Belted dresses", "Bold prints"]},
        "pear":      {"what_works": ["Bold shoulder tops", "A-line skirts", "Dark bottom bright top", "Structured shoulders", "Boat necklines"]},
        "apple":     {"what_works": ["V-necklines", "Flowy tunics", "Empire waist", "Palazzo pants", "Vertical patterns"]},
        "inverted_triangle": {"what_works": ["Wide-leg pants", "A-line skirts", "Flared bottoms", "Soft shoulder styles", "Solid tops"]},
    }
    fb = FALLBACK.get(shape, FALLBACK["rectangle"])
    return {
        "shape_label": shape.replace("_", " ").title(),
        "shape_description": f"Your {shape.replace('_', ' ')} body shape — {descs.get(shape, '')}.",
        **fb,
        "what_to_avoid": ["Clingy fabrics around problem areas", "Overly structured shoulders", "Stiff fabrics"],
        "key_pieces": ["Fitted top", "Well-cut bottom", "Ethnic suit", "Block heels", "Statement accessory"],
        "styling_hack": "Define your silhouette with a well-fitted outfit that emphasizes your best features.",
        "search_queries": {
            "shirt": f"{shape} body {gl} top India",
            "pants": f"{shape} body {gl} pants India",
            "ethnic": f"{shape} body {gl} ethnic India"
        },
    }


def _get_body_shape_products(shape: str, gender: str, skin_tone: str, advice: dict) -> dict:
    """
    Get products specifically recommended for the body shape.
    Uses curated queries that target flattering styles for each shape.
    """
    from services.product_service import get_product_recommendations

    gl = "male" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "female"

    # Use curated body-shape-specific queries
    shape_queries = BODY_SHAPE_PRODUCT_QUERIES.get(shape, {}).get(gl, {})

    # Override with LLM-generated queries if available and better
    llm_queries = advice.get("search_queries", {})

    # Merge: use LLM queries if they look specific, else fallback to curated
    final_queries = {}
    for cat in ["shirt", "pants", "ethnic"]:
        llm_q = llm_queries.get(cat, "")
        curated_q = shape_queries.get(cat, "")
        # Use LLM query if it contains shape-specific keywords, else use curated
        if llm_q and len(llm_q) > 20 and any(w in llm_q.lower() for w in [shape.replace("_", " "), "flatter", "define", "balance", "wide", "slim"]):
            final_queries[cat] = llm_q
        elif curated_q:
            final_queries[cat] = curated_q
        elif llm_q:
            final_queries[cat] = llm_q

    products = {}
    for cat, query in final_queries.items():
        try:
            prods = get_product_recommendations(query, cat)
            if prods:
                products[cat] = prods[:4]
        except Exception as e:
            print(f"Body shape product fetch error {cat}: {e}")

    return products


@body_shape_bp.route("/detect-body-shape", methods=["POST"])
def detect_body_shape():
    gender = request.form.get("gender", "male")
    skin_tone = request.form.get("skin_tone", "medium")
    if "image" not in request.files:
        return jsonify({"error": "image file required"}), 400
    file = request.files["image"]
    if not _allowed(file.filename):
        return jsonify({"error": "Unsupported file type"}), 415
    path, image_url = _save_file(file)
    try:
        m = _detect_body_measurements(path)
        if not m.get("pose_detected"):
            return jsonify({
                "error": "No full body detected. Upload a clear full-body photo.",
                "pose_detected": False
            }), 422
        if "error" in m:
            return jsonify({"error": m["error"], "pose_detected": True}), 422

        shape = _classify_body_shape(m)
        print(f"BODY SHAPE: {shape} | s/h={m.get('shoulder_hip_ratio')} w/s={m.get('waist_shoulder_ratio')}")

        advice = _get_shape_outfit_advice(shape, gender, skin_tone, m)

        # Get body-shape-specific products
        products = _get_body_shape_products(shape, gender, skin_tone, advice)

        return jsonify({
            "pose_detected": True,
            "body_shape": shape,
            "measurements": {k: v for k, v in m.items() if k != "pose_detected"},
            "advice": advice,
            "products": products,
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