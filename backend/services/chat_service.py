"""
chat_service.py — FACEFIT STYLIST v13 (PATCHED)
═══════════════════════════════════════════════════
MERGED CHANGES (from chat_service_patch.py):
  1. _extract_user_id() helper — priority: userId > user_id > name > "guest"
  2. get_event_appropriate_wardrobe imported from closet_agent
  3. _plan_dual_outfit_fixed() — event-filtered wardrobe (no gym shorts at weddings)
  4. chat_with_ai() uses _extract_user_id() and _plan_dual_outfit_fixed()

KEY FEATURES in v13:
  1. DUAL OUTFIT: Closet query → returns BOTH wardrobe outfit + new product picks
  2. Gender-aware accessories: males never get necklace/earrings, females never get watch/bracelet
  3. Closet outfit: uses ALL wardrobe items, picks best by color harmony + event formality
  4. Weekly planner action: returns structured JSON plan for 7 days
  5. Gap analysis action: returns gap data for frontend
  6. Festival/ethnic: checks wardrobe first, shows what they have + new ethnic picks
  7. No hardcoding — all products from RAG + skin analysis + Serper API
  8. Style aesthetics: Old Money, Streetwear, Minimalist, Athleisure, Boho, Indo Western, etc.
  9. Outfit validation: filters wardrobe items inappropriate for event (gym, beach, interview)
"""

from langchain_groq import ChatGroq
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from datetime import datetime
import pytz

try:
    from langchain_huggingface import HuggingFaceEmbeddings as Embeddings
except ImportError:
    from langchain_community.embeddings import SentenceTransformerEmbeddings as Embeddings

import os
import re
import json
import requests as _requests

from services.fashion_rag_service import (
    generate_outfit_recommendation,
    generate_outfit_for_context,
    OUTFITS,
    STYLE_KEYWORDS,
)
from services.skin_rag_service import generate_skin_recommendation
from services.product_service import get_product_recommendations
from services.closet_agent import (
    plan_outfit_for_event,
    get_closet_summary,
    get_wardrobe,
    get_event_appropriate_wardrobe,   # ← PATCHED: now imported
    style_gap_analysis,
    mix_and_match,
    EVENT_REQUIREMENTS,
    GROQ_API_KEY as _GROQ_KEY,
)

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.5,
    groq_api_key=os.getenv("GROQ_API_KEY"),
)


def _load_rag(path, collection):
    loader   = TextLoader(path)
    docs     = loader.load()
    splitter = CharacterTextSplitter(chunk_size=600, chunk_overlap=100)
    chunks   = splitter.split_documents(docs)
    emb      = Embeddings(model_name="all-MiniLM-L6-v2")
    vs       = Chroma.from_documents(chunks, emb, collection_name=collection)
    return vs.as_retriever(search_kwargs={"k": 6})


_skin_ret    = _load_rag("rag_data/skincare_knowledge.txt", "chat_skin_v13")
_fashion_ret = _load_rag("rag_data/fashion_knowledge.txt",  "chat_fashion_v13")


def _rag(retriever, query):
    return "\n\n".join(d.page_content for d in retriever.invoke(query))


# ── Constants ──────────────────────────────────────────────────────────────────
BLAZER_NEEDED_EVENTS = ["wedding","party","office","date","reception","interview","farewell","dinner","concert"]
ETHNIC_EVENTS = {"wedding","sangeet","mehndi","haldi","reception","engagement","puja","festival"}
ATHLETIC_EVENTS = {"gym", "beach", "cricket", "football", "running", "sport"}

FASHION_SINGLE_ITEM_MAP = {
    "t-shirt":"shirt","tshirt":"shirt","t shirt":"shirt","shirt":"shirt",
    "polo":"shirt","kurta":"ethnic","top":"top","blouse":"top","kurti":"ethnic",
    "kurta pajama":"ethnic","sherwani":"ethnic","lehenga":"ethnic","saree":"ethnic",
    "sari":"ethnic","salwar":"ethnic","anarkali":"ethnic","dupatta":"ethnic",
    "pant":"pants","pants":"pants","trouser":"pants","jeans":"pants",
    "chino":"pants","shorts":"pants","legging":"pants",
    "shoe":"shoes","shoes":"shoes","sneaker":"shoes","boot":"shoes",
    "sandal":"shoes","loafer":"shoes","heel":"shoes","jutti":"shoes","kolhapuri":"shoes",
    "watch":"watch","bracelet":"bracelet","sunglasses":"sunglasses",
    "necklace":"necklace","earring":"earrings","ring":"accessories",
    "jacket":"jacket","blazer":"blazer","hoodie":"shirt","sweater":"shirt",
    "dress":"dress","gown":"dress","skirt":"pants","bodysuit":"top",
    "cargo":"pants","linen shirt":"shirt","oxford":"shirt",
    "track pant":"pants","track pants":"pants","jogger":"pants","sweatpant":"pants",
    "gym tshirt":"shirt","gym t-shirt":"shirt","gym wear":"shirt",
    "sports shoe":"shoes","running shoe":"shoes","training shoe":"shoes",
    "swim short":"pants","swim shorts":"pants","beach short":"pants","board short":"pants",
}

SKINCARE_SINGLE_MAP = {
    "salicylic acid":"serum_night","bha":"serum_night",
    "niacinamide":"serum_day","vitamin c":"serum_day",
    "retinol":"serum_night","hyaluronic acid":"serum_day",
    "ceramide":"moisturizer","benzoyl peroxide":"spot_treatment",
    "spf":"sunscreen","sunscreen":"sunscreen",
    "face wash":"cleanser","cleanser":"cleanser",
    "toner":"toner","moisturizer":"moisturizer","eye cream":"eye_cream","serum":None,
    "alpha arbutin":"serum_night","azelaic acid":"serum_night",
    "caffeine":"eye_cream","peptide":"moisturizer","kojic acid":"serum_night",
}

COLOR_KEYWORDS = [
    "red","blue","green","black","white","grey","gray","navy","navy blue",
    "yellow","orange","pink","purple","maroon","brown","beige","cream",
    "teal","olive","mustard","burgundy","coral","magenta","lavender",
    "mint","sage","khaki","emerald","royal blue","electric blue",
    "burnt orange","pastel","dark green","forest green","off white","ivory",
    "champagne","gold","silver","rust","peach","lilac","violet",
    "saffron","terracotta","camel","copper","wine","crimson","charcoal",
]

_SK = ["skin","acne","pimple","serum","moisturizer","sunscreen","cleanser","toner",
       "dark circle","dark spot","routine","oily","dry","sensitive","spf","vitamin c",
       "niacinamide","retinol","salicylic","breakout","glow","hyperpigmentation",
       "eye cream","spot treatment","face wash","bha","aha","skincare","ingredient",
       "caffeine","peptide","kojic","arbutin","azelaic","glycolic","lactic",
       "skin care","skin issue","skin problem","complexion"]

_FK = ["outfit","dress","wear","clothes","kurta","shirt","jeans","fashion","style",
       "wedding","party","office","work","casual","date","gym","festival","puja",
       "reception","farewell","beach","brunch","club","concert","college","interview",
       "shoes","look","colour","color","top","trousers","accessories","t-shirt",
       "tshirt","pant","pants","watch","bracelet","sunglasses","necklace","earring",
       "blazer","jacket","tonight","event","function","ceremony","occasion",
       "old money","streetwear","boho","formal","ethnic","minimal","smart casual","luxe",
       "preppy","hypebeast","indo western","indo-western","kurta pajama","sherwani",
       "saree","lehenga","salwar","anarkali","palazzo","churidar","dupatta",
       "linen","cotton","denim","silk","velvet","what to wear","how to dress",
       "coordinate","look for","outfit for","dress for","what should i wear","suggestions",
       "recommendation","trending","trend","aesthetic","vibe","look","lewk","drip",
       "grooming","beard","hairstyle","haircut","styling tip",
       "kurti","ethnic wear","traditional","festive wear","ethnic outfit",
       "track pant","gym wear","gym tshirt","sports wear","athletic","workout",
       "beach wear","swim","beach outfit","summer outfit",
       ]

_CK = [
    "my closet","my wardrobe","my clothes","what i have","from my wardrobe",
    "in my closet","from what i own","mix and match","outfit from",
    "clothes i have","show my wardrobe","wardrobe","what i own","from my clothes",
    "using my clothes","use my wardrobe","do i have","is there a","is there an",
    "do i own","have i got","check my closet","check my wardrobe",
    "in my wardrobe","from my closet","plan from my","style from my",
    "from my collection","based on my wardrobe","based on my closet",
    "i have a wedding","i have a party","i have an event","i have a date",
    "i have a dinner","i have office","based on","using my","with my clothes",
    "color in my","colour in my","black in my","green in my","blue in my",
    "kurta","kurti","sherwani","lehenga","saree","ethnic","my kurta","my kurti",
    "gym outfit","gym clothes","gym wear","track pants","my gym",
    "beach outfit","beach clothes","beach wear","swim shorts",
]

_EV = ["wedding","party","office","work","casual","date","gym","festival",
       "puja","reception","farewell","beach","brunch","club","concert",
       "college","interview","dinner","tonight","event","function","ceremony","occasion",
       "sangeet","mehndi","haldi","reception","engagement"]

