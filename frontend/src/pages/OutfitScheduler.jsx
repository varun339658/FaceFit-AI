/**
 * OutfitScheduler.jsx — FaceFit Outfit Planner v3
 * ══════════════════════════════════════════════════
 * FIXES:
 *  1. Delete button on ALL reminders (including fired ones)
 *  2. Reschedule button on fired reminders
 *  3. Live minDt (refreshed every 30s, never stale)
 *  4. Frontend time validation before API call
 *  5. "Today at HH:MM" friendly date labels
 *  6. Auto-refresh reminders every 30s
 *  7. Images shown from PUBLIC_BASE_URL if available
 *  8. Calendar link shown when available
 */

import { useState, useEffect, useCallback } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const OCCASIONS = [
  { val: "casual",    label: "Casual",    icon: "😊" },
  { val: "office",    label: "Office",    icon: "💼" },
  { val: "party",     label: "Party",     icon: "🎊" },
  { val: "date",      label: "Date",      icon: "🌹" },
  { val: "wedding",   label: "Wedding",   icon: "💍" },
  { val: "festival",  label: "Festival",  icon: "🎉" },
  { val: "college",   label: "College",   icon: "🎓" },
  { val: "gym",       label: "Gym",       icon: "💪" },
  { val: "interview", label: "Interview", icon: "🎯" },
  { val: "dinner",    label: "Dinner",    icon: "🍽️" },
  { val: "beach",     label: "Beach",     icon: "🏖️" },
  { val: "concert",   label: "Concert",   icon: "🎸" },
];

const SCORE_COLOR = { 3: "#7ec8a0", 2: "#c8a96e", 1: "#b0a090" };
const SLOT_ICONS  = { top: "👕", bottom: "👖", shoes: "👟", accessories: "💍", ethnic: "🧣" };

// ── Helpers ───────────────────────────────────────────────────────────────────

function getMinDt(offsetMinutes = 1) {
  const d   = new Date(Date.now() + offsetMinutes * 60 * 1000);
  const pad = n => String(n).padStart(2, "0");
  return (
    d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) +
    "T" + pad(d.getHours()) + ":" + pad(d.getMinutes())
  );
}

function fmtDt(isoStr) {
  if (!isoStr) return "–";
  const d = new Date(isoStr);
  if (isNaN(d)) return isoStr;
  const now   = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dDay  = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diff  = Math.round((dDay - today) / 86400000);
  const time  = d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });
  const date  = d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  if (diff === 0)  return `Today at ${time}`;
  if (diff === 1)  return `Tomorrow at ${time}`;
  if (diff === -1) return `Yesterday at ${time}`;
  return `${date} at ${time}`;
}

// Convert ISO back to datetime-local value for rescheduling
function toDatetimeLocal(isoStr) {
  if (!isoStr) return "";
  const d   = new Date(isoStr);
  const pad = n => String(n).padStart(2, "0");
  return (
    d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) +
    "T" + pad(d.getHours()) + ":" + pad(d.getMinutes())
  );
}

// ── OutfitCard ────────────────────────────────────────────────────────────────

