"""
event_planner_routes.py — FaceFit AI Event Planner v5
======================================================
CRITICAL FIXES:
  1. wardrobe_items: returns MAX 6 most relevant items (not all 35)
  2. Outfit plan: AI uses wardrobe context to pick correct items
  3. Skincare timeline: returns morning_steps[] and night_steps[] arrays
     for beautiful step-by-step UI rendering
  4. Products deduplicated before returning
  5. Gender-aware accessories (men never get earrings/necklace)
  6. All AI+RAG+skin analysis preserved
"""

import os, re, json, random
from flask import Blueprint, request, jsonify
from langchain_groq import ChatGroq

event_planner_bp = Blueprint("event_planner", __name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.4,
    groq_api_key=GROQ_API_KEY,
)


# ── Utility ───────────────────────────────────────────────────────────────────

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


def _extract_json_array(text: str) -> list:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _deduplicate_products(products: list) -> list:
    if not products:
        return []
    seen = set()
    result = []
    for p in products:
        if not p or not p.get("title"):
            continue
        key = p.get("title", "").lower().strip()[:40] + "|" + p.get("link", "").split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
    return result


def _is_male(gender: str) -> bool:
    return (gender or "male").lower() not in ("female", "women", "woman", "girl", "f")


# ── Event detection ───────────────────────────────────────────────────────────

def _detect_event(message: str) -> tuple:
    """Returns (event_type, days_until, icon)"""
    msg = message.lower()

    # Days
    days = 3
    if "today" in msg or "tonight" in msg:
        days = 0
    elif "tomorrow" in msg:
        days = 1
    else:
        m = re.search(r"in\s+(\d+)\s+day", msg)
        if m:
            days = int(m.group(1))

    # Event
    EVENTS = [
        (["wedding","shaadi","marriage","baraat"],       "wedding",    "💍"),
        (["sangeet"],                                     "sangeet",    "🎶"),
        (["mehndi","mehendi"],                           "mehndi",     "🌿"),
        (["haldi"],                                      "haldi",      "🌼"),
        (["reception"],                                   "reception",  "✨"),
        (["engagement","roka"],                          "engagement", "💌"),
        (["puja","pooja","temple"],                      "puja",       "🪔"),
        (["festival","diwali","navratri","holi","eid"],  "festival",   "🎉"),
        (["party","birthday","celebration"],              "party",      "🎊"),
        (["interview","job interview"],                  "interview",  "🎯"),
        (["office","work meeting","presentation"],       "office",     "💼"),
        (["date","romantic"],                            "date",       "🌹"),
        (["gym","workout","exercise"],                   "gym",        "💪"),
        (["beach","pool","swim"],                        "beach",      "🏖️"),
        (["concert","show","gig"],                       "concert",    "🎸"),
        (["dinner","restaurant"],                        "dinner",     "🍽️"),
        (["college","campus","class","farewell"],        "college",    "🎓"),
        (["brunch","lunch"],                             "brunch",     "☕"),
    ]
    for keywords, ev, icon in EVENTS:
        if any(k in msg for k in keywords):
            return ev, days, icon
    return "casual", days, "😊"


# ── KEY FIX: Get TOP 6 most relevant wardrobe items ───────────────────────────

