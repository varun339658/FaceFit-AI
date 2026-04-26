"""
skin_rag_service.py
────────────────────
AI + RAG powered skincare recommendation engine.
Uses Groq (Llama 3.3 70b) + ChromaDB + SentenceTransformer embeddings.

KEY FIXES:
 - For ACNE: night serum is SALICYLIC ACID 2% BHA — not retinol
 - Conditions deduplicated before LLM call
 - Optional products (eye_cream, spot_treatment) guaranteed when conditions detected
 - retriever.invoke() replaces deprecated get_relevant_documents()
 - Post-processing ensures correct serums per condition
"""

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
try:
    from langchain_huggingface import HuggingFaceEmbeddings as SentenceTransformerEmbeddings
except ImportError:
    from langchain_huggingface import HuggingFaceEmbeddings as SentenceTransformerEmbeddings
from langchain_groq import ChatGroq

import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

# ── Load & index skincare knowledge ──────────────────────────────────────────
loader = TextLoader("rag_data/skincare_knowledge.txt")
documents = loader.load()

splitter = CharacterTextSplitter(chunk_size=600, chunk_overlap=100)
docs = splitter.split_documents(documents)

embedding = SentenceTransformerEmbeddings(model_name="paraphrase-MiniLM-L3-v2")
vectorstore = Chroma.from_documents(docs, embedding, collection_name="skincare_v2")
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}


def _retrieve_context(query: str) -> str:
    retrieved = retriever.invoke(query)
    return "\n\n".join(d.page_content for d in retrieved)


