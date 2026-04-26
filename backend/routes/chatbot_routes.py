from flask import Blueprint, request, jsonify
from services.chat_service import chat_with_ai

chatbot_bp = Blueprint("chatbot", __name__)

@chatbot_bp.route("/chat", methods=["POST"], endpoint="chatbot_chat")
def chat():
    try:
        data = request.json

        message = data.get("message", "")
        user    = data.get("user_context", {})
        history = data.get("history", [])

        if not message:
            return jsonify({"error": "Message is required"}), 400

        response = chat_with_ai(message, user, history)
        return jsonify(response)

    except Exception as e:
        print("CHAT ERROR:", e)
        import traceback; traceback.print_exc()
        return jsonify({
            "error": "Something went wrong in chatbot",
            "details": str(e)
        }), 500