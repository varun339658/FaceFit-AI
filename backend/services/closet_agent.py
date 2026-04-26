"""
closet_agent.py — SMART WARDROBE AI v6
════════════════════════════════════════
FIXES in v6:
  1. STRICT event-based item filtering — gym items NEVER in festival/office/etc
  2. Ethnic items ALWAYS preferred for ethnic events (wedding, festival, puja)
  3. Athletic-only items (gym shorts, track pants) filtered OUT for non-gym events
  4. Per-user data isolation guaranteed (all queries scoped to user_id)
  5. Plan/mix_and_match: AI prompt enforced with hard event rules
"""

import os
import uuid
import base64
import requests
import json
import re
import cv2
import numpy as np
from datetime import datetime
from pymongo import MongoClient
from itertools import product as iterproduct

# ── DB ─────────────────────────────────────────────────────────────────────────
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority"
)
client = MongoClient(MONGO_URI)
db = client["facefit_ai"]
closet_collection = db["wardrobe"]

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

SERPER_KEYS = [
    os.getenv("SERPER_API_KEY_1", "b2c52277a6602960e38a074ff603f8335f7ec83f"),
    os.getenv("SERPER_API_KEY_2", "f6110be0a8db43231ccb3d7760579ba5a01132aa"),
]

# ── Category mapping ──────────────────────────────────────────────────────────
CLOSET_CATEGORIES = {
    "shirt":       ["shirt","tshirt","t-shirt","polo","blouse","top","kurti","kurta","hoodie","jacket","sweater","blazer"],
    "pants":       ["pant","trouser","jeans","leggings","skirt","shorts","palazzo","salwar","dhoti","cargo","chino"],
    "shoes":       ["shoe","sneaker","sandal","heel","boot","slipper","loafer","flat","chappal","jutti","kolhapuri"],
    "accessories": ["watch","bag","handbag","belt","scarf","hat","cap","sunglasses","jewellery","necklace","earring","bracelet","ring"],
    "ethnic":      ["saree","sari","sherwani","lehenga","dupatta","anarkali","kurta set","salwar kameez"],
    "dress":       ["dress","gown","jumpsuit","co-ord","suit","romper"],
}

# ── Keywords that mark an item as ATHLETIC/GYM-ONLY ──────────────────────────
ATHLETIC_ITEM_KEYWORDS = [
    "track pant", "track pants", "jogger", "sweatpant", "compression",
    "gym short", "gym shorts", "athletic short", "sport short",
    "dri-fit", "dry fit", "moisture-wicking", "workout pant",
    "cycling short", "legging gym", "yoga pant",
]

# ── Keywords that mark an item as ETHNIC ─────────────────────────────────────
ETHNIC_ITEM_KEYWORDS = [
    "kurta", "kurti", "sherwani", "lehenga", "saree", "sari", "dupatta",
    "anarkali", "salwar", "ethnic", "traditional", "festive", "nehru",
    "bandhgala", "churidar", "dhoti kurta", "patiala",
]

# ── Events where ethnic is REQUIRED (non-athletic items only) ─────────────────
ETHNIC_EVENTS = {"wedding","sangeet","mehndi","haldi","reception","engagement","puja","festival"}
ATHLETIC_EVENTS = {"gym", "beach", "cricket", "football", "running", "sport"}