def _get_top_wardrobe_items(user_id: str, event_type: str, max_items: int = 6) -> list:
    """
    Returns MAX max_items wardrobe items most relevant for the event.
    Scoring: event formality match + ethnic preference for ethnic events + no gym clothes for weddings.
    """
    if not user_id or user_id == "guest":
        return []
    try:
        from services.closet_agent import get_event_appropriate_wardrobe
        all_items = get_event_appropriate_wardrobe(user_id, event_type)
        if not all_items:
            return []
    except Exception as e:
        print(f"Wardrobe fetch error: {e}")
        return []

    # Scoring function
    ETHNIC_EVENTS = {"wedding","sangeet","mehndi","haldi","reception","engagement","puja","festival"}
    ATHLETIC_EVENTS = {"gym","beach","cricket","football","running","sport"}
    ETHNIC_KW = ["kurta","kurti","sherwani","lehenga","saree","ethnic","anarkali","salwar","traditional","festive"]
    FORMAL_KW = ["formal","slim fit","oxford","blazer","chino","trouser","button","polo"]

    prefer_ethnic = event_type in ETHNIC_EVENTS
    prefer_athletic = event_type in ATHLETIC_EVENTS

    def score_item(item):
        score = 0.0
        text = " ".join([
            item.get("item_name",""), item.get("color",""),
            item.get("category",""), item.get("style",""),
            " ".join(item.get("occasion",[]))
        ]).lower()

        # Formality match
        formality = item.get("formality","casual")
        if event_type in ("wedding","reception","interview","office") and formality == "formal":
            score += 6
        elif event_type in ("party","date","dinner","sangeet") and formality == "semi-formal":
            score += 5
        elif event_type in ("casual","college","brunch") and formality == "casual":
            score += 4

        # Event occasion match
        if event_type in [o.lower() for o in item.get("occasion", [])]:
            score += 7

        # Ethnic bonus
        if prefer_ethnic and any(kw in text for kw in ETHNIC_KW):
            score += 10

        # Formal bonus
        if event_type in ("office","interview") and any(kw in text for kw in FORMAL_KW):
            score += 5

        # Category variety bonus (prefer diverse categories)
        return score

    scored = [(score_item(item), item) for item in all_items]
    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top items but ensure category diversity
    seen_cats = set()
    result = []
    for _, item in scored:
        cat = item.get("category", "")
        # Allow max 2 per category
        cat_count = sum(1 for i in result if i.get("category") == cat)
        if cat_count < 2:
            result.append(item)
        if len(result) >= max_items:
            break

    # If we still have room, add remaining
    if len(result) < max_items:
        for _, item in scored:
            if item not in result:
                result.append(item)
            if len(result) >= max_items:
                break

    print(f"🎯 Wardrobe: {len(result)} top items selected from {len(all_items)} total for event={event_type}")
    return result[:max_items]


# ── Outfit plan ───────────────────────────────────────────────────────────────