TONE_COLOR_POOL = {
    "dark": {
        "shirt":  ["electric blue","emerald green","royal blue","burnt orange","magenta","saffron yellow","coral red","deep purple","forest green","mustard"],
        "pants":  ["black slim","khaki cargo","cream chino","navy blue","off white linen","brown cargo","olive","charcoal grey"],
        "shoes":  ["white chunky sneakers","black leather loafers","tan kolhapuri","white canvas sneakers","brown suede"],
        "top":    ["electric blue crop","saffron yellow blouse","burnt orange off-shoulder","emerald green kurti","magenta bodysuit","coral crop"],
        "blazer": ["black blazer","white blazer","electric blue blazer","olive green blazer"],
        "ethnic": ["saffron yellow","emerald green","electric blue","magenta","coral red"],
    },
    "medium": {
        "shirt":  ["mustard yellow","olive green","terracotta","burgundy","teal blue","rust orange","forest green","camel brown","wine red","sage green"],
        "pants":  ["khaki beige","dark navy","camel chino","brown slim","olive cargo","cream linen","charcoal slim"],
        "shoes":  ["tan sneakers","brown loafers","white leather","camel suede","dark brown boots"],
        "top":    ["mustard crop","terracotta blouse","teal kurti","burgundy bodysuit","maroon off-shoulder"],
        "blazer": ["camel blazer","navy blazer","burgundy blazer","olive blazer"],
        "ethnic": ["mustard","teal blue","burgundy","forest green","terracotta"],
    },
    "light": {
        "shirt":  ["pastel blue","mint green","lavender","sage green","soft pink","sky blue","peach","lilac","powder blue","baby yellow"],
        "pants":  ["light grey","white slim","cream linen","ivory","light blue","beige chino","pale yellow"],
        "shoes":  ["white minimal sneakers","nude heels","white loafers","light pink sandals","silver flats"],
        "top":    ["lavender crop","mint bodysuit","soft pink kurti","sky blue off-shoulder","peach blouse"],
        "blazer": ["white blazer","beige blazer","powder blue blazer","soft grey blazer"],
        "ethnic": ["pastel pink","ivory","powder blue","mint","champagne"],
    },
}


# ── Style Aesthetics Knowledge Base ───────────────────────────────────────────
STYLE_AESTHETICS = {
    "old money": {
        "desc": "Quiet luxury — understated elegance, quality over logos. Navy, camel, cream, hunter green.",
        "men_pieces": {
            "shirt": "polo shirt white navy fitted men India",
            "pants": "slim chino trousers camel beige men India",
            "shoes": "brown leather loafers oxford men India",
            "blazer": "navy blue tailored blazer men India",
            "accessories": "classic silver gold watch minimal men India",
        },
        "women_pieces": {
            "top": "silk blouse cream white women India",
            "pants": "tailored wide leg trousers women camel beige India",
            "shoes": "nude ballet flat loafer women India",
            "blazer": "beige camel structured blazer women India",
            "accessories": "pearl necklace gold bracelet women minimal India",
        },
        "colors": ["navy", "camel", "cream", "hunter green", "burgundy", "white"],
        "avoid": ["logos", "bright prints", "athleisure", "streetwear"],
        "key_pieces": ["Polo shirt", "Chinos", "Loafers", "Blazer", "Classic watch"],
    },
    "streetwear": {
        "desc": "Oversized silhouettes, graphic tees, cargo pants, chunky sneakers. Bold and expressive.",
        "men_pieces": {
            "shirt": "oversized graphic t-shirt men streetwear India",
            "pants": "cargo jogger pants men streetwear black India",
            "shoes": "chunky white sneakers men Nike Adidas India",
            "accessories": "cap bucket hat streetwear men India",
            "jacket": "puffer jacket oversized men streetwear India",
        },
        "women_pieces": {
            "top": "oversized graphic tee crop top women streetwear India",
            "pants": "baggy cargo pants women streetwear India",
            "shoes": "chunky platform sneakers women India",
            "accessories": "chain necklace cap bucket hat women India",
        },
        "colors": ["black", "white", "grey", "electric blue", "red", "neon"],
        "avoid": ["formal shoes", "slim trousers", "blazers", "formal shirts"],
        "key_pieces": ["Oversized graphic tee", "Cargo pants", "Chunky sneakers", "Cap/beanie"],
    },
    "minimalist": {
        "desc": "Less is more. Clean lines, neutral palette, quality basics. Monochromatic dressing.",
        "men_pieces": {
            "shirt": "plain white black grey tee men minimal India",
            "pants": "straight leg trousers minimal men India",
            "shoes": "clean white leather sneakers men minimal India",
            "accessories": "simple thin watch men minimal India",
        },
        "women_pieces": {
            "top": "plain white black tee blouse women minimal India",
            "pants": "straight leg trousers minimal women India",
            "shoes": "white minimal sneaker flat women India",
            "accessories": "thin gold ring bracelet women India",
        },
        "colors": ["white", "black", "grey", "cream", "beige", "navy"],
        "avoid": ["bold prints", "heavy branding", "loud accessories", "multiple colors"],
        "key_pieces": ["Plain tee", "Straight trousers", "Clean white sneakers", "Simple watch"],
    },
    "athleisure": {
        "desc": "Athletic + leisure fusion. Elevated gym wear worn off the track.",
        "men_pieces": {
            "shirt": "slim fit tee hoodie sport men India athleisure",
            "pants": "slim jogger tech pants men India sport",
            "shoes": "crisp clean running sneakers men India Nike",
            "accessories": "sport fitness watch men India",
        },
        "women_pieces": {
            "top": "sport crop top hoodie women India athleisure",
            "pants": "high waist legging jogger women India",
            "shoes": "crisp running sneakers women India",
            "accessories": "fitness tracker sport watch women India",
        },
        "colors": ["black", "grey", "navy", "electric blue", "coral"],
        "avoid": ["formal blazers", "leather shoes", "ethnic wear", "structured clothing"],
        "key_pieces": ["Slim joggers", "Performance tee/hoodie", "Crisp sneakers"],
    },
    "boho": {
        "desc": "Bohemian — flowy fabrics, earthy tones, ethnic prints, layers. Free-spirited.",
        "men_pieces": {
            "shirt": "linen floral printed shirt men boho India",
            "pants": "linen wide leg trouser men boho India",
            "shoes": "kolhapuri leather sandal men India",
            "accessories": "beaded bracelet layered necklace men boho India",
        },
        "women_pieces": {
            "top": "floral printed boho kurti blouse women India",
            "pants": "flared pallazo linen trouser women boho India",
            "shoes": "kolhapuri sandal flat women India boho",
            "accessories": "layered necklace jhumka earring women boho India",
        },
        "colors": ["terracotta", "mustard", "cream", "olive", "rust", "sage"],
        "avoid": ["structured blazers", "formal shoes", "monochrome clean looks"],
        "key_pieces": ["Linen/flowy shirt", "Wide-leg or flared pants", "Sandals", "Layered accessories"],
    },
    "indo western": {
        "desc": "East meets West — kurta with jeans, dhoti pants with shirts, embroidered blazers.",
        "men_pieces": {
            "ethnic": "kurta men slim fit India Indo western fusion",
            "pants": "slim fit dark jeans churidar men India Indo western",
            "shoes": "oxford jutti leather shoe men Indo western India",
            "blazer": "embroidered bandhgala nehru jacket men India",
        },
        "women_pieces": {
            "ethnic": "kurti anarkali women India Indo western",
            "pants": "slim jeans palazzo wide leg women Indo western India",
            "shoes": "heels jutti sandal women India Indo western",
            "accessories": "oxidised silver jewellery women Indo western India",
        },
        "colors": ["navy", "cream", "black", "mustard", "emerald"],
        "avoid": ["full formal western", "pure ethnic traditional only"],
        "key_pieces": ["Kurta + slim jeans", "Embroidered blazer", "Oxford shoes or juttis"],
    },
    "smart casual": {
        "desc": "Sweet spot between formal and casual. Clean jeans or chinos with a neat shirt.",
        "men_pieces": {
            "shirt": "oxford shirt linen shirt smart casual men India",
            "pants": "dark slim jeans chino trousers men India",
            "shoes": "loafer clean white leather sneaker men India smart casual",
            "blazer": "unstructured casual blazer men India optional",
        },
        "women_pieces": {
            "top": "blouse smart casual women India linen cotton",
            "pants": "slim straight jeans chino women India",
            "shoes": "loafer block heel white sneaker women India smart",
            "accessories": "dainty necklace watch women smart casual India",
        },
        "colors": ["navy", "white", "grey", "olive", "camel", "black"],
        "avoid": ["track pants", "gym wear", "very casual graphic tees", "flip flops"],
        "key_pieces": ["Oxford/linen shirt", "Dark jeans or chinos", "Loafers/clean sneakers"],
    },
    "preppy": {
        "desc": "College campus-inspired — polos, chinos, pastel shirts, boat shoes. Clean and classic.",
        "men_pieces": {
            "shirt": "polo shirt pastel stripe men preppy India",
            "pants": "chino slim fit men pastel India",
            "shoes": "boat shoe loafer white men preppy India",
            "accessories": "minimal watch leather strap men preppy India",
        },
        "women_pieces": {
            "top": "polo pastel stripe blouse women preppy India",
            "pants": "chino slim fit skirt women preppy India",
            "shoes": "boat shoe loafer white women India",
            "accessories": "pearl small earrings minimal women preppy India",
        },
        "colors": ["navy", "pastel blue", "white", "salmon", "mint", "yellow"],
        "avoid": ["heavy streetwear", "loud graphics", "dark heavy tones", "athleisure"],
        "key_pieces": ["Polo shirt", "Chinos", "Boat shoes/loafers"],
    },
    "hypebeast": {
        "desc": "Limited drops, bold logos, sneaker culture. Off-White energy.",
        "men_pieces": {
            "shirt": "graphic hoodie limited streetwear men hypebeast India",
            "pants": "slim jogger tech fleece men hype India",
            "shoes": "limited edition sneakers Jordan Nike men India",
            "accessories": "cap crossbody bag chain men hypebeast India",
        },
        "women_pieces": {
            "top": "graphic cropped hoodie tee women hypebeast India",
            "pants": "tech jogger biker shorts women hype India",
            "shoes": "platform sneakers limited edition women India",
            "accessories": "cap chain bag women hypebeast India",
        },
        "colors": ["black", "white", "red", "yellow", "neon", "grey"],
        "avoid": ["formal wear", "ethnic wear", "muted understated tones"],
        "key_pieces": ["Statement graphic tee/hoodie", "Slim joggers", "Limited sneakers"],
    },
}

