/**
 * OutfitPhotoAnalyzer.jsx — FaceFit Occasion Photo Analyzer v5
 * ===============================================================
 * FIXES:
 *  1. Save/Alert button on EVERY product card (price drop alerts)
 *  2. Products deduplicated (no duplicates by title/link)
 *  3. Wardrobe item images shown correctly via resolveWardrobeImage
 *  4. Gender-aware accessories preserved
 *  5. All AI+RAG+skin analysis intact
 */
import { useState, useRef } from "react";
import axios from "axios";
import { SaveButton } from "./SavedProducts";
import { getProfile } from "./Register";

const API = "http://127.0.0.1:5000";

const EVENTS = [
  {val:"wedding",   label:"Wedding",   icon:"💍"}, {val:"party",     label:"Party",     icon:"🎊"},
  {val:"office",    label:"Office",    icon:"💼"}, {val:"casual",    label:"Casual",    icon:"😊"},
  {val:"date",      label:"Date",      icon:"🌹"}, {val:"college",   label:"College",   icon:"🎓"},
  {val:"gym",       label:"Gym",       icon:"💪"}, {val:"festival",  label:"Festival",  icon:"🎉"},
  {val:"interview", label:"Interview", icon:"🎯"}, {val:"general",   label:"General",   icon:"✨"},
  {val:"dinner",    label:"Dinner",    icon:"🍽️"}, {val:"beach",     label:"Beach",     icon:"🏖️"},
];

const CAT_LABELS = {
  shirt:"Shirt / Top", pants:"Pants / Bottom", shoes:"Shoes", top:"Top",
  dress:"Dress", blazer:"Blazer", ethnic:"Ethnic Wear", accessories:"Accessories",
  watch:"Watch", bracelet:"Bracelet", earrings:"Earrings", necklace:"Necklace",
  sunglasses:"Sunglasses", gym_tshirt:"Gym T-Shirt", track_pants:"Track Pants", sports_shoes:"Sports Shoes",
};

const CAT_EMOJI = {
  shirt:"👕", pants:"👖", shoes:"👟", top:"👚", dress:"👗", blazer:"🧥",
  ethnic:"🥻", accessories:"💍", watch:"⌚", bracelet:"📿", earrings:"✨",
  necklace:"💎", sunglasses:"🕶️", gym_tshirt:"💪", track_pants:"🩳", sports_shoes:"👟",
};