def _get_outfit_plan(event_type, days, gender, skin_tone, face_shape, body_shape, conditions, wardrobe_items, user_name):
    is_male = _is_male(gender)
    gl = "male" if is_male else "female"

    wardrobe_desc = "\n".join([
        f"- {item.get('color','')} {item.get('item_name','')} ({item.get('category','')})"
        for item in wardrobe_items
    ]) if wardrobe_items else "No wardrobe items found"

    tone_colors = {
        "dark":   "bold jewel tones: electric blue, emerald green, saffron yellow, magenta, coral, royal blue, fuchsia",
        "medium": "warm earth tones: mustard, teal, burgundy, terracotta, forest green, rust orange",
        "light":  "soft pastels: lavender, mint green, sage, blush pink, powder blue, ivory, champagne",
    }.get(skin_tone.lower(), "complementary tones")

    acc_rule = (
        "Men only: watch (gold/silver), bracelet/kada, sunglasses, belt. NEVER necklace or earrings."
        if is_male else
        "Women only: necklace, earrings, bangles/bracelet, handbag, bindi (for ethnic). NEVER men's watch style."
    )

    prompt = f"""You are the world's best Indian fashion stylist creating an event plan.

CLIENT: {user_name} | {gl} | {skin_tone} skin → best colors: {tone_colors} | {face_shape} face | {body_shape} body
EVENT: {event_type} (in {days} days)
CONDITIONS: {', '.join(conditions) if conditions else 'normal skin'}

WARDROBE ITEMS AVAILABLE:
{wardrobe_desc}

ACCESSORY RULE: {acc_rule}

Return ONLY valid JSON (no markdown):
{{
  "main_outfit": {{
    "description": "2 sentences: exact outfit with specific colors that suit {skin_tone} skin at a {event_type}",
    "top": "specific item name from wardrobe or recommendation",
    "bottom": "specific item name from wardrobe or recommendation",
    "shoes": "specific shoes",
    "accessories": ["3-4 gender-appropriate accessories only"],
    "colors": ["color1", "color2", "color3"],
    "why_these_colors": "1-2 sentences: why these colors work for {skin_tone} skin at {event_type}"
  }},
  "backup_outfit": {{
    "description": "1 sentence alternative",
    "top": "backup top from wardrobe",
    "bottom": "backup bottom",
    "shoes": "backup shoes"
  }},
  "wardrobe_suggestion": "1 specific tip using wardrobe items",
  "excitement_message": "1 punchy line about this event"
}}"""

    try:
        resp = llm.invoke(prompt)
        raw  = resp.content if hasattr(resp,"content") else str(resp)
        data = _extract_json(raw)
        if data and "main_outfit" in data:
            return data
    except Exception as e:
        print(f"Outfit plan error: {e}")

    # Fallback
    color = {"dark":"saffron yellow","medium":"mustard","light":"lavender"}.get(skin_tone.lower(),"navy blue")
    return {
        "main_outfit": {
            "description": f"A stunning {event_type} look for {skin_tone} skin.",
            "top": "Embroidered kurta" if event_type in ("wedding","festival","sangeet") else "Fitted shirt",
            "bottom": "Churidar pants" if event_type in ("wedding","festival","sangeet") else "Slim trousers",
            "shoes": "Kolhapuri sandals" if event_type in ("wedding","festival","sangeet") else "Leather loafers",
            "accessories": ["Gold dial watch","Silver bracelet","Aviator sunglasses"] if is_male else ["Gold jhumka","Gold bangles","Potli bag"],
            "colors": [color, "white", "black"],
            "why_these_colors": f"{color} is stunning on {skin_tone} skin — creates beautiful contrast and warmth.",
        },
        "backup_outfit": {
            "description": "A versatile backup look from your wardrobe.",
            "top": "Polo shirt",
            "bottom": "Slim chinos",
            "shoes": "White sneakers",
        },
        "wardrobe_suggestion": "Mix your most formal items for the best look.",
        "excitement_message": f"Get ready to be the best dressed at your {event_type}!",
    }


# ── Skincare timeline (beautiful step arrays) ─────────────────────────────────