# ── 20+ Event definitions ──────────────────────────────────────────────────────
EVENT_REQUIREMENTS = {
    "wedding":    {
        "cats":["ethnic","dress","shoes","accessories"],
        "required_style": "ethnic_or_formal",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS,
        "prefer_ethnic": True,
        "search_cats":{"ethnic":"kurta sherwani lehenga saree wedding Indian festive","dress":"party dress gown wedding","shoes":"ethnic wedding footwear kolhapuri mojri heels","accessories":"gold jewellery watches ethnic accessories wedding"},
        "vibe":"elegant, festive, traditional or indo-western","formality":"formal","icon":"💍"},
    "sangeet":    {
        "cats":["ethnic","dress","shoes","accessories"],
        "required_style": "ethnic_or_formal",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS,
        "prefer_ethnic": True,
        "search_cats":{"ethnic":"sangeet outfit kurta lehenga bollywood colors","dress":"sangeet party dress vibrant","shoes":"dance-friendly footwear sangeet heels sandals","accessories":"bold earrings bangles jewellery sangeet"},
        "vibe":"vibrant, dancing-ready, bold colors","formality":"semi-formal","icon":"🎶"},
    "mehndi":     {
        "cats":["ethnic","dress","shoes","accessories"],
        "required_style": "ethnic",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS,
        "prefer_ethnic": True,
        "search_cats":{"ethnic":"mehndi outfit yellow green pink kurti lehenga","dress":"mehndi ceremony dress","shoes":"comfortable ethnic sandals mehndi","accessories":"floral jewellery mehndi look"},
        "vibe":"yellow, green, pink — traditional haldi colors","formality":"casual","icon":"🌿"},
    "haldi":      {
        "cats":["ethnic","dress","shoes","accessories"],
        "required_style": "ethnic",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS,
        "prefer_ethnic": True,
        "search_cats":{"ethnic":"haldi ceremony yellow turmeric outfit kurta","dress":"haldi yellow outfit","shoes":"flat sandals ethnic haldi","accessories":"floral garland jewellery"},
        "vibe":"yellow, orange, turmeric tones","formality":"casual","icon":"🌼"},
    "reception":  {
        "cats":["ethnic","dress","shoes","accessories"],
        "required_style": "ethnic_or_formal",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS,
        "prefer_ethnic": True,
        "search_cats":{"ethnic":"reception sherwani indo-western men lehenga saree women formal","dress":"formal gown reception evening dress","shoes":"formal ethnic footwear reception heels","accessories":"premium jewellery statement accessories reception"},
        "vibe":"most formal — indo-western or sherwani/lehenga","formality":"formal","icon":"✨"},
    "engagement": {
        "cats":["ethnic","dress","shoes","accessories"],
        "required_style": "ethnic_or_formal",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS,
        "prefer_ethnic": True,
        "search_cats":{"ethnic":"engagement outfit pastel kurta lehenga Indo-western","dress":"engagement party dress romantic","shoes":"heels sandals engagement ceremony","accessories":"elegant jewellery engagement look"},
        "vibe":"romantic, elegant, pastel or jewel tones","formality":"semi-formal","icon":"💌"},
    "puja":       {
        "cats":["ethnic","shirt","pants","shoes"],
        "required_style": "ethnic",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS,
        "prefer_ethnic": True,
        "search_cats":{"ethnic":"puja kurta cotton silk traditional Indian","shirt":"simple kurta puja","pants":"churidar pajama cotton puja","shoes":"kolhapuri mojri ethnic sandals puja"},
        "vibe":"traditional, modest, pure cotton or silk","formality":"semi-formal","icon":"🪔"},
    "festival":   {
        "cats":["ethnic","shirt","pants","shoes","accessories"],
        "required_style": "ethnic_preferred",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS,
        "prefer_ethnic": True,
        "search_cats":{"ethnic":"festival kurta sherwani ethnic colorful India","shirt":"festive shirt kurta bright colors","pants":"festive churidar dhoti pants","shoes":"kolhapuri juttis ethnic sandals festival","accessories":"gold jewellery ethnic accessories festival"},
        "vibe":"colorful, celebratory, traditional","formality":"semi-formal","icon":"🎉"},
    "office":     {
        "cats":["shirt","pants","shoes"],
        "required_style": "formal",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS,
        "search_cats":{"shirt":"formal office shirt men women India","pants":"formal trousers office wear slim fit","shoes":"leather office shoes loafers formal"},
        "vibe":"professional, clean, polished","formality":"formal","icon":"💼"},
    "interview":  {
        "cats":["shirt","pants","shoes","accessories"],
        "required_style": "formal",
        "forbidden_in_wardrobe": ATHLETIC_ITEM_KEYWORDS + ["kurta","ethnic"],
        "search_cats":{"shirt":"formal interview shirt white light blue","pants":"formal slim trousers interview","shoes":"formal leather derby shoes interview","accessories":"minimal watch professional accessories"},
        "vibe":"sharp, professional, minimal accessories","formality":"formal","icon":"🎯"},
    "school":     {
        "cats":["shirt","pants","shoes"],
        "search_cats":{"shirt":"casual school t-shirt polo","pants":"school comfortable jeans trousers","shoes":"white canvas school shoes sneakers"},
        "vibe":"neat, comfortable, age-appropriate","formality":"casual","icon":"📚"},
    "college":    {
        "cats":["shirt","pants","shoes","accessories"],
        "search_cats":{"shirt":"college casual t-shirt oversized streetwear","pants":"jeans cargo pants college casual","shoes":"white sneakers chunky college","accessories":"cap sunglasses bracelet college"},
        "vibe":"trendy, comfortable, streetwear or casual chic","formality":"casual","icon":"🎓"},
    "farewell":   {
        "cats":["shirt","pants","shoes","accessories"],
        "search_cats":{"shirt":"smart casual farewell shirt blazer","pants":"slim fit trousers farewell party","shoes":"loafers smart casual farewell shoes","accessories":"watch bracelet farewell accessories"},
        "vibe":"stylish, memorable, smart casual","formality":"semi-formal","icon":"🎊"},
    "party":      {
        "cats":["shirt","pants","shoes","accessories"],
        "search_cats":{"shirt":"party shirt bold print night out","pants":"slim fit party trousers dark","shoes":"leather boots party night shoes","accessories":"statement watch bracelet party"},
        "vibe":"bold, trendy, night-ready","formality":"semi-formal","icon":"🎊"},
    "date":       {
        "cats":["shirt","pants","shoes","accessories"],
        "search_cats":{"shirt":"date night smart casual shirt charming","pants":"slim chino trousers date night","shoes":"clean loafers white leather date shoes","accessories":"elegant watch minimal bracelet date"},
        "vibe":"stylish, put-together, charming","formality":"semi-formal","icon":"🌹"},
    "dinner":     {
        "cats":["shirt","pants","shoes","accessories"],
        "search_cats":{"shirt":"smart casual dinner shirt restaurant","pants":"slim fit dinner trousers chino","shoes":"loafers leather shoes dinner restaurant","accessories":"watch necklace dinner accessories"},
        "vibe":"smart casual to semi-formal","formality":"semi-formal","icon":"🍽️"},
    "club":       {
        "cats":["shirt","pants","shoes","accessories"],
        "search_cats":{"shirt":"nightclub outfit bold dark shirt","pants":"slim fit club dark trousers","shoes":"leather boots club shoes","accessories":"chain bracelet sunglasses club night"},
        "vibe":"edgy, bold, night-ready, dark tones","formality":"semi-formal","icon":"🌙"},
    "concert":    {
        "cats":["shirt","pants","shoes","accessories"],
        "search_cats":{"shirt":"concert graphic t-shirt band tee streetwear","pants":"cargo jogger concert outfit","shoes":"chunky sneakers concert shoes","accessories":"cap bucket hat sunglasses concert"},
        "vibe":"cool, expressive, streetwear","formality":"casual","icon":"🎸"},
    "brunch":     {
        "cats":["shirt","pants","shoes","accessories"],
        "search_cats":{"shirt":"brunch casual chic top blouse pastel","pants":"wide leg trousers linen brunch","shoes":"white sneakers block heels brunch","accessories":"sunglasses bag brunch accessories"},
        "vibe":"smart casual, pastel, fresh","formality":"casual","icon":"☕"},
    "shopping":   {
        "cats":["shirt","pants","shoes"],
        "search_cats":{"shirt":"comfortable casual t-shirt shopping day","pants":"comfortable jeans cargo shopping","shoes":"comfortable sneakers walking shopping"},
        "vibe":"comfortable, casual, trendy","formality":"casual","icon":"🛍️"},
    "gym":        {
        "cats":["gym_tshirt","track_pants","sports_shoes"],
        "is_athletic": True,
        "required_style": "athletic",
        "forbidden_in_wardrobe": ETHNIC_ITEM_KEYWORDS,
        "search_cats":{
            "gym_tshirt":    "dry fit gym t-shirt athletic performance men women India",
            "track_pants":   "track pants jogger gym athletic training men women India",
            "sports_shoes":  "running shoes gym training shoes athletic India",
        },
        "vibe":"athletic, performance, comfortable and sporty","formality":"casual","icon":"💪"},
    "beach":      {
        "cats":["beach_shirt","swim_shorts","flip_flops"],
        "is_athletic": True,
        "required_style": "beach",
        "search_cats":{
            "beach_shirt":   "linen beach shirt floral relaxed fit men women India summer",
            "swim_shorts":   "swim shorts beach shorts men women India summer",
            "flip_flops":    "flip flops beach sandals summer comfortable India",
        },
        "vibe":"light, breathable, summer beach vibes","formality":"casual","icon":"🏖️"},
    "travel":     {
        "cats":["shirt","pants","shoes","accessories"],
        "search_cats":{"shirt":"comfortable travel shirt light breathable","pants":"comfortable travel pants jogger chino","shoes":"comfortable walking sneakers travel","accessories":"travel bag cap sunglasses"},
        "vibe":"comfortable, versatile, layered","formality":"casual","icon":"✈️"},
    "cricket": {
        "cats": ["gym_tshirt", "track_pants", "sports_shoes"],
        "is_athletic": True,
        "required_style": "athletic",
        "forbidden_in_wardrobe": [],
        "search_cats": {
            "gym_tshirt":   "cricket jersey dry fit sport t-shirt men India",
            "track_pants":  "cricket whites track pants sports trousers men India",
            "sports_shoes": "cricket shoes sport rubber sole men India",
        },
        "vibe": "athletic, sporty, performance-ready for cricket",
        "formality": "casual", "icon": "🏏",
    },
    "football": {
        "cats": ["gym_tshirt", "track_pants", "sports_shoes"],
        "is_athletic": True,
        "required_style": "athletic",
        "forbidden_in_wardrobe": [],
        "search_cats": {
            "gym_tshirt":   "football jersey dry fit sport t-shirt men India",
            "track_pants":  "football shorts track pants sport men India",
            "sports_shoes": "football shoes sport training men India",
        },
        "vibe": "athletic, sporty, performance-ready",
        "formality": "casual", "icon": "⚽",
    },
    "running": {
        "cats": ["gym_tshirt", "track_pants", "sports_shoes"],
        "is_athletic": True,
        "required_style": "athletic",
        "forbidden_in_wardrobe": [],
        "search_cats": {
            "gym_tshirt":   "running t-shirt dry fit lightweight men India",
            "track_pants":  "running shorts track pants lightweight men India",
            "sports_shoes": "running shoes lightweight cushioned men India",
        },
        "vibe": "lightweight, performance, running-ready",
        "formality": "casual", "icon": "🏃",
    },
    "sport": {
        "cats": ["gym_tshirt", "track_pants", "sports_shoes"],
        "is_athletic": True,
        "required_style": "athletic",
        "forbidden_in_wardrobe": [],
        "search_cats": {
            "gym_tshirt":   "sports t-shirt dry fit athletic performance men India",
            "track_pants":  "sports track pants athletic training men India",
            "sports_shoes": "sports shoes athletic training men India",
        },
        "vibe": "athletic, sporty, performance-ready",
        "formality": "casual", "icon": "🏅",
    },
    "casual":     {
        "cats":["shirt","pants","shoes"],
        "search_cats":{"shirt":"casual everyday t-shirt comfortable","pants":"casual jeans everyday comfortable","shoes":"everyday sneakers casual comfortable"},
        "vibe":"comfortable, everyday, relaxed","formality":"casual","icon":"😊"},
}


# ── Item classification helpers ───────────────────────────────────────────────

def _is_athletic_item(item: dict) -> bool:
    """Returns True if this item is gym/athletic-only wear."""
    text = " ".join([
        item.get("item_name", ""),
        item.get("style", ""),
        item.get("category", ""),
        " ".join(item.get("occasion", [])),
    ]).lower()
    return any(kw in text for kw in ATHLETIC_ITEM_KEYWORDS)


def _is_ethnic_item(item: dict) -> bool:
    """Returns True if this item is ethnic/traditional wear."""
    text = " ".join([
        item.get("item_name", ""),
        item.get("style", ""),
        item.get("category", ""),
        " ".join(item.get("occasion", [])),
    ]).lower()
    return any(kw in text for kw in ETHNIC_ITEM_KEYWORDS)


def _item_is_appropriate_for_event(item: dict, event_type: str) -> bool:
    """
    KEY FUNCTION: Determines if a wardrobe item is appropriate for the event.
    
    Rules:
    - Gym/athletic items ONLY for gym events
    - Ethnic items PREFERRED (not forbidden) for ethnic events
    - Ethnic items ALLOWED in casual/college but not preferred
    - Athletic items FORBIDDEN in all non-gym events
    """
    is_athletic = _is_athletic_item(item)
    is_ethnic = _is_ethnic_item(item)
    ev_info = EVENT_REQUIREMENTS.get(event_type, {})
    
    # Athletic items: ONLY allowed at gym
    if is_athletic and event_type not in ATHLETIC_EVENTS:
        return False
    
    # Ethnic items: not for gym
    if is_ethnic and event_type == "gym":
        return False
    
    # Additional forbidden keywords from event config
    forbidden = ev_info.get("forbidden_in_wardrobe", [])
    if forbidden:
        text = " ".join([
            item.get("item_name", ""),
            item.get("style", ""),
        ]).lower()
        if any(kw in text for kw in forbidden):
            return False
    
    return True


