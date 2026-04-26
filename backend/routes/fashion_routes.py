"""
fashion_routes.py — FIXED: Budget + Brand filters properly applied to ALL product fetches
"""

from flask import Blueprint, request, jsonify
from services.fashion_rag_service import generate_outfit_recommendation
from services.product_service import get_product_recommendations, get_multiple_categories_parallel
from services.weather_service import get_weather_filters

fashion_bp = Blueprint("fashion", __name__)

EVENT_QUERY_TEMPLATES = {
    "gym": {
        "male": {
            "gym_tshirt":   "Nike Puma HRX dry fit gym t-shirt athletic performance men India",
            "track_pants":  "Nike Puma track pants jogger training slim fit men India",
            "sports_shoes": "Nike Adidas running training shoes men India lightweight",
        },
        "female": {
            "gym_tshirt":   "Nike Puma HRX sports crop top women gym India athletic",
            "track_pants":  "Nike Puma gym leggings high waist tights women India",
            "sports_shoes": "Nike Adidas running shoes women India training lightweight",
        },
    },
    "beach": {
        "male": {
            "beach_shirt": "linen beach shirt floral relaxed fit men India summer",
            "swim_shorts":  "quick dry swim shorts beach men India colorful",
            "flip_flops":  "Havaianas flip flops beach sandals men India",
        },
        "female": {
            "beach_shirt": "floral beach dress sundress boho women India summer Myntra",
            "swim_shorts":  "swimsuit one piece beach women India summer",
            "flip_flops":  "flip flops flat beach sandals women India Havaianas",
        },
    },
    "college": {
        "male": {
            "shirt":  "oversized graphic t-shirt casual streetwear men India college Myntra",
            "pants":  "slim fit jeans cargo pants men India casual college Myntra",
            "shoes":  "white chunky sneakers men India casual college Nike Adidas",
        },
        "female": {
            "shirt":  "oversized crop top casual streetwear women India college",
            "pants":  "high waist jeans cargo pants women India casual college",
            "shoes":  "platform sneakers white women India casual college",
        },
    },
    "office": {
        "male": {
            "shirt":  "formal slim fit shirt men India office professional Myntra",
            "pants":  "formal slim trousers chino men India office professional",
            "shoes":  "leather oxford derby shoes men India formal office",
        },
        "female": {
            "shirt":  "formal blouse shirt women India office professional Myntra",
            "pants":  "formal slim trousers women India office professional",
            "shoes":  "block heels formal shoes women India office professional",
        },
    },
    "interview": {
        "male": {
            "shirt":  "white light blue formal shirt men India interview slim fit",
            "pants":  "formal slim trousers black navy men India interview",
            "shoes":  "black leather derby oxford shoes men India formal interview",
        },
        "female": {
            "shirt":  "formal white pastel blouse women India interview professional",
            "pants":  "formal straight trousers women India interview professional",
            "shoes":  "block heels formal women India interview professional",
        },
    },
    "party": {
        "male": {
            "shirt":  "party shirt bold print men India night out Myntra",
            "pants":  "slim fit dark party trousers men India",
            "shoes":  "leather boots party men India night shoes",
        },
        "female": {
            "shirt":  "party dress bodysuit women India night out Myntra",
            "pants":  "mini skirt wide leg party trousers women India",
            "shoes":  "heels block pumps party women India night",
        },
    },
    "wedding": {
        "male": {
            "ethnic": "sherwani indo-western kurta men India wedding festive embroidered",
            "shoes":  "kolhapuri mojri ethnic shoes men India wedding",
            "accessories": "gold watch kada bracelet men ethnic India wedding",
        },
        "female": {
            "ethnic": "lehenga choli saree women India wedding festive embroidered",
            "shoes":  "heeled sandals gold ethnic juttis women India wedding",
            "accessories": "gold necklace earrings bangles women India wedding",
        },
    },
    "festival": {
        "male": {
            "ethnic": "festive kurta ethnic print men India Diwali festival embroidered",
            "shoes":  "kolhapuri juttis mojri ethnic men India festival",
            "accessories": "gold watch ethnic bracelet men India festive",
        },
        "female": {
            "ethnic": "kurti anarkali women India festive Diwali festival ethnic",
            "shoes":  "juttis sandals ethnic women India festive",
            "accessories": "gold earrings bangles necklace women India festive",
        },
    },
    "casual": {
        "male": {
            "shirt":  "casual comfortable t-shirt men India Myntra",
            "pants":  "casual jeans everyday men India Myntra",
            "shoes":  "everyday sneakers casual comfortable men India",
        },
        "female": {
            "shirt":  "casual top blouse women India Myntra comfortable",
            "pants":  "casual jeans comfortable women India Myntra",
            "shoes":  "everyday sneakers casual comfortable women India",
        },
    },
    "date": {
        "male": {
            "shirt":  "smart casual date night shirt men India slim fit",
            "pants":  "slim fit dark jeans chinos men India date night",
            "shoes":  "leather loafers boots men India date smart",
        },
        "female": {
            "shirt":  "off shoulder wrap date outfit women India",
            "pants":  "slim jeans wide leg trousers women India date",
            "shoes":  "block heels strappy sandals women India date",
        },
    },
    "dinner": {
        "male": {
            "shirt":  "smart formal shirt men India dinner evening",
            "pants":  "slim formal trousers dark men India dinner",
            "shoes":  "leather loafers smart men India dinner",
        },
        "female": {
            "shirt":  "elegant blouse top women India dinner",
            "pants":  "wide leg trousers skirt women India dinner",
            "shoes":  "block heels strappy women India dinner",
        },
    },
    "brunch": {
        "male": {
            "shirt":  "smart casual linen shirt men India brunch weekend",
            "pants":  "chino slim trousers men India brunch",
            "shoes":  "loafers clean sneakers men India brunch",
        },
        "female": {
            "shirt":  "flowy blouse casual top women India brunch",
            "pants":  "wide leg trousers jeans women India brunch",
            "shoes":  "flat sandals sneakers women India brunch",
        },
    },
    "travel": {
        "male": {
            "shirt":  "comfortable linen casual shirt men India travel",
            "pants":  "cargo jogger comfortable pants men India travel",
            "shoes":  "comfortable sneakers walking shoes men India travel",
        },
        "female": {
            "shirt":  "comfortable cotton top blouse women India travel",
            "pants":  "comfortable jogger pants jeans women India travel",
            "shoes":  "comfortable sneakers walking shoes women India travel",
        },
    },
    "puja": {
        "male": {
            "ethnic": "cotton kurta dhoti puja men India traditional",
            "shoes":  "kolhapuri sandals ethnic men India puja temple",
        },
        "female": {
            "ethnic": "cotton saree salwar women India puja temple traditional",
            "shoes":  "juttis flat sandals ethnic women India puja",
        },
    },
    "sangeet": {
        "male": {
            "ethnic": "indo western kurta men India sangeet festive dance embroidered",
            "shoes":  "mojri juttis ethnic shoes men India sangeet",
            "accessories": "gold watch bracelet men India sangeet",
        },
        "female": {
            "ethnic": "lehenga anarkali women India sangeet festive dance colorful",
            "shoes":  "heels ethnic sandals juttis women India sangeet",
            "accessories": "gold earrings bangles women India sangeet",
        },
    },
    "concert": {
        "male": {
            "shirt":  "bold graphic oversized tshirt men India concert streetwear",
            "pants":  "slim dark jeans cargo men India concert",
            "shoes":  "chunky sneakers boots men India concert",
        },
        "female": {
            "shirt":  "bold top bodysuit women India concert",
            "pants":  "slim jeans mini skirt women India concert",
            "shoes":  "platform boots heels women India concert",
        },
    },
}