def _get_skincare_timeline(days, skin_tone, conditions, event_type):
    """
    Returns timeline with morning_steps[] and night_steps[] arrays
    for beautiful step-by-step rendering in the UI.
    """
    conditions_str = ", ".join(conditions) if conditions else "normal skin"
    has_acne     = any("acne"        in c.lower() for c in conditions)
    has_dc       = any("dark circle" in c.lower() for c in conditions)
    has_spots    = any("dark spot"   in c.lower() or "hyperpig" in c.lower() for c in conditions)
    has_dry      = any("dry"         in c.lower() for c in conditions)

    tone_note = {
        "dark":   "Dark skin tip: niacinamide is essential to prevent PIH. Avoid harsh peels.",
        "medium": "Medium skin tip: SPF 50 every morning to prevent tanning. Niacinamide for evenness.",
        "light":  "Light skin tip: Be gentle — SPF 50+ critical. Centella for sensitivity.",
    }.get(skin_tone.lower(), "")

    # Build condition-specific routine rules
    rules = []
    if has_acne:
        rules.append("For acne: serum_night = salicylic acid 2% BHA (NOT retinol). Day serum = niacinamide 10%.")
    if has_dc:
        rules.append("For dark circles: always include caffeine eye cream morning and night.")
    if has_spots:
        rules.append("For dark spots: vitamin C 15% serum every morning.")
    if has_dry:
        rules.append("For dry skin: hyaluronic acid serum + ceramide moisturiser.")
    if not rules:
        rules.append("Normal skin: niacinamide day + peptide repair night.")

    rules_str = "\n".join(rules)

    prompt = f"""Expert dermatologist creating a {days}-day skincare prep for {event_type}.
CLIENT: {skin_tone} skin, conditions: {conditions_str}
{tone_note}
INGREDIENT RULES:
{rules_str}

Return ONLY a valid JSON array with {min(days+1, 7)} entries:
[
  {{
    "day": "Day 3 — 3 Days Before",
    "focus": "one-line focus for this day",
    "morning_steps": [
      "Step 1: Gentle cleanser — massage 60 seconds",
      "Step 2: Vitamin C serum — 2-3 drops, press gently",
      "Step 3: Light moisturiser",
      "Step 4: SPF 50 — last step always"
    ],
    "night_steps": [
      "Step 1: Double cleanse if wearing makeup",
      "Step 2: Niacinamide 10% serum",
      "Step 3: Salicylic acid 2% (acne areas only)",
      "Step 4: Ceramide moisturiser"
    ],
    "tip": "one specific tip for this day"
  }}
]

Rules:
- morning_steps: 4-5 numbered steps with specific application tips
- night_steps: 4-5 numbered steps with specific active ingredients
- For acne skin: night serum = salicylic acid 2% BHA (NEVER retinol for active acne)
- Last day (event day): "Day 0" or "Event Day" — minimal routine, NO actives
- Include SPF 50 EVERY morning step 4
- Be specific: "Niacinamide 10% serum — 2-3 drops, let absorb 60 seconds"
- {min(days+1, 7)} entries total for {days} days prep"""

    try:
        resp = llm.invoke(prompt)
        raw  = resp.content if hasattr(resp,"content") else str(resp)
        data = _extract_json_array(raw)
        if data and len(data) > 0:
            return data
    except Exception as e:
        print(f"Skincare timeline error: {e}")

    # Fallback timeline
    timeline = []
    for i in range(min(days, 5)):
        d = days - i
        is_event = d == 0
        timeline.append({
            "day": "Event Day ★" if is_event else f"Day {d} — {d} Day{'s' if d>1 else ''} Before",
            "focus": "Gentle & minimal — let your prep shine" if is_event else f"{'Start treatment' if i==0 else 'Continue routine'}",
            "morning_steps": [
                "Gentle cleanser — 60 second massage, rinse with cool water",
                "Caffeine eye cream (if dark circles)" if has_dc else "Toner — pat gently, don't rub",
                "Vitamin C 15% serum — 2-3 drops, press into skin" if (has_spots and not is_event) else "Niacinamide 10% — 2-3 drops",
                "Light moisturiser — wait 2 minutes after serum",
                "SPF 50 PA+++ — apply generously as the final step",
            ] if not is_event else [
                "Gentle cleanser — extra gentle today",
                "Light hydrating moisturiser",
                "SPF 50 — skip all actives today",
            ],
            "night_steps": [
                "Remove makeup thoroughly if worn",
                "Cleanser — salicylic acid 2% (acne) or gentle cream (dry)" if not is_event else "Gentle cleanser only",
                "Salicylic acid 2% BHA serum — acne areas" if (has_acne and not is_event) else ("Hyaluronic acid serum" if has_dry else "Peptide repair serum"),
                "Rich ceramide moisturiser — lock in hydration",
            ] if not is_event else ["Gentle cleanser", "Light moisturiser"],
            "tip": (
                "Sleep 7-8 hours — skin repairs overnight!" if i < 2
                else "No new products today — stick to what your skin knows"
                if i < days-1
                else "Skin is prepped and ready to glow!"
            ),
        })
    return timeline


# ── Shopping list ─────────────────────────────────────────────────────────────

