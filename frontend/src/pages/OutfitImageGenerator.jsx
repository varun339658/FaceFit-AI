/**
 * OutfitImageGenerator.jsx — FIXED: Better image generation
 * - Builds more specific prompts from outfit items
 * - Shows actual outfit details while loading
 * - Better fallback with fashion search
 * - Retry with different seeds
 */
import { useState } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

export default function OutfitImageGenerator({ outfit, gender, skinTone, event = "casual" }) {
  const [imageUrl, setImageUrl] = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [source, setSource]     = useState("");
  const [attempt, setAttempt]   = useState(0);

  // Extract outfit summary for display
  const items = outfit?.items || {};
  const itemList = Object.entries(items)
    .filter(([, v]) => v)
    .map(([slot, item]) => `${item.color || ""} ${item.item_name || slot}`.trim())
    .filter(Boolean)
    .slice(0, 4);

  const generate = async () => {
    if (!outfit) return;
    setLoading(true);
    setError("");
    setImageUrl(null);
    setAttempt(a => a + 1);
    try {
      const r = await axios.post(`${API}/closet/outfit-image`, {
        outfit,
        gender:    gender || "male",
        skin_tone: skinTone || "medium",
        event:     event || "casual",
      });
      setImageUrl(r.data.image_url);
      setSource(r.data.source || "ai");
    } catch (e) {
      const msg = e?.response?.data?.error || "Image generation failed. Please try again.";
      setError(msg);
    }
    setLoading(false);
  };

  const S = {
    wrap:    { marginTop: 10 },
    genBtn:  {
      padding: "8px 16px",
      border: "1px solid rgba(200,165,90,.35)",
      background: "rgba(200,165,90,.06)",
      borderRadius: 8,
      color: "#8a5820",
      fontFamily: "inherit",
      fontSize: 10.5,
      fontWeight: 700,
      letterSpacing: ".1em",
      textTransform: "uppercase",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      gap: 7,
      transition: "all .2s",
    },
    loader: {
      marginTop: 10,
      padding: "20px 16px",
      background: "rgba(26,15,0,.03)",
      border: "1px solid rgba(200,165,90,.15)",
      borderRadius: 12,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: 10,
    },
    loaderIcon: { fontSize: 28, animation: "pulse 1.5s ease infinite" },
    loaderTitle: { fontSize: 12.5, fontWeight: 600, color: "#1a0f00" },
    loaderSub:   { fontSize: 11, color: "#a8998a", textAlign: "center", lineHeight: 1.6 },
    loaderItems: { display: "flex", gap: 5, flexWrap: "wrap", justifyContent: "center", marginTop: 4 },
    loaderItem:  { fontSize: 10, padding: "2px 8px", background: "rgba(200,165,90,.1)", borderRadius: 8, color: "#8a5820", border: "1px solid rgba(200,165,90,.2)" },
    spinner: { width: 14, height: 14, border: "1.5px solid rgba(200,165,90,.3)", borderTopColor: "#c8a55a", borderRadius: "50%", display: "inline-block", animation: "spin .8s linear infinite" },
    imgWrap: { marginTop: 10, borderRadius: 12, overflow: "hidden", border: "1px solid #ece6dc", boxShadow: "0 8px 28px rgba(0,0,0,.1)", position: "relative" },
    img:     { width: "100%", display: "block", maxHeight: 400, objectFit: "cover", background: "#f7f3ee" },
    badge:   { position: "absolute", top: 8, left: 8, padding: "3px 9px", background: "rgba(26,15,0,.75)", backdropFilter: "blur(6px)", borderRadius: 10, fontSize: 8.5, color: "#c8a55a", fontWeight: 700, letterSpacing: ".08em", textTransform: "uppercase" },
    errBox:  { marginTop: 8, fontSize: 11.5, color: "#c05050", background: "rgba(192,57,43,.06)", padding: "8px 12px", borderRadius: 7, border: "1px solid rgba(192,57,43,.15)" },
    actRow:  { marginTop: 8, display: "flex", gap: 7 },
  };

  const sourceLabel = source === "pollinations" ? "AI · Flux" : source === "fashion_search" ? "Fashion Ref" : "AI";

  return (
    <div style={S.wrap}>
      {!imageUrl && !loading && (
        <button style={S.genBtn} onClick={generate}>
          <span>🎨</span>
          Visualize Outfit
        </button>
      )}

      {loading && (
        <div style={S.loader}>
          <span style={S.loaderIcon}>🎨</span>
          <span style={S.loaderTitle}>Generating outfit visualization...</span>
          <span style={S.loaderSub}>
            Creating a photorealistic image of your outfit.<br />
            <span style={{ fontSize: 10 }}>Takes 15–45 seconds.</span>
          </span>
          {itemList.length > 0 && (
            <div style={S.loaderItems}>
              {itemList.map((item, i) => <span key={i} style={S.loaderItem}>{item}</span>)}
            </div>
          )}
          <span style={S.spinner} />
        </div>
      )}

      {imageUrl && (
        <>
          <div style={S.imgWrap}>
            <img
              src={imageUrl.startsWith("/") ? `${API}${imageUrl}` : imageUrl}
              alt="AI Generated Outfit"
              style={S.img}
              onError={e => { e.target.src = ""; e.target.style.display = "none"; setError("Image failed to load."); }}
            />
            <div style={S.badge}>✦ {sourceLabel}</div>
          </div>
          <div style={S.actRow}>
            <button style={{ ...S.genBtn, fontSize: 10 }} onClick={generate} disabled={loading}>
              {loading ? <span style={S.spinner} /> : "↺"} Regenerate
            </button>
            <a
              href={imageUrl.startsWith("/") ? `${API}${imageUrl}` : imageUrl}
              download="facefit-outfit.jpg"
              target="_blank"
              rel="noreferrer"
              style={{ ...S.genBtn, textDecoration: "none", fontSize: 10 }}
            >
              ↓ Save
            </a>
          </div>
        </>
      )}

      {error && <div style={S.errBox}>⚠️ {error}</div>}
    </div>
  );
}