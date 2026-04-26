/**
 * WeatherBanner.jsx — FaceFit Weather Strip
 * ===========================================
 * A small dismissible banner shown above outfit recommendations
 * when weather-based filtering was applied.
 *
 * Usage in Chatbot.jsx — place above outfit cards when msg.weather exists:
 *   {msg.weather?.summary && <WeatherBanner weather={msg.weather} />}
 */

import { useState } from "react";

const WEATHER_ICON = (summary = "") => {
  const s = summary.toLowerCase();
  if (s.includes("rain") || s.includes("storm")) return "🌧️";
  if (s.includes("humid"))  return "💧";
  const temp = parseFloat(s.match(/(\d+)°/)?.[1] || "25");
  if (temp >= 38) return "🔥";
  if (temp >= 30) return "☀️";
  if (temp >= 20) return "🌤️";
  if (temp >= 12) return "🧥";
  return "❄️";
};

export default function WeatherBanner({ weather }) {
  const [dismissed, setDismissed] = useState(false);
  if (!weather || dismissed) return null;

  const icon    = WEATHER_ICON(weather.summary);
  const tips    = [weather.fabric_tip, weather.carry_tip, weather.color_tip].filter(Boolean);

  return (
    <div style={{
      background: "#fffbf5", border: "1px solid #e8ddd0",
      borderRadius: 10, padding: "10px 14px",
      marginBottom: 12, fontSize: 12,
      display: "flex", gap: 10, alignItems: "flex-start",
    }}>
      <span style={{ fontSize: 18, lineHeight: 1 }}>{icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 500, color: "#1a1208", marginBottom: 3 }}>
          {weather.summary}
        </div>
        {tips.length > 0 && (
          <div style={{ color: "#8a7a6a", lineHeight: 1.5 }}>
            {tips.join(" · ")}
          </div>
        )}
      </div>
      <button
        onClick={() => setDismissed(true)}
        style={{
          background: "none", border: "none", color: "#b8a898",
          cursor: "pointer", fontSize: 14, padding: "0 2px", lineHeight: 1,
        }}
      >✕</button>
    </div>
  );
}