def _get_shopping_list(event_type, gender, skin_tone, user_id):
    from services.product_service import get_product_recommendations

    is_male = _is_male(gender)
    gl = "men" if is_male else "women"

    SKIN_COLORS = {
        "dark":   ["electric blue","saffron yellow","emerald green","coral","magenta"],
        "medium": ["mustard","teal","burgundy","forest green","terracotta"],
        "light":  ["pastel blue","lavender","mint green","sage green","blush pink"],
    }
    power_color = random.choice(SKIN_COLORS.get(skin_tone.lower(), SKIN_COLORS["medium"])[:3])

    # Event-specific queries (gender-aware, skin-tone-aware)
    EVENT_QUERIES = {
        "wedding":    {"ethnic":f"{power_color} sherwani indo-western kurta {gl} India wedding","shoes":"kolhapuri mojri ethnic shoes {gl} India","accessories":"gold watch kada bracelet {gl} ethnic India"} if is_male else {"ethnic":f"{power_color} lehenga choli saree {gl} India wedding","shoes":"heels juttis ethnic sandals {gl} India","accessories":"gold jewellery jhumka bangles {gl} India"},
        "sangeet":    {"ethnic":f"{power_color} silk kurta set {gl} India sangeet festive","shoes":"mojri juttis ethnic shoes {gl} India","accessories":"gold watch bracelet {gl} India sangeet"} if is_male else {"ethnic":f"{power_color} lehenga anarkali {gl} India sangeet","shoes":"heels ethnic sandals {gl} India","accessories":"gold earrings bangles {gl} India"},
        "festival":   {"ethnic":f"{power_color} festive kurta ethnic print {gl} India Diwali","shoes":"kolhapuri juttis ethnic {gl} India","accessories":"gold watch bracelet {gl} India festive"} if is_male else {"ethnic":f"{power_color} kurti anarkali {gl} India festive","shoes":"juttis sandals ethnic {gl} India","accessories":"gold earrings bangles necklace {gl} India"},
        "party":      {"shirt":f"{power_color} party shirt bold slim fit {gl} India night out","pants":"slim fit dark party trousers {gl} India","shoes":"leather loafers boots party {gl} India"} if is_male else {"top":f"{power_color} party dress bodysuit {gl} India night out","pants":"mini skirt wide leg trousers {gl} India party","shoes":"heels block pumps party {gl} India"},
        "office":     {"shirt":f"formal slim fit shirt {gl} India office professional","pants":"formal slim trousers {gl} India office","shoes":"leather oxford derby shoes {gl} India formal"} if is_male else {"top":"formal blouse shirt {gl} India office","pants":"formal straight trousers {gl} India office","shoes":"block heels formal {gl} India office"},
        "interview":  {"shirt":f"white light blue formal shirt {gl} India interview slim fit","pants":"formal slim trousers black navy {gl} India","shoes":"black leather derby oxford {gl} India formal"} if is_male else {"top":"formal white pastel blouse {gl} India interview","pants":"formal straight trousers {gl} India","shoes":"block heels formal {gl} India interview"},
        "date":       {"shirt":f"{power_color} smart casual shirt {gl} India date night","pants":"slim dark jeans chinos {gl} India date","shoes":"leather loafers boots {gl} India date"} if is_male else {"top":f"{power_color} off shoulder wrap date outfit {gl} India","pants":"slim jeans wide leg {gl} India date","shoes":"block heels strappy {gl} India date"},
        "gym":        {"gym_tshirt":f"{power_color} dry fit gym t-shirt Nike Puma {gl} India","track_pants":"Nike Puma track pants jogger training {gl} India","sports_shoes":"Nike Adidas running training shoes {gl} India"},
        "beach":      {"beach_shirt":f"linen floral beach shirt relaxed {gl} India summer","swim_shorts":"quick dry swim shorts beach {gl} India","flip_flops":"flip flops Havaianas beach sandals {gl} India"},
        "college":    {"shirt":f"oversized graphic t-shirt streetwear {gl} India college","pants":"slim jeans cargo {gl} India casual college","shoes":"white chunky sneakers {gl} India college"},
        "dinner":     {"shirt":f"{power_color} smart casual dinner shirt {gl} India","pants":"slim fit dark trousers {gl} India dinner","shoes":"leather loafers smart {gl} India dinner"} if is_male else {"top":f"{power_color} elegant blouse {gl} India dinner","pants":"wide leg trousers {gl} India dinner","shoes":"block heels {gl} India dinner"},
        "casual":     {"shirt":f"{power_color} casual polo t-shirt {gl} India","pants":"slim jeans comfortable {gl} India","shoes":"white sneakers everyday {gl} India"},
    }

    queries = EVENT_QUERIES.get(event_type, EVENT_QUERIES["casual"])
    shopping_list = []

    for cat, query in list(queries.items())[:5]:
        try:
            prods = get_product_recommendations(query, cat, event_type, user_id=user_id)
            deduped = _deduplicate_products(prods or [])
            shopping_list.append({
                "category":       cat,
                "item":           cat.replace("_", " ").title(),
                "query":          query,
                "priority":       "must-have" if cat in ("shirt","top","ethnic","pants","shoes","gym_tshirt","track_pants","sports_shoes") else "nice-to-have",
                "estimated_price": _price_est(cat, event_type),
                "products":        deduped[:4],
            })
        except Exception as e:
            print(f"Shopping [{cat}] error: {e}")
            shopping_list.append({
                "category": cat, "item": cat.replace("_"," ").title(),
                "query": query, "priority":"must-have",
                "estimated_price":"₹500–₹3000", "products":[],
            })

    return shopping_list


