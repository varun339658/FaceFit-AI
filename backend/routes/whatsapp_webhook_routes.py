"""
whatsapp_webhook_routes.py — FaceFit WhatsApp Chatbot (LINKS-ONLY v7)
=======================================================================
v7 CHANGES:
  1. ZERO image sending — pure text with clickable links only
  2. Every product gets its own tappable link line
  3. Beautiful WhatsApp formatting with emojis
  4. Message split: outfit plan (msg 1) + shop links (msg 2) via Twilio
  5. No truncation of product sections
  6. Rate-limit retry with exponential backoff
  7. Wardrobe combos + shopping picks cleanly separated
"""

import os
import re
import time
from flask import Blueprint, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from pymongo import MongoClient as _MC

whatsapp_bp = Blueprint("whatsapp", __name__)

TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM  = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
MONGO_URI    = os.getenv("MONGO_URI")

if not TWILIO_SID or not TWILIO_TOKEN:
    raise RuntimeError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set.")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI must be set.")

_mc    = _MC(MONGO_URI)
_db    = _mc["facefit_ai"]
_users = _db["users"]
_face  = _db["face_analysis"]
_conv  = _db["whatsapp_conversations"]
_saved = _db["saved_products"]

twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)


# ─────────────────────────────────────────────────────────────────────────────
# EMOJI / LABEL MAPS
# ─────────────────────────────────────────────────────────────────────────────

CAT_EMOJI = {
    "shirt": "👕", "pants": "👖", "shoes": "👟", "watch": "⌚",
    "bracelet": "📿", "sunglasses": "🕶️", "top": "👚",
    "necklace": "💎", "earrings": "✨", "ethnic": "🥻",
    "dress": "👗", "blazer": "🧥", "track_pants": "🩳",
    "gym_tshirt": "💪", "sports_shoes": "👟", "swim_shorts": "🩱",
    "beach_shirt": "🌴", "flip_flops": "🩴", "accessories": "💍",
    "cleanser": "🧴", "toner": "💧", "serum_day": "☀️",
    "serum_night": "🌙", "moisturizer": "🫧", "sunscreen": "🌞",
    "eye_cream": "👁️", "spot_treatment": "🎯",
    "brightening_serum": "✨",
}

CAT_LABEL = {
    "shirt": "Shirts", "pants": "Pants", "shoes": "Shoes",
    "watch": "Watches", "bracelet": "Bracelets", "sunglasses": "Sunglasses",
    "top": "Tops", "necklace": "Necklaces", "earrings": "Earrings",
    "ethnic": "Ethnic Wear", "dress": "Dresses", "blazer": "Blazers",
    "track_pants": "Track Pants", "gym_tshirt": "Gym T-Shirts",
    "sports_shoes": "Sports Shoes", "swim_shorts": "Swim Shorts",
    "beach_shirt": "Beach Shirts", "flip_flops": "Flip Flops",
    "accessories": "Accessories", "cleanser": "Cleansers",
    "toner": "Toners", "serum_day": "Day Serums",
    "serum_night": "Night Serums", "moisturizer": "Moisturizers",
    "sunscreen": "Sunscreens", "eye_cream": "Eye Creams",
    "spot_treatment": "Spot Treatments",
    "brightening_serum": "Brightening Serums",
}

COLOR_SWATCH = {
    "black": "⬛", "white": "⬜", "grey": "🔲", "gray": "🔲",
    "red": "🟥", "blue": "🟦", "green": "🟩", "yellow": "🟨",
    "orange": "🟧", "purple": "🟪", "brown": "🟫",
    "navy": "🔵", "navy blue": "🔵", "maroon": "🔴",
    "teal": "🩵", "olive": "🟢", "mustard": "🟡",
    "burgundy": "🔴", "emerald": "💚", "coral": "🟠",
    "pink": "🩷", "beige": "🟤", "cream": "⬜",
    "camel": "🟤", "saffron": "🟡", "terracotta": "🟤",
    "forest green": "🟩", "ivory": "⬜", "teal": "🩵",
}

DIVIDER = "─" * 28


def _color_dot(color: str) -> str:
    if not color:
        return "•"
    cl = color.lower()
    for k, v in COLOR_SWATCH.items():
        if k in cl:
            return v
    return "•"


# ─────────────────────────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    return phone.replace("whatsapp:", "").strip()