SKIN_TONE_COLORS = {
    "dark":   ["electric blue", "emerald green", "royal blue", "saffron yellow", "coral"],
    "medium": ["mustard", "burgundy", "teal", "forest green", "terracotta"],
    "light":  ["pastel blue", "mint green", "lavender", "sage green", "blush pink"],
}


def _inject_skin_color(query: str, skin_tone: str, category: str) -> str:
    color_cats = {"shirt", "top", "ethnic", "gym_tshirt", "beach_shirt", "dress", "blazer"}
    if category not in color_cats:
        return query
    colors = SKIN_TONE_COLORS.get(skin_tone.lower(), SKIN_TONE_COLORS["medium"])
    import random
    color = random.choice(colors[:3])
    if not any(c in query.lower() for c in colors):
        return f"{color} {query}"
    return query


def _build_event_queries(event: str, gender: str, skin_tone: str) -> dict:
    gl = "male" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "female"
    event_key = event if event in EVENT_QUERY_TEMPLATES else "casual"
    templates = EVENT_QUERY_TEMPLATES.get(event_key, EVENT_QUERY_TEMPLATES["casual"])
    gender_templates = templates.get(gl, templates.get("male", {}))
    queries = {}
    for cat, query in gender_templates.items():
        queries[cat] = _inject_skin_color(query, skin_tone, cat)
    return queries