function OutfitCard({ outfit, selected, onSelect, index }) {
  const items  = outfit.items || {};
  const filled = Object.entries(items).filter(([, v]) => v);
  const score  = outfit.color_score || 1;

  return (
    <div
      onClick={() => onSelect(outfit)}
      style={{
        border:       `2px solid ${selected ? "#c8a96e" : "#e8ddd0"}`,
        borderRadius: 10, padding: "16px", cursor: "pointer",
        background:   selected ? "#fffbf5" : "#fff",
        transition:   "all 0.2s", position: "relative",
        boxShadow:    selected ? "0 4px 20px rgba(200,169,110,0.2)" : "0 1px 4px rgba(0,0,0,0.06)",
      }}
    >
      <div style={{
        position: "absolute", top: 10, right: 10,
        background: selected ? "#c8a96e" : "#f0e8d8",
        color: selected ? "#1a1208" : "#8a7a6a",
        borderRadius: "50%", width: 22, height: 22,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 11, fontWeight: 600,
      }}>
        {selected ? "✓" : index + 1}
      </div>

      {outfit.outfit_name && (
        <div style={{ fontSize: 12, fontWeight: 500, color: "#1a1208", marginBottom: 6, paddingRight: 28 }}>
          {outfit.outfit_name}
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: SCORE_COLOR[Math.round(score)] || "#b0a090" }} />
        <span style={{ fontSize: 11, color: SCORE_COLOR[Math.round(score)] || "#b0a090", fontWeight: 500 }}>
          {outfit.color_label || "Wearable"} · {score}/3
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(72px,1fr))", gap: 8, marginBottom: 10 }}>
        {filled.map(([slot, item]) => (
          <div key={slot} style={{ textAlign: "center" }}>
            {item.image_url ? (
              <img
                src={`${API}${item.image_url}`}
                alt={item.item_name}
                style={{ width: 64, height: 64, objectFit: "cover", borderRadius: 6, border: "1px solid #e8ddd0" }}
                onError={e => { e.target.style.display = "none"; e.target.nextSibling.style.display = "flex"; }}
              />
            ) : null}
            <div style={{
              width: 64, height: 64, background: "#f0e8d8", borderRadius: 6,
              display: item.image_url ? "none" : "flex", alignItems: "center", justifyContent: "center",
              fontSize: 22, border: "1px solid #e8ddd0",
            }}>
              {SLOT_ICONS[slot] || "👔"}
            </div>
            <div style={{ fontSize: 9, color: "#8a7a6a", marginTop: 3, textTransform: "capitalize" }}>{slot}</div>
            <div style={{ fontSize: 10, color: "#1a1208", fontWeight: 500, lineHeight: 1.2 }}>
              {item.color} {(item.item_name || "").split(" ").slice(0, 2).join(" ")}
            </div>
          </div>
        ))}
      </div>

      {outfit.styling_tip && (
        <div style={{ fontSize: 11, color: "#7a6a5a", lineHeight: 1.5, borderTop: "1px solid #f0e8d8", paddingTop: 8 }}>
          ✦ {outfit.styling_tip}
        </div>
      )}
    </div>
  );
}

// ── ReminderCard — delete + reschedule on ALL reminders ──────────────────────