STYLE_AESTHETIC_KEYWORDS = [
    "old money", "streetwear", "minimalist", "athleisure", "boho", "bohemian",
    "indo western", "indo-western", "smart casual", "preppy", "hypebeast",
    "style aesthetic", "aesthetic style", "style guide", "style for me",
    "fashion aesthetic", "my style", "what style", "style vibe", "dress like",
]


# ── Event Outfit Validation ────────────────────────────────────────────────────
EVENT_OUTFIT_VALIDATION = {
    "gym": {
        "forbidden_keywords": ["kurta", "sherwani", "ethnic", "blazer", "oxford",
                               "loafer", "leather shoe", "jeans", "denim", "chino",
                               "saree", "lehenga"],
        "required_style": "athletic",
        "message": "⚠️ Your wardrobe has no gym-appropriate clothes. Gym needs: dry-fit tee, track pants, sports shoes.",
    },
    "beach": {
        "forbidden_keywords": ["formal", "kurta", "sherwani", "blazer", "oxford",
                               "ethnic", "suit", "trouser"],
        "required_style": "casual beach",
        "message": "⚠️ Beach attire should be light — linen shirt, swim shorts, flip flops.",
    },
    "interview": {
        "forbidden_keywords": ["track pant", "jogger", "graphic tee", "oversized",
                               "ethnic", "kurta", "flip flop", "slipper"],
        "required_style": "formal professional",
        "message": "⚠️ Interviews need professional attire — formal shirt, trousers, leather shoes.",
    },
}


def validate_wardrobe_for_event(available_items: dict, event_type: str) -> dict:
    """
    Filter out items inappropriate for an event.
    Returns filtered items + warnings.
    """
    rules = EVENT_OUTFIT_VALIDATION.get(event_type, {})
    if not rules:
        return {"items": available_items, "warnings": [], "all_valid": True}

    forbidden = rules.get("forbidden_keywords", [])
    valid_items = {}
    warnings = []
    removed = []

    for cat, item in available_items.items():
        if not item:
            continue
        item_text = " ".join([
            item.get("item_name", ""),
            item.get("style", ""),
            item.get("category", ""),
            " ".join(item.get("occasion", [])),
        ]).lower()
        is_forbidden = any(kw in item_text for kw in forbidden)
        if is_forbidden:
            removed.append(item.get("item_name", cat))
        else:
            valid_items[cat] = item

    if removed:
        warnings.append(rules["message"])

    return {
        "items": valid_items,
        "warnings": warnings,
        "removed": removed,
        "all_valid": len(removed) == 0,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────
def _is_male(gender):
    return gender.lower() not in ("female","women","woman","girl","f")


def _gender_label(gender):
    return "men" if _is_male(gender) else "women"


def _get_time_context():
    try:
        ist  = pytz.timezone("Asia/Kolkata")
        hour = datetime.now(ist).hour
    except Exception:
        hour = datetime.now().hour
    if 5 <= hour < 12:    return "morning"
    elif 12 <= hour < 17: return "afternoon"
    elif 17 <= hour < 20: return "evening"
    else:                 return "night"


def _detect_time_from_message(msg):
    msg_low = msg.lower()
    if any(w in msg_low for w in ["tonight","night","evening","dinner","cocktail","after dark"]):
        return "night"
    if any(w in msg_low for w in ["morning","daytime","breakfast","early"]):
        return "morning"
    if any(w in msg_low for w in ["afternoon","lunch","noon"]):
        return "afternoon"
    return None


def _detect_event(msg):
    msg_low = msg.lower()
    for ev in ["sangeet","mehndi","haldi","reception","engagement"]:
        if ev in msg_low:
            return ev
    # Sports events — detect specific sport first, then fall back to gym
    if any(w in msg_low for w in [
        "gym", "workout", "exercise", "training", "athletic", "sports wear", "gym wear",
        "cricket", "football", "running", "sport", "badminton", "basketball", "tennis",
        "play cricket", "play football", "morning run", "going for a run",
    ]):
        if "cricket" in msg_low:  return "cricket"
        if "football" in msg_low or "soccer" in msg_low: return "football"
        if "running" in msg_low or "morning run" in msg_low: return "running"
        if "badminton" in msg_low or "basketball" in msg_low or "tennis" in msg_low: return "sport"
        return "gym"
    if any(w in msg_low for w in ["beach","pool","swim","seaside","summer outing"]):
        return "beach"
    for ev in ["wedding","party","office","work","casual","date","festival",
               "puja","farewell","brunch","club","concert","college","interview","dinner"]:
        if ev in msg_low:
            return ev
    if "tonight" in msg_low:
        return "evening"
    return None


def _detect_style_keyword(msg):
    msg_low = msg.lower()
    for style in sorted(STYLE_KEYWORDS.keys(), key=len, reverse=True):
        if style in msg_low:
            return style
    return None


def _detect_color_in_message(msg):
    msg_low = msg.lower()
    for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(color) + r"\b", msg_low):
            return color
    return None


def _detect_color_request(msg):
    msg_low = msg.lower()
    if re.search(r"\b(another|different|other|change)\b.{0,15}\bcolou?r\b", msg_low):
        return "__different__"
    if re.search(r"\bcolou?r\b.{0,15}\b(another|different|other|change)\b", msg_low):
        return "__different__"
    for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(color) + r"\b", msg_low):
            return color
    return None


def _detect_single_fashion_item(msg):
    msg_low = msg.lower()
    for keyword, category in FASHION_SINGLE_ITEM_MAP.items():
        if keyword in msg_low:
            return category, keyword
    return None, None


def _detect_single_skincare_item(msg):
    msg_low = msg.lower()
    for keyword, category in SKINCARE_SINGLE_MAP.items():
        if keyword in msg_low:
            return category, keyword
    return None, None


def _extract_last_category_from_history(history):
    for h in reversed(history[-8:]):
        if h.get("role") == "assistant":
            content = h.get("content","").lower()
            for kw, cat in FASHION_SINGLE_ITEM_MAP.items():
                if kw in content:
                    return cat
    return None


def _extract_last_color_from_history(history):
    for h in reversed(history[-8:]):
        content = h.get("content","").lower()
        for color in sorted(COLOR_KEYWORDS, key=len, reverse=True):
            if re.search(r"\b" + re.escape(color) + r"\b", content):
                return color
    return None


def _score(text, keywords):
    t = text.lower()
    return sum(1 for kw in keywords if kw in t)


def _hit(text, keywords):
    t = text.lower()
    return any(kw in t for kw in keywords)


def _search_wardrobe_for_item(wardrobe, query):
    query_low  = query.lower()
    color_hits = [c for c in COLOR_KEYWORDS if re.search(r"\b" + re.escape(c) + r"\b", query_low)]
    cat_hits   = [cat for kw, cat in FASHION_SINGLE_ITEM_MAP.items() if kw in query_low]

    ETHNIC_KEYWORDS = ["kurta","kurti","sherwani","lehenga","saree","sari","dupatta","anarkali",
                       "salwar","ethnic","indo-western","indowestern","bandhgala","nehru","churidar"]
    GYM_KEYWORDS    = ["gym","athletic","sport","track","jogger","dri-fit","workout","active"]

    has_ethnic_query = any(kw in query_low for kw in ETHNIC_KEYWORDS)
    has_gym_query    = any(kw in query_low for kw in GYM_KEYWORDS)

    results = []
    for item in wardrobe:
        full = " ".join([
            (item.get("color") or "").lower(),
            (item.get("item_name") or "").lower(),
            (item.get("category") or "").lower(),
            (item.get("style") or "").lower(),
            " ".join(item.get("occasion") or []).lower(),
        ])
        score = 0
        for c in color_hits:
            if c in full: score += 3
        for cat in cat_hits:
            if cat in full: score += 2
        if has_ethnic_query:
            for kw in ETHNIC_KEYWORDS:
                if kw in full: score += 4; break
            if item.get("category") == "shirt":
                for kw in ETHNIC_KEYWORDS:
                    if kw in (item.get("item_name","") + " " + item.get("style","")).lower():
                        score += 3; break
        if has_gym_query:
            for kw in GYM_KEYWORDS:
                if kw in full: score += 3; break
        for word in query_low.split():
            if len(word) > 2 and word in full: score += 1
        if score > 0:
            results.append((score, item))
    results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in results]


# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFIER v13
# ══════════════════════════════════════════════════════════════════════════════
def _classify(message, history, user_id):
    msg     = message.strip()
    msg_low = msg.lower()
    hist_text = " ".join(h.get("content","") for h in history[-6:]).lower()

    # ── 1. Special features ───────────────────────────────────────────────────
    if any(kw in msg_low for kw in STYLE_AESTHETIC_KEYWORDS):
        return {"action": "style_aesthetic", "topic": "fashion", "specific": msg}

    if _hit(msg_low, ["plan outfits for the week","weekly outfit","7 day outfit","outfit plan for week",
                       "plan my week","week plan","weekly plan","plan weekly"]):
        return {"action":"weekly_planner","topic":"fashion","specific":msg}

    if _hit(msg_low, ["gap analys","gap report","what.*missing","wardrobe gap","style gap","closet gap",
                       "what do i need","what am i missing","shopping list"]):
        return {"action":"gap_analysis","topic":"fashion","specific":msg}

    if _hit(msg_low, ["what colours suit","what colors suit","what color looks","what colour looks",
                       "colours for my skin","colors for my skin","best color for me","best colour for me"]):
        return {"action":"color_theory","topic":"fashion","specific":msg}

    if _hit(msg_low, ["grooming","beard style","beard trim","hairstyle","haircut","hair tip"]):
        return {"action":"grooming","topic":"fashion","specific":msg}

    if _hit(msg_low, ["trend","trending","what's in","what is in style","latest fashion","what's hot"]):
        return {"action":"trend","topic":"fashion","specific":msg}

    if _hit(msg_low, ["what is old money","explain old money","what is streetwear","explain streetwear",
                       "what is boho","explain my style","style guide"]):
        return {"action":"style_explain","topic":"fashion","specific":msg}

    # ── 2. CLOSET keywords ────────────────────────────────────────────────────
    if _hit(msg_low, _CK):
        event = _detect_event(msg_low)
        if _hit(msg_low, ["is there","do i have","do i own","have i got"]):
            return {"action":"closet_search","topic":"closet","specific":msg}
        color_in_msg = _detect_color_in_message(msg_low)
        if color_in_msg and _hit(msg_low, ["outfit","give","based on","using","style","look","show","color in","colour in"]):
            return {"action":"closet_color","topic":"closet","specific":msg,
                    "color_filter":color_in_msg,"event":event}
        if _hit(msg_low, ["show my","what's in","list my","wardrobe summary","what i own","what do i have"]) and not event:
            return {"action":"closet_summary","topic":"closet","specific":msg}
        return {"action":"closet","topic":"closet","specific":msg,"event":event}

    # ── 2b. Ethnic / kurta → check closet first ───────────────────────────────
    ETHNIC_QUERY_WORDS = ["kurta","kurti","sherwani","lehenga","saree","sari","ethnic","anarkali","salwar"]
    if any(kw in msg_low for kw in ETHNIC_QUERY_WORDS):
        event = _detect_event(msg_low) or "festival"
        try:
            if get_wardrobe(user_id):
                return {"action":"closet","topic":"closet","specific":msg,"event":event}
        except Exception:
            pass
        return {"action":"products_fashion","topic":"fashion","specific":msg,"single_cat":"ethnic","event":event}

    # ── 3. Event → closet if wardrobe exists ─────────────────────────────────
    event = _detect_event(msg_low)
    if event:
        try:
            if get_wardrobe(user_id):
                return {"action":"closet","topic":"closet","specific":msg,"event":event}
        except Exception:
            pass

    # ── 4. Analysis ───────────────────────────────────────────────────────────
    if _hit(msg_low, ["my face","my skin","my tone","face shape","scan result",
                       "what did you detect","tell me about my","my condition","what is my profile"]):
        return {"action":"analysis","topic":"general","specific":""}

    # ── 5. Color follow-up ────────────────────────────────────────────────────
    color_req = _detect_color_request(msg_low)
    if color_req:
        last_cat = _extract_last_category_from_history(history)
        last_bot = next((h.get("content","") for h in reversed(history[-6:]) if h.get("role")=="assistant"), "")
        if "wardrobe" in last_bot.lower() or "closet" in last_bot.lower():
            return {"action":"closet_color","topic":"closet","specific":msg,
                    "color_filter": color_req if color_req != "__different__" else None,"event":None}
        return {"action":"products_fashion","topic":"fashion","specific":msg,
                "single_cat":last_cat or "shirt","event":None,"color_override":color_req}

    # ── 6. Skincare ───────────────────────────────────────────────────────────
    sk_cat, sk_item = _detect_single_skincare_item(msg_low)
    sk_score = _score(msg_low, _SK)
    fk_score = _score(msg_low, _FK)

    if sk_score > 0 and fk_score == 0:
        is_q = _hit(msg_low, ["how","what","why","explain","tell me","which","when","is it","does"])
        is_p = _hit(msg_low, ["give","recommend","suggest","show","buy","find","best","good","want"])
        if is_q and not is_p:
            return {"action":"explain","topic":"skincare","specific":msg}
        return {"action":"products_skin","topic":"skincare","specific":msg,"category":sk_cat}

    # ── 7. Style keywords ─────────────────────────────────────────────────────
    style_kw = _detect_style_keyword(msg_low)
    if style_kw:
        return {"action":"products_fashion","topic":"fashion","specific":msg,
                "single_cat":None,"event":event,"style_keyword":style_kw}

    # ── 8. Fashion ────────────────────────────────────────────────────────────
    fk_cat, fk_item = _detect_single_fashion_item(msg_low)
    if fk_score > 0 or fk_cat:
        is_q = _hit(msg_low, ["how","what","why","explain","tell me","which","when"])
        is_p = _hit(msg_low, ["give","show","best","suggest","recommend","find","want","buy"])
        if fk_cat and not event:
            return {"action":"products_fashion","topic":"fashion","specific":fk_item,"single_cat":fk_cat,"event":None}
        if event:
            return {"action":"products_fashion","topic":"fashion","specific":msg,"single_cat":None,"event":event}
        if not is_q or is_p:
            return {"action":"products_fashion","topic":"fashion","specific":msg,"single_cat":None,"event":event}
        return {"action":"explain","topic":"fashion","specific":msg}

    # ── 9. Both ───────────────────────────────────────────────────────────────
    if sk_score > 0 and fk_score > 0:
        return {"action":"products_both","topic":"both","specific":msg}

    # ── 10. Affirmation ───────────────────────────────────────────────────────
    if _hit(msg_low, ["yes","yeah","sure","ok","okay","definitely","please","go ahead","yep","yup"]) and len(msg.split()) <= 4:
        if "closet" in hist_text or "wardrobe" in hist_text:
            return {"action":"closet","topic":"closet","specific":""}
        if _score(hist_text, _FK) >= _score(hist_text, _SK):
            return {"action":"products_fashion","topic":"fashion","specific":""}
        if _score(hist_text, _SK) > 0:
            return {"action":"products_skin","topic":"skincare","specific":"","category":None}
        return {"action":"chat","topic":"general","specific":""}

    return {"action":"chat","topic":"general","specific":""}


# ══════════════════════════════════════════════════════════════════════════════
# GENDER-AWARE ACCESSORIES
# ══════════════════════════════════════════════════════════════════════════════
def _get_accessories_for_gender(gender, skin_tone, event, is_night, is_ethnic):
    """Returns accessory search queries appropriate for gender."""
    gl   = _gender_label(gender)
    male = _is_male(gender)

    if male:
        if is_ethnic:
            return {
                "watch":       f"gold ethnic watch men India {event}",
                "accessories": f"gold kada bracelet ethnic men India {event}",
            }
        elif is_night:
            return {
                "watch":       f"men formal gold watch night {event} India",
                "bracelet":    f"men chain bracelet gold silver India",
                "sunglasses":  f"men aviator sunglasses India",
            }
        else:
            return {
                "watch":       f"men {'gold' if skin_tone == 'dark' else 'silver'} casual watch India",
                "bracelet":    f"men beaded bracelet casual India",
                "sunglasses":  f"men wayfarer sunglasses India",
            }
    else:
        if is_ethnic:
            return {
                "accessories": f"gold jhumka bangles jewellery women ethnic India {event}",
            }
        elif is_night:
            return {
                "necklace": f"gold statement necklace women night India",
                "earrings": f"gold hoop drop earrings women India",
            }
        else:
            return {
                "necklace": f"delicate gold necklace women India",
                "earrings": f"gold stud hoop earrings women India",
            }


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _fetch_fashion_single(skin_tone, face_shape, gender, category, query_hint="",
                           color_override=None, last_color=None):
    import random
    tone_key   = skin_tone.lower() if skin_tone.lower() in TONE_COLOR_POOL else "medium"
    gl         = _gender_label(gender)
    color_pool = TONE_COLOR_POOL[tone_key].get(category, TONE_COLOR_POOL[tone_key].get("shirt",[]))

    if color_override == "__different__":
        avail = [c for c in color_pool if last_color and last_color.lower() not in c.lower()]
        chosen_color = random.choice(avail) if avail else random.choice(color_pool)
    elif color_override and color_override != "__different__":
        chosen_color = color_override
    else:
        chosen_color = random.choice(color_pool[:4])

    GARMENT_MAP = {
        "tshirt":"t-shirt","t shirt":"t-shirt","t-shirt":"t-shirt","polo":"polo shirt",
        "kurta":"kurta","hoodie":"hoodie","shirt":"shirt","pant":"trousers","pants":"trousers",
        "jeans":"jeans","trouser":"trousers","chino":"chinos","shorts":"shorts",
        "shoe":"shoes","shoes":"shoes","sneaker":"sneakers","sandal":"sandals","boot":"boots",
        "loafer":"loafers","heel":"heels","dress":"dress","gown":"gown","skirt":"skirt",
        "top":"top","blouse":"blouse","kurti":"kurti","watch":"watch","bracelet":"bracelet",
        "sunglasses":"sunglasses","necklace":"necklace","earring":"earrings",
        "jacket":"jacket","blazer":"blazer","sweater":"sweater",
    }
    hint_lower   = (query_hint or "").lower().strip()
    garment_word = GARMENT_MAP.get(hint_lower)
    if not garment_word:
        for kw, term in GARMENT_MAP.items():
            if kw in hint_lower:
                garment_word = term; break
    if not garment_word:
        garment_word = {"shirt":"t-shirt","pants":"trousers","shoes":"sneakers",
                        "top":"top","dress":"dress","watch":"watch","bracelet":"bracelet",
                        "sunglasses":"sunglasses","blazer":"blazer","jacket":"jacket",
                        "ethnic":"kurta" if _is_male(gender) else "kurti"}.get(category, category)

    raw_query = f"{chosen_color} {garment_word} {gl} India".strip().replace("  "," ")
    print(f"👕 SINGLE FETCH: cat={category} garment={garment_word} color={chosen_color}")
    prods = get_product_recommendations(raw_query, category)
    return {category: prods[:3]}, raw_query


