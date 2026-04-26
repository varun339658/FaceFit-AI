"""
outfit_validator.py — FaceFit Outfit Validation
════════════════════════════════════════════════
Validates that wardrobe items shown to users are appropriate for the event.

The core problem: plan_outfit_for_event() falls back to shirt/pants for
gym events if no gym clothes exist, showing a kurta/jeans for the gym.

This module:
1. FILTERS: Removes inappropriate items for an event before showing them
2. WARNS: Adds a warning message when items aren't ideal
3. REDIRECTS: Points user to shop the right items

Usage: Import and wrap the closet_agent's plan_outfit_for_event result.
"""

# ── Event-specific FORBIDDEN categories/keywords ──────────────────────────────

# Items that MUST NOT appear for these events
EVENT_FORBIDDEN = {
    "gym": {
        "categories": [],  # No category is outright forbidden — we check keywords
        "keywords": ["kurta", "sherwani", "lehenga", "saree", "ethnic", "blazer",
                     "suit", "formal", "lace-up", "oxford", "derby", "loafer",
                     "jeans", "denim", "chino", "khakis"],
        "message": "Gym requires athletic wear — dry-fit tops, track pants, and sports shoes.",
        "redirect_to": ["gym_tshirt", "track_pants", "sports_shoes"],
    },
    "beach": {
        "keywords": ["formal", "kurta", "sherwani", "blazer", "suit", "oxford",
                     "derby", "trouser", "chino", "ethnic"],
        "message": "Beach calls for light fabrics — linen shirts, swim shorts, and flip flops.",
        "redirect_to": ["beach_shirt", "swim_shorts", "flip_flops"],
    },
    "interview": {
        "keywords": ["track pant", "jogger", "gym", "athletic", "sport",
                     "graphic tee", "oversized", "cargo", "flip flop", "slipper",
                     "ethnic", "kurta"],
        "message": "Interview requires professional attire — formal shirt, trousers, and leather shoes.",
        "redirect_to": ["shirt", "pants", "shoes"],
    },
    "office": {
        "keywords": ["track pant", "jogger", "gym", "athletic", "flip flop",
                     "slipper", "graphic tee", "oversized"],
        "message": "Office wear should be professional — shirt, formal trousers, and closed shoes.",
        "redirect_to": ["shirt", "pants", "shoes"],
    },
}

# Items PREFERRED for these events (used to score/rank)
EVENT_PREFERRED_KEYWORDS = {
    "gym":      ["dry fit", "dri-fit", "polyester", "athletic", "sport", "track",
                 "jogger", "compression", "training", "nike", "adidas", "puma"],
    "beach":    ["linen", "beach", "floral", "hawaiian", "quick dry", "swim",
                 "casual", "light", "summer"],
    "wedding":  ["kurta", "sherwani", "ethnic", "traditional", "silk", "embroidered",
                 "festive", "formal"],
    "festival": ["kurta", "ethnic", "traditional", "festive", "embroidered",
                 "silk", "cotton", "colorful"],
    "interview":["formal", "white", "light blue", "slim fit", "button down",
                 "blazer", "trouser", "oxford"],
    "office":   ["formal", "shirt", "trouser", "blazer", "slim fit", "chino"],
    "casual":   ["casual", "jeans", "t-shirt", "comfortable", "relaxed"],
    "party":    ["bold", "dark", "slim", "blazer", "party", "dressy"],
    "college":  ["casual", "oversized", "graphic", "jeans", "cargo", "streetwear"],
}


def _item_keywords(item: dict) -> str:
    """Get all searchable text from a wardrobe item."""
    return " ".join([
        item.get("item_name", ""),
        item.get("style", ""),
        item.get("category", ""),
        " ".join(item.get("occasion", [])),
        item.get("color", ""),
        item.get("formality", ""),
    ]).lower()


def validate_outfit_for_event(available_items: dict, event_type: str) -> dict:
    """
    Validates whether the wardrobe items chosen are appropriate for the event.
    
    Returns:
        {
            "valid": bool,
            "filtered_items": dict,  # items after removing inappropriate ones
            "warnings": list[str],   # warning messages
            "removed": list[str],    # names of removed items
            "should_redirect": bool, # True if user needs to shop
        }
    """
    rules = EVENT_FORBIDDEN.get(event_type, {})
    if not rules:
        return {
            "valid": True,
            "filtered_items": available_items,
            "warnings": [],
            "removed": [],
            "should_redirect": False,
        }

    forbidden_kws = rules.get("keywords", [])
    filtered = {}
    removed = []
    warnings = []

    for cat, item in available_items.items():
        if not item:
            continue
        keywords_str = _item_keywords(item)
        is_forbidden = any(kw in keywords_str for kw in forbidden_kws)
        if is_forbidden:
            removed.append(item.get("item_name", cat))
        else:
            filtered[cat] = item

    if removed:
        warnings.append(rules.get("message", f"Some items may not suit a {event_type} event."))

    # If we removed things and have very few items left, suggest shopping
    should_redirect = len(filtered) < 2 and len(removed) > 0

    return {
        "valid": len(removed) == 0,
        "filtered_items": filtered,
        "warnings": warnings,
        "removed": removed,
        "should_redirect": should_redirect,
        "redirect_cats": rules.get("redirect_to", []),
    }


def score_item_appropriateness(item: dict, event_type: str) -> float:
    """
    Score how appropriate a wardrobe item is for the event.
    Higher is better. Used to rank items for display.
    """
    preferred = EVENT_PREFERRED_KEYWORDS.get(event_type, [])
    keywords_str = _item_keywords(item)
    score = 0.0
    for kw in preferred:
        if kw in keywords_str:
            score += 2.0
    # Check occasion tags
    occasions = [o.lower() for o in item.get("occasion", [])]
    if event_type in occasions:
        score += 5.0
    return score


def get_event_appropriateness_message(event_type: str, has_items: bool) -> str:
    """Get a helpful message about what to wear for an event."""
    messages = {
        "gym": "💪 For gym: Athletic wear only — dry-fit tee, track pants, sports shoes. No jeans or ethnic wear.",
        "beach": "🏖️ For beach: Light fabrics — linen shirt, swim shorts, flip flops.",
        "interview": "🎯 For interviews: Professional attire — formal shirt, slim trousers, leather shoes.",
        "office": "💼 For office: Smart professional — button shirt, formal pants, closed shoes.",
        "wedding": "💍 For wedding: Ethnic or formal — kurta/sherwani for men, lehenga/saree for women.",
        "festival": "🎉 For festival: Ethnic and festive — colorful kurta, traditional wear.",
    }
    if not has_items:
        shopping_tips = {
            "gym": "Shop Nike/Puma dry-fit tees and track pants for your gym wardrobe.",
            "beach": "Pick up a linen beach shirt and swim shorts for your beach look.",
            "interview": "A crisp formal shirt and slim trousers are interview essentials.",
        }
        return shopping_tips.get(event_type, f"Upload appropriate {event_type} clothes to get outfit suggestions.")
    return messages.get(event_type, "")