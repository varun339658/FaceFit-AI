/**
 * ColorPaletteWheel.jsx — Visual Color Palette for Outfit Combinations
 * Feature 8: Shows color wheel + harmony scores for any outfit
 */
import { useState, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

// Harmony angle → label
function harmonyLabel(score) {
  if (score >= 0.85) return { label: "✦ Perfect", color: "#2d7a4f" };
  if (score >= 0.65) return { label: "✓ Good", color: "#c8a55a" };
  if (score >= 0.4)  return { label: "~ OK", color: "#8a7a6a" };
  return { label: "⚠ Clash", color: "#c05050" };
}

function ColorSwatch({ hex, name, category, size = 56 }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 5 }}>
      <div style={{
        width: size, height: size, borderRadius: "50%",
        background: hex,
        border: "2px solid rgba(0,0,0,.08)",
        boxShadow: `0 4px 14px ${hex}44`,
        transition: "transform .2s",
        cursor: "default",
      }} title={`${name}: ${hex}`} />
      <div style={{ fontSize: 9.5, color: "#8a7a6a", textAlign: "center", maxWidth: size + 10, lineHeight: 1.3 }}>
        <div style={{ fontWeight: 600, color: "#3a2e24" }}>{(category || "").replace(/_/g," ")}</div>
        <div>{name?.split(" ").slice(-1)[0]}</div>
      </div>
    </div>
  );
}

function HarmonyArc({ score, size = 80 }) {
  const r = 32, cx = 40, cy = 40;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score * circ);
  const { color } = harmonyLabel(score);
  const pct = Math.round(score * 100);
  return (
    <svg width={size} height={size} viewBox="0 0 80 80">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f0ebe4" strokeWidth={7} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color}
        strokeWidth={7} strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round" transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dashoffset .7s ease" }} />
      <text x={cx} y={cy + 5} textAnchor="middle"
        style={{ fontSize: 14, fontWeight: 700, fill: color, fontFamily: "'DM Sans',sans-serif" }}>
        {pct}%
      </text>
    </svg>
  );
}