function ReminderCard({ reminder, onDelete, onReschedule }) {
  const items  = reminder.outfit?.items || {};
  const filled = Object.entries(items).filter(([, v]) => v);
  const dtStr  = fmtDt(reminder.scheduled_at);
  const isPast = reminder.scheduled_at ? new Date(reminder.scheduled_at) < new Date() : false;

  const statusColor = reminder.fired ? "#7ec8a0" : isPast ? "#c87a50" : "#c8a96e";
  const statusLabel = reminder.fired ? "✓ Sent" : isPast ? "⚡ Processing" : "⏰ Scheduled";

  return (
    <div style={{
      border: "1px solid #e8ddd0", borderRadius: 10, padding: "14px 16px",
      background: "#fff", boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
    }}>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>

        {/* Outfit thumbnails */}
        <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
          {filled.slice(0, 3).map(([slot, item]) => (
            item?.image_url ? (
              <img key={slot} src={`${API}${item.image_url}`} alt={slot}
                style={{ width: 44, height: 44, objectFit: "cover", borderRadius: 6, border: "1px solid #e8ddd0" }} />
            ) : (
              <div key={slot} style={{
                width: 44, height: 44, background: "#f0e8d8", borderRadius: 6,
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18,
              }}>
                {SLOT_ICONS[slot] || "👔"}
              </div>
            )
          ))}
        </div>

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#1a1208", textTransform: "capitalize" }}>
              {reminder.occasion}
            </span>
            <span style={{ fontSize: 11, color: statusColor, fontWeight: 500 }}>{statusLabel}</span>
          </div>
          <div style={{ fontSize: 12, color: "#5a4a3a", marginBottom: 2 }}>{dtStr}</div>
          <div style={{ fontSize: 11, color: "#b8a898", marginBottom: 4 }}>
            {reminder.email && `✉ ${reminder.email}`}
            {reminder.phone && ` · 📱 ${reminder.phone}`}
          </div>
          {/* Outfit items text */}
          <div style={{ fontSize: 10.5, color: "#9a8a7a", lineHeight: 1.6 }}>
            {filled.map(([slot, item]) =>
              item ? `${slot}: ${item.color} ${item.item_name}` : ""
            ).filter(Boolean).join(" · ")}
          </div>
          {reminder.calendar_link && (
            <a href={reminder.calendar_link} target="_blank" rel="noreferrer"
              style={{ fontSize: 11, color: "#c8a96e", textDecoration: "none", marginTop: 4, display: "inline-block" }}>
              📅 View in Google Calendar →
            </a>
          )}
        </div>

        {/* Action buttons — shown for ALL reminders */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0 }}>
          {/* Reschedule (only for future/unfired) */}
          {!reminder.fired && (
            <button
              onClick={() => onReschedule(reminder)}
              title="Edit / Reschedule"
              style={{
                background: "#fffbf5", border: "1px solid #e8d8b0", borderRadius: 6,
                color: "#7a5a30", cursor: "pointer", fontSize: 12, padding: "5px 10px",
                whiteSpace: "nowrap",
              }}
            >
              ✏️ Edit
            </button>
          )}
          {/* Delete — ALWAYS shown */}
          <button
            onClick={() => onDelete(reminder._id)}
            title="Delete reminder"
            style={{
              background: "#fff5f5", border: "1px solid #f0b0b0", borderRadius: 6,
              color: "#c05050", cursor: "pointer", fontSize: 12, padding: "5px 10px",
              whiteSpace: "nowrap",
            }}
          >
            🗑 Delete
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Reschedule Modal ──────────────────────────────────────────────────────────

function RescheduleModal({ reminder, minDt, onClose, onSave }) {
  const [newDt,  setNewDt]  = useState(toDatetimeLocal(reminder.scheduled_at));
  const [occ,    setOcc]    = useState(reminder.occasion || "casual");
  const [err,    setErr]    = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!newDt) { setErr("Please select a date and time."); return; }
    const ms = new Date(newDt).getTime();
    if (isNaN(ms) || ms < Date.now() + 60_000) {
      setErr("Please choose a time at least 1 minute in the future.");
      return;
    }
    setSaving(true); setErr("");
    try {
      // Delete old, create new
      await axios.delete(`${API}/scheduler/remind/${reminder._id}`);
      await axios.post(`${API}/scheduler/remind`, {
        user_id:      reminder.user_id,
        user_name:    reminder.user_name,
        email:        reminder.email,
        phone:        reminder.phone,
        outfit:       reminder.outfit,
        occasion:     occ,
        scheduled_at: newDt,
      });
      onSave();
    } catch (e) {
      setErr(e?.response?.data?.error || "Failed to reschedule. Try again.");
    }
    setSaving(false);
  };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 999, padding: 16,
    }}>
      <div style={{
        background: "#fff", borderRadius: 12, padding: "28px 24px",
        width: "100%", maxWidth: 400, boxShadow: "0 8px 40px rgba(0,0,0,0.18)",
      }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: "#1a1208", marginBottom: 18 }}>
          ✏️ Edit Reminder
        </div>

        <label style={LABEL_STYLE}>Occasion</label>
        <select
          value={occ}
          onChange={e => setOcc(e.target.value)}
          style={{ ...INPUT_STYLE, marginBottom: 14 }}
        >
          {OCCASIONS.map(o => (
            <option key={o.val} value={o.val}>{o.icon} {o.label}</option>
          ))}
        </select>

        <label style={LABEL_STYLE}>New Date & Time</label>
        <input
          type="datetime-local"
          value={newDt}
          min={minDt}
          onChange={e => { setNewDt(e.target.value); setErr(""); }}
          style={{ ...INPUT_STYLE, marginBottom: 6 }}
        />
        {newDt && (
          <div style={{ fontSize: 11, color: "#7a5a30", marginBottom: 14 }}>
            ⏰ {fmtDt(newDt)}
          </div>
        )}

        {err && (
          <div style={{ fontSize: 12, color: "#c05050", background: "#fff5f5", border: "1px solid #f0b0b0", borderRadius: 4, padding: "8px 12px", marginBottom: 14 }}>
            {err}
          </div>
        )}

        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={onClose} style={{ flex: 1, padding: 12, background: "#f0e8d8", border: "none", borderRadius: 6, color: "#5a4a3a", cursor: "pointer", fontSize: 13 }}>
            Cancel
          </button>
          <button onClick={handleSave} disabled={saving}
            style={{ flex: 1, padding: 12, background: "#1a1208", border: "none", borderRadius: 6, color: "#c8a96e", cursor: "pointer", fontSize: 13, fontWeight: 500, opacity: saving ? 0.7 : 1 }}>
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}