# ── Color Compatibility Matrix ─────────────────────────────────────────────────
COLOR_PAIRS = {
    ("white","black"):3,("black","white"):3,
    ("white","navy blue"):3,("navy blue","white"):3,
    ("white","beige"):3,("beige","white"):3,
    ("white","blue"):3,("blue","white"):3,
    ("cream","navy blue"):3,("navy blue","cream"):3,
    ("cream","brown"):3,("brown","cream"):3,
    ("cream","camel"):3,("camel","cream"):3,
    ("beige","brown"):3,("brown","beige"):3,
    ("beige","navy blue"):3,("navy blue","beige"):3,
    ("khaki","navy blue"):3,("navy blue","khaki"):3,
    ("khaki","olive"):2,("olive","khaki"):2,
    ("black","red"):3,("red","black"):3,
    ("black","grey"):3,("grey","black"):3,
    ("black","navy blue"):2,("navy blue","black"):2,
    ("mustard","black"):3,("black","mustard"):3,
    ("mustard","brown"):3,("brown","mustard"):3,
    ("mustard","navy blue"):3,("navy blue","mustard"):3,
    ("mustard","white"):3,("white","mustard"):3,
    ("olive","camel"):3,("camel","olive"):3,
    ("olive","cream"):3,("cream","olive"):3,
    ("olive","brown"):2,("brown","olive"):2,
    ("burgundy","beige"):3,("beige","burgundy"):3,
    ("burgundy","cream"):3,("cream","burgundy"):3,
    ("burgundy","grey"):3,("grey","burgundy"):3,
    ("maroon","beige"):3,("beige","maroon"):3,
    ("maroon","cream"):3,("cream","maroon"):3,
    ("teal","white"):3,("white","teal"):3,
    ("teal","cream"):3,("cream","teal"):3,
    ("teal","beige"):3,("beige","teal"):3,
    ("blue","grey"):3,("grey","blue"):3,
    ("blue","beige"):3,("beige","blue"):3,
    ("navy blue","grey"):3,("grey","navy blue"):3,
    ("royal blue","cream"):3,("cream","royal blue"):3,
    ("electric blue","black"):3,("black","electric blue"):3,
    ("emerald","black"):3,("black","emerald"):3,
    ("emerald","cream"):3,("cream","emerald"):3,
    ("forest green","khaki"):3,("khaki","forest green"):3,
    ("forest green","camel"):3,("camel","forest green"):3,
    ("orange","white"):3,("white","orange"):3,
    ("orange","navy blue"):3,("navy blue","orange"):3,
    ("coral","white"):3,("white","coral"):3,
    ("coral","navy blue"):3,("navy blue","coral"):3,
    ("pink","grey"):3,("grey","pink"):3,
    ("pink","white"):3,("white","pink"):3,
    ("pink","navy blue"):3,("navy blue","pink"):3,
    ("lavender","white"):3,("white","lavender"):3,
    ("lavender","grey"):3,("grey","lavender"):3,
    ("purple","black"):3,("black","purple"):3,
    ("purple","grey"):2,("grey","purple"):2,
    ("grey","white"):3,("white","grey"):3,
    ("grey","beige"):2,("beige","grey"):2,
    ("camel","white"):3,("white","camel"):3,
    ("saffron","white"):3,("white","saffron"):3,
    ("saffron","cream"):3,("cream","saffron"):3,
    ("yellow","white"):3,("white","yellow"):3,
    ("yellow","navy blue"):3,("navy blue","yellow"):3,
    ("rust","beige"):3,("beige","rust"):3,
    ("rust","cream"):3,("cream","rust"):3,
    ("terracotta","white"):3,("white","terracotta"):3,
    ("terracotta","beige"):3,("beige","terracotta"):3,
}


def _color_pair_score(c1: str, c2: str) -> int:
    c1, c2 = c1.lower().strip(), c2.lower().strip()
    if c1 == c2:
        return 1
    direct = COLOR_PAIRS.get((c1, c2)) or COLOR_PAIRS.get((c2, c1))
    if direct is not None:
        return direct
    for (a, b), score in COLOR_PAIRS.items():
        if (a in c1 or c1 in a) and (b in c2 or c2 in b):
            return score
        if (a in c2 or c2 in a) and (b in c1 or c1 in b):
            return score
    return 1


def _color_pair_label(score: int) -> str:
    return {3: "✦ Perfect match", 2: "Good combo", 1: "Wearable"}.get(score, "Neutral")


# ── CV2 COLOR + SMART CATEGORY DETECTION ─────────────────────────────────────

def _get_dominant_color(image_path: str) -> str:
    try:
        img = cv2.imread(image_path)
        if img is None: return "unknown"
        img = cv2.resize(img, (150, 150))
        h, w = img.shape[:2]
        center = img[h//6:5*h//6, w//6:5*w//6]
        hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
        pixels = hsv.reshape(-1, 3).astype(np.float32)
        avg_h = np.median(pixels[:, 0])
        avg_s = np.median(pixels[:, 1])
        avg_v = np.median(pixels[:, 2])
        if avg_v < 40: return "black"
        if avg_v > 200 and avg_s < 30: return "white"
        if avg_s < 30: return "grey"
        if avg_h < 10 or avg_h > 165: return "red" if avg_s > 60 else "maroon"
        if 10 <= avg_h < 25: return "orange" if avg_s > 80 else "brown"
        if 25 <= avg_h < 38: return "yellow"
        if 38 <= avg_h < 85: return "dark green" if avg_v < 80 else "green"
        if 85 <= avg_h < 105: return "teal"
        if 105 <= avg_h < 130: return "navy blue" if avg_v < 80 else "blue"
        if 130 <= avg_h < 160: return "purple"
        if 160 <= avg_h < 175: return "pink"
        return "mixed"
    except Exception as e:
        print(f"⚠️ Color error: {e}")
        return "unknown"


def _smart_category_from_image(image_path: str) -> str:
    try:
        img = cv2.imread(image_path)
        if img is None: return "shirt"
        orig_h, orig_w = img.shape[:2]
        img_ratio = orig_h / orig_w
        img_small = cv2.resize(img, (200, 200))
        hsv = cv2.cvtColor(img_small, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        s_channel = hsv[:, :, 1]
        not_white_bg = v_channel < 230
        not_black_bg = v_channel > 20
        has_color = s_channel > 20
        fg_mask = ((not_white_bg & not_black_bg) | has_color).astype(np.uint8) * 255
        kernel = np.ones((5, 5), np.uint8)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return "shoes" if img_ratio < 0.65 else ("pants" if img_ratio > 1.3 else "shirt")
        main_contour = max(contours, key=cv2.contourArea)
        x, y, cw, ch = cv2.boundingRect(main_contour)
        garment_ratio = ch / max(cw, 1)
        garment_top_pct = y / 200
        if garment_ratio < 0.6 and garment_top_pct > 0.4: return "shoes"
        if img_ratio < 0.65: return "shoes"
        pants_score = 0
        if garment_ratio > 1.4: pants_score += 2
        lower_half = fg_mask[100:, :]
        upper_half = fg_mask[:100, :]
        lower_fill = np.sum(lower_half > 0)
        upper_fill = np.sum(upper_half > 0)
        if lower_fill > 0 and upper_fill > 0:
            if lower_fill / upper_fill > 0.85: pants_score += 1
        top_center = fg_mask[:60, 70:130]
        top_center_fill = np.sum(top_center > 0) / (60 * 60)
        if top_center_fill < 0.3: pants_score += 1
        if pants_score >= 2: return "pants"
        return "shirt"
    except Exception as e:
        print(f"⚠️ Smart category error: {e}")
        return "shirt"


# ── GROQ VISION DETECTION ────────────────────────────────────────────────────

def _img_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _parse_detection_json(text: str) -> dict | None:
    text = re.sub(r"```json|```", "", text).strip()
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
    return None


def _validate_detection(data: dict) -> bool:
    if not data: return False
    cat = data.get("category", "")
    color = data.get("color", "").lower()
    name = data.get("item_name", "").lower()
    if cat not in ("shirt","pants","shoes","accessories","ethnic","dress"): return False
    if color in ("unknown","","none"): return False
    if name in ("clothing item","item","","unknown"): return False
    return True


DETECTION_PROMPT = """You are a clothing recognition AI for a wardrobe app.
Analyze the image and identify the clothing item.

Return ONLY a JSON object — no explanation, no markdown:
{
  "category": "pants",
  "item_name": "black slim fit trousers",
  "color": "black",
  "style": "slim fit formal trousers",
  "formality": "casual",
  "gender": "male",
  "occasion": ["casual", "office"]
}

CATEGORY — choose EXACTLY ONE:
- "shirt"       → t-shirt, polo, button shirt, kurta, blouse, hoodie, jacket, sweater (upper body)
- "pants"       → jeans, trousers, chinos, shorts, leggings, skirt, palazzo (lower body)
- "shoes"       → sneakers, sandals, heels, boots, loafers (footwear)
- "accessories" → watch, bag, belt, hat, sunglasses, jewelry
- "ethnic"      → saree, sherwani, lehenga (full traditional outfit)
- "dress"       → dress, gown, jumpsuit (one-piece full body)

FORMALITY — choose ONE: "casual", "semi-formal", "formal"
OCCASION — list from: ["casual","office","party","wedding","date","college","gym","beach","festival","travel"]

IMPORTANT:
- Black pants/jeans/trousers = "pants" NOT "shirt"
- T-shirt/polo/shirt = "shirt" NOT "pants"
- Color must be specific: "black", "navy blue", "dark green", "off white", "maroon"
- item_name must be descriptive: "black slim fit jeans" not "clothing item"
- Gym shorts/track pants = "pants" + occasion: ["gym"]
- Ethnic kurta = "shirt" + occasion: ["festival", "wedding", "casual"]

Output ONLY the JSON."""

GROQ_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]


def _groq_detect_clothing(image_path: str) -> dict | None:
    if not GROQ_API_KEY: return None
    b64 = _img_to_base64(image_path)
    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type = f"image/{ext}" if ext in ("jpg","jpeg","png","webp") else "image/jpeg"

    for model in GROQ_VISION_MODELS:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role":"user","content":[
                        {"type":"image_url","image_url":{"url":f"data:{media_type};base64,{b64}"}},
                        {"type":"text","text":DETECTION_PROMPT}
                    ]}],
                    "max_tokens": 300, "temperature": 0.1,
                },
                timeout=25
            )
            if resp.status_code == 400:
                err = resp.json().get("error",{}).get("message","")
                if any(w in err.lower() for w in ["decommissioned","deprecated","not supported"]):
                    continue
                continue
            if resp.status_code != 200:
                continue
            raw = resp.json()["choices"][0]["message"]["content"]
            data = _parse_detection_json(raw)
            if _validate_detection(data):
                print(f"✅ Groq [{model}]: {data['color']} {data['item_name']} ({data['category']})")
                return data
        except Exception as e:
            print(f"⚠️ Groq [{model}]: {e}")
    return None


