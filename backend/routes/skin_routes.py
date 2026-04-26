from flask import Blueprint, request, jsonify
from services.skin_rag_service import generate_skin_recommendation

skin_bp = Blueprint("skin", __name__)

@skin_bp.route("/skin-recommendation", methods=["POST"])
def skin_recommendation():

    data = request.json

    skin_tone = data["skinTone"]
    skin_conditions = data["conditions"]

    recommendation = generate_skin_recommendation(
        skin_tone,
        skin_conditions
    )

    return jsonify({
        "recommendation": recommendation
    })