def _price_est(cat, event_type):
    base = {"ethnic":"₹1500–₹8000","sherwani":"₹3000–₹15000","shoes":"₹800–₹3000",
            "accessories":"₹300–₹2000","shirt":"₹500–₹2500","top":"₹400–₹2000",
            "pants":"₹600–₹3000","gym_tshirt":"₹400–₹1500","track_pants":"₹500–₹2000",
            "sports_shoes":"₹800–₹4000","blazer":"₹1500–₹6000","dress":"₹800–₹4000"}.get(cat,"₹500–₹3000")
    if event_type in ("wedding","reception","sangeet"):
        return "₹2000–₹15000"
    return base


def _get_checklist(event_type, days, gender):
    is_male = _is_male(gender)
    base = [
        "Iron or steam your outfit the night before",
        "Polish your shoes",
        "Lay out all accessories the night before",
        "Set alarm 30 mins earlier than planned",
        "Confirm event address and transport",
        "Charge your phone to 100%",
        "Prepare a backup outfit just in case",
    ]
    grooming = [
        ("Trim beard cleanly (do it 2 days before)" if is_male else "Get nails done if planned"),
        ("Apply cologne/perfume subtly" if is_male else "Decide makeup look and rehearse it"),
        ("Haircut if overdue — book 3 days before" if is_male else "Blow dry or set hair the night before"),
    ]
    ethnic = [
        ("Starch the kurta if needed" if is_male else "Practice draping saree/lehenga"),
        "Pack safety pins for ethnic wear",
    ] if event_type in ("wedding","reception","sangeet","festival","puja","mehndi","haldi","engagement") else []
    return (base + grooming + ethnic)[:10]


def _get_grooming_tips(event_type, gender, face_shape, skin_tone):
    is_male = _is_male(gender)
    shape_tips = {
        "oval":   "Any hairstyle or collar works — oval face is versatile!",
        "round":  "Add volume on top to elongate. Avoid bowl cuts and turtlenecks.",
        "square": "Soft textured styles soften the jaw. Open collars work great.",
        "heart":  "Side-swept styles balance a wider forehead. Scoop or boat necks flatter.",
    }
    skin_tips = {
        "dark":   "Apply moisturiser 30 mins before the event — dark skin glows with hydration. Skip heavy powder.",
        "medium": "Light BB cream or tinted moisturiser gives the perfect natural finish.",
        "light":  "SPF is essential even indoors. A light bronzer adds warmth to fair skin.",
    }
    return [
        shape_tips.get(face_shape.lower(), "Choose a hairstyle that frames your face."),
        skin_tips.get(skin_tone.lower(), "Keep skin moisturised and glowing."),
        "Trim or clean beard 2 days before (day-before irritation is real)" if is_male else "Bold lip OR smoky eye — never both",
        f"For {event_type}: {'a subtle cologne goes further than a strong one' if event_type in ('date','party','wedding') else 'fresh and clean is the best accessory'}",
        "Trim nails and clean hands — people notice!" if is_male else "Set your makeup with a setting spray for long-lasting wear",
    ]


