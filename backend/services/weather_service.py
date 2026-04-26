"""
weather_service.py — FaceFit Weather-Aware Outfit Filtering
=============================================================
Uses Open-Meteo (free, no API key needed) to fetch current weather
for any Indian city, then returns outfit filtering rules that the
fashion_routes.py and closet_agent.py can use.

Usage in fashion_routes.py:
    from services.weather_service import get_weather_filters
    weather = get_weather_filters(city="Hyderabad")
    # Pass weather["filters"] into the outfit generation prompt

No new packages needed — uses only `requests` (already installed).
"""

import requests
import os
import logging
from datetime import datetime

log = logging.getLogger("weather_service")

# ── Indian city coordinates (top 20 cities) ────────────────────────────────
CITY_COORDS = {
    "hyderabad":   (17.385044, 78.486671),
    "mumbai":      (19.076090, 72.877426),
    "delhi":       (28.613939, 77.209023),
    "bangalore":   (12.971599, 77.594566),
    "bengaluru":   (12.971599, 77.594566),
    "chennai":     (13.082680, 80.270721),
    "kolkata":     (22.572646, 88.363895),
    "pune":        (18.520430, 73.856743),
    "ahmedabad":   (23.022505, 72.571362),
    "jaipur":      (26.922070, 75.778885),
    "lucknow":     (26.846694, 80.946166),
    "surat":       (21.170240, 72.831062),
    "chandigarh":  (30.733315, 76.779418),
    "indore":      (22.719568, 75.857727),
    "bhopal":      (23.259933, 77.412615),
    "patna":       (25.594095, 85.137566),
    "kochi":       (9.931233,  76.267304),
    "visakhapatnam":(17.686816, 83.218482),
    "nagpur":      (21.145800, 79.088158),
    "coimbatore":  (11.016844, 76.955833),
}


def _get_coords(city: str) -> tuple[float, float]:
    """Return (lat, lon) for a city. Defaults to Hyderabad."""
    return CITY_COORDS.get(city.lower().strip(), CITY_COORDS["hyderabad"])


def fetch_weather(city: str = "Hyderabad") -> dict | None:
    """
    Fetch current weather from Open-Meteo (free, no key).
    Returns raw weather dict or None on failure.
    """
    lat, lon = _get_coords(city)
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current_weather=true"
        f"&hourly=relativehumidity_2m,precipitation_probability,apparent_temperature"
        f"&timezone=Asia/Kolkata"
        f"&forecast_days=1"
    )
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current_weather", {})

        # Get current hour index for humidity and precipitation
        hourly        = data.get("hourly", {})
        current_hour  = datetime.now().hour
        humidity_list = hourly.get("relativehumidity_2m", [])
        precip_list   = hourly.get("precipitation_probability", [])
        feels_list    = hourly.get("apparent_temperature", [])

        humidity     = humidity_list[current_hour]   if len(humidity_list) > current_hour else None
        precip_prob  = precip_list[current_hour]     if len(precip_list)   > current_hour else None
        feels_like   = feels_list[current_hour]      if len(feels_list)    > current_hour else None

        return {
            "city":           city,
            "temperature":    current.get("temperature"),
            "feels_like":     feels_like,
            "windspeed":      current.get("windspeed"),
            "weathercode":    current.get("weathercode"),
            "humidity":       humidity,
            "precip_prob":    precip_prob,
            "is_daytime":     bool(current.get("is_day", 1)),
        }
    except Exception as e:
        log.warning(f"Weather fetch failed for {city}: {e}")
        return None


