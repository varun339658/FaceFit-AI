from flask import Blueprint, request, Response, jsonify
from flask_cors import CORS
import cv2
import mediapipe as mp
import numpy as np
import os
from rembg import remove
from PIL import Image
import io
import uuid

tryon_bp = Blueprint("virtual_tryon", __name__)

# ── Enable CORS on this blueprint ──
# (also call CORS(app) in your main app.py)

# ── Camera ─────────────────────────
camera = cv2.VideoCapture(0)

# ── MediaPipe ──────────────────────
mp_face_mesh = mp.solutions.face_mesh
mp_hands     = mp.solutions.hands

face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)
hands     = mp_hands.Hands(max_num_hands=1)

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

current_accessory = None
current_type      = None


# ── BACKGROUND REMOVAL ─────────────
def remove_bg_and_save(file):
    img    = Image.open(file.stream).convert("RGBA")
    output = remove(img)

    filename = f"{uuid.uuid4().hex}.png"
    path     = os.path.join(UPLOAD_FOLDER, filename)
    output.save(path)
    return path


# ── SAFE OVERLAY ───────────────────
def overlay(frame, overlay_img, x, y, w, h):
    if w <= 0 or h <= 0:
        return frame

    fh, fw = frame.shape[:2]

    # Clip to frame boundaries
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + w, fw), min(y + h, fh)

    if x2 <= x1 or y2 <= y1:
        return frame

    # Corresponding region in the overlay image
    ox1 = x1 - x
    oy1 = y1 - y
    ox2 = ox1 + (x2 - x1)
    oy2 = oy1 + (y2 - y1)

    resized = cv2.resize(overlay_img, (w, h))
    roi     = resized[oy1:oy2, ox1:ox2]

    alpha = roi[:, :, 3:4] / 255.0
    frame[y1:y2, x1:x2] = (alpha * roi[:, :, :3] +
                             (1 - alpha) * frame[y1:y2, x1:x2]).astype(np.uint8)
    return frame


# ── UPLOAD API ─────────────────────
@tryon_bp.route("/upload-accessory", methods=["POST"])
def upload_accessory():
    global current_accessory, current_type

    file     = request.files["image"]
    acc_type = request.form.get("type")   # sunglasses / earrings / bracelet / ring / necklace / hat

    path = remove_bg_and_save(file)
    img  = cv2.imread(path, cv2.IMREAD_UNCHANGED)

    current_accessory = img
    current_type      = acc_type

    return jsonify({"success": True})


# ── RESET API ──────────────────────
@tryon_bp.route("/reset-accessory", methods=["POST"])
def reset_accessory():
    global current_accessory, current_type
    current_accessory = None
    current_type      = None
    return jsonify({"success": True})