def _cv2_detect_clothing(image_path: str) -> dict:
    color = _get_dominant_color(image_path)
    category = _smart_category_from_image(image_path)
    cat_display = {"shirt":"t-shirt","pants":"trousers","shoes":"shoes","accessories":"accessory","ethnic":"ethnic wear","dress":"dress"}
    item_name = f"{color} {cat_display.get(category,'clothing item')}"
    return {
        "category": category, "item_name": item_name, "color": color,
        "style": f"{color} {category}", "formality": "casual",
        "gender": "unisex", "occasion": ["casual","everyday"],
    }


def _detect_clothing(image_path: str) -> dict:
    result = _groq_detect_clothing(image_path)
    return result if result else _cv2_detect_clothing(image_path)


# ── CLOSET CRUD ──────────────────────────────────────────────────────────────

def _serialize_item(item: dict) -> dict:
    """Convert MongoDB document to JSON-safe dict."""
    item = dict(item)
    item.pop("_id", None)
    for key, val in item.items():
        if isinstance(val, datetime):
            item[key] = val.isoformat()
    return item


def add_to_closet(user_id: str, image_path: str, image_url: str = None) -> dict:
    detection = _detect_clothing(image_path)
    item = {
        "user_id":   user_id,
        "item_id":   uuid.uuid4().hex,
        "category":  detection.get("category","shirt"),
        "item_name": detection.get("item_name","clothing item"),
        "color":     detection.get("color","unknown"),
        "style":     detection.get("style",""),
        "formality": detection.get("formality","casual"),
        "gender":    detection.get("gender","unisex"),
        "occasion":  detection.get("occasion",["casual"]),
        "image_url": image_url or "",
        "added_at":  datetime.utcnow(),
    }
    closet_collection.insert_one(item)
    print(f"✅ Added: {item['color']} {item['item_name']} ({item['category']}) for user={user_id}")
    return _serialize_item(item)


def get_wardrobe(user_id: str) -> list:
    """Get wardrobe items SCOPED to this user only."""
    items = list(closet_collection.find({"user_id": user_id}, {"_id": 0}))
    return [_serialize_item(i) for i in items]


def delete_wardrobe_item(user_id: str, item_id: str) -> bool:
    # Scoped to user_id for security
    result = closet_collection.delete_one({"user_id": user_id, "item_id": item_id})
    return result.deleted_count > 0


# ── EVENT-FILTERED WARDROBE ───────────────────────────────────────────────────

def get_event_appropriate_wardrobe(user_id: str, event_type: str) -> list:
    """
    Returns only wardrobe items appropriate for the event.
    Filters out:
    - Athletic/gym items for non-gym events
    - Ethnic items for gym
    - Other forbidden items per event rules
    """
    all_items = get_wardrobe(user_id)
    filtered = [item for item in all_items if _item_is_appropriate_for_event(item, event_type)]
    removed = len(all_items) - len(filtered)
    if removed > 0:
        print(f"🔧 Event filter [{event_type}]: removed {removed} inappropriate items from {len(all_items)} total")
    return filtered


# ── MIX AND MATCH ENGINE v6 — EVENT-FILTERED ─────────────────────────────────

def _groq_generate_outfit_combos(wardrobe_items: list, skin_tone: str, event: str = None) -> list:
    """Use LLM to generate 4-6 styled outfit combos. Returns list of combos."""
    if not GROQ_API_KEY:
        return []

    wardrobe_desc = []
    for item in wardrobe_items:
        wardrobe_desc.append({
            "id": item.get("item_id",""),
            "name": item.get("item_name",""),
            "color": item.get("color",""),
            "category": item.get("category",""),
            "formality": item.get("formality","casual"),
        })

    event_ctx = f" for {event}" if event else ""
    ev_info = EVENT_REQUIREMENTS.get(event or "casual", {})
    ev_vibe = ev_info.get("vibe","everyday casual")
    prefer_ethnic = ev_info.get("prefer_ethnic", False)

    ethnic_instruction = ""
    if prefer_ethnic:
        ethnic_instruction = "PRIORITY: Always prefer kurta/ethnic/traditional items over casual shirts for this event. If ethnic items exist in wardrobe, they MUST be the primary top choice."

    prompt = f"""You are a world-class personal stylist creating outfit combinations from a wardrobe.

WARDROBE ITEMS (ALL ALREADY FILTERED FOR THIS EVENT — use ONLY these):
{json.dumps(wardrobe_desc, indent=2)}

CLIENT PROFILE:
- Skin tone: {skin_tone}
- Occasion: {event or "casual"}{event_ctx}
- Event vibe: {ev_vibe}

{ethnic_instruction}

TASK: Create 4-6 DISTINCT, well-styled outfit combinations from these EXACT wardrobe items.

RULES:
1. Use ONLY item IDs from the list above
2. Each outfit: 1 top + 1 bottom + 1 shoes (if available). NEVER 2 bottoms or 2 tops.
3. Rank outfits by color harmony and event suitability
4. Each outfit must be DIFFERENT — vary combinations

OUTPUT — ONLY valid JSON array, no markdown:
[
  {{
    "outfit_number": 1,
    "outfit_name": "Festival Ready Look",
    "item_ids": ["id1", "id2", "id3"],
    "color_harmony": "perfect",
    "tip": "Tuck the kurta slightly and add a gold watch for a regal festival look.",
    "why_it_works": "The saffron kurta glows against medium skin, especially at festival lighting."
  }}
]

Return 4-6 outfits. Each must use different primary items."""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],
                  "max_tokens":1500,"temperature":0.5},
            timeout=20
        )
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"]
            raw = re.sub(r"```json|```","",raw).strip()
            combos = json.loads(raw)
            if isinstance(combos, list):
                return combos
    except Exception as e:
        print(f"⚠️ LLM mix-match error: {e}")
    return []


