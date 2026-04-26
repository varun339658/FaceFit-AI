"""
fashion_rag_service.py — FaceFit Fashion RAG v13 (Combined)
═══════════════════════════════════════════════════════════════════════════════
COMBINED from:
  • v1  (weather_context injection into LLM prompt)
  • v12 (pre-verified outfit formula library, style/event routing, chatbot pipeline)

ARCHITECTURE:
  - RAG retrieves fashion knowledge (color theory, face shape, occasions)
  - Pre-verified OUTFITS formulas guarantee correct colors, shoes, accessories
  - Weather context is injected into formula selection AND into LLM narrative
  - generate_outfit_recommendation : /outfits route (profile-based, weather-aware)
  - generate_outfit_for_context    : chatbot (message + event + style + weather)
"""

import random
import os
import json
import re

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma

try:
    from langchain_huggingface import HuggingFaceEmbeddings as SentenceTransformerEmbeddings
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings as SentenceTransformerEmbeddings
    except ImportError:
        from langchain_community.embeddings import SentenceTransformerEmbeddings

from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# ── Load fashion knowledge into RAG ──────────────────────────────────────────
loader    = TextLoader("rag_data/fashion_knowledge.txt")
documents = loader.load()
splitter  = CharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
docs      = splitter.split_documents(documents)

embedding   = SentenceTransformerEmbeddings(model_name="paraphrase-MiniLM-L3-v2")
vectorstore = Chroma.from_documents(docs, embedding, collection_name="fashion_v13")
retriever   = vectorstore.as_retriever(search_kwargs={"k": 6})

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.4,
    groq_api_key=os.getenv("GROQ_API_KEY"),
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rag(query: str) -> str:
    """Retrieve relevant fashion knowledge from vector store."""
    results = retriever.invoke(query)
    return "\n\n".join(d.page_content for d in results)


def _extract_json(text: str) -> dict:
    """Safely extract a JSON object from LLM output."""
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


def _build_weather_block(weather_context: dict) -> str:
    """
    Build a weather context string for injection into prompts.
    weather_context keys (all optional):
      summary    : "32°C, 60% humidity in Mumbai"
      filters    : ["EXCLUDE: heavy jackets, jeans", "PREFER: linen, cotton"]
      fabric_tip : "Hot weather — lightweight breathable fabrics only."
      carry_tip  : "40% rain chance — carry a light jacket."
      color_tip  : "Avoid dark colors in this heat."
    """
    if not weather_context or not weather_context.get("summary"):
        return ""

    wf = weather_context.get("filters", [])
    filters_str = "\n".join(f"  - {f}" for f in wf) if wf else "  - None"

    return f"""
CURRENT WEATHER IN USER'S CITY:
  Conditions : {weather_context['summary']}
  Fabric tip : {weather_context.get('fabric_tip', '')}
  Color tip  : {weather_context.get('color_tip', '')}
  Carry tip  : {weather_context.get('carry_tip', '')}
  Outfit filters (MUST follow):
{filters_str}

You MUST adjust outfit choices to respect these weather conditions.
Ignore weather filters only for strictly indoor events (e.g. office, interview).
"""


# ══════════════════════════════════════════════════════════════════════════════
# OUTFIT FORMULA LIBRARY — COMPLETE & VERIFIED
# Rules: top ≠ bottom color, shoes match style, colors complement skin tone
# ══════════════════════════════════════════════════════════════════════════════

