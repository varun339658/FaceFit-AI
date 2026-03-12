from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

from routes.register_routes import register_bp
from routes.skin_routes import skin_bp
from routes.product_routes import product_bp
from routes.vision_routes import vision_bp
import os
os.makedirs("uploads", exist_ok=True)
app = Flask(__name__)

CORS(app)

app.register_blueprint(register_bp)
app.register_blueprint(skin_bp)
app.register_blueprint(product_bp)
app.register_blueprint(vision_bp)


@app.route("/")
def home():
    return jsonify({"status": "ok"})


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)


if __name__ == "__main__":
    app.run(debug=True)