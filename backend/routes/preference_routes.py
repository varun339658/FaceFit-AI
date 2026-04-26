"""
preference_routes.py — FaceFit Replace Item + Learning System
=============================================================
Two features:
  1. POST /outfit/replace-item  — AI replaces ONE item, keeps rest same
  2. POST /outfit/feedback       — record accept/reject for learning
  3. GET  /outfit/preferences/<user_id> — get user style preferences
  4. POST /outfit/reset-preferences/<user_id> — reset learning data
"""

import os, json, re, uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from pymongo import MongoClient, DESCENDING
from langchain_groq import ChatGroq

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority",
)
_client = MongoClient(MONGO_URI)
_db     = _client["facefit_ai"]

# Collections
feedback_col    = _db["outfit_feedback"]      # stores accept/reject per item
preferences_col = _db["user_style_prefs"]     # aggregated learned preferences

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.4,
    groq_api_key=GROQ_API_KEY,
)

preference_bp = Blueprint("preference", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _deduplicate_products(products: list) -> list:
    if not products:
        return []
    seen = set()
    result = []
    for p in products:
        if not p or not p.get("title"):
            continue
        key = p.get("title","").lower().strip()[:40] + "|" + p.get("link","").split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
    return result


def _get_user_preferences(user_id: str) -> dict:
    """Load learned preferences for this user."""
    doc = preferences_col.find_one({"userId": user_id}, {"_id": 0})
    if doc:
        return doc
    return {
        "userId":          user_id,
        "rejected_items":  [],   # list of {category, color, style, reason}
        "accepted_items":  [],   # list of {category, color, style}
        "rejected_colors": {},   # {category: [colors]}
        "preferred_colors":{}    # {category: [colors]}
    }


def _update_preferences_from_feedback(user_id: str, feedback_type: str, item: dict, reason: str = ""):
    """Update learned preferences based on feedback."""
    prefs = _get_user_preferences(user_id)
    category = item.get("category", "")
    color    = (item.get("color", "") or "").lower().strip()
    style    = item.get("style", "") or item.get("item_name", "")

    if feedback_type == "reject":
        # Add to rejected items
        rejected = prefs.get("rejected_items", [])
        rejected.append({
            "category": category, "color": color,
            "style": style, "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Keep last 50 rejections
        prefs["rejected_items"] = rejected[-50:]

        # Track rejected colors per category
        rej_colors = prefs.get("rejected_colors", {})
        if category not in rej_colors:
            rej_colors[category] = []
        if color and color not in rej_colors[category]:
            rej_colors[category].append(color)
        prefs["rejected_colors"] = rej_colors

    elif feedback_type == "accept":
        accepted = prefs.get("accepted_items", [])
        accepted.append({
            "category": category, "color": color,
            "style": style, "timestamp": datetime.utcnow().isoformat()
        })
        prefs["accepted_items"] = accepted[-50:]

        # Track preferred colors per category
        pref_colors = prefs.get("preferred_colors", {})
        if category not in pref_colors:
            pref_colors[category] = []
        if color and color not in pref_colors[category]:
            pref_colors[category].append(color)
        prefs["preferred_colors"] = pref_colors

    prefs["updated_at"] = datetime.utcnow().isoformat()

    preferences_col.update_one(
        {"userId": user_id},
        {"$set": prefs},
        upsert=True,
    )
    return prefs


def _build_preference_context(user_id: str) -> str:
    """Build a context string for AI from learned preferences."""
    prefs = _get_user_preferences(user_id)
    parts = []

    rejected_items = prefs.get("rejected_items", [])
    if rejected_items:
        # Summarize rejections
        reject_summary = []
        for item in rejected_items[-10:]:  # last 10
            r = f"{item.get('color','')} {item.get('style','')} ({item.get('category','')})"
            if item.get("reason"):
                r += f" — reason: {item['reason']}"
            reject_summary.append(r)
        parts.append(f"USER DISLIKES (avoid these): {'; '.join(reject_summary)}")

    rejected_colors = prefs.get("rejected_colors", {})
    if rejected_colors:
        color_avoids = [f"{cat}: avoid {', '.join(colors)}" for cat, colors in rejected_colors.items() if colors]
        if color_avoids:
            parts.append(f"AVOID COLORS: {'; '.join(color_avoids)}")

    preferred_colors = prefs.get("preferred_colors", {})
    if preferred_colors:
        color_prefs = [f"{cat}: prefers {', '.join(colors[:3])}" for cat, colors in preferred_colors.items() if colors]
        if color_prefs:
            parts.append(f"PREFERRED COLORS: {'; '.join(color_prefs)}")

    return "\n".join(parts) if parts else "No preference history yet."


# ── Route 1: Replace a single item ───────────────────────────────────────────

@preference_bp.route("/outfit/replace-item", methods=["POST"])
def replace_item():
    """
    Replace exactly ONE item in an outfit, keeping everything else the same.
    
    Body:
    {
      "user_id": "varun",
      "category": "pants",           ← which slot to replace
      "reason": "I don't like jeans",← optional reason
      "current_outfit": {             ← the full current outfit (products dict)
        "shirt":   [...products],
        "pants":   [...products],
        "shoes":   [...products],
        ...
      },
      "user_context": {
        "skinTone": "dark", "gender": "male",
        "face_shape": "oval", "event": "casual"
      }
    }
    
    Returns:
    {
      "replacement": [...new products for that category],
      "category": "pants",
      "search_query": "...",
      "reason_acknowledged": "..."
    }
    """
    data = request.json or {}

    user_id     = data.get("user_id", "guest")
    category    = data.get("category", "")
    reason      = data.get("reason", "")
    current_outfit = data.get("current_outfit", {})
    user_ctx    = data.get("user_context", {})

    if not category:
        return jsonify({"error": "category is required"}), 400

    skin_tone  = user_ctx.get("skinTone",   "medium")
    gender     = user_ctx.get("gender",     "male")
    event      = user_ctx.get("event",      "casual")
    face_shape = user_ctx.get("face_shape", "oval")

    gl = "men" if gender.lower() not in ("female","women","woman","girl","f") else "women"

    # Load user preferences for smart replacement
    pref_context = _build_preference_context(user_id)

    # Describe what's currently in the outfit (for context)
    other_items = []
    current_item_desc = ""
    for cat, products in current_outfit.items():
        if not products:
            continue
        if isinstance(products, list) and products:
            p = products[0]
            desc = p.get("title", cat)
        elif isinstance(products, dict):
            desc = products.get("item_name", cat)
        else:
            desc = str(products)

        if cat == category:
            current_item_desc = desc
        else:
            other_items.append(f"{cat}: {desc}")

    other_context = "; ".join(other_items) if other_items else "no other items"

    # Also record the rejection in learning system
    if user_id and user_id != "guest":
        feedback_col.insert_one({
            "userId":    user_id,
            "type":      "reject",
            "category":  category,
            "item_desc": current_item_desc,
            "reason":    reason,
            "timestamp": datetime.utcnow(),
        })
        # Update preferences
        _update_preferences_from_feedback(user_id, "reject", {
            "category": category,
            "item_name": current_item_desc,
            "color": "",  # will be parsed from description
        }, reason)

    # Skin tone colors
    SKIN_COLORS = {
        "dark":   ["electric blue","saffron yellow","emerald green","coral","royal blue","magenta"],
        "medium": ["mustard","teal","burgundy","forest green","terracotta","rust"],
        "light":  ["pastel blue","lavender","mint green","sage green","blush pink","ivory"],
    }
    import random
    tone_colors = SKIN_COLORS.get(skin_tone.lower(), SKIN_COLORS["medium"])

    # Build avoided colors/styles from preferences
    prefs = _get_user_preferences(user_id)
    avoided_colors = prefs.get("rejected_colors", {}).get(category, [])
    avoid_str = f"AVOID these colors (user rejected before): {', '.join(avoided_colors)}" if avoided_colors else ""

    # AI generates the best replacement query
    prompt = f"""You are a world-class fashion stylist. The user wants to REPLACE their {category}.

CURRENT OUTFIT CONTEXT:
{other_context}

REJECTED ITEM: {current_item_desc}
REASON FOR REJECTION: {reason if reason else "didn't like it"}

USER PROFILE:
- Skin tone: {skin_tone} → best colors: {', '.join(tone_colors[:4])}
- Gender: {gl}
- Event: {event}
- Face shape: {face_shape}

USER PREFERENCE HISTORY:
{pref_context}
{avoid_str}

TASK: Generate a DIFFERENT and BETTER {category} that:
1. Complements the rest of the outfit ({other_context})
2. Suits {skin_tone} skin tone
3. Is appropriate for {event}
4. Is DIFFERENT from "{current_item_desc}" (completely different color/style)
5. Respects user's rejection history

Return ONLY valid JSON:
{{
  "search_query": "specific product search query for {gl} {event} India Myntra",
  "reason_acknowledged": "1 sentence: why this replacement is better",
  "replacement_color": "the new color you're recommending",
  "replacement_style": "specific style description"
}}"""

    try:
        resp = llm.invoke(prompt)
        raw  = resp.content if hasattr(resp,"content") else str(resp)
        ai_data = _extract_json(raw)
    except Exception as e:
        print(f"Replace item LLM error: {e}")
        ai_data = {}

    if not ai_data or not ai_data.get("search_query"):
        # Fallback: pick a fresh color and build query
        fresh_color = random.choice([c for c in tone_colors if c not in avoided_colors] or tone_colors)
        ai_data = {
            "search_query": f"{fresh_color} {category.replace('_',' ')} {gl} India {event}",
            "reason_acknowledged": f"This fresh {fresh_color} {category} will complement your outfit better.",
            "replacement_color": fresh_color,
            "replacement_style": f"Modern {event} style",
        }

    # Fetch replacement products
    try:
        from services.product_service import get_product_recommendations
        raw_products = get_product_recommendations(
            ai_data["search_query"], category, event, user_id=user_id
        )
        products = _deduplicate_products(raw_products or [])
    except Exception as e:
        print(f"Replace product fetch error: {e}")
        products = []

    return jsonify({
        "category":           category,
        "replacement":        products[:4],
        "search_query":       ai_data.get("search_query", ""),
        "reason_acknowledged": ai_data.get("reason_acknowledged", ""),
        "replacement_color":  ai_data.get("replacement_color", ""),
        "replacement_style":  ai_data.get("replacement_style", ""),
        "success":            True,
    })


# ── Route 2: Record feedback ──────────────────────────────────────────────────

@preference_bp.route("/outfit/feedback", methods=["POST"])
def record_feedback():
    """
    Record that a user accepted or rejected an outfit/item.
    
    Body:
    {
      "user_id": "varun",
      "type": "accept" | "reject",    ← whole outfit or single item
      "scope": "outfit" | "item",
      "item": {                         ← for item-level feedback
        "category": "pants",
        "color": "blue",
        "item_name": "blue slim jeans",
        "style": "slim fit"
      },
      "outfit_id": "optional-id",
      "reason": "optional reason text"
    }
    """
    data = request.json or {}

    user_id      = data.get("user_id", "guest")
    feedback_type = data.get("type", "accept")        # accept | reject
    scope        = data.get("scope", "outfit")         # outfit | item
    item         = data.get("item", {})
    outfit_id    = data.get("outfit_id", "")
    reason       = data.get("reason", "")

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    # Store raw feedback
    feedback_col.insert_one({
        "feedbackId": uuid.uuid4().hex,
        "userId":    user_id,
        "type":      feedback_type,
        "scope":     scope,
        "item":      item,
        "outfit_id": outfit_id,
        "reason":    reason,
        "timestamp": datetime.utcnow(),
    })

    # Update aggregated preferences
    if item and item.get("category"):
        prefs = _update_preferences_from_feedback(user_id, feedback_type, item, reason)
    else:
        prefs = _get_user_preferences(user_id)

    # Build response summary
    summary = {
        "recorded":          True,
        "type":              feedback_type,
        "total_rejections":  len(prefs.get("rejected_items", [])),
        "total_accepted":    len(prefs.get("accepted_items", [])),
    }

    if feedback_type == "reject" and item.get("category"):
        cat = item.get("category","")
        avoided = prefs.get("rejected_colors", {}).get(cat, [])
        summary["message"] = f"Got it! I'll avoid {item.get('color','this style')} {cat}s for you in future recommendations."
        summary["avoided_now"] = avoided
    elif feedback_type == "accept":
        summary["message"] = "Great choice! I'll remember your style preferences."

    return jsonify(summary)


# ── Route 3: Get preferences ──────────────────────────────────────────────────

@preference_bp.route("/outfit/preferences/<user_id>", methods=["GET"])
def get_preferences(user_id):
    """Get the learned style preferences for a user."""
    prefs = _get_user_preferences(user_id)

    # Build human-readable summary
    rejected_colors = prefs.get("rejected_colors", {})
    preferred_colors = prefs.get("preferred_colors", {})

    summary = {
        "total_interactions": len(prefs.get("rejected_items", [])) + len(prefs.get("accepted_items", [])),
        "rejected_colors":    rejected_colors,
        "preferred_colors":   preferred_colors,
        "top_rejected": [
            f"{item.get('color','')} {item.get('category','')}"
            for item in prefs.get("rejected_items", [])[-5:]
        ],
        "top_accepted": [
            f"{item.get('color','')} {item.get('category','')}"
            for item in prefs.get("accepted_items", [])[-5:]
        ],
    }

    return jsonify({
        "preferences": prefs,
        "summary":     summary,
    })


# ── Route 4: Reset preferences ────────────────────────────────────────────────

@preference_bp.route("/outfit/reset-preferences/<user_id>", methods=["POST"])
def reset_preferences(user_id):
    """Reset all learned preferences for a user."""
    preferences_col.delete_one({"userId": user_id})
    return jsonify({"success": True, "message": "Preferences reset. Starting fresh!"})


# ── Route 5: Get feedback history ─────────────────────────────────────────────

@preference_bp.route("/outfit/feedback-history/<user_id>", methods=["GET"])
def get_feedback_history(user_id):
    """Get recent feedback history."""
    docs = list(feedback_col.find(
        {"userId": user_id},
        {"_id": 0},
        sort=[("timestamp", DESCENDING)],
        limit=20,
    ))
    for d in docs:
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].isoformat()
    return jsonify({"history": docs, "total": len(docs)})