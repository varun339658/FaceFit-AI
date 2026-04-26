/**
 * BudgetBrandPanel.jsx — Budget Filter + Brand Preference UI
 * Features 1 & 2: Price range slider + brand memory
 */
import { useState, useEffect } from "react";
import axios from "axios";

const API = "http://127.0.0.1:5000";

const POPULAR_BRANDS = {
  fashion: ["Mango","Zara","H&M","FabIndia","Biba","W","AND","Global Desi","Vero Moda","Forever 21","Levi's","Van Heusen","Allen Solly","Peter England","Louis Philippe","Roadster","HRX","Puma","Nike","Adidas"],
  footwear: ["Metro","Bata","Woodland","Hush Puppies","Clarks","Steve Madden","FabAlley","Inc.5"],
  ethnic: ["Manyavar","Mohey","FabIndia","Biba","Soch","Libas","Aurelia","W"],
  skincare: ["Minimalist","Dot & Key","Mamaearth","Plum","The Derma Co","Cetaphil","Neutrogena","Lakme","VLCC","Nykaa Naturals"],
};

export default function BudgetBrandPanel({ userId, onUpdate }) {
  const [brands, setBrands]       = useState([]);
  const [budget, setBudget]       = useState({ min_price: 0, max_price: null });
  const [loading, setLoading]     = useState(false);
  const [saved, setSaved]         = useState(false);
  const [activeTab, setActiveTab] = useState("budget");
  const [maxInput, setMaxInput]   = useState("");
  const [minInput, setMinInput]   = useState("0");
  const [category, setCategory]   = useState("fashion");

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
    const isAdded = brands.includes(brand);
    setLoading(true);
    try {
      if (isAdded) {
        const r = await axios.delete(`${API}/preferences/brands/${userId}/${encodeURIComponent(brand)}`);
        setBrands(r.data.brands || []);
      } else {
        const r = await axios.post(`${API}/preferences/brands/${userId}`, { brands: [brand] });
        setBrands(r.data.brands || []);
      }
      onUpdate?.();
    } catch (e) { console.error(e); }
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
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const S = {
    wrap: { padding: "16px 0" },
    tabs: { display: "flex", gap: 8, marginBottom: 18 },
    tab: (active) => ({ padding: "7px 16px", border: `1px solid ${active ? "#c8a55a" : "#ddd3c2"}`, background: active ? "rgba(200,165,90,.1)" : "#fff", color: active ? "#8a5820" : "#6a5a4a", borderRadius: 20, cursor: "pointer", fontSize: 12, fontWeight: active ? 600 : 400, fontFamily: "inherit" }),
    sectionLabel: { fontSize: 9, letterSpacing: ".28em", textTransform: "uppercase", color: "#b8a898", fontWeight: 700, marginBottom: 12 },
    row: { display: "flex", alignItems: "center", gap: 12, marginBottom: 14 },
    inp: { flex: 1, padding: "9px 12px", border: "1px solid #ddd3c2", borderRadius: 6, fontFamily: "inherit", fontSize: 13, color: "#1a1208", outline: "none", background: "#faf7f3" },
    saveBtn: { padding: "9px 20px", background: saved ? "#2d7a4f" : "#1a1208", color: saved ? "#fff" : "#c8a55a", border: "none", borderRadius: 6, fontSize: 11, fontWeight: 700, letterSpacing: ".12em", textTransform: "uppercase", cursor: "pointer", fontFamily: "inherit", transition: "all .2s" },
    catTabs: { display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 },
    catTab: (a) => ({ padding: "4px 11px", border: `1px solid ${a?"#c8a55a":"#ddd3c2"}`, background: a?"rgba(200,165,90,.1)":"transparent", borderRadius: 12, fontSize: 10.5, color: a?"#8a5820":"#7a6a5a", cursor: "pointer", fontFamily: "inherit" }),
    brandGrid: { display: "flex", gap: 7, flexWrap: "wrap" },
    brandChip: (selected) => ({ padding: "5px 12px", border: `1.5px solid ${selected ? "#c8a55a" : "#ece6dc"}`, background: selected ? "rgba(200,165,90,.12)" : "#fff", borderRadius: 20, fontSize: 11, color: selected ? "#8a5820" : "#5a4a3a", cursor: "pointer", fontWeight: selected ? 600 : 400, transition: "all .15s", fontFamily: "inherit", display: "flex", alignItems: "center", gap: 5 }),
    savedBrands: { display: "flex", gap: 7, flexWrap: "wrap", marginBottom: 14 },
    savedBrandPill: { padding: "4px 10px", background: "rgba(200,165,90,.12)", border: "1px solid rgba(200,165,90,.3)", borderRadius: 20, fontSize: 11, color: "#8a5820", fontWeight: 600, display: "flex", alignItems: "center", gap: 5 },
    removeBtn: { background: "none", border: "none", color: "#c87060", cursor: "pointer", fontSize: 12, fontWeight: 700, padding: 0 },
    budgetInfo: { fontSize: 11, color: "#a8998a", marginTop: 6, lineHeight: 1.6 },
    savedMsg: { fontSize: 12, color: "#2d7a4f", fontWeight: 500 },
  };

  return (
    <div style={S.wrap}>
      <div style={S.tabs}>
        <button style={S.tab(activeTab === "budget")} onClick={() => setActiveTab("budget")}>💰 Budget Filter</button>
        <button style={S.tab(activeTab === "brands")} onClick={() => setActiveTab("brands")}>⭐ Brand Preferences</button>
      </div>

      {activeTab === "budget" && (
        <div>
          <div style={S.sectionLabel}>Set Your Price Range</div>
          <div style={S.row}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 10, color: "#8a7a6a", marginBottom: 4 }}>Min Price (₹)</div>
              <input style={S.inp} type="number" placeholder="0" value={minInput} min="0"
                onChange={e => setMinInput(e.target.value)} />
            </div>
            <div style={{ color: "#c4b4a4", fontSize: 16, paddingTop: 18 }}>—</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 10, color: "#8a7a6a", marginBottom: 4 }}>Max Price (₹)</div>
              <input style={S.inp} type="number" placeholder="No limit" value={maxInput}
                onChange={e => setMaxInput(e.target.value)} />
            </div>
            <div style={{ paddingTop: 18 }}>
              <button style={S.saveBtn} onClick={saveBudget} disabled={loading}>
                {saved ? "✓ Saved" : loading ? "..." : "Save"}
              </button>
            </div>
          </div>
          {budget.max_price && (
            <div style={S.budgetInfo}>
              ✓ Filtering products: ₹{budget.min_price.toLocaleString()} – ₹{budget.max_price.toLocaleString()}<br />
              Products outside this range are automatically filtered from recommendations.
            </div>
          )}
          {!budget.max_price && (
            <div style={S.budgetInfo}>No budget limit set — all prices shown. Set a max price to filter results.</div>
          )}
          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase", color: "#b8a898", fontWeight: 700, marginBottom: 8 }}>Quick Select</div>
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
              {[["Under ₹500", 0, 500],["₹500–₹1500", 500, 1500],["₹1500–₹3000", 1500, 3000],["₹3000–₹7000", 3000, 7000],["₹7000+", 7000, null]].map(([label, min, max]) => (
                <button key={label}
                  style={{ padding: "5px 12px", border: `1px solid ${budget.min_price===min&&budget.max_price===max?"#c8a55a":"#ddd3c2"}`, background: budget.min_price===min&&budget.max_price===max?"rgba(200,165,90,.1)":"#fff", borderRadius: 16, fontSize: 11, color: "#5a4838", cursor: "pointer", fontFamily: "inherit" }}
                  onClick={() => { setMinInput(String(min)); setMaxInput(max?String(max):""); }}>
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "brands" && (
        <div>
          {brands.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={S.sectionLabel}>Your Saved Brands ({brands.length})</div>
              <div style={S.savedBrands}>
                {brands.map(b => (
                  <div key={b} style={S.savedBrandPill}>
                    ⭐ {b}
                    <button style={S.removeBtn} onClick={() => toggleBrand(b)}>✕</button>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div style={S.sectionLabel}>Browse by Category</div>
          <div style={S.catTabs}>
            {Object.keys(POPULAR_BRANDS).map(cat => (
              <button key={cat} style={S.catTab(category===cat)} onClick={() => setCategory(cat)}>
                {cat.charAt(0).toUpperCase()+cat.slice(1)}
              </button>
            ))}
          </div>
          <div style={S.brandGrid}>
            {POPULAR_BRANDS[category].map(brand => {
              const selected = brands.includes(brand);
              return (
                <button key={brand} style={S.brandChip(selected)} onClick={() => toggleBrand(brand)} disabled={loading}>
                  {selected ? "✓" : "+"} {brand}
                </button>
              );
            })}
          </div>
          <div style={{ fontSize: 11, color: "#a8998a", marginTop: 12 }}>
            ✦ Saved brands are automatically prioritized in product search results.
          </div>
        </div>
      )}
    </div>
  );
}