/**
 * BudgetBrandChatPanel.jsx
 * ========================
 * Compact budget/brand panel that appears INSIDE the chatbot sidebar/drawer.
 * Also exports a hook useBudgetBrand() that chatbot uses to apply preferences
 * to every product request it makes.
 */
import { useState, useEffect, useCallback } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const BRANDS = {
  fashion:  ["Zara","H&M","Mango","FabIndia","Levi's","Van Heusen","Allen Solly","Roadster","HRX","Puma","Nike","Adidas","Peter England","Louis Philippe","Biba","W"],
  footwear: ["Metro","Bata","Woodland","Hush Puppies","Adidas","Nike","Puma","Skechers"],
  ethnic:   ["Manyavar","Mohey","FabIndia","Biba","Soch","Libas","Aurelia"],
  skincare: ["Minimalist","Dot & Key","Mamaearth","Plum","The Derma Co","Cetaphil","Nykaa Naturals"],
};

// ── Hook: use in Chatbot.jsx to auto-apply budget/brand to requests ──────────
export function useBudgetBrand(userId) {
  const [prefs, setPrefs] = useState({ brands: [], min_price: 0, max_price: null });

  const reload = useCallback(async () => {
    if (!userId) return;
    try {
      const [br, bu] = await Promise.all([
        axios.get(`${API}/preferences/brands/${userId}`),
        axios.get(`${API}/preferences/budget/${userId}`),
      ]);
      setPrefs({
        brands:    br.data.brands || [],
        min_price: bu.data.min_price || 0,
        max_price: bu.data.max_price || null,
      });
    } catch { }
  }, [userId]);

  useEffect(() => { reload(); }, [reload]);

  // Returns context string to append to chatbot messages
  const buildContext = useCallback(() => {
    const parts = [];
    if (prefs.brands.length > 0) {
      parts.push(`Preferred brands: ${prefs.brands.slice(0, 3).join(", ")}`);
    }
    if (prefs.max_price) {
      parts.push(`Budget: ₹${prefs.min_price}–₹${prefs.max_price}`);
    } else if (prefs.min_price > 0) {
      parts.push(`Min budget: ₹${prefs.min_price}`);
    }
    return parts.length > 0 ? `[User preferences: ${parts.join(" | ")}]` : "";
  }, [prefs]);

  return { prefs, reload, buildContext };
}

