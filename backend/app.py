
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from datetime import timedelta
import os

# ── Existing blueprints ───────────────────────────────────────────────────────
from routes.register_routes          import register_bp
from routes.skin_routes              import skin_bp
from routes.product_routes           import product_bp
from routes.vision_routes            import vision_bp
from routes.fashion_routes           import fashion_bp
from routes.chatbot_routes           import chatbot_bp
from routes.closet_routes            import closet_bp
from routes.virtual_tryon_routes     import tryon_bp
from routes.outfit_scheduler_routes  import scheduler_bp
from routes.auth_routes              import auth_bp, jwt
from routes.saved_products_routes    import saved_products_bp
from routes.skin_progress_routes     import skin_progress_bp
from routes.budget_brand_routes      import preferences_bp
from routes.outfit_image_routes      import outfit_image_bp
from routes.body_shape_routes        import body_shape_bp
from routes.skin_explain_route       import skin_explain_bp
from services.color_palette_service  import color_palette_bp
from routes.preference_routes import preference_bp

# ── New feature blueprints ────────────────────────────────────────────────────
from routes.event_planner_routes            import event_planner_bp
from routes.occasion_photo_analyzer_routes  import occasion_analyzer_bp

# Optional — WhatsApp
try:
    from routes.whatsapp_webhook_routes import whatsapp_bp
    _has_whatsapp = True
except Exception as e:
    print(f"WhatsApp blueprint load failed (non-fatal): {e}")
    _has_whatsapp = False

os.makedirs("uploads", exist_ok=True)

app = Flask(__name__)

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    expose_headers=["Content-Type", "Authorization"],
)

# ── JWT ───────────────────────────────────────────────────────────────────────
app.config["JWT_SECRET_KEY"]           = os.getenv("JWT_SECRET_KEY", "facefit-secret-change-in-prod")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
jwt.init_app(app)


@app.before_request
def handle_preflight():
    from flask import request, Response
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Max-Age"]       = "3600"
        return response, 200


# ── Register blueprints ───────────────────────────────────────────────────────
app.register_blueprint(register_bp)
app.register_blueprint(skin_bp)
app.register_blueprint(product_bp)
app.register_blueprint(vision_bp)
app.register_blueprint(fashion_bp)
app.register_blueprint(chatbot_bp)
app.register_blueprint(closet_bp)
app.register_blueprint(tryon_bp)
app.register_blueprint(scheduler_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(saved_products_bp)
app.register_blueprint(skin_progress_bp)
app.register_blueprint(preferences_bp)
app.register_blueprint(outfit_image_bp)
app.register_blueprint(body_shape_bp)
app.register_blueprint(skin_explain_bp)
app.register_blueprint(color_palette_bp)
app.register_blueprint(event_planner_bp)      # ← NEW: /event-planner/plan
app.register_blueprint(occasion_analyzer_bp)  # ← NEW: /analyze-outfit-photo
app.register_blueprint(preference_bp)

if _has_whatsapp:
    app.register_blueprint(whatsapp_bp)


@app.route("/")
def home():
    return jsonify({
        "status":  "ok",
        "version": "v4-final",
        "features": [
            "AI Stylist Chat",
            "Digital Closet + Mix & Match",
            "Body Shape Detection",
            "Skin Progress Tracker",
            "Budget + Brand Preferences",
            "Price Drop Alerts",
            "Outfit Scheduler",
            "Virtual Try-On",
            "AI Event Planner — NEW",
            "Occasion Photo Analyzer — NEW",
            "WhatsApp Chatbot",
            "Color Palette Wheel",
            "Outfit Image Generator (Pollinations)",
        ],
        "new_routes": [
            "POST /event-planner/plan     — Full event plan (outfit + skincare + shopping)",
            "POST /event-planner/quick    — Quick event detection",
            "POST /analyze-outfit-photo   — Rate outfit 1-10 with improvements",
        ],
        "all_routes": [
            "POST /register",
            "GET  /auth/me",
            "POST /chat",
            "POST /outfits",
            "GET  /closet/<user_id>",
            "POST /closet/add",
            "POST /closet/multi-outfit",
            "GET  /closet/mix-match/<user_id>",
            "GET  /closet/gap-analysis/<user_id>",
            "POST /closet/outfit-image",
            "GET  /closet/color-palette/<user_id>",
            "POST /skin/scan",
            "GET  /skin/progress/<user_id>",
            "POST /skin/explain",
            "GET  /preferences/brands/<user_id>",
            "POST /preferences/brands/<user_id>",
            "GET  /preferences/budget/<user_id>",
            "POST /preferences/budget/<user_id>",
            "POST /scheduler/remind",
            "GET  /scheduler/reminders/<user_id>",
            "POST /detect-body-shape",
            "POST /products",
            "GET  /products/saved/<user_id>",
            "POST /products/save",
            "POST /products/price-check",
            "POST /whatsapp/webhook",
            "POST /event-planner/plan",
            "POST /analyze-outfit-photo",
        ],
    })


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
