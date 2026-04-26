import { useState, useRef } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const ACCESSORIES = [
  { value: "sunglasses", label: "Sunglasses", icon: "🕶️" },
  { value: "earrings",   label: "Earrings",   icon: "💎" },
  { value: "bracelet",   label: "Bracelet",   icon: "📿" },
  { value: "ring",       label: "Ring",       icon: "💍" },
  { value: "necklace",   label: "Necklace",   icon: "✨" },
  { value: "hat",        label: "Hat",        icon: "🎩" },
];

export default function TryOnPage() {
  const [file, setFile]       = useState(null);
  const [preview, setPreview] = useState(null);
  const [type, setType]       = useState("sunglasses");
  const [started, setStarted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const fileRef               = useRef();

  const handleFile = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setStarted(false);
    setError("");
  };

  const upload = async () => {
    if (!file) { setError("Please select an accessory image first."); return; }
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("image", file);
      formData.append("type", type);
      await axios.post(`${API}/upload-accessory`, formData);
      setStarted(true);
    } catch (err) {
      setError("❌ Could not connect to Flask server. Make sure it's running on port 5000 and flask-cors is installed.");
    } finally {
      setLoading(false);
    }
  };

  const reset = async () => {
    try { await axios.post(`${API}/reset-accessory`); } catch {}
    setStarted(false);
    setFile(null);
    setPreview(null);
  };

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>✨ Virtual Try-On Lab</h1>
        <p style={styles.sub}>Upload an accessory → pick category → see it on you live</p>
      </div>

      <div style={styles.body}>
        {/* LEFT PANEL */}
        <div style={styles.panel}>
          <h2 style={styles.panelTitle}>1. Choose Accessory Type</h2>
          <div style={styles.typeGrid}>
            {ACCESSORIES.map((a) => (
              <button
                key={a.value}
                onClick={() => { setType(a.value); setStarted(false); }}
                style={{
                  ...styles.typeBtn,
                  ...(type === a.value ? styles.typeBtnActive : {}),
                }}
              >
                <span style={{ fontSize: 24 }}>{a.icon}</span>
                <span style={{ fontSize: 12, marginTop: 4 }}>{a.label}</span>
              </button>
            ))}
          </div>

          <h2 style={{ ...styles.panelTitle, marginTop: 28 }}>2. Upload Image</h2>
          <div
            style={styles.dropzone}
            onClick={() => fileRef.current.click()}
          >
            {preview
              ? <img src={preview} alt="preview" style={styles.previewImg} />
              : <span style={styles.dropText}>Click to upload<br /><span style={{ fontSize: 12, opacity: 0.6 }}>PNG with transparent bg works best</span></span>
            }
          </div>
          <input ref={fileRef} type="file" accept="image/*" onChange={handleFile} style={{ display: "none" }} />

          {error && <p style={styles.error}>{error}</p>}

          <div style={styles.btnRow}>
            <button
              onClick={upload}
              disabled={loading || !file}
              style={{ ...styles.primaryBtn, opacity: (!file || loading) ? 0.5 : 1 }}
            >
              {loading ? "Processing…" : "🚀 Start Try-On"}
            </button>
            {started && (
              <button onClick={reset} style={styles.resetBtn}>✕ Reset</button>
            )}
          </div>

          {/* Tips */}
          <div style={styles.tips}>
            <p style={styles.tipsTitle}>💡 Tips for best results</p>
            <ul style={styles.tipsList}>
              <li>Use PNG images with transparent backgrounds</li>
              <li>Background removal is automatic if needed</li>
              <li>Good lighting improves face/hand detection</li>
              <li>Face the camera directly for face accessories</li>
            </ul>
          </div>
        </div>

        {/* RIGHT PANEL — Live Feed */}
        <div style={styles.feedPanel}>
          <h2 style={styles.panelTitle}>3. Live Preview</h2>
          {started ? (
            <div style={styles.feedWrapper}>
              <img
                src={`${API}/virtual-tryon?t=${Date.now()}`}
                alt="Live Try-On"
                style={styles.feed}
                key={started} // force re-mount on new upload
              />
              <div style={styles.liveTag}>● LIVE</div>
            </div>
          ) : (
            <div style={styles.feedPlaceholder}>
              <span style={{ fontSize: 48 }}>📷</span>
              <p style={{ margin: "12px 0 0", opacity: 0.5 }}>
                Upload an accessory and click <strong>Start Try-On</strong>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────────
const styles = {
  page: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
    fontFamily: "'Segoe UI', sans-serif",
    color: "#fff",
    padding: "0 0 60px",
  },
  header: {
    textAlign: "center",
    padding: "40px 20px 24px",
    borderBottom: "1px solid rgba(255,255,255,0.08)",
  },
  title: {
    margin: 0,
    fontSize: 36,
    fontWeight: 800,
    letterSpacing: "-1px",
    background: "linear-gradient(90deg, #f9a8d4, #a78bfa, #7dd3fc)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  sub: {
    margin: "8px 0 0",
    opacity: 0.6,
    fontSize: 15,
  },
  body: {
    display: "flex",
    gap: 28,
    maxWidth: 1100,
    margin: "36px auto 0",
    padding: "0 24px",
    flexWrap: "wrap",
  },
  panel: {
    flex: "0 0 300px",
    background: "rgba(255,255,255,0.05)",
    borderRadius: 20,
    padding: 24,
    backdropFilter: "blur(10px)",
    border: "1px solid rgba(255,255,255,0.1)",
  },
  panelTitle: {
    margin: "0 0 14px",
    fontSize: 14,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "1px",
    opacity: 0.7,
  },
  typeGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 10,
  },
  typeBtn: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "12px 8px",
    borderRadius: 12,
    border: "2px solid rgba(255,255,255,0.1)",
    background: "rgba(255,255,255,0.04)",
    color: "#fff",
    cursor: "pointer",
    transition: "all 0.2s",
  },
  typeBtnActive: {
    border: "2px solid #a78bfa",
    background: "rgba(167,139,250,0.2)",
    boxShadow: "0 0 12px rgba(167,139,250,0.3)",
  },
  dropzone: {
    border: "2px dashed rgba(255,255,255,0.2)",
    borderRadius: 14,
    height: 140,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    transition: "border-color 0.2s",
    overflow: "hidden",
  },
  dropText: {
    textAlign: "center",
    opacity: 0.5,
    fontSize: 14,
    lineHeight: 1.6,
  },
  previewImg: {
    maxWidth: "100%",
    maxHeight: 136,
    objectFit: "contain",
    borderRadius: 10,
  },
  error: {
    marginTop: 10,
    fontSize: 13,
    color: "#f87171",
    lineHeight: 1.5,
  },
  btnRow: {
    display: "flex",
    gap: 10,
    marginTop: 18,
  },
  primaryBtn: {
    flex: 1,
    padding: "12px 0",
    borderRadius: 12,
    border: "none",
    background: "linear-gradient(135deg, #a78bfa, #7c3aed)",
    color: "#fff",
    fontWeight: 700,
    fontSize: 14,
    cursor: "pointer",
    transition: "transform 0.1s",
  },
  resetBtn: {
    padding: "12px 16px",
    borderRadius: 12,
    border: "1px solid rgba(255,255,255,0.2)",
    background: "transparent",
    color: "#fff",
    cursor: "pointer",
    fontSize: 14,
  },
  tips: {
    marginTop: 24,
    background: "rgba(255,255,255,0.04)",
    borderRadius: 12,
    padding: "14px 16px",
    border: "1px solid rgba(255,255,255,0.07)",
  },
  tipsTitle: {
    margin: "0 0 8px",
    fontSize: 13,
    fontWeight: 700,
  },
  tipsList: {
    margin: 0,
    paddingLeft: 18,
    fontSize: 12,
    opacity: 0.6,
    lineHeight: 1.9,
  },
  feedPanel: {
    flex: 1,
    minWidth: 300,
    background: "rgba(255,255,255,0.05)",
    borderRadius: 20,
    padding: 24,
    backdropFilter: "blur(10px)",
    border: "1px solid rgba(255,255,255,0.1)",
    display: "flex",
    flexDirection: "column",
  },
  feedWrapper: {
    position: "relative",
    flex: 1,
    borderRadius: 14,
    overflow: "hidden",
    background: "#000",
  },
  feed: {
    width: "100%",
    borderRadius: 14,
    display: "block",
  },
  liveTag: {
    position: "absolute",
    top: 12,
    left: 12,
    background: "rgba(239,68,68,0.9)",
    color: "#fff",
    fontSize: 12,
    fontWeight: 700,
    padding: "4px 10px",
    borderRadius: 20,
    letterSpacing: "1px",
  },
  feedPlaceholder: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    border: "2px dashed rgba(255,255,255,0.1)",
    color: "#fff",
    textAlign: "center",
    padding: 40,
  },
};