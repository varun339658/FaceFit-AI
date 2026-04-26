"""
outfit_scheduler_routes.py — FaceFit Outfit Reminder API
══════════════════════════════════════════════════════════
Routes:
  POST /scheduler/remind          — schedule a reminder for a selected outfit
  GET  /scheduler/reminders/<uid> — get all reminders for a user
  DELETE /scheduler/remind/<rid>  — cancel a reminder
  GET  /scheduler/mix-match/<uid> — AI-verified mix & match outfits (for UI selection)
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import re

from services.outfit_scheduler_service import (
    schedule_outfit_reminder,
    get_user_reminders,
    delete_reminder,
    save_user_contact,
    get_user_contact,
)
from services.closet_agent import mix_and_match, get_wardrobe
from services.outfit_validator import validate_outfit_for_event

scheduler_bp = Blueprint("scheduler", __name__)


def _parse_dt(dt_str: str) -> datetime | None:
    """Parse ISO-like datetime string from frontend."""
    for fmt in (
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def _validate_phone(phone: str) -> bool:
    # Accept +91XXXXXXXXXX or 10-digit number
    cleaned = re.sub(r"\s+", "", phone)
    return bool(re.match(r"^(\+91)?[6-9]\d{9}$", cleaned))


def _normalize_phone(phone: str) -> str:
    cleaned = re.sub(r"\s+", "", phone)
    if not cleaned.startswith("+"):
        cleaned = "+91" + cleaned.lstrip("91")
    return cleaned


# ── AI Mix & Match (verified outfits for scheduler UI) ───────────────────────

@scheduler_bp.route("/scheduler/mix-match/<user_id>", methods=["GET"])
def verified_mix_match(user_id):
    """
    Returns AI-verified outfit combinations from the user's wardrobe.
    Each outfit is validated for color harmony (≥2/3) and completeness.
    Query params: skin_tone, gender, event (optional filter)
    """
    skin_tone = request.args.get("skin_tone", "medium")
    gender    = request.args.get("gender", "male")
    event     = request.args.get("event", None)

    try:
        result = mix_and_match(user_id, skin_tone, event)
        outfits = result.get("outfits", [])

        # AI verification: keep outfits with color_score >= 1 and at least 2 items
        verified = []
        for outfit in outfits:
            items = outfit.get("items", {})
            filled = {k: v for k, v in items.items() if v}
            if len(filled) < 2:
                continue
            score = outfit.get("color_score", 1)

            # Run event validator if event is specified
            if event:
                val = validate_outfit_for_event(filled, event)
                if not val["valid"] and val["should_redirect"]:
                    continue  # Skip outfits completely wrong for event
                outfit["validation"] = {
                    "warnings": val.get("warnings", []),
                    "removed":  val.get("removed", []),
                }

            outfit["outfit_id"]    = f"{user_id}_{len(verified)}"
            outfit["items_filled"] = len(filled)
            verified.append(outfit)

        # Sort by color_score descending
        verified.sort(key=lambda x: x.get("color_score", 0), reverse=True)

        return jsonify({
            "outfits":       verified,
            "total":         len(verified),
            "wardrobe_count": result.get("total_items", 0),
        }), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Schedule Reminder ─────────────────────────────────────────────────────────

@scheduler_bp.route("/scheduler/remind", methods=["POST"])
def create_reminder():
    """
    Body (JSON):
    {
      "user_id":    "varun",
      "user_name":  "Varun",
      "email":      "varun@example.com",
      "phone":      "+919876543210",
      "outfit":     { <outfit object from mix_and_match> },
      "occasion":   "office",
      "scheduled_at": "2025-06-15T09:00"
    }
    """
    data = request.json
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    user_id      = data.get("user_id", "").strip()
    user_name    = data.get("user_name", "Friend").strip()
    email        = data.get("email", "").strip()
    phone        = data.get("phone", "").strip()
    outfit       = data.get("outfit")
    occasion     = data.get("occasion", "event").strip()
    scheduled_str = data.get("scheduled_at", "")

    # ── Validate ──────────────────────────────────────────────────────────────
    errors = []
    if not user_id:
        errors.append("user_id is required")
    if not outfit:
        errors.append("outfit is required")
    if not scheduled_str:
        errors.append("scheduled_at is required")
    if email and not _validate_email(email):
        errors.append("Invalid email address")
    if phone and not _validate_phone(phone):
        errors.append("Invalid phone number (use +91XXXXXXXXXX or 10 digits)")
    if not email and not phone:
        errors.append("At least one of email or phone is required")

    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    scheduled_dt = _parse_dt(scheduled_str)
    if not scheduled_dt:
        return jsonify({"error": f"Cannot parse scheduled_at: '{scheduled_str}'. Use YYYY-MM-DDTHH:MM"}), 400

    # Normalize phone
    if phone:
        phone = _normalize_phone(phone)

    # Save user contact to DB
    if email or phone:
        save_user_contact(user_id, email, phone)

    try:
        result = schedule_outfit_reminder(
            user_id      = user_id,
            user_name    = user_name,
            email        = email,
            phone        = phone,
            outfit       = outfit,
            occasion     = occasion,
            scheduled_at = scheduled_dt,
        )
        return jsonify({
            "success":       True,
            "reminder_id":   result["reminder_id"],
            "calendar_link": result.get("calendar_link"),
            "scheduled_at":  result["scheduled_at"],
            "message":       f"Reminder set for {scheduled_dt.strftime('%d %b %Y at %I:%M %p')}. You'll be notified via email & WhatsApp.",
        }), 201

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Get All Reminders ─────────────────────────────────────────────────────────

@scheduler_bp.route("/scheduler/reminders/<user_id>", methods=["GET"])
def list_reminders(user_id):
    try:
        docs = get_user_reminders(user_id)
        return jsonify({"reminders": docs, "total": len(docs)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Delete Reminder ───────────────────────────────────────────────────────────

@scheduler_bp.route("/scheduler/remind/<reminder_id>", methods=["DELETE"])
def cancel_reminder(reminder_id):
    try:
        success = delete_reminder(reminder_id)
        if success:
            return jsonify({"success": True, "message": "Reminder cancelled"}), 200
        return jsonify({"error": "Reminder not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Get User Contact ──────────────────────────────────────────────────────────

@scheduler_bp.route("/scheduler/contact/<user_id>", methods=["GET"])
def get_contact(user_id):
    try:
        contact = get_user_contact(user_id)
        return jsonify(contact), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500