def generate_skin_recommendation(skin_tone: str, skin_conditions: list) -> dict:
    """
    Returns AI-generated skincare routine + product search queries.
    Products are 100% based on detected skin conditions from face analysis.

    For acne: serum_night = salicylic acid 2% BHA (NOT retinol)
    For dark circles: eye_cream added
    For active acne: spot_treatment added
    """

    # ── Deduplicate conditions ────────────────────────────────────────────────
    seen = set()
    unique_conditions = []
    for c in skin_conditions:
        c_clean = c.lower().strip()
        if c_clean and c_clean not in seen:
            seen.add(c_clean)
            unique_conditions.append(c_clean)

    if not unique_conditions:
        unique_conditions = ["normal skin"]

    conditions_str = ", ".join(unique_conditions)
    print(f"🔬 UNIQUE CONDITIONS: {unique_conditions}")

    # ── Detect what's present ─────────────────────────────────────────────────
    has_acne        = any("acne" in c for c in unique_conditions)
    has_dark_circle = any("dark circle" in c or "dark_circle" in c for c in unique_conditions)
    has_dark_spots  = any("dark spot" in c or "hyperpigmentation" in c for c in unique_conditions)
    has_dry         = any("dry" in c for c in unique_conditions)

    # ── Retrieve relevant knowledge ───────────────────────────────────────────
    context = _retrieve_context(
        f"skincare routine {conditions_str} {skin_tone} skin tone serum ingredients products"
    )

    skin_tone_note = {
        "light":  "Light skin is sensitive, prone to redness. Use gentle formulations, SPF 50+.",
        "medium": "Medium skin is prone to hyperpigmentation. Prioritize niacinamide, alpha arbutin, SPF 50.",
        "dark":   "Dark skin is very prone to PIH (post-inflammatory hyperpigmentation) from acne. "
                  "Niacinamide is critical to prevent PIH. Use azelaic acid, vitamin C. Avoid harsh peels.",
    }.get(skin_tone.lower(), "Use appropriate products for the skin tone.")

    # ── Build precise instructions for each detected condition ────────────────
    condition_instructions = []

    if has_acne:
        condition_instructions.append("""ACNE DETECTED — Follow these rules EXACTLY:
   - cleanser: salicylic acid 2% face wash for acne prone oily skin
   - toner: BHA exfoliating toner for oily acne skin
   - serum_day: niacinamide 10% serum for acne inflammation oil control (morning)
   - serum_night: salicylic acid 2% BHA night serum for acne pore exfoliation (night) — NOT RETINOL
   - moisturizer: oil free non-comedogenic gel moisturizer for acne
   - spot_treatment: benzoyl peroxide 2.5% spot treatment gel (REQUIRED for acne)
   CRITICAL: serum_night MUST be salicylic acid BHA for active acne, never retinol""")

    if has_dark_circle:
        condition_instructions.append("""DARK CIRCLES DETECTED:
   - eye_cream: caffeine peptide under eye cream for dark circles puffiness (REQUIRED)""")

    if has_dark_spots:
        condition_instructions.append("""DARK SPOTS DETECTED:
   - brightening_serum: vitamin C 15% serum for dark spots brightening (REQUIRED)""")

    if has_dry and not has_acne:
        condition_instructions.append("""DRY SKIN DETECTED:
   - serum_day: hyaluronic acid serum for dry dehydrated skin
   - serum_night: ceramide repair serum for dry skin barrier""")

    condition_block = "\n\n".join(condition_instructions) if condition_instructions else "Normal skin — use gentle balanced products."

    # ── Build optional JSON keys ──────────────────────────────────────────────
    optional_keys = []
    if has_acne:
        optional_keys.append('    "spot_treatment": "benzoyl peroxide 2.5% spot treatment gel active acne pimples India"')
    if has_dark_circle:
        optional_keys.append('    "eye_cream": "caffeine peptide under eye cream dark circles puffiness India"')
    if has_dark_spots:
        optional_keys.append('    "brightening_serum": "vitamin C 15% L-ascorbic acid serum dark spots brightening India"')

    optional_block = (",\n" + ",\n".join(optional_keys)) if optional_keys else ""

    prompt = f"""You are a board-certified dermatologist. Create a precise skincare routine.

PATIENT ANALYSIS (from AI computer vision):
- Skin Tone: {skin_tone}
- Detected Conditions: {conditions_str}

SKIN TONE NOTE: {skin_tone_note}

CONDITION-SPECIFIC REQUIREMENTS:
{condition_block}

KNOWLEDGE BASE:
{context}

YOUR TASK:
Generate a complete skincare routine with specific Indian e-commerce product search queries.
Base EVERY product choice strictly on the detected conditions above.

PRODUCT QUERY RULES:
1. Be SPECIFIC: include active ingredient + concentration + skin concern + India
   CORRECT: "niacinamide 10% zinc serum acne prone oily skin oil control India"
   WRONG: "serum" or "face serum"
2. serum_day and serum_night MUST be DIFFERENT products:
   - If acne: serum_day = niacinamide | serum_night = SALICYLIC ACID 2% BHA (NOT retinol)
   - If dry: serum_day = hyaluronic acid | serum_night = ceramide repair
   - If normal: serum_day = niacinamide | serum_night = peptide repair
3. Sunscreen is ALWAYS required in morning routine
4. All products must be available on Nykaa or Amazon India
5. Morning and night routine steps in correct application order

OUTPUT — ONLY valid JSON, no markdown, no explanation:
{{
  "routine": {{
    "morning": ["Step 1", "Step 2", "Step 3", "Step 4", "SPF 50 Sunscreen"],
    "night": ["Step 1", "Step 2", "Step 3", "Step 4"]
  }},
  "ingredients": {{
    "cleanser": "specific query India",
    "toner": "specific query India",
    "serum_day": "specific query India",
    "serum_night": "specific query India",
    "moisturizer": "specific query India",
    "sunscreen": "specific query India"{optional_block}
  }}
}}"""

    response = llm.invoke(prompt)
    raw = response.content if hasattr(response, "content") else str(response)
    print("🔬 SKIN RAG OUTPUT:", raw[:800])

    data = _extract_json(raw)

    if not data or "ingredients" not in data:
        print("⚠️  Skin RAG JSON failed — using smart fallback")
        data = _fallback(skin_tone, unique_conditions)

    if "routine" not in data:
        data["routine"] = {"morning": [], "night": []}

    ings = data.setdefault("ingredients", {})

    # ── POST-PROCESSING: Guarantee correct products based on conditions ────────

    # Fix serum_night — must be salicylic acid for acne, not retinol
    if has_acne:
        night_serum = ings.get("serum_night", "")
        if "retinol" in night_serum.lower() or not night_serum or len(night_serum) < 5:
            ings["serum_night"] = "salicylic acid 2% BHA night serum acne prone oily skin pore exfoliation India"
            print("✅ FIXED serum_night → salicylic acid 2% BHA (was retinol or missing)")

    # Guarantee day serum for acne
    if has_acne:
        day_serum = ings.get("serum_day", "")
        if not day_serum or len(day_serum) < 5:
            ings["serum_day"] = "niacinamide 10% zinc serum acne prone oily skin oil control India"

    # Guarantee spot_treatment for acne
    if has_acne and "spot_treatment" not in ings:
        ings["spot_treatment"] = "benzoyl peroxide 2.5% spot treatment gel active pimples acne India"
        print("✅ ADDED spot_treatment for acne")

    # Guarantee eye_cream for dark circles
    if has_dark_circle and "eye_cream" not in ings:
        ings["eye_cream"] = "caffeine peptide under eye cream dark circles puffiness India"
        print("✅ ADDED eye_cream for dark circles")

    # Guarantee brightening serum for dark spots
    if has_dark_spots and "brightening_serum" not in ings:
        ings["brightening_serum"] = "vitamin C 15% L-ascorbic acid serum dark spots brightening India"
        print("✅ ADDED brightening_serum for dark spots")

    # Guarantee sunscreen
    if "sunscreen" not in ings:
        ings["sunscreen"] = f"SPF 50 PA+++ non-comedogenic sunscreen for {skin_tone} skin India"

    return data