@fashion_bp.route("/outfits", methods=["POST"])
def get_outfits():
    data = request.json

    skin_tone  = data.get("skinTone",   "medium")
    face_shape = data.get("face_shape", "oval")
    body_shape = data.get("body_shape", "average")
    gender     = data.get("gender",     "male")
    city       = data.get("city",       request.args.get("city", "Hyderabad"))
    event      = data.get("event",      None)
    user_id    = data.get("user_id",    data.get("userId", None))

    print(f"OUTFIT REQUEST → tone={skin_tone} | shape={face_shape} | gender={gender} | city={city} | event={event} | user={user_id}")

    # Weather
    weather_data = get_weather_filters(city)
    weather_ctx  = {
        "summary":    weather_data.get("summary", ""),
        "filters":    weather_data.get("filters", []),
        "fabric_tip": weather_data.get("fabric_tip", ""),
        "carry_tip":  weather_data.get("carry_tip", ""),
        "color_tip":  weather_data.get("color_tip", ""),
    }

    # Build queries
    if event and event in EVENT_QUERY_TEMPLATES:
        outfit_queries = _build_event_queries(event, gender, skin_tone)
        print(f"✦ EVENT-BASED queries for {event}: {list(outfit_queries.keys())}")
    else:
        outfit_queries = generate_outfit_recommendation(
            skin_tone, face_shape, body_shape, gender,
            weather_context=weather_ctx,
        )
        print(f"✦ RAG queries: {list(outfit_queries.keys())}")

    # Apply brand preferences to queries FIRST
    if user_id:
        try:
            from services.budget_brand_service import inject_brands_into_query
            enriched = {}
            for cat, q in outfit_queries.items():
                enriched[cat] = inject_brands_into_query(q, user_id, max_brands=2)
            outfit_queries = enriched
            print(f"✦ Brand preferences applied for user={user_id}")
        except Exception as e:
            print(f"Brand inject error (non-fatal): {e}")

        # Inject style DISLIKES from learning system
        try:
            from pymongo import MongoClient
            import os
            _mc = MongoClient(os.getenv("MONGO_URI", "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority"))
            _pref = _mc["facefit_ai"]["user_style_prefs"].find_one({"userId": user_id}, {"_id": 0})
            if _pref:
                rejected_colors = _pref.get("rejected_colors", {})
                enriched2 = {}
                for cat, q in outfit_queries.items():
                    avoid = rejected_colors.get(cat, [])
                    if avoid:
                        # Append "not <color>" hints to query
                        avoid_str = " ".join(f"-{c}" for c in avoid[:2])
                        enriched2[cat] = f"{q} {avoid_str}"
                    else:
                        enriched2[cat] = q
                outfit_queries = enriched2
                print(f"✦ Style preferences applied for user={user_id}")
        except Exception as e:
            print(f"Style prefs inject (non-fatal): {e}")

    # Fetch products in parallel
    outfit_products = get_multiple_categories_parallel(outfit_queries, event=event, user_id=user_id)

    # Fallback for failed categories
    for category, query in outfit_queries.items():
        if category not in outfit_products or not outfit_products[category]:
            try:
                gl = "men" if gender.lower() not in ("female", "women", "woman", "girl", "f") else "women"
                fallback_q = f"{category.replace('_', ' ')} fashion {gl} India"
                products   = get_product_recommendations(fallback_q, category, event, user_id=user_id)
                if products:
                    outfit_products[category] = products
            except Exception as e:
                print(f"Fallback ERROR [{category}]:", e)
                outfit_products[category] = []

    # Apply budget filter to ALL products
    if user_id:
        try:
            from services.budget_brand_service import filter_all_products_by_budget, get_user_budget
            budget = get_user_budget(user_id)
            min_p  = budget.get("min_price", 0) or 0
            max_p  = budget.get("max_price") or None
            if min_p > 0 or max_p is not None:
                outfit_products = filter_all_products_by_budget(outfit_products, min_p, max_p)
                print(f"✦ Budget filter ₹{min_p}–₹{max_p} applied to outfits")
        except Exception as e:
            print(f"Budget filter error (non-fatal): {e}")

    return jsonify({
        "outfits":         outfit_queries,
        "outfit_products": outfit_products,
        "weather":         weather_ctx,
    })