def mix_and_match(user_id: str, skin_tone: str = "medium", event: str = None) -> dict:
    """
    Generate AI-powered outfit combinations from wardrobe.
    v6: Event-filtered wardrobe — gym items excluded from festival, etc.
    """
    # Get event-appropriate items only
    if event:
        wardrobe = get_event_appropriate_wardrobe(user_id, event)
        all_wardrobe = get_wardrobe(user_id)
    else:
        wardrobe = get_wardrobe(user_id)
        all_wardrobe = wardrobe

    if not wardrobe:
        msg = "Your closet is empty! Upload clothes first." if not all_wardrobe else \
              f"No {event}-appropriate clothes found in your wardrobe. You may need to shop for {event} attire!"
        return {"outfits": [], "combinations": [], "total": 0, "total_items": len(all_wardrobe),
                "message": msg}

    tops = [i for i in wardrobe if i["category"] in ("shirt","ethnic","dress")]
    bottoms = [i for i in wardrobe if i["category"] == "pants"]
    shoes_list = [i for i in wardrobe if i["category"] == "shoes"]
    accessories = [i for i in wardrobe if i["category"] == "accessories"]

    item_by_id = {i["item_id"]: i for i in wardrobe}

    # Try AI-powered combos first
    ai_combos_raw = _groq_generate_outfit_combos(wardrobe, skin_tone, event)

    outfits = []

    if ai_combos_raw:
        for raw_combo in ai_combos_raw:
            item_ids = raw_combo.get("item_ids", [])
            combo_items = [item_by_id[iid] for iid in item_ids if iid in item_by_id]

            combo_top    = next((i for i in combo_items if i["category"] in ("shirt","ethnic","dress")), None)
            combo_bottom = next((i for i in combo_items if i["category"] == "pants"), None)
            combo_shoes  = next((i for i in combo_items if i["category"] == "shoes"), None)
            combo_acc    = next((i for i in combo_items if i["category"] == "accessories"), None)

            # Dedup checks
            if combo_bottom and combo_shoes and combo_bottom.get("item_id") == combo_shoes.get("item_id"):
                combo_shoes = None

            pants_in_combo = [i for i in combo_items if i["category"] == "pants"]
            if len(pants_in_combo) > 1:
                combo_bottom = pants_in_combo[0]

            # Fallback shoe if none
            if not combo_shoes and shoes_list:
                ref_colors = [
                    combo_top.get("color","") if combo_top else "",
                    combo_bottom.get("color","") if combo_bottom else ""
                ]
                combo_shoes = max(
                    shoes_list,
                    key=lambda s: sum(_color_pair_score(s["color"], c) for c in ref_colors if c)
                )

            # Color score
            items_for_score = [i for i in [combo_top, combo_bottom, combo_shoes] if i]
            color_scores = []
            for i in range(len(items_for_score)):
                for j in range(i+1, len(items_for_score)):
                    c1 = items_for_score[i].get("color","")
                    c2 = items_for_score[j].get("color","")
                    if c1 and c2:
                        color_scores.append(_color_pair_score(c1, c2))
            avg_score = round(sum(color_scores)/len(color_scores)) if color_scores else 2

            harmony_label = raw_combo.get("color_harmony","")
            if harmony_label == "perfect": avg_score = 3
            elif harmony_label == "good": avg_score = max(avg_score, 2)

            items_dict = {}
            if combo_top:    items_dict["top"]         = combo_top
            if combo_bottom: items_dict["bottom"]      = combo_bottom
            if combo_shoes:  items_dict["shoes"]       = combo_shoes
            if combo_acc:    items_dict["accessories"] = combo_acc

            outfits.append({
                "items":        items_dict,
                "top":          combo_top,
                "bottom":       combo_bottom,
                "shoes":        combo_shoes,
                "color_score":  avg_score,
                "color_label":  _color_pair_label(avg_score),
                "combo_id":     uuid.uuid4().hex[:8],
                "outfit_name":  raw_combo.get("outfit_name","Styled Look"),
                "styling_tip":  raw_combo.get("tip","") or raw_combo.get("why_it_works",""),
                "event":        event,
            })

    # Algorithmic fallback if AI returned nothing
    if not outfits:
        print("⚠️ AI mix-match returned nothing, using algorithmic fallback")
        standalone  = [i for i in tops if i["category"] == "dress"]
        paired_tops = [i for i in tops if i["category"] != "dress"]

        def _versatility(item):
            neutral = ["black","white","grey","beige","navy","cream","camel"]
            return sum(1 for n in neutral if n in item.get("color","").lower())

        sorted_tops    = sorted(paired_tops, key=_versatility, reverse=True)
        sorted_bottoms = sorted(bottoms,     key=_versatility, reverse=True)

        for top in sorted_tops:
            best_bottom = None
            best_score  = -1
            for bottom in sorted_bottoms:
                s = _color_pair_score(top["color"], bottom["color"])
                if s > best_score:
                    best_score  = s
                    best_bottom = bottom
            if not best_bottom:
                continue

            best_shoe = None
            if shoes_list:
                best_shoe = max(shoes_list, key=lambda s: (
                    _color_pair_score(s["color"], top["color"]) +
                    _color_pair_score(s["color"], best_bottom["color"])
                ))

            items_dict = {"top": top, "bottom": best_bottom}
            if best_shoe: items_dict["shoes"] = best_shoe

            outfits.append({
                "items":       items_dict,
                "top":         top,
                "bottom":      best_bottom,
                "shoes":       best_shoe,
                "color_score": best_score,
                "color_label": _color_pair_label(best_score),
                "combo_id":    f"{top['item_id']}_{best_bottom['item_id']}",
                "outfit_name": f"{top['color'].title()} {top['item_name']} + {best_bottom['color'].title()} {best_bottom['item_name']}",
                "styling_tip": f"Pair your {top['color']} top with {best_bottom['color']} bottoms for a clean, balanced look.",
                "event":       event,
            })

        for dress in standalone:
            best_shoe = max(shoes_list, key=lambda s: _color_pair_score(s["color"], dress["color"])) if shoes_list else None
            items_dict = {"top": dress}
            if best_shoe: items_dict["shoes"] = best_shoe
            outfits.append({
                "items":       items_dict,
                "top":         dress, "bottom": None, "shoes": best_shoe,
                "color_score": 3, "color_label": "✦ Complete look",
                "combo_id":    dress["item_id"],
                "outfit_name": f"{dress['color'].title()} {dress['item_name']}",
                "styling_tip": f"This {dress['color']} dress is a complete look on its own.",
                "is_dress":    True,
            })

    outfits.sort(key=lambda x: x.get("color_score", 1), reverse=True)

    return {
        "outfits":       outfits[:8],
        "combinations":  outfits[:8],
        "total":         len(outfits),
        "total_items":   len(all_wardrobe),
        "filtered_for_event": event,
        "tops_count":    len(tops),
        "bottoms_count": len(bottoms),
        "shoes_count":   len(shoes_list),
        "ai_powered":    bool(ai_combos_raw),
    }


def _get_combo_styling_tip(combo: dict, skin_tone: str, event: str = None) -> str:
    top_name  = f"{combo['top']['color']} {combo['top']['item_name']}" if combo.get("top") else ""
    bot_name  = f"{combo['bottom']['color']} {combo['bottom']['item_name']}" if combo.get("bottom") else ""
    shoe_name = f"{combo['shoes']['color']} {combo['shoes']['item_name']}" if combo.get("shoes") else ""
    event_ctx = f" for {event}" if event else ""

    prompt = f"""One sentence styling tip for: {top_name} + {bot_name} + {shoe_name}{event_ctx}.
Client has {skin_tone} skin. Be specific and punchy. Max 20 words."""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],
                  "max_tokens":60,"temperature":0.6},
            timeout=8
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return _color_pair_label(combo.get("color_score",1))


# ── OUTFIT PLANNING — WITH EVENT FILTERING ───────────────────────────────────

