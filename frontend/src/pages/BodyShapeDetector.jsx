/**
 * BodyShapeDetector.jsx — Body Shape Detection + Outfit Recommendations
 * Feature 7: MediaPipe Pose analysis from full-body photo
 */
import { useState, useRef } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const SHAPE_ICONS = {
  hourglass:         "⌛",
  rectangle:         "▭",
  pear:              "🍐",
  apple:             "🍎",
  inverted_triangle: "△",
};

const SHAPE_COLORS = {
  hourglass:         { bg: "rgba(200,165,90,.08)",  border: "rgba(200,165,90,.3)",  accent: "#c8a55a" },
  rectangle:         { bg: "rgba(30,80,53,.06)",    border: "rgba(30,80,53,.25)",   accent: "#1e5035" },
  pear:              { bg: "rgba(0,105,156,.06)",   border: "rgba(0,105,156,.25)",  accent: "#00699c" },
  apple:             { bg: "rgba(192,57,43,.06)",   border: "rgba(192,57,43,.25)",  accent: "#c0392b" },
  inverted_triangle: { bg: "rgba(90,60,160,.06)",   border: "rgba(90,60,160,.25)",  accent: "#5a3ca0" },
};

const CAT_LABELS = { shirt: "👕 Top", pants: "👖 Bottom", ethnic: "🥻 Ethnic/Dress" };