OUTFITS = {
    "dark": {
        "men": [
            {
                "shirt":      "electric blue oversized graphic t-shirt men",
                "pants":      "black slim cargo pants men",
                "shoes":      "white chunky sneakers men",
                "watch":      "silver stainless steel watch men",
                "bracelet":   "black beaded bracelet men",
                "sunglasses": "black rectangular sunglasses men",
                "_label":     "Bold Streetwear — Electric Blue + Black",
                "_styles":    ["streetwear", "bold", "casual"],
                "_events":    ["college", "casual", "party"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "saffron yellow embroidered kurta men",
                "pants":      "off white churidar men",
                "shoes":      "tan kolhapuri sandals men",
                "watch":      "gold dial watch men",
                "bracelet":   "gold kada bracelet men",
                "sunglasses": "gold aviator sunglasses men",
                "_label":     "Ethnic Festive — Saffron + Off-White",
                "_styles":    ["ethnic", "festive"],
                "_events":    ["wedding", "festival", "puja", "reception"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "burnt orange polo shirt slim fit men",
                "pants":      "beige slim chino trousers men",
                "shoes":      "white leather loafers men",
                "watch":      "gold minimalist watch men",
                "bracelet":   "gold chain bracelet men",
                "sunglasses": "brown tortoise frame sunglasses men",
                "_label":     "Smart Casual — Burnt Orange + Beige",
                "_styles":    ["smart casual", "old money", "minimal"],
                "_events":    ["office", "date", "brunch", "casual"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "emerald green slim fit button down shirt men",
                "pants":      "black slim jeans men",
                "shoes":      "black leather loafers men",
                "watch":      "gold watch men",
                "bracelet":   "green beaded bracelet men",
                "sunglasses": "black aviator sunglasses men",
                "_label":     "Jewel Tone — Emerald + Black",
                "_styles":    ["party", "bold", "luxe"],
                "_events":    ["party", "date", "dinner", "club"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "royal blue oxford shirt men slim fit",
                "pants":      "cream linen trousers men wide leg",
                "shoes":      "white clean leather loafers men",
                "watch":      "silver chronograph watch men",
                "bracelet":   "silver chain bracelet men",
                "sunglasses": "black wayfarer sunglasses men",
                "_label":     "Old Money — Royal Blue + Cream",
                "_styles":    ["old money", "preppy", "minimal", "smart casual", "formal"],
                "_events":    ["office", "date", "brunch", "dinner", "interview"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "magenta embroidered kurta men",
                "pants":      "cream palazzo pants men",
                "shoes":      "tan mojri shoes men ethnic",
                "watch":      "rose gold watch men",
                "bracelet":   "rose gold kada men",
                "sunglasses": "gold round metal sunglasses men",
                "_label":     "Vibrant Ethnic — Magenta + Cream",
                "_styles":    ["ethnic", "festive", "bold"],
                "_events":    ["wedding", "sangeet", "festival"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "mustard yellow oversized linen shirt men",
                "pants":      "brown cargo pants men",
                "shoes":      "tan suede sneakers men",
                "watch":      "bronze analog watch men",
                "bracelet":   "brown leather bracelet men",
                "sunglasses": "tortoise shell round sunglasses men",
                "_label":     "Earthy Bold — Mustard + Brown",
                "_styles":    ["streetwear", "casual", "earthy"],
                "_events":    ["casual", "college", "beach"],
                "_weather":   ["hot", "any"],
            },
            {
                "shirt":      "coral red slim fit polo shirt men",
                "pants":      "cream slim chino trousers men",
                "shoes":      "white canvas sneakers men",
                "watch":      "gold analog watch men",
                "bracelet":   "coral beaded bracelet men",
                "sunglasses": "gold metal aviator sunglasses men",
                "_label":     "Coral Fresh — Coral + Cream",
                "_styles":    ["casual", "smart casual"],
                "_events":    ["brunch", "casual", "date"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "deep purple polo shirt men slim",
                "pants":      "champagne beige slim trousers men",
                "shoes":      "white leather sneakers men",
                "watch":      "silver watch men",
                "bracelet":   "purple beaded bracelet men",
                "sunglasses": "black square frame sunglasses men",
                "_label":     "Rich Contrast — Deep Purple + Champagne",
                "_styles":    ["bold", "party", "luxe", "old money"],
                "_events":    ["party", "dinner", "date"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "forest green linen shirt men relaxed fit",
                "pants":      "khaki slim trousers men",
                "shoes":      "white minimal sneakers men",
                "watch":      "olive canvas watch men",
                "bracelet":   "olive beaded bracelet men",
                "sunglasses": "green tinted aviator sunglasses men",
                "_label":     "Forest Urban — Forest Green + Khaki",
                "_styles":    ["casual", "boho", "minimal"],
                "_events":    ["casual", "beach", "brunch"],
                "_weather":   ["hot", "any"],
            },
            {
                "shirt":      "white oxford shirt men slim fit",
                "pants":      "navy blue slim chino trousers men",
                "shoes":      "tan suede loafers men",
                "watch":      "silver minimalist watch men",
                "bracelet":   "silver link bracelet men",
                "sunglasses": "tortoise shell sunglasses men",
                "_label":     "Classic Old Money — White + Navy",
                "_styles":    ["old money", "preppy", "formal", "smart casual", "minimal", "luxe"],
                "_events":    ["office", "interview", "date", "dinner", "brunch"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "white linen shirt men relaxed oversized",
                "pants":      "beige wide leg linen trousers men",
                "shoes":      "tan leather sandals men",
                "watch":      "brown leather strap watch men",
                "bracelet":   "wooden beads bracelet men",
                "sunglasses": "gold aviator sunglasses men",
                "_label":     "Linen Old Money — White Linen + Beige",
                "_styles":    ["old money", "minimal", "boho", "preppy", "luxe"],
                "_events":    ["brunch", "beach", "casual", "date"],
                "_weather":   ["hot", "any"],
            },
        ],
        "women": [
            {
                "top":       "electric blue fitted crop top women",
                "pants":     "white high waist flare trousers women",
                "shoes":     "white platform sneakers women",
                "necklace":  "gold layered statement necklace women",
                "bracelet":  "gold stacked bracelets women",
                "earrings":  "gold hoop earrings women",
                "_label":    "Electric Bold — Blue + White",
                "_styles":   ["bold", "streetwear", "party"],
                "_events":   ["party", "casual", "college"],
                "_weather":  ["any"],
            },
            {
                "top":       "saffron yellow embroidered kurti women",
                "pants":     "white palazzo pants women",
                "shoes":     "gold juttis ethnic footwear women",
                "necklace":  "gold statement kundan necklace women",
                "bracelet":  "gold glass bangles women",
                "earrings":  "gold chandbali earrings women",
                "_label":    "Saffron Festive — Yellow + White",
                "_styles":   ["ethnic", "festive"],
                "_events":   ["wedding", "festival", "puja"],
                "_weather":  ["any"],
            },
            {
                "top":       "burnt orange off-shoulder blouse women",
                "pants":     "beige wide leg linen trousers women",
                "shoes":     "tan block heels women",
                "necklace":  "gold pendant necklace women",
                "bracelet":  "gold bangles women",
                "earrings":  "gold teardrop earrings women",
                "_label":    "Warm Earth — Burnt Orange + Beige",
                "_styles":   ["smart casual", "old money", "boho"],
                "_events":   ["brunch", "date", "casual"],
                "_weather":  ["any"],
            },
            {
                "top":       "emerald green embroidered kurti women",
                "pants":     "cream palazzo pants women",
                "shoes":     "gold juttis ethnic footwear women",
                "necklace":  "gold jhumka necklace set women",
                "bracelet":  "green glass bangles women",
                "earrings":  "gold jhumka earrings women",
                "_label":    "Jewel Ethnic — Emerald + Cream",
                "_styles":   ["ethnic", "festive", "bold"],
                "_events":   ["wedding", "festival"],
                "_weather":  ["any"],
            },
            {
                "top":       "magenta fitted bodysuit women",
                "pants":     "black high waist slim jeans women",
                "shoes":     "black platform heels women",
                "necklace":  "silver chain layered necklace women",
                "bracelet":  "silver stacked bracelets women",
                "earrings":  "silver hoop earrings women",
                "_label":    "Magenta Trendy — Magenta + Black",
                "_styles":   ["bold", "party", "streetwear"],
                "_events":   ["party", "club", "date"],
                "_weather":  ["any"],
            },
            {
                "top":       "white linen blazer women oversized",
                "pants":     "beige wide leg trousers women",
                "shoes":     "nude block heels women",
                "necklace":  "gold minimal pendant necklace women",
                "bracelet":  "gold thin bangles women",
                "earrings":  "gold small hoop earrings women",
                "_label":    "Old Money — White Blazer + Beige",
                "_styles":   ["old money", "minimal", "smart casual", "formal", "luxe", "preppy"],
                "_events":   ["office", "date", "brunch", "interview", "dinner"],
                "_weather":  ["any"],
            },
            {
                "top":       "royal blue off-shoulder blouse women",
                "pants":     "cream wide palazzo pants women",
                "shoes":     "gold flat sandals women",
                "necklace":  "gold layered necklace women",
                "bracelet":  "gold bangles women",
                "earrings":  "gold drop earrings women",
                "_label":    "Royal Boho — Royal Blue + Cream",
                "_styles":   ["boho", "casual", "ethnic"],
                "_events":   ["brunch", "casual", "date"],
                "_weather":  ["any"],
            },
            {
                "top":       "coral red fitted crop top women",
                "pants":     "navy blue wide leg trousers women",
                "shoes":     "nude block heels women",
                "necklace":  "gold pendant necklace women",
                "bracelet":  "coral bead bracelet women",
                "earrings":  "gold hoop earrings women",
                "_label":    "Coral Street — Coral + Navy",
                "_styles":   ["casual", "bold"],
                "_events":   ["casual", "college", "brunch"],
                "_weather":  ["any"],
            },
        ],
    },

    "medium": {
        "men": [
            {
                "shirt":      "olive green oversized graphic t-shirt men",
                "pants":      "khaki cargo pants men",
                "shoes":      "white chunky sneakers men",
                "watch":      "black analog watch men",
                "bracelet":   "olive beaded bracelet men",
                "sunglasses": "brown aviator sunglasses men",
                "_label":     "Earthy Streetwear — Olive + Khaki",
                "_styles":    ["streetwear", "casual", "earthy"],
                "_events":    ["college", "casual", "gym"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "mustard yellow oversized t-shirt men",
                "pants":      "black slim cargo pants men",
                "shoes":      "white chunky sneakers men",
                "watch":      "black digital watch men",
                "bracelet":   "black leather bracelet men",
                "sunglasses": "black rectangular sunglasses men",
                "_label":     "Bold Casual — Mustard + Black",
                "_styles":    ["bold", "streetwear", "casual"],
                "_events":    ["casual", "party", "college"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "navy blue polo shirt men slim fit",
                "pants":      "beige slim chino trousers men",
                "shoes":      "tan leather loafers men",
                "watch":      "brown leather strap watch men",
                "bracelet":   "brown beaded bracelet men",
                "sunglasses": "brown tortoise sunglasses men",
                "_label":     "Smart Navy — Navy + Beige",
                "_styles":    ["smart casual", "old money", "preppy", "formal", "minimal"],
                "_events":    ["office", "date", "interview", "brunch", "dinner"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "white slim fit oxford shirt men",
                "pants":      "camel chino trousers men slim",
                "shoes":      "tan suede loafers men",
                "watch":      "gold minimalist watch men",
                "bracelet":   "brown leather cuff men",
                "sunglasses": "tortoise shell sunglasses men",
                "_label":     "Classic Old Money — White Oxford + Camel",
                "_styles":    ["old money", "minimal", "preppy", "smart casual", "formal", "luxe"],
                "_events":    ["office", "date", "interview", "dinner", "brunch"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "mustard yellow kurta men embroidered",
                "pants":      "off white churidar pants men",
                "shoes":      "tan kolhapuri sandals men leather",
                "watch":      "brown leather analog watch men",
                "bracelet":   "wooden beads bracelet men",
                "sunglasses": "gold metal sunglasses men",
                "_label":     "Ethnic Warm — Mustard Kurta + Off-White",
                "_styles":    ["ethnic", "festive"],
                "_events":    ["wedding", "festival", "puja", "reception"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "burgundy slim fit button down shirt men",
                "pants":      "dark grey slim trousers men",
                "shoes":      "black leather loafers men",
                "watch":      "silver watch men",
                "bracelet":   "maroon beaded bracelet men",
                "sunglasses": "black wayfarer sunglasses men",
                "_label":     "Rich Burgundy — Burgundy + Grey",
                "_styles":    ["party", "bold", "luxe"],
                "_events":    ["party", "dinner", "date"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "rust orange polo shirt men slim fit",
                "pants":      "brown chino trousers men",
                "shoes":      "tan sneakers men",
                "watch":      "bronze analog watch men",
                "bracelet":   "rust beaded bracelet men",
                "sunglasses": "tortoise shell sunglasses men",
                "_label":     "Rust Earth — Rust Orange + Brown",
                "_styles":    ["casual", "boho", "earthy"],
                "_events":    ["casual", "brunch", "beach"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "teal polo shirt slim fit men",
                "pants":      "off white wide leg linen trousers men",
                "shoes":      "white loafers men",
                "watch":      "silver minimalist watch men",
                "bracelet":   "teal beaded bracelet men",
                "sunglasses": "black square sunglasses men",
                "_label":     "Teal Fresh — Teal + Off-White",
                "_styles":    ["smart casual", "minimal", "old money"],
                "_events":    ["office", "date", "brunch"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "forest green oxford shirt men slim",
                "pants":      "camel chino trousers men",
                "shoes":      "white leather sneakers men",
                "watch":      "gold watch men",
                "bracelet":   "green beaded bracelet men",
                "sunglasses": "gold aviator sunglasses men",
                "_label":     "Forest Smart — Forest Green + Camel",
                "_styles":    ["old money", "minimal", "smart casual"],
                "_events":    ["brunch", "office", "date"],
                "_weather":   ["any"],
            },
        ],
        "women": [
            {
                "top":       "burnt orange bodysuit women fitted",
                "pants":     "cream wide leg high waist trousers women",
                "shoes":     "tan block heels women",
                "necklace":  "gold layered necklace women",
                "bracelet":  "gold stacked bracelets women",
                "earrings":  "gold hoop earrings women",
                "_label":    "Burnt Orange Chic",
                "_styles":   ["smart casual", "bold", "old money"],
                "_events":   ["office", "date", "brunch"],
                "_weather":  ["any"],
            },
            {
                "top":       "mustard yellow crop top women fitted",
                "pants":     "brown high waist wide leg trousers women",
                "shoes":     "tan platform sneakers women",
                "necklace":  "gold pendant necklace women",
                "bracelet":  "brown beaded bracelets women",
                "earrings":  "gold hoop earrings women",
                "_label":    "Mustard Chic",
                "_styles":   ["casual", "earthy", "streetwear"],
                "_events":   ["college", "casual", "brunch"],
                "_weather":  ["any"],
            },
            {
                "top":       "teal embroidered kurti women",
                "pants":     "cream palazzo pants women",
                "shoes":     "gold juttis ethnic footwear women",
                "necklace":  "gold layered necklace women",
                "bracelet":  "teal glass bangles women",
                "earrings":  "gold jhumka earrings women",
                "_label":    "Teal Ethnic",
                "_styles":   ["ethnic", "festive"],
                "_events":   ["wedding", "festival"],
                "_weather":  ["any"],
            },
            {
                "top":       "maroon off-shoulder blouse women",
                "pants":     "beige wide leg trousers women",
                "shoes":     "tan strappy heeled sandals women",
                "necklace":  "gold statement necklace women",
                "bracelet":  "gold bangles women",
                "earrings":  "gold chandbali earrings women",
                "_label":    "Maroon Boho",
                "_styles":   ["boho", "party", "date"],
                "_events":   ["date", "party", "dinner"],
                "_weather":  ["any"],
            },
            {
                "top":       "white linen blouse women relaxed",
                "pants":     "beige wide leg trousers women",
                "shoes":     "nude block heels women",
                "necklace":  "gold minimal pendant necklace women",
                "bracelet":  "gold thin bangle women",
                "earrings":  "gold stud earrings women",
                "_label":    "Old Money — White + Beige",
                "_styles":   ["old money", "minimal", "smart casual", "preppy", "luxe", "formal"],
                "_events":   ["office", "interview", "date", "brunch", "dinner"],
                "_weather":  ["any"],
            },
        ],
    },

    "light": {
        "men": [
            {
                "shirt":      "pastel blue oxford shirt men slim fit",
                "pants":      "light grey slim chino trousers men",
                "shoes":      "white minimal leather sneakers men",
                "watch":      "silver minimalist watch men",
                "bracelet":   "silver chain bracelet men",
                "sunglasses": "light blue tinted sunglasses men",
                "_label":     "Pastel Preppy — Pastel Blue + Grey",
                "_styles":    ["preppy", "old money", "minimal", "smart casual"],
                "_events":    ["brunch", "office", "date", "casual"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "mint green polo shirt men slim fit",
                "pants":      "white slim chino trousers men",
                "shoes":      "white clean sneakers men",
                "watch":      "silver watch men",
                "bracelet":   "white beaded bracelet men",
                "sunglasses": "black rectangular sunglasses men",
                "_label":     "Mint Fresh — Mint + White",
                "_styles":    ["casual", "minimal", "old money"],
                "_events":    ["casual", "brunch", "beach"],
                "_weather":   ["hot", "any"],
            },
            {
                "shirt":      "lavender casual linen shirt men",
                "pants":      "cream linen trousers men wide leg",
                "shoes":      "white loafers men clean",
                "watch":      "rose gold watch men",
                "bracelet":   "lavender beaded bracelet men",
                "sunglasses": "rose gold metal sunglasses men",
                "_label":     "Lavender Soft — Lavender + Cream",
                "_styles":    ["minimal", "boho", "old money", "preppy"],
                "_events":    ["brunch", "casual", "date"],
                "_weather":   ["hot", "any"],
            },
            {
                "shirt":      "sage green slim fit button down shirt men",
                "pants":      "beige slim chino trousers men",
                "shoes":      "white leather loafers men",
                "watch":      "silver watch men",
                "bracelet":   "green beaded bracelet men",
                "sunglasses": "green tinted sunglasses men",
                "_label":     "Sage Smart — Sage Green + Beige",
                "_styles":    ["smart casual", "old money", "minimal", "preppy"],
                "_events":    ["office", "date", "brunch", "casual"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "soft pink polo shirt men slim fit",
                "pants":      "ivory slim trousers men",
                "shoes":      "white leather loafers men",
                "watch":      "rose gold minimalist watch men",
                "bracelet":   "pearl beaded bracelet men",
                "sunglasses": "gold aviator sunglasses men",
                "_label":     "Soft Pink Minimal",
                "_styles":    ["minimal", "old money", "preppy"],
                "_events":    ["brunch", "casual", "date"],
                "_weather":   ["any"],
            },
            {
                "shirt":      "white slim fit polo shirt men",
                "pants":      "navy blue slim chino trousers men",
                "shoes":      "tan leather loafers men",
                "watch":      "silver minimal watch men",
                "bracelet":   "silver thin bracelet men",
                "sunglasses": "silver metal aviator sunglasses men",
                "_label":     "Old Money Classic — White Polo + Navy",
                "_styles":    ["old money", "preppy", "minimal", "smart casual", "formal", "luxe"],
                "_events":    ["office", "interview", "date", "dinner", "brunch"],
                "_weather":   ["any"],
            },
        ],
        "women": [
            {
                "top":       "lavender floral blouse women",
                "pants":     "light blue high waist slim jeans women",
                "shoes":     "white platform sneakers women",
                "necklace":  "silver delicate necklace women",
                "bracelet":  "pearl stacked bracelets women",
                "earrings":  "silver stud earrings women",
                "_label":    "Lavender Casual",
                "_styles":   ["casual", "minimal", "preppy"],
                "_events":   ["casual", "college", "brunch"],
                "_weather":  ["any"],
            },
            {
                "top":       "soft pink embroidered kurti women",
                "pants":     "cream palazzo pants women wide",
                "shoes":     "pink juttis ethnic footwear women",
                "necklace":  "rose gold necklace women",
                "bracelet":  "pink glass bangles women",
                "earrings":  "rose gold jhumka earrings women",
                "_label":    "Soft Pink Ethnic",
                "_styles":   ["ethnic", "festive"],
                "_events":   ["wedding", "festival"],
                "_weather":  ["any"],
            },
            {
                "top":       "sky blue off-shoulder crop top women",
                "pants":     "white wide leg trousers women",
                "shoes":     "white platform sneakers women",
                "necklace":  "silver layered necklace women",
                "bracelet":  "silver stacked bracelets women",
                "earrings":  "silver hoop earrings women",
                "_label":    "Sky Blue Fresh",
                "_styles":   ["casual", "bold", "streetwear"],
                "_events":   ["brunch", "casual", "date"],
                "_weather":  ["hot", "any"],
            },
            {
                "top":       "mint green fitted bodysuit women",
                "pants":     "ivory high waist wide leg trousers women",
                "shoes":     "white block heels women",
                "necklace":  "pearl pendant necklace women",
                "bracelet":  "pearl bracelet women",
                "earrings":  "pearl drop earrings women",
                "_label":    "Mint Minimal",
                "_styles":   ["minimal", "old money", "preppy", "smart casual"],
                "_events":   ["office", "date", "brunch"],
                "_weather":  ["any"],
            },
            {
                "top":       "white linen blazer women oversized",
                "pants":     "light grey slim trousers women",
                "shoes":     "white loafers women",
                "necklace":  "pearl pendant necklace women",
                "bracelet":  "silver thin bracelet women",
                "earrings":  "pearl drop earrings women",
                "_label":    "Old Money Minimal — White Blazer + Grey",
                "_styles":   ["old money", "minimal", "formal", "preppy", "smart casual", "luxe"],
                "_events":   ["office", "interview", "date", "dinner", "brunch"],
                "_weather":  ["any"],
            },
        ],
    },
}

# Style keyword → matching labels/tokens
STYLE_KEYWORDS = {
    "old money":    ["old money", "oxford", "polo", "chino", "loafer", "linen", "minimal", "preppy", "slim", "blazer", "white", "navy", "camel", "sage", "beige"],
    "streetwear":   ["streetwear", "cargo", "graphic", "oversized", "sneaker", "urban", "bold", "chunky"],
    "boho":         ["ethnic", "boho", "floral", "kurti", "palazzo", "juttis", "earthy", "linen", "flare"],
    "formal":       ["oxford", "blazer", "slim", "loafer", "chino", "button", "formal", "smart"],
    "ethnic":       ["ethnic", "kurta", "sherwani", "kurti", "jhumka", "chandbali", "mojri", "kolhapuri", "palazzo", "churidar"],
    "casual":       ["casual", "relaxed", "everyday", "polo", "chino", "sneaker"],
    "party":        ["bold", "jewel", "royal", "electric", "deep", "magenta", "bodysuit", "chic", "party"],
    "minimal":      ["minimal", "clean", "white", "pastel", "simple", "sage", "mint", "linen"],
    "smart casual": ["smart", "polo", "chino", "loafer", "slim", "oxford"],
    "luxe":         ["silk", "velvet", "statement", "gold", "jewel", "royal", "luxe", "linen"],
    "preppy":       ["polo", "oxford", "chino", "loafer", "slim", "pastel", "stripe", "navy"],
}

# Weather condition tags that map to formula weather tags
_HOT_KEYWORDS  = ["hot", "warm", "humid", "summer", "heat", "sweat", "sunny", "tropical"]
_COLD_KEYWORDS = ["cold", "cool", "winter", "chilly", "jacket", "wool", "rainy", "wet"]


def _detect_weather_preference(weather_context: dict) -> str:
    """Derive a broad weather tag ('hot' | 'cold' | 'any') from context."""
    if not weather_context:
        return "any"
    summary = (weather_context.get("summary", "") + " " +
               weather_context.get("fabric_tip", "")).lower()
    if any(k in summary for k in _HOT_KEYWORDS):
        return "hot"
    if any(k in summary for k in _COLD_KEYWORDS):
        return "cold"
    return "any"


def _select_formula(
    tone_key:        str,
    gender_label:    str,
    style_keyword:   str  = None,
    event:           str  = None,
    time_of_day:     str  = None,
    weather_context: dict = None,
) -> dict:
    """
    Select the best outfit formula using:
      1. Style keyword scoring
      2. Event matching
      3. Weather filtering (from v1 weather_context)
      4. Random fallback
    """
    formula_list = OUTFITS.get(tone_key, OUTFITS["medium"]).get(gender_label, [])
    weather_pref = _detect_weather_preference(weather_context)

    # Pre-filter by weather if we have strong signal
    if weather_pref == "hot":
        hot_list = [f for f in formula_list if "hot" in f.get("_weather", ["any"])]
        if hot_list:
            formula_list = hot_list

    chosen = None

    # 1. Style keyword scoring
    if style_keyword and style_keyword in STYLE_KEYWORDS:
        tokens = STYLE_KEYWORDS[style_keyword]
        scored = []
        for f in formula_list:
            f_styles = [s.lower() for s in f.get("_styles", [])]
            f_text   = " ".join(str(v) for v in f.values()).lower()
            score    = sum(1 for tok in tokens if tok in f_styles or tok in f_text)
            scored.append((score, f))
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored and scored[0][0] > 0:
            best = scored[0][0]
            top  = [f for s, f in scored if s == best]
            chosen = random.choice(top)
            print(f"👔 STYLE '{style_keyword}' → {chosen.get('_label', '')}")

    # 2. Event matching
    if not chosen and event:
        event_low = event.lower()
        if any(w in event_low for w in ["wedding", "reception", "festival", "puja", "sangeet"]):
            ethnic = [f for f in formula_list if "ethnic" in [s.lower() for s in f.get("_styles", [])]]
            chosen = random.choice(ethnic) if ethnic else None
        elif any(w in event_low for w in ["office", "interview", "work"]):
            smart  = [f for f in formula_list if any(s in f.get("_styles", []) for s in ["smart casual", "formal", "old money", "minimal"])]
            chosen = random.choice(smart) if smart else None
        elif time_of_day == "night" and any(w in event_low for w in ["party", "club", "dinner", "date"]):
            night  = [f for f in formula_list if any(s in f.get("_styles", []) for s in ["party", "bold", "luxe"])]
            chosen = random.choice(night) if night else None

    if not chosen:
        chosen = random.choice(formula_list)

    return chosen


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def generate_outfit_recommendation(
    skin_tone:       str,
    face_shape:      str,
    body_shape:      str  = "average",
    gender:          str  = "male",
    style_keyword:   str  = None,
    event:           str  = None,
    user_message:    str  = None,
    weather_context: dict = None,
) -> dict:
    """
    Returns { category: "search query" } from pre-verified outfit formulas.

    Parameters
    ----------
    skin_tone       : "dark" | "medium" | "light"
    face_shape      : e.g. "oval", "round", "square"
    body_shape      : e.g. "average", "athletic", "slim"  (informational, passed to LLM)
    gender          : "male" | "female" / "men" | "women" / etc.
    style_keyword   : e.g. "old money", "streetwear", "ethnic" — overrides auto-detect
    event           : e.g. "wedding", "office", "party"
    user_message    : raw user text for style auto-detection
    weather_context : dict with keys summary, filters, fabric_tip, carry_tip, color_tip
                      Injected into formula selection AND returned as extra metadata.
    """
    gender_label = "women" if gender.lower() in ("female", "women", "woman", "girl", "f") else "men"
    tone_key     = skin_tone.lower()
    if tone_key not in OUTFITS:
        tone_key = "medium"

    # Auto-detect style keyword from user message if not explicitly passed
    if not style_keyword and user_message:
        msg_low = user_message.lower()
        for sk in STYLE_KEYWORDS:
            if sk in msg_low:
                style_keyword = sk
                break

    print(f"👔 OUTFIT → tone={tone_key} | face={face_shape} | gender={gender_label} | style={style_keyword} | event={event}")
    if weather_context:
        print(f"🌤 WEATHER → {weather_context.get('summary', '')}")

    chosen = _select_formula(tone_key, gender_label, style_keyword, event,
                             weather_context=weather_context)
    label  = chosen.get("_label", "")
    print(f"👔 CHOSEN: {label}")

    # Build output — strip metadata keys, append "India"
    output = {}
    for k, v in chosen.items():
        if k.startswith("_"):
            continue
        output[k] = f"{v} India"

    # Optionally surface carry_tip so the frontend can display it
    if weather_context and weather_context.get("carry_tip"):
        output["_carry_tip"] = weather_context["carry_tip"]

    print(f"👔 QUERIES: {output}")
    return output


def generate_outfit_for_context(
    skin_tone:       str,
    face_shape:      str,
    gender:          str,
    user_message:    str,
    event:           str  = None,
    time_of_day:     str  = None,
    conditions:      list = None,
    weather_context: dict = None,
) -> tuple:
    """
    Full RAG + LLM + formula pipeline for the chatbot.

    Returns
    -------
    (products_dict, outfit_queries_dict, label_str, ai_explanation_str)

    weather_context is injected into:
      • _select_formula  (formula pre-filtering)
      • LLM prompt       (narrative explanation, fabric/color guidance)
    """
    from services.product_service import get_product_recommendations

    gender_label = "women" if gender.lower() in ("female", "women", "woman", "girl", "f") else "men"
    tone_key     = skin_tone.lower() if skin_tone.lower() in OUTFITS else "medium"

    # Detect style from user message
    style_keyword = None
    msg_low       = user_message.lower()
    for sk in STYLE_KEYWORDS:
        if sk in msg_low:
            style_keyword = sk
            break

    # RAG retrieval
    rag_query = f"{user_message} {skin_tone} skin {face_shape} face {gender_label} outfit style"
    if event:
        rag_query += f" {event}"
    if style_keyword:
        rag_query += f" {style_keyword}"
    rag_context = _rag(rag_query)

    # Select formula (weather-aware)
    chosen = _select_formula(tone_key, gender_label, style_keyword, event, time_of_day,
                             weather_context=weather_context)
    label         = chosen.get("_label", "")
    outfit_queries = {k: f"{v} India" for k, v in chosen.items() if not k.startswith("_")}

    # Fetch products
    products = {}
    for cat, query in outfit_queries.items():
        try:
            prods = get_product_recommendations(query.replace(" India", "").strip(), cat)
            if prods and not (len(prods) == 1 and "Search:" in prods[0].get("title", "")):
                products[cat] = prods[:4]
        except Exception as e:
            print(f"Fashion fetch [{cat}]: {e}")

    # ── LLM narrative (weather-aware, from v1 pattern) ───────────────────────
    weather_block = _build_weather_block(weather_context)

    is_female     = gender_label == "women"
    accessory_note = (
        "Can include necklace, earrings, bracelet, handbag, bindi."
        if is_female else
        "Watch, bracelet, sunglasses, belt. No necklace or earrings for men."
    )

    narrative_prompt = f"""You are a world-class Indian fashion stylist.
Explain why this outfit works for the person below. Keep it to 3–4 sentences.

PERSON:
  Skin tone : {skin_tone}
  Face shape : {face_shape}
  Gender    : {gender}
  Event     : {event or 'general'}
  Style     : {style_keyword or 'not specified'}
{weather_block}
CHOSEN OUTFIT: {label}
OUTFIT QUERIES: {json.dumps(outfit_queries, indent=2)}

RAG CONTEXT (for reference):
{rag_context[:800]}

RULES:
- Mention why the colors suit {skin_tone} skin
- If weather context is present, mention one fabric/color choice driven by it
- {accessory_note}
- Do NOT recommend different items — only explain the chosen outfit

Reply in 3–4 concise sentences, no bullet points.
"""

    try:
        llm_response = llm.invoke(narrative_prompt)
        ai_explanation = llm_response.content if hasattr(llm_response, "content") else str(llm_response)
    except Exception as e:
        print(f"LLM narrative error: {e}")
        ai_explanation = f"This {label} look is styled to complement your {skin_tone} skin tone and {face_shape} face shape."

    return products, outfit_queries, label, ai_explanation