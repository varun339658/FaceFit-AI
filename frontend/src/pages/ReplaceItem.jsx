/**
 * ReplaceItem.jsx — Replace Item + Learning System
 * ==================================================
 * Drop-in component. Add <ReplaceItem> under any product category
 * in Chatbot.jsx ProductGrid.
 *
 * Features:
 *  1. "Replace This" button per category → AI replaces ONLY that item
 *  2. "❤ Love it" / "✕ Not for me" buttons → learning system
 *  3. Replacement products slide in without reloading anything else
 *  4. Rejection reason picker (optional, quick taps)
 *  5. Preference memory indicator ("Based on your style")
 *
 * Usage in Chatbot.jsx ProductGrid component:
 *   import ReplaceItem from "./ReplaceItem";
 *   <ReplaceItem
 *     category="pants"
 *     currentProducts={products["pants"]}
 *     userContext={user}
 *     userId={user.name}
 *     event={detectedEvent}
 *     onReplaced={(cat, newProds) => updateProducts(cat, newProds)}
 *   />
 */

import { useState, useRef } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const REJECT_REASONS = [
  "Wrong color",
  "Don't like the style",
  "Too formal",
  "Too casual",
  "Wrong fit",
  "Not my vibe",
];

// Resolve image URL
function resolveImg(url) {
  if (!url || url === "None" || url === "null") return null;
  if (url.startsWith("/uploads/") || url.startsWith("/static/")) return `${API}${url}`;
  if (url.startsWith("http://127") || url.startsWith("http://localhost")) return url;
  const trusted = ["myntassets","rukminim","m.media-amazon","images.nykaa","images-cdn.ajio","encrypted-tbn"];
  if (url.startsWith("https") && trusted.some(d => url.includes(d))) return url;
  if (url.startsWith("http")) {
    try { return `https://images.weserv.nl/?url=${encodeURIComponent(url)}&w=400&h=300&fit=contain&bg=ffffff`; }
    catch { return url; }
  }
  return null;
}

