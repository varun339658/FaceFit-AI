import React, { useEffect, useState, useRef } from "react";

const API = "http://127.0.0.1:5000";
const PLACEHOLDER = "https://placehold.co/300x300?text=No+Image";

/* ─── Category metadata ──────────────────────────────────────────────────── */
const CATEGORY_META = {
  // Men fashion
  shirt:      { label: "Shirt / Top",      icon: "👕", section: "outfit" },
  pants:      { label: "Pants / Bottom",   icon: "👖", section: "outfit" },
  shoes:      { label: "Shoes",            icon: "👟", section: "outfit" },
  watch:      { label: "Watch",            icon: "⌚", section: "outfit" },
  bracelet:   { label: "Bracelet",         icon: "📿", section: "outfit" },
  sunglasses: { label: "Sunglasses",       icon: "🕶️", section: "outfit" },
  // Women fashion
  top:        { label: "Top / Blouse",     icon: "👚", section: "outfit" },
  necklace:   { label: "Necklace",         icon: "💎", section: "outfit" },
  earrings:   { label: "Earrings",         icon: "✨", section: "outfit" },
  // Skincare
  cleanser:           { label: "Cleanser",          icon: "🧼", section: "skin" },
  toner:              { label: "Toner",              icon: "💧", section: "skin" },
  serum_day:          { label: "Day Serum",          icon: "🌅", section: "skin" },
  serum_night:        { label: "Night Serum",        icon: "🌙", section: "skin" },
  moisturizer:        { label: "Moisturizer",        icon: "🫧", section: "skin" },
  sunscreen:          { label: "Sunscreen",          icon: "☀️", section: "skin" },
  eye_cream:          { label: "Eye Cream",          icon: "👁️", section: "skin" },
  spot_treatment:     { label: "Spot Treatment",     icon: "🎯", section: "skin" },
  brightening_serum:  { label: "Brightening Serum", icon: "✨", section: "skin" },
  face_oil:           { label: "Face Oil",           icon: "💆", section: "skin" },
};