def _fetch_fashion_full_outfit(skin_tone, face_shape, gender, event=None,
                                time_of_day=None, style_keyword=None, user_message=""):
    import random
    gl       = _gender_label(gender)
    tone_key = skin_tone.lower() if skin_tone.lower() in TONE_COLOR_POOL else "medium"

    if event in ("gym", "cricket", "football", "running", "sport"):
        SPORT_LABELS = {
            "gym":"💪 Gym Ready","cricket":"🏏 Cricket Ready",
            "football":"⚽ Football Ready","running":"🏃 Running Ready","sport":"🏅 Sport Ready",
        }
        GYM_COLORS = {
            "dark":   ["electric blue","bright yellow","coral","fuchsia","lime green"],
            "medium": ["teal","burnt orange","olive green","burgundy","navy blue"],
            "light":  ["mint green","sky blue","soft pink","lavender","white"],
        }
        color = random.choice(GYM_COLORS.get(tone_key, GYM_COLORS["medium"]))
        ev = event or "gym"
        SHIRT_Q = {
            "gym":     f"Nike Puma {color} dry fit gym t-shirt athletic performance men India",
            "cricket": f"{color} cricket jersey dry fit sport t-shirt men India",
            "football":f"{color} football jersey dry fit sport t-shirt men India",
            "running": f"{color} lightweight running t-shirt dry fit men India",
            "sport":   f"{color} dry fit sports t-shirt athletic performance men India",
        }
        PANTS_Q = {
            "gym":     "Puma Nike track pants jogger training slim fit men black navy India",
            "cricket": "cricket whites track pants sports trousers men India",
            "football":"football shorts track pants sport men India",
            "running": "lightweight running shorts track pants men India",
            "sport":   "athletic track pants sports training men India",
        }
        SHOES_Q = {
            "gym":     "Nike Adidas running shoes training men India lightweight",
            "cricket": "cricket shoes sport rubber sole men India",
            "football":"sport shoes training athletic men India",
            "running": "lightweight running shoes cushioned men India Nike Adidas",
            "sport":   "sport shoes training athletic men India",
        }
        products = {}
        if _is_male(gender):
            queries = {
                "gym_tshirt":   SHIRT_Q.get(ev, SHIRT_Q["gym"]),
                "track_pants":  PANTS_Q.get(ev, PANTS_Q["gym"]),
                "sports_shoes": SHOES_Q.get(ev, SHOES_Q["gym"]),
            }
        else:
            queries = {
                "gym_tshirt":   f"Nike Puma {color} sports crop top women {ev} India athletic",
                "track_pants":  "Puma Nike gym leggings tights high waist women India training",
                "sports_shoes": "Nike Adidas running shoes women India training lightweight",
            }
        for cat, q in queries.items():
            try:
                prods = get_product_recommendations(q, cat)
                if prods: products[cat] = prods[:4]
            except Exception: pass
        return products, queries, SPORT_LABELS.get(ev, "🏅 Sport Ready")

    if event == "beach":
        products = {}
        if _is_male(gender):
            queries = {
                "beach_shirt": f"linen beach shirt floral relaxed fit men India summer Myntra",
                "swim_shorts": f"quick dry swim shorts beach men India colorful HRX Puma",
                "flip_flops":  f"flip flops Havaianas beach sandals men India comfortable",
            }
        else:
            queries = {
                "beach_shirt": f"floral beach dress sundress boho women India summer Myntra",
                "swim_shorts": f"swimsuit bikini one piece beach women India",
                "flip_flops":  f"flip flops Havaianas beach flat sandals women India",
            }
        for cat, q in queries.items():
            try:
                prods = get_product_recommendations(q, cat)
                if prods: products[cat] = prods[:4]
            except Exception: pass
        return products, queries, "🏖️ Beach Vibes"

    if event in ETHNIC_EVENTS:
        ETHNIC_COLORS = {
            "dark":   ["saffron yellow","electric blue","magenta","emerald green","coral red","fuchsia"],
            "medium": ["mustard","teal","burgundy","forest green","terracotta","wine red"],
            "light":  ["pastel pink","ivory","powder blue","mint","champagne","lilac"],
        }
        color = random.choice(ETHNIC_COLORS.get(tone_key, ETHNIC_COLORS["medium"]))
        products = {}
        if _is_male(gender):
            MEN_ETHNIC = {
                "wedding":"sherwani indo-western","sangeet":"silk kurta set",
                "mehndi":"light kurta yellow green","haldi":"yellow cotton kurta",
                "reception":"bandhgala nehru jacket sherwani","engagement":"kurta blazer indo-western",
                "puja":"cotton kurta plain","festival":"festive embroidered kurta",
            }
            garment = MEN_ETHNIC.get(event, "kurta ethnic")
            queries = {
                "ethnic":      f"{color} {garment} men India",
                "shoes":       f"kolhapuri mojri ethnic shoes men India {event}",
                "accessories": f"gold watch kada bracelet men ethnic India {event}",
            }
        else:
            WOMEN_ETHNIC = {
                "wedding":"lehenga choli saree wedding","sangeet":"lehenga sharara sangeet vibrant",
                "mehndi":"kurti lehenga mehndi yellow green","haldi":"kurti haldi yellow ceremony",
                "reception":"heavy lehenga saree reception formal","engagement":"lehenga sharara engagement pastel",
                "puja":"cotton kurti saree puja","festival":"anarkali kurti festive embroidered",
            }
            garment = WOMEN_ETHNIC.get(event, "ethnic kurti lehenga")
            queries = {
                "ethnic":      f"{color} {garment} women India",
                "shoes":       f"heels juttis ethnic sandals women India {event}",
                "accessories": f"gold jewellery jhumka bangles women ethnic India {event}",
            }
        for cat, q in queries.items():
            try:
                prods = get_product_recommendations(q, cat)
                if prods: products[cat] = prods[:4]
            except Exception: pass
        return products, queries, f"🎉 {event.capitalize()} Look"

    products, outfit_queries, label, _ = generate_outfit_for_context(
        skin_tone=skin_tone, face_shape=face_shape, gender=gender,
        user_message=user_message or f"{event or 'casual'} outfit",
        event=event, time_of_day=time_of_day,
    )
    return products, outfit_queries, label


def _fetch_skin_products(skin_tone, conditions, specific_cat=None):
    rag_data    = generate_skin_recommendation(skin_tone, conditions)
    ingredients = rag_data.get("ingredients",{})
    routine     = rag_data.get("routine",{})
    if specific_cat and specific_cat in ingredients:
        prods = get_product_recommendations(ingredients[specific_cat], specific_cat)
        return {specific_cat: prods[:3]}, routine, ingredients
    products = {}
    for cat, q in ingredients.items():
        try:
            prods = get_product_recommendations(q, cat)
            if prods:
                products[cat] = prods[:3]
        except Exception:
            pass
    return products, routine, ingredients


# ══════════════════════════════════════════════════════════════════════════════
# PATCHED: _extract_user_id helper
# ══════════════════════════════════════════════════════════════════════════════
def _extract_user_id(user: dict) -> str:
    """
    Extract the canonical user_id from the user context object.
    Priority: userId (from JWT /auth/me) > user_id > name > "guest"
    """
    return (
        user.get("userId") or
        user.get("user_id") or
        user.get("name") or
        "guest"
    ).strip()


# ══════════════════════════════════════════════════════════════════════════════
# PATCHED: DUAL OUTFIT PLANNER (event-filtered wardrobe)
# ══════════════════════════════════════════════════════════════════════════════
def _plan_dual_outfit(user_id, message, event, time_of_day, skin_tone, face_shape, gender, user_profile):
    """
    Returns a dual outfit response:
    - closet: outfit from wardrobe (event-filtered — gym shorts never at festival, etc.)
    - new_products: fresh outfit to buy based on skin+gender+event
    - event_label: display label

    CRITICAL RULES:
    - closet plan uses event-appropriate wardrobe items only (get_event_appropriate_wardrobe)
    - new products: gym→athletic only, ethnic events→ethnic only
    - gender-aware: male never gets necklace/earrings; female never gets watch/bracelet/sunglasses
    """
    all_wardrobe = get_wardrobe(user_id)
    is_night     = time_of_day in ("night", "evening")
    event_type   = event or "casual"
    ev_info      = EVENT_REQUIREMENTS.get(event_type, EVENT_REQUIREMENTS.get("casual", {}))
    is_ethnic    = event_type in ETHNIC_EVENTS
    is_athletic  = event_type in ATHLETIC_EVENTS
    ev_icon      = ev_info.get("icon", "✦")
    ev_vibe      = ev_info.get("vibe", "")
    gl           = _gender_label(gender)

    # ── 1. Wardrobe outfit (plan_outfit_for_event already uses event-filtered wardrobe internally) ─
    closet_result = {}
    if all_wardrobe:
        outfit_data = plan_outfit_for_event(user_id, event_type, {
            "skinTone": skin_tone, "face_shape": face_shape, "gender": gender,
        })
        closet_result = outfit_data
    else:
        closet_result = {
            "available_items": {}, "missing_categories": list(ev_info.get("cats", [])),
            "outfit_plan": "Your wardrobe is empty! Upload clothes in the Closet tab.",
            "event_icon": ev_icon, "event_vibe": ev_vibe,
        }

    # ── 2. New product picks ──────────────────────────────────────────────────
    new_products, _, _ = _fetch_fashion_full_outfit(
        skin_tone, face_shape, gender, event_type, time_of_day, user_message=message
    )

    # Add gender-aware accessories (only for non-athletic events)
    if not is_athletic:
        acc_queries = _get_accessories_for_gender(gender, skin_tone, event_type, is_night, is_ethnic)
        for cat, q in acc_queries.items():
            if cat not in new_products:
                try:
                    prods = get_product_recommendations(q, cat)
                    if prods and not (len(prods) == 1 and "Search:" in prods[0].get("title", "")):
                        new_products[cat] = prods[:4]
                except Exception:
                    pass

        # Shoes if missing
        wardrobe_cats = {i["category"] for i in all_wardrobe} if all_wardrobe else set()
        if "shoes" not in wardrobe_cats and "shoes" not in new_products:
            is_male = _is_male(gender)
            if is_ethnic:
                shoe_q = f"{'kolhapuri mojri ethnic shoes men' if is_male else 'heels juttis ethnic sandals women'} India"
            elif is_night:
                shoe_q = f"{'black leather loafers men' if is_male else 'black block heels women'} India"
            else:
                shoe_q = f"{'white sneakers men' if is_male else 'white platform sneakers women'} India"
            try:
                prods = get_product_recommendations(shoe_q, "shoes")
                if prods: new_products["shoes"] = prods[:4]
            except Exception:
                pass

    event_label = f"{ev_icon} {event_type.capitalize()} — {ev_vibe}" if ev_vibe else f"{ev_icon} {event_type.capitalize()}"

    return {
        "closet":       closet_result,
        "new_products": new_products,
        "event_label":  event_label,
    }


