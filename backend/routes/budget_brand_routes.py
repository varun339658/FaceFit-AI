"""
budget_brand_routes.py — FaceFit Budget & Brand Preference API
===============================================================
Routes:
  GET  /preferences/brands/<user_id>      — get saved brands
  POST /preferences/brands/<user_id>      — save/add brands
  DELETE /preferences/brands/<user_id>/<brand> — remove a brand
  GET  /preferences/budget/<user_id>      — get budget range
  POST /preferences/budget/<user_id>      — set budget range
"""

from flask import Blueprint, request, jsonify
from services.budget_brand_service import (
    get_user_brands,
    save_user_brands,
    remove_user_brand,
    get_user_budget,
    save_user_budget,
)

preferences_bp = Blueprint("preferences", __name__)

# ── Brand Preference Routes ───────────────────────────────────────────────────

@preferences_bp.route("/preferences/brands/<user_id>", methods=["GET"])
def get_brands(user_id):
    brands = get_user_brands(user_id)
    return jsonify({"brands": brands, "total": len(brands)}), 200


@preferences_bp.route("/preferences/brands/<user_id>", methods=["POST"])
def add_brands(user_id):
    """
    Body: { "brands": ["Mango", "Zara", "FabIndia"] }
    """
    data = request.json or {}
    brands = data.get("brands", [])
    if not brands or not isinstance(brands, list):
        return jsonify({"error": "brands array required"}), 400
    result = save_user_brands(user_id, brands)
    return jsonify(result), 200


@preferences_bp.route("/preferences/brands/<user_id>/<brand>", methods=["DELETE"])
def delete_brand(user_id, brand):
    result = remove_user_brand(user_id, brand)
    return jsonify(result), 200


# ── Budget Routes ─────────────────────────────────────────────────────────────

@preferences_bp.route("/preferences/budget/<user_id>", methods=["GET"])
def get_budget(user_id):
    budget = get_user_budget(user_id)
    return jsonify(budget), 200


@preferences_bp.route("/preferences/budget/<user_id>", methods=["POST"])
def set_budget(user_id):
    """
    Body: { "min_price": 500, "max_price": 3000 }
    max_price: null means no upper limit
    """
    data = request.json or {}
    min_price = data.get("min_price", 0)
    max_price = data.get("max_price", None)
    try:
        min_price = int(min_price) if min_price is not None else 0
        max_price = int(max_price) if max_price is not None else None
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid price values"}), 400
    if min_price < 0:
        return jsonify({"error": "min_price cannot be negative"}), 400
    if max_price is not None and max_price < min_price:
        return jsonify({"error": "max_price must be >= min_price"}), 400
    result = save_user_budget(user_id, min_price, max_price)
    return jsonify(result), 200