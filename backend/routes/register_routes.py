from flask import Blueprint, request, jsonify
import os
import uuid

from services.vision_service import (
    detect_face,
    detect_face_landmarks,
    detect_face_shape,
    detect_skin_tone,
    detect_skin_issues,
    save_face_analysis
)

register_bp = Blueprint("register", __name__)

UPLOAD_FOLDER = "uploads"


@register_bp.route("/register", methods=["POST"])
def register_user():

    name = request.form.get("name")
    file = request.files["image"]

    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file.save(filepath)

    face = detect_face(filepath)
    landmarks = detect_face_landmarks(filepath)
    shape = detect_face_shape(filepath)
    tone = detect_skin_tone(filepath)
    skin = detect_skin_issues(filepath)

    save_face_analysis(
        user_id=name,
        face_shape=shape["face_shape"],
        skin_tone=tone["skin_tone"],
        acne_count=skin["total_detected"],
        conditions=skin["detections"],
        landmarks=landmarks["landmarks_count"]
    )

    return jsonify({
        "name": name,
        "face_detection": face,
        "landmarks": landmarks,
        "face_shape": shape,
        "skin_tone": tone,
        "skin_analysis": skin
    })