# ══════════════════════════════════════════════════════════════════════════════
# WEEKLY OUTFIT PLANNER
# ══════════════════════════════════════════════════════════════════════════════
def _build_weekly_plan(user_id, skin_tone, face_shape, gender, day_events: dict) -> dict:
    """
    day_events: { "Monday": "casual", "Tuesday": "office", ... }
    Returns: { days: [ { day, event, icon, outfit, tip, wardrobe_items } ] }
    v14: Now includes wardrobe_items (with images) for each day
    """
    wardrobe = get_wardrobe(user_id)
    gl       = _gender_label(gender)
    days_out = []

    DAYS_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    COLOR_TIPS = {
        "dark":   ["electric blue", "emerald green", "gold", "royal blue", "fuchsia"],
        "medium": ["mustard", "terracotta", "burgundy", "teal", "forest green"],
        "light":  ["lavender", "sage green", "blush pink", "navy blue", "ivory"],
    }
    best_colors = COLOR_TIPS.get(skin_tone.lower(), COLOR_TIPS["medium"])

    for day in DAYS_ORDER:
        event = day_events.get(day, "casual")
        ev_info = EVENT_REQUIREMENTS.get(event, EVENT_REQUIREMENTS.get("casual",{}))
        ev_icon = ev_info.get("icon","👕")
        ev_vibe = ev_info.get("vibe","")

        outfit_text    = ""
        wardrobe_items = []

        if wardrobe:
            try:
                outfit_data = plan_outfit_for_event(user_id, event, {
                    "skinTone": skin_tone, "face_shape": face_shape, "gender": gender,
                })
                outfit_text = outfit_data.get("outfit_plan", "")
                available   = outfit_data.get("available_items", {})

                seen_ids = set()
                for v in available.values():
                    if v and v.get("item_id") not in seen_ids:
                        seen_ids.add(v.get("item_id"))
                        wardrobe_items.append({
                            "item_name": v.get("item_name",""),
                            "color":     v.get("color",""),
                            "category":  v.get("category",""),
                            "image_url": v.get("image_url",""),
                        })

                if not outfit_text:
                    if wardrobe_items:
                        parts = [f"{i['color']} {i['item_name']}" for i in wardrobe_items[:3]]
                        outfit_text = " + ".join(parts)
                    else:
                        outfit_text = f"Style your best {event} look"
            except Exception:
                outfit_text = f"Style your best {event} look"
        else:
            outfit_text = f"{ev_vibe or event} outfit"

        days_out.append({
            "day":            day,
            "event":          event,
            "icon":           ev_icon,
            "vibe":           ev_vibe,
            "outfit":         outfit_text,
            "tip":            f"Power colors for {skin_tone} skin: {', '.join(best_colors[:3])}",
            "wardrobe_items": wardrobe_items,
        })

    return {"days": days_out}


# ══════════════════════════════════════════════════════════════════════════════
# STYLIST MESSAGES
# ══════════════════════════════════════════════════════════════════════════════
def _stylist_wardrobe_message(name, skin_tone, face_shape, gender, message, available, missing_cats, event, time_of_day):
    gl       = _gender_label(gender)
    is_night = time_of_day in ("night","evening")
    avail_str = ", ".join([f"{i.get('color','')} {i.get('item_name','')}" for i in available.values()]) if available else "your items"
    color_tip = {"dark":"jewel tones, bold brights — gold accessories glow","medium":"earthy tones, mustard, burgundy","light":"pastels, soft neutrals — silver or rose gold"}.get(skin_tone.lower(),"")
    face_tip  = {"square":"open collar or V-neck","round":"V-necks and vertical lines","heart":"scoop neck or wide collar","oval":"any neckline"}.get(face_shape.lower(),"")
    prompt = f"""World-class personal stylist. CLIENT: {name} | {skin_tone} skin | {face_shape} face | {gl}
EVENT: {event or 'occasion'} | {'evening/night' if is_night else 'daytime'}
WARDROBE: {avail_str}
MISSING: {', '.join(missing_cats) if missing_cats else 'nothing major'}
COLOR TIP: {color_tip} | FACE TIP: {face_tip}

3-4 sentences: (1) EXACTLY how to wear the pieces — specific: "Wear the maroon shirt open over the black tee", "Roll cuffs twice" (2) WHY these colors work for {skin_tone} skin (3) What accessories complete this (4) One punchy verdict.
Under 100 words. No bullet lists. Sound like a real designer."""
    return llm.invoke(prompt).content


def _stylist_fashion_message(name, skin_tone, face_shape, gender, message, outfit_label,
                              event=None, time_of_day=None, style_keyword=None, rag_ctx=""):
    gl        = _gender_label(gender)
    tone_desc = {"dark":"jewel tones, bold brights, electric blue, gold","medium":"earthy tones, mustard, burgundy, terracotta","light":"pastels, sage, blush, mint"}.get(skin_tone,"complementary tones")
    face_desc = {"oval":"oval face: wear anything boldly","round":"round face: V-necks and vertical lines","square":"square face: rounded collars","heart":"heart face: boat necks"}.get(face_shape,"")
    style_ctx = f"Style: {style_keyword} aesthetic — nail it" if style_keyword else ""
    event_ctx = f"Event: {event} ({time_of_day})" if event else ""

    if event == "gym":
        prompt = f"""Fitness fashion stylist. CLIENT: {name} | {skin_tone} skin | {gl}
3 sentences: (1) Exact gym wear color combination for {skin_tone} skin — e.g. "Electric blue compression tee + black joggers" — name the color and WHY it works (2) Fabric tip: dry-fit, moisture-wicking, compression for performance (3) "Gym picks below ↓"
Max 70 words. Be specific about color combos, not generic."""
        return llm.invoke(prompt).content

    if event == "beach":
        prompt = f"""Summer fashion stylist. CLIENT: {name} | {skin_tone} skin | {gl}
3 sentences: (1) Best beach outfit colors for {skin_tone} skin in sunlight — specific shades (2) Fabric tip: linen or quick-dry (3) "Beach-ready picks below ↓"
Max 70 words."""
        return llm.invoke(prompt).content

    if event in ETHNIC_EVENTS:
        prompt = f"""Luxury Indian fashion stylist — Sabyasachi × Manish Malhotra. CLIENT: {name} | {skin_tone} skin | {gl} | EVENT: {event}
3-4 sentences: (1) Exact ethnic wear — with specific color for {skin_tone} skin at a {event} (2) Styling tip: dupatta/collar/jewelry (3) Footwear tip (4) "Curated picks below ↓"
Max 90 words."""
        return llm.invoke(prompt).content

    prompt = f"""World's best personal stylist. CLIENT: {name} | {skin_tone} skin → {tone_desc} | {face_desc} | {gl}
{event_ctx} {style_ctx}
USER SAID: "{message}" | CHOSEN OUTFIT: {outfit_label}

3-4 sentences: (1) What you picked and WHY for their skin — name colors specifically (2) {"How this nails the " + style_keyword + " aesthetic" if style_keyword else "Event context + what this outfit communicates"} (3) Styling tip: roll sleeves/tuck/layer (4) Punchy verdict.
Max 90 words. No lists."""
    return llm.invoke(prompt).content


def _stylist_single_item_message(name, skin_tone, gender, item_name, rag_ctx=""):
    gl     = _gender_label(gender)
    prompt = f"""World's best personal stylist. CLIENT: {name} | {skin_tone} skin | {gl}
ITEM: {item_name}
2 sentences: (1) Exact color/shade that makes {skin_tone} skin POP (2) "Here are my top picks ↓"
Under 50 words."""
    return llm.invoke(prompt).content


def _stylist_color_followup_message(name, skin_tone, gender, item_name, color):
    gl         = _gender_label(gender)
    color_desc = "a fresh new color" if color == "__different__" else color
    prompt = f"""World's best personal stylist. CLIENT: {name} | {skin_tone} skin | {gl}
WANT: {item_name} in {color_desc}
2 sentences: (1) Why this color is a power move for {skin_tone} skin (2) "Here are my top picks ↓"
Under 45 words."""
    return llm.invoke(prompt).content


def _stylist_skin_message(name, skin_tone, conditions_str, specific_item=None, rag_ctx=""):
    if specific_item:
        prompt = f"""Dermatologist. CLIENT: {name}, {skin_tone} skin, {conditions_str}.
ITEM: {specific_item}
2 sentences: what it does for their conditions + why right for {skin_tone} skin. End: "Here are the best options ↓" Under 55 words."""
    else:
        prompt = f"""Dermatologist. CLIENT: {name} | {skin_tone} skin | {conditions_str}
2-3 sentences: main concern + KEY ingredient + why it works for {skin_tone} skin.
End: "Here are my top picks ↓" Under 75 words. Name ingredients."""
    return llm.invoke(prompt + (f"\nKNOWLEDGE:\n{rag_ctx[:300]}" if rag_ctx else "")).content


def _stylist_wardrobe_search_message(name, skin_tone, face_shape, gender, query, found_items, not_found):
    gl = _gender_label(gender)
    if found_items:
        items_desc = ", ".join([f"{i.get('color','')} {i.get('item_name','')}" for i in found_items[:3]])
        prompt = f"""World-class personal stylist. CLIENT: {name} | {skin_tone} skin | {gl}
ASKED: "{query}" | FOUND: {items_desc}
3 sentences: (1) Yes, name items (2) Specific styling tip (3) Why it works for {skin_tone} skin.
Under 70 words. No lists."""
    else:
        prompt = f"""World-class personal stylist. CLIENT: {name} | {skin_tone} skin | {gl}
ASKED: "{query}" | NOT FOUND in wardrobe.
2-3 sentences: (1) Not in wardrobe (2) Recommend specific color/style for {skin_tone} skin (3) "Want me to find some options?"
Under 60 words."""
    return llm.invoke(prompt).content