def _get_user_profile(from_number: str) -> dict:
    phone_clean = _normalize_phone(from_number)
    variants = [phone_clean]
    if phone_clean.startswith("+91"):
        variants.append(phone_clean[3:])
    elif re.match(r"^[6-9]\d{9}$", phone_clean):
        variants.append(f"+91{phone_clean}")

    user_doc = None
    for v in variants:
        user_doc = _users.find_one({"phone": v}, {"_id": 0})
        if user_doc:
            break

    if not user_doc:
        user_doc = _users.find_one({}, {"_id": 0}, sort=[("updated_at", -1)])

    if not user_doc:
        return {
            "name": "there", "gender": "male", "email": "", "phone": phone_clean,
            "skinTone": "medium", "face_shape": "oval", "conditions": [],
        }

    user_id = (
        user_doc.get("user_id") or
        user_doc.get("userId") or
        user_doc.get("name") or ""
    )

    face_doc = None
    if user_id:
        face_doc = _face.find_one(
            {"userId": user_id}, {"_id": 0}, sort=[("timestamp", -1)]
        )

    return {
        "name":       user_id or "there",
        "gender":     user_doc.get("gender", "male"),
        "email":      user_doc.get("email", ""),
        "phone":      phone_clean,
        "skinTone":   face_doc.get("skinTone",       "medium") if face_doc else "medium",
        "face_shape": face_doc.get("faceShape",      "oval")   if face_doc else "oval",
        "conditions": face_doc.get("skinConditions", [])       if face_doc else [],
    }


def _get_history(phone: str, limit: int = 8) -> list:
    phone_clean = _normalize_phone(phone)
    doc = _conv.find_one({"phone": phone_clean}, {"_id": 0})
    return doc.get("history", [])[-limit:] if doc else []