export default function BodyShapeDetector({ user, onShapeDetected }) {
  const [loading,   setLoading]   = useState(false);
  const [result,    setResult]    = useState(null);
  const [preview,   setPreview]   = useState(null);
  const [error,     setError]     = useState("");
  const [file,      setFile]      = useState(null);
  const [activeTab, setActiveTab] = useState("advice");
  const fileRef = useRef();

  const handleFile = (f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setError("");
  };

  const analyze = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    const fd = new FormData();
    fd.append("image", file);
    fd.append("gender", user?.gender || "male");
    fd.append("skin_tone", user?.skinTone || "medium");
    try {
      const r = await axios.post(`${API}/detect-body-shape`, fd);
      setResult(r.data);
      onShapeDetected?.(r.data);
    } catch (e) {
      const msg = e?.response?.data?.error || "Analysis failed. Please use a clear full-body photo.";
      setError(msg);
    }
    setLoading(false);
  };

  const S = {
    wrap:       { padding: "20px 0", maxWidth: 680 },
    uploadCard: { border: "1.5px dashed #ddd3c2", borderRadius: 14, padding: "28px 20px", textAlign: "center", cursor: "pointer", background: "#faf7f3", transition: "all .2s" },
    previewWrap:{ position: "relative", borderRadius: 14, overflow: "hidden", border: "1px solid #ece6dc" },
    previewImg: { width: "100%", maxHeight: 320, objectFit: "contain", display: "block", background: "#f7f3ee" },
    analyzeBtn: { width: "100%", marginTop: 12, padding: 14, background: "#1a0f00", border: "none", color: "#c8a55a", borderRadius: 8, fontFamily: "inherit", fontSize: 11, fontWeight: 700, letterSpacing: ".18em", textTransform: "uppercase", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 10, transition: "all .2s" },
    resultCard: (shape) => ({ background: SHAPE_COLORS[shape]?.bg || "rgba(200,165,90,.06)", border: `1px solid ${SHAPE_COLORS[shape]?.border || "rgba(200,165,90,.2)"}`, borderRadius: 14, padding: "20px 22px", marginTop: 16 }),
    shapeHeader:{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 },
    shapeBadge: (shape) => ({ width: 52, height: 52, borderRadius: "50%", background: SHAPE_COLORS[shape]?.accent || "#c8a55a", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, flexShrink: 0 }),
    tabs:       { display: "flex", gap: 6, marginBottom: 14, borderBottom: "1px solid #ece6dc", paddingBottom: 8 },
    tab:        (a) => ({ padding: "5px 14px", border: "none", background: "none", fontFamily: "inherit", fontSize: 12, fontWeight: a ? 700 : 400, color: a ? "#8a5820" : "#8a7a6a", borderBottom: `2px solid ${a ? "#c8a55a" : "transparent"}`, cursor: "pointer", marginBottom: -9 }),
    list:       { paddingLeft: 16, margin: "6px 0 0" },
    listItem:   { fontSize: 12.5, color: "#3a2e24", lineHeight: 1.8, listStyleType: "'✦ '" },
    avoidItem:  { fontSize: 12, color: "#7a5048", lineHeight: 1.8, listStyleType: "'✕ '" },
    hack:       { fontSize: 12.5, color: "#3a2e24", padding: "10px 14px", background: "rgba(200,165,90,.06)", borderLeft: "3px solid #c8a55a", borderRadius: "0 8px 8px 0", lineHeight: 1.65, marginTop: 10 },
    prodGrid:   { display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(140px,1fr))", gap: 10, marginTop: 10 },
    prodCard:   { border: "1px solid #ece6dc", borderRadius: 10, overflow: "hidden", background: "#fff", textDecoration: "none", display: "block", transition: "transform .2s", cursor: "pointer" },
    prodImg:    { height: 120, background: "#f7f3ee", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" },
    prodInfo:   { padding: "8px 10px 12px" },
    prodTitle:  { fontSize: 11, color: "#2c1f0f", lineHeight: 1.4, marginBottom: 5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" },
    prodPrice:  { fontSize: 13, fontWeight: 700, color: "#8a5820" },
    spinner:    { width: 14, height: 14, border: "2px solid rgba(200,165,90,.3)", borderTopColor: "#c8a55a", borderRadius: "50%", animation: "spin .8s linear infinite" },
  };

  return (
    <div style={S.wrap}>
      {/* Upload zone */}
      {!preview ? (
        <div style={S.uploadCard} onClick={() => fileRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); }}>
          <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
            onChange={e => handleFile(e.target.files[0])} />
          <div style={{ fontSize: 40, marginBottom: 12, opacity: .6 }}>🧍</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#3a2e24", marginBottom: 4 }}>Upload Full-Body Photo</div>
          <div style={{ fontSize: 12, color: "#8a7a6a", lineHeight: 1.65 }}>
            MediaPipe AI detects your body proportions and recommends outfits that flatter your shape.<br />
            <span style={{ color: "#c8a55a", fontWeight: 600 }}>Stand straight, face the camera, full body visible.</span>
          </div>
        </div>
      ) : (
        <div>
          <div style={S.previewWrap}>
            <img src={preview} alt="Body" style={S.previewImg} />
            <button onClick={() => { setPreview(null); setFile(null); setResult(null); }}
              style={{ position: "absolute", top: 10, right: 10, background: "rgba(26,15,0,.65)", border: "none", color: "#fff", borderRadius: "50%", width: 30, height: 30, cursor: "pointer", fontSize: 14, display: "flex", alignItems: "center", justifyContent: "center" }}>✕</button>
          </div>
          {!result && (
            <button style={S.analyzeBtn} onClick={analyze} disabled={loading}>
              {loading ? <><span style={S.spinner} /> Detecting body shape...</> : "Analyze My Body Shape →"}
            </button>
          )}
        </div>
      )}

      {error && (
        <div style={{ marginTop: 10, fontSize: 12, color: "#c05050", background: "rgba(192,57,43,.06)", border: "1px solid rgba(192,57,43,.15)", borderRadius: 8, padding: "10px 14px", lineHeight: 1.65 }}>
          ⚠️ {error}<br />
          <span style={{ fontSize: 10.5, color: "#8a7a6a" }}>Tip: Stand against a plain wall, ensure full body (head to feet) is in frame.</span>
        </div>
      )}

      {result && (
        <div style={S.resultCard(result.body_shape)} className="sp-card">
          {/* Shape header */}
          <div style={S.shapeHeader}>
            <div style={S.shapeBadge(result.body_shape)}>
              {SHAPE_ICONS[result.body_shape] || "👤"}
            </div>
            <div>
              <div style={{ fontSize: 11, letterSpacing: ".2em", textTransform: "uppercase", color: "#b8a898", fontWeight: 600, marginBottom: 2 }}>AI Detected</div>
              <div style={{ fontSize: 20, fontWeight: 300, color: "#1a0f00", fontFamily: "'Cormorant Garamond',serif" }}>
                {result.advice?.shape_label || result.body_shape?.replace(/_/g," ")} Body
              </div>
              <div style={{ fontSize: 11.5, color: "#6a5a4a", marginTop: 3, lineHeight: 1.5 }}>
                {result.advice?.shape_description}
              </div>
            </div>
          </div>

          {/* Measurements */}
          {result.measurements && (
            <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
              {[
                { label: "Shoulder", val: result.measurements.shoulder_hip_ratio, suffix: " ratio" },
                { label: "Waist", val: result.measurements.waist_shoulder_ratio, suffix: " ratio" },
              ].map(({ label, val, suffix }) => (
                <div key={label} style={{ flex: 1, padding: "8px 12px", background: "rgba(255,255,255,.6)", borderRadius: 8, textAlign: "center" }}>
                  <div style={{ fontSize: 17, fontWeight: 300, color: "#1a0f00", fontFamily: "'Cormorant Garamond',serif" }}>{val?.toFixed(2)}</div>
                  <div style={{ fontSize: 9.5, color: "#8a7a6a", textTransform: "uppercase", letterSpacing: ".1em" }}>{label}{suffix}</div>
                </div>
              ))}
            </div>
          )}

          {/* Tabs */}
          <div style={S.tabs}>
            {[["advice","✦ Outfit Advice"],["products","🛍 Shop Now"]].map(([id,label]) => (
              <button key={id} style={S.tab(activeTab===id)} onClick={() => setActiveTab(id)}>{label}</button>
            ))}
          </div>

          {activeTab === "advice" && result.advice && (
            <div>
              <div style={{ fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase", color: "#b8a898", fontWeight: 700, marginBottom: 4 }}>What Works For You</div>
              <ul style={S.list}>
                {(result.advice.what_works || []).map((w, i) => (
                  <li key={i} style={S.listItem}>{w}</li>
                ))}
              </ul>
              {result.advice.what_to_avoid?.length > 0 && (
                <>
                  <div style={{ fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase", color: "#b8a898", fontWeight: 700, marginTop: 12, marginBottom: 4 }}>Avoid</div>
                  <ul style={S.list}>
                    {result.advice.what_to_avoid.map((w, i) => (
                      <li key={i} style={S.avoidItem}>{w}</li>
                    ))}
                  </ul>
                </>
              )}
              {result.advice.styling_hack && (
                <div style={S.hack}>💡 {result.advice.styling_hack}</div>
              )}
              {result.advice.key_pieces && (
                <div style={{ marginTop: 12, display: "flex", gap: 7, flexWrap: "wrap" }}>
                  {result.advice.key_pieces.map((p, i) => (
                    <span key={i} style={{ fontSize: 11, padding: "4px 11px", background: "rgba(200,165,90,.1)", border: "1px solid rgba(200,165,90,.25)", borderRadius: 14, color: "#8a5820", fontWeight: 600 }}>{p}</span>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === "products" && (
            <div>
              {Object.keys(result.products || {}).length === 0 ? (
                <div style={{ fontSize: 12, color: "#a8998a", padding: "12px 0" }}>Loading product recommendations...</div>
              ) : (
                Object.entries(result.products).map(([cat, prods]) => (
                  <div key={cat} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: ".15em", color: "#8a7a6a", textTransform: "uppercase", marginBottom: 8 }}>{CAT_LABELS[cat] || cat}</div>
                    <div style={S.prodGrid}>
                      {(prods || []).slice(0, 4).map((p, i) => (
                        <a key={i} href={p.link} target="_blank" rel="noreferrer" style={S.prodCard}>
                          <div style={S.prodImg}>
                            {p.image
                              ? <img src={p.image} alt={p.title} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                              : <span style={{ fontSize: 28, opacity: .2 }}>◈</span>}
                          </div>
                          <div style={S.prodInfo}>
                            <div style={S.prodTitle}>{p.title}</div>
                            <div style={S.prodPrice}>{p.price || "View Price"}</div>
                          </div>
                        </a>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}