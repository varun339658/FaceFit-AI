from langchain_groq import ChatGroq
import os

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

def detect_intent(message: str) -> str:

    prompt = f"""
You are an AI intent classifier for a fashion + skincare assistant.

User message:
"{message}"

Classify the intent into ONE of these categories:
- fashion → outfit, dress, clothes, wedding, styling
- skincare → acne, routine, skin care, face issues
- both → if user asks for both fashion and skincare

Rules:
- Return ONLY one word
- No explanation
- No punctuation

Answer:
"""

    try:
        res = llm.invoke(prompt)
        intent = res.content.strip().lower()

        # Safety fallback
        if intent not in ["fashion", "skincare", "both"]:
            return "fashion"

        return intent

    except Exception as e:
        print("Intent error:", e)
        return "fashion"