def plan_outfit_for_event(user_id: str, event_description: str, user_profile: dict) -> dict:
    # Get event-appropriate wardrobe only
    event_low  = event_description.lower()
    event_type = "casual"
    for ev in EVENT_REQUIREMENTS:
        if ev in event_low:
            event_type = ev
            break

    wardrobe   = get_event_appropriate_wardrobe(user_id, event_type)
    all_items  = get_wardrobe(user_id)

    skin_tone  = user_profile.get("skinTone","medium")
    face_shape = user_profile.get("face_shape","oval")
    gender     = user_profile.get("gender","male")
    gender_label = "women" if gender.lower() in ("female","women","woman","girl","f") else "men"

    is_night  = any(w in event_low for w in ["night","evening","dinner","cocktail"])
    time_hint = "night / evening" if is_night else "day / afternoon"
    event_info = EVENT_REQUIREMENTS.get(event_type, EVENT_REQUIREMENTS["casual"])
    ev_formality = event_info["formality"]
    is_athletic  = event_info.get("is_athletic", False)
    prefer_ethnic = event_info.get("prefer_ethnic", False)

    VIRTUAL_CAT_KEYWORDS = {
        # STRICT gym keywords — only actual athletic/gym items match, NOT generic shirts
        "gym_tshirt": [
            "dry fit", "dri-fit", "drifit", "gym", "athletic t-shirt", "sport tshirt",
            "performance tshirt", "workout tshirt", "compression tshirt", "jersey",
            "activewear", "training tee", "moisture-wicking", "polyester sport",
            "gym wear", "gym t-shirt", "gym tshirt", "fitness top", "sport top",
        ],
        # STRICT track pants — only actual track/jogger/sweatpants, NOT jeans/trousers/cargo
        "track_pants": [
            "track pant", "track pants", "trackpant", "jogger pant", "joggers",
            "sweatpant", "gym pant", "athletic pant", "training pant", "sport pant",
            "yoga pant", "legging gym", "active pant", "running pant",
            "compression pant", "gym jogger", "workout pant", "track",
        ],
        "sports_shoes": [
            "running shoe", "running shoes", "sport shoe", "sports shoe",
            "training shoe", "gym shoe", "athletic shoe", "sneaker",
            "nike", "adidas", "puma", "campus", "reebok", "skechers",
            "sports", "running", "workout shoe",
        ],
        "swim_shorts": [
            "swim short", "swim trunk", "beach short", "board short",
            "surf short", "water short", "swim",
        ],
        "beach_shirt": [
            "linen shirt", "floral shirt", "beach shirt", "hawaiian",
            "camp shirt", "resort shirt", "summer shirt", "beach top",
        ],
        "flip_flops": [
            "flip flop", "flipflop", "slipper", "chappal",
            "beach sandal", "croc",
        ],
        "ethnic": [
            "kurta", "sherwani", "lehenga", "saree", "sari", "dupatta",
            "anarkali", "salwar", "kurti", "nehru jacket", "bandhgala",
            "dhoti kurta", "ethnic", "traditional", "festive wear",
            "puja wear", "churidar", "pajama kurta",
        ],
    }

    wardrobe_by_cat = {}
    for item in wardrobe:
        wardrobe_by_cat.setdefault(item["category"], []).append(item)

    # Event preference keywords for scoring
    EVENT_PREFER_KEYWORDS = {
        "wedding":   ["sherwani","kurta","ethnic","bandhgala","nehru","lehenga","saree","indo-western","traditional"],
        "festival":  ["kurta","ethnic","traditional","festive","kurti","sherwani","dupatta"],
        "sangeet":   ["kurta","ethnic","festive","bold","colorful","vibrant"],
        "mehndi":    ["kurta","ethnic","festive","cotton","linen","yellow","green","pink"],
        "haldi":     ["kurta","ethnic","cotton","yellow","traditional"],
        "reception": ["sherwani","blazer","suit","indo-western","formal","kurta"],
        "puja":      ["kurta","cotton","silk","ethnic","traditional","nehru"],
        "office":    ["formal","shirt","trouser","blazer","chino","slim fit","button"],
        "interview": ["formal","white","light blue","shirt","trouser","slim","button","blazer"],
        "party":     ["bold","dark","print","graphic","slim","blazer","jacket","dressy"],
        "date":      ["smart","casual","chino","slim","shirt","loafer","clean"],
        "college":   ["casual","streetwear","oversized","graphic","jeans","cargo","sneaker","canvas"],
        "casual":    ["casual","everyday","comfortable","relaxed","t-shirt","jeans"],
        "gym":       ["gym","sport","athletic","track","jogger","dry fit","compression","jersey"],
        "beach":     ["linen","beach","floral","casual","light","summer","hawaiian"],
    }
    event_prefer = EVENT_PREFER_KEYWORDS.get(event_type, [])

    SKIN_TONE_POWER_COLORS = {
        "light":  ["pastel","ivory","blush","sage","navy","burgundy","deep green","white","cream"],
        "medium": ["earthy","terracotta","mustard","royal blue","emerald","wine","brown","orange","olive"],
        "dark":   ["bright","fuchsia","gold","electric blue","red","royal blue","emerald","jewel","white","orange"],
    }
    power_colors = SKIN_TONE_POWER_COLORS.get(skin_tone.lower(), [])

    def _score_item_for_event(item: dict) -> float:
        score = 0.0
        name_style = (
            item.get("item_name","") + " " +
            item.get("style","") + " " +
            " ".join(item.get("occasion",[]))
        ).lower()
        item_color = item.get("color","").lower()
        item_formality = item.get("formality","casual")
        formality_rank = {"formal":2, "semi-formal":1, "casual":0}
        ev_rank = formality_rank.get(ev_formality, 0)
        item_rank = formality_rank.get(item_formality, 0)
        formality_diff = abs(ev_rank - item_rank)
        score += (2 - formality_diff) * 3
        item_occasions = [o.lower() for o in item.get("occasion",[])]
        if event_type in item_occasions:
            score += 5
        for kw in event_prefer:
            if kw in name_style or kw in item_color:
                score += 4
        # Ethnic bonus for ethnic events
        if prefer_ethnic and _is_ethnic_item(item):
            score += 10
        for pc in power_colors:
            if pc in item_color:
                score += 2
                break
        return score

    def _find_item_for_cat(cat: str):
        # Direct category match first
        if cat in wardrobe_by_cat:
            candidates = wardrobe_by_cat[cat]
            if len(candidates) == 1:
                return candidates[0]
            scored = sorted(candidates, key=_score_item_for_event, reverse=True)
            return scored[0]

        keywords = VIRTUAL_CAT_KEYWORDS.get(cat, [])
        if keywords:
            scored = []
            for item in wardrobe:
                full = " ".join([
                    item.get("item_name", ""),
                    item.get("style", ""),
                    item.get("category", ""),
                    " ".join(item.get("occasion", [])),
                ]).lower()
                kw_score = sum(3 if kw in full else 0 for kw in keywords[:6])
                kw_score += sum(1 if kw in full else 0 for kw in keywords[6:])
                if kw_score > 0:
                    ev_score = _score_item_for_event(item)
                    scored.append((kw_score * 2 + ev_score, item))
            if scored:
                scored.sort(key=lambda x: x[0], reverse=True)
                return scored[0][1]

        # Category-level fallbacks (only for ethnic/virtual cats that map to real cats)
        if cat == "ethnic":
            # Check ethnic items in shirt category
            for item in wardrobe:
                name_style = (item.get("item_name", "") + " " + item.get("style", "")).lower()
                if any(kw in name_style for kw in ["kurta","kurti","sherwani","lehenga","ethnic","saree","salwar","anarkali","nehru"]):
                    return item
            # For ethnic events, DO NOT fall back to casual shirts
            if prefer_ethnic:
                return None  # Better to show "missing" than wrong item
            if "shirt" in wardrobe_by_cat:
                return wardrobe_by_cat["shirt"][0]

        # Athletic fallbacks only for athletic events
        if cat == "gym_tshirt" and event_type == "gym":
            if "shirt" in wardrobe_by_cat:
                return wardrobe_by_cat["shirt"][0]
        if cat == "track_pants" and event_type == "gym":
            if "pants" in wardrobe_by_cat:
                return wardrobe_by_cat["pants"][0]
        if cat == "sports_shoes" and event_type == "gym":
            if "shoes" in wardrobe_by_cat:
                return wardrobe_by_cat["shoes"][0]

        # Beach fallbacks only for beach events
        if cat == "beach_shirt" and event_type == "beach":
            if "shirt" in wardrobe_by_cat:
                return wardrobe_by_cat["shirt"][0]
        if cat in ("swim_shorts","gym_shorts") and event_type == "beach":
            if "pants" in wardrobe_by_cat:
                return wardrobe_by_cat["pants"][0]
        if cat == "flip_flops" and event_type == "beach":
            if "shoes" in wardrobe_by_cat:
                return wardrobe_by_cat["shoes"][0]

        # Non-ethnic non-athletic generic fallbacks (only if event allows it)
        if cat == "shirt" and event_type not in ETHNIC_EVENTS:
            if "shirt" in wardrobe_by_cat:
                return wardrobe_by_cat["shirt"][0]
        if cat == "pants" and event_type not in ETHNIC_EVENTS:
            if "pants" in wardrobe_by_cat:
                return wardrobe_by_cat["pants"][0]
        if cat == "shoes":
            if "shoes" in wardrobe_by_cat:
                return wardrobe_by_cat["shoes"][0]

        return None

    available    = {}
    missing      = []
    used_item_ids = set()

    for cat in event_info["cats"]:
        item = _find_item_for_cat(cat)
        if item:
            iid = item.get("item_id", "")
            if iid and iid in used_item_ids:
                alt = None
                for candidate in wardrobe_by_cat.get(item["category"], []):
                    if candidate.get("item_id") not in used_item_ids:
                        alt = candidate
                        break
                if alt:
                    used_item_ids.add(alt.get("item_id", ""))
                    available[cat] = alt
                else:
                    missing.append(cat)
            else:
                if iid:
                    used_item_ids.add(iid)
                available[cat] = item
        else:
            missing.append(cat)

    color_scores = []
    items_list = list(available.values())
    for i in range(len(items_list)):
        for j in range(i+1, len(items_list)):
            c1 = items_list[i].get("color","")
            c2 = items_list[j].get("color","")
            if c1 and c2:
                color_scores.append(_color_pair_score(c1, c2))
    avg_color_score = sum(color_scores) / len(color_scores) if color_scores else 2

    wardrobe_summary = [
        f"{cat}: {item['color']} {item['item_name']} ({item['formality']})"
        for cat, item in available.items()
    ]
    missing_str   = ", ".join(missing) if missing else "none"
    available_str = "\n".join(wardrobe_summary) if wardrobe_summary else "No matching items found"

    outfit_plan_text = _ai_outfit_plan(
        event_description, event_type, time_hint,
        available_str, missing_str, skin_tone, face_shape, gender, is_night,
        event_info.get("vibe","")
    )

    search_cats = event_info.get("search_cats", {})
    missing_products = {}
    for cat in missing:
        if cat in search_cats:
            query = f"{search_cats[cat]} {gender_label}"
        else:
            query = f"{ev_formality} {cat} {gender_label} India"
        prods = _serper_product_search(query)
        if prods:
            missing_products[cat] = prods

    return {
        "event":              event_description,
        "event_type":         event_type,
        "event_icon":         event_info.get("icon","✦"),
        "event_vibe":         event_info.get("vibe",""),
        "time":               time_hint,
        "outfit_plan":        outfit_plan_text,
        "available_items":    available,
        "missing_categories": missing,
        "missing_products":   missing_products,
        "wardrobe_count":     len(all_items),
        "filtered_count":     len(wardrobe),
        "color_harmony":      avg_color_score,
        "is_athletic":        is_athletic,
    }


def get_outfit_suggestions(user_id: str, skin_tone: str = "medium",
                           gender: str = "male", face_shape: str = "oval") -> dict:
    wardrobe = get_wardrobe(user_id)
    if not wardrobe:
        return {"suggestions": [], "message": "Upload clothes first!"}

    wardrobe_cats = set(i["category"] for i in wardrobe)
    suggestions = []

    priority_events = ["casual","college","office","party","date","wedding","brunch","shopping","gym","festival"]

    for event in priority_events:
        ev_info = EVENT_REQUIREMENTS.get(event, {})
        req_cats = set(ev_info.get("cats", []))
        covered = req_cats & wardrobe_cats
        coverage = len(covered) / len(req_cats) if req_cats else 0

        if coverage >= 0.5:
            suggestions.append({
                "event":    event,
                "icon":     ev_info.get("icon","✦"),
                "vibe":     ev_info.get("vibe",""),
                "coverage": round(coverage * 100),
                "ready":    coverage >= 0.9,
            })

    return {
        "suggestions":   suggestions[:5],
        "total_events":  len(suggestions),
        "wardrobe_cats": list(wardrobe_cats),
    }


