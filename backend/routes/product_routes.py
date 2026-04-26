from flask import Blueprint, request, jsonify
from services.skin_rag_service import generate_skin_recommendation
from services.product_service import get_product_recommendations

product_bp = Blueprint("products", __name__)


@product_bp.route("/products", methods=["POST"])
def get_products():
    data = request.json
    print("SKINCARE REQUEST:", data)

    skin_tone  = data.get("skinTone", "medium")
    raw_conditions = data.get("conditions", [])

    # ── FIX: Deduplicate conditions — YOLO detects same class N times ─────────
    # e.g. ['acne','acne','acne','dark circle','acne'] → ['acne','dark circle']
    seen = set()
    conditions = []
    for c in raw_conditions:
        c_clean = c.lower().strip()
        if c_clean and c_clean not in seen:
            seen.add(c_clean)
            conditions.append(c_clean)

    if not conditions:
        conditions = ["normal skin"]

    print("UNIQUE CONDITIONS:", conditions)

    # ── Step 1: AI + RAG generates routine + ingredient search queries ─────────
    rag_json = generate_skin_recommendation(skin_tone, conditions)

    ingredients = rag_json.get("ingredients", {})
    routine     = rag_json.get("routine", {})

    print("INGREDIENTS:", ingredients)

    # ── Step 2: Fetch real products for each ingredient ───────────────────────
    products = {}

    for category, query in ingredients.items():
        print(f"FETCHING [{category}]: {query}")
        try:
            results = get_product_recommendations(query, category)
            products[category] = results
        except Exception as e:
            print(f"ERROR [{category}]:", e)
            products[category] = []

    return jsonify({
        "routine":     routine,
        "ingredients": ingredients,
        "products":    products,
    })