// Mini product card for replacement results
function MiniProductCard({ p, onAccept }) {
  const [err, setErr]       = useState(false);
  const [loaded, setLoaded] = useState(false);
  const src   = resolveImg(p?.image || p?.thumbnail);
  const label = (p?.source || "").replace(/^www\./,"").replace(/\.(com|in)$/,"").slice(0,10);

  return (
    <div style={{
      background: "#fff", border: "1.5px solid rgba(200,165,90,.3)",
      borderRadius: 12, overflow: "hidden",
      transition: "transform .2s, box-shadow .2s",
      display: "flex", flexDirection: "column",
    }}
      onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 6px 20px rgba(0,0,0,.1)"; }}
      onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = ""; }}
    >
      <a href={p?.link || "#"} target="_blank" rel="noreferrer" style={{ textDecoration: "none", display: "block" }}>
        {/* Image */}
        <div style={{ height: 120, background: "#f7f3ee", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
          {!loaded && !err && src && (
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(90deg,#f0ebe4,#e8e0d4,#f0ebe4)", backgroundSize: "200% 100%", animation: "ri-shimmer 1.4s infinite" }}/>
          )}
          {src && !err
            ? <img src={src} alt={p?.title} style={{ width: "100%", height: "100%", objectFit: "contain", padding: 6, opacity: loaded?1:0, transition: "opacity .3s" }} onLoad={()=>setLoaded(true)} onError={()=>{setErr(true);setLoaded(true);}} crossOrigin="anonymous"/>
            : <span style={{ fontSize: 26, opacity: .2 }}>◈</span>
          }
          {label && <div style={{ position: "absolute", bottom: 4, left: 5, background: "rgba(26,15,0,.65)", padding: "1px 6px", borderRadius: 4, fontSize: 7.5, color: "#e8d8b8", letterSpacing: ".06em", textTransform: "uppercase" }}>{label}</div>}
        </div>
        {/* Info */}
        <div style={{ padding: "8px 10px 4px" }}>
          <div style={{ fontSize: 11, color: "#2c1f0f", lineHeight: 1.35, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", minHeight: 28, marginBottom: 4 }}>{p?.title}</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#8a5820" }}>{p?.price || "View"}</div>
        </div>
      </a>
      {/* Accept this replacement */}
      <button
        onClick={() => onAccept(p)}
        style={{
          margin: "4px 8px 8px", padding: "6px 0",
          background: "rgba(45,122,79,.1)", border: "1px solid rgba(45,122,79,.3)",
          borderRadius: 7, color: "#2d7a4f", fontFamily: "inherit",
          fontSize: 10, fontWeight: 700, letterSpacing: ".08em",
          textTransform: "uppercase", cursor: "pointer",
          transition: "all .18s",
        }}
        onMouseEnter={e => { e.currentTarget.style.background = "rgba(45,122,79,.2)"; }}
        onMouseLeave={e => { e.currentTarget.style.background = "rgba(45,122,79,.1)"; }}
      >
        ✓ Love This
      </button>
    </div>
  );
}

const CSS = `
@keyframes ri-shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
@keyframes ri-slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes ri-spin{to{transform:rotate(360deg)}}
`;

export default function ReplaceItem({
  category,
  currentProducts,    // current products array for this category
  userContext,        // { skinTone, gender, face_shape, ... }
  userId,
  event,
  onReplaced,         // callback(category, newProducts)
}) {
  const [phase, setPhase]           = useState("idle");   // idle | reason | loading | replaced | accepted
  const [selectedReason, setReason] = useState("");
  const [customReason, setCustom]   = useState("");
  const [replacements, setReplace]  = useState([]);
  const [aiMessage, setAiMsg]       = useState("");
  const [likedCat, setLikedCat]     = useState(false);

  const catLabel = category.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

  // Build current outfit description for context
  const buildCurrentOutfitCtx = () => {
    if (!currentProducts || !currentProducts.length) return {};
    return { [category]: currentProducts };
  };

  // Step 1: User clicks "Replace This"
  const handleReplaceClick = () => {
    setPhase("reason");
    setReason("");
    setCustom("");
  };

  // Step 2: User picks/skips reason → call API
  const handleDoReplace = async (reason = "") => {
    setPhase("loading");
    setAiMsg("");
    setReplace([]);

    const finalReason = reason || customReason || selectedReason || "";

    try {
      const r = await axios.post(`${API}/outfit/replace-item`, {
        user_id:        userId || "guest",
        category,
        reason:         finalReason,
        current_outfit: buildCurrentOutfitCtx(),
        user_context:   {
          skinTone:   userContext?.skinTone   || "medium",
          gender:     userContext?.gender     || "male",
          face_shape: userContext?.face_shape || "oval",
          event:      event || "casual",
        },
      });

      const data = r.data;
      setReplace(data.replacement || []);
      setAiMsg(data.reason_acknowledged || "");
      setPhase("replaced");

      // Notify parent so it can update the product grid
      if (onReplaced && data.replacement?.length) {
        onReplaced(category, data.replacement);
      }
    } catch(e) {
      console.error("Replace item error:", e);
      setPhase("idle");
    }
  };

  // Record "love it" feedback for learning
  const handleAccept = async (product) => {
    setLikedCat(true);
    setPhase("accepted");
    try {
      await axios.post(`${API}/outfit/feedback`, {
        user_id: userId || "guest",
        type:    "accept",
        scope:   "item",
        item: {
          category,
          color:     product?.title?.split(" ")[0] || "",
          item_name: product?.title || "",
          style:     product?.title || "",
        },
        reason: "user accepted replacement",
      });
    } catch(e) { console.error("Accept feedback error:", e); }
  };

  // Record "hate it" for learning
  const handleLike = async () => {
    setLikedCat(true);
    setPhase("accepted");
    if (!currentProducts?.[0]) return;
    try {
      await axios.post(`${API}/outfit/feedback`, {
        user_id: userId || "guest",
        type:    "accept",
        scope:   "item",
        item: {
          category,
          color:     "",
          item_name: currentProducts[0]?.title || "",
          style:     currentProducts[0]?.title || "",
        },
      });
    } catch(e) { console.error("Like feedback:", e); }
  };

  const handleReset = () => {
    setPhase("idle");
    setReason("");
    setCustom("");
    setReplace([]);
    setAiMsg("");
    setLikedCat(false);
  };

  return (
    <>
      <style>{CSS}</style>
      <div style={{ marginTop: 8 }}>

        {/* ── IDLE: Like/Replace buttons ────────────────────────────────── */}
        {phase === "idle" && (
          <div style={{ display: "flex", gap: 7, alignItems: "center", flexWrap: "wrap" }}>
            <button
              onClick={handleLike}
              style={{
                padding: "5px 12px", border: "1px solid rgba(45,122,79,.3)",
                background: "rgba(45,122,79,.07)", borderRadius: 20,
                fontFamily: "inherit", fontSize: 11, color: "#2d7a4f",
                cursor: "pointer", display: "flex", alignItems: "center", gap: 5,
                transition: "all .18s",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = "rgba(45,122,79,.15)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(45,122,79,.07)"; }}
            >
              ❤ Love this {catLabel}
            </button>
            <button
              onClick={handleReplaceClick}
              style={{
                padding: "5px 12px", border: "1px solid rgba(192,57,43,.3)",
                background: "rgba(192,57,43,.06)", borderRadius: 20,
                fontFamily: "inherit", fontSize: 11, color: "#c0392b",
                cursor: "pointer", display: "flex", alignItems: "center", gap: 5,
                transition: "all .18s",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = "rgba(192,57,43,.12)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "rgba(192,57,43,.06)"; }}
            >
              🔄 Replace this {catLabel}
            </button>
          </div>
        )}

        {/* ── REASON PICKER ──────────────────────────────────────────────── */}
        {phase === "reason" && (
          <div style={{
            padding: "14px 16px", background: "#fff",
            border: "1px solid rgba(192,57,43,.2)", borderRadius: 12,
            animation: "ri-slideIn .25s ease",
          }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: "#1a0f00", marginBottom: 10 }}>
              Why don't you like this {catLabel}? (optional — helps me learn)
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
              {REJECT_REASONS.map(r => (
                <button key={r}
                  onClick={() => setReason(r === selectedReason ? "" : r)}
                  style={{
                    padding: "5px 11px", borderRadius: 20, fontFamily: "inherit",
                    fontSize: 11, cursor: "pointer", transition: "all .15s",
                    border: selectedReason === r ? "1.5px solid #c0392b" : "1px solid #ddd3c2",
                    background: selectedReason === r ? "rgba(192,57,43,.12)" : "#fff",
                    color: selectedReason === r ? "#c0392b" : "#6a5a4a",
                    fontWeight: selectedReason === r ? 700 : 400,
                  }}
                >{r}</button>
              ))}
            </div>
            {/* Or type custom */}
            <input
              type="text"
              value={customReason}
              onChange={e => setCustom(e.target.value)}
              placeholder="Or type a reason..."
              style={{
                width: "100%", padding: "8px 12px", border: "1px solid #ddd3c2",
                borderRadius: 8, fontFamily: "inherit", fontSize: 12,
                outline: "none", background: "#faf7f3", color: "#2c1f0f",
                marginBottom: 10, boxSizing: "border-box",
              }}
              onKeyDown={e => { if (e.key === "Enter") handleDoReplace(customReason || selectedReason); }}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => handleDoReplace(customReason || selectedReason)}
                style={{
                  flex: 1, padding: "9px 0", background: "#1a0f00", color: "#c8a55a",
                  border: "none", borderRadius: 8, fontFamily: "inherit",
                  fontSize: 10.5, fontWeight: 700, letterSpacing: ".12em",
                  textTransform: "uppercase", cursor: "pointer",
                }}
              >
                Find Me a Better {catLabel} →
              </button>
              <button
                onClick={handleReset}
                style={{
                  padding: "9px 14px", background: "#f0ebe4", color: "#8a7a6a",
                  border: "none", borderRadius: 8, fontFamily: "inherit",
                  fontSize: 11, cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* ── LOADING ──────────────────────────────────────────────────── */}
        {phase === "loading" && (
          <div style={{
            display: "flex", alignItems: "center", gap: 10, padding: "12px 16px",
            background: "rgba(200,165,90,.06)", border: "1px solid rgba(200,165,90,.2)",
            borderRadius: 10, animation: "ri-slideIn .2s ease",
          }}>
            <div style={{ width: 16, height: 16, border: "2px solid rgba(200,165,90,.3)", borderTopColor: "#c8a55a", borderRadius: "50%", animation: "ri-spin .8s linear infinite", flexShrink: 0 }}/>
            <span style={{ fontSize: 12.5, color: "#8a5820", fontStyle: "italic" }}>
              Finding a better {catLabel} for your style...
            </span>
          </div>
        )}

        {/* ── REPLACED: Show new options ────────────────────────────────── */}
        {phase === "replaced" && (
          <div style={{ animation: "ri-slideIn .3s ease" }}>
            {/* AI message */}
            {aiMessage && (
              <div style={{
                padding: "9px 13px", marginBottom: 10,
                background: "rgba(45,122,79,.07)", border: "1px solid rgba(45,122,79,.2)",
                borderRadius: 8, fontSize: 12, color: "#1e5035", lineHeight: 1.55,
                display: "flex", gap: 7, alignItems: "flex-start",
              }}>
                <span style={{ flexShrink: 0 }}>✦</span>
                <span>{aiMessage}</span>
              </div>
            )}
            {/* New products grid */}
            {replacements.length > 0 ? (
              <>
                <div style={{ fontSize: 9.5, letterSpacing: ".18em", textTransform: "uppercase", color: "#a8998a", fontWeight: 700, marginBottom: 8 }}>
                  Better {catLabel} Options For You
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 8, marginBottom: 10 }}>
                  {replacements.map((p, i) => (
                    <MiniProductCard key={i} p={p} onAccept={handleAccept}/>
                  ))}
                </div>
              </>
            ) : (
              <div style={{ fontSize: 12, color: "#a8998a", padding: "8px 0" }}>
                No alternatives found. Try again?
              </div>
            )}
            {/* Try again / cancel */}
            <div style={{ display: "flex", gap: 7, marginTop: 4 }}>
              <button
                onClick={() => handleDoReplace(selectedReason || customReason)}
                style={{
                  padding: "5px 12px", border: "1px solid #ddd3c2", background: "#fff",
                  borderRadius: 20, fontFamily: "inherit", fontSize: 11, color: "#6a5a4a",
                  cursor: "pointer",
                }}
              >
                ↻ Try different
              </button>
              <button
                onClick={handleReset}
                style={{
                  padding: "5px 12px", border: "1px solid #ddd3c2", background: "#fff",
                  borderRadius: 20, fontFamily: "inherit", fontSize: 11, color: "#6a5a4a",
                  cursor: "pointer",
                }}
              >
                Keep original
              </button>
            </div>
          </div>
        )}

        {/* ── ACCEPTED ──────────────────────────────────────────────────── */}
        {phase === "accepted" && (
          <div style={{
            padding: "8px 12px", background: "rgba(45,122,79,.08)",
            border: "1px solid rgba(45,122,79,.25)", borderRadius: 8,
            fontSize: 12, color: "#2d7a4f", fontWeight: 500,
            display: "flex", alignItems: "center", gap: 7,
            animation: "ri-slideIn .2s ease",
          }}>
            <span>✓</span>
            <span>Got it! Your taste is saved — future picks will be smarter.</span>
            <button onClick={handleReset} style={{ marginLeft: "auto", background: "none", border: "none", color: "#a8998a", fontSize: 11, cursor: "pointer" }}>
              ✕
            </button>
          </div>
        )}
      </div>
    </>
  );
}