def _fallback(skin_tone: str, conditions: list) -> dict:
    c = " ".join(conditions).lower()
    is_acne        = "acne" in c
    is_dark_circle = "dark circle" in c
    is_dark_spots  = "dark spot" in c or "hyperpigmentation" in c
    is_dry         = "dry" in c

    ings = {
        "cleanser":    "salicylic acid 2% face wash acne prone oily skin India"
                       if is_acne else f"gentle hydrating cleanser {skin_tone} skin India",
        "toner":       "BHA salicylic acid exfoliating toner oily acne skin India"
                       if is_acne else "hydrating niacinamide toner normal skin India",
        "serum_day":   "niacinamide 10% zinc serum acne oil control India"
                       if is_acne else "hyaluronic acid 2% glycerin serum dry dehydrated skin India",
        "serum_night": "salicylic acid 2% BHA night serum acne pore exfoliation India"
                       if is_acne else "ceramide repair serum dry skin barrier restoration India",
        "moisturizer": "oil free non-comedogenic gel moisturizer acne prone skin India"
                       if is_acne else ("rich ceramide moisturizer dry skin India"
                                        if is_dry else f"lightweight gel moisturizer {skin_tone} skin India"),
        "sunscreen":   "SPF 50 PA+++ lightweight non-comedogenic sunscreen oily acne skin India"
                       if is_acne else f"SPF 50 PA+++ broad spectrum sunscreen {skin_tone} skin India",
    }

    if is_acne:
        ings["spot_treatment"] = "benzoyl peroxide 2.5% spot treatment gel active pimples India"
    if is_dark_circle:
        ings["eye_cream"] = "caffeine peptide under eye cream dark circles puffiness India"
    if is_dark_spots:
        ings["brightening_serum"] = "vitamin C 15% L-ascorbic acid serum dark spots brightening India"

    morning = ["Salicylic Acid Cleanser", "Niacinamide 10% Serum", "Oil-Free Moisturizer", "SPF 50 Sunscreen"]
    night   = ["Salicylic Acid Cleanser", "BHA Toner", "Salicylic Acid 2% BHA Serum", "Oil-Free Moisturizer"]

    if is_dark_circle:
        morning.insert(1, "Caffeine Eye Cream")
        night.insert(1, "Caffeine Eye Cream")

    if not is_acne and is_dry:
        morning = ["Hydrating Cleanser", "Hyaluronic Acid Serum", "Ceramide Moisturizer", "Hydrating SPF 50"]
        night   = ["Hydrating Cleanser", "Ceramide Repair Serum", "Rich Moisturizer"]

    return {
        "routine":     {"morning": morning, "night": night},
        "ingredients": ings,
    }