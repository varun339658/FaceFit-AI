"""
color_palette_service.py — Outfit Color Palette Generator
==========================================================
Generates a color palette visualization from wardrobe item colors.
Returns structured data for the React color wheel component.
Also exposes /closet/color-palette/<user_id> route.
"""
import os, colorsys
from flask import Blueprint, request, jsonify
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI","mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority")
_mc  = MongoClient(MONGO_URI)
_db  = _mc["facefit_ai"]
_wardrobe = _db["wardrobe"]

color_palette_bp = __import__('flask').Blueprint("color_palette", __name__)

# Named color → hex mapping (comprehensive)
COLOR_HEX = {
    "black":"#1a1a1a","white":"#f5f5f0","grey":"#9e9e9e","gray":"#9e9e9e",
    "red":"#d32f2f","blue":"#1565c0","green":"#2e7d32","yellow":"#f9a825",
    "orange":"#e65100","pink":"#c2185b","purple":"#6a1b9a","brown":"#4e342e",
    "beige":"#d7c4a3","cream":"#f5f0dc","navy":"#0d2b6e","navy blue":"#0d2b6e",
    "dark green":"#1b5e20","off white":"#f5f0dc","dark grey":"#424242",
    "maroon":"#880e4f","teal":"#00695c","olive":"#827717","mustard":"#f57f17",
    "burgundy":"#880e4f","emerald":"#1b5e20","royal blue":"#1565c0",
    "electric blue":"#0288d1","coral":"#e64a19","gold":"#f9a825",
    "saffron":"#ff8f00","terracotta":"#bf360c","camel":"#a1887f",
    "forest green":"#2e7d32","mint":"#a5d6a7","lavender":"#ce93d8",
    "peach":"#ffcc80","sage":"#a5b68d","khaki":"#c0b283","rust":"#b7410e",
    "copper":"#b87333","wine":"#722f37","charcoal":"#36454f","ivory":"#fffff0",
    "champagne":"#f7e7ce","lilac":"#c8a2c8","magenta":"#ff00ff","cyan":"#00bcd4",
    "indigo":"#3f51b5","violet":"#ee82ee","turquoise":"#40e0d0","tan":"#d2b48c",
    "blush":"#de5d83","rose":"#ff007f","ash":"#b2bec3","denim":"#1560bd",
}

# Color harmony rules
def _hex_to_hsl(hex_color):
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i:i+2], 16)/255.0 for i in (0,2,4)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h*360, s*100, l*100

def _complementary(h): return (h + 180) % 360
def _analogous(h): return [(h - 30) % 360, h, (h + 30) % 360]
def _triadic(h): return [h, (h + 120) % 360, (h + 240) % 360]

def _score_harmony(hex1, hex2):
    """Score color harmony between two colors: 0-1."""
    try:
        h1, s1, l1 = _hex_to_hsl(hex1)
        h2, s2, l2 = _hex_to_hsl(hex2)
        angle = abs(h1 - h2)
        if angle > 180: angle = 360 - angle
        # Complementary (near 180°): high score
        if 150 <= angle <= 180: return 1.0
        # Analogous (near 30°): good
        if angle <= 30: return 0.85
        # Triadic (near 120°): good
        if 100 <= angle <= 140: return 0.75
        # Split complementary: ok
        if 140 <= angle <= 160: return 0.65
        # Neutral neutrals: always ok
        if s1 < 15 or s2 < 15: return 0.70
        return max(0.2, 0.6 - (angle / 360))
    except:
        return 0.5

def _resolve_color(color_str):
    """Find the best hex for a color name string."""
    if not color_str: return "#c8a55a"
    c = color_str.lower().strip()
    # Direct match
    if c in COLOR_HEX: return COLOR_HEX[c]
    # Partial match
    for name, hex_ in COLOR_HEX.items():
        if name in c or c in name:
            return hex_
    # Default
    return "#c8a55a"

def generate_palette_for_outfit(outfit_items: list, skin_tone: str = "medium") -> dict:
    """
    Generate color palette data for a list of outfit items.
    outfit_items: list of wardrobe item dicts with 'color', 'item_name', 'category'
    """
    palette = []
    for item in outfit_items:
        if not item: continue
        color_str = item.get("color", "")
        hex_color = _resolve_color(color_str)
        palette.append({
            "name":       item.get("item_name", "Item"),
            "category":   item.get("category", ""),
            "color_name": color_str,
            "hex":        hex_color,
        })

    if not palette:
        return {"palette": [], "harmony_score": 0, "harmony_label": "No colors", "combos": []}

    # Score harmony between all pairs
    hexes = [p["hex"] for p in palette]
    pair_scores = []
    for i in range(len(hexes)):
        for j in range(i+1, len(hexes)):
            score = _score_harmony(hexes[i], hexes[j])
            pair_scores.append({
                "item1": palette[i]["name"],
                "item2": palette[j]["name"],
                "color1": hexes[i],
                "color2": hexes[j],
                "score": round(score, 2),
                "label": "Excellent" if score >= 0.85 else "Good" if score >= 0.65 else "OK" if score >= 0.4 else "Clash",
            })

    avg_score = sum(p["score"] for p in pair_scores) / len(pair_scores) if pair_scores else 0.5
    harmony_label = "✦ Perfect Harmony" if avg_score >= 0.85 else "✓ Good Combo" if avg_score >= 0.65 else "~ Wearable" if avg_score >= 0.4 else "⚠ Color Clash"

    # Skin tone accent suggestions
    SKIN_ACCENTS = {
        "dark":   ["#0288d1","#2e7d32","#1565c0","#ff8f00","#e64a19"],
        "medium": ["#f57f17","#880e4f","#00695c","#1b5e20","#bf360c"],
        "light":  ["#ce93d8","#a5d6a7","#90caf9","#81d4fa","#ffcc80"],
    }
    accent_hexes = SKIN_ACCENTS.get(skin_tone.lower(), SKIN_ACCENTS["medium"])

    return {
        "palette":       palette,
        "harmony_score": round(avg_score, 2),
        "harmony_label": harmony_label,
        "pair_scores":   pair_scores[:10],  # top 10 pairs
        "accent_suggestions": [{"hex": h, "label": f"Accent color for {skin_tone} skin"} for h in accent_hexes[:3]],
    }


@color_palette_bp.route("/closet/color-palette/<user_id>", methods=["GET"])
def get_color_palette(user_id):
    """Get color palette for user's wardrobe or a specific outfit."""
    from services.closet_agent import get_wardrobe
    skin_tone = request.args.get("skin_tone", "medium")
    outfit_items_param = request.args.get("items")  # optional: comma-sep item_ids
    try:
        wardrobe = get_wardrobe(user_id)
        if not wardrobe:
            return jsonify({"palette": [], "message": "No wardrobe items found"}), 200
        # Filter by specific items if requested
        if outfit_items_param:
            ids = set(outfit_items_param.split(","))
            wardrobe = [w for w in wardrobe if w.get("item_id") in ids]
        palette_data = generate_palette_for_outfit(wardrobe[:12], skin_tone)
        return jsonify(palette_data), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500