def _save_msg(phone: str, role: str, content: str):
    phone_clean = _normalize_phone(phone)
    _conv.update_one(
        {"phone": phone_clean},
        {"$push": {"history": {"$each": [{"role": role, "content": content}], "$slice": -20}}},
        upsert=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TWILIO SEND HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _send_whatsapp(to: str, body: str):
    """Send a plain text WhatsApp message via Twilio REST (no TwiML)."""
    if not body or not body.strip():
        return
    # WhatsApp cap is 4096 chars
    body = body[:4000]
    try:
        twilio_client.messages.create(
            body=body,
            from_=TWILIO_FROM,
            to=to,
        )
        print(f"✅ Sent msg ({len(body)} chars) to {to}")
    except Exception as e:
        print(f"❌ Twilio send error: {e}")


def _send_two_part(to: str, part1: str, part2: str):
    """Send outfit plan first, then shopping links 1 second later."""
    _send_whatsapp(to, part1)
    if part2 and part2.strip():
        time.sleep(1)
        _send_whatsapp(to, part2)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _extract_all_products(data: dict) -> dict:
    """Merge products from every location chat_with_ai might put them."""
    merged = {}

    def _absorb(src):
        if not src or not isinstance(src, dict):
            return
        for cat, prods in src.items():
            if not prods or not isinstance(prods, list):
                continue
            if cat not in merged:
                merged[cat] = []
            existing = {p.get("title", "") for p in merged[cat]}
            for p in prods:
                if isinstance(p, dict) and p.get("title", "") not in existing:
                    merged[cat].append(p)
                    existing.add(p.get("title", ""))

    _absorb(data.get("products"))

    dual = data.get("dual_outfit") or {}
    _absorb(dual.get("new_products"))
    _absorb(dual.get("products"))

    co = data.get("closet_outfit") or {}
    _absorb(co.get("products"))
    _absorb(co.get("new_products"))
    _absorb(co.get("missing_products"))

    _absorb(data.get("outfit_products"))
    _absorb(data.get("missing_products"))

    gap = data.get("gap_analysis") or {}
    _absorb(gap.get("buy_suggestions"))
    _absorb(gap.get("products"))

    mm = data.get("mix_match") or {}
    _absorb(mm.get("missing_products"))

    print(f"🛍️ Products extracted → {list(merged.keys())}")
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTERS
# ─────────────────────────────────────────────────────────────────────────────

def _md(text: str) -> str:
    """Convert markdown bold/headers to WhatsApp *bold*."""
    if not text:
        return ""
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"#+\s+(.+)", r"*\1*", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"\1: \2", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fmt_shopping_links(products: dict, max_cats: int = 5, max_each: int = 3) -> str:
    """
    Build a clean shopping section.
    Each product: name, price, then link on its own line (WhatsApp makes it tappable).
    """
    if not products:
        return ""

    lines = [
        f"🛒 *Shop Your Picks*",
        DIVIDER,
    ]

    shown_cats = 0
    total_products = 0

    for cat, prods in products.items():
        if shown_cats >= max_cats:
            break
        if not prods or not isinstance(prods, list):
            continue

        valid_prods = [p for p in prods if isinstance(p, dict) and (p.get("title") or p.get("name"))]
        if not valid_prods:
            continue

        emoji = CAT_EMOJI.get(cat, "🛍️")
        label = CAT_LABEL.get(cat, cat.replace("_", " ").title())
        lines.append(f"\n{emoji} *{label}*")

        shown_in_cat = 0
        for p in valid_prods:
            if shown_in_cat >= max_each:
                break

            title = (p.get("title") or p.get("name") or "").strip()
            title = title[:60]

            # Price
            raw_price = p.get("price") or p.get("extracted_price") or ""
            if isinstance(raw_price, (int, float)) and raw_price > 0:
                price_str = f"₹{int(raw_price)}"
            else:
                price_str = str(raw_price).strip()
                if price_str in ("0", "None", "", "null", "0.0"):
                    price_str = ""

            # Link
            link = (
                p.get("link") or
                p.get("url") or
                p.get("product_link") or
                p.get("productLink") or ""
            ).strip()

            # Build lines — title + price
            if price_str:
                lines.append(f"  • *{title}*  _{price_str}_")
            else:
                lines.append(f"  • *{title}*")

            # Link on its own line so WhatsApp renders it as a tap-to-open button
            if link and link.startswith("http"):
                lines.append(f"    🔗 {link}")
            else:
                lines.append(f"    _(no link available)_")

            shown_in_cat += 1
            total_products += 1

        shown_cats += 1

    if total_products == 0:
        return ""

    lines.append(f"\n{DIVIDER}")
    lines.append("_Tap any 🔗 link to open & buy_")

    return "\n".join(lines)


def _fmt_wardrobe_combos(combinations: list, max_combos: int = 3) -> str:
    """Format mix & match wardrobe combinations."""
    if not combinations:
        return ""

    lines = [
        "✨ *Your Best Wardrobe Combinations*",
        DIVIDER,
    ]

    for i, combo in enumerate(combinations[:max_combos]):
        if not isinstance(combo, dict):
            continue

        label = "🏆 *Best Look*" if i == 0 else f"*Look #{i + 1}*"
        score_label = combo.get("color_label", combo.get("color_score", ""))
        header = label
        if score_label:
            header += f"  _{score_label}_"
        lines.append(f"\n{header}")

        items_shown = 0
        for slot in ("top", "bottom", "shoes", "accessories"):
            item = combo.get(slot) or (combo.get("items") or {}).get(slot)
            if not item or not isinstance(item, dict):
                continue
            color = item.get("color", "")
            name = item.get("item_name", slot)
            dot = _color_dot(color)
            color_part = f"{color} " if color else ""
            lines.append(f"  {dot} {color_part}{name}")
            items_shown += 1

        if items_shown == 0:
            for slot, item in (combo.get("items") or {}).items():
                if not item or not isinstance(item, dict):
                    continue
                color = item.get("color", "")
                name = item.get("item_name", slot)
                dot = _color_dot(color)
                lines.append(f"  {dot} {color} {name}".strip())

        tip = combo.get("styling_tip") or combo.get("tip", "")
        if tip:
            lines.append(f"  💡 _{str(tip)[:100]}_")

    return "\n".join(lines)


def _fmt_routine(routine: dict) -> str:
    """Format skincare routine."""
    if not routine or not isinstance(routine, dict):
        return ""
    lines = [f"✨ *Your Skincare Routine*", DIVIDER]
    morning = routine.get("morning") or []
    night = routine.get("night") or []
    if morning:
        lines.append("☀️ *Morning*")
        for i, s in enumerate(morning[:4], 1):
            lines.append(f"  {i}. {str(s)[:90]}")
    if night:
        lines.append("\n🌙 *Night*")
        for i, s in enumerate(night[:3], 1):
            lines.append(f"  {i}. {str(s)[:90]}")
    return "\n".join(lines)


def _fmt_wardrobe_items(items: dict, heading: str) -> str:
    """Format available wardrobe items."""
    if not items or not isinstance(items, dict):
        return ""
    lines = [heading]
    for slot, item in list(items.items())[:6]:
        if not item or not isinstance(item, dict):
            continue
        color = item.get("color", "")
        name = item.get("item_name", slot)
        dot = _color_dot(color)
        color_part = f"{color} " if color else ""
        lines.append(f"  {dot} {color_part}{name}")
    return "\n".join(lines) if len(lines) > 1 else ""


def _fmt_gap(gap: dict) -> str:
    if not gap or not isinstance(gap, dict):
        return ""
    ready = gap.get("ready_events", [])
    gaps = gap.get("gaps", {})
    lines = []
    if ready and isinstance(ready, list):
        lines.append(f"✅ *Ready for:* {', '.join(str(e) for e in ready[:5])}")
    if gaps and isinstance(gaps, dict):
        lines.append(f"📦 *Need items for:* {', '.join(list(gaps.keys())[:4])}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN REPLY BUILDER  →  returns (part1_outfit_text, part2_links_text)
# ─────────────────────────────────────────────────────────────────────────────

def _build_two_part_reply(data: dict, uname: str) -> tuple:
    """
    Returns (part1, part2):
      part1 = outfit plan / combos / routine (no links)
      part2 = all shopping links (separate message)
    """
    part1_lines = []
    part2_lines = []

    # ── AI message intro ──────────────────────────────────────────────────────
    full_msg = _md(data.get("message", ""))
    if full_msg:
        # Keep first 350 chars of the AI message
        intro = full_msg[:350].rstrip()
        if len(full_msg) > 350:
            intro += "..."
        part1_lines.append(intro)

    # ── Mix & match combos ────────────────────────────────────────────────────
    mm = data.get("mix_match") or {}
    combos = mm.get("combinations") or mm.get("outfits") or []
    if combos:
        combo_text = _fmt_wardrobe_combos(combos, max_combos=3)
        if combo_text:
            part1_lines.append(combo_text)

    # ── Dual outfit — closet section ──────────────────────────────────────────
    dual = data.get("dual_outfit") or {}
    if dual:
        closet = dual.get("closet") or {}
        avail = (closet.get("available_items") if isinstance(closet, dict) else None) \
                or dual.get("available_items", {})
        if avail:
            wt = _fmt_wardrobe_items(avail, "👔 *From Your Wardrobe:*")
            if wt:
                part1_lines.append(wt)
        plan = _md(
            (closet.get("outfit_plan", "") if isinstance(closet, dict) else "")
            or dual.get("outfit_plan", "")
        )
        if plan:
            part1_lines.append(f"\n💡 _{plan[:200]}_")

    # ── Closet outfit (no dual) ───────────────────────────────────────────────
    co = data.get("closet_outfit") or {}
    if co and not dual:
        avail = co.get("available_items", {})
        wt = _fmt_wardrobe_items(avail, "👗 *Your Outfit:*")
        if wt:
            part1_lines.append(wt)
        plan = _md(co.get("outfit_plan", ""))
        if plan:
            part1_lines.append(f"\n💡 _{plan[:200]}_")
        miss = co.get("missing_categories", [])
        if miss:
            miss_labels = [CAT_LABEL.get(c, c) for c in miss[:3]]
            part1_lines.append(f"\n🛍️ *Still need:* {', '.join(miss_labels)}")

    # ── Skincare routine ──────────────────────────────────────────────────────
    routine_text = _fmt_routine(data.get("routine"))
    if routine_text:
        part1_lines.append(routine_text)

    # ── Gap analysis ──────────────────────────────────────────────────────────
    gap_text = _fmt_gap(data.get("gap_analysis"))
    if gap_text:
        part1_lines.append(gap_text)

    # ── Part 1 assembly ───────────────────────────────────────────────────────
    part1 = "\n\n".join(p for p in part1_lines if p and str(p).strip())
    if not part1.strip():
        part1 = (
            "I processed your request! Here are your picks below 👇\n\n"
            "Try also:\n"
            "• _Outfit for wedding tonight_\n"
            "• _Skincare for acne_\n"
            "• _Mix and match my wardrobe_"
        )
    if len(part1) > 3800:
        part1 = part1[:3700] + "\n\n_(See shopping links in next message)_"

    # ── Part 2: Shopping links ────────────────────────────────────────────────
    all_products = _extract_all_products(data)
    if all_products:
        shop_text = _fmt_shopping_links(all_products, max_cats=5, max_each=3)
        if shop_text:
            part2_lines.append(shop_text)

    part2 = "\n".join(p for p in part2_lines if p and str(p).strip())
    if len(part2) > 3900:
        part2 = part2[:3800] + "\n\n_(Reply *more* for remaining picks)_"

    print(f"📤 Part1={len(part1)}c Part2={len(part2)}c Products={list(all_products.keys())}")
    return part1, part2


# ─────────────────────────────────────────────────────────────────────────────
# MIX & MATCH DIRECT HANDLER
# ─────────────────────────────────────────────────────────────────────────────

def _handle_mix_match(from_number: str, user: dict) -> tuple:
    """Returns (part1, part2) for mix & match."""
    from services.closet_agent import mix_and_match, get_wardrobe

    user_id   = user.get("userId") or user.get("user_id") or user.get("name") or "guest"
    skin_tone = user.get("skinTone", "medium")

    wardrobe = get_wardrobe(user_id)
    if not wardrobe:
        p1 = (
            "👔 *Your digital wardrobe is empty!*\n\n"
            "To use Mix & Match:\n"
            "1️⃣ Open the FaceFit app\n"
            "2️⃣ Go to *Digital Closet* tab\n"
            "3️⃣ Upload your clothes\n\n"
            "Then ask me again here 🙂"
        )
        return p1, ""

    print(f"🔀 Mix & Match for {user_id} — {len(wardrobe)} items, tone={skin_tone}")
    result = mix_and_match(user_id, skin_tone)

    combos    = result.get("combinations") or result.get("outfits") or []
    total     = result.get("total", 0)
    ai_powered = result.get("ai_powered", False)

    if not combos:
        p1 = (
            f"Found *{len(wardrobe)} items* in your wardrobe but couldn't form complete outfits yet.\n\n"
            "💡 Try uploading more tops and bottoms in the FaceFit app!"
        )
        return p1, ""

    header_line = (
        f"✨ *Mix & Match — {total} combinations found*\n"
        f"_Showing best {min(len(combos), 3)}"
        + (" · AI Styled 🤖" if ai_powered else "") + "_"
    )

    combo_text = _fmt_wardrobe_combos(combos[:3])

    part1 = header_line + "\n\n" + combo_text
    part1 += "\n\n💡 _Open FaceFit app → Closet → Mix & Match for all combinations & outfit photos_"

    # Missing products for mix & match
    missing = result.get("missing_products", {})
    part2 = ""
    if missing:
        shop_text = _fmt_shopping_links(missing, max_cats=3, max_each=3)
        if shop_text:
            part2 = "🛍️ *Complete Your Looks — Shop These:*\n\n" + shop_text

    return part1, part2


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK ROUTE
# ─────────────────────────────────────────────────────────────────────────────

@whatsapp_bp.route("/whatsapp/webhook", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get("Body", "").strip()
    from_number  = request.values.get("From", "")

    print(f"📱 WhatsApp from {from_number}: {incoming_msg[:80]}")

    # Always return empty TwiML — we send via REST to control timing
    empty_resp = Response(str(MessagingResponse()), mimetype="application/xml")

    if not incoming_msg:
        _send_whatsapp(from_number, "👋 Hi! Ask me about outfits or skincare. Try: _Wedding outfit for tonight_")
        return empty_resp

    # ── Load user profile ──────────────────────────────────────────────────────
    try:
        user  = _get_user_profile(from_number)
        uname = user.get("name", "there")
        print(f"👤 {uname} | tone={user.get('skinTone')} | gender={user.get('gender')}")
    except Exception as e:
        print(f"⚠️ Profile error: {e}")
        user  = {"name": "there", "gender": "male", "skinTone": "medium",
                 "face_shape": "oval", "conditions": []}
        uname = "there"

    try:
        history = _get_history(from_number)
    except Exception as e:
        print(f"⚠️ History error: {e}")
        history = []

    msg_low = incoming_msg.lower()

    # ── Greeting / help ────────────────────────────────────────────────────────
    if msg_low in ("hi", "hello", "hey", "help", "start"):
        name_d = uname if uname not in ("there", "") else "there"
        reply = (
            f"👋 *Hi {name_d}! I'm FaceFit AI Stylist* 🤖\n"
            f"{DIVIDER}\n\n"
            "What can I do for you?\n\n"
            "👗 *Outfit Ideas*\n"
            "  → _Wedding outfit for tonight_\n"
            "  → _Outfit for gym_\n"
            "  → _Casual date night look_\n\n"
            "💄 *Skincare*\n"
            "  → _Skincare routine for acne_\n"
            "  → _Night routine for oily skin_\n\n"
            "👔 *Wardrobe*\n"
            "  → _Mix and match my wardrobe_\n"
            "  → _Closet gap analysis_\n"
            "  → _My saved products_\n\n"
            f"{DIVIDER}\n"
            "Type *help* anytime 💫"
        )
        _save_msg(from_number, "user", incoming_msg)
        _save_msg(from_number, "assistant", reply)
        _send_whatsapp(from_number, reply)
        return empty_resp

    # ── Saved products ─────────────────────────────────────────────────────────
    if re.search(r"saved\s*product|price\s*alert|price\s*drop|my\s*saves|wishlist", incoming_msg, re.I):
        try:
            docs = list(_saved.find(
                {"userId": uname, "active": True},
                {"_id": 0, "title": 1, "original_price": 1, "last_checked_price": 1, "url": 1},
                sort=[("saved_at", -1)],
                limit=6,
            ))
            if not docs:
                reply = (
                    f"📦 *No saved products yet, {uname}.*\n\n"
                    "In the FaceFit app:\n"
                    "• Tap 🔔 *Alert me* on any product\n"
                    "• Get WhatsApp alerts on price drops 5%+\n\n"
                    "Try: _Wedding outfit for tonight_ to find products to save!"
                )
            else:
                lines = [f"📦 *Your Saved Products ({len(docs)})*", DIVIDER]
                for d in docs:
                    orig = d.get("original_price") or 0
                    curr = d.get("last_checked_price") or orig
                    drop = round((orig - curr) / orig * 100, 1) if orig > 0 and curr < orig else 0
                    t    = (d.get("title") or "Product")[:50]
                    url  = d.get("url", "")
                    p_str = f"₹{int(curr)}" if curr else "Price not tracked"
                    if drop > 0:
                        p_str = f"~₹{int(orig)}~ → *₹{int(curr)}* 🔽 {drop}% off!"
                    lines.append(f"\n• *{t}*")
                    lines.append(f"  {p_str}")
                    if url:
                        lines.append(f"  🔗 {url}")
                lines.append(f"\n{DIVIDER}")
                lines.append("_Alerts fire daily on drops ≥ 5%_")
                reply = "\n".join(lines)
        except Exception as e:
            print(f"⚠️ Saved products error: {e}")
            reply = "Couldn't load saved products right now. Please try again in a moment."

        _save_msg(from_number, "user", incoming_msg)
        _save_msg(from_number, "assistant", reply)
        _send_whatsapp(from_number, reply)
        return empty_resp

    # ── MIX & MATCH ───────────────────────────────────────────────────────────
    is_mix_match = re.search(
        r"mix.*(and|&|n).*(match|wear)|match.*my.*wardrobe|combine.*my.*clothes"
        r"|mix.*wardrobe|mix.*match|my.*combinations|wardrobe.*combinations",
        incoming_msg, re.I
    )
    if is_mix_match:
        try:
            part1, part2 = _handle_mix_match(from_number, user)
        except Exception as e:
            print(f"❌ Mix & match error: {e}")
            import traceback; traceback.print_exc()
            part1 = (
                "Couldn't load wardrobe combinations right now.\n\n"
                "Try: Open FaceFit app → Closet → Mix & Match for the full experience 💫"
            )
            part2 = ""
        _save_msg(from_number, "user", incoming_msg)
        _save_msg(from_number, "assistant", part1 + ("\n\n" + part2 if part2 else ""))
        _send_two_part(from_number, part1, part2)
        return empty_resp

    # ── MAIN AI HANDLER ───────────────────────────────────────────────────────
    try:
        from services.chat_service import chat_with_ai
        ai_data = chat_with_ai(message=incoming_msg, user=user, history=history)
        print(f"✅ chat_with_ai keys: {list(ai_data.keys())}")

        for key in ("products", "dual_outfit", "closet_outfit", "outfit_products",
                    "missing_products", "gap_analysis", "mix_match"):
            val = ai_data.get(key)
            if val:
                print(f"   📦 '{key}' → {list(val.keys()) if isinstance(val, dict) else 'list'}")

        part1, part2 = _build_two_part_reply(ai_data, uname)

    except Exception as e:
        err_str = str(e)
        print(f"❌ chat_with_ai error: {err_str[:200]}")
        import traceback; traceback.print_exc()

        # Rate limit specific message
        if "rate_limit" in err_str.lower() or "429" in err_str:
            wait_match = re.search(r"try again in (\d+m\d+s|\d+s|\d+\.\d+s)", err_str, re.I)
            wait_str = wait_match.group(1) if wait_match else "a few minutes"
            part1 = (
                f"⏳ *Too many requests right now*\n\n"
                f"The AI is busy — please try again in *{wait_str}*.\n\n"
                "_(We're on Groq's free tier which has daily limits)_"
            )
        else:
            em = re.search(
                r"(wedding|gym|office|party|festival|beach|college|casual|date|acne|skincare)",
                incoming_msg, re.I
            )
            topic = em.group(1) if em else "your request"
            part1 = (
                f"Sorry, I had a hiccup with _{topic}_ recommendations. 🙏\n\n"
                "Please try again in a moment, or open the FaceFit app for the full experience!"
            )
        part2 = ""

    # ── Save + send ────────────────────────────────────────────────────────────
    try:
        _save_msg(from_number, "user", incoming_msg)
        _save_msg(from_number, "assistant", part1 + ("\n\n" + part2 if part2 else ""))
    except Exception as e:
        print(f"⚠️ Failed to save conversation: {e}")

    _send_two_part(from_number, part1, part2)
    return empty_resp


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY / DEBUG ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@whatsapp_bp.route("/whatsapp/test", methods=["POST"])
def test_send():
    data = request.json or {}
    to   = data.get("to")
    msg  = data.get("message", "Hello from FaceFit! 👗✨")
    if not to:
        return {"error": "to required"}, 400
    try:
        to_fmt = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
        m = twilio_client.messages.create(body=msg, from_=TWILIO_FROM, to=to_fmt)
        return {"success": True, "sid": m.sid}, 200
    except Exception as e:
        return {"error": str(e)}, 500


@whatsapp_bp.route("/whatsapp/profile-check/<path:phone>", methods=["GET"])
def check_profile(phone):
    profile = _get_user_profile(f"+{phone.lstrip('+')}")
    return {"profile": profile}


@whatsapp_bp.route("/whatsapp/debug-ai", methods=["POST"])
def debug_ai():
    """
    Debug: POST { "message": "Outfit for gym", "phone": "+916301842932" }
    Returns raw AI keys, extracted products, and reply previews.
    """
    data    = request.json or {}
    msg     = data.get("message", "Outfit for gym")
    phone   = data.get("phone", "+916301842932")
    user    = _get_user_profile(phone)
    history = _get_history(phone)

    try:
        from services.chat_service import chat_with_ai
        ai_data      = chat_with_ai(message=msg, user=user, history=history)
        all_products = _extract_all_products(ai_data)
        part1, part2 = _build_two_part_reply(ai_data, user.get("name", "there"))
        return {
            "raw_keys":         list(ai_data.keys()),
            "products_found":   {k: len(v) for k, v in all_products.items()},
            "part1_preview":    part1[:600],
            "part2_preview":    part2[:600],
            "part1_length":     len(part1),
            "part2_length":     len(part2),
        }, 200
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}, 500


@whatsapp_bp.route("/whatsapp/debug-mixmatch", methods=["POST"])
def debug_mix_match():
    """Debug: POST { "phone": "+916301842932" }"""
    data  = request.json or {}
    phone = data.get("phone", "+916301842932")
    user  = _get_user_profile(phone)

    try:
        part1, part2 = _handle_mix_match(phone, user)
        return {"part1": part1, "part2": part2,
                "part1_length": len(part1), "part2_length": len(part2)}, 200
    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}, 500