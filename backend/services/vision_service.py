import cv2
import mediapipe as mp
import numpy as np
from ultralytics import YOLO
import os
from utils.db import face_collection
from datetime import datetime


mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh

# Load YOLO model
MODEL_PATH = "models/best.pt"
yolo_model = YOLO(MODEL_PATH)


# ───────── FACE DETECTION ─────────

def detect_face(image_path):

    image = cv2.imread(image_path)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp_face_detection.FaceDetection(
        model_selection=0,
        min_detection_confidence=0.5
    ) as detector:

        results = detector.process(rgb)

        if results.detections:
            return {
                "face_detected": True,
                "count": len(results.detections)
            }

        return {"face_detected": False}


# ───────── LANDMARKS ─────────

def detect_face_landmarks(image_path):

    image = cv2.imread(image_path)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp_face_mesh.FaceMesh(static_image_mode=True) as mesh:

        results = mesh.process(rgb)

        if results.multi_face_landmarks:

            count = len(results.multi_face_landmarks[0].landmark)

            return {
                "landmarks_detected": True,
                "landmarks_count": count
            }

        return {"landmarks_detected": False}


# ───────── FACE SHAPE ─────────

def detect_face_shape(image_path):

    image = cv2.imread(image_path)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp_face_mesh.FaceMesh(static_image_mode=True) as mesh:

        results = mesh.process(rgb)

        if not results.multi_face_landmarks:
            return {"face_shape": "unknown"}

        landmarks = results.multi_face_landmarks[0].landmark

        forehead = landmarks[10]
        chin = landmarks[152]
        left_cheek = landmarks[234]
        right_cheek = landmarks[454]

        face_height = abs(forehead.y - chin.y)
        face_width = abs(left_cheek.x - right_cheek.x)

        ratio = face_height / face_width

        if ratio > 1.5:
            shape = "oval"
        elif ratio > 1.3:
            shape = "round"
        elif ratio > 1.1:
            shape = "heart"
        else:
            shape = "square"

        return {
            "face_shape": shape,
            "height_width_ratio": round(ratio, 2)
        }


# ───────── SKIN TONE ─────────

def detect_skin_tone(image_path):

    image = cv2.imread(image_path)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    h, w, _ = rgb.shape
    center = rgb[h//3:h//2, w//3:w//2]

    avg_color = np.mean(center, axis=(0, 1))
    brightness = np.mean(avg_color)

    if brightness > 180:
        tone = "light"
    elif brightness > 130:
        tone = "medium"
    else:
        tone = "dark"

    return {
        "skin_tone": tone,
        "brightness_score": float(round(brightness, 2))
    }


# ───────── DRAW LANDMARKS ─────────

def draw_face_landmarks(image_path):

    image = cv2.imread(image_path)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp_face_mesh.FaceMesh(static_image_mode=True) as mesh:

        results = mesh.process(rgb)

        if not results.multi_face_landmarks:
            return None

        for face_landmarks in results.multi_face_landmarks:

            for landmark in face_landmarks.landmark:

                h, w, _ = image.shape
                x = int(landmark.x * w)
                y = int(landmark.y * h)

                cv2.circle(image, (x, y), 1, (0,255,0), -1)

        output_path = "uploads/landmarks_output.jpg"
        cv2.imwrite(output_path, image)

        return output_path


# ───────── YOLO ACNE DETECTION ─────────

def detect_skin_issues(image_path):

    results = yolo_model(image_path, conf=0.15)

    detections = []

    for box in results[0].boxes:
        cls = int(box.cls[0])
        detections.append(yolo_model.names[int(cls)])

    annotated = results[0].plot()

    output_path = "uploads/yolo_output.jpg"
    cv2.imwrite(output_path, annotated)

    return {
        "detections": detections,
        "total_detected": len(detections),
        "image_path": output_path
    }
    
def save_face_analysis(user_id, face_shape, skin_tone, acne_count, conditions, landmarks):

    record = {
        "userId": user_id,
        "faceShape": face_shape,
        "skinTone": skin_tone,
        "landmarks": landmarks,
        "skinConditions": conditions,
        "acneCount": acne_count,
        "timestamp": datetime.utcnow()
    }

    face_collection.insert_one(record)