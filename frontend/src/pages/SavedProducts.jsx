/**
 * SavedProducts.jsx — FaceFit Price Drop Alert UI
 * =================================================
 * Displays saved products with current prices and drop indicators.
 *
 * Also exports a <SaveButton /> component you embed next to any
 * product card in Chatbot.jsx to let users save products in one click.
 *
 * Usage in Chatbot.jsx:
 *   import { SaveButton } from "./SavedProducts";
 *   <SaveButton product={p} userId={user.name} />
 */

import { useState, useEffect } from "react";
import axios from "axios";
import { getProfile } from "./Register";

const API = "http://127.0.0.1:5000";

// ── Save Button — embed this in any product card in Chatbot.jsx ───────────────
export function SaveButton({ product, userId }) {
  const [saved,   setSaved]   = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    if (saved || loading || !userId) return;
    setLoading(true);
    try {
      await axios.post(`${API}/products/save`, {
        userId:    userId,
        title:     product.title,
        url:       product.link || product.url,
        thumbnail: product.image || product.thumbnail || "",
        price:     product.price,
        platform:  product.source || "",
      });
      setSaved(true);
    } catch (e) {
      console.error("Save error:", e);
    }
    setLoading(false);
  }

  return (
    <button
      onClick={handleSave}
      disabled={saved || loading}
      title={saved ? "Saved! You'll be alerted on price drops" : "Save for price drop alerts"}
      style={{
        border: `1px solid ${saved ? "#2d7a4f" : "#e8ddd0"}`,
        background: saved ? "#eafaf1" : "#fff",
        color:  saved ? "#2d7a4f" : "#8a7a6a",
        borderRadius: 6, padding: "4px 10px",
        fontSize: 11, cursor: saved ? "default" : "pointer",
        fontFamily: "'DM Sans', sans-serif",
        display: "flex", alignItems: "center", gap: 4,
        transition: "all 0.2s", whiteSpace: "nowrap",
      }}
    >
      {loading ? "..." : saved ? "✓ Saved" : "🔔 Alert me"}
    </button>
  );
}

// ── Main Saved Products Page ──────────────────────────────────────────────────
export default function SavedProducts() {
  const user    = getProfile();
  const userId  = user?.name || user?.userId || "";

  const [products, setProducts] = useState([]);
  const [loading,  setLoading]  = useState(false);
  const [checking, setChecking] = useState(null);  // product_id being checked

  useEffect(() => {
    if (userId) loadSaved();
  }, [userId]);

  async function loadSaved() {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/products/saved/${userId}`);
      setProducts(res.data.products || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  async function unsave(product_id) {
    try {
      await axios.delete(`${API}/products/saved/${product_id}`);
      setProducts(prev => prev.filter(p => p.product_id !== product_id));
    } catch (e) {
      console.error(e);
    }
  }

  async function manualCheck(product_id) {
    setChecking(product_id);
    try {
      const res = await axios.post(`${API}/products/price-check`, { product_id });
      const d   = res.data;
      setProducts(prev => prev.map(p =>
        p.product_id === product_id
          ? { ...p, last_checked_price: d.current_price, drop_pct: d.drop_pct }
          : p
      ));
    } catch (e) {
      console.error(e);
    }
    setChecking(null);
  }

  function PriceDropBadge({ drop_pct }) {
    if (!drop_pct || drop_pct <= 0) return null;
    return (
      <span style={{
        background: "#eafaf1", color: "#2d7a4f", borderRadius: 12,
        padding: "2px 8px", fontSize: 11, fontWeight: 500,
      }}>
        ↓ {drop_pct}% off
      </span>
    );
  }

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", maxWidth: 640, margin: "0 auto", padding: "24px 16px" }}>

      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontFamily: "'Cormorant Garamond', serif", fontWeight: 300, fontSize: 28, color: "#1a1208", margin: 0 }}>
          Saved <em style={{ fontStyle: "italic", color: "#c8a96e" }}>Products</em>
        </h2>
        <p style={{ fontSize: 13, color: "#8a7a6a", marginTop: 6 }}>
          You'll receive WhatsApp + email alerts when the price drops — even ₹1.
        </p>
      </div>

      {loading && (
        <div style={{ textAlign: "center", padding: 32, color: "#8a7a6a", fontSize: 13 }}>
          Loading saved products...
        </div>
      )}

      {!loading && products.length === 0 && (
        <div style={{
          textAlign: "center", padding: 40, color: "#b8a898",
          border: "1px dashed #e0d6c8", borderRadius: 12, fontSize: 13,
        }}>
          No saved products yet.<br />
          <span style={{ fontSize: 12 }}>Tap "🔔 Alert me" on any product in the chatbot to track its price.</span>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {products.map(p => (
          <div key={p.product_id} style={{
            border: "1px solid #e8ddd0", borderRadius: 12, padding: 16,
            background: "#fff", display: "flex", gap: 14, alignItems: "flex-start",
          }}>
            {p.thumbnail && (
              <img
                src={p.thumbnail} alt={p.title}
                style={{ width: 64, height: 64, objectFit: "cover", borderRadius: 8, flexShrink: 0 }}
                onError={e => { e.target.style.display = "none"; }}
              />
            )}
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 500, color: "#1a1208", marginBottom: 4, lineHeight: 1.4 }}>
                {p.title}
              </div>

              {/* Prices */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                {p.original_price && (
                  <span style={{
                    fontSize: 12, color: "#8a7a6a",
                    textDecoration: p.drop_pct > 0 ? "line-through" : "none",
                  }}>
                    ₹{Math.round(p.original_price)}
                  </span>
                )}
                {p.drop_pct > 0 && p.last_checked_price && (
                  <span style={{ fontSize: 14, fontWeight: 600, color: "#2d7a4f" }}>
                    ₹{Math.round(p.last_checked_price)}
                  </span>
                )}
                <PriceDropBadge drop_pct={p.drop_pct} />
              </div>

              {/* Platform + last checked */}
              <div style={{ fontSize: 11, color: "#b8a898", marginBottom: 10 }}>
                {p.platform && <span>{p.platform} · </span>}
                {p.last_checked_at && (
                  <span>Checked {new Date(p.last_checked_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</span>
                )}
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: 8 }}>
                <a
                  href={p.url} target="_blank" rel="noreferrer"
                  style={{
                    fontSize: 11, padding: "5px 12px", borderRadius: 6,
                    background: "#1a1208", color: "#c8a96e", textDecoration: "none",
                    letterSpacing: "0.05em",
                  }}
                >
                  Shop →
                </a>
                <button
                  onClick={() => manualCheck(p.product_id)}
                  disabled={checking === p.product_id}
                  style={{
                    fontSize: 11, padding: "5px 12px", borderRadius: 6,
                    border: "1px solid #e8ddd0", background: "#fff",
                    color: "#8a7a6a", cursor: "pointer",
                  }}
                >
                  {checking === p.product_id ? "Checking..." : "Check price"}
                </button>
                <button
                  onClick={() => unsave(p.product_id)}
                  style={{
                    fontSize: 11, padding: "5px 12px", borderRadius: 6,
                    border: "1px solid #fde8e8", background: "#fff",
                    color: "#c0392b", cursor: "pointer",
                  }}
                >
                  Remove
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}