# ── STYLE GAP ANALYSIS ────────────────────────────────────────────────────────

def style_gap_analysis(user_id: str) -> dict:
    wardrobe = get_wardrobe(user_id)
    wardrobe_cats = set(i["category"] for i in wardrobe)

    gaps = {}
    for event, info in EVENT_REQUIREMENTS.items():
        req_cats = set(info["cats"])
        VIRTUAL_MAP = {
            "gym_tshirt":"shirt","track_pants":"pants","sports_shoes":"shoes",
            "beach_shirt":"shirt","swim_shorts":"pants","flip_flops":"shoes",
        }
        real_req = set()
        for cat in req_cats:
            real_req.add(VIRTUAL_MAP.get(cat, cat))

        missing_real = real_req - wardrobe_cats
        missing_display = []
        for cat in info["cats"]:
            real = VIRTUAL_MAP.get(cat, cat)
            if real in missing_real and cat not in missing_display:
                missing_display.append(cat)

        if missing_display:
            gaps[event] = {
                "missing":    missing_display,
                "icon":       info.get("icon","✦"),
                "vibe":       info.get("vibe",""),
                "urgency":    "high" if len(missing_display) >= 2 else "low",
                "search_cats": {
                    cat: info.get("search_cats",{}).get(cat, f"{cat} India buy online")
                    for cat in missing_display
                },
            }

    high_priority_gaps = {ev: g for ev, g in gaps.items() if g["urgency"] == "high"}

    return {
        "gaps":                gaps,
        "total_missing":       len(gaps),
        "ready_events":        [e for e in EVENT_REQUIREMENTS if e not in gaps],
        "high_priority_gaps":  list(high_priority_gaps.keys()),
    }


def _ai_outfit_plan(event, event_type, time_hint, available_str, missing_str,
                    skin_tone, face_shape, gender, is_night, event_vibe="") -> str:
    if not GROQ_API_KEY:
        return f"For your {event}, here's your outfit plan based on your wardrobe."

    color_palette = {
        "light":  "pastels, ivory, blush, sage green" if not is_night else "navy, burgundy, deep green",
        "medium": "earthy tones, terracotta, mustard"  if not is_night else "royal blue, emerald, wine red",
        "dark":   "bright jewel tones, fuchsia, gold"  if not is_night else "gold, red, electric blue",
    }.get(skin_tone, "neutral tones")

    ETHNIC_EVENTS_SET = {"wedding","sangeet","mehndi","haldi","reception","engagement","puja","festival"}

    if event_type == "gym":
        prompt = f"""You are a fitness & athletic fashion stylist.

EVENT: Gym / Workout
CLIENT: {skin_tone} skin | {face_shape} face | {gender}
ATHLETIC WEAR FOUND IN WARDROBE:
{available_str}
MISSING: {missing_str}

Write a confident gym outfit plan (2-3 sentences):
1. EXACTLY how to wear the athletic items found
2. WHY this color combo works for {skin_tone} skin at the gym
3. One performance tip: moisture-wicking, proper shoe support, etc.
Under 70 words. Energetic, motivating tone."""

    elif event_type == "beach":
        prompt = f"""You are a summer fashion stylist.

EVENT: Beach / Outdoor Summer
CLIENT: {skin_tone} skin | {face_shape} face | {gender}
BEACH WEAR FOUND:
{available_str}
MISSING: {missing_str}

Write a breezy beach outfit plan (2-3 sentences).
Under 70 words. Light, breezy tone."""

    elif event_type in ETHNIC_EVENTS_SET:
        prompt = f"""You are a luxury Indian fashion stylist — Sabyasachi meets Manish Malhotra.

EVENT: {event_type.capitalize()} ceremony
VIBE: {event_vibe}
CLIENT: {skin_tone} skin | {face_shape} face | {gender}
ETHNIC WEAR FOUND IN WARDROBE:
{available_str}
MISSING: {missing_str}

Write an ethnic outfit plan (3-4 sentences):
1. EXACTLY how to style the kurta/ethnic item found
2. WHY these colors are stunning for {skin_tone} skin at a {event_type}
3. Specific jewelry/accessory tip for this event
4. Footwear tip
Under 100 words. Sound like a real Indian fashion expert."""

    else:
        prompt = f"""You are a world-class personal stylist. Specific, opinionated, stylish.

EVENT: {event} ({event_type}, {time_hint})
VIBE: {event_vibe}
CLIENT: {skin_tone} skin | {face_shape} face | {gender}
POWER COLORS FOR THEIR SKIN TONE: {color_palette}

WARDROBE AVAILABLE:
{available_str}

MISSING ITEMS: {missing_str}

Write a confident outfit plan (3-4 sentences):
1. EXACTLY how to combine the available wardrobe items — be specific
2. WHY these colors work for their exact skin tone
3. One specific accessory tip for this event vibe
Under 100 words."""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],
                  "max_tokens":200,"temperature":0.5},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"AI outfit plan error: {e}")
    return f"For your {event} ({time_hint}), here's your outfit plan."


# ── PRODUCT SEARCH ───────────────────────────────────────────────────────────

def _is_valid_image_url(url: str) -> bool:
    if not url or not isinstance(url, str): return False
    if not url.startswith("http"): return False
    if "encrypted-tbn" in url or "googleusercontent" in url: return True
    cdn_domains = ["assets.myntassets.com","rukminim","m.media-amazon","images.nykaa",
                   "images-cdn.ajio","images.meesho.com","gloimg","lh3.googleusercontent",
                   "static.nike","images.bewakoof","img1.ajio","cdn.shopify"]
    if any(d in url for d in cdn_domains): return True
    if re.search(r"\.(jpg|jpeg|png|webp|gif)(\?|$)", url, re.I): return True
    return False


def _fetch_image_for_title(title: str) -> str | None:
    for key in SERPER_KEYS:
        if not key: continue
        try:
            resp = requests.post(
                "https://google.serper.dev/images",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": title, "gl": "in", "hl": "en", "num": 5},
                timeout=12,
            )
            if resp.status_code == 200:
                for img in resp.json().get("images", []):
                    u = img.get("imageUrl") or img.get("thumbnailUrl")
                    if u and _is_valid_image_url(u): return u
        except Exception: pass
    return None


def _serper_product_search(query: str) -> list:
    products = []
    for key in SERPER_KEYS:
        if not key: continue
        try:
            resp = requests.post(
                "https://google.serper.dev/shopping",
                headers={"X-API-KEY": key, "Content-Type": "application/json"},
                json={"q": query, "gl": "in", "hl": "en", "num": 8},
                timeout=12
            )
            if resp.status_code in (402, 429): continue
            if resp.status_code != 200: continue
            for item in resp.json().get("shopping", [])[:4]:
                link = item.get("link") or item.get("productLink","")
                if not link or "http" not in link: continue
                title = item.get("title","").strip()
                if not title or len(title) < 4: continue
                image = None
                for f in ("thumbnailUrl","imageUrl","image","thumbnail"):
                    v = item.get(f)
                    if v and _is_valid_image_url(v):
                        image = v; break
                if not image:
                    image = _fetch_image_for_title(title)
                products.append({
                    "title": title, "price": item.get("price","Check price") or "Check price",
                    "image": image, "link": link, "source": item.get("source","amazon.in"),
                })
                if len(products) >= 4: break
            if products: break
        except Exception as e:
            print(f"Serper search error: {e}")
    return products


# ── CLOSET SUMMARY ───────────────────────────────────────────────────────────

def get_closet_summary(user_id: str) -> dict:
    wardrobe = get_wardrobe(user_id)
    if not wardrobe:
        return {"total": 0, "categories": {}, "summary": "Your closet is empty!"}

    by_cat = {}
    for item in wardrobe:
        by_cat.setdefault(item["category"], []).append(item["item_name"])

    all_cats = set(CLOSET_CATEGORIES.keys())
    present  = set(by_cat.keys())
    gaps     = list(all_cats - present)

    gap_data = style_gap_analysis(user_id)
    ready_events = gap_data.get("ready_events", [])

    return {
        "total":        len(wardrobe),
        "categories":   by_cat,
        "gaps":         gaps,
        "ready_events": ready_events,
        "summary": (
            f"You have {len(wardrobe)} items across {len(by_cat)} categories. "
            f"Ready for: {', '.join(ready_events[:4]) if ready_events else 'upload more items'}. "
            f"Missing: {', '.join(gaps) if gaps else 'nothing major!'}"
        ),
    }


# ── MULTI-OUTFIT PLANNER ─────────────────────────────────────────────────────