def get_weather_filters(city: str = "Hyderabad") -> dict:
    """
    Main entry point. Returns:
    {
        "weather": { raw weather dict },
        "filters": { list of outfit filter rules as strings },
        "fabric_tip": str,
        "carry_tip": str,
        "color_tip": str,
    }
    These strings can be injected directly into the LLM outfit prompt.
    """
    weather = fetch_weather(city)
    if not weather:
        return {
            "weather": None,
            "filters": [],
            "fabric_tip": "",
            "carry_tip": "",
            "color_tip": "",
        }

    temp       = weather.get("temperature")    or 25
    feels      = weather.get("feels_like")     or temp
    humidity   = weather.get("humidity")       or 50
    precip     = weather.get("precip_prob")    or 0
    windspeed  = weather.get("windspeed")      or 0
    weathercode= weather.get("weathercode")    or 0

    filters    = []
    fabric_tip = ""
    carry_tip  = ""
    color_tip  = ""

    # ── Temperature rules ─────────────────────────────────────────────────────
    if temp >= 38:
        filters.append("EXCLUDE: heavy fabrics, dark colors, blazers, jackets, jeans, full-sleeve shirts")
        filters.append("PREFER: linen, cotton, loose-fit, breathable light colors")
        fabric_tip = "It's very hot — recommend linen, cotton, or moisture-wicking fabrics only."
        color_tip  = "Avoid dark colors that absorb heat. Prefer whites, pastels, and light neutrals."

    elif temp >= 32:
        filters.append("EXCLUDE: heavy jackets, woollen blazers, full-sleeve thick shirts")
        filters.append("PREFER: cotton, linen, breathable fabrics; half-sleeves preferred")
        fabric_tip = "Warm weather — lightweight breathable fabrics recommended."
        color_tip  = "Light and neutral colors are best in this heat."

    elif temp >= 24:
        filters.append("NEUTRAL: Standard outfit rules apply — no strong temperature restrictions")
        fabric_tip = "Pleasant weather — most fabrics work well."

    elif temp >= 16:
        filters.append("PREFER: light layering — a jacket or blazer over a shirt works well")
        fabric_tip = "Mildly cool — light layers like a denim jacket or cardigan are perfect."

    elif temp >= 8:
        filters.append("PREFER: warm layers — sweater, jacket, full sleeves essential")
        filters.append("EXCLUDE: shorts, sleeveless tops, beach wear")
        fabric_tip = "Cool weather — recommend warm layers, sweaters, and jackets."

    else:
        filters.append("PREFER: heavy winter layers — coat, sweater, thermal wear essential")
        filters.append("EXCLUDE: shorts, T-shirts, light fabrics")
        fabric_tip = "Cold weather — heavy layering is essential."

    # ── Humidity rules ────────────────────────────────────────────────────────
    if humidity >= 80:
        filters.append("HIGH HUMIDITY: avoid synthetic fabrics that trap moisture; prefer cotton or linen")
        fabric_tip += " High humidity — avoid synthetics."

    # ── Rain rules ────────────────────────────────────────────────────────────
    if precip >= 70:
        carry_tip = "High chance of rain — recommend carrying a light jacket or umbrella. Avoid suede shoes."
        filters.append("RAIN LIKELY: avoid suede, open-toe shoes; recommend water-resistant footwear")

    elif precip >= 40:
        carry_tip = "Some chance of rain — a packable jacket is a good idea."

    # ── Wind rules ─────────────────────────────────────────────────────────────
    if windspeed >= 30:
        carry_tip += " Windy — avoid loose scarves or very oversized silhouettes."

    # ── Weather code rules (WMO codes) ────────────────────────────────────────
    # 0=clear, 1-3=partly cloudy, 45-48=fog, 51-67=rain, 71-77=snow, 80-99=storm
    if weathercode >= 80:
        filters.append("STORM/HEAVY RAIN: strongly prefer water-resistant or indoor-suitable outfits")
        carry_tip = "Stormy conditions — stay indoors if possible; waterproof jacket essential."
    elif weathercode >= 51:
        filters.append("RAINY: avoid light fabrics that become see-through when wet; prefer darker colors")

    return {
        "weather":    weather,
        "filters":    filters,
        "fabric_tip": fabric_tip.strip(),
        "carry_tip":  carry_tip.strip(),
        "color_tip":  color_tip.strip(),
        "summary": (
            f"{temp}°C, {humidity}% humidity"
            + (f", {precip}% rain chance" if precip else "")
            + f" in {city}"
        ),
    }