/* ─── CSS ────────────────────────────────────────────────────────────────── */
const css = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }

  .pp { min-height:100vh; background:#F7F5F0; font-family:'DM Sans',sans-serif; color:#1A1A1A; }

  /* hero */
  .hero {
    background: linear-gradient(135deg, #1A1A1A 0%, #2d2d2d 100%);
    color: white; padding: 48px 56px 40px;
  }
  .hero-eyebrow { font-size:0.7rem; letter-spacing:0.22em; text-transform:uppercase; color:rgba(255,255,255,0.45); margin-bottom:10px; }
  .hero h1 { font-family:'Playfair Display',serif; font-size:clamp(2rem,4vw,3rem); font-weight:700; margin-bottom:14px; }
  .hero-tags { display:flex; gap:10px; flex-wrap:wrap; }
  .hero-tag { background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.15); padding:4px 14px; border-radius:20px; font-size:0.78rem; color:rgba(255,255,255,0.7); }
  .hero-tag strong { color:white; }

  .body { padding: 48px 56px; }

  /* section header */
  .sec-hdr { display:flex; align-items:center; gap:16px; margin-bottom:32px; margin-top:56px; }
  .sec-hdr:first-child { margin-top:0; }
  .sec-hdr h2 { font-family:'Playfair Display',serif; font-size:1.7rem; font-weight:700; white-space:nowrap; }
  .sec-line { flex:1; height:1px; background:#D9D4CA; }

  /* outfit pills */
  .outfit-pills { display:flex; flex-direction:column; gap:8px; margin-bottom:36px; }
  .outfit-pill { display:flex; align-items:flex-start; gap:12px; background:white; border:1px solid #e8e3dc; border-radius:8px; padding:12px 18px; }
  .outfit-pill .icon { font-size:1.2rem; flex-shrink:0; margin-top:1px; }
  .outfit-pill .key { font-size:0.7rem; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; color:#888; min-width:80px; margin-top:3px; }
  .outfit-pill .val { font-size:0.9rem; line-height:1.5; color:#333; }

  /* routine */
  .routine-row { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:40px; }
  .routine-card { background:white; border:1px solid #e8e3dc; border-radius:8px; padding:20px 22px; }
  .routine-card h4 { font-size:0.72rem; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; margin-bottom:14px; color:#444; }
  .routine-card ol { padding-left:18px; display:flex; flex-direction:column; gap:8px; }
  .routine-card li { font-size:0.88rem; color:#333; line-height:1.4; }

  /* category block */
  .cat-block { margin-bottom:44px; }
  .cat-title { display:flex; align-items:center; gap:8px; margin-bottom:16px; }
  .cat-title .icon { font-size:1.1rem; }
  .cat-title .label { font-family:'Playfair Display',serif; font-size:1.05rem; font-weight:600; text-transform:capitalize; color:#222; }

  /* product grid */
  .prod-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:14px; }

  /* product card */
  .prod-card { background:white; border:1px solid #e8e3dc; border-radius:8px; overflow:hidden; display:flex; flex-direction:column; transition:box-shadow 0.2s,transform 0.2s; }
  .prod-card:hover { box-shadow:0 8px 28px rgba(0,0,0,0.1); transform:translateY(-2px); }
  .prod-img-wrap { width:100%; height:170px; background:#f0ede8; display:flex; align-items:center; justify-content:center; overflow:hidden; }
  .prod-img-wrap img { width:100%; height:100%; object-fit:contain; padding:8px; transition:transform 0.3s; }
  .prod-card:hover .prod-img-wrap img { transform:scale(1.04); }
  .prod-info { padding:12px 14px; flex:1; display:flex; flex-direction:column; gap:4px; }
  .prod-title { font-size:0.8rem; line-height:1.4; color:#333; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
  .prod-price { font-size:0.92rem; font-weight:700; color:#1A1A1A; margin-top:4px; }
  .prod-src { font-size:0.68rem; color:#aaa; }
  .buy-btn { display:block; margin:0 12px 12px; background:#1A1A1A; color:white; text-align:center; padding:9px 0; text-decoration:none; font-size:0.76rem; font-weight:600; letter-spacing:0.07em; border-radius:5px; transition:background 0.2s; }
  .buy-btn:hover { background:#333; }

  /* states */
  .loading-wrap { min-height:80vh; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:16px; }
  .spinner { width:38px; height:38px; border:3px solid #e0dbd3; border-top-color:#1A1A1A; border-radius:50%; animation:spin 0.75s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .empty-note { color:#bbb; font-size:0.88rem; padding:12px 0; }
  .err-banner { background:#fff0f0; border:1px solid #ffcccc; color:#c00; padding:14px 18px; border-radius:6px; margin-bottom:24px; font-size:0.9rem; }

  /* ── Upload & Search Outfit ── */
  .upload-search-section {
    background: white;
    border: 1px solid #e8e3dc;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 20px;
  }
  .upload-search-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #1A1A1A;
    margin-bottom: 6px;
  }
  .upload-search-sub {
    font-size: 0.82rem;
    color: #888;
    margin-bottom: 20px;
    line-height: 1.5;
  }
  .upload-area {
    border: 2px dashed #d9d4ca;
    border-radius: 10px;
    padding: 28px 20px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    background: #faf9f7;
    position: relative;
  }
  .upload-area:hover, .upload-area.drag-over {
    border-color: #1A1A1A;
    background: #f5f3ef;
  }
  .upload-area input[type=file] {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
    width: 100%;
    height: 100%;
  }
  .upload-icon-big { font-size: 2.2rem; margin-bottom: 8px; }
  .upload-hint-text { font-size: 0.85rem; color: #888; }
  .upload-hint-text strong { color: #1A1A1A; }

  .preview-row {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    margin-top: 16px;
    flex-wrap: wrap;
  }
  .preview-thumb {
    width: 110px;
    height: 110px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid #e8e3dc;
    flex-shrink: 0;
  }
  .preview-info {
    flex: 1;
    min-width: 180px;
  }
  .preview-filename {
    font-size: 0.78rem;
    color: #888;
    margin-bottom: 6px;
    word-break: break-all;
  }
  .preview-query-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #aaa;
    margin-bottom: 4px;
  }
  .preview-query-val {
    font-size: 0.85rem;
    color: #333;
    font-style: italic;
    line-height: 1.4;
  }

  .search-btn {
    margin-top: 16px;
    padding: 12px 28px;
    background: #1A1A1A;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: background 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .search-btn:hover { background: #333; }
  .search-btn:disabled { background: #aaa; cursor: not-allowed; }

  .clear-btn {
    margin-top: 16px;
    margin-left: 10px;
    padding: 12px 20px;
    background: transparent;
    color: #888;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 0.82rem;
    cursor: pointer;
    transition: all 0.2s;
  }
  .clear-btn:hover { border-color: #1A1A1A; color: #1A1A1A; }

  .search-results-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #aaa;
    margin: 24px 0 12px;
  }
  .search-results-query {
    font-size: 0.88rem;
    color: #555;
    margin-bottom: 16px;
    font-style: italic;
  }

  .mini-spinner {
    width: 18px; height: 18px;
    border: 2px solid rgba(255,255,255,0.4);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    display: inline-block;
  }

  .paste-hint {
    font-size: 0.75rem;
    color: #aaa;
    margin-top: 8px;
    text-align: center;
  }

  @media(max-width:680px) {
    .hero { padding:32px 24px; }
    .body { padding:32px 24px; }
    .routine-row { grid-template-columns:1fr; }
    .prod-grid { grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); }
    .upload-search-section { padding: 20px; }
  }
`;

/* ─── Sub-components ─────────────────────────────────────────────────────── */

function ProductCard({ p }) {
  const src = p?.image && p.image !== "None" && p.image !== "null"
    ? p.image : PLACEHOLDER;
  return (
    <div className="prod-card">
      <div className="prod-img-wrap">
        <img src={src} alt={p?.title || "product"} onError={(e) => { e.target.src = PLACEHOLDER; }} />
      </div>
      <div className="prod-info">
        <div className="prod-title">{p?.title || "—"}</div>
        {p?.price && <div className="prod-price">{p.price}</div>}
        {p?.source && <div className="prod-src">via {p.source}</div>}
      </div>
      <a href={p?.link || "#"} target="_blank" rel="noopener noreferrer" className="buy-btn">
        Buy Now →
      </a>
    </div>
  );
}

function CategoryBlock({ catKey, items }) {
  if (!items || items.length === 0) return null;
  const meta = CATEGORY_META[catKey] || { label: catKey.replace(/_/g, " "), icon: "🛍" };
  return (
    <div className="cat-block">
      <div className="cat-title">
        <span className="icon">{meta.icon}</span>
        <span className="label">{meta.label}</span>
      </div>
      <div className="prod-grid">
        {items.map((p, i) => <ProductCard key={i} p={p} />)}
      </div>
    </div>
  );
}

/* ─── Upload & Search Outfit Component ──────────────────────────────────── */

function OutfitSearchUploader() {
  const [file, setFile]               = useState(null);
  const [preview, setPreview]         = useState(null);
  const [searching, setSearching]     = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults]         = useState([]);
  const [error, setError]             = useState("");
  const [dragOver, setDragOver]       = useState(false);
  const inputRef = useRef();

  // Allow paste from clipboard (Ctrl+V screenshot)
  useEffect(() => {
    const handlePaste = (e) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const blob = item.getAsFile();
          if (blob) {
            const namedFile = new File([blob], "pasted_image.png", { type: blob.type });
            handleFile(namedFile);
          }
          break;
        }
      }
    };
    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, []);

  const handleFile = (f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResults([]);
    setSearchQuery("");
    setError("");
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith("image/")) handleFile(f);
  };

  const handleSearch = async () => {
    if (!file) return;
    setSearching(true);
    setError("");
    setResults([]);
    setSearchQuery("");

    const formData = new FormData();
    formData.append("image", file);

    try {
      const res = await fetch(`${API}/search-outfit`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setSearchQuery(data.query || "");
      setResults(data.products || []);
    } catch (e) {
      console.error("Outfit search error:", e);
      setError(`Search failed: ${e.message}`);
    } finally {
      setSearching(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setResults([]);
    setSearchQuery("");
    setError("");
  };

  return (
    <div className="upload-search-section">
      <div className="upload-search-title">🔍 Search Similar Outfits</div>
      <div className="upload-search-sub">
        Upload a photo of any clothing item — shirt, kurta, dress, shoes — or paste a screenshot.
        Our AI will identify it and find similar products on Indian e-commerce sites.
      </div>

      {/* Drop Zone */}
      <div
        className={`upload-area ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          onChange={(e) => handleFile(e.target.files[0])}
        />
        <div className="upload-icon-big">📸</div>
        <div className="upload-hint-text">
          <strong>Click to upload</strong> or drag &amp; drop a clothing photo
        </div>
      </div>
      <div className="paste-hint">💡 You can also press Ctrl+V / ⌘+V to paste a screenshot directly</div>

      {/* Preview */}
      {preview && (
        <div className="preview-row">
          <img src={preview} alt="preview" className="preview-thumb" />
          <div className="preview-info">
            <div className="preview-filename">{file?.name || "Uploaded image"}</div>
            {searchQuery && (
              <>
                <div className="preview-query-label">AI Detected Query</div>
                <div className="preview-query-val">"{searchQuery}"</div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Buttons */}
      {preview && (
        <div>
          <button className="search-btn" onClick={handleSearch} disabled={searching}>
            {searching ? (
              <><span className="mini-spinner" /> Searching…</>
            ) : (
              "🔍 Find Similar Products"
            )}
          </button>
          <button className="clear-btn" onClick={handleClear}>Clear</button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="err-banner" style={{ marginTop: 16 }}>⚠ {error}</div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <>
          <div className="search-results-label">Results</div>
          {searchQuery && (
            <div className="search-results-query">Showing results for: "{searchQuery}"</div>
          )}
          <div className="prod-grid">
            {results.map((p, i) => <ProductCard key={i} p={p} />)}
          </div>
        </>
      )}

      {!searching && results.length === 0 && searchQuery && (
        <div className="empty-note" style={{ marginTop: 16 }}>
          No products found for "{searchQuery}". Try a different image.
        </div>
      )}
    </div>
  );
}

/* ─── Main Products Component ────────────────────────────────────────────── */

export default function Products() {
  const [skinProducts, setSkinProducts] = useState({});
  const [skinRoutine,  setSkinRoutine]  = useState({});
  const [outfits,      setOutfits]      = useState({});
  const [outfitProds,  setOutfitProds]  = useState({});
  const [analysis,     setAnalysis]     = useState({});
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState(null);

  useEffect(() => {
    try {
      setOutfits(JSON.parse(localStorage.getItem("outfits") || "{}"));
      setOutfitProds(JSON.parse(localStorage.getItem("outfit_products") || "{}"));
      setAnalysis(JSON.parse(localStorage.getItem("faceAnalysis") || "{}"));
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    const a = (() => {
      try { return JSON.parse(localStorage.getItem("faceAnalysis") || "{}"); }
      catch { return {}; }
    })();

    fetch(`${API}/products`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        skinTone:   a.skinTone   || "medium",
        conditions: a.conditions || [],
      }),
    })
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        setSkinProducts(data.products || {});
        setSkinRoutine(data.routine   || {});
        setLoading(false);
      })
      .catch(err => {
        console.error("Skincare error:", err);
        setError("Could not load skincare products. Make sure the backend is running.");
        setLoading(false);
      });
  }, []);

  if (loading) return (
    <>
      <style>{css}</style>
      <div className="loading-wrap">
        <div className="spinner" />
        <p style={{ color: "#888", fontFamily: "'DM Sans', sans-serif" }}>
          Building your personalised picks…
        </p>
      </div>
    </>
  );
const addClosetItem = async () => {
  try {
    const res = await fetch("http://127.0.0.1:5000/closet/add", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        user_id: "Varun",
        item: {
          category: "shirt",
          color: "black",
          type: "oversized t-shirt",
          image: ""
        }
      })
    });

    const data = await res.json();
    console.log("Response:", data);
    alert("Item added!");
  } catch (err) {
    console.error(err);
    alert("Error adding item");
  }
};
  const hasOutfitDesc = Object.keys(outfits).length > 0;
  const hasOutfitProd = Object.keys(outfitProds).length > 0;
  const hasSkinProd   = Object.keys(skinProducts).length > 0;
  const hasRoutine    = skinRoutine.morning?.length > 0 || skinRoutine.night?.length > 0;

  return (
    <>
      <style>{css}</style>

      {/* ── Hero ────────────────────────────────────────────────────── */}
      <div className="hero">
        <div className="hero-eyebrow">FACEFIT — PERSONALISED RECOMMENDATIONS</div>
        <h1>Your Style &amp; Skincare Report</h1>
        <div className="hero-tags">
          {analysis.skinTone   && <span className="hero-tag">Skin Tone: <strong>{analysis.skinTone}</strong></span>}
          {analysis.face_shape && <span className="hero-tag">Face Shape: <strong>{analysis.face_shape}</strong></span>}
          {analysis.gender     && <span className="hero-tag">Gender: <strong style={{ textTransform: "capitalize" }}>{analysis.gender}</strong></span>}
          {(analysis.conditions || [])
            .filter((c, i, a) => a.indexOf(c) === i)
            .map((c, i) => (
              <span key={i} className="hero-tag">
                Condition: <strong style={{ textTransform: "capitalize" }}>{c}</strong>
              </span>
            ))}
        </div>
      </div>

      <div className="body">
        {error && <div className="err-banner">⚠ {error}</div>}

        {/* ════════ OUTFIT SECTION ════════════════════════════════ */}
        {(hasOutfitDesc || hasOutfitProd) && (
          <div className="sec-hdr">
            <h2>👔 Outfit Recommendations</h2>
            <div className="sec-line" />
          </div>
        )}
      <button onClick={addClosetItem}>
  Add Closet Item
</button>
        {/* Outfit description pills */}
        {hasOutfitDesc && (
          <div className="outfit-pills">
            {Object.entries(outfits).map(([key, val]) => {
              const meta = CATEGORY_META[key] || { icon: "🛍", label: key };
              return (
                <div key={key} className="outfit-pill">
                  <span className="icon">{meta.icon}</span>
                  <span className="key">{meta.label || key}</span>
                  <span className="val">{val}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Outfit products */}
        {hasOutfitProd
          ? Object.entries(outfitProds).map(([cat, items]) => (
              <CategoryBlock key={cat} catKey={cat} items={items} />
            ))
          : hasOutfitDesc && <p className="empty-note">No outfit products found — check backend logs.</p>
        }

        {/* ════════ UPLOAD & SEARCH OUTFIT ════════════════════════ */}
        <div className="sec-hdr">
          <h2>📸 Upload &amp; Search Outfit</h2>
          <div className="sec-line" />
        </div>
        <OutfitSearchUploader />

        {/* ════════ SKINCARE SECTION ══════════════════════════════ */}
        {(hasSkinProd || hasRoutine) && (
          <div className="sec-hdr">
            <h2>🧴 Skincare Routine</h2>
            <div className="sec-line" />
          </div>
        )}

        {/* Morning / Night routine */}
        {hasRoutine && (
          <div className="routine-row">
            {skinRoutine.morning?.length > 0 && (
              <div className="routine-card">
                <h4>☀️ Morning Routine</h4>
                <ol>{skinRoutine.morning.map((s, i) => <li key={i}>{s}</li>)}</ol>
              </div>
            )}
            {skinRoutine.night?.length > 0 && (
              <div className="routine-card">
                <h4>🌙 Night Routine</h4>
                <ol>{skinRoutine.night.map((s, i) => <li key={i}>{s}</li>)}</ol>
              </div>
            )}
          </div>
        )}

        {/* Skincare products */}
        {hasSkinProd
          ? Object.entries(skinProducts).map(([cat, items]) => (
              <CategoryBlock key={cat} catKey={cat} items={items} />
            ))
          : <p className="empty-note">No skincare products found — check backend logs.</p>
        }
      </div>
    </>
  );
}