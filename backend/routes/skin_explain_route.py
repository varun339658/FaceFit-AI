"""
skin_explain_route.py — FIXED: Added CORS + correct blueprint registration
"""
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from services.skin_explainer_service import generate_condition_explanations

skin_explain_bp = Blueprint("skin_explain", __name__)


@skin_explain_bp.route("/skin/explain", methods=["POST", "OPTIONS"])
@cross_origin()
def explain_skin_conditions():
    """
    Generate plain-English explanations for skin conditions.

    Body:
    {
      "conditions": ["acne", "dark circle"],
      "skin_tone": "medium",
      "severity_counts": {"acne_count": 5, "dark_circle_count": 2}
    }
    """
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.json or {}
    conditions      = data.get("conditions", [])
    skin_tone       = data.get("skin_tone", "medium")
    severity_counts = data.get("severity_counts", {})

    if not conditions:
        return jsonify({"error": "conditions array required"}), 400

    # Deduplicate conditions
    seen, unique = set(), []
    for c in conditions:
        k = c.lower().strip()
        if k and k not in seen:
            seen.add(k)
            unique.append(k)

    if not unique:
        return jsonify({"error": "No valid conditions provided"}), 400

    try:
        result = generate_condition_explanations(unique, skin_tone, severity_counts)
        return jsonify(result), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500