import { useState, useRef, useCallback, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const ACTIONS = [
  { id: "camera-detect", label: "Live Camera", icon: "◉", desc: "Real-time detection", live: true },
  { id: "detect-face", label: "Detect Face", icon: "◎", desc: "Find faces in image" },
  { id: "face-landmarks", label: "Landmarks", icon: "⬡", desc: "478 facial points" },
  { id: "face-shape", label: "Face Shape", icon: "◇", desc: "Geometry analysis" },
  { id: "skin-tone", label: "Skin Tone", icon: "◐", desc: "Tone classification" },
  { id: "draw-landmarks", label: "Face Mesh", icon: "⌘", desc: "Visualize mesh" },
  { id: "detect-skin", label: "Skin Analysis", icon: "✦", desc: "Detect acne & issues" },
];

const SHAPE_ICONS = { oval: "🥚", round: "⭕", heart: "♡", square: "⬜", unknown: "?" };
const TONE_COLORS = { light: "#F5DEB3", medium: "#C68642", dark: "#4A2C17" };

// ── Accent color tokens (purple palette) ─────────────────────────────────────
const A = {
  full:    "#8b5cf6",          // vivid violet
  bright:  "#a78bfa",          // lighter violet
  dim:     "rgba(139,92,246,0.5)",
  glow:    "rgba(139,92,246,0.35)",
  bg1:     "rgba(139,92,246,0.03)",
  bg2:     "rgba(139,92,246,0.08)",
  bg3:     "rgba(139,92,246,0.14)",
  border1: "rgba(139,92,246,0.12)",
  border2: "rgba(139,92,246,0.3)",
  border3: "rgba(139,92,246,0.55)",
  grid:    "rgba(139,92,246,0.04)",
};

// ── Sci-fi decorators ─────────────────────────────────────────────────────────

const ScanLine = () => (
  <div style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden", borderRadius: "inherit" }}>
    <div style={{
      position: "absolute", left: 0, right: 0, height: 2,
      background: `linear-gradient(90deg, transparent, ${A.full} 40%, ${A.bright} 60%, transparent)`,
      animation: "scanline 3s linear infinite", opacity: 0.7,
      boxShadow: `0 0 14px ${A.full}`
    }} />
  </div>
);

const GridOverlay = () => (
  <div style={{
    position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
    backgroundImage: `linear-gradient(${A.grid} 1px, transparent 1px), linear-gradient(90deg, ${A.grid} 1px, transparent 1px)`,
    backgroundSize: "44px 44px"
  }} />
);

const Corner = ({ pos }) => {
  const base = { position: "absolute", width: 18, height: 18 };
  const b = `2px solid ${A.full}`;
  const corners = {
    tl: { top: 0, left: 0, borderTop: b, borderLeft: b },
    tr: { top: 0, right: 0, borderTop: b, borderRight: b },
    bl: { bottom: 0, left: 0, borderBottom: b, borderLeft: b },
    br: { bottom: 0, right: 0, borderBottom: b, borderRight: b },
  };
  return <div style={{ ...base, ...corners[pos] }} />;
};

// ── Smart result card ─────────────────────────────────────────────────────────

function ResultCard({ result }) {
  if (!result || Object.keys(result).length === 0) return null;
  const entries = Object.entries(result).filter(([k]) => k !== "image_path");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {entries.map(([key, val]) => {
        const label = key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
        let display = typeof val === "object" ? null : String(val);
        let accent = null;

        if (key === "face_shape") {
          display = val.charAt(0).toUpperCase() + val.slice(1);
          accent = SHAPE_ICONS[val] || "?";
        } else if (key === "skin_tone") {
          accent = <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: "50%", background: TONE_COLORS[val] || "#999", verticalAlign: "middle", marginRight: 6, border: "1px solid rgba(255,255,255,0.2)" }} />;
          display = val.charAt(0).toUpperCase() + val.slice(1);
        } else if (typeof val === "boolean") {
          display = val ? "Yes" : "No";
          accent = <span style={{ color: val ? A.bright : "#f87171" }}>{val ? "✓" : "✗"}</span>;
        } else if (typeof val === "number") {
          display = val.toFixed(4);
        }

        return (
          <div key={key} style={{
            background: A.bg1,
            border: `1px solid ${A.border1}`,
            borderRadius: 8, padding: "11px 14px",
            display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12
          }}>
            <span style={{ fontSize: 10, color: A.dim, textTransform: "uppercase", letterSpacing: "0.12em", paddingTop: 2, flexShrink: 0 }}>
              {label}
            </span>
            {typeof val === "object" && val !== null ? (
              <div style={{ fontSize: 11, color: "#e8e0ff", textAlign: "right" }}>
                {Object.entries(val).map(([k2, v2]) => (
                  <div key={k2} style={{ marginBottom: 2 }}>
                    <span style={{ color: A.dim, marginRight: 6 }}>{k2.replace(/_/g, " ")}:</span>
                    <span style={{ color: A.bright, fontWeight: 700 }}>
                      {typeof v2 === "number" ? v2.toFixed(3) : String(v2)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <span style={{ fontSize: 13, color: A.bright, fontWeight: 700, fontFamily: "'DM Mono', monospace", textAlign: "right" }}>
                {accent && <span style={{ marginRight: 5 }}>{accent}</span>}
                {display}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState({});
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [scanActive, setScanActive] = useState(false);
  const [toast, setToast] = useState(null);
  const [mounted, setMounted] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  const fileRef = useRef();
  const videoRef = useRef(null);
  const intervalRef = useRef(null);

  useEffect(() => { setMounted(true); }, []);

  const showToast = (msg, type = "error") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleFile = (file) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) return showToast("Please upload an image file");
    setImage(file);
    setPreview(URL.createObjectURL(file));
    setResult({});
    setActiveAction(null);
    setShowRaw(false);
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  }, []);

  const startRealtimeDetection = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      setActiveAction("camera-detect");
      setScanActive(true);
      setTimeout(() => { if (videoRef.current) videoRef.current.srcObject = stream; }, 200);
      intervalRef.current = setInterval(captureFrameAndDetect, 800);
    } catch {
      showToast("Camera access denied");
    }
  };

  const stopCamera = () => {
    clearInterval(intervalRef.current);
    if (videoRef.current?.srcObject) videoRef.current.srcObject.getTracks().forEach(t => t.stop());
    setActiveAction(null);
    setScanActive(false);
  };

  const captureFrameAndDetect = async () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const blob = await new Promise(res => canvas.toBlob(res, "image/jpeg"));
    const formData = new FormData();
    formData.append("image", blob, "frame.jpg");
    try {
      const res = await axios.post(`${API}/detect-skin`, formData);
      if (res.data.image_path) setPreview(`${API}/${res.data.image_path}?t=${Date.now()}`);
      setResult(res.data);
    } catch { }
  };

  const analyze = async (endpoint) => {
    if (!image) return showToast("Upload an image first");
    const formData = new FormData();
    formData.append("image", image);
    setLoading(true);
    setActiveAction(endpoint);
    setScanActive(true);
    setShowRaw(false);
    try {
      const res = await axios.post(`${API}/${endpoint}`, formData);
      if (res.data.image_path) setPreview(`${API}/${res.data.image_path}`);
      setResult(res.data);
      showToast("Analysis complete", "success");
    } catch {
      showToast("Server error — is Flask running?");
    }
    setLoading(false);
    setScanActive(false);
  };

  const hasResult = Object.keys(result).length > 0;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
          background: #0a0a0f;
          color: #e8e0ff;
          font-family: 'Syne', sans-serif;
          min-height: 100vh;
        }

        @keyframes scanline { 0% { top: -2px; } 100% { top: 100%; } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes toastIn { from { opacity: 0; transform: translateY(8px) translateX(-50%); } to { opacity: 1; transform: translateY(0) translateX(-50%); } }
        @keyframes pulse-ring {
          0%   { box-shadow: 0 0 0 0   rgba(139,92,246,0.45); }
          70%  { box-shadow: 0 0 0 10px rgba(139,92,246,0); }
          100% { box-shadow: 0 0 0 0   rgba(139,92,246,0); }
        }

        .action-btn {
          background: rgba(139,92,246,0.03);
          border: 1px solid rgba(139,92,246,0.12);
          color: #a78bfa99;
          font-family: 'Syne', sans-serif;
          font-size: 12px;
          padding: 12px 16px;
          cursor: pointer;
          transition: all 0.18s;
          text-align: left;
          width: 100%;
          border-radius: 8px;
        }
        .action-btn:hover:not(:disabled) {
          background: rgba(139,92,246,0.09);
          border-color: rgba(139,92,246,0.45);
          color: #c4b5fd;
        }
        .action-btn.active {
          background: rgba(139,92,246,0.14);
          border-color: #8b5cf6;
          color: #c4b5fd;
          animation: pulse-ring 2s infinite;
        }
        .action-btn:disabled { opacity: 0.3; cursor: not-allowed; }

        .upload-zone {
          border: 1.5px dashed rgba(139,92,246,0.22);
          background: rgba(139,92,246,0.02);
          cursor: pointer;
          transition: all 0.2s;
          border-radius: 12px;
        }
        .upload-zone:hover, .upload-zone.drag {
          border-color: rgba(139,92,246,0.6);
          background: rgba(139,92,246,0.07);
        }

        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(139,92,246,0.3); border-radius: 2px; }
      `}</style>

      {/* Background radial mesh — same as reference */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none",
        background: "radial-gradient(ellipse 80% 60% at 20% 10%, rgba(88,28,135,0.2) 0%, transparent 60%), radial-gradient(ellipse 60% 50% at 80% 80%, rgba(109,40,217,0.1) 0%, transparent 60%)"
      }} />
      <GridOverlay />

      <div style={{ position: "relative", zIndex: 1, minHeight: "100vh" }}>

        {/* ── Header ── */}
        <header style={{
          padding: "22px 40px",
          borderBottom: "1px solid rgba(139,92,246,0.1)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          animation: mounted ? "fadeUp 0.5s ease both" : "none"
        }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 7, height: 7, borderRadius: "50%", background: A.full, boxShadow: `0 0 8px ${A.full}`, animation: "blink 2.5s ease infinite" }} />
              <span style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 20, letterSpacing: "-0.5px", color: "#fff" }}>
                FACEFIT<span style={{ color: A.full }}>_AI</span>
              </span>
            </div>
            <div style={{ fontSize: 9, color: A.dim, marginTop: 3, letterSpacing: "0.18em" }}>
              FACIAL ANALYSIS SYSTEM v2.0
            </div>
          </div>

          {/* Badge — same pill style as reference header */}
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 8,
            background: "rgba(139,92,246,0.12)", border: `1px solid ${A.border2}`,
            borderRadius: 100, padding: "5px 14px", fontSize: 10,
            letterSpacing: "0.15em", color: A.bright, textTransform: "uppercase"
          }}>
            ◉ AI Vision Analysis
          </div>

          <div style={{ fontSize: 10, color: "rgba(139,92,246,0.4)", textAlign: "right", letterSpacing: "0.1em" }}>
            <div>STATUS: <span style={{ color: A.full }}>ONLINE</span></div>
            <div style={{ marginTop: 2 }}>{new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })}</div>
          </div>
        </header>

        {/* ── Body ── */}
        <div style={{
          maxWidth: 1160, margin: "0 auto", padding: "36px 32px",
          display: "grid", gridTemplateColumns: "220px 1fr 1fr", gap: 24,
          animation: mounted ? "fadeUp 0.5s 0.1s ease both" : "none", opacity: mounted ? undefined : 0
        }}>

          {/* LEFT — Modules */}
          <div>
            <div style={{ fontSize: 9, letterSpacing: "0.18em", color: A.dim, marginBottom: 12 }}>ANALYSIS MODULES</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {ACTIONS.map((a) => (
                <button
                  key={a.id}
                  className={`action-btn ${activeAction === a.id ? "active" : ""}`}
                  disabled={loading && activeAction !== a.id}
                  onClick={() => {
                    if (a.id === "camera-detect") {
                      activeAction === "camera-detect" ? stopCamera() : startRealtimeDetection();
                    } else {
                      analyze(a.id);
                    }
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 15, minWidth: 18, opacity: 0.85 }}>{a.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 12 }}>{a.label}</div>
                      <div style={{ fontSize: 9, opacity: 0.45, marginTop: 1 }}>{a.desc}</div>
                    </div>
                    {activeAction === a.id && loading && (
                      <div style={{ width: 11, height: 11, border: `2px solid ${A.border1}`, borderTopColor: A.full, borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                    )}
                    {activeAction === a.id && !loading && (
                      <span style={{ fontSize: 10, color: A.full }}>✓</span>
                    )}
                  </div>
                </button>
              ))}
            </div>

            {activeAction === "camera-detect" && (
              <button onClick={stopCamera} style={{
                marginTop: 10, width: "100%", padding: "9px", fontSize: 10,
                background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.25)",
                color: "#f87171", cursor: "pointer", fontFamily: "'Syne', sans-serif",
                borderRadius: 8, letterSpacing: "0.08em", fontWeight: 700
              }}>
                ◼ STOP CAMERA
              </button>
            )}
          </div>

          {/* CENTRE — Upload + Preview */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ fontSize: 9, letterSpacing: "0.18em", color: A.dim }}>VISUAL OUTPUT</div>

            {!preview && activeAction !== "camera-detect" && (
              <div
                className={`upload-zone ${dragOver ? "drag" : ""}`}
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                style={{ padding: "60px 24px", textAlign: "center", minHeight: 300, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12 }}
              >
                <div style={{ fontSize: 36, opacity: 0.25 }}>⬆</div>
                <p style={{ fontSize: 13, color: "#777" }}>
                  <span style={{ color: A.bright, fontWeight: 600 }}>Click to upload</span> or drag & drop
                </p>
                <p style={{ fontSize: 11, color: "#555" }}>PNG · JPG · WEBP</p>
                <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => handleFile(e.target.files[0])} />
              </div>
            )}

            {preview && activeAction !== "camera-detect" && (
              <div style={{ position: "relative", borderRadius: 12, overflow: "hidden", background: "#111", border: `1px solid ${A.border1}` }}>
                {scanActive && <ScanLine />}
                <Corner pos="tl" /><Corner pos="tr" /><Corner pos="bl" /><Corner pos="br" />
                <img src={preview} alt="preview" style={{ width: "100%", maxHeight: 420, objectFit: "contain", display: "block" }} />
                {loading && (
                  <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.55)", display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(4px)" }}>
                    <div style={{ width: 40, height: 40, border: `3px solid ${A.border2}`, borderTopColor: A.full, borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                  </div>
                )}
              </div>
            )}

            {activeAction === "camera-detect" && (
              <div style={{ position: "relative", borderRadius: 12, overflow: "hidden", background: "#111", border: `1px solid ${A.border1}` }}>
                <ScanLine />
                <Corner pos="tl" /><Corner pos="tr" /><Corner pos="bl" /><Corner pos="br" />
                <video ref={videoRef} autoPlay playsInline style={{ width: "100%", maxHeight: 420, display: "block" }} />
                <div style={{ position: "absolute", top: 12, left: 12, background: "rgba(220,30,30,0.85)", borderRadius: 4, padding: "3px 10px", fontSize: 9, letterSpacing: "0.15em", color: "#fff", display: "flex", alignItems: "center", gap: 5 }}>
                  <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#fff", animation: "blink 1s infinite" }} />
                  LIVE
                </div>
              </div>
            )}

            {preview && (
              <div>
                <button onClick={() => fileRef.current?.click()} style={{ fontSize: 11, padding: "7px 16px", background: "transparent", border: `1px solid ${A.border2}`, color: A.bright, cursor: "pointer", fontFamily: "'Syne', sans-serif", borderRadius: 8, letterSpacing: "0.06em", fontWeight: 600 }}>
                  ↑ New Image
                </button>
                <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => handleFile(e.target.files[0])} />
              </div>
            )}
          </div>

          {/* RIGHT — Results */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ fontSize: 9, letterSpacing: "0.18em", color: A.dim }}>ANALYSIS RESULTS</div>

            <div style={{
              background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: 16, padding: 20, minHeight: 120,
              display: "flex", flexDirection: "column", gap: 10
            }}>
              {!hasResult && !loading && (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1, minHeight: 100 }}>
                  <p style={{ fontSize: 13, color: "#444", textAlign: "center" }}>Run an analysis to see results</p>
                </div>
              )}
              {loading && (
                <div style={{ display: "flex", alignItems: "center", gap: 10, color: A.dim, fontSize: 12, padding: "8px 0" }}>
                  <div style={{ width: 14, height: 14, border: `2px solid ${A.border2}`, borderTopColor: A.full, borderRadius: "50%", animation: "spin 0.8s linear infinite", flexShrink: 0 }} />
                  PROCESSING...
                </div>
              )}
              {hasResult && (
                <div style={{ animation: "fadeUp 0.35s ease" }}>
                  <ResultCard result={result} />
                </div>
              )}
            </div>

            {hasResult && (
              <div>
                <button
                  onClick={() => setShowRaw(v => !v)}
                  style={{ fontSize: 10, color: "#555", background: "none", border: "none", cursor: "pointer", fontFamily: "'Syne', sans-serif", letterSpacing: "0.1em", textTransform: "uppercase", padding: "4px 0" }}
                >
                  {showRaw ? "▾" : "▸"} Raw JSON
                </button>
                {showRaw && (
                  <pre style={{
                    marginTop: 8, padding: 14, borderRadius: 10, fontSize: 11,
                    color: A.full, fontFamily: "'DM Mono', monospace",
                    background: "rgba(0,0,0,0.4)", border: `1px solid ${A.border2}`,
                    overflow: "auto", lineHeight: 1.7, maxHeight: 280,
                    animation: "fadeUp 0.25s ease"
                  }}>
                    {JSON.stringify(result, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Toast ── */}
      {toast && (
        <div style={{
          position: "fixed", bottom: 32, left: "50%", transform: "translateX(-50%)",
          background: toast.type === "error" ? "rgba(220,38,38,0.92)" : "rgba(5,150,105,0.92)",
          color: "#fff", padding: "10px 22px", borderRadius: 100,
          fontSize: 13, fontWeight: 600, fontFamily: "'Syne', sans-serif",
          backdropFilter: "blur(10px)", animation: "toastIn 0.3s ease",
          zIndex: 999, boxShadow: "0 8px 32px rgba(0,0,0,0.5)", letterSpacing: "0.04em"
        }}>
          {toast.msg}
        </div>
      )}
    </>
  );
}