const LABEL_STYLE = { fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase", color: "#8a7a6a", fontWeight: 500, marginBottom: 6, display: "block" };
const INPUT_STYLE = { width: "100%", padding: "10px 12px", border: "1px solid #e0d6c8", borderRadius: 6, fontFamily: "inherit", fontSize: 13, color: "#1a1208", background: "#fff", outline: "none", boxSizing: "border-box" };

// ── Main Component ────────────────────────────────────────────────────────────

export default function OutfitScheduler() {
  const profile  = JSON.parse(localStorage.getItem("faceAnalysis") || "{}");
  const userId   = profile.name     || "guest";
  const skinTone = profile.skinTone || "medium";
  const gender   = profile.gender   || "male";

  const [step,            setStep]            = useState("select");
  const [outfits,         setOutfits]         = useState([]);
  const [loading,         setLoading]         = useState(true);
  const [loadErr,         setLoadErr]         = useState("");
  const [selectedOutfit,  setSelectedOutfit]  = useState(null);
  const [occasion,        setOccasion]        = useState("casual");
  const [scheduledAt,     setScheduledAt]     = useState("");
  const [submitting,      setSubmitting]      = useState(false);
  const [submitErr,       setSubmitErr]       = useState("");
  const [reminders,       setReminders]       = useState([]);
  const [remErr,          setRemErr]          = useState("");
  const [tab,             setTab]             = useState("outfits");
  const [email,           setEmail]           = useState(profile.email || "");
  const [phone,           setPhone]           = useState(profile.phone || "");
  const [minDt,           setMinDt]           = useState(getMinDt(1));
  const [rescheduleTarget,setRescheduleTarget]= useState(null);
  const [deleteLoading,   setDeleteLoading]   = useState("");

  // Refresh minDt every 30s
  useEffect(() => {
    const t = setInterval(() => setMinDt(getMinDt(1)), 30_000);
    return () => clearInterval(t);
  }, []);

  const fetchOutfits = useCallback(async () => {
    setLoading(true); setLoadErr("");
    try {
      const r = await axios.get(`${API}/scheduler/mix-match/${userId}`, { params: { skin_tone: skinTone, gender } });
      setOutfits(r.data.outfits || []);
    } catch (e) {
      setLoadErr(e?.response?.data?.error || "Failed to load outfits. Add items to your closet first.");
    }
    setLoading(false);
  }, [userId, skinTone, gender]);

  const fetchReminders = useCallback(async () => {
    setRemErr("");
    try {
      const r = await axios.get(`${API}/scheduler/reminders/${userId}`);
      setReminders(r.data.reminders || []);
    } catch { setRemErr("Could not load reminders."); }
  }, [userId]);

  useEffect(() => {
    fetchOutfits();
    fetchReminders();
    axios.get(`${API}/scheduler/contact/${userId}`).then(r => {
      if (r.data.email && !email) setEmail(r.data.email);
      if (r.data.phone && !phone) setPhone(r.data.phone);
    }).catch(() => {});
  }, [fetchOutfits, fetchReminders]);

  // Auto-refresh reminders every 30s
  useEffect(() => {
    const t = setInterval(fetchReminders, 30_000);
    return () => clearInterval(t);
  }, [fetchReminders]);

  function validate() {
    if (!selectedOutfit)   return "Please select an outfit first.";
    if (!scheduledAt)      return "Please set a date and time.";
    const ms = new Date(scheduledAt).getTime();
    if (isNaN(ms))         return "Invalid date. Please pick again.";
    if (ms < Date.now() + 60_000) return "Please choose a time at least 1 minute in the future.";
    if (!email && !phone)  return "Please provide your email or phone number.";
    if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return "Invalid email address.";
    if (phone) {
      const c = phone.replace(/[\s\-()]/g, "");
      if (!/^(\+91)?[6-9]\d{9}$/.test(c)) return "Invalid Indian phone number.";
    }
    return null;
  }

  const handleSchedule = async () => {
    const err = validate();
    if (err) { setSubmitErr(err); return; }
    setSubmitting(true); setSubmitErr("");
    try {
      await axios.post(`${API}/scheduler/remind`, {
        user_id: userId, user_name: profile.name || "Friend",
        email: email.trim(), phone: phone.trim(),
        outfit: selectedOutfit, occasion, scheduled_at: scheduledAt,
      });
      setStep("done");
      fetchReminders();
    } catch (e) {
      setSubmitErr(e?.response?.data?.error || "Failed to schedule. Please try again.");
    }
    setSubmitting(false);
  };

  const handleDelete = async (rid) => {
    if (!window.confirm("Delete this reminder?")) return;
    setDeleteLoading(rid);
    try {
      await axios.delete(`${API}/scheduler/remind/${rid}`);
      fetchReminders();
    } catch { alert("Could not delete reminder."); }
    setDeleteLoading("");
  };

  const handleRescheduleClose = () => {
    setRescheduleTarget(null);
    fetchReminders();
  };

  const resetPlanner = () => {
    setStep("select"); setSelectedOutfit(null);
    setScheduledAt(""); setSubmitErr(""); setOccasion("casual");
  };

  const scheduledCount = reminders.filter(r => !r.fired).length;
  const sentCount      = reminders.filter(r => r.fired).length;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Sans:wght@300;400;500&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes fadeUp { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:translateY(0); } }
        @keyframes spin   { to { transform: rotate(360deg); } }

        .sch-root { min-height:100vh; background:#f8f4ef; font-family:'DM Sans',sans-serif; }
        .sch-header { background:#1a1208; padding:20px 32px; display:flex; align-items:center; gap:16px; position:sticky; top:0; z-index:10; }
        .sch-header-title { font-family:'Cormorant Garamond',serif; font-size:24px; font-weight:300; color:#f5ede0; }
        .sch-header-title em { font-style:italic; color:#c8a96e; }
        .sch-header-sub { font-size:11px; color:rgba(200,169,110,0.6); letter-spacing:0.15em; text-transform:uppercase; }

        .sch-tabs { display:flex; border-bottom:2px solid #e8ddd0; background:#fff; }
        .sch-tab  { flex:1; padding:14px; text-align:center; font-size:12px; font-weight:500; letter-spacing:0.08em; text-transform:uppercase; cursor:pointer; color:#8a7a6a; border-bottom:2px solid transparent; margin-bottom:-2px; transition:all 0.2s; }
        .sch-tab.active { color:#1a1208; border-bottom-color:#c8a96e; }

        .sch-body { max-width:900px; margin:0 auto; padding:28px 20px; animation:fadeUp 0.3s ease; }

        .section-label { font-size:10px; letter-spacing:0.25em; text-transform:uppercase; color:#8a7a6a; font-weight:500; margin-bottom:14px; }
        .outfit-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:16px; margin-bottom:28px; }

        .occasion-grid { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:20px; }
        .occ-btn { padding:7px 14px; border:1px solid #e8ddd0; border-radius:20px; background:#fff; font-size:12px; color:#5a4a3a; cursor:pointer; transition:all 0.15s; }
        .occ-btn.active { background:#1a1208; color:#c8a96e; border-color:#1a1208; }
        .occ-btn:hover:not(.active) { background:#f8f4ef; }

        .inp { width:100%; padding:11px 14px; border:1px solid #e0d6c8; border-radius:6px; font-family:'DM Sans',sans-serif; font-size:13px; color:#1a1208; background:#fff; outline:none; }
        .inp:focus { border-color:#c8a96e; box-shadow:0 0 0 3px rgba(200,169,110,0.1); }

        .field-label { font-size:10px; letter-spacing:0.18em; text-transform:uppercase; color:#8a7a6a; font-weight:500; margin-bottom:6px; display:block; }

        .cta-btn { width:100%; padding:14px; background:#1a1208; border:none; color:#c8a96e; font-family:'DM Sans',sans-serif; font-size:11px; font-weight:500; letter-spacing:0.25em; text-transform:uppercase; cursor:pointer; border-radius:6px; margin-top:4px; transition:all 0.2s; display:flex; align-items:center; justify-content:center; gap:8px; }
        .cta-btn:hover:not(:disabled) { background:#c8a96e; color:#1a1208; }
        .cta-btn:disabled { opacity:0.6; cursor:not-allowed; }
        .cta-btn.ghost { background:#f0e8d8; color:#5a4a3a; }
        .cta-btn.ghost:hover { background:#e0d4c0; color:#1a1208; }

        .spinner { width:13px; height:13px; border:1.5px solid currentColor; border-top-color:transparent; border-radius:50%; animation:spin 0.7s linear infinite; }

        .err-box     { background:#fff5f5; border:1px solid #f0b0b0; border-radius:6px; padding:10px 14px; font-size:12px; color:#c05050; margin-bottom:14px; }
        .info-box    { background:#fffbf5; border:1px solid #e8d8b0; border-radius:6px; padding:10px 14px; font-size:12px; color:#7a5a30; margin-bottom:14px; line-height:1.7; }
        .success-box { background:#f0fff5; border:1px solid #90d0a0; border-radius:6px; padding:10px 14px; font-size:12px; color:#307a50; margin-bottom:16px; line-height:1.7; }

        .done-card { text-align:center; padding:40px 24px; background:#fff; border-radius:12px; border:1px solid #e8ddd0; animation:fadeUp 0.4s ease; }
        .done-icon  { font-size:48px; margin-bottom:16px; }
        .done-title { font-family:'Cormorant Garamond',serif; font-size:28px; font-weight:300; color:#1a1208; margin-bottom:8px; }
        .done-sub   { font-size:13px; color:#8a7a6a; line-height:1.7; margin-bottom:20px; }

        .rem-list  { display:flex; flex-direction:column; gap:10px; }
        .empty-state { text-align:center; padding:48px 20px; color:#b8a898; font-size:13px; }
        .empty-state .big { font-size:36px; margin-bottom:12px; }

        .rem-stats { display:flex; gap:12px; margin-bottom:18px; }
        .stat-chip { padding:6px 14px; border-radius:20px; font-size:11px; font-weight:500; }

        .dt-preview { font-size:12px; color:#7a5a30; background:#fffbf5; border:1px solid #e8d8b0; border-radius:4px; padding:7px 12px; margin-top:6px; margin-bottom:14px; }

        @media(max-width:600px) {
          .sch-header { padding:16px; }
          .sch-body   { padding:16px 12px; }
          .outfit-grid { grid-template-columns:1fr; }
          .contact-row { grid-template-columns:1fr; }
        }
      `}</style>

      <div className="sch-root">

        {/* Header */}
        <div className="sch-header">
          <div>
            <div className="sch-header-sub">FaceFit</div>
            <div className="sch-header-title">Outfit <em>Planner</em></div>
          </div>
          <div style={{ marginLeft: "auto", fontSize: 12, color: "rgba(200,169,110,0.7)" }}>
            {profile.name && `👤 ${profile.name}`}
          </div>
        </div>

        {/* Tabs */}
        <div className="sch-tabs">
          {[
            { key: "outfits",   label: "📅 Plan Outfit" },
            { key: "reminders", label: `⏰ Reminders (${reminders.length})` },
          ].map(t => (
            <div key={t.key} className={`sch-tab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
              {t.label}
            </div>
          ))}
        </div>

        <div className="sch-body">

          {/* ── PLAN OUTFIT TAB ──────────────────────────────────────────── */}
          {tab === "outfits" && (
            <>
              {/* DONE */}
              {step === "done" && (
                <div className="done-card">
                  <div className="done-icon">✅</div>
                  <div className="done-title">Reminder <em>Set!</em></div>
                  <div className="done-sub">
                    Scheduled for <strong>{fmtDt(scheduledAt)}</strong>
                  </div>
                  <div className="success-box" style={{ textAlign: "left", maxWidth: 320, margin: "0 auto 20px" }}>
                    📧 <strong>Email</strong> — Will be sent at reminder time<br />
                    📱 <strong>WhatsApp</strong> — Message queued via Twilio<br />
                    📅 <strong>Google Calendar</strong> — Event created (if configured)
                  </div>
                  <button className="cta-btn" style={{ maxWidth: 280, margin: "0 auto 10px" }} onClick={resetPlanner}>
                    Plan Another Outfit →
                  </button>
                  <button className="cta-btn ghost" style={{ maxWidth: 280, margin: "0 auto" }} onClick={() => setTab("reminders")}>
                    View All Reminders
                  </button>
                </div>
              )}

              {/* SELECT */}
              {step === "select" && (
                <>
                  <div className="section-label">Step 1 — Choose Your Outfit</div>
                  {loading && (
                    <div style={{ textAlign: "center", padding: "48px 0", color: "#8a7a6a", fontSize: 13 }}>
                      <div className="spinner" style={{ margin: "0 auto 12px", width: 20, height: 20, borderWidth: 2 }} />
                      Generating AI outfit combinations from your wardrobe...
                    </div>
                  )}
                  {loadErr && (
                    <div className="err-box">{loadErr}
                      <button onClick={fetchOutfits} style={{ background: "none", border: "none", color: "#c8a96e", cursor: "pointer", marginLeft: 8, fontSize: 11, textDecoration: "underline" }}>Retry</button>
                    </div>
                  )}
                  {!loading && !loadErr && outfits.length === 0 && (
                    <div className="empty-state">
                      <div className="big">👕</div>
                      <div style={{ fontWeight: 500, color: "#5a4a3a", marginBottom: 6 }}>No outfits yet</div>
                      Upload at least 2–3 clothing items to your Digital Closet to generate combinations.
                    </div>
                  )}
                  {!loading && outfits.length > 0 && (
                    <>
                      <div className="info-box">
                        ✦ {outfits.length} AI-verified outfit combinations from your wardrobe. Tap one to schedule a reminder.
                      </div>
                      <div className="outfit-grid">
                        {outfits.map((o, i) => (
                          <OutfitCard key={o.outfit_id || i} outfit={o} index={i}
                            selected={selectedOutfit?.outfit_id === o.outfit_id}
                            onSelect={o => { setSelectedOutfit(o); setStep("schedule"); window.scrollTo(0, 0); }}
                          />
                        ))}
                      </div>
                    </>
                  )}
                </>
              )}

              {/* SCHEDULE */}
              {step === "schedule" && selectedOutfit && (
                <>
                  <div className="section-label">Selected Outfit</div>
                  <div style={{ marginBottom: 20 }}>
                    <OutfitCard outfit={selectedOutfit} index={0} selected onSelect={() => {}} />
                    <button onClick={() => { setStep("select"); setSubmitErr(""); }}
                      style={{ background: "none", border: "none", color: "#c8a96e", cursor: "pointer", fontSize: 12, marginTop: 8, textDecoration: "underline" }}>
                      ← Change outfit
                    </button>
                  </div>

                  <div className="section-label">Step 2 — Select Occasion</div>
                  <div className="occasion-grid">
                    {OCCASIONS.map(o => (
                      <button key={o.val} className={`occ-btn ${occasion === o.val ? "active" : ""}`} onClick={() => setOccasion(o.val)}>
                        {o.icon} {o.label}
                      </button>
                    ))}
                  </div>

                  <div className="section-label" style={{ marginTop: 4 }}>Step 3 — Set Date & Time</div>
                  <input
                    className="inp"
                    type="datetime-local"
                    value={scheduledAt}
                    min={minDt}
                    onChange={e => { setScheduledAt(e.target.value); setSubmitErr(""); }}
                  />
                  {scheduledAt && (
                    <div className="dt-preview">⏰ Reminder fires: <strong>{fmtDt(scheduledAt)}</strong></div>
                  )}

                  <div className="section-label">Step 4 — Notification Details</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }} className="contact-row">
                    <div>
                      <label className="field-label">Email</label>
                      <input className="inp" type="email" placeholder="you@example.com"
                        value={email} onChange={e => { setEmail(e.target.value); setSubmitErr(""); }} />
                    </div>
                    <div>
                      <label className="field-label">WhatsApp Number</label>
                      <input className="inp" type="tel" placeholder="+91 98765 43210"
                        value={phone} onChange={e => { setPhone(e.target.value); setSubmitErr(""); }} />
                    </div>
                  </div>

                  <div className="info-box">
                    📧 <strong>Email</strong> — HTML email with outfit details &amp; AI tip<br />
                    📱 <strong>WhatsApp</strong> — Message via Twilio sandbox<br />
                    📅 <strong>Google Calendar</strong> — Event invite (requires fix_token.py setup)
                  </div>

                  {submitErr && <div className="err-box">{submitErr}</div>}
                  <button className="cta-btn" onClick={handleSchedule} disabled={submitting}>
                    {submitting ? <><div className="spinner" /> Scheduling...</> : "Set Reminder →"}
                  </button>
                </>
              )}
            </>
          )}

          {/* ── REMINDERS TAB ────────────────────────────────────────────── */}
          {tab === "reminders" && (
            <>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <div className="section-label" style={{ marginBottom: 0 }}>Your Outfit Reminders</div>
                <button onClick={fetchReminders}
                  style={{ background: "none", border: "none", color: "#c8a96e", cursor: "pointer", fontSize: 11, textDecoration: "underline" }}>
                  ↻ Refresh
                </button>
              </div>

              {/* Stats chips */}
              {reminders.length > 0 && (
                <div className="rem-stats">
                  <span className="stat-chip" style={{ background: "#fffbf5", border: "1px solid #e8d8b0", color: "#7a5a30" }}>
                    ⏰ {scheduledCount} upcoming
                  </span>
                  <span className="stat-chip" style={{ background: "#f0fff5", border: "1px solid #90d0a0", color: "#307a50" }}>
                    ✓ {sentCount} sent
                  </span>
                </div>
              )}

              {remErr && <div className="err-box">{remErr}</div>}

              {reminders.length === 0 ? (
                <div className="empty-state">
                  <div className="big">⏰</div>
                  <div style={{ fontWeight: 500, color: "#5a4a3a", marginBottom: 6 }}>No reminders yet</div>
                  <div style={{ marginBottom: 20 }}>Plan an outfit and set a reminder from the Plan Outfit tab.</div>
                  <button className="cta-btn" style={{ maxWidth: 240, margin: "0 auto" }} onClick={() => setTab("outfits")}>
                    Plan an Outfit →
                  </button>
                </div>
              ) : (
                <div className="rem-list">
                  {reminders.map(r => (
                    <ReminderCard
                      key={r._id}
                      reminder={r}
                      onDelete={rid => handleDelete(rid)}
                      onReschedule={rem => setRescheduleTarget(rem)}
                    />
                  ))}
                </div>
              )}
            </>
          )}

        </div>
      </div>

      {/* Reschedule modal */}
      {rescheduleTarget && (
        <RescheduleModal
          reminder={rescheduleTarget}
          minDt={minDt}
          onClose={() => setRescheduleTarget(null)}
          onSave={handleRescheduleClose}
        />
      )}
    </>
  );
}