def _stylist_closet_color_message(name, skin_tone, gender, color, found_items, event):
    gl        = _gender_label(gender)
    items_str = ", ".join([f"{i.get('color','')} {i.get('item_name','')}" for i in found_items]) if found_items else "none"
    if found_items:
        prompt = f"""World-class personal stylist. CLIENT: {name} | {skin_tone} skin | {gl}
WANT: outfits using {color} wardrobe pieces | EVENT: {event or 'general'}
FOUND: {items_str}

3-4 sentences: (1) Name the {color} pieces and HOW to style them (2) What other colors pair with {color} for {skin_tone} skin (3) Best accessories (4) One punchy verdict.
Under 90 words. No lists."""
    else:
        prompt = f"""World-class personal stylist. CLIENT: {name} | {skin_tone} skin | {gl}
WANT: {color} outfits from wardrobe. RESULT: No {color} items found.

2-3 sentences: (1) No {color} in wardrobe (2) Recommend a specific {color} piece for {skin_tone} skin (3) "Want me to find some options?"
Under 60 words."""
    return llm.invoke(prompt).content


# ══════════════════════════════════════════════════════════════════════════════
# STYLE AESTHETIC HANDLER
# ══════════════════════════════════════════════════════════════════════════════
def _handle_style_aesthetic(name, skin_tone, face_shape, gender, message):
    """
    Handles style aesthetic requests like Old Money, Streetwear, Minimalist.
    Returns products specific to that style + skin tone + gender.
    """
    import random
    msg_low  = message.lower()
    gl       = "men" if gender.lower() not in ("female","women","woman","girl","f") else "women"
    tone_key = skin_tone.lower() if skin_tone.lower() in ["light","medium","dark"] else "medium"

    detected = None
    for key in STYLE_AESTHETICS:
        if key in msg_low:
            detected = key
            break
    if not detected:
        if "boho" in msg_low:                                   detected = "boho"
        elif "hype" in msg_low:                                 detected = "hypebeast"
        elif "indo" in msg_low:                                 detected = "indo western"
        elif "preppy" in msg_low or "prep" in msg_low:         detected = "preppy"
        elif "casual" in msg_low and "smart" in msg_low:       detected = "smart casual"
        elif "minimal" in msg_low:                              detected = "minimalist"

    if not detected:
        return None

    aesthetic = STYLE_AESTHETICS[detected]
    pieces    = aesthetic.get(f"{gl}_pieces") or aesthetic.get("men_pieces", {})

    tone_colors = {
        "dark":   ["electric blue", "emerald", "royal blue", "saffron yellow", "coral red"],
        "medium": ["mustard", "burgundy", "teal", "forest green", "terracotta"],
        "light":  ["pastel blue", "mint", "lavender", "sage", "blush pink"],
    }.get(tone_key, ["navy", "white", "grey"])

    color    = random.choice(tone_colors[:3])
    products = {}

    for cat, base_query in pieces.items():
        query = f"{color} {base_query}" if cat in ("shirt", "top", "ethnic") and color not in base_query else base_query
        try:
            prods = get_product_recommendations(query, cat)
            if prods:
                products[cat] = prods[:4]
        except Exception:
            pass

    rag_ctx = _rag(_fashion_ret, f"{detected} style {skin_tone} skin {gl}")
    prompt  = f"""World-class fashion editor and personal stylist. CLIENT: {name} | {skin_tone} skin | {face_shape} face | {gl}
STYLE AESTHETIC: {detected.upper()} — {aesthetic["desc"]}

USER ASKED: "{message}"
KNOWLEDGE: {rag_ctx}

4-5 sentences:
(1) Define {detected} in one memorable, opinionated sentence
(2) Exact colors for {skin_tone} skin within this aesthetic — be specific
(3) Top 3 key pieces they MUST have
(4) One piece to AVOID completely
(5) "Here are your curated {detected} picks ↓"

Max 120 words. Sound like a real editor, not a chatbot. Be specific."""

    try:
        stylist_msg = llm.invoke(prompt).content
    except Exception:
        stylist_msg = f"Here's your complete **{detected}** style guide, {name}! Curated for {skin_tone} skin."

    return {
        "message":        stylist_msg,
        "products":       products,
        "product_type":   "fashion",
        "outfit_label":   f"{detected.title()} Aesthetic",
        "style_aesthetic": detected,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY
# ══════════════════════════════════════════════════════════════════════════════
def chat_with_ai(message: str, user: dict, history: list = None) -> dict:
    history = history or []

    skin_tone  = user.get("skinTone", "medium")
    face_shape = user.get("face_shape", "oval")
    conditions = user.get("conditions", [])
    gender     = user.get("gender", "male")
    name       = user.get("name", "there")

    # PATCHED: use _extract_user_id() for safe, priority-ordered ID extraction
    user_id = _extract_user_id(user)

    # Weekly planner special: if _weekly_plan passed
    _weekly_plan_data = user.get("_weekly_plan", None)

    seen, unique_conds = set(), []
    for c in conditions:
        cc = c.lower().strip()
        if cc and cc not in seen:
            seen.add(cc); unique_conds.append(cc)
    conds_str = ", ".join(unique_conds) or "normal skin"

    hist_block = ""
    if history:
        hist_block = "\nCONVERSATION HISTORY:\n"
        for h in history[-6:]:
            role = "User" if h.get("role") == "user" else "Stylist"
            hist_block += f"{role}: {h.get('content','')}\n"

    clf            = _classify(message, history, user_id)
    action         = clf["action"]
    topic          = clf["topic"]
    specific       = clf.get("specific","")
    category       = clf.get("category",None)
    single_cat     = clf.get("single_cat",None)
    event          = clf.get("event",None) or _detect_event(message)
    color_override = clf.get("color_override",None)
    color_filter   = clf.get("color_filter",None)
    style_keyword  = clf.get("style_keyword",None)

    time_from_msg = _detect_time_from_message(message)
    time_of_day   = time_from_msg or _get_time_context()
    gl            = _gender_label(gender)

    print(f"🤖 ACTION={action} | TOPIC={topic} | EVENT={event} | TIME={time_of_day} | GENDER={gender} | STYLE={style_keyword}")

    result = {"intent": topic, "action": action}

    # ── WEEKLY PLANNER ────────────────────────────────────────────────────────
    if action == "weekly_planner" or _weekly_plan_data:
        day_events = _weekly_plan_data or {
            "Monday":"casual","Tuesday":"office","Wednesday":"college",
            "Thursday":"casual","Friday":"party","Saturday":"date","Sunday":"casual"
        }
        weekly_plan = _build_weekly_plan(user_id, skin_tone, face_shape, gender, day_events)
        result["message"]     = f"Here's your personalised **7-day outfit plan**, {name}! Each look is picked from your wardrobe and tailored to your **{skin_tone} skin tone**."
        result["weekly_plan"] = weekly_plan
        return result

    # ── GAP ANALYSIS ──────────────────────────────────────────────────────────
    if action == "gap_analysis":
        gap_data = style_gap_analysis(user_id)
        gaps     = gap_data.get("gaps",{})
        ready    = gap_data.get("ready_events",[])
        result["message"]      = f"Here's your **Style Gap Report**, {name}! You're ready for **{len(ready)} events** and missing items for **{len(gaps)} others**. I've highlighted what to buy below."
        result["gap_analysis"] = gap_data
        return result

    # ── STYLE AESTHETIC ───────────────────────────────────────────────────────
    if action == "style_aesthetic":
        aesthetic_result = _handle_style_aesthetic(name, skin_tone, face_shape, gender, message)
        if aesthetic_result:
            result.update(aesthetic_result)
            return result
        action = "products_fashion"

    # ── EXPLAIN ───────────────────────────────────────────────────────────────
    if action == "explain":
        rag_ctx = _rag(_skin_ret if topic=="skincare" else _fashion_ret,
                       f"{message} {conds_str} {skin_tone}")
        prompt = f"""FaceFit AI — expert skincare & fashion advisor.
USER: {name} | {skin_tone} skin | {conds_str} | {gl}
{hist_block}
KNOWLEDGE: {rag_ctx}
QUESTION: "{message}"
Answer clearly, personally (max 100 words). One actionable tip.
If products would help: "Want me to find the best products for this?" """
        result["message"] = llm.invoke(prompt).content
        return result

    # ── ANALYSIS ──────────────────────────────────────────────────────────────
    if action == "analysis":
        prompt = f"""FaceFit AI — warm, expert.
Tell {name}: Skin Tone {skin_tone} (skincare + best fashion colors), Face Shape {face_shape} (best necklines/collars), Conditions {conds_str} (what each means + key ingredient).
Warm, reassuring, under 100 words. End with one specific tip."""
        result["message"] = llm.invoke(prompt).content
        return result

    # ── COLOR THEORY ──────────────────────────────────────────────────────────
    if action == "color_theory":
        rag_ctx = _rag(_fashion_ret, f"color theory {skin_tone} skin tone best colors fashion India")
        prompt = f"""World-class colorist and personal stylist. CLIENT: {name} | {skin_tone} skin tone | {face_shape} face | {gl}
KNOWLEDGE: {rag_ctx}
Answer: "{message}"
4-5 sentences: (1) Undertone and what it means (2) Top 5 specific colors that make them glow — name exact shades (3) Colors to avoid + why (4) Best statement color (5) "Want outfit picks in these colors?"
Under 110 words. Be specific."""
        result["message"] = llm.invoke(prompt).content
        return result

    # ── GROOMING ──────────────────────────────────────────────────────────────
    if action == "grooming":
        prompt = f"""Master grooming expert for India. CLIENT: {name} | {skin_tone} skin | {face_shape} face | {gl}
QUESTION: "{message}"
3-4 sentences: (1) Grooming tip specific to {face_shape} face (2) Beard/hair style that flatters (3) One product recommendation (4) Power tip they'll use tomorrow.
Under 90 words."""
        result["message"] = llm.invoke(prompt).content
        return result

    # ── TREND ─────────────────────────────────────────────────────────────────
    if action == "trend":
        rag_ctx = _rag(_fashion_ret, f"trending style India streetwear ethnic fusion 2025")
        prompt = f"""Top Indian fashion editor. CLIENT: {name} | {skin_tone} skin | {gl}
QUESTION: "{message}" | KNOWLEDGE: {rag_ctx}
4 sentences: (1) Top trend in India right now for {gl} (2) Key pieces (3) How {skin_tone} skin makes it look better (4) "Want to shop the trend? I'll find the pieces ↓"
Under 90 words."""
        result["message"] = llm.invoke(prompt).content
        return result

    # ── STYLE EXPLAIN ─────────────────────────────────────────────────────────
    if action == "style_explain":
        rag_ctx = _rag(_fashion_ret, f"{message} {skin_tone} skin {gl} style guide")
        prompt = f"""Fashion editor and personal stylist. CLIENT: {name} | {skin_tone} skin | {face_shape} face | {gl}
QUESTION: "{message}" | KNOWLEDGE: {rag_ctx}
4-5 sentences: (1) Define the style in one punchy sentence (2) Key pieces that define it (3) How it works for {skin_tone} skin (4) Specific items they need (5) "Want me to build this look for you?"
Under 110 words."""
        result["message"] = llm.invoke(prompt).content
        return result

    # ── CLOSET SEARCH ─────────────────────────────────────────────────────────
    if action == "closet_search":
        wardrobe = get_wardrobe(user_id)
        if not wardrobe:
            result["message"]      = f"Your closet is empty, {name}! Go to the **Closet tab** and upload your clothes."
            result["closet_empty"] = True
            return result
        found_items = _search_wardrobe_for_item(wardrobe, message)
        result["closet_found_items"] = found_items[:4] if found_items else []
        result["found"]              = bool(found_items)
        result["message"]            = _stylist_wardrobe_search_message(name, skin_tone, face_shape, gender, message, found_items, not found_items)
        result["product_type"]       = "closet_search"
        return result

    # ── CLOSET SUMMARY ────────────────────────────────────────────────────────
    if action == "closet_summary":
        wardrobe = get_wardrobe(user_id)
        if not wardrobe:
            result["message"]      = f"Your digital closet is empty, {name}! Head to the **Closet tab** and upload your clothes."
            result["closet_empty"] = True
            return result
        summary = get_closet_summary(user_id)
        result["message"]         = f"Here's your wardrobe, {name}! You have **{summary['total']} items**. {summary['summary']} What are we dressing for today?"
        result["closet_summary"]  = summary
        return result

    # ── CLOSET COLOR ──────────────────────────────────────────────────────────
    if action == "closet_color":
        wardrobe = get_wardrobe(user_id)
        if not wardrobe:
            result["message"]      = f"Your closet is empty, {name}! Upload clothes in the **Closet tab** first."
            result["closet_empty"] = True
            return result
        color       = color_filter or _detect_color_in_message(message)
        found_items = _search_wardrobe_for_item(wardrobe, color or message) if color else []
        result["message"]      = _stylist_closet_color_message(name, skin_tone, gender, color or "your", found_items, event)
        result["product_type"] = "closet"
        if found_items:
            result["closet_found_items"] = found_items[:4]
        acc_queries = _get_accessories_for_gender(
            gender, skin_tone, event or "casual",
            time_of_day in ("night","evening"),
            event in ETHNIC_EVENTS if event else False,
        )
        products = {}
        for cat, q in acc_queries.items():
            try:
                prods = get_product_recommendations(q, cat)
                if prods: products[cat] = prods[:4]
            except Exception: pass
        if products: result["products"] = products
        return result

    # ── CLOSET — MAIN EVENT-BASED (DUAL OUTFIT) ───────────────────────────────
    if action == "closet":
        wardrobe = get_wardrobe(user_id)
        if not wardrobe:
            result["message"]      = f"Your digital closet is empty, {name}! Head to the **Closet tab** and upload your clothes."
            result["closet_empty"] = True
            return result

        event_type  = event or "casual"
        ev_info     = EVENT_REQUIREMENTS.get(event_type, EVENT_REQUIREMENTS.get("casual",{}))
        is_ethnic   = event_type in ETHNIC_EVENTS
        is_athletic = event_type in ATHLETIC_EVENTS

        # PATCHED: _plan_dual_outfit now uses event-filtered wardrobe
        dual = _plan_dual_outfit(user_id, message, event_type, time_of_day, skin_tone, face_shape, gender, user)

        if is_athletic and event_type == "gym":
            ai_msg = _stylist_fashion_message(name, skin_tone, face_shape, gender, message, "gym outfit", event="gym")
        elif is_athletic and event_type in ("cricket", "football", "running", "sport"):
            ai_msg = _stylist_fashion_message(name, skin_tone, face_shape, gender, message, f"{event_type} outfit", event="gym")
        elif is_athletic and event_type == "beach":
            ai_msg = _stylist_fashion_message(name, skin_tone, face_shape, gender, message, "beach outfit", event="beach")
        elif is_ethnic:
            ai_msg = _stylist_fashion_message(name, skin_tone, face_shape, gender, message, "ethnic outfit", event=event_type)
        else:
            available = dual["closet"].get("available_items", {})
            missing   = dual["closet"].get("missing_categories", [])
            ai_msg    = _stylist_wardrobe_message(name, skin_tone, face_shape, gender, message, available, missing, event_type, time_of_day)

        result["message"]      = ai_msg
        result["dual_outfit"]  = dual
        result["product_type"] = "closet"
        return result

    # ── FASHION — SINGLE ITEM WITH COLOR OVERRIDE ─────────────────────────────
    if action == "products_fashion" and color_override:
        last_color = _extract_last_color_from_history(history)
        item_cat   = single_cat or _extract_last_category_from_history(history) or "shirt"
        products, _ = _fetch_fashion_single(skin_tone, face_shape, gender, item_cat, color_override=color_override, last_color=last_color)
        result["message"]      = _stylist_color_followup_message(name, skin_tone, gender, item_cat, color_override)
        result["products"]     = products
        result["product_type"] = "fashion"
        return result

    if action == "products_fashion" and single_cat:
        rag_ctx     = _rag(_fashion_ret, f"{specific} {skin_tone} {face_shape} {gl}")
        products, _ = _fetch_fashion_single(skin_tone, face_shape, gender, single_cat, specific)
        result["message"]      = _stylist_single_item_message(name, skin_tone, gender, specific, rag_ctx)
        result["products"]     = products
        result["product_type"] = "fashion"
        return result

    if action == "products_fashion":
        rag_ctx = _rag(_fashion_ret, f"{message} {skin_tone} {face_shape} {gl}")
        products, outfits, outfit_label = _fetch_fashion_full_outfit(
            skin_tone, face_shape, gender, event, time_of_day, style_keyword, message
        )
        if event not in ATHLETIC_EVENTS:
            acc_queries = _get_accessories_for_gender(
                gender, skin_tone, event or "casual",
                time_of_day in ("night","evening"),
                event in ETHNIC_EVENTS if event else False,
            )
            for cat, q in acc_queries.items():
                if cat not in products:
                    try:
                        prods = get_product_recommendations(q, cat)
                        if prods: products[cat] = prods[:4]
                    except Exception: pass
        result["message"]      = _stylist_fashion_message(name, skin_tone, face_shape, gender, message, outfit_label, event, time_of_day, style_keyword, rag_ctx)
        result["products"]     = products
        result["outfits"]      = outfits
        result["product_type"] = "fashion"
        result["outfit_label"] = outfit_label
        return result

    # ── SKINCARE ──────────────────────────────────────────────────────────────
    if action == "products_skin":
        rag_ctx              = _rag(_skin_ret, f"{message} {conds_str} {skin_tone}")
        products, routine, _ = _fetch_skin_products(skin_tone, unique_conds, category)
        result["message"]      = _stylist_skin_message(name, skin_tone, conds_str, specific if category else None, rag_ctx)
        result["products"]     = products
        result["product_type"] = "skincare"
        if not category: result["routine"] = routine
        return result

    # ── BOTH ──────────────────────────────────────────────────────────────────
    if action == "products_both":
        prompt = f"""FaceFit AI. USER: {name} | {skin_tone} skin | {face_shape} face | {gl}
SAID: "{message}"
2 sentences: best outfit + skincare pick for their profile. End: "Here are my top curated picks ↓" """
        result["message"]    = llm.invoke(prompt).content
        f_prods, _, _        = _fetch_fashion_full_outfit(skin_tone, face_shape, gender, event, time_of_day, user_message=message)
        s_prods, routine, _  = _fetch_skin_products(skin_tone, unique_conds)
        combined             = {**{k:v[:3] for k,v in f_prods.items()}, **{k:v[:3] for k,v in s_prods.items()}}
        if combined:
            result["products"]     = combined
            result["routine"]      = routine
            result["product_type"] = "both"
        return result

    # ── GENERAL CHAT ──────────────────────────────────────────────────────────
    prompt = f"""FaceFit AI — world's most stylish AI personal stylist. Confident, opinionated, warm.
USER: {name} | {skin_tone} skin | {face_shape} face | {conds_str} | {gl}
{hist_block}
USER SAID: "{message}"
Under 80 words. If greeting → introduce yourself + mention you know their profile. If "yes/ok" → ask what look/routine they need. Any question → answer using their exact profile. Have a real opinion. End with one actionable suggestion or question."""
    result["message"] = llm.invoke(prompt).content
    return result