export default function ColorPaletteWheel({ userId, outfitItems, skinTone = "medium" }) {
  const [palette, setPalette]   = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (outfitItems?.length > 0) {
      fetchPaletteFromItems(outfitItems);
    } else if (userId) {
      fetchPaletteFromWardrobe();
    }
  }, [userId, outfitItems]);

  const fetchPaletteFromItems = async (items) => {
    // Generate palette client-side from item colors (no API call needed)
    const generatePaletteClientSide = null;
    // Fallback: call API with item_ids
    const ids = items.map(i => i.item_id).filter(Boolean).join(",");
    if (!ids && !userId) return;
    fetchPaletteFromWardrobe(ids);
  };

  const fetchPaletteFromWardrobe = async (ids = "") => {
    const uid = userId || "guest";
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ skin_tone: skinTone });
      if (ids) params.append("items", ids);
      const r = await axios.get(`${API}/closet/color-palette/${uid}?${params}`);
      setPalette(r.data);
    } catch (e) {
      setError("Could not load color palette.");
    }
    setLoading(false);
  };

  if (loading) return (
    <div style={{ fontSize: 12, color: "#c8a55a", padding: "12px 0", display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ width: 12, height: 12, border: "2px solid #c8a55a", borderTopColor: "transparent", borderRadius: "50%", display: "inline-block", animation: "spin .8s linear infinite" }} />
      Analyzing colors...
    </div>
  );

  if (error) return null;
  if (!palette?.palette?.length) return null;

  const { label: hLabel, color: hColor } = harmonyLabel(palette.harmony_score);

  return (
    <div style={{ marginTop: 14, maxWidth: 680 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, cursor: "pointer" }}
        onClick={() => setExpanded(v => !v)}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "conic-gradient(#d32f2f,#f9a825,#2e7d32,#1565c0,#6a1b9a,#d32f2f)", flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: 11.5, fontWeight: 600, color: "#2c1f0f" }}>Outfit Color Palette</div>
            <div style={{ fontSize: 10, color: hColor, fontWeight: 600 }}>{hLabel} · {Math.round(palette.harmony_score * 100)}% harmony</div>
          </div>
        </div>
        <span style={{ fontSize: 12, color: "#c8a55a", fontWeight: 700 }}>{expanded ? "▲ Hide" : "▼ Show"}</span>
      </div>

      {expanded && (
        <div style={{ background: "#fff", border: "1px solid #ece6dc", borderRadius: 14, padding: "18px 20px", animation: "fadeUp .25s ease" }}>
          {/* Color swatches row */}
          <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 18, alignItems: "flex-start" }}>
            {palette.palette.slice(0, 8).map((item, i) => (
              <ColorSwatch key={i} hex={item.hex} name={item.color_name} category={item.category} />
            ))}
          </div>

          {/* Harmony score arc */}
          <div style={{ display: "flex", alignItems: "center", gap: 18, padding: "14px 16px", background: "rgba(200,165,90,.04)", borderRadius: 10, border: "1px solid rgba(200,165,90,.15)", marginBottom: 14 }}>
            <HarmonyArc score={palette.harmony_score} />
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: hColor, marginBottom: 4 }}>{hLabel} Color Harmony</div>
              <div style={{ fontSize: 11.5, color: "#5a4838", lineHeight: 1.6 }}>
                {palette.harmony_score >= 0.85 && "These colors work beautifully together — a visually cohesive outfit."}
                {palette.harmony_score >= 0.65 && palette.harmony_score < 0.85 && "Good color combination — these pieces complement each other well."}
                {palette.harmony_score >= 0.4 && palette.harmony_score < 0.65 && "Wearable combination — consider adding a neutral to tie it together."}
                {palette.harmony_score < 0.4 && "These colors clash — try swapping one piece for a more neutral shade."}
              </div>
            </div>
          </div>

          {/* Pair scores */}
          {palette.pair_scores?.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 9, letterSpacing: ".22em", textTransform: "uppercase", color: "#b8a898", fontWeight: 700, marginBottom: 8 }}>Pair Analysis</div>
              {palette.pair_scores.slice(0, 4).map((pair, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                  <div style={{ width: 12, height: 12, borderRadius: "50%", background: pair.color1, border: "1px solid rgba(0,0,0,.1)", flexShrink: 0 }} />
                  <span style={{ fontSize: 9, color: "#c4b4a4" }}>+</span>
                  <div style={{ width: 12, height: 12, borderRadius: "50%", background: pair.color2, border: "1px solid rgba(0,0,0,.1)", flexShrink: 0 }} />
                  <div style={{ flex: 1, height: 4, background: "#f0ebe4", borderRadius: 2, overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${pair.score * 100}%`, background: harmonyLabel(pair.score).color, borderRadius: 2, transition: "width .5s ease" }} />
                  </div>
                  <span style={{ fontSize: 10, color: harmonyLabel(pair.score).color, fontWeight: 600, minWidth: 55 }}>{pair.label}</span>
                </div>
              ))}
            </div>
          )}

          {/* Accent suggestions for skin tone */}
          {palette.accent_suggestions?.length > 0 && (
            <div>
              <div style={{ fontSize: 9, letterSpacing: ".22em", textTransform: "uppercase", color: "#b8a898", fontWeight: 700, marginBottom: 8 }}>Accent Colors for Your Skin Tone</div>
              <div style={{ display: "flex", gap: 10 }}>
                {palette.accent_suggestions.map((acc, i) => (
                  <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                    <div style={{ width: 30, height: 30, borderRadius: "50%", background: acc.hex, border: "2px solid rgba(0,0,0,.08)", boxShadow: `0 2px 8px ${acc.hex}44` }} />
                    <div style={{ fontSize: 8.5, color: "#b8a898", textAlign: "center" }}>Accent</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}