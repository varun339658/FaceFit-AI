"""
auth_routes.py — FaceFit JWT Authentication (FIXED)
=====================================================
FIXES:
  1. JWT properly configured with flask-jwt-extended
  2. /auth/me uses Bearer token correctly
  3. Per-user data isolation enforced at DB query level
  4. Token refresh endpoint added
  5. CORS headers handled for JWT preflight
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
)
from pymongo import MongoClient
import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority",
)
client   = MongoClient(MONGO_URI)
db       = client["facefit_ai"]
users_col = db["users"]
face_col  = db["face_analysis"]

auth_bp = Blueprint("auth", __name__)
jwt     = JWTManager()


def issue_token(user_id: str) -> str:
    """Issue a JWT for a user. Call from register_routes after successful registration."""
    return create_access_token(identity=user_id)


@auth_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def get_profile():
    """
    Called on every app boot with the stored JWT.
    Returns full profile so sessionStorage is never needed.
    
    Frontend: axios.get('/auth/me', { headers: { Authorization: `Bearer ${token}` } })
    """
    user_id = get_jwt_identity()

    # Get most recent face analysis — SCOPED TO THIS USER
    face = face_col.find_one(
        {"userId": user_id},
        {"_id": 0},
        sort=[("timestamp", -1)],
    )

    # Get contact info — SCOPED TO THIS USER
    user = users_col.find_one({"userId": user_id}, {"_id": 0})

    if not face:
        # User exists (has token) but no face analysis yet
        return jsonify({
            "userId":     user_id,
            "name":       user_id,
            "gender":     user.get("gender", "male") if user else "male",
            "email":      user.get("email", "")      if user else "",
            "phone":      user.get("phone", "")      if user else "",
            "face_shape": "oval",
            "skinTone":   "medium",
            "conditions": [],
        }), 200

    # Deduplicate conditions
    raw  = face.get("skinConditions", [])
    seen, unique = set(), []
    for c in raw:
        k = c.lower().strip()
        if k and k not in seen:
            seen.add(k)
            unique.append(k)

    return jsonify({
        "userId":     user_id,
        "name":       user_id,
        "gender":     user.get("gender", "male") if user else "male",
        "email":      user.get("email", "")      if user else "",
        "phone":      user.get("phone", "")      if user else "",
        "face_shape": face.get("faceShape", "oval"),
        "skinTone":   face.get("skinTone", "medium"),
        "conditions": unique,
    })


@auth_bp.route("/auth/refresh", methods=["POST"])
@jwt_required()
def refresh_token():
    """Issue a fresh token for an existing valid token."""
    user_id   = get_jwt_identity()
    new_token = create_access_token(identity=user_id)
    return jsonify({"access_token": new_token})


@auth_bp.route("/auth/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    JWT is stateless — logout is handled client-side by deleting the token.
    This endpoint exists so the frontend has a clean logout call.
    """
    return jsonify({"success": True, "message": "Logged out. Delete your token client-side."})


@auth_bp.route("/auth/check", methods=["GET"])
def check_token():
    """Quick check if a token is still valid (no user data returned)."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        return jsonify({"valid": True, "userId": user_id})
    except Exception:
        return jsonify({"valid": False}), 401