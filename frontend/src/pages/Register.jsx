import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const ScanLine = () => (
  <div style={{
    position: "absolute", top: 0, left: 0, right: 0,
    height: "2px",
    background: "linear-gradient(90deg, transparent, #00ffe0, transparent)",
    animation: "scanDown 2.5s linear infinite",
    zIndex: 10,
  }} />
);

const GridOverlay = () => (
  <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.07 }}>
    <defs>
      <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
        <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#00ffe0" strokeWidth="0.5" />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#grid)" />
  </svg>
);

const CornerBracket = ({ pos }) => {
  const s = 18;
  const thickness = 2;
  const color = "#00ffe0";
  const styles = {
    position: "absolute", width: s, height: s,
    ...(pos === "tl" && { top: 0, left: 0, borderTop: `${thickness}px solid ${color}`, borderLeft: `${thickness}px solid ${color}` }),
    ...(pos === "tr" && { top: 0, right: 0, borderTop: `${thickness}px solid ${color}`, borderRight: `${thickness}px solid ${color}` }),
    ...(pos === "bl" && { bottom: 0, left: 0, borderBottom: `${thickness}px solid ${color}`, borderLeft: `${thickness}px solid ${color}` }),
    ...(pos === "br" && { bottom: 0, right: 0, borderBottom: `${thickness}px solid ${color}`, borderRight: `${thickness}px solid ${color}` }),
  };
  return <div style={styles} />;
};

