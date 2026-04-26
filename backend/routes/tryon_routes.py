from flask import Blueprint, Response
import cv2
import mediapipe as mp
import numpy as np
import os

tryon_bp = Blueprint("tryon", __name__)

# ── Camera ─────────────────────────────────────────
camera = cv2.VideoCapture(0)

# ── MediaPipe Setup ────────────────────────────────
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# ── Base Directory ─────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Load Sunglasses (PNG ONLY) ─────────────────────
sunglasses_path = os.path.join(BASE_DIR, "uploads/sunglasses.png")

if not os.path.exists(sunglasses_path):
    raise FileNotFoundError("❌ sunglasses.png not found in uploads folder")

sunglasses = cv2.imread(sunglasses_path, cv2.IMREAD_UNCHANGED)

# Ensure transparency exists
if sunglasses.shape[2] == 3:
    # fallback (rare case)
    sunglasses = cv2.cvtColor(sunglasses, cv2.COLOR_BGR2BGRA)

print("✅ Sunglasses Loaded:", sunglasses.shape)


# ── Overlay Function ───────────────────────────────
def overlay(frame, overlay_img, x, y, w, h):

    overlay_img = cv2.resize(overlay_img, (w, h))

    h_frame, w_frame, _ = frame.shape

    # Boundary check
    if x < 0 or y < 0 or x + w > w_frame or y + h > h_frame:
        return frame

    alpha = overlay_img[:, :, 3] / 255.0

    for c in range(3):
        frame[y:y+h, x:x+w, c] = (
            alpha * overlay_img[:, :, c] +
            (1 - alpha) * frame[y:y+h, x:x+w, c]
        )

    return frame


# ── Frame Generator ───────────────────────────────
def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        if results.multi_face_landmarks:
            for face in results.multi_face_landmarks:

                h, w, _ = frame.shape

                # Eye landmarks
                left_eye  = face.landmark[33]
                right_eye = face.landmark[263]

                x1, y1 = int(left_eye.x * w), int(left_eye.y * h)
                x2, y2 = int(right_eye.x * w), int(right_eye.y * h)

                eye_distance = abs(x2 - x1)

                # 🔥 Perfect scaling
                width  = int(eye_distance * 1.8)
                height = int(width * 0.55)

                # 🔥 Perfect positioning
                x = int((x1 + x2) / 2 - width / 2)
                y = int((y1 + y2) / 2 - height / 2 - 10)

                frame = overlay(frame, sunglasses, x, y, width, height)

        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# ── Route ─────────────────────────────────────────
@tryon_bp.route("/tryon")
def tryon():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')