"""
register_routes.py — FaceFit Registration with Body Shape Analysis (FIXED)
===========================================================================
CHANGES:
  1. Body shape detection runs automatically during registration (MediaPipe)
  2. body_shape stored in face_analysis record and returned in response
  3. JWT issued as before
  4. Face validation still required
"""

from flask import Blueprint, request, jsonify
import os, uuid, re

from services.vision_service import (
    detect_face, detect_face_landmarks, detect_face_shape,
    detect_skin_tone, detect_skin_issues, save_face_analysis,
)
from services.outfit_scheduler_service import save_user_contact
from routes.auth_routes import issue_token

register_bp   = Blueprint("register", __name__)
UPLOAD_FOLDER = "uploads"


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def _validate_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-()]", "", phone)
    return bool(re.match(r"^(\+91)?[6-9]\d{9}$", cleaned))


def _normalize_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-()]", "", phone)
    if not cleaned.startswith("+"):
        cleaned = "+91" + cleaned.lstrip("91")
    return cleaned


def _detect_body_shape_from_file(filepath: str) -> dict:
    """
    Run MediaPipe Pose on the selfie to attempt body shape detection.
    Falls back gracefully — registration never fails because of this.
    """
    try:
        import cv2, numpy as np, mediapipe as mp
        mp_pose = mp.solutions.pose
        image   = cv2.imread(filepath)
        if image is None:
            return {"body_shape": "average", "pose_detected": False}
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]
        with mp_pose.Pose(static_image_mode=True, model_complexity=1,
                          min_detection_confidence=0.4) as pose:
            results = pose.process(rgb)
        if not results.pose_landmarks:
            return {"body_shape": "average", "pose_detected": False}
        lm = results.pose_landmarks.landmark
        ls, rs = lm[11], lm[12]
        lh, rh = lm[23], lm[24]
        if any(pt.visibility < 0.3 for pt in [ls, rs, lh, rh]):
            return {"body_shape": "average", "pose_detected": False}
        sw = abs(ls.x - rs.x) * w
        hw = abs(lh.x - rh.x) * w
        ww = (sw + hw) / 2 * 0.82
        s_h = sw / hw if hw > 0 else 1.0
        w_s = ww / sw if sw > 0 else 0.8
        w_h = ww / hw if hw > 0 else 0.8
        if s_h > 1.15:
            shape = "inverted_triangle"
        elif s_h < 0.90:
            shape = "pear"
        elif w_h > 0.88:
            shape = "apple"
        elif w_s < 0.76 and 0.90 <= s_h <= 1.10:
            shape = "hourglass"
        else:
            shape = "rectangle"
        return {
            "body_shape": shape,
            "pose_detected": True,
            "shoulder_hip_ratio": round(s_h, 3),
            "waist_shoulder_ratio": round(w_s, 3),
        }
    except Exception as e:
        print(f"Body shape detection (non-fatal): {e}")
        return {"body_shape": "average", "pose_detected": False}


@register_bp.route("/register", methods=["POST"])
def register_user():

    name   = request.form.get("name",   "").strip()
    gender = request.form.get("gender", "male").strip()
    email  = request.form.get("email",  "").strip()
    phone  = request.form.get("phone",  "").strip()

    # ── Validate ──────────────────────────────────────────────────────────────
    errors = []
    if not name:
        errors.append("Name is required")
    if not email:
        errors.append("Email is required")
    elif not _validate_email(email):
        errors.append("Please enter a valid email address (e.g. you@example.com)")
    if not phone:
        errors.append("Phone number is required")
    elif not _validate_phone(phone):
        errors.append("Please enter a valid Indian mobile number (10 digits or +91XXXXXXXXXX)")
    if "image" not in request.files:
        errors.append("Profile photo is required")

    if errors:
        return jsonify({"error": errors[0], "all_errors": errors}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No photo selected"}), 400

    # Save uploaded image
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file.save(filepath)

    phone_normalized = _normalize_phone(phone)

    # ── Face analysis ─────────────────────────────────────────────────────────
    try:
        face = detect_face(filepath)
        if not face.get("face_detected", False):
            import os as _os
            if _os.path.exists(filepath):
                _os.remove(filepath)
            return jsonify({
                "error": "No face detected in the uploaded photo. Please upload a clear selfie.",
                "face_detected": False,
            }), 422

        landmarks = detect_face_landmarks(filepath)
        shape     = detect_face_shape(filepath)
        tone      = detect_skin_tone(filepath)
        skin      = detect_skin_issues(filepath)
    except Exception as e:
        return jsonify({"error": f"Face analysis failed: {str(e)}"}), 500

    # ── Body shape detection (runs on the same selfie — best effort) ──────────
    body_result = _detect_body_shape_from_file(filepath)
    body_shape  = body_result.get("body_shape", "average")
    print(f"👤 Body shape from selfie: {body_shape} (pose_detected={body_result.get('pose_detected')})")

    # Deduplicate YOLO conditions
    raw_detections     = skin.get("detections", [])
    seen               = set()
    unique_conditions  = []
    for d in raw_detections:
        d_clean = d.lower().strip()
        if d_clean and d_clean not in seen:
            seen.add(d_clean)
            unique_conditions.append(d_clean)

    # Save face analysis (including body shape)
    save_face_analysis(
        user_id    = name,
        face_shape = shape["face_shape"],
        skin_tone  = tone["skin_tone"],
        acne_count = skin["total_detected"],
        conditions = raw_detections,
        landmarks  = landmarks.get("landmarks_count", 0),
    )

    # Also store body_shape in face_analysis record
    try:
        from utils.db import face_collection
        from datetime import datetime
        face_collection.update_one(
            {"userId": name},
            {"$set": {"bodyShape": body_shape, "bodyShapeData": body_result, "updatedAt": datetime.utcnow()}},
            upsert=False,
        )
    except Exception as e:
        print(f"Body shape DB save (non-fatal): {e}")

    # Save contact info
    save_user_contact(name, email, phone_normalized)

    # Also save gender and userId to users collection for WhatsApp lookup
    try:
        from utils.db import users_collection
        from datetime import datetime
        users_collection.update_one(
            {"phone": phone_normalized},
            {"$set": {
                "userId":     name,
                "user_id":    name,
                "name":       name,
                "gender":     gender,
                "email":      email,
                "phone":      phone_normalized,
                "updated_at": datetime.utcnow(),
            }},
            upsert=True,
        )
    except Exception as e:
        print(f"Users collection update (non-fatal): {e}")

    # Issue JWT
    token = issue_token(name)

    print(
        f"✅ REGISTER → name={name} | gender={gender} | email={email} | "
        f"phone={phone_normalized} | tone={tone['skin_tone']} | "
        f"face={shape['face_shape']} | body={body_shape}"
    )

    return jsonify({
        "name":         name,
        "gender":       gender,
        "email":        email,
        "phone":        phone_normalized,
        "face_shape":   shape["face_shape"],
        "skinTone":     tone["skin_tone"],
        "conditions":   raw_detections,
        "body_shape":   body_shape,
        "access_token": token,
    })