// ── Compact panel component ───────────────────────────────────────────────────
export default function BudgetBrandChatPanel({ userId, onUpdate }) {
  const [brands, setBrands]     = useState([]);
  const [budget, setBudget]     = useState({ min_price: 0, max_price: null });
  const [minInput, setMinInput] = useState("0");
  const [maxInput, setMaxInput] = useState("");
  const [loading, setLoading]   = useState(false);
  const [saved,   setSaved]     = useState(false);
  const [section, setSection]   = useState("budget"); // budget | brands
  const [catTab,  setCatTab]    = useState("fashion");

  useEffect(() => {
    if (!userId) return;
    axios.get(`${API}/preferences/brands/${userId}`).then(r => setBrands(r.data.brands || [])).catch(() => {});
    axios.get(`${API}/preferences/budget/${userId}`).then(r => {
      setBudget(r.data);
      setMinInput(String(r.data.min_price || 0));
      setMaxInput(r.data.max_price ? String(r.data.max_price) : "");
    }).catch(() => {});
  }, [userId]);

  const toggleBrand = async (brand) => {
    setLoading(true);
    try {
      const isAdded = brands.includes(brand);
      if (isAdded) {
        const r = await axios.delete(`${API}/preferences/brands/${userId}/${encodeURIComponent(brand)}`);
        setBrands(r.data.brands || []);
      } else {
        const r = await axios.post(`${API}/preferences/brands/${userId}`, { brands: [brand] });
        setBrands(r.data.brands || []);
      }
      onUpdate?.();
    } catch { }
    setLoading(false);
  };

  const saveBudget = async () => {
    setLoading(true);
    try {
      const min = parseInt(minInput) || 0;
      const max = maxInput ? parseInt(maxInput) : null;
      await axios.post(`${API}/preferences/budget/${userId}`, { min_price: min, max_price: max });
      setBudget({ min_price: min, max_price: max });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onUpdate?.();
    } catch { }
    setLoading(false);
  };

  const S = {
    wrap: { background: "rgba(200,165,90,.04)", border: "1px solid rgba(200,165,90,.2)", borderRadius: 14, padding: "16px 18px", marginBottom: 14 },
    header: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 },
    title: { fontSize: 10, letterSpacing: ".22em", textTransform: "uppercase", color: "#c8a55a", fontWeight: 700 },
    tabs: { display: "flex", gap: 6 },
    tab: (a) => ({ padding: "4px 12px", border: `1px solid ${a ? "#c8a55a" : "#ddd3c2"}`, background: a ? "rgba(200,165,90,.12)" : "transparent", borderRadius: 12, fontSize: 10.5, color: a ? "#8a5820" : "#8a7a6a", cursor: "pointer", fontFamily: "inherit" }),
    row: { display: "flex", gap: 10, alignItems: "center", marginBottom: 10 },
    inp: { flex: 1, padding: "8px 10px", border: "1px solid #ddd3c2", borderRadius: 6, fontFamily: "inherit", fontSize: 12, color: "#1a1208", outline: "none", background: "#faf7f3" },
    saveBtn: { padding: "8px 14px", background: saved ? "#2d7a4f" : "#1a1208", color: saved ? "#fff" : "#c8a55a", border: "none", borderRadius: 6, fontSize: 10, fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", cursor: "pointer", fontFamily: "inherit", whiteSpace: "nowrap" },
    quickRow: { display: "flex", gap: 5, flexWrap: "wrap", marginTop: 8 },
    quickBtn: (active) => ({ padding: "3px 9px", border: `1px solid ${active ? "#c8a55a" : "#ddd3c2"}`, background: active ? "rgba(200,165,90,.1)" : "transparent", borderRadius: 10, fontSize: 10, color: active ? "#8a5820" : "#7a6a5a", cursor: "pointer", fontFamily: "inherit" }),
    brandGrid: { display: "flex", gap: 5, flexWrap: "wrap" },
    brandChip: (sel) => ({ padding: "4px 10px", border: `1.5px solid ${sel ? "#c8a55a" : "#ece6dc"}`, background: sel ? "rgba(200,165,90,.1)" : "#fff", borderRadius: 14, fontSize: 10.5, color: sel ? "#8a5820" : "#5a4a3a", cursor: "pointer", fontWeight: sel ? 600 : 400, fontFamily: "inherit" }),
    catTabs: { display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 10 },
    savedRow: { display: "flex", gap: 5, flexWrap: "wrap", marginBottom: 10 },
    savedPill: { padding: "3px 9px", background: "rgba(200,165,90,.1)", border: "1px solid rgba(200,165,90,.3)", borderRadius: 10, fontSize: 10.5, color: "#8a5820", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 },
    removeX: { background: "none", border: "none", color: "#c87060", cursor: "pointer", fontSize: 11, padding: 0, fontWeight: 700 },
    hint: { fontSize: 10, color: "#a8998a", marginTop: 8, lineHeight: 1.5 },
  };

  return (
    <div style={S.wrap}>
      <div style={S.header}>
        <div style={S.title}>⚙ My Preferences</div>
        <div style={S.tabs}>
          <button style={S.tab(section === "budget")} onClick={() => setSection("budget")}>💰 Budget</button>
          <button style={S.tab(section === "brands")} onClick={() => setSection("brands")}>⭐ Brands</button>
        </div>
      </div>

      {section === "budget" && (
        <>
          <div style={S.row}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 9, color: "#8a7a6a", marginBottom: 3 }}>Min (₹)</div>
              <input style={S.inp} type="number" value={minInput} min="0" placeholder="0"
                onChange={e => setMinInput(e.target.value)} />
            </div>
            <div style={{ color: "#ccc", fontSize: 14 }}>—</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 9, color: "#8a7a6a", marginBottom: 3 }}>Max (₹)</div>
              <input style={S.inp} type="number" value={maxInput} placeholder="No limit"
                onChange={e => setMaxInput(e.target.value)} />
            </div>
            <div style={{ paddingTop: 16 }}>
              <button style={S.saveBtn} onClick={saveBudget} disabled={loading}>
                {saved ? "✓" : loading ? "..." : "Save"}
              </button>
            </div>
          </div>
          <div style={S.quickRow}>
            {[["<₹500",0,500],["₹500-1.5k",500,1500],["₹1.5k-3k",1500,3000],["₹3k-7k",3000,7000],["₹7k+",7000,null]].map(([l,mn,mx])=>(
              <button key={l} style={S.quickBtn(budget.min_price===mn&&budget.max_price===mx)}
                onClick={() => { setMinInput(String(mn)); setMaxInput(mx?String(mx):""); }}>
                {l}
              </button>
            ))}
          </div>
          <div style={S.hint}>
            {budget.max_price
              ? `✓ Filtering: ₹${budget.min_price.toLocaleString()} – ₹${budget.max_price.toLocaleString()} applied to all chatbot recommendations`
              : "Set a budget to auto-filter all product recommendations in chat"}
          </div>
        </>
      )}

      {section === "brands" && (
        <>
          {brands.length > 0 && (
            <div style={S.savedRow}>
              {brands.map(b => (
                <div key={b} style={S.savedPill}>
                  {b}
                  <button style={S.removeX} onClick={() => toggleBrand(b)}>✕</button>
                </div>
              ))}
            </div>
          )}
          <div style={S.catTabs}>
            {Object.keys(BRANDS).map(cat => (
              <button key={cat} style={S.tab(catTab===cat)} onClick={() => setCatTab(cat)}>
                {cat.charAt(0).toUpperCase()+cat.slice(1)}
              </button>
            ))}
          </div>
          <div style={S.brandGrid}>
            {BRANDS[catTab].map(brand => (
              <button key={brand} style={S.brandChip(brands.includes(brand))}
                onClick={() => toggleBrand(brand)} disabled={loading}>
                {brands.includes(brand) ? "✓ " : "+ "}{brand}
              </button>
            ))}
          </div>
          <div style={S.hint}>
            ✦ Saved brands are prioritized in every outfit + skincare recommendation from the chatbot.
          </div>
        </>
      )}
    </div>
  );
}