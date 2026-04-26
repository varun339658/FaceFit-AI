/**
 * SkinConditionExplainer.jsx — Plain-English Skin Condition Cards
 * Feature 4: Shows condition explanations + ingredient warnings from AI
 */
import { useState, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const COND_ICONS = {
  "acne":        { icon: "🔴", color: "#d96b6b", bg: "rgba(217,107,107,.06)" },
  "dark circle": { icon: "👁️", color: "#7c6bab", bg: "rgba(124,107,171,.06)" },
  "dark spot":   { icon: "🟤", color: "#c8a96e", bg: "rgba(200,169,110,.06)" },
  "normal skin": { icon: "✨", color: "#2d7a4f", bg: "rgba(45,122,79,.06)" },
};

function getCondStyle(cond) {
  const key = Object.keys(COND_ICONS).find(k => cond.toLowerCase().includes(k));
  return COND_ICONS[key] || { icon: "💊", color: "#8a7a6a", bg: "rgba(138,122,106,.06)" };
}

function ConditionCard({ condName, data }) {
  const [expanded, setExpanded] = useState(false);
  const style = getCondStyle(condName);

  const sevColor = { mild: "#2d7a4f", moderate: "#c8a55a", severe: "#c05050" };
  const sevBg    = { mild: "rgba(45,122,79,.1)", moderate: "rgba(200,165,90,.1)", severe: "rgba(192,57,43,.1)" };

  return (
    <div style={{
      border: `1px solid ${style.color}22`, borderRadius: 12, overflow: "hidden",
      background: style.bg, marginBottom: 10, transition: "all .2s",
    }}>
      {/* Header */}
      <div style={{ padding: "14px 16px", cursor: "pointer", display: "flex", alignItems: "center", gap: 12 }}
        onClick={() => setExpanded(v => !v)}>
        <div style={{ width: 38, height: 38, borderRadius: "50%", background: style.color + "18", border: `1.5px solid ${style.color}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0 }}>
          {style.icon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#1a0f00", textTransform: "capitalize" }}>
            {condName.replace(/_/g, " ")}
          </div>
          <div style={{ fontSize: 11, color: "#8a7a6a", marginTop: 1 }}>{data.what_it_is}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {data.severity && (
            <span style={{ fontSize: 10, padding: "2px 9px", borderRadius: 12, fontWeight: 700, background: sevBg[data.severity] || "rgba(200,165,90,.1)", color: sevColor[data.severity] || "#c8a55a" }}>
              {data.severity}
            </span>
          )}
          <span style={{ fontSize: 12, color: "#c8a55a" }}>{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div style={{ padding: "0 16px 16px", borderTop: `1px solid ${style.color}18`, animation: "fadeUp .2s ease" }}>
          {data.why_you_have_it && (
            <div style={{ marginTop: 12, fontSize: 12.5, color: "#3a2e24", lineHeight: 1.7, padding: "10px 12px", background: "rgba(255,255,255,.6)", borderRadius: 8 }}>
              💡 {data.why_you_have_it}
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 12 }}>
            {/* Good for you */}
            {data.good_for_you?.length > 0 && (
              <div style={{ padding: "10px 12px", background: "rgba(45,122,79,.06)", border: "1px solid rgba(45,122,79,.15)", borderRadius: 8 }}>
                <div style={{ fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase", color: "#2d7a4f", fontWeight: 700, marginBottom: 6 }}>✓ Use These</div>
                {data.good_for_you.map((g, i) => (
                  <div key={i} style={{ fontSize: 11, color: "#1e5035", lineHeight: 1.6, marginBottom: 2 }}>• {g}</div>
                ))}
              </div>
            )}

            {/* Avoid */}
            {data.avoid?.length > 0 && (
              <div style={{ padding: "10px 12px", background: "rgba(192,57,43,.04)", border: "1px solid rgba(192,57,43,.12)", borderRadius: 8 }}>
                <div style={{ fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase", color: "#c05050", fontWeight: 700, marginBottom: 6 }}>✕ Avoid</div>
                {data.avoid.map((a, i) => (
                  <div key={i} style={{ fontSize: 11, color: "#8a3030", lineHeight: 1.6, marginBottom: 2 }}>• {a}</div>
                ))}
              </div>
            )}
          </div>

          {data.key_ingredient && (
            <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 9, padding: "8px 12px", background: "rgba(200,165,90,.06)", borderLeft: "3px solid #c8a55a", borderRadius: "0 8px 8px 0" }}>
              <span style={{ fontSize: 14 }}>⭐</span>
              <div>
                <div style={{ fontSize: 9, color: "#b8a898", textTransform: "uppercase", letterSpacing: ".15em", fontWeight: 700 }}>Best Ingredient</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#8a5820" }}>{data.key_ingredient}</div>
              </div>
            </div>
          )}

          {data.lifestyle_tip && (
            <div style={{ marginTop: 10, fontSize: 11.5, color: "#5a4838", lineHeight: 1.65, display: "flex", gap: 8, alignItems: "flex-start" }}>
              <span style={{ fontSize: 14, flexShrink: 0 }}>🌿</span>
              <span>{data.lifestyle_tip}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SkinConditionExplainer({ conditions, skinTone, severityCounts }) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (conditions?.length > 0) fetchExplanations();
  }, [JSON.stringify(conditions), skinTone]);

  const fetchExplanations = async () => {
    setLoading(true);
    try {
      const r = await axios.post(`${API}/skin/explain`, {
        conditions:      conditions || [],
        skin_tone:       skinTone || "medium",
        severity_counts: severityCounts || {},
      });
      setData(r.data);
    } catch (e) {
      console.error("Explainer error:", e);
    }
    setLoading(false);
  };

  if (!conditions?.length) return null;
  if (loading) return (
    <div style={{ fontSize: 12, color: "#c8a55a", display: "flex", alignItems: "center", gap: 8, padding: "8px 0" }}>
      <span style={{ width: 12, height: 12, border: "2px solid #c8a55a", borderTopColor: "transparent", borderRadius: "50%", display: "inline-block", animation: "spin .8s linear infinite" }} />
      Loading skin insights...
    </div>
  );
  if (!data) return null;

  return (
    <div style={{ marginTop: 14 }}>
      {/* Summary banner */}
      {data.summary && (
        <div style={{ padding: "12px 16px", background: "rgba(200,165,90,.04)", border: "1px solid rgba(200,165,90,.2)", borderRadius: 10, fontSize: 12.5, color: "#3a2e24", lineHeight: 1.7, marginBottom: 12, display: "flex", gap: 10, alignItems: "flex-start", cursor: "pointer" }}
          onClick={() => setExpanded(v => !v)}>
          <span style={{ fontSize: 16, flexShrink: 0 }}>🔬</span>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong style={{ fontSize: 11, letterSpacing: ".12em", textTransform: "uppercase", color: "#8a5820" }}>AI Skin Analysis</strong>
              <span style={{ fontSize: 11, color: "#c8a55a" }}>{expanded ? "Hide Details ▲" : "Show Details ▼"}</span>
            </div>
            <div style={{ marginTop: 3 }}>{data.summary}</div>
          </div>
        </div>
      )}

      {expanded && (
        <div style={{ animation: "fadeUp .2s ease" }}>
          {/* Global warnings */}
          {data.global_warnings?.length > 0 && (
            <div style={{ padding: "10px 14px", background: "rgba(192,57,43,.04)", border: "1px solid rgba(192,57,43,.12)", borderRadius: 8, marginBottom: 12 }}>
              <div style={{ fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase", color: "#c05050", fontWeight: 700, marginBottom: 5 }}>⚠ Important Warnings</div>
              {data.global_warnings.map((w, i) => (
                <div key={i} style={{ fontSize: 11.5, color: "#8a3030", lineHeight: 1.6 }}>• {w}</div>
              ))}
            </div>
          )}

          {/* Per-condition cards */}
          {Object.entries(data.explanations || {}).map(([cond, info]) => (
            <ConditionCard key={cond} condName={cond} data={info} />
          ))}
        </div>
      )}
    </div>
  );
}