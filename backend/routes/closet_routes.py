"""
closet_routes.py — v3
══════════════════════
Routes:
  POST /closet/add           — upload item image → AI detect → add
  GET  /closet/<user_id>     — get all wardrobe items
  DELETE /closet/<user_id>/<item_id> — remove item
  POST /closet/outfit        — plan outfit for specific event
  GET  /closet/summary/<user_id>     — summary + gaps + ready events
  GET  /closet/mix-match/<user_id>   — AI mix & match all combinations
  GET  /closet/suggestions/<user_id> — outfit suggestions for multiple events
  GET  /closet/gap-analysis/<user_id>— style gap analysis
  POST /closet/outfit-event  — plan outfit for any of 20+ events
"""

from flask import Blueprint, request, jsonify
import os, uuid, base64
from services.closet_agent import (
    add_to_closet, get_wardrobe, delete_wardrobe_item,
    plan_outfit_for_event, get_closet_summary,
    mix_and_match, get_outfit_suggestions, style_gap_analysis,
    plan_multiple_outfits_for_event,
)

closet_bp = Blueprint("closet", __name__)
UPLOAD_FOLDER = "uploads"
ALLOWED = {"jpg","jpeg","png","webp"}


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


def _save_file(file):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, name)
    file.save(path)
    return path, name


@closet_bp.route("/closet/add", methods=["POST"])
def add_item():
    user_id = request.form.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400
    file = request.files["image"]
    if not _allowed(file.filename):
        return jsonify({"error": "Unsupported file type"}), 415
    path, fname = _save_file(file)
    try:
        image_url = f"/uploads/{fname}"
        item = add_to_closet(user_id, path, image_url)
        return jsonify({"success": True, "item": item}), 200
    except Exception as e:
        print(f"Closet add error: {e}")
        return jsonify({"error": str(e)}), 500


@closet_bp.route("/closet/<user_id>", methods=["GET"])
def get_closet(user_id):
    try:
        items = get_wardrobe(user_id)
        return jsonify({"items": items, "total": len(items)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@closet_bp.route("/closet/<user_id>/<item_id>", methods=["DELETE"])
def remove_item(user_id, item_id):
    try:
        success = delete_wardrobe_item(user_id, item_id)
        return jsonify({"success": success}), 200 if success else 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@closet_bp.route("/closet/outfit", methods=["POST"])
def outfit_for_event():
    data = request.json
    user_id = data.get("user_id")
    event   = data.get("event","")
    profile = data.get("user_context",{})
    if not user_id or not event:
        return jsonify({"error": "user_id and event required"}), 400
    try:
        result = plan_outfit_for_event(user_id, event, profile)
        return jsonify(result), 200
    except Exception as e:
        print(f"Outfit plan error: {e}")
        return jsonify({"error": str(e)}), 500


@closet_bp.route("/closet/outfit-event", methods=["POST"])
def outfit_for_any_event():
    """Plan outfit for any of 20+ events."""
    data    = request.json
    user_id = data.get("user_id")
    event   = data.get("event","casual")
    profile = data.get("user_context",{})
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    try:
        result = plan_outfit_for_event(user_id, event, profile)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@closet_bp.route("/closet/multi-outfit", methods=["POST"])
def multi_outfit_for_event():
    """Plan 2-3 complete outfit combinations for any event."""
    data    = request.json
    user_id = data.get("user_id")
    event   = data.get("event","casual")
    profile = data.get("user_context",{})
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    try:
        result = plan_multiple_outfits_for_event(user_id, event, profile)
        return jsonify(result), 200
    except Exception as e:
        print(f"Multi-outfit error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@closet_bp.route("/closet/summary/<user_id>", methods=["GET"])
def closet_summary(user_id):
    try:
        summary = get_closet_summary(user_id)
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@closet_bp.route("/closet/mix-match/<user_id>", methods=["GET"])
def mix_match(user_id):
    """AI mix & match — all possible outfit combinations with color scores."""
    skin_tone = request.args.get("skin_tone","medium")
    event     = request.args.get("event", None)
    try:
        result = mix_and_match(user_id, skin_tone, event)
        return jsonify(result), 200
    except Exception as e:
        print(f"Mix & match error: {e}")
        return jsonify({"error": str(e)}), 500


@closet_bp.route("/closet/suggestions/<user_id>", methods=["GET"])
def outfit_suggestions(user_id):
    """Outfit suggestions for multiple events from wardrobe."""
    skin_tone  = request.args.get("skin_tone","medium")
    gender     = request.args.get("gender","male")
    face_shape = request.args.get("face_shape","oval")
    try:
        result = get_outfit_suggestions(user_id, skin_tone, gender, face_shape)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@closet_bp.route("/closet/gap-analysis/<user_id>", methods=["GET"])
def gap_analysis(user_id):
    """Style gap analysis — what you need for each event type."""
    try:
        result = style_gap_analysis(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500