def plan_multiple_outfits_for_event(user_id: str, event_description: str, user_profile: dict) -> dict:
    """Generate 2-3 DISTINCT complete outfit combinations for an event, event-filtered."""
    event_low  = event_description.lower()
    event_type = "casual"
    for ev in EVENT_REQUIREMENTS:
        if ev in event_low:
            event_type = ev
            break

    # KEY: Use event-appropriate wardrobe only
    wardrobe   = get_event_appropriate_wardrobe(user_id, event_type)
    all_items  = get_wardrobe(user_id)

    skin_tone  = user_profile.get("skinTone","medium")
    face_shape = user_profile.get("face_shape","oval")
    gender     = user_profile.get("gender","male")
    gender_label = "women" if gender.lower() in ("female","women","woman","girl","f") else "men"

    is_night  = any(w in event_low for w in ["night","evening","dinner","cocktail"])
    time_hint = "night / evening" if is_night else "day / afternoon"
    event_info = EVENT_REQUIREMENTS.get(event_type, EVENT_REQUIREMENTS["casual"])
    ev_formality = event_info["formality"]
    is_athletic  = event_info.get("is_athletic", False)
    prefer_ethnic = event_info.get("prefer_ethnic", False)

    EVENT_PREFER_KEYWORDS = {
        "wedding":   ["sherwani","kurta","ethnic","bandhgala","nehru","lehenga","saree"],
        "festival":  ["kurta","ethnic","traditional","festive","kurti","sherwani","dupatta"],
        "office":    ["formal","shirt","trouser","blazer","chino","slim fit","button"],
        "interview": ["formal","white","light blue","shirt","trouser","slim","button"],
        "party":     ["bold","dark","print","graphic","slim","blazer","jacket"],
        "date":      ["smart","casual","chino","slim","shirt","loafer"],
        "college":   ["casual","streetwear","oversized","graphic","jeans","cargo","sneaker"],
        "casual":    ["casual","everyday","comfortable","relaxed","t-shirt","jeans"],
        "gym":       ["gym","sport","athletic","track","jogger","dry fit","compression"],
        "beach":     ["linen","beach","floral","casual","light","summer"],
    }
    event_prefer = EVENT_PREFER_KEYWORDS.get(event_type, [])

    ETHNIC_KW = ["kurta","kurti","sherwani","lehenga","saree","sari","dupatta","anarkali",
                 "salwar","ethnic","traditional","festive","nehru","churidar","bandhgala"]

    def _item_text(item):
        return " ".join([
            item.get("item_name",""), item.get("style",""),
            item.get("category",""), " ".join(item.get("occasion",[]))
        ]).lower()

    def _event_score(item):
        score = 0.0
        text  = _item_text(item)
        color = item.get("color","").lower()
        formality_rank = {"formal":2,"semi-formal":1,"casual":0}
        ev_rank = formality_rank.get(ev_formality,0)
        item_rank = formality_rank.get(item.get("formality","casual"),0)
        score += (2 - abs(ev_rank - item_rank)) * 3
        if event_type in [o.lower() for o in item.get("occasion",[])]:
            score += 5
        for kw in event_prefer:
            if kw in text or kw in color: score += 4
        if prefer_ethnic and _is_ethnic_item(item):
            score += 10
        return score

    def _get_tops():
        candidates = []
        for item in wardrobe:
            if item["category"] in ("shirt","ethnic","dress","top"):
                candidates.append((_event_score(item), item))
        candidates.sort(key=lambda x: x[0], reverse=True)
        seen, result = set(), []
        for _, item in candidates:
            if item["item_id"] not in seen:
                seen.add(item["item_id"])
                result.append(item)
        return result

    def _get_bottoms():
        candidates = []
        for item in wardrobe:
            if item["category"] == "pants":
                candidates.append((_event_score(item), item))
        candidates.sort(key=lambda x: x[0], reverse=True)
        seen, result = set(), []
        for _, item in candidates:
            if item["item_id"] not in seen:
                seen.add(item["item_id"])
                result.append(item)
        return result

    tops        = _get_tops()
    bottoms     = _get_bottoms()
    shoes_list  = sorted([i for i in wardrobe if i["category"] == "shoes"], key=_event_score, reverse=True)
    accessories = [i for i in wardrobe if i["category"] == "accessories"] if event_type not in {"gym","beach"} else []

    outfits = []

    if tops and bottoms:
        t = tops[0]
        best_b = max(bottoms, key=lambda b: _color_pair_score(t["color"], b["color"]))
        outfit = {"top": t, "bottom": best_b}
        if shoes_list:
            outfit["shoes"] = max(shoes_list, key=lambda s: _color_pair_score(s["color"], t["color"]) + _color_pair_score(s["color"], best_b["color"]))
        if accessories:
            outfit["accessories"] = accessories[0]
        outfits.append(outfit)

    if len(tops) >= 2:
        t2 = tops[1]
        other_bottoms = [b for b in bottoms if not outfits or b["item_id"] != outfits[0]["bottom"]["item_id"]]
        best_b2 = max(other_bottoms if other_bottoms else bottoms, key=lambda b: _color_pair_score(t2["color"], b["color"]))
        outfit2 = {"top": t2, "bottom": best_b2}
        if shoes_list:
            outfit2["shoes"] = max(shoes_list, key=lambda s: _color_pair_score(s["color"], t2["color"]) + _color_pair_score(s["color"], best_b2["color"]))
        if accessories:
            outfit2["accessories"] = accessories[min(1, len(accessories)-1)]
        outfits.append(outfit2)
    elif tops and len(bottoms) >= 2:
        t = tops[0]
        other_bottoms = [b for b in bottoms if not outfits or b["item_id"] != outfits[0]["bottom"]["item_id"]]
        if other_bottoms:
            b2 = max(other_bottoms, key=lambda b: _color_pair_score(t["color"], b["color"]))
            outfit2 = {"top": t, "bottom": b2}
            if shoes_list:
                outfit2["shoes"] = max(shoes_list, key=lambda s: _color_pair_score(s["color"], t["color"]) + _color_pair_score(s["color"], b2["color"]))
            outfits.append(outfit2)

    def _outfit_color_score(outfit):
        items = [v for v in outfit.values() if isinstance(v, dict)]
        if len(items) < 2: return 2
        scores = []
        for i in range(len(items)):
            for j in range(i+1, len(items)):
                c1 = items[i].get("color","")
                c2 = items[j].get("color","")
                if c1 and c2: scores.append(_color_pair_score(c1, c2))
        return round(sum(scores)/len(scores), 1) if scores else 2

    scored_outfits = []
    for outfit in outfits:
        score = _outfit_color_score(outfit)
        items_dict = {}
        for k, v in outfit.items():
            if isinstance(v, dict):
                items_dict[k] = v
        scored_outfits.append({
            "items":       items_dict,
            **outfit,
            "color_score": score,
            "color_label": _color_pair_label(int(score)),
        })

    if GROQ_API_KEY and scored_outfits:
        for i, so in enumerate(scored_outfits[:3]):
            items_desc = ", ".join([
                f"{v['color']} {v['item_name']}"
                for v in so["items"].values() if isinstance(v, dict) and v
            ])
            prompt = f"""One punchy sentence (max 20 words): styling tip for {event_type} outfit #{i+1}.
Items: {items_desc}. Client has {skin_tone} skin, {gender}. Be specific."""
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json={"model":"llama-3.3-70b-versatile",
                          "messages":[{"role":"user","content":prompt}],
                          "max_tokens":60,"temperature":0.6},
                    timeout=8
                )
                if resp.status_code == 200:
                    so["styling_tip"] = resp.json()["choices"][0]["message"]["content"].strip().strip('"')
            except Exception:
                so["styling_tip"] = so["color_label"]

    event_cats = event_info.get("cats",[])
    all_wardrobe_cats = set(i["category"] for i in all_items)
    VIRTUAL_MAP = {
        "gym_tshirt":"shirt","track_pants":"pants","sports_shoes":"shoes",
        "beach_shirt":"shirt","swim_shorts":"pants","flip_flops":"shoes",
    }
    missing_cats = [
        cat for cat in event_cats
        if VIRTUAL_MAP.get(cat, cat) not in all_wardrobe_cats
    ]

    search_cats = event_info.get("search_cats", {})
    missing_products = {}
    for cat in missing_cats[:3]:
        query = f"{search_cats.get(cat, f'{ev_formality} {cat}')} {gender_label}"
        prods = _serper_product_search(query)
        if prods:
            missing_products[cat] = prods

    main_avail_str = "\n".join(
        f"{k}: {v['color']} {v['item_name']}"
        for k, v in scored_outfits[0]["items"].items() if isinstance(v, dict) and v
    ) if scored_outfits else "No items found"

    main_outfit_plan = _ai_outfit_plan(
        event_description, event_type, time_hint,
        main_avail_str,
        ", ".join(missing_cats) if missing_cats else "none",
        skin_tone, face_shape, gender, is_night,
        event_info.get("vibe","")
    )

    return {
        "event":              event_description,
        "event_type":         event_type,
        "event_icon":         event_info.get("icon","✦"),
        "event_vibe":         event_info.get("vibe",""),
        "time":               time_hint,
        "outfit_plan":        main_outfit_plan,
        "outfits":            scored_outfits,
        "available_items":    scored_outfits[0]["items"] if scored_outfits else {},
        "missing_categories": missing_cats,
        "missing_products":   missing_products,
        "wardrobe_count":     len(all_items),
        "filtered_count":     len(wardrobe),
        "is_athletic":        is_athletic,
        "color_harmony":      scored_outfits[0]["color_score"] if scored_outfits else 2,
    }