# ── FRAME GENERATOR ────────────────
def generate_frames():
    global current_accessory, current_type

    while True:
        success, frame = camera.read()
        if not success:
            break

        h, w, _ = frame.shape

        if current_accessory is not None:

            # ── SUNGLASSES ──────────────────────────────────────────────────
            if current_type == "sunglasses":
                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb)

                if results.multi_face_landmarks:
                    face = results.multi_face_landmarks[0]

                    # Outer eye corners (more accurate width reference)
                    left_outer  = face.landmark[33]    # left outer canthus
                    right_outer = face.landmark[263]   # right outer canthus

                    # Eye-centre landmarks for vertical positioning
                    left_eye_top    = face.landmark[159]
                    left_eye_bottom = face.landmark[145]
                    right_eye_top   = face.landmark[386]
                    right_eye_bottom= face.landmark[374]

                    lx1 = int(left_outer.x  * w)
                    rx2 = int(right_outer.x * w)

                    eye_center_y = int(((left_eye_top.y + left_eye_bottom.y +
                                         right_eye_top.y + right_eye_bottom.y) / 4) * h)

                    acc_w = int(abs(rx2 - lx1) * 1.55)
                    acc_h = int(acc_w * 0.42)

                    acc_x = int((lx1 + rx2) / 2 - acc_w / 2)
                    acc_y = eye_center_y - acc_h // 2   # centred on eye-line

                    frame = overlay(frame, current_accessory, acc_x, acc_y, acc_w, acc_h)

            # ── EARRINGS ────────────────────────────────────────────────────
            elif current_type == "earrings":
                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb)

                if results.multi_face_landmarks:
                    face = results.multi_face_landmarks[0]

                    # Ear-lobe reference points
                    left_ear  = face.landmark[234]
                    right_ear = face.landmark[454]

                    # Chin for scale
                    chin = face.landmark[152]
                    chin_y = int(chin.y * h)

                    for ear in [left_ear, right_ear]:
                        ex = int(ear.x * w)
                        ey = int(ear.y * h)

                        ear_w = 35
                        ear_h = int(ear_w * 2.0)

                        # Hang the earring just below the ear-lobe point
                        acc_x = ex - ear_w // 2
                        acc_y = ey                    # starts at lobe, hangs down

                        frame = overlay(frame, current_accessory, acc_x, acc_y, ear_w, ear_h)

            # ── BRACELET ────────────────────────────────────────────────────
            elif current_type == "bracelet":
                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                if results.multi_hand_landmarks:
                    hand  = results.multi_hand_landmarks[0]

                    # Use wrist (0) and index-MCP (5) to measure hand width + angle
                    wrist    = hand.landmark[0]
                    idx_mcp  = hand.landmark[5]
                    pinky_mcp= hand.landmark[17]

                    wx, wy = int(wrist.x * w), int(wrist.y * h)
                    ix, iy = int(idx_mcp.x * w), int(idx_mcp.y * h)
                    px, py = int(pinky_mcp.x * w), int(pinky_mcp.y * h)

                    # Bracelet width ≈ distance between index and pinky MCPs
                    band_w = int(np.hypot(ix - px, iy - py) * 1.3)
                    band_h = max(20, band_w // 4)

                    acc_x = wx - band_w // 2
                    acc_y = wy - band_h // 2

                    frame = overlay(frame, current_accessory, acc_x, acc_y, band_w, band_h)

            # ── RING ────────────────────────────────────────────────────────
            elif current_type == "ring":
                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                if results.multi_hand_landmarks:
                    hand = results.multi_hand_landmarks[0]

                    # Ring finger middle phalanx (between landmarks 14 and 15)
                    ring_base = hand.landmark[14]
                    ring_tip  = hand.landmark[16]

                    rx = int((ring_base.x + ring_tip.x) / 2 * w)
                    ry = int((ring_base.y + ring_tip.y) / 2 * h)

                    ring_sz = int(np.hypot(
                        (ring_tip.x - ring_base.x) * w,
                        (ring_tip.y - ring_base.y) * h
                    ) * 1.4)
                    ring_sz = max(ring_sz, 20)

                    frame = overlay(frame, current_accessory,
                                    rx - ring_sz // 2, ry - ring_sz // 2,
                                    ring_sz, ring_sz)

            # ── NECKLACE ────────────────────────────────────────────────────
            elif current_type == "necklace":
                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb)

                if results.multi_face_landmarks:
                    face = results.multi_face_landmarks[0]

                    # Chin bottom as anchor; width ≈ face width
                    chin      = face.landmark[152]
                    left_jaw  = face.landmark[234]
                    right_jaw = face.landmark[454]

                    chin_x = int(chin.x * w)
                    chin_y = int(chin.y * h)

                    face_width = int(abs(right_jaw.x - left_jaw.x) * w)

                    neck_w = int(face_width * 1.1)
                    neck_h = int(neck_w * 0.55)

                    acc_x = chin_x - neck_w // 2
                    acc_y = chin_y + 5        # just below chin

                    frame = overlay(frame, current_accessory, acc_x, acc_y, neck_w, neck_h)

            # ── HAT ─────────────────────────────────────────────────────────
            elif current_type == "hat":
                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb)

                if results.multi_face_landmarks:
                    face = results.multi_face_landmarks[0]

                    # Forehead top = midpoint of landmarks 10 (top of head area)
                    top       = face.landmark[10]
                    left_jaw  = face.landmark[234]
                    right_jaw = face.landmark[454]

                    face_width = int(abs(right_jaw.x - left_jaw.x) * w)
                    top_x      = int(top.x * w)
                    top_y      = int(top.y * h)

                    hat_w = int(face_width * 1.6)
                    hat_h = int(hat_w * 0.75)

                    acc_x = top_x - hat_w // 2
                    acc_y = top_y - hat_h + 10   # sits above forehead

                    frame = overlay(frame, current_accessory, acc_x, acc_y, hat_w, hat_h)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


# ── STREAM ROUTE ───────────────────
@tryon_bp.route("/virtual-tryon")
def virtual_tryon():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')