// ── Deduplicate products ────────────────────────────────────────────────────
function deduplicateProducts(products) {
  if (!products || !products.length) return [];
  const seen = new Set();
  return products.filter(p => {
    if (!p || !p.title) return false;
    const key = (p.title||"").toLowerCase().trim().slice(0, 40) + "|" + (p.link||"").split("?")[0];
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

// ── Resolve product image ───────────────────────────────────────────────────
function resolveProductImage(url) {
  if (!url || url==="None" || url==="null") return null;
  if (url.startsWith("data:")) return url;
  if (url.startsWith("/uploads/") || url.startsWith("/static/")) return `${API}${url}`;
  if (url.startsWith("http://127") || url.startsWith("http://localhost")) return url;
  const trusted = ["myntassets.com","rukminim","m.media-amazon","images.nykaa","images-cdn.ajio",
    "images.meesho","lh3.googleusercontent","images.bewakoof","img1.ajio","cdn.shopify","encrypted-tbn"];
  if (url.startsWith("https") && trusted.some(d => url.includes(d))) return url;
  if (url.startsWith("http")) {
    try { return `https://images.weserv.nl/?url=${encodeURIComponent(url)}&w=400&h=400&fit=contain&bg=ffffff`; }
    catch { return url; }
  }
  return null;
}

// ── Product card with Save/Alert button ────────────────────────────────────
function ProductCardWithAlert({ p, userId }) {
  const [imgErr,  setImgErr]  = useState(false);
  const [loaded,  setLoaded]  = useState(false);

  if (!p || !p.link) return null;
  const src   = resolveProductImage(p.image || p.thumbnail);
  const label = (p.source||"").replace(/^www\./,"").replace(/\.(com|in)$/,"").slice(0,12);

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
      <a
        href={p.link} target="_blank" rel="noreferrer"
        style={{
          display:"block", textDecoration:"none",
          background:"#fff", border:"1px solid #ece6dc", borderRadius:12,
          overflow:"hidden", transition:"transform .2s, box-shadow .2s",
        }}
        onMouseEnter={e => { e.currentTarget.style.transform="translateY(-3px)"; e.currentTarget.style.boxShadow="0 10px 28px rgba(0,0,0,.1)"; }}
        onMouseLeave={e => { e.currentTarget.style.transform=""; e.currentTarget.style.boxShadow=""; }}
      >
        {/* Image */}
        <div style={{
          height:140, background:"#f7f3ee",
          display:"flex", alignItems:"center", justifyContent:"center",
          overflow:"hidden", position:"relative",
        }}>
          {!loaded && !imgErr && src && (
            <div style={{
              position:"absolute", inset:0,
              background:"linear-gradient(90deg,#f0ebe4,#e8e0d4,#f0ebe4)",
              backgroundSize:"200% 100%", animation:"pa-shimmer 1.4s infinite",
            }}/>
          )}
          {src && !imgErr ? (
            <img
              src={src} alt={p.title}
              style={{ width:"100%", height:"100%", objectFit:"contain", padding:8, opacity:loaded?1:0, transition:"opacity .3s" }}
              onLoad={() => setLoaded(true)}
              onError={() => { setImgErr(true); setLoaded(true); }}
              crossOrigin="anonymous"
            />
          ) : (
            <span style={{ fontSize:30, opacity:.2 }}>◈</span>
          )}
          {label && (
            <div style={{
              position:"absolute", bottom:6, left:6,
              background:"rgba(26,15,0,.65)", backdropFilter:"blur(4px)",
              padding:"2px 7px", borderRadius:4,
              fontSize:8, color:"#e8d8b8", letterSpacing:".06em", textTransform:"uppercase",
            }}>{label}</div>
          )}
        </div>
        {/* Info */}
        <div style={{ padding:"10px 12px 4px" }}>
          <div style={{
            fontSize:11.5, color:"#2c1f0f", lineHeight:1.4, marginBottom:5,
            display:"-webkit-box", WebkitLineClamp:2, WebkitBoxOrient:"vertical", overflow:"hidden",
            minHeight:30,
          }}>{p.title}</div>
          <div style={{ fontSize:14, fontWeight:700, color:"#8a5820", marginBottom:8 }}>
            {p.price||"View Price"}
          </div>
        </div>
        <div style={{
          display:"block", margin:"0 10px 10px", padding:"8px 0",
          background:"#1a0f00", color:"#c8a55a", textAlign:"center",
          fontSize:10, fontWeight:700, letterSpacing:".15em", textTransform:"uppercase",
          borderRadius:7,
        }}>Shop Now →</div>
      </a>
      {/* 🔔 Save / Price Alert button */}
      {userId && (
        <div style={{ marginTop:5 }}>
          <SaveButton product={p} userId={userId}/>
        </div>
      )}
    </div>
  );
}

// ── CSS ───────────────────────────────────────────────────────────────────────
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=DM+Sans:wght@300;400;500;600&display=swap');
@keyframes pa-shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
@keyframes paFU{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes pasp{to{transform:rotate(360deg)}}
.pa-root{font-family:'DM Sans',sans-serif;max-width:900px;padding-bottom:60px;color:#1a0f00}
.pa-hero{background:linear-gradient(145deg,#0a0608,#180d10,#0a0608);border-radius:20px;padding:44px 40px 36px;margin-bottom:24px;position:relative;overflow:hidden}
.pa-hero::before{content:'';position:absolute;top:-60px;left:-60px;width:280px;height:280px;border-radius:50%;background:radial-gradient(circle,rgba(200,80,120,.12) 0%,transparent 70%);pointer-events:none}
.pa-hero::after{content:'';position:absolute;bottom:-60px;right:-60px;width:240px;height:240px;border-radius:50%;background:radial-gradient(circle,rgba(200,165,90,.12) 0%,transparent 70%);pointer-events:none}
.pa-eyebrow{font-size:9px;letter-spacing:.4em;text-transform:uppercase;color:rgba(200,165,90,.6);font-weight:600;margin-bottom:10px}
.pa-title{font-family:'Cormorant Garamond',serif;font-size:40px;font-weight:300;color:#f5ede0;line-height:1.1;margin-bottom:8px}
.pa-title em{font-style:italic;color:#c8a55a}
.pa-sub{font-size:12.5px;color:rgba(200,165,90,.5);line-height:1.7;max-width:480px}
.pa-upload-zone{border:1.5px dashed rgba(200,165,90,.3);border-radius:16px;padding:48px 20px;text-align:center;cursor:pointer;background:rgba(200,165,90,.03);transition:all .2s}
.pa-upload-zone:hover{border-color:rgba(200,165,90,.6);background:rgba(200,165,90,.06)}
.pa-preview{position:relative;border-radius:16px;overflow:hidden;border:1px solid #ece6dc;margin-bottom:20px}
.pa-preview img{width:100%;max-height:400px;object-fit:contain;display:block;background:#f7f3ee}
.pa-close{position:absolute;top:12px;right:12px;background:rgba(26,15,0,.7);border:none;color:#fff;border-radius:50%;width:32px;height:32px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
.pa-ev-grid{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:16px}
.pa-ev-btn{padding:7px 14px;border-radius:22px;border:1.5px solid #ddd3c2;background:#fff;font-family:inherit;font-size:11.5px;color:#6a5a4a;cursor:pointer;transition:all .18s;display:flex;align-items:center;gap:6px;font-weight:500}
.pa-ev-btn.active{border-color:#c8a55a;color:#8a5820;background:rgba(200,165,90,.1);font-weight:600}
.pa-notes-inp{width:100%;padding:11px 14px;border:1px solid #ddd3c2;border-radius:10px;font-family:inherit;font-size:13px;color:#1a0f00;outline:none;background:#faf7f3;box-sizing:border-box;margin-bottom:14px;transition:border-color .2s}
.pa-notes-inp:focus{border-color:#c8a55a;background:#fff}
.pa-analyze-btn{width:100%;padding:15px;background:#1a0f00;border:none;color:#c8a55a;border-radius:12px;cursor:pointer;font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;font-family:inherit;display:flex;align-items:center;justify-content:center;gap:10px;transition:all .2s}
.pa-analyze-btn:hover:not(:disabled){background:#c8a55a;color:#1a0f00}
.pa-analyze-btn:disabled{opacity:.5;cursor:not-allowed}
.pa-result{background:#fff;border:1px solid #ece6dc;border-radius:20px;overflow:hidden;margin-top:24px;animation:paFU .4s ease both}
.pa-result-header{padding:28px 32px;background:linear-gradient(135deg,#0e0a06,#1e1208);display:flex;align-items:center;gap:24px}
.pa-ring-wrap{flex-shrink:0;display:flex;flex-direction:column;align-items:center;gap:6px}
.pa-summary{flex:1}
.pa-result-eyebrow{font-size:9px;letter-spacing:.25em;text-transform:uppercase;color:rgba(200,165,90,.5);margin-bottom:6px}
.pa-result-summary{font-size:13.5px;color:#f5ede0;line-height:1.75}
.pa-badges{display:flex;align-items:center;gap:7px;flex-wrap:wrap;padding:14px 32px;border-bottom:1px solid #ece6dc;background:#faf7f3}
.pa-badge-good{padding:4px 12px;background:rgba(45,122,79,.1);border:1px solid rgba(45,122,79,.2);border-radius:20px;font-size:10.5px;font-weight:600;color:#2d7a4f}
.pa-badge-bad{padding:4px 12px;background:rgba(192,57,43,.08);border:1px solid rgba(192,57,43,.18);border-radius:20px;font-size:10.5px;font-weight:600;color:#c0392b}
.pa-tabs{display:flex;border-bottom:1px solid #ece6dc;padding:0 32px;overflow-x:auto}
.pa-tab{padding:14px 18px;border:none;border-bottom:2px solid transparent;background:none;font-family:inherit;font-size:12px;font-weight:500;color:#a8998a;cursor:pointer;transition:all .18s;display:flex;align-items:center;gap:7px;margin-bottom:-1px;white-space:nowrap}
.pa-tab.active{color:#8a5820;border-bottom-color:#c8a55a;font-weight:600}
.pa-body{padding:28px 32px}
.pa-sl{font-size:9px;letter-spacing:.3em;text-transform:uppercase;color:#a8998a;font-weight:700;margin-bottom:14px}
.pa-score-row{margin-bottom:12px}
.pa-score-lrow{display:flex;justify-content:space-between;margin-bottom:6px}
.pa-score-label{font-size:12px;color:#5a4838}
.pa-score-num{font-size:12px;font-weight:700}
.pa-score-track{height:7px;background:#f0ece4;border-radius:4px;overflow:hidden}
.pa-score-fill{height:100%;border-radius:4px;transition:width .8s cubic-bezier(.34,1.56,.64,1)}
.pa-works-pill{padding:9px 14px;background:rgba(45,122,79,.06);border:1px solid rgba(45,122,79,.15);border-radius:10px;font-size:12.5px;color:#1e5035;margin-bottom:7px;display:flex;gap:9px;align-items:flex-start;line-height:1.6}
.pa-wrong-pill{padding:9px 14px;background:rgba(192,57,43,.05);border:1px solid rgba(192,57,43,.12);border-radius:10px;font-size:12.5px;color:#7a2020;margin-bottom:7px;display:flex;gap:9px;align-items:flex-start;line-height:1.6}
.pa-imp-card{border:1px solid #ece6dc;border-radius:12px;padding:14px 18px;margin-bottom:10px;background:#fff}
.pa-imp-issue{font-size:12px;font-weight:600;color:#c05050;margin-bottom:5px}
.pa-imp-fix{font-size:13px;color:#1a0f00;margin-bottom:4px;line-height:1.6}
.pa-imp-ex{font-size:11px;color:#8a7a6a;font-style:italic}
.pa-alt-card{padding:18px 20px;background:linear-gradient(135deg,rgba(200,165,90,.07),rgba(200,165,90,.02));border:1px solid rgba(200,165,90,.2);border-radius:14px;margin-bottom:20px}
.pa-alt-title{font-family:'Cormorant Garamond',serif;font-size:18px;color:#1a0f00;margin-bottom:10px;line-height:1.5}
.pa-alt-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}
.pa-alt-item{padding:10px 12px;background:#fff;border-radius:8px;border:1px solid #ece6dc}
.pa-alt-k{font-size:9px;color:#a8998a;font-weight:700;text-transform:uppercase;margin-bottom:3px}
.pa-alt-v{font-size:12px;color:#1a0f00;line-height:1.4}
.pa-alt-acc{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px}
.pa-alt-ap{padding:4px 11px;background:rgba(200,165,90,.1);border:1px solid rgba(200,165,90,.25);border-radius:14px;font-size:11px;color:#8a5820}
.pa-alt-why{font-size:12px;color:#5a4838;font-style:italic;line-height:1.65;margin-bottom:16px}
.pa-color-tip{margin-top:16px;padding:13px 17px;border-left:3px solid #c8a55a;background:rgba(200,165,90,.05);border-radius:0 10px 10px 0;font-size:12.5px;color:#3a2e24;line-height:1.75}
.pa-conf{margin-top:16px;padding:16px 20px;background:linear-gradient(135deg,rgba(200,165,90,.07),rgba(200,165,90,.02));border:1px solid rgba(200,165,90,.18);border-radius:12px;font-size:14px;color:#1a0f00;line-height:1.8;font-style:italic;font-family:'Cormorant Garamond',serif}
.pa-gender-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;background:rgba(200,165,90,.1);border:1px solid rgba(200,165,90,.25);border-radius:20px;font-size:10px;font-weight:700;color:#8a5820;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px}
.pa-alert-banner{padding:10px 14px;background:rgba(200,165,90,.06);border:1px solid rgba(200,165,90,.2);border-radius:10px;margin-bottom:16px;font-size:12px;color:#8a5820;display:flex;align-items:center;gap:8px}
.pa-err{padding:13px 17px;background:rgba(192,80,80,.06);border:1px solid rgba(192,80,80,.2);border-radius:10px;font-size:12.5px;color:#a04040;margin-top:12px}
.pa-spin{width:16px;height:16px;border:2px solid rgba(200,165,90,.3);border-top-color:#c8a55a;border-radius:50%;animation:pasp .8s linear infinite;display:inline-block}
.pa-prod-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
@media(max-width:640px){
  .pa-hero{padding:28px 20px}.pa-title{font-size:28px}
  .pa-result-header{flex-direction:column;gap:16px;padding:24px 20px}
  .pa-body{padding:20px}.pa-tabs{padding:0 20px}
  .pa-badges{padding:12px 20px}.pa-alt-grid{grid-template-columns:1fr 1fr}
  .pa-prod-grid{grid-template-columns:repeat(2,1fr)}
}
`;

function RatingRing({ score, size=100 }) {
  const r=38, cx=size/2, cy=size/2;
  const circ  = 2*Math.PI*r;
  const offset = circ - (score/10)*circ;
  const color  = score>=8 ? "#2d7a4f" : score>=6 ? "#c8a55a" : score>=4 ? "#e07040" : "#c05050";
  const label  = score>=8 ? "Excellent" : score>=6 ? "Good" : score>=4 ? "Decent" : "Needs Work";
  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:6 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,.1)" strokeWidth={7}/>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={color}
          strokeWidth={7} strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round" transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition:"stroke-dashoffset .9s cubic-bezier(.34,1.56,.64,1)" }}/>
        <text x={cx} y={cy+8} textAnchor="middle"
          style={{ fontSize:26, fontWeight:700, fill:color, fontFamily:"'Cormorant Garamond',serif" }}>
          {score}
        </text>
      </svg>
      <div style={{ fontSize:10, fontWeight:700, color, letterSpacing:".08em", textTransform:"uppercase" }}>{label}</div>
    </div>
  );
}

function ScoreBar({ label, score }) {
  const color = score>=8 ? "#2d7a4f" : score>=6 ? "#c8a55a" : score>=4 ? "#e07040" : "#c05050";
  return (
    <div className="pa-score-row">
      <div className="pa-score-lrow">
        <span className="pa-score-label">{label}</span>
        <span className="pa-score-num" style={{ color }}>{score}/10</span>
      </div>
      <div className="pa-score-track">
        <div className="pa-score-fill" style={{ width:`${score*10}%`, background:color }}/>
      </div>
    </div>
  );
}

export default function OutfitPhotoAnalyzer({ user }) {
  const [image,   setImage]   = useState(null);
  const [preview, setPreview] = useState(null);
  const [event,   setEvent]   = useState("general");
  const [notes,   setNotes]   = useState("");
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState(null);
  const [error,   setError]   = useState("");
  const [tab,     setTab]     = useState("scores");
  const fileRef = useRef();

  // User profile for AI context
  const profile    = user || getProfile();
  const gender     = profile?.gender    || "male";
  const skinTone   = profile?.skinTone  || "medium";
  const faceShape  = profile?.face_shape || "oval";
  const bodyShape  = profile?.body_shape || "average";
  const conditions = (profile?.conditions||[]).join(",");
  const userId     = profile?.name || profile?.userId || "";
  const isMale     = !["female","women","woman","girl","f"].includes(gender.toLowerCase());
  const genderLabel = isMale ? "Male" : "Female";

  const handleFile = (f) => {
    if (!f) return;
    setImage(f); setPreview(URL.createObjectURL(f)); setResult(null); setError("");
  };

  const analyze = async () => {
    if (!image) return;
    setLoading(true); setError(""); setResult(null);
    const fd = new FormData();
    fd.append("image",      image);
    fd.append("event",      event);
    fd.append("user_notes", notes);
    fd.append("gender",     gender);
    fd.append("skin_tone",  skinTone);
    fd.append("face_shape", faceShape);
    fd.append("body_shape", bodyShape);
    fd.append("conditions", conditions);
    try {
      const r = await axios.post(`${API}/analyze-outfit-photo`, fd);
      setResult(r.data); setTab("scores");
    } catch (e) {
      setError(e?.response?.data?.error || "Analysis failed. Try a clearer full-body photo.");
    }
    setLoading(false);
  };

  return (
    <>
      <style>{CSS}</style>
      <div className="pa-root">

        {/* Hero */}
        <div className="pa-hero">
          <div className="pa-eyebrow">✦ AI Vision Analysis</div>
          <h1 className="pa-title">Photo <em>Analyzer</em></h1>
          <p className="pa-sub">Upload an outfit photo — AI rates it 1–10, spots mistakes, and suggests exactly what to improve. Fully tailored to your skin tone and gender.</p>
        </div>

        {/* Profile confirmation */}
        <div style={{ marginBottom:16 }}>
          <div className="pa-gender-badge">
            {isMale ? "♂" : "♀"} {genderLabel} · {skinTone} skin · {faceShape} face
          </div>
        </div>

        {!preview ? (
          <div className="pa-upload-zone"
            onClick={() => fileRef.current?.click()}
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); }}>
            <input ref={fileRef} type="file" accept="image/*" style={{ display:"none" }}
              onChange={e => handleFile(e.target.files[0])}/>
            <div style={{ fontSize:48, marginBottom:14, opacity:.6 }}>📸</div>
            <div style={{ fontSize:15, fontWeight:600, color:"#1a0f00", marginBottom:5, fontFamily:"'Cormorant Garamond',serif" }}>
              Upload Your Outfit Photo
            </div>
            <div style={{ fontSize:12, color:"#a8998a", lineHeight:1.6 }}>
              Drop a photo here or <span style={{ color:"#c8a55a", fontWeight:600 }}>click to browse</span><br/>
              <span style={{ color:"#c8a55a", fontWeight:600 }}>Include your full outfit</span> — top, bottom, shoes for best results
            </div>
          </div>
        ) : (
          <>
            <div className="pa-preview">
              <img src={preview} alt="Outfit to analyze"/>
              <button className="pa-close" onClick={() => { setPreview(null); setImage(null); setResult(null); }}>✕</button>
            </div>

            <div style={{ fontSize:10, fontWeight:600, color:"#6a5a4a", letterSpacing:".12em", textTransform:"uppercase", marginBottom:8 }}>
              What occasion was this for?
            </div>
            <div className="pa-ev-grid">
              {EVENTS.map(ev => (
                <button key={ev.val}
                  className={`pa-ev-btn${event===ev.val?" active":""}`}
                  onClick={() => setEvent(ev.val)}>
                  {ev.icon} {ev.label}
                </button>
              ))}
            </div>

            <div style={{ fontSize:10, fontWeight:600, color:"#6a5a4a", letterSpacing:".12em", textTransform:"uppercase", marginTop:4, marginBottom:6 }}>
              Your notes (optional)
            </div>
            <input className="pa-notes-inp" value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="e.g. I felt overdressed, shoes didn't match..."/>

            <button className="pa-analyze-btn" onClick={analyze} disabled={loading}>
              {loading
                ? <><span className="pa-spin"/>Analyzing your outfit...</>
                : `🔍 Analyze My ${genderLabel} Outfit →`
              }
            </button>
          </>
        )}

        {error && <div className="pa-err">⚠️ {error}</div>}

        {result && !loading && (() => {
          const scores   = result.scores || {};
          const mistakes = result.mistakes_detected || {};

          return (
            <div className="pa-result">
              {/* Score header */}
              <div className="pa-result-header">
                <div className="pa-ring-wrap">
                  <RatingRing score={result.overall_rating||5} size={110}/>
                </div>
                <div className="pa-summary">
                  <div className="pa-result-eyebrow">
                    {genderLabel} Outfit Analysis · {EVENTS.find(e => e.val===event)?.icon} {event}
                  </div>
                  <div className="pa-result-summary">{result.summary}</div>
                </div>
              </div>

              {/* Mistake badges */}
              {Object.keys(mistakes).length > 0 && (
                <div className="pa-badges">
                  {Object.entries(mistakes).map(([k, v]) => (
                    <span key={k} className={v ? "pa-badge-bad" : "pa-badge-good"}>
                      {v ? "✕" : "✓"} {k.replace(/_/g," ")}
                    </span>
                  ))}
                </div>
              )}

              {/* Tabs */}
              <div className="pa-tabs">
                {[
                  ["scores",       "📊 Scores"],
                  ["feedback",     "💬 Feedback"],
                  ["improvements", "🔧 Fixes"],
                  ["alternative",  "✨ Better Look"],
                ].map(([id, label]) => (
                  <button key={id}
                    className={`pa-tab${tab===id?" active":""}`}
                    onClick={() => setTab(id)}>
                    {label}
                  </button>
                ))}
              </div>

              <div className="pa-body">

                {/* ── SCORES ─────────────────────────────────── */}
                {tab==="scores" && (
                  <div style={{ animation:"paFU .3s ease both" }}>
                    <div className="pa-sl">Score Breakdown</div>
                    {[
                      ["Color Harmony",         scores.color_harmony],
                      ["Event Appropriateness", scores.event_appropriateness],
                      ["Fit Quality",           scores.fit_quality],
                      ["Skin Tone Match",       scores.skin_tone_match],
                      ["Style Cohesion",        scores.style_cohesion],
                    ].map(([label, score]) => score!=null ? (
                      <ScoreBar key={label} label={label} score={Math.round(score||5)}/>
                    ) : null)}
                    {result.color_tip_for_skin && (
                      <div className="pa-color-tip">
                        🎨 <strong>Color tip for {skinTone} skin ({genderLabel}):</strong> {result.color_tip_for_skin}
                      </div>
                    )}
                  </div>
                )}

                {/* ── FEEDBACK ──────────────────────────────── */}
                {tab==="feedback" && (
                  <div style={{ animation:"paFU .3s ease both" }}>
                    {result.what_worked?.length > 0 && (
                      <div style={{ marginBottom:18 }}>
                        <div className="pa-sl">✓ What Worked</div>
                        {result.what_worked.map((w, i) => (
                          <div key={i} className="pa-works-pill"><span>✦</span><span>{w}</span></div>
                        ))}
                      </div>
                    )}
                    {result.what_went_wrong?.length > 0 && (
                      <div>
                        <div className="pa-sl">✕ What Went Wrong</div>
                        {result.what_went_wrong.map((w, i) => (
                          <div key={i} className="pa-wrong-pill"><span>✗</span><span>{w}</span></div>
                        ))}
                      </div>
                    )}
                    {result.color_analysis?.clashes?.length > 0 && (
                      <div style={{ marginTop:14 }}>
                        <div className="pa-sl">🎨 Color Issues</div>
                        {result.color_analysis.clashes.map((c, i) => (
                          <div key={i} className="pa-wrong-pill"><span>⚠️</span><span>{c}</span></div>
                        ))}
                      </div>
                    )}
                    {result.color_analysis?.positives?.length > 0 && (
                      <div style={{ marginTop:14 }}>
                        <div className="pa-sl">🎨 Color Wins</div>
                        {result.color_analysis.positives.map((c, i) => (
                          <div key={i} className="pa-works-pill"><span>✓</span><span>{c}</span></div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* ── IMPROVEMENTS ──────────────────────────── */}
                {tab==="improvements" && (
                  <div style={{ animation:"paFU .3s ease both" }}>
                    <div className="pa-sl">Specific Improvements for {genderLabel}</div>
                    {(result.specific_improvements||[]).map((item, i) => (
                      <div key={i} className="pa-imp-card">
                        <div className="pa-imp-issue">⚠️ {item.issue}</div>
                        <div className="pa-imp-fix">✦ Fix: {item.fix}</div>
                        {item.example && <div className="pa-imp-ex">e.g. {item.example}</div>}
                      </div>
                    ))}
                    {(!result.specific_improvements || result.specific_improvements.length===0) && (
                      <div style={{ fontSize:13, color:"#6a9278", padding:"12px 0" }}>
                        ✓ No major improvements needed — solid outfit!
                      </div>
                    )}
                    {result.confidence_message && (
                      <div className="pa-conf">✨ "{result.confidence_message}"</div>
                    )}
                  </div>
                )}

                {/* ── ALTERNATIVE — WITH IMAGES + SAVE BUTTONS ── */}
                {tab==="alternative" && result.alternative_outfit && (
                  <div style={{ animation:"paFU .3s ease both" }}>
                    <div className="pa-sl">✨ A Better Look For This Occasion ({genderLabel})</div>

                    {/* Gender badge */}
                    <div style={{
                      display:"inline-flex", alignItems:"center", gap:6,
                      padding:"4px 12px", background:"rgba(200,165,90,.08)",
                      border:"1px solid rgba(200,165,90,.2)", borderRadius:20,
                      fontSize:10, color:"#8a5820", fontWeight:700,
                      letterSpacing:".08em", marginBottom:14,
                    }}>
                      {isMale ? "♂ Men's Look" : "♀ Women's Look"} · {skinTone} skin optimized
                    </div>

                    {/* Alternative outfit */}
                    <div className="pa-alt-card">
                      <div className="pa-alt-title">{result.alternative_outfit.description}</div>
                      <div className="pa-alt-grid">
                        {[
                          [isMale?"👕 Top":"👚 Top",           result.alternative_outfit.top],
                          [isMale?"👖 Bottom":"👗 Bottom",      result.alternative_outfit.bottom],
                          ["👟 Shoes",                          result.alternative_outfit.shoes],
                        ].map(([k, v]) => v ? (
                          <div key={k} className="pa-alt-item">
                            <div className="pa-alt-k">{k}</div>
                            <div className="pa-alt-v">{v}</div>
                          </div>
                        ) : null)}
                      </div>
                      {result.alternative_outfit.accessories?.length > 0 && (
                        <div>
                          <div style={{ fontSize:9, color:"#a8998a", fontWeight:700, letterSpacing:".15em", textTransform:"uppercase", marginBottom:8 }}>
                            {isMale ? "♂ Men's Accessories" : "♀ Women's Accessories"}
                          </div>
                          <div className="pa-alt-acc">
                            {result.alternative_outfit.accessories
                              .filter(a => {
                                const al = a.toLowerCase();
                                if (isMale && (al.includes("necklace")||al.includes("earring")||al.includes("bindi"))) return false;
                                return true;
                              })
                              .map((a, i) => <span key={i} className="pa-alt-ap">{a}</span>)}
                          </div>
                        </div>
                      )}
                      {result.alternative_outfit.why_better && (
                        <div className="pa-alt-why">💡 {result.alternative_outfit.why_better}</div>
                      )}
                    </div>

                    {/* ── Shop This Look — REAL IMAGES + SAVE BUTTONS ── */}
                    {result.alternative_products && Object.keys(result.alternative_products).length > 0 && (
                      <div>
                        {/* Alert banner */}
                        <div className="pa-alert-banner">
                          🔔 Tap <strong style={{ marginLeft:4, marginRight:4 }}>"Alert me"</strong> on any product to track price drops via WhatsApp + email.
                        </div>

                        <div className="pa-sl">🛒 Shop This {genderLabel} Look</div>

                        {Object.entries(result.alternative_products).map(([cat, prods]) => {
                          const deduplicated = deduplicateProducts(prods);
                          if (!deduplicated || deduplicated.length===0) return null;
                          return (
                            <div key={cat} style={{ marginBottom:24 }}>
                              <div style={{
                                fontSize:10, fontWeight:700, color:"#8a7a6a",
                                letterSpacing:".15em", textTransform:"uppercase",
                                marginBottom:12, display:"flex", alignItems:"center", gap:6,
                              }}>
                                <span>{CAT_EMOJI[cat]||"🛍"}</span>
                                {CAT_LABELS[cat] || cat.replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase())}
                                <span style={{ fontSize:10, color:"#c4b4a4" }}>({deduplicated.length} options)</span>
                              </div>
                              <div className="pa-prod-grid">
                                {deduplicated.slice(0,4).map((p, i) => (
                                  <ProductCardWithAlert key={i} p={p} userId={userId}/>
                                ))}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Fallback */}
                    {(!result.alternative_products || Object.keys(result.alternative_products).length===0) && (
                      <div style={{ fontSize:12, color:"#a8998a", padding:"12px 0" }}>
                        Product recommendations loading... Check your Serper API key if they don't appear.
                      </div>
                    )}
                  </div>
                )}

              </div>
            </div>
          );
        })()}
      </div>
    </>
  );
}