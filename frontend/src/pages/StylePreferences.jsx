/**
 * StylePreferences.jsx — Learned Style Preferences Panel
 * ========================================================
 * Shows the user what the AI has learned about their style.
 * Add as a tab in Chatbot.jsx (preferences tab) or as a section.
 *
 * Usage:
 *   import StylePreferences from "./StylePreferences";
 *   <StylePreferences userId={user.name} />
 */

import { useState, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const CAT_EMOJI = {
  shirt:"👕", pants:"👖", shoes:"👟", ethnic:"🥻", accessories:"💍",
  dress:"👗", blazer:"🧥", watch:"⌚", top:"👚", jacket:"🧥",
  track_pants:"🩳", gym_tshirt:"💪", sports_shoes:"👟",
};

const COLOR_HEX = {
  black:"#1a1a1a", white:"#f5f5f0", grey:"#9e9e9e", navy:"#0d2b6e",
  blue:"#1565c0", green:"#2e7d32", red:"#d32f2f", yellow:"#f9a825",
  mustard:"#f57f17", teal:"#00695c", burgundy:"#880e4f", maroon:"#7b1f1f",
  olive:"#6d7c1e", cream:"#f5f0dc", beige:"#d7c4a3", lavender:"#9575cd",
  mint:"#80cbc4", orange:"#e65100", pink:"#c2185b", coral:"#e64a19",
  "electric blue":"#0288d1", saffron:"#ff8f00", terracotta:"#bf360c",
  "royal blue":"#1565c0", emerald:"#00897b", brown:"#4e342e",
  "dark green":"#1b5e20", "light blue":"#90caf9", gold:"#f9a825",
  "navy blue":"#0d2b6e",
};

function getHex(color) {
  if (!color) return "#c8a55a";
  const lc = color.toLowerCase().trim();
  if (COLOR_HEX[lc]) return COLOR_HEX[lc];
  for (const [k, v] of Object.entries(COLOR_HEX)) {
    if (lc.includes(k)) return v;
  }
  return "#c8a55a";
}

function ColorDot({ color, size = 14 }) {
  const hex = getHex(color);
  return (
    <span style={{
      display: "inline-block", width: size, height: size,
      borderRadius: "50%", background: hex,
      border: "1.5px solid rgba(0,0,0,.1)", flexShrink: 0,
      boxShadow: `0 0 5px ${hex}44`,
    }}/>
  );
}

export default function StylePreferences({ userId }) {
  const [prefs,   setPrefs]   = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    if (userId) load();
  }, [userId]);

  const load = async () => {
    setLoading(true);
    try {
      const [prefR, histR] = await Promise.all([
        axios.get(`${API}/outfit/preferences/${userId}`),
        axios.get(`${API}/outfit/feedback-history/${userId}`),
      ]);
      setPrefs(prefR.data);
      setHistory(histR.data.history || []);
    } catch(e) {
      console.error("Load prefs error:", e);
    }
    setLoading(false);
  };

  const handleReset = async () => {
    if (!window.confirm("Reset all learned preferences? The AI will start fresh.")) return;
    setResetting(true);
    try {
      await axios.post(`${API}/outfit/reset-preferences/${userId}`);
      await load();
    } catch(e) { console.error("Reset error:", e); }
    setResetting(false);
  };

  if (loading) return (
    <div style={{ padding: "32px 0", textAlign: "center", color: "#a8998a", fontSize: 13, fontFamily: "'DM Sans',sans-serif" }}>
      Loading your style profile...
    </div>
  );

  const summary  = prefs?.summary || {};
  const prefData = prefs?.preferences || {};
  const totalInteractions = summary.total_interactions || 0;
  const rejectedColors = prefData.rejected_colors || {};
  const preferredColors = prefData.preferred_colors || {};
  const hasData = totalInteractions > 0;

  return (
    <div style={{ fontFamily: "'DM Sans',sans-serif", maxWidth: 680, padding: "0 0 40px" }}>
      <style>{`
        @keyframes sp-fadeup{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        .sp-tab{padding:11px 16px;border:none;border-bottom:2px solid transparent;background:none;font-family:'DM Sans',sans-serif;font-size:12px;font-weight:500;color:#a8998a;cursor:pointer;transition:all .18s;white-space:nowrap}
        .sp-tab.active{color:#8a5820;border-bottom-color:#c8a55a;font-weight:600}
        .sp-chip-rej{padding:4px 10px;border-radius:14px;background:rgba(192,57,43,.08);border:1px solid rgba(192,57,43,.2);font-size:11px;color:#c0392b;display:flex;align-items:center;gap:5px;font-weight:500}
        .sp-chip-acc{padding:4px 10px;border-radius:14px;background:rgba(45,122,79,.08);border:1px solid rgba(45,122,79,.2);font-size:11px;color:#2d7a4f;display:flex;align-items:center;gap:5px;font-weight:500}
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
          <div>
            <h2 style={{ fontFamily: "'Cormorant Garamond',serif", fontWeight: 300, fontSize: 30, color: "#1a1208", margin: "0 0 4px" }}>
              My Style <em style={{ fontStyle: "italic", color: "#c8a55a" }}>Profile</em>
            </h2>
            <p style={{ fontSize: 12.5, color: "#8a7a6a", margin: 0 }}>
              {hasData
                ? `Based on ${totalInteractions} interactions — your AI stylist keeps learning.`
                : "Rate outfits and replace items to train your personal AI stylist."
              }
            </p>
          </div>
          {hasData && (
            <button
              onClick={handleReset}
              disabled={resetting}
              style={{
                padding: "7px 14px", background: "rgba(192,57,43,.07)",
                border: "1px solid rgba(192,57,43,.2)", borderRadius: 20,
                fontFamily: "inherit", fontSize: 11, color: "#c0392b",
                cursor: "pointer",
              }}
            >
              {resetting ? "Resetting..." : "Reset Preferences"}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #ece6dc", marginBottom: 20, overflow: "auto" }}>
        {[
          ["overview", "📊 Overview"],
          ["dislikes", `🚫 Dislikes (${Object.values(rejectedColors).flat().length})`],
          ["likes",    `❤ Loves (${Object.values(preferredColors).flat().length})`],
          ["history",  `📋 History (${history.length})`],
        ].map(([id, label]) => (
          <button key={id} className={`sp-tab${tab===id?" active":""}`} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW ──────────────────────────────────────────────────────── */}
      {tab === "overview" && (
        <div style={{ animation: "sp-fadeup .3s ease" }}>
          {!hasData ? (
            <div style={{ textAlign: "center", padding: "40px 20px" }}>
              <div style={{ fontSize: 42, marginBottom: 14 }}>🎨</div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#1a0f00", marginBottom: 8, fontFamily: "'Cormorant Garamond',serif" }}>
                Your Style Profile is Empty
              </div>
              <div style={{ fontSize: 12.5, color: "#8a7a6a", lineHeight: 1.7, maxWidth: 320, margin: "0 auto 20px" }}>
                When you click <strong>"Replace This"</strong> or <strong>"❤ Love it"</strong> on any outfit item in the chatbot, the AI learns your style and gets smarter.
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 320, margin: "0 auto", textAlign: "left" }}>
                {[
                  ["🔄", "Replace an item → AI avoids that style next time"],
                  ["❤", "Love an item → AI recommends more like it"],
                  ["✕ Wrong color", "Pick a reject reason → AI avoids that color"],
                ].map(([icon, text], i) => (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "10px 14px", background: "#faf7f3", border: "1px solid #ece6dc", borderRadius: 10 }}>
                    <span style={{ fontSize: 16, flexShrink: 0 }}>{icon}</span>
                    <span style={{ fontSize: 12.5, color: "#3a2e24", lineHeight: 1.5 }}>{text}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* Stats row */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12, marginBottom: 20 }}>
                {[
                  { label: "Interactions", value: totalInteractions, color: "#c8a55a", bg: "rgba(200,165,90,.08)" },
                  { label: "Items Loved",  value: (prefData.accepted_items||[]).length, color: "#2d7a4f", bg: "rgba(45,122,79,.08)" },
                  { label: "Items Replaced", value: (prefData.rejected_items||[]).length, color: "#c0392b", bg: "rgba(192,57,43,.08)" },
                ].map(({ label, value, color, bg }) => (
                  <div key={label} style={{ padding: "16px 14px", background: bg, border: `1px solid ${color}22`, borderRadius: 12, textAlign: "center" }}>
                    <div style={{ fontSize: 28, fontWeight: 300, color, fontFamily: "'Cormorant Garamond',serif", lineHeight: 1 }}>{value}</div>
                    <div style={{ fontSize: 10, color: "#8a7a6a", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".1em", marginTop: 5 }}>{label}</div>
                  </div>
                ))}
              </div>

              {/* Quick summary */}
              {(summary.top_rejected||[]).length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 10, letterSpacing: ".2em", textTransform: "uppercase", color: "#a8998a", fontWeight: 700, marginBottom: 8 }}>
                    🚫 AI Will Avoid
                  </div>
                  <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
                    {summary.top_rejected.map((item, i) => (
                      <div key={i} className="sp-chip-rej">✕ {item}</div>
                    ))}
                  </div>
                </div>
              )}
              {(summary.top_accepted||[]).length > 0 && (
                <div>
                  <div style={{ fontSize: 10, letterSpacing: ".2em", textTransform: "uppercase", color: "#a8998a", fontWeight: 700, marginBottom: 8 }}>
                    ❤ AI Will Suggest More Of
                  </div>
                  <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
                    {summary.top_accepted.map((item, i) => (
                      <div key={i} className="sp-chip-acc">✓ {item}</div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── DISLIKES ──────────────────────────────────────────────────────── */}
      {tab === "dislikes" && (
        <div style={{ animation: "sp-fadeup .3s ease" }}>
          {Object.keys(rejectedColors).length === 0 ? (
            <div style={{ padding: "32px 0", textAlign: "center", color: "#b8a898", fontSize: 13 }}>
              No dislikes recorded yet. Replace items in the chatbot to train your stylist.
            </div>
          ) : (
            Object.entries(rejectedColors).map(([cat, colors]) => (
              <div key={cat} style={{ marginBottom: 18, padding: "14px 18px", background: "rgba(192,57,43,.03)", border: "1px solid rgba(192,57,43,.12)", borderRadius: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <span style={{ fontSize: 18 }}>{CAT_EMOJI[cat] || "👕"}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#2c1f0f", textTransform: "capitalize" }}>{cat.replace(/_/g," ")}</span>
                  <span style={{ fontSize: 10, color: "#c0392b", background: "rgba(192,57,43,.1)", padding: "1px 8px", borderRadius: 10, fontWeight: 700 }}>
                    {colors.length} avoided
                  </span>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {colors.map((color, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", background: "#fff", border: "1px solid rgba(192,57,43,.2)", borderRadius: 20 }}>
                      <ColorDot color={color}/>
                      <span style={{ fontSize: 11, color: "#6a5a4a", fontWeight: 500 }}>{color}</span>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 10.5, color: "#c0392b", marginTop: 8, fontStyle: "italic" }}>
                  ✕ AI will avoid these for {cat.replace(/_/g," ")} recommendations
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ── LIKES ─────────────────────────────────────────────────────────── */}
      {tab === "likes" && (
        <div style={{ animation: "sp-fadeup .3s ease" }}>
          {Object.keys(preferredColors).length === 0 ? (
            <div style={{ padding: "32px 0", textAlign: "center", color: "#b8a898", fontSize: 13 }}>
              No loved items yet. Tap "❤ Love this" on items in the chatbot.
            </div>
          ) : (
            Object.entries(preferredColors).map(([cat, colors]) => (
              <div key={cat} style={{ marginBottom: 18, padding: "14px 18px", background: "rgba(45,122,79,.04)", border: "1px solid rgba(45,122,79,.15)", borderRadius: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <span style={{ fontSize: 18 }}>{CAT_EMOJI[cat] || "👕"}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#2c1f0f", textTransform: "capitalize" }}>{cat.replace(/_/g," ")}</span>
                  <span style={{ fontSize: 10, color: "#2d7a4f", background: "rgba(45,122,79,.1)", padding: "1px 8px", borderRadius: 10, fontWeight: 700 }}>
                    {colors.length} preferred
                  </span>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {colors.map((color, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 10px", background: "#fff", border: "1px solid rgba(45,122,79,.25)", borderRadius: 20 }}>
                      <ColorDot color={color}/>
                      <span style={{ fontSize: 11, color: "#2d7a4f", fontWeight: 500 }}>{color}</span>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 10.5, color: "#2d7a4f", marginTop: 8, fontStyle: "italic" }}>
                  ✓ AI will recommend more {cat.replace(/_/g," ")} in these colors
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ── HISTORY ───────────────────────────────────────────────────────── */}
      {tab === "history" && (
        <div style={{ animation: "sp-fadeup .3s ease" }}>
          {history.length === 0 ? (
            <div style={{ padding: "32px 0", textAlign: "center", color: "#b8a898", fontSize: 13 }}>
              No interaction history yet.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {history.map((item, i) => {
                const isAccept = item.type === "accept";
                const ts = item.timestamp ? new Date(item.timestamp).toLocaleDateString("en-IN", { day:"numeric", month:"short", hour:"2-digit", minute:"2-digit" }) : "";
                const cat  = item.item?.category || "";
                const name = item.item?.item_name || item.item?.style || item.item_desc || "";

                return (
                  <div key={i} style={{
                    display: "flex", alignItems: "flex-start", gap: 10,
                    padding: "11px 14px", background: isAccept ? "rgba(45,122,79,.05)" : "rgba(192,57,43,.04)",
                    border: `1px solid ${isAccept?"rgba(45,122,79,.15)":"rgba(192,57,43,.12)"}`,
                    borderRadius: 10,
                  }}>
                    <span style={{ fontSize: 14, flexShrink: 0 }}>{isAccept ? "❤" : "🔄"}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, fontWeight: 500, color: "#2c1f0f" }}>
                        {isAccept ? "Loved" : "Replaced"} {cat && <span style={{ textTransform: "capitalize" }}>{cat.replace(/_/g," ")}</span>}
                        {name && <span style={{ color: "#8a7a6a", fontWeight: 400 }}> — {name.slice(0,50)}</span>}
                      </div>
                      {item.reason && (
                        <div style={{ fontSize: 10.5, color: "#a8998a", marginTop: 2 }}>Reason: {item.reason}</div>
                      )}
                      <div style={{ fontSize: 10, color: "#c4b4a4", marginTop: 2 }}>{ts}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}