# ── Main Route ────────────────────────────────────────────────────────────────

@event_planner_bp.route("/event-planner/plan", methods=["POST"])
def plan_event():
    data     = request.json or {}
    message  = data.get("message", "").strip()
    user_ctx = data.get("user_context", {})
    user_id  = data.get("user_id", user_ctx.get("name","")) or ""

    skin_tone  = user_ctx.get("skinTone",   "medium")
    face_shape = user_ctx.get("face_shape", "oval")
    gender     = user_ctx.get("gender",     "male")
    conditions = user_ctx.get("conditions", []) or []
    body_shape = user_ctx.get("body_shape", "average")
    user_name  = user_ctx.get("name", "friend") or "friend"

    if not message:
        return jsonify({"error": "message is required"}), 400

    # 1. Detect event
    event_type, days, icon = _detect_event(message)
    print(f"📅 Event: {event_type} | Days: {days} | Gender: {gender} | Skin: {skin_tone} | User: {user_id}")

    # 2. KEY FIX: Get TOP 6 most relevant wardrobe items only
    wardrobe_items = _get_top_wardrobe_items(user_id, event_type, max_items=6)
    print(f"👚 Top {len(wardrobe_items)} wardrobe items selected for {event_type}")

    # 3. Outfit plan
    outfit_plan = _get_outfit_plan(
        event_type, days, gender, skin_tone, face_shape,
        body_shape, conditions, wardrobe_items, user_name,
    )

    # 4. Skincare timeline with beautiful step arrays
    skincare_timeline = _get_skincare_timeline(days, skin_tone, conditions, event_type)

    # 5. Shopping list (deduplicated)
    shopping_list = _get_shopping_list(event_type, gender, skin_tone, user_id)

    # 6. Checklist + grooming
    checklist     = _get_checklist(event_type, days, gender)
    grooming_tips = _get_grooming_tips(event_type, gender, face_shape, skin_tone)

    # 7. Skincare summary for banner
    tone_summaries = {
        "dark":   "Bold jewel tones work best for you. Niacinamide is your best friend to keep that gorgeous glow.",
        "medium": "Warm earthy tones complement your skin. SPF 50 every morning — non-negotiable.",
        "light":  "Pastel and neutral shades are your power palette. Gentle actives work best.",
    }
    skincare_summary = tone_summaries.get(skin_tone.lower(), "Personalised routine for your unique skin.")

    event_day_tip = "Keep it minimal on event day. Gentle cleanser → SPF → light moisturiser. Skip all actives — your prep work is done and your skin is ready!"

    confidence = f"Walk in knowing you've prepared perfectly. Your {skin_tone} skin in {', '.join((outfit_plan.get('main_outfit',{}).get('colors',[]) or ['complementary tones'])[:2])} is going to be stunning. Own the room."

    return jsonify({
        "event":             event_type,
        "event_icon":        icon,
        "days_until":        days,
        "excitement_message": outfit_plan.get("excitement_message", f"Ready to be the best dressed at your {event_type}!"),

        # Wardrobe — ONLY top 6, full objects with image_url
        "wardrobe_count":    len(wardrobe_items),
        "wardrobe_items":    wardrobe_items,

        # Plans
        "outfit_plan":       outfit_plan,
        "skincare_timeline": skincare_timeline,
        "skincare_summary":  skincare_summary,
        "event_day_skin_tip": event_day_tip,
        "shopping_list":     shopping_list,
        "day_of_checklist":  checklist,
        "grooming_tips":     grooming_tips,
        "confidence_tip":    confidence,
    })


@event_planner_bp.route("/event-planner/quick", methods=["POST"])
def quick_detect():
    data    = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400
    event_type, days, icon = _detect_event(message)
    return jsonify({"event": event_type, "event_icon": icon, "days_until": days})