"""
skin_progress_routes.py — FaceFit Skincare Progress Tracker (UPDATED)
======================================================================
NEW in this version:
  - /skin/scan now calls skin_explainer_service.generate_condition_explanations()
    and returns "explanations" field with plain-English condition breakdown
  - All existing routes preserved unchanged
"""

from flask import Blueprint, request, jsonify
from pymongo import MongoClient
import os, uuid
from datetime import datetime

from services.vision_service import detect_skin_issues

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority",
)
_client   = MongoClient(MONGO_URI)
_db       = _client["facefit_ai"]
scans_col = _db["skin_scans"]

UPLOAD_FOLDER = "uploads"
ALLOWED       = {"jpg", "jpeg", "png", "webp"}

skin_progress_bp = Blueprint("skin_progress", __name__)


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


def _save_file(file) -> tuple:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ext  = file.filename.rsplit(".", 1)[-1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, name)
    file.save(path)
    return path, f"/uploads/{name}"


def _summarize(detections: list) -> dict:
    summary = {"acne_count": 0, "dark_circle_count": 0, "dark_spot_count": 0, "total": 0}
    for d in detections:
        d_lower = d.lower()
        if "acne" in d_lower:
            summary["acne_count"] += 1
        elif "dark circle" in d_lower or "dark_circle" in d_lower:
            summary["dark_circle_count"] += 1
        elif "dark spot" in d_lower or "dark_spot" in d_lower:
            summary["dark_spot_count"] += 1
        summary["total"] += 1
    return summary


def _compute_deltas(scans: list) -> list:
    result = []
    for i, scan in enumerate(scans):
        entry = dict(scan)
        if i == 0:
            entry["delta"] = None
            entry["delta_label"] = "Baseline"
        else:
            prev = scans[i - 1]["summary"]
            curr = scan["summary"]
            d    = {
                "acne":        curr["acne_count"]        - prev["acne_count"],
                "dark_circle": curr["dark_circle_count"] - prev["dark_circle_count"],
                "dark_spot":   curr["dark_spot_count"]   - prev["dark_spot_count"],
                "total":       curr["total"]              - prev["total"],
            }
            entry["delta"] = d
            if d["total"] < 0:
                entry["delta_label"] = f"↓ {abs(d['total'])} fewer detections"
            elif d["total"] > 0:
                entry["delta_label"] = f"↑ {d['total']} more detections"
            else:
                entry["delta_label"] = "No change"
        result.append(entry)
    return result


def _trend_message(scans: list) -> str:
    if len(scans) < 2:
        return "Keep up your routine! Come back next week to see your progress."
    first  = scans[0]["summary"]
    latest = scans[-1]["summary"]
    weeks  = len(scans) - 1
    acne_diff = first["acne_count"] - latest["acne_count"]
    dc_diff   = first["dark_circle_count"] - latest["dark_circle_count"]
    ds_diff   = first["dark_spot_count"]   - latest["dark_spot_count"]
    parts = []
    if acne_diff > 0:
        parts.append(f"acne reduced by {acne_diff} spot{'s' if acne_diff > 1 else ''}")
    elif acne_diff < 0:
        parts.append(f"acne increased by {abs(acne_diff)} spot{'s' if abs(acne_diff) > 1 else ''}")
    if dc_diff > 0:
        parts.append("dark circles improved")
    if ds_diff > 0:
        parts.append("dark spots fading")
    if not parts:
        return f"Your skin has stayed consistent over {weeks} week{'s' if weeks > 1 else ''}. Keep following your routine!"
    return f"Over {weeks} week{'s' if weeks > 1 else ''}: {' and '.join(parts)}. Great progress!"


# ── NEW: Skin Condition Explainer helper ──────────────────────────────────────