export default function Register({ onRegistered }) {

  const navigate = useNavigate();   // ✅ add this
  const [name, setName] = useState("");
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState("idle"); // idle | scanning | done | error
  const [dots, setDots] = useState(0);
  const inputRef = useRef();

  useEffect(() => {
    if (!loading) return;
    const id = setInterval(() => setDots(d => (d + 1) % 4), 420);
    return () => clearInterval(id);
  }, [loading]);

  const handleImage = (file) => {
    if (!file) return;
    setImage(file);
    setPreview(URL.createObjectURL(file));
    setPhase("idle");
  };

  const registerUser = async () => {
    if (!name || !image) {
      setPhase("error");
      setTimeout(() => setPhase("idle"), 1800);
      return;
    }
    const formData = new FormData();
    formData.append("name", name);
    formData.append("image", image);
    try {
      setLoading(true);
      setPhase("scanning");
      const res = await axios.post(`${API}/register`, formData);
      setPhase("done");
      localStorage.setItem("faceAnalysis", JSON.stringify(res.data));
      setTimeout(() => {
  navigate("/products");   // ✅ correct React navigation
}, 1200);
    } catch {
      setPhase("error");
    }
    setLoading(false);
  };

  const statusMsg = {
    idle: null,
    scanning: `ANALYZING BIOMETRICS${"·".repeat(dots + 1)}`,
    done: "✓ IDENTITY REGISTERED",
    error: !name || !image ? "⚠ NAME AND PHOTO REQUIRED" : "✗ REGISTRATION FAILED",
  }[phase];

  const btnLabel = loading ? `PROCESSING${"·".repeat(dots + 1)}` : "REGISTER IDENTITY";

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body { background: #03080f; }

        @keyframes scanDown {
          0% { top: 0; opacity: 1; }
          85% { opacity: 0.8; }
          100% { top: 100%; opacity: 0; }
        }

        @keyframes pulse-ring {
          0% { box-shadow: 0 0 0 0 rgba(0,255,224,0.3); }
          70% { box-shadow: 0 0 0 10px rgba(0,255,224,0); }
          100% { box-shadow: 0 0 0 0 rgba(0,255,224,0); }
        }

        @keyframes flicker {
          0%, 98%, 100% { opacity: 1; }
          99% { opacity: 0.7; }
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }

        .register-wrap {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #03080f;
          font-family: 'Rajdhani', sans-serif;
          overflow: hidden;
          position: relative;
        }

        .bg-glow {
          position: fixed;
          width: 600px; height: 600px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(0,255,224,0.055) 0%, transparent 70%);
          top: 50%; left: 50%;
          transform: translate(-50%, -50%);
          pointer-events: none;
        }

        .card {
          position: relative;
          width: 400px;
          background: rgba(4, 14, 24, 0.92);
          border: 1px solid rgba(0,255,224,0.2);
          padding: 36px 32px 32px;
          animation: flicker 8s infinite;
          backdrop-filter: blur(12px);
        }

        .card::before {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(135deg, rgba(0,255,224,0.03) 0%, transparent 60%);
          pointer-events: none;
        }

        .eyebrow {
          font-family: 'Share Tech Mono', monospace;
          font-size: 10px;
          letter-spacing: 0.25em;
          color: #00ffe0;
          opacity: 0.6;
          margin-bottom: 6px;
        }

        .title {
          font-size: 26px;
          font-weight: 700;
          letter-spacing: 0.08em;
          color: #e8f5f3;
          margin-bottom: 28px;
          line-height: 1.1;
        }

        .title span { color: #00ffe0; }

        .field-label {
          font-family: 'Share Tech Mono', monospace;
          font-size: 10px;
          letter-spacing: 0.2em;
          color: rgba(0,255,224,0.5);
          margin-bottom: 6px;
          display: block;
        }

        .field-input {
          width: 100%;
          padding: 11px 14px;
          background: rgba(0,255,224,0.04);
          border: 1px solid rgba(0,255,224,0.18);
          color: #e8f5f3;
          font-family: 'Share Tech Mono', monospace;
          font-size: 13px;
          letter-spacing: 0.06em;
          outline: none;
          transition: border-color 0.2s, background 0.2s;
          margin-bottom: 20px;
        }

        .field-input:focus {
          border-color: rgba(0,255,224,0.55);
          background: rgba(0,255,224,0.07);
        }

        .field-input::placeholder { color: rgba(200,240,235,0.2); }

        .upload-zone {
          position: relative;
          border: 1px dashed rgba(0,255,224,0.25);
          background: rgba(0,255,224,0.03);
          padding: 22px;
          text-align: center;
          cursor: pointer;
          transition: border-color 0.2s, background 0.2s;
          margin-bottom: 20px;
          overflow: hidden;
        }

        .upload-zone:hover {
          border-color: rgba(0,255,224,0.5);
          background: rgba(0,255,224,0.06);
        }

        .upload-zone input {
          position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
        }

        .upload-icon {
          font-size: 28px;
          margin-bottom: 6px;
          opacity: 0.5;
        }

        .upload-hint {
          font-family: 'Share Tech Mono', monospace;
          font-size: 10px;
          letter-spacing: 0.15em;
          color: rgba(0,255,224,0.45);
        }

        .preview-wrap {
          position: relative;
          margin-bottom: 20px;
          overflow: hidden;
          animation: fadeIn 0.35s ease;
        }

        .preview-img {
          width: 100%;
          display: block;
          filter: saturate(0.7) contrast(1.1);
        }

        .preview-overlay {
          position: absolute;
          inset: 0;
          background: linear-gradient(180deg, transparent 60%, rgba(3,8,15,0.8) 100%);
        }

        .face-tag {
          position: absolute;
          bottom: 10px; left: 12px;
          font-family: 'Share Tech Mono', monospace;
          font-size: 9px;
          letter-spacing: 0.15em;
          color: #00ffe0;
          opacity: 0.75;
        }

        .btn {
          width: 100%;
          padding: 14px;
          background: transparent;
          border: 1px solid #00ffe0;
          color: #00ffe0;
          font-family: 'Share Tech Mono', monospace;
          font-size: 12px;
          letter-spacing: 0.25em;
          cursor: pointer;
          position: relative;
          overflow: hidden;
          transition: color 0.25s;
        }

        .btn::before {
          content: '';
          position: absolute;
          inset: 0;
          background: #00ffe0;
          transform: translateX(-101%);
          transition: transform 0.25s ease;
        }

        .btn:hover::before, .btn.loading::before {
          transform: translateX(0);
        }

        .btn:hover, .btn.loading {
          color: #03080f;
        }

        .btn span { position: relative; z-index: 1; }

        .btn:disabled { cursor: not-allowed; opacity: 0.8; }

        .btn.loading {
          animation: pulse-ring 1.5s infinite;
        }

        .status-bar {
          margin-top: 14px;
          font-family: 'Share Tech Mono', monospace;
          font-size: 10px;
          letter-spacing: 0.18em;
          text-align: center;
          min-height: 16px;
          animation: fadeIn 0.2s ease;
        }

        .status-bar.scanning { color: #00ffe0; }
        .status-bar.done { color: #00ff88; }
        .status-bar.error { color: #ff4466; }

        .divider {
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(0,255,224,0.2), transparent);
          margin: 24px 0;
        }
      `}</style>

      <div className="register-wrap">
        <div className="bg-glow" />
        <GridOverlay />

        <div className="card">
          <ScanLine />
          <CornerBracket pos="tl" />
          <CornerBracket pos="tr" />
          <CornerBracket pos="bl" />
          <CornerBracket pos="br" />

          <div className="eyebrow">FACEFIT — BIOMETRIC ENROLLMENT</div>
          <div className="title">Register<br /><span>Identity</span></div>

          <label className="field-label">SUBJECT NAME</label>
          <input
            className="field-input"
            type="text"
            placeholder="ENTER FULL NAME"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <label className="field-label">FACIAL IMAGE CAPTURE</label>

          {!preview ? (
            <div className="upload-zone">
              <input
                ref={inputRef}
                type="file"
                accept="image/*"
                onChange={(e) => handleImage(e.target.files[0])}
              />
              <div className="upload-icon">◈</div>
              <div className="upload-hint">DROP PHOTO OR CLICK TO SELECT</div>
            </div>
          ) : (
            <div
              className="preview-wrap"
              onClick={() => inputRef.current?.click()}
              style={{ cursor: "pointer" }}
              title="Click to change photo"
            >
              <input
                ref={inputRef}
                type="file"
                accept="image/*"
                onChange={(e) => handleImage(e.target.files[0])}
                style={{ display: "none" }}
              />
              <img className="preview-img" src={preview} alt="preview" />
              <div className="preview-overlay" />
              {phase === "scanning" && <ScanLine />}
              <CornerBracket pos="tl" />
              <CornerBracket pos="tr" />
              <CornerBracket pos="bl" />
              <CornerBracket pos="br" />
              <div className="face-tag">[ FACE DETECTED — CLICK TO CHANGE ]</div>
            </div>
          )}

          <div className="divider" />

          <button
            className={`btn ${loading ? "loading" : ""}`}
            onClick={registerUser}
            disabled={loading}
          >
            <span>{btnLabel}</span>
          </button>

          {statusMsg && (
            <div className={`status-bar ${phase}`}>{statusMsg}</div>
          )}
        </div>
      </div>
    </>
  );
} 