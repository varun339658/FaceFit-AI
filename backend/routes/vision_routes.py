from flask import Blueprint, request, jsonify
from services.vision_service import detect_skin_issues
import os
import uuid
from services.vision_service import (
    detect_face,
    detect_face_landmarks,
    detect_face_shape,
    detect_skin_tone,
    draw_face_landmarks,
)

vision_bp = Blueprint("vision", __name__)
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    """Save uploaded image with a unique name to avoid collisions."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(path)
    return path


def handle_vision_request(processor_fn, *extra_args):
    """
    Generic handler: validate → save → process → clean up → respond.
    `processor_fn` receives the saved image path and returns a dict.
    Returns (json_response, http_status_code).
    """
    if "image" not in request.files:
        return jsonify({"error": "No image field in request"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 415

    path = save_uploaded_file(file)

    try:
        result = processor_fn(path, *extra_args)
    except Exception as exc:
        return jsonify({"error": f"Processing failed: {str(exc)}"}), 500
    finally:
        # Always clean up the temp upload (output files are kept intentionally)
        if os.path.exists(path):
            os.remove(path)

    return jsonify(result), 200


# ── Routes ──────────────────────────────────────────────────────────────────

@vision_bp.route("/detect-face", methods=["POST"])
def detect_face_api():
    return handle_vision_request(detect_face)


@vision_bp.route("/face-landmarks", methods=["POST"])
def face_landmarks_api():
    return handle_vision_request(detect_face_landmarks)


@vision_bp.route("/face-shape", methods=["POST"])
def face_shape_api():
    return handle_vision_request(detect_face_shape)


@vision_bp.route("/skin-tone", methods=["POST"])
def skin_tone_api():
    return handle_vision_request(detect_skin_tone)


@vision_bp.route("/draw-landmarks", methods=["POST"])
def draw_landmarks_api():
    if "image" not in request.files:
        return jsonify({"error": "No image field in request"}), 400

    file = request.files["image"]
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 415

    path = save_uploaded_file(file)

    try:
        output_path = draw_face_landmarks(path)
    except Exception as exc:
        return jsonify({"error": f"Processing failed: {str(exc)}"}), 500
    finally:
        if os.path.exists(path):
            os.remove(path)

    if output_path is None:
        return jsonify({"error": "No face detected in image"}), 422

    return jsonify({"image_path": output_path}), 200
@vision_bp.route("/detect-skin", methods=["POST"])
def detect_skin_api():
    return handle_vision_request(detect_skin_issues)