def _get_condition_explanations(detections: list, skin_tone: str, summary: dict) -> dict:
    """
    Call Groq LLaMA via skin_explainer_service for plain-English condition explanations.
    Returns {} on any error (non-fatal — never blocks the scan from saving).
    """
    try:
        from services.skin_explainer_service import generate_condition_explanations
        if not detections:
            return {}
        unique_conds = list(dict.fromkeys(d.lower().strip() for d in detections if d.strip()))
        severity_counts = {
            "acne_count":        summary.get("acne_count", 0),
            "dark_circle_count": summary.get("dark_circle_count", 0),
            "dark_spot_count":   summary.get("dark_spot_count", 0),
        }
        return generate_condition_explanations(
            conditions=unique_conds,
            skin_tone=skin_tone,
            severity_counts=severity_counts,
        )
    except Exception as e:
        print(f"Skin explainer (non-fatal): {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@skin_progress_bp.route("/skin/scan", methods=["POST"])
def submit_skin_scan():
    """
    Accept a weekly selfie, run YOLO skin detection, store results.
    Form fields: user_id (text), skin_tone (text, optional), image (file)
    NEW: returns "explanations" field with AI-generated condition breakdown.
    """
    user_id   = request.form.get("user_id",   "").strip()
    skin_tone = request.form.get("skin_tone",  "medium").strip()

    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    if "image" not in request.files:
        return jsonify({"error": "image file required"}), 400

    file = request.files["image"]
    if not _allowed(file.filename):
        return jsonify({"error": "Unsupported file type"}), 415

    path, image_url = _save_file(file)

    try:
        result     = detect_skin_issues(path)
        detections = result.get("detections", [])
        summary    = _summarize(detections)

        existing_count = scans_col.count_documents({"userId": user_id})
        week_number    = existing_count + 1

        # ── NEW: Generate condition explanations (Groq + RAG) ─────────────────
        condition_explanations = _get_condition_explanations(detections, skin_tone, summary)

        doc = {
            "scan_id":     uuid.uuid4().hex,
            "userId":      user_id,
            "week_number": week_number,
            "scan_date":   datetime.utcnow(),
            "photo_url":   image_url,
            "detections":  detections,
            "summary":     summary,
        }
        scans_col.insert_one(doc)

        return jsonify({
            "success":      True,
            "week_number":  week_number,
            "summary":      summary,
            "detections":   detections,
            "message":      f"Week {week_number} scan saved. {summary['total']} condition(s) detected.",
            "explanations": condition_explanations,   # ← NEW
        }), 201

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@skin_progress_bp.route("/skin/progress/<user_id>", methods=["GET"])
def get_progress(user_id):
    raw_scans = list(scans_col.find({"userId": user_id}, {"_id": 0}, sort=[("scan_date", 1)]))
    if not raw_scans:
        return jsonify({"scans": [], "total_weeks": 0,
                        "trend_message": "No scans yet. Upload your first weekly selfie to start tracking!",
                        "chart_data": {}}), 200
    for s in raw_scans:
        if isinstance(s.get("scan_date"), datetime):
            s["scan_date"] = s["scan_date"].isoformat()
    scans_with_delta = _compute_deltas(raw_scans)
    trend            = _trend_message(raw_scans)
    labels      = [f"Week {s['week_number']}" for s in raw_scans]
    acne_series = [s["summary"]["acne_count"]        for s in raw_scans]
    dc_series   = [s["summary"]["dark_circle_count"] for s in raw_scans]
    ds_series   = [s["summary"]["dark_spot_count"]   for s in raw_scans]
    return jsonify({
        "scans":         scans_with_delta,
        "total_weeks":   len(raw_scans),
        "trend_message": trend,
        "chart_data":    {"labels": labels, "acne": acne_series, "dark_circles": dc_series, "dark_spots": ds_series},
    }), 200


@skin_progress_bp.route("/skin/progress/latest/<user_id>", methods=["GET"])
def get_latest_scan(user_id):
    scan = scans_col.find_one({"userId": user_id}, {"_id": 0}, sort=[("scan_date", -1)])
    if not scan:
        return jsonify({"error": "No scans found"}), 404
    if isinstance(scan.get("scan_date"), datetime):
        scan["scan_date"] = scan["scan_date"].isoformat()
    return jsonify(scan), 200


@skin_progress_bp.route("/skin/scan/<scan_id>", methods=["DELETE"])
def delete_scan(scan_id):
    result = scans_col.delete_one({"scan_id": scan_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Scan not found"}), 404
    return jsonify({"success": True, "message": "Scan deleted"}), 200


@skin_progress_bp.route("/skin/scan/<scan_id>/user/<user_id>", methods=["DELETE"])
def delete_scan_and_renumber(scan_id, user_id):
    result = scans_col.delete_one({"scan_id": scan_id, "userId": user_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Scan not found"}), 404
    remaining = list(scans_col.find({"userId": user_id}, sort=[("scan_date", 1)]))
    for i, scan in enumerate(remaining):
        scans_col.update_one({"_id": scan["_id"]}, {"$set": {"week_number": i + 1}})
    return jsonify({"success": True, "message": "Scan deleted and weeks renumbered",
                    "remaining_scans": len(remaining)}), 200


@skin_progress_bp.route("/skin/scan/<scan_id>", methods=["PATCH"])
def update_scan_note(scan_id):
    data = request.json or {}
    note = data.get("note", "").strip()
    if not note:
        return jsonify({"error": "Note is required"}), 400
    result = scans_col.update_one(
        {"scan_id": scan_id},
        {"$set": {"note": note, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        return jsonify({"error": "Scan not found"}), 404
    return jsonify({"success": True, "message": "Note updated"}), 200