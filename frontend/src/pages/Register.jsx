/**
 * Register.jsx — FaceFit Registration (FIXED)
 * =============================================
 * FIXES:
 *  1. Face validation on image select — calls /detect-face BEFORE registration
 *     Rejects non-face images immediately with a clear error message
 *  2. Shows face check indicator while validating
 *  3. Backend also validates (422 if no face) as double safety
 *  4. JWT + localStorage session persistence (unchanged from original)
 */

import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = "http://127.0.0.1:5000";

// ─── Auth helpers ─────────────────────────────────────────────────────────────
export const saveToken   = (token)   => localStorage.setItem("ff_token", token);
export const getToken    = ()        => localStorage.getItem("ff_token");
export const removeToken = ()        => localStorage.removeItem("ff_token");
export const saveProfile = (profile) => localStorage.setItem("faceAnalysis", JSON.stringify(profile));
export const getProfile  = ()        => {
  try { return JSON.parse(localStorage.getItem("faceAnalysis") || "{}"); }
  catch { return {}; }
};

export async function restoreSession() {
  const token = getToken();
  if (!token) return null;
  const cached = getProfile();
  if (cached?.name) return cached;
  try {
    const res = await axios.get(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    saveProfile(res.data);
    return res.data;
  } catch (err) {
    if (err?.response?.status === 401 || err?.response?.status === 422) {
      removeToken();
      localStorage.removeItem("faceAnalysis");
    }
    return null;
  }
}

export async function logout() {
  const token = getToken();
  if (token) {
    try {
      await axios.post(`${API}/auth/logout`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (_) {}
  }
  removeToken();
  localStorage.removeItem("faceAnalysis");
}

// ─────────────────────────────────────────────────────────────────────────────

export default function Register({ onRegistered }) {
  const navigate = useNavigate();
  const [name,         setName]         = useState("");
  const [email,        setEmail]        = useState("");
  const [phone,        setPhone]        = useState("");
  const [gender,       setGender]       = useState("male");
  const [image,        setImage]        = useState(null);
  const [preview,      setPreview]      = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [faceChecking, setFaceChecking] = useState(false);
  const [faceValid,    setFaceValid]    = useState(false);
  const [phase,        setPhase]        = useState("idle"); // idle | face_checking | face_ok | face_fail | scanning | done | error
  const [errMsg,       setErrMsg]       = useState("");
  const [progress,     setProgress]     = useState(0);
  const inputRef    = useRef();
  const progressRef = useRef(null);

  // Skip registration if already logged in
  useEffect(() => {
    const token = getToken();
    const profile = getProfile();
    if (token && profile?.name) navigate("/chat");
  }, [navigate]);

  useEffect(() => {
    if (loading) {
      setProgress(0);
      progressRef.current = setInterval(() => {
        setProgress(p => Math.min(p + Math.random() * 8, 85));
      }, 200);
    } else {
      clearInterval(progressRef.current);
      if (phase === "done") setProgress(100);
    }
    return () => clearInterval(progressRef.current);
  }, [loading, phase]);

  // ── Face validation on image select ──────────────────────────────────────────
  const handleImage = async (file) => {
    if (!file) return;
    setImage(file);
    setPreview(URL.createObjectURL(file));
    setFaceValid(false);
    setPhase("face_checking");
    setErrMsg("");
    setFaceChecking(true);

    try {
      const fd = new FormData();
      fd.append("image", file);
      const res = await axios.post(`${API}/detect-face`, fd);

      if (res.data.face_detected) {
        setFaceValid(true);
        setPhase("face_ok");
        setErrMsg("");
      } else {
        setFaceValid(false);
        setPhase("face_fail");
        setImage(null);
        setPreview(null);
        setErrMsg("No face detected in this photo. Please upload a clear selfie with your face visible and well-lit.");
      }
    } catch (e) {
      // API error — let backend validate, don't block
      console.warn("Face pre-check failed, will validate on submit:", e);
      setFaceValid(true); // optimistic — backend will catch it
      setPhase("face_ok");
    }

    setFaceChecking(false);
  };

  const validateEmail = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
  const validatePhone = (p) => {
    const cleaned = p.replace(/[\s\-()]/g, "");
    return /^(\+91)?[6-9]\d{9}$/.test(cleaned);
  };

  const registerUser = async () => {
    // Validation
    if (!name.trim())                           { setErrMsg("Please enter your name");            setPhase("error"); return; }
    if (!email.trim() || !validateEmail(email)) { setErrMsg("Please enter a valid email");        setPhase("error"); return; }
    if (!phone.trim() || !validatePhone(phone)) { setErrMsg("Please enter a valid phone number"); setPhase("error"); return; }
    if (!image)                                 { setErrMsg("Please upload your photo");          setPhase("error"); return; }
    if (!faceValid) {
      setErrMsg("Please upload a clear selfie with your face visible.");
      setPhase("error");
      return;
    }

    const fd = new FormData();
    fd.append("name",   name.trim());
    fd.append("email",  email.trim());
    fd.append("phone",  phone.trim());
    fd.append("gender", gender);
    fd.append("image",  image);

    try {
      setLoading(true);
      setPhase("scanning");
      setErrMsg("");

      const res      = await axios.post(`${API}/register`, fd);
      const analysis = res.data;

      if (analysis.access_token) saveToken(analysis.access_token);
      const { access_token, ...profile } = analysis;
      saveProfile(profile);

      if (onRegistered) onRegistered(profile);

      setPhase("done");
      setTimeout(() => navigate("/chat"), 1400);
    } catch (err) {
      console.error(err);
      const msg = err?.response?.data?.error || "Something went wrong. Please try again.";
      // If backend says no face, clear the photo
      if (err?.response?.status === 422) {
        setImage(null);
        setPreview(null);
        setFaceValid(false);
      }
      setErrMsg(msg);
      setPhase("error");
    }
    setLoading(false);
  };

  const phaseColor = {
    idle: "#c8a96e", face_checking: "#c8a96e", face_ok: "#7ec8a0",
    face_fail: "#e07070", scanning: "#c8a96e", done: "#7ec8a0", error: "#e07070",
  };
  const phaseText = {
    face_checking: "Checking for face…",
    face_ok:       "✓ Face detected — ready to scan",
    face_fail:     errMsg,
    scanning:      "Analyzing your face…",
    done:          "✓ Analysis complete — redirecting",
    error:         errMsg,
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Sans:wght@300;400;500&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes fadeUp   { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes shimmer  { 0% { background-position: -200% center; } 100% { background-position: 200% center; } }
        @keyframes spin     { to { transform: rotate(360deg); } }
        @keyframes scanLine { 0% { top: 0; opacity: 1; } 90% { opacity: 0.6; } 100% { top: 100%; opacity: 0; } }
        @keyframes pulse    { 0%,100%{opacity:1} 50%{opacity:.5} }

        .reg-root { min-height: 100vh; display: flex; background: #0e0c0a; font-family: 'DM Sans', sans-serif; overflow: hidden; }
        .reg-left { width: 42%; position: relative; background: linear-gradient(160deg, #1a1510 0%, #0e0c0a 60%); display: flex; flex-direction: column; justify-content: space-between; padding: 56px 52px; overflow: hidden; }
        .reg-left::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse 60% 50% at 30% 70%, rgba(200,169,110,0.12) 0%, transparent 60%), radial-gradient(ellipse 40% 60% at 80% 20%, rgba(200,169,110,0.06) 0%, transparent 50%); }
        .gold-line { width: 48px; height: 1px; background: linear-gradient(90deg, #c8a96e, transparent); margin-bottom: 28px; }
        .brand-eyebrow { font-size: 10px; font-weight: 500; letter-spacing: 0.35em; color: #c8a96e; text-transform: uppercase; margin-bottom: 20px; }
        .brand-title { font-family: 'Cormorant Garamond', serif; font-size: 56px; font-weight: 300; line-height: 1.1; color: #f5ede0; margin-bottom: 24px; }
        .brand-title em { font-style: italic; color: #c8a96e; }
        .brand-desc { font-size: 13.5px; font-weight: 300; line-height: 1.8; color: rgba(245,237,224,0.5); max-width: 300px; }
        .features { display: flex; flex-direction: column; gap: 14px; position: relative; z-index: 1; }
        .feat { display: flex; align-items: center; gap: 14px; padding: 14px 18px; border: 1px solid rgba(200,169,110,0.12); background: rgba(200,169,110,0.03); }
        .feat-icon { width: 36px; height: 36px; border: 1px solid rgba(200,169,110,0.25); display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
        .feat-label { font-size: 12px; font-weight: 500; color: rgba(245,237,224,0.7); }
        .feat-sub   { font-size: 10.5px; color: rgba(200,169,110,0.5); font-weight: 300; margin-top: 2px; }
        .reg-right { flex: 1; display: flex; align-items: center; justify-content: center; padding: 40px 36px; background: #f8f4ef; position: relative; overflow-y: auto; }
        .reg-right::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse 50% 40% at 80% 80%, rgba(200,169,110,0.07) 0%, transparent 60%); }
        .form-card { width: 100%; max-width: 440px; animation: fadeUp 0.6s ease both; position: relative; z-index: 1; }
        .form-heading { font-family: 'Cormorant Garamond', serif; font-size: 34px; font-weight: 300; color: #1a1208; margin-bottom: 6px; line-height: 1.2; }
        .form-heading em { font-style: italic; color: #c8a96e; }
        .form-sub { font-size: 13px; color: #8a7a6a; font-weight: 300; margin-bottom: 28px; line-height: 1.6; }
        .field { margin-bottom: 18px; }
        .field-label { display: block; font-size: 10px; font-weight: 500; letter-spacing: 0.2em; color: #8a7a6a; text-transform: uppercase; margin-bottom: 7px; }
        .field-input { width: 100%; padding: 12px 14px; border: 1px solid #e0d6c8; background: #fff; font-family: 'DM Sans', sans-serif; font-size: 14px; color: #1a1208; outline: none; border-radius: 2px; transition: border-color 0.2s; }
        .field-input:focus { border-color: #c8a96e; }
        .field-hint { font-size: 10.5px; color: #b8a898; margin-top: 4px; font-weight: 300; }
        .row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; }
        .gender-toggle { display: flex; border: 1px solid #e0d6c8; border-radius: 2px; overflow: hidden; }
        .gender-btn { flex: 1; padding: 11px 8px; border: none; background: #fff; font-family: 'DM Sans', sans-serif; font-size: 13px; color: #8a7a6a; cursor: pointer; transition: all 0.2s; }
        .gender-btn.active { background: #1a1208; color: #c8a96e; }
        .upload-zone { border: 1.5px dashed #d0c4b4; background: #fff; padding: 28px 16px; text-align: center; cursor: pointer; transition: border-color 0.2s; border-radius: 2px; position: relative; }
        .upload-zone:hover { border-color: #c8a96e; }
        .upload-zone.face-ok  { border-color: #2d7a4f; border-style: solid; background: rgba(45,122,79,.03); }
        .upload-zone.face-bad { border-color: #c0392b; border-style: solid; background: rgba(192,57,43,.03); }
        .upload-icon { font-size: 24px; color: #c8a96e; margin-bottom: 8px; }
        .upload-hint { font-size: 13px; color: #8a7a6a; }
        .upload-hint span { color: #c8a96e; text-decoration: underline; }
        .face-check-banner { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 4px; font-size: 12px; font-weight: 500; margin-top: 8px; }
        .face-check-banner.ok   { background: rgba(45,122,79,.08); border: 1px solid rgba(45,122,79,.2); color: #2d7a4f; }
        .face-check-banner.fail { background: rgba(192,57,43,.08); border: 1px solid rgba(192,57,43,.2); color: #c0392b; }
        .face-check-banner.checking { background: rgba(200,169,110,.08); border: 1px solid rgba(200,169,110,.2); color: #8a5820; }
        .preview-wrap { position: relative; border-radius: 2px; overflow: hidden; cursor: pointer; height: 160px; }
        .preview-img { width: 100%; height: 160px; object-fit: cover; filter: saturate(0.9); }
        .preview-overlay { position: absolute; inset: 0; background: linear-gradient(180deg, transparent 50%, rgba(26,18,8,0.7) 100%); }
        .preview-label { position: absolute; bottom: 10px; left: 14px; font-size: 10px; letter-spacing: 0.15em; color: rgba(245,237,224,0.8); text-transform: uppercase; }
        .preview-badge { position: absolute; top: 10px; right: 10px; padding: 4px 10px; border-radius: 12px; font-size: 10px; font-weight: 700; }
        .preview-badge.ok   { background: rgba(45,122,79,.85); color: #fff; }
        .preview-badge.fail { background: rgba(192,57,43,.85); color: #fff; }
        .preview-badge.checking { background: rgba(26,15,0,.7); color: #c8a96e; }
        .scan-line { position: absolute; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, #c8a96e, transparent); animation: scanLine 2s linear infinite; }
        .progress-wrap { margin-bottom: 12px; height: 2px; background: #e0d6c8; border-radius: 1px; overflow: hidden; }
        .progress-bar  { height: 100%; background: linear-gradient(90deg, #c8a96e, #e0c080, #c8a96e); background-size: 200% 100%; animation: shimmer 1.5s linear infinite; transition: width 0.3s ease; border-radius: 1px; }
        .status-msg { font-size: 11.5px; text-align: center; margin-bottom: 12px; min-height: 18px; font-weight: 400; transition: color 0.3s; }
        .submit-btn { width: 100%; padding: 14px; background: #1a1208; border: none; color: #c8a96e; font-family: 'DM Sans', sans-serif; font-size: 11px; font-weight: 500; letter-spacing: 0.25em; text-transform: uppercase; cursor: pointer; transition: background 0.25s, color 0.25s; border-radius: 2px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .submit-btn:hover:not(:disabled) { background: #c8a96e; color: #1a1208; }
        .submit-btn:disabled { opacity: 0.7; cursor: not-allowed; }
        .spinner { width: 14px; height: 14px; border: 1.5px solid currentColor; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; }
        .face-pulse { width: 10px; height: 10px; border-radius: 50%; background: currentColor; animation: pulse 1s ease infinite; }
        @media (max-width: 768px) { .reg-left { display: none; } .form-card { max-width: 100%; } .row-2 { grid-template-columns: 1fr; } }
      `}</style>

      <div className="reg-root">

        {/* ── Left panel ── */}
        <div className="reg-left">
          <div style={{ position: "relative", zIndex: 1 }}>
            <div className="gold-line" />
            <div className="brand-eyebrow">FaceFit — AI Style Intelligence</div>
            <h1 className="brand-title">Your face.<br />Your <em>style.</em></h1>
            <p className="brand-desc">
              Upload your photo once and let our AI create a personalized skincare routine
              and outfit recommendations — saved permanently.
            </p>
          </div>
          <div className="features" style={{ position: "relative", zIndex: 1 }}>
            {[
              { icon: "◈", label: "Face & Skin Analysis",      sub: "AI-powered biometric scan — done once" },
              { icon: "✦", label: "Skincare Progress Tracker",  sub: "Weekly scans, before/after charts" },
              { icon: "◇", label: "Weather-Aware Outfits",      sub: "Outfits adjusted to your city's weather" },
              { icon: "◉", label: "Price Drop Alerts",           sub: "Save products, get notified on drops" },
            ].map((f, i) => (
              <div className="feat" key={i}>
                <div className="feat-icon">{f.icon}</div>
                <div>
                  <div className="feat-label">{f.label}</div>
                  <div className="feat-sub">{f.sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Right panel ── */}
        <div className="reg-right">
          <div className="form-card">
            <h2 className="form-heading">Create your<br /><em>profile</em></h2>
            <p className="form-sub">A one-time setup. You'll never need to register again.</p>

            <div className="row-2">
              <div className="field" style={{ marginBottom: 0 }}>
                <label className="field-label">Your Name</label>
                <input className="field-input" type="text" placeholder="Full name" value={name}
                  onChange={e => { setName(e.target.value); setPhase("idle"); }} />
              </div>
              <div className="field" style={{ marginBottom: 0 }}>
                <label className="field-label">Gender</label>
                <div className="gender-toggle">
                  {[{ val: "male", label: "♂ Male" }, { val: "female", label: "♀ Female" }].map(g => (
                    <button key={g.val} className={`gender-btn ${gender === g.val ? "active" : ""}`}
                      onClick={() => setGender(g.val)}>{g.label}</button>
                  ))}
                </div>
              </div>
            </div>

            <div className="field">
              <label className="field-label">Email Address</label>
              <input className="field-input" type="email" placeholder="you@example.com"
                value={email} onChange={e => { setEmail(e.target.value); setPhase("idle"); }} autoComplete="email" />
              <div className="field-hint">For outfit reminders &amp; price drop alerts</div>
            </div>

            <div className="field">
              <label className="field-label">Phone Number</label>
              <input className="field-input" type="tel" placeholder="+91 98765 43210"
                value={phone} onChange={e => { setPhone(e.target.value); setPhase("idle"); }} autoComplete="tel" />
              <div className="field-hint">For WhatsApp outfit reminders</div>
            </div>

            <div className="field">
              <label className="field-label">Your Photo</label>

              {/* Face validation hint */}
              <div style={{ fontSize: 10.5, color: "#8a7a6a", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ color: "#c8a96e" }}>✦</span>
                Upload a clear front-facing selfie — AI validates face automatically
              </div>

              {!preview ? (
                <div
                  className={`upload-zone ${phase === "face_ok" ? "face-ok" : phase === "face_fail" ? "face-bad" : ""}`}
                  onClick={() => inputRef.current?.click()}
                >
                  <input ref={inputRef} type="file" accept="image/*" style={{ display: "none" }}
                    onChange={e => handleImage(e.target.files[0])} />
                  <div className="upload-icon">⊕</div>
                  <div className="upload-hint">Drop your photo here or <span>browse</span></div>
                  <div style={{ fontSize: 10.5, color: "#b8a898", marginTop: 8, fontWeight: 300 }}>
                    JPG, PNG or WebP · Face must be clearly visible
                  </div>
                </div>
              ) : (
                <div className="preview-wrap" onClick={() => inputRef.current?.click()}>
                  <input ref={inputRef} type="file" accept="image/*" style={{ display: "none" }}
                    onChange={e => handleImage(e.target.files[0])} />
                  <img className="preview-img" src={preview} alt="preview" />
                  <div className="preview-overlay" />
                  {phase === "scanning" && <div className="scan-line" />}
                  {/* Face detection badge */}
                  {phase === "face_checking" && (
                    <div className="preview-badge checking">
                      <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                        <span className="face-pulse" style={{ width: 7, height: 7 }} /> Checking…
                      </span>
                    </div>
                  )}
                  {phase === "face_ok" && (
                    <div className="preview-badge ok">✓ Face detected</div>
                  )}
                  {phase === "face_fail" && (
                    <div className="preview-badge fail">✕ No face found</div>
                  )}
                  <div className="preview-label">Click to change photo</div>
                </div>
              )}

              {/* Face check status banner */}
              {phase === "face_checking" && (
                <div className="face-check-banner checking">
                  <span className="face-pulse" style={{ width: 8, height: 8 }} />
                  Detecting face in your photo…
                </div>
              )}
              {phase === "face_ok" && !loading && (
                <div className="face-check-banner ok">
                  ✓ Face detected — ready to proceed
                </div>
              )}
              {phase === "face_fail" && (
                <div className="face-check-banner fail">
                  ✕ {errMsg || "No face detected. Please upload a clear selfie."}
                </div>
              )}
            </div>

            {loading && (
              <div className="progress-wrap">
                <div className="progress-bar" style={{ width: `${progress}%` }} />
              </div>
            )}

            <div className="status-msg"
              style={{ color: phaseColor[phase] || "#c8a96e", display: (phaseText[phase] && phase !== "face_ok" && phase !== "face_fail") ? "block" : "none" }}>
              {phaseText[phase]}
            </div>

            {/* Show error for registration errors (not face errors — those show in banner) */}
            {phase === "error" && errMsg && phase !== "face_fail" && (
              <div style={{ fontSize: 12, color: "#c0392b", textAlign: "center", marginBottom: 10, padding: "8px 12px", background: "rgba(192,57,43,.06)", border: "1px solid rgba(192,57,43,.15)", borderRadius: 4 }}>
                {errMsg}
              </div>
            )}

            <button className="submit-btn" onClick={registerUser}
              disabled={loading || faceChecking || phase === "face_fail" || phase === "face_checking"}>
              {loading
                ? <><div className="spinner" /> Analyzing your face...</>
                : faceChecking
                  ? <><div className="spinner" /> Validating photo…</>
                  : "Begin Analysis →"
              }
            </button>

            <div style={{ textAlign: "center", marginTop: 14, fontSize: 11, color: "#b8a898", fontWeight: 300 }}>
              Your data is kept private and only used for personalized recommendations.
            </div>
          </div>
        </div>
      </div>
    </>
  );
}