from flask import Blueprint, request, jsonify
from services.skin_rag_service import generate_skin_recommendation
from services.product_service import get_product_recommendations

product_bp = Blueprint("products", __name__)

@product_bp.route("/products", methods=["POST"])
def get_products():

    data = request.json
    print("REQUEST DATA:", data)

    skin_tone = data["skin_tone"]["skin_tone"]
    conditions = data["skin_analysis"]["detections"]

    rag_json = generate_skin_recommendation(skin_tone, conditions)

    ingredients = rag_json["ingredients"]
    print("INGREDIENTS:", ingredients)

    products = {}

    for category, query in ingredients.items():

        results = get_product_recommendations(query)

        print("CATEGORY:", category)
        print("RESULTS:", results)

        products[category] = results

    return jsonify({
        "routine": rag_json["routine"],
        "products": products
    })