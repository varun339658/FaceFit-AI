/**
 * SkinProgress.jsx — FaceFit Skincare Progress Tracker (FULLY UPDATED)
 * ======================================================================
 * NEW in this version:
 *   1. SkinConditionExplainer integrated — shows AI condition breakdowns after scan
 *   2. skin_tone passed to /skin/scan so explainer gets correct context
 *   3. Explanations shown in scan result + each history row (collapsed by default)
 */

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { getProfile } from "./Register";
import SkinConditionExplainer from "./SkinConditionExplainer";

const API = "http://127.0.0.1:5000";

const S = {
  wrap:       { fontFamily: "'DM Sans', sans-serif", maxWidth: 680, margin: "0 auto", padding: "32px 20px 48px" },
  headerRow:  { display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 32, gap: 16, flexWrap: "wrap" },
  heading:    { fontFamily: "'Cormorant Garamond', serif", fontWeight: 300, fontSize: 38, lineHeight: 1.1, color: "#1a1208", margin: 0 },
  headingEm:  { fontStyle: "italic", color: "#c8a96e" },
  subtext:    { fontSize: 12.5, color: "#8a7a6a", marginTop: 8, lineHeight: 1.65, maxWidth: 380 },
  weekBadge:  { display: "inline-flex", alignItems: "center", gap: 7, padding: "6px 16px", background: "linear-gradient(135deg,rgba(200,169,110,.12),rgba(200,169,110,.06))", border: "1px solid rgba(200,169,110,.35)", borderRadius: 24, fontSize: 11, fontWeight: 600, color: "#b8842a", letterSpacing: ".1em", textTransform: "uppercase", flexShrink: 0 },
  weekDot:    { width: 6, height: 6, borderRadius: "50%", background: "#c8a96e", boxShadow: "0 0 6px rgba(200,169,110,.6)" },
  card:       { background: "#fff", border: "1px solid #ece6dc", borderRadius: 16, padding: "24px", marginBottom: 18, boxShadow: "0 2px 20px rgba(26,18,8,.04)" },
  cardLabel:  { fontSize: 9, fontWeight: 700, letterSpacing: ".28em", textTransform: "uppercase", color: "#b8a898", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 },
  cardLabelDot: { width: 14, height: 1, background: "#d8cec0", display: "inline-block" },
  dropZone:   { border: "1.5px dashed #d8cec0", borderRadius: 12, padding: "40px 20px", textAlign: "center", cursor: "pointer", background: "#fdf9f5", transition: "all .22s ease" },
  dropIcon:   { width: 48, height: 48, borderRadius: "50%", background: "linear-gradient(135deg,rgba(200,169,110,.15),rgba(200,169,110,.06))", border: "1px solid rgba(200,169,110,.3)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 14px", fontSize: 22, color: "#c8a96e" },
  dropText:   { fontSize: 13, color: "#6a5a4a", fontWeight: 500, marginBottom: 5 },
  dropHint:   { fontSize: 11, color: "#b8a898" },
  previewWrap:{ position: "relative", borderRadius: 12, overflow: "hidden", border: "1px solid #ece6dc" },
  previewImg: { width: "100%", height: 220, objectFit: "cover", display: "block" },
  previewClose:{ position: "absolute", top: 10, right: 10, background: "rgba(26,18,8,.6)", border: "none", color: "#fff", borderRadius: "50%", width: 30, height: 30, cursor: "pointer", fontSize: 14, display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(4px)" },
  btnScan:    { marginTop: 16, width: "100%", padding: "14px", background: "#1a1208", border: "none", color: "#c8a96e", borderRadius: 10, cursor: "pointer", fontSize: 10.5, fontWeight: 700, letterSpacing: ".22em", textTransform: "uppercase", fontFamily: "'DM Sans',sans-serif", display: "flex", alignItems: "center", justifyContent: "center", gap: 10, transition: "all .2s" },
  badgesRow:  { display: "flex", gap: 10, marginTop: 18 },
  badge:      (isClear) => ({ flex: 1, borderRadius: 10, padding: "14px 10px", textAlign: "center", border: `1px solid ${isClear ? "rgba(45,122,79,.25)" : "#ece6dc"}`, background: isClear ? "rgba(45,122,79,.05)" : "#faf8f5" }),
  badgeNum:   (isClear) => ({ fontSize: 24, fontWeight: 300, color: isClear ? "#2d7a4f" : "#1a1208", lineHeight: 1, fontFamily: "'Cormorant Garamond',serif" }),
  badgeLabel: { fontSize: 9.5, color: "#8a7a6a", fontWeight: 600, marginTop: 5, letterSpacing: ".08em", textTransform: "uppercase" },
  trendCard:  { background: "linear-gradient(135deg,rgba(200,169,110,.07),rgba(200,169,110,.03))", border: "1px solid rgba(200,169,110,.25)", borderRadius: 12, padding: "16px 20px", marginBottom: 18, display: "flex", gap: 14, alignItems: "flex-start" },
  trendIcon:  { width: 34, height: 34, borderRadius: "50%", background: "rgba(200,169,110,.15)", border: "1px solid rgba(200,169,110,.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 },
  trendText:  { fontSize: 13, color: "#2c1f0f", lineHeight: 1.7, flex: 1 },
  chartTitle: { fontSize: 9, fontWeight: 700, letterSpacing: ".28em", textTransform: "uppercase", color: "#b8a898", marginBottom: 20, display: "flex", alignItems: "center", gap: 8 },
  chartRow:   { marginBottom: 20 },
  chartRowMeta: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  chartRowLabel:{ fontSize: 11, color: "#6a5a4a", fontWeight: 600, display: "flex", alignItems: "center", gap: 7 },
  chartRowDelta:(isDown) => ({ fontSize: 10, color: isDown ? "#2d7a4f" : "#c0392b", fontWeight: 600, background: isDown ? "rgba(45,122,79,.08)" : "rgba(192,57,43,.08)", padding: "2px 9px", borderRadius: 10 }),
  barsWrap:   { display: "flex", alignItems: "flex-end", gap: 5, height: 56 },
  barCol:     { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 3 },
  barVal:     { fontSize: 9.5, color: "#b8a898", fontWeight: 500 },
  barEl:      (h, color, isEmpty) => ({ width: "100%", borderRadius: "3px 3px 0 0", height: `${h}px`, background: isEmpty ? "#f0ebe4" : color, transition: "height .5s cubic-bezier(.34,1.56,.64,1)" }),
  barWk:      { fontSize: 9, color: "#c4b4a4", textAlign: "center", marginTop: 4 },
  legendDot:  (color) => ({ width: 8, height: 8, borderRadius: "50%", background: color, display: "inline-block", flexShrink: 0 }),
  sectionLabel:{ fontSize: 9, fontWeight: 700, letterSpacing: ".28em", textTransform: "uppercase", color: "#b8a898", marginBottom: 12, display: "flex", alignItems: "center", gap: 8 },
  historyList: { display: "flex", flexDirection: "column", gap: 10 },
  scanRow:    { background: "#fff", border: "1px solid #ece6dc", borderRadius: 12, padding: "16px", display: "flex", gap: 14, alignItems: "flex-start", transition: "box-shadow .2s,transform .2s" },
  scanThumb:  { width: 58, height: 58, objectFit: "cover", borderRadius: 10, flexShrink: 0, border: "1px solid #ece6dc" },
  scanThumbPlaceholder: { width: 58, height: 58, borderRadius: 10, background: "linear-gradient(135deg,#f5f0e8,#ece6dc)", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, color: "#d8cec0" },
  scanInfo:   { flex: 1, minWidth: 0 },
  scanTop:    { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 },
  scanWeek:   { fontSize: 13.5, fontWeight: 600, color: "#1a1208" },
  deltaPill:  (dir) => ({ fontSize: 10, padding: "3px 10px", borderRadius: 20, fontWeight: 600, background: dir==="down"?"rgba(45,122,79,.1)":dir==="up"?"rgba(192,57,43,.08)":"rgba(184,168,152,.12)", color: dir==="down"?"#2d7a4f":dir==="up"?"#c0392b":"#8a7a6a", border: `1px solid ${dir==="down"?"rgba(45,122,79,.2)":dir==="up"?"rgba(192,57,43,.15)":"rgba(184,168,152,.2)"}`, display: "flex", alignItems: "center", gap: 4 }),
  scanCountsRow:{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 2 },
  scanCount:  { fontSize: 11, color: "#8a7a6a", display: "flex", alignItems: "center", gap: 4 },
  countDot:   (color) => ({ width: 6, height: 6, borderRadius: "50%", background: color, display: "inline-block", flexShrink: 0 }),
  scanDate:   { fontSize: 10, color: "#c4b4a4", marginTop: 4 },
  scanNote:   { fontSize: 11, color: "#7a6a5a", marginTop: 5, fontStyle: "italic", padding: "4px 8px", background: "rgba(200,169,110,.06)", borderRadius: 6 },
  scanActions:{ display: "flex", gap: 6, flexShrink: 0, flexDirection: "column" },
  btnDelete:  { padding: "5px 10px", border: "1px solid rgba(192,57,43,.3)", background: "rgba(192,57,43,.06)", borderRadius: 6, color: "#c0392b", cursor: "pointer", fontSize: 11, fontFamily: "inherit", fontWeight: 600, whiteSpace: "nowrap" },
  btnEdit:    { padding: "5px 10px", border: "1px solid rgba(200,169,110,.35)", background: "rgba(200,169,110,.06)", borderRadius: 6, color: "#8a5820", cursor: "pointer", fontSize: 11, fontFamily: "inherit", fontWeight: 600, whiteSpace: "nowrap" },
  empty:      { textAlign: "center", padding: "40px 24px", color: "#b8a898", border: "1.5px dashed #e0d6c8", borderRadius: 14, fontSize: 13, lineHeight: 1.75, background: "#fdf9f5" },
  successBanner:{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", background: "rgba(45,122,79,.07)", border: "1px solid rgba(45,122,79,.2)", borderRadius: 8, fontSize: 12.5, color: "#2d7a4f", fontWeight: 500, marginBottom: 14 },
  errorText:  { marginTop: 10, fontSize: 12, color: "#c0392b", padding: "8px 12px", background: "rgba(192,57,43,.06)", border: "1px solid rgba(192,57,43,.15)", borderRadius: 7 },
  loading:    { textAlign: "center", padding: "28px", color: "#8a7a6a", fontSize: 13, display: "flex", alignItems: "center", justifyContent: "center", gap: 10 },
  modalOverlay:{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 999, padding: 16 },
  modalBox:   { background: "#fff", borderRadius: 12, padding: "24px", width: "100%", maxWidth: 380, boxShadow: "0 8px 40px rgba(0,0,0,.18)" },
  modalTitle: { fontSize: 15, fontWeight: 600, color: "#1a1208", marginBottom: 14 },
  modalInput: { width: "100%", padding: "10px 12px", border: "1px solid #e0d6c8", borderRadius: 6, fontFamily: "inherit", fontSize: 13, color: "#1a1208", outline: "none", resize: "vertical", minHeight: 80, boxSizing: "border-box" },
  modalBtns:  { display: "flex", gap: 10, marginTop: 14 },
  modalBtnCancel:{ flex: 1, padding: 11, background: "#f0e8d8", border: "none", borderRadius: 6, color: "#5a4a3a", cursor: "pointer", fontSize: 13, fontFamily: "inherit" },
  modalBtnSave:  { flex: 1, padding: 11, background: "#1a1208", border: "none", borderRadius: 6, color: "#c8a96e", cursor: "pointer", fontSize: 13, fontFamily: "inherit", fontWeight: 500 },
};

const CONDITION_COLORS = { acne: "#d96b6b", dark_circles: "#7c6bab", dark_spots: "#c8a96e" };

const Spinner = ({ size = 16, color = "#c8a96e" }) => (
  <span style={{ width: size, height: size, flexShrink: 0, border: "2px solid rgba(200,169,110,.25)", borderTopColor: color, borderRadius: "50%", display: "inline-block", animation: "sp-spin .7s linear infinite" }} />
);

function ChartRow({ label, data, color }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data, 1);
  const first = data[0], last = data[data.length - 1];
  const isDown = last < first;
  const delta  = first - last;
  return (
    <div style={S.chartRow}>
      <div style={S.chartRowMeta}>
        <div style={S.chartRowLabel}><span style={S.legendDot(color)} />{label}</div>
        {delta !== 0 && data.length > 1 && <span style={S.chartRowDelta(isDown)}>{isDown ? "↓" : "↑"} {Math.abs(delta)} {isDown ? "less" : "more"}</span>}
      </div>
      <div style={S.barsWrap}>
        {data.map((val, i) => {
          const h = Math.max((val / max) * 44, val > 0 ? 6 : 2);
          return (
            <div key={i} style={S.barCol}>
              <div style={S.barVal}>{val}</div>
              <div style={S.barEl(h, color, val === 0)} />
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 5 }}>
        {data.map((_, i) => <div key={i} style={S.barCol}><div style={S.barWk}>W{i + 1}</div></div>)}
      </div>
    </div>
  );
}

function NoteModal({ scan, onClose, onSave }) {
  const [note, setNote] = useState(scan.note || "");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  const handleSave = async () => {
    if (!note.trim()) { setErr("Please enter a note."); return; }
    setSaving(true);
    try {
      await axios.patch(`${API}/skin/scan/${scan.scan_id}`, { note: note.trim() });
      onSave(scan.scan_id, note.trim());
      onClose();
    } catch (e) { setErr(e?.response?.data?.error || "Failed to save note."); }
    setSaving(false);
  };
  return (
    <div style={S.modalOverlay} onClick={onClose}>
      <div style={S.modalBox} onClick={e => e.stopPropagation()}>
        <div style={S.modalTitle}>✏️ Add / Edit Note — Week {scan.week_number}</div>
        <div style={{ fontSize: 11.5, color: "#8a7a6a", marginBottom: 10 }}>Note what changed this week.</div>
        <textarea style={S.modalInput} value={note}
          onChange={e => { setNote(e.target.value); setErr(""); }}
          placeholder="e.g. Started salicylic acid cleanser. Drinking more water." autoFocus />
        {err && <div style={{ fontSize: 12, color: "#c0392b", marginTop: 6 }}>{err}</div>}
        <div style={S.modalBtns}>
          <button style={S.modalBtnCancel} onClick={onClose}>Cancel</button>
          <button style={S.modalBtnSave} onClick={handleSave} disabled={saving}>{saving ? "Saving..." : "Save Note"}</button>
        </div>
      </div>
    </div>
  );
}

export default function SkinProgress() {
  const user   = getProfile();
  const userId = user?.name || user?.userId || "";
  const skinTone = user?.skinTone || "medium";

  const [scans,        setScans]        = useState([]);
  const [chartData,    setChartData]    = useState(null);
  const [trendMessage, setTrendMessage] = useState("");
  const [totalWeeks,   setTotalWeeks]   = useState(0);
  const [scanning,     setScanning]     = useState(false);
  const [preview,      setPreview]      = useState(null);
  const [scanFile,     setScanFile]     = useState(null);
  const [scanResult,   setScanResult]   = useState(null);
  const [scanError,    setScanError]    = useState("");
  const [loading,      setLoading]      = useState(false);
  const [faceChecking, setFaceChecking] = useState(false);
  const [editTarget,   setEditTarget]   = useState(null);
  const [deletingId,   setDeletingId]   = useState("");
  const fileRef = useRef();

  useEffect(() => {
    const id = "sp-keyframes";
    if (!document.getElementById(id)) {
      const s = document.createElement("style");
      s.id = id;
      s.textContent = `
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');
        @keyframes sp-spin { to { transform: rotate(360deg); } }
        @keyframes sp-fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
        @keyframes fadeUp { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
        @keyframes blink { 0%,100%{opacity:.3;transform:scale(.9)} 50%{opacity:1;transform:scale(1.1)} }
        .sp-scan-row:hover { box-shadow: 0 4px 18px rgba(26,18,8,.07) !important; transform: translateY(-1px); }
        .sp-btn-scan:hover:not(:disabled) { background: #c8a96e !important; color: #1a1208 !important; }
        .sp-btn-scan:disabled { opacity:.5; cursor:not-allowed; }
        .sp-card { animation: sp-fadeUp .3s ease both; }
      `;
      document.head.appendChild(s);
    }
  }, []);

  useEffect(() => { if (userId) loadProgress(); }, [userId]);

  async function loadProgress() {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/skin/progress/${userId}`);
      setScans(res.data.scans || []);
      setChartData(res.data.chart_data || null);
      setTrendMessage(res.data.trend_message || "");
      setTotalWeeks(res.data.total_weeks || 0);
    } catch (e) { console.error("Progress load:", e); }
    setLoading(false);
  }

  async function handleFile(file) {
    if (!file) return;
    setFaceChecking(true);
    setScanError("");
    try {
      const fd = new FormData();
      fd.append("image", file);
      const res = await axios.post(`${API}/detect-face`, fd);
      if (!res.data.face_detected) {
        setScanError("⚠️ No face detected. Please upload a clear selfie with your face visible.");
        setFaceChecking(false);
        return;
      }
    } catch (e) {
      console.warn("Face check failed, proceeding:", e);
    }
    setFaceChecking(false);
    setScanFile(file);
    setPreview(URL.createObjectURL(file));
    setScanResult(null);
    setScanError("");
  }

  async function submitScan() {
    if (!scanFile || !userId) return;
    setScanning(true);
    setScanError("");
    setScanResult(null);
    const fd = new FormData();
    fd.append("user_id",   userId);
    fd.append("skin_tone", skinTone);  // NEW: pass skin_tone for explainer
    fd.append("image",     scanFile);
    try {
      const res = await axios.post(`${API}/skin/scan`, fd);
      setScanResult(res.data);
      setScanFile(null);
      setPreview(null);
      await loadProgress();
    } catch (e) {
      setScanError(e?.response?.data?.error || "Scan failed. Please try again.");
    }
    setScanning(false);
  }

  async function deleteScan(scanId) {
    if (!window.confirm("Delete this scan? Week numbers will be renumbered.")) return;
    setDeletingId(scanId);
    try {
      await axios.delete(`${API}/skin/scan/${scanId}/user/${userId}`);
      await loadProgress();
    } catch (e) { alert(e?.response?.data?.error || "Delete failed."); }
    setDeletingId("");
  }

  function handleNoteSaved(scanId, note) {
    setScans(prev => prev.map(s => s.scan_id === scanId ? { ...s, note } : s));
  }

  function getDeltaDir(label) {
    if (!label) return "same";
    if (label.includes("↓")) return "down";
    if (label.includes("↑")) return "up";
    return "same";
  }

  function fmtDate(dateStr) {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  }

  const showChart = chartData && totalWeeks >= 2;
  const nextWeek  = totalWeeks + (scanResult ? 0 : 1);

  return (
    <div style={S.wrap}>
      {/* Header */}
      <div style={S.headerRow}>
        <div>
          <h2 style={S.heading}>Skin <em style={S.headingEm}>Progress</em></h2>
          <p style={S.subtext}>Upload a selfie each week. AI runs the same scan to reveal how your skin heals over time.</p>
        </div>
        <div style={S.weekBadge}><span style={S.weekDot} /> Week {nextWeek} active</div>
      </div>

      {/* Upload card */}
      <div style={S.card} className="sp-card">
        <div style={S.cardLabel}><span style={S.cardLabelDot} />New weekly scan<span style={S.cardLabelDot} /></div>

        {scanResult && (
          <div style={S.successBanner}>
            <span>✓</span> {scanResult.message || "Scan saved successfully!"}
          </div>
        )}

        {faceChecking && (
          <div style={{ ...S.loading, marginBottom: 12, padding: "14px 0" }}>
            <Spinner size={14} /> Checking for face in image...
          </div>
        )}

        {!preview && !faceChecking ? (
          <div style={S.dropZone} onClick={() => fileRef.current?.click()}
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); handleFile(e.dataTransfer.files[0]); }}>
            <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
              onChange={e => handleFile(e.target.files[0])} />
            <div style={S.dropIcon}>+</div>
            <div style={S.dropText}>Drop your selfie here or click to browse</div>
            <div style={S.dropHint}>JPG, PNG, or WebP — face front-on in good lighting</div>
            <div style={{ fontSize: 10.5, color: "#c8a96e", marginTop: 8, fontWeight: 500 }}>
              ✦ Face must be clearly visible
            </div>
          </div>
        ) : !faceChecking && (
          <div style={S.previewWrap}>
            <img src={preview} alt="Preview" style={S.previewImg} />
            <button style={S.previewClose} onClick={() => { setPreview(null); setScanFile(null); }}>✕</button>
          </div>
        )}

        {/* Scan result badges */}
        {scanResult && (
          <div style={S.badgesRow}>
            {[
              { label: "Acne",         count: scanResult.summary?.acne_count || 0,        color: CONDITION_COLORS.acne },
              { label: "Dark Circles", count: scanResult.summary?.dark_circle_count || 0, color: CONDITION_COLORS.dark_circles },
              { label: "Dark Spots",   count: scanResult.summary?.dark_spot_count || 0,   color: CONDITION_COLORS.dark_spots },
            ].map(({ label, count, color }) => {
              const isClear = count === 0;
              return (
                <div key={label} style={S.badge(isClear)}>
                  <div style={S.badgeNum(isClear)}>{isClear ? "✓" : count}</div>
                  <div style={S.badgeLabel}>{label}</div>
                  {isClear && <div style={{ fontSize: 9, color: "#2d7a4f", marginTop: 3, fontWeight: 500 }}>All clear</div>}
                  {!isClear && (
                    <div style={{ width: "100%", height: 3, background: "#f0ebe4", borderRadius: 2, marginTop: 7, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${Math.min(count * 10, 100)}%`, background: color, borderRadius: 2 }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* ── NEW: Skin Condition Explainer after scan result ────────────── */}
        {scanResult?.detections?.length > 0 && (
          <SkinConditionExplainer
            conditions={[...new Set(scanResult.detections)]}
            skinTone={skinTone}
            severityCounts={{
              acne_count:        scanResult.summary?.acne_count || 0,
              dark_circle_count: scanResult.summary?.dark_circle_count || 0,
              dark_spot_count:   scanResult.summary?.dark_spot_count || 0,
            }}
          />
        )}

        {scanError && <div style={S.errorText}>{scanError}</div>}

        {preview && !scanResult && (
          <button className="sp-btn-scan" style={S.btnScan} onClick={submitScan} disabled={scanning}>
            {scanning ? <><Spinner size={14} color="#c8a96e" /> Scanning your skin...</> : <>Run AI Skin Scan →</>}
          </button>
        )}
      </div>

      {/* Trend message */}
      {trendMessage && totalWeeks > 0 && (
        <div style={S.trendCard}>
          <div style={S.trendIcon}>✦</div>
          <div style={S.trendText}>{trendMessage}</div>
        </div>
      )}

      {/* Chart */}
      {showChart && (
        <div style={S.card} className="sp-card">
          <div style={S.chartTitle}><span style={S.cardLabelDot} />Progress over {totalWeeks} week{totalWeeks > 1 ? "s" : ""}<span style={S.cardLabelDot} /></div>
          <ChartRow label="Acne"         data={chartData.acne}         color={CONDITION_COLORS.acne} />
          <ChartRow label="Dark Circles" data={chartData.dark_circles} color={CONDITION_COLORS.dark_circles} />
          <ChartRow label="Dark Spots"   data={chartData.dark_spots}   color={CONDITION_COLORS.dark_spots} />
        </div>
      )}

      {/* History */}
      {loading ? (
        <div style={S.loading}><Spinner /> Loading your scan history...</div>
      ) : scans.length === 0 ? (
        <div style={S.empty} className="sp-card">
          <div style={{ fontSize: 36, marginBottom: 12, opacity: .5 }}>✦</div>
          No scans yet.<br />
          <span style={{ color: "#c8a96e", fontWeight: 500 }}>Upload your first selfie</span> to begin tracking.
        </div>
      ) : (
        <div>
          <div style={S.sectionLabel}><span style={S.cardLabelDot} />Scan history · {scans.length} session{scans.length > 1 ? "s" : ""}</div>
          <div style={S.historyList}>
            {[...scans].reverse().map((scan) => {
              const dir  = getDeltaDir(scan.delta_label);
              const acne = scan.summary?.acne_count || 0;
              const dc   = scan.summary?.dark_circle_count || 0;
              const ds   = scan.summary?.dark_spot_count || 0;
              const photoSrc = scan.photo_url
                ? (scan.photo_url.startsWith("http") ? scan.photo_url : `${API}${scan.photo_url}`)
                : null;
              const isDeleting = deletingId === scan.scan_id;

              return (
                <div key={scan.scan_id} className="sp-scan-row" style={{ ...S.scanRow, opacity: isDeleting ? .5 : 1, flexDirection: "column" }}>
                  <div style={{ display: "flex", gap: 14, alignItems: "flex-start", width: "100%" }}>
                    {photoSrc
                      ? <img src={photoSrc} alt={`Week ${scan.week_number}`} style={S.scanThumb} onError={e => { e.target.style.display = "none"; }} />
                      : <div style={S.scanThumbPlaceholder}>✦</div>
                    }
                    <div style={S.scanInfo}>
                      <div style={S.scanTop}>
                        <span style={S.scanWeek}>Week {scan.week_number}</span>
                        {scan.delta_label && <span style={S.deltaPill(dir)}>{scan.delta_label}</span>}
                      </div>
                      <div style={S.scanCountsRow}>
                        <span style={S.scanCount}><span style={S.countDot(CONDITION_COLORS.acne)} />Acne: {acne}</span>
                        <span style={S.scanCount}><span style={S.countDot(CONDITION_COLORS.dark_circles)} />Circles: {dc}</span>
                        <span style={S.scanCount}><span style={S.countDot(CONDITION_COLORS.dark_spots)} />Spots: {ds}</span>
                      </div>
                      <div style={S.scanDate}>{fmtDate(scan.scan_date)}</div>
                      {scan.note && <div style={S.scanNote}>"{scan.note}"</div>}
                    </div>
                    <div style={S.scanActions}>
                      <button style={S.btnEdit} onClick={() => setEditTarget(scan)} title="Add or edit note">✏️ Note</button>
                      <button style={S.btnDelete} onClick={() => deleteScan(scan.scan_id)} disabled={isDeleting} title="Delete this scan">{isDeleting ? "..." : "🗑 Delete"}</button>
                    </div>
                  </div>

                  {/* ── NEW: Condition Explainer per history row ─────────────── */}
                  {scan.detections?.length > 0 && (
                    <div style={{ width: "100%", marginTop: 4 }}>
                      <SkinConditionExplainer
                        conditions={[...new Set(scan.detections)].slice(0, 3)}
                        skinTone={skinTone}
                        severityCounts={scan.summary || {}}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {editTarget && (
        <NoteModal scan={editTarget} onClose={() => setEditTarget(null)} onSave={handleNoteSaved} />
      )}
    </div>
  );
}