/**
 * ProductCard.jsx — Universal Product Card with Image
 * =====================================================
 * Handles all image sources: absolute URLs, relative /uploads/ paths,
 * weserv proxy for CORS issues, shimmer loading, graceful fallback.
 *
 * Import in EventPlanner.jsx, OutfitPhotoAnalyzer.jsx, Chatbot.jsx, etc.
 *
 * Usage:
 *   import ProductCard, { ProductGrid } from "./ProductCard";
 *   <ProductCard product={p} />
 *   <ProductGrid products={[...]} label="Shop This Look" />
 */

import { useState } from "react";

const API = "http://127.0.0.1:5000";

// ── Universal image URL resolver ──────────────────────────────────────────────
export function resolveProductImage(url) {
  if (!url || url === "None" || url === "null" || url === "undefined") return null;
  if (url.startsWith("data:")) return url;

  // Backend relative paths
  if (url.startsWith("/uploads/") || url.startsWith("/static/")) {
    return `${API}${url}`;
  }

  // Already absolute
  if (url.startsWith("http://127") || url.startsWith("http://localhost") || url.startsWith(`${API}`)) {
    return url;
  }

  // Trusted CDNs — serve directly
  const trustedDomains = [
    "myntassets.com", "rukminim", "m.media-amazon", "images.nykaa",
    "images-cdn.ajio", "images.meesho", "lh3.googleusercontent",
    "images.bewakoof", "img1.ajio", "cdn.shopify", "encrypted-tbn",
    "googleusercontent", "media.istockphoto", "assets.ajio",
    "assets.myntassets",
  ];
  if (url.startsWith("https") && trustedDomains.some(d => url.includes(d))) {
    return url;
  }

  // External images — proxy through weserv to avoid CORS issues
  if (url.startsWith("http")) {
    try {
      return `https://images.weserv.nl/?url=${encodeURIComponent(url)}&w=400&h=400&fit=contain&bg=ffffff&output=jpg`;
    } catch {
      return url;
    }
  }

  return null;
}

// ── CSS injected once ─────────────────────────────────────────────────────────
const CARD_CSS = `
  @keyframes pc-shimmer {
    0% { background-position: -200% center; }
    100% { background-position: 200% center; }
  }
  @keyframes pc-fadeIn {
    from { opacity: 0; transform: scale(0.98); }
    to   { opacity: 1; transform: scale(1); }
  }
  .pc-card {
    background: #fff;
    border: 1px solid #ece6dc;
    border-radius: 14px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: transform 0.22s cubic-bezier(.34,1.56,.64,1), box-shadow 0.22s ease;
    text-decoration: none;
    cursor: pointer;
    position: relative;
  }
  .pc-card:hover {
    transform: translateY(-4px) scale(1.01);
    box-shadow: 0 14px 36px rgba(26,18,8,0.13);
    border-color: rgba(200,165,90,0.4);
  }
  .pc-img-wrap {
    position: relative;
    width: 100%;
    padding-top: 100%;
    background: #f7f3ee;
    overflow: hidden;
    flex-shrink: 0;
  }
  .pc-img-wrap img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    padding: 10px;
    transition: transform 0.35s ease, opacity 0.3s ease;
  }
  .pc-card:hover .pc-img-wrap img {
    transform: scale(1.06);
  }
  .pc-shimmer {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, #f0ebe4 25%, #e8e0d4 50%, #f0ebe4 75%);
    background-size: 200% 100%;
    animation: pc-shimmer 1.4s infinite;
  }
  .pc-fallback {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    background: linear-gradient(135deg, #faf7f3, #f0ece6);
  }
  .pc-fallback-icon {
    font-size: 28px;
    opacity: 0.35;
  }
  .pc-fallback-text {
    font-size: 9px;
    color: #c4b4a4;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 600;
  }
  .pc-source-badge {
    position: absolute;
    bottom: 8px;
    left: 8px;
    background: rgba(26,15,0,0.68);
    backdrop-filter: blur(4px);
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 8px;
    color: #e8d8b8;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 600;
    pointer-events: none;
  }
  .pc-sale-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    background: linear-gradient(135deg, #e04040, #c82020);
    color: #fff;
    font-size: 9px;
    font-weight: 800;
    padding: 3px 8px;
    border-radius: 20px;
    letter-spacing: 0.06em;
  }
  .pc-info {
    padding: 12px 13px 14px;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .pc-title {
    font-size: 12px;
    color: #2c1f0f;
    line-height: 1.45;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    min-height: 34px;
  }
  .pc-price-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 2px;
  }
  .pc-price {
    font-size: 15px;
    font-weight: 700;
    color: #1a0f00;
    font-family: 'DM Sans', sans-serif;
  }
  .pc-buy-btn {
    display: block;
    margin: 0 12px 12px;
    padding: 9px 0;
    background: #1a0f00;
    color: #c8a55a;
    text-align: center;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    border-radius: 8px;
    text-decoration: none;
    font-family: 'DM Sans', sans-serif;
    transition: background 0.18s, color 0.18s;
  }
  .pc-buy-btn:hover {
    background: #c8a55a;
    color: #1a0f00;
  }
  .pc-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
  }
  .pc-grid-label {
    font-size: 9px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: #a8998a;
    font-weight: 700;
    margin-bottom: 12px;
    font-family: 'DM Sans', sans-serif;
  }
  @media (max-width: 640px) {
    .pc-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  }
`;

let cssInjected = false;
function injectCSS() {
  if (cssInjected) return;
  const style = document.createElement("style");
  style.textContent = CARD_CSS;
  document.head.appendChild(style);
  cssInjected = true;
}

// ── Source label cleaner ──────────────────────────────────────────────────────
function sourceLabel(source) {
  if (!source) return "shop";
  return source.replace(/^www\./, "").replace(/\.(com|in|net|org)$/, "").slice(0, 14);
}

// ── Main ProductCard ──────────────────────────────────────────────────────────
export default function ProductCard({ product: p, showSaveButton, userId }) {
  injectCSS();

  const [imgState, setImgState] = useState("loading"); // loading | loaded | error
  const src = resolveProductImage(p?.image || p?.thumbnail || p?.imageUrl);

  // Parse price for sale detection
  const priceStr = p?.price || p?.Price || "";
  const hasDiscount = priceStr.includes("₹") && priceStr.match(/\d{4,}/);

  const label = sourceLabel(p?.source || p?.platform || "");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      <a
        href={p?.link || p?.url || "#"}
        target="_blank"
        rel="noreferrer"
        className="pc-card"
        style={{ animation: "pc-fadeIn 0.3s ease both" }}
        onClick={e => { if (!p?.link && !p?.url) e.preventDefault(); }}
      >
        {/* Image */}
        <div className="pc-img-wrap">
          {/* Shimmer while loading */}
          {imgState === "loading" && <div className="pc-shimmer" />}

          {/* Actual image */}
          {src && imgState !== "error" && (
            <img
              src={src}
              alt={p?.title || "product"}
              style={{ opacity: imgState === "loaded" ? 1 : 0 }}
              onLoad={() => setImgState("loaded")}
              onError={() => setImgState("error")}
              crossOrigin="anonymous"
            />
          )}

          {/* Fallback when no image or error */}
          {(!src || imgState === "error") && (
            <div className="pc-fallback">
              <span className="pc-fallback-icon">◈</span>
              <span className="pc-fallback-text">No Preview</span>
            </div>
          )}

          {/* Source badge */}
          {label && <div className="pc-source-badge">{label}</div>}
        </div>

        {/* Info */}
        <div className="pc-info">
          <div className="pc-title">{p?.title || "View Product"}</div>
          <div className="pc-price-row">
            {priceStr && <span className="pc-price">{priceStr}</span>}
          </div>
        </div>

        {/* Buy button */}
        <div className="pc-buy-btn">Shop Now →</div>
      </a>
    </div>
  );
}

// ── ProductGrid — multi-product display ───────────────────────────────────────
export function ProductGrid({ products, label, maxItems = 4, columns }) {
  injectCSS();

  if (!products || products.length === 0) return null;

  const gridStyle = columns
    ? { display: "grid", gridTemplateColumns: `repeat(${columns}, 1fr)`, gap: "12px" }
    : undefined;

  return (
    <div style={{ marginTop: 12 }}>
      {label && <div className="pc-grid-label">{label}</div>}
      <div className={gridStyle ? undefined : "pc-grid"} style={gridStyle}>
        {products.slice(0, maxItems).map((p, i) => (
          <ProductCard key={i} product={p} />
        ))}
      </div>
    </div>
  );
}

// ── CategoryProductSection — label + grid ─────────────────────────────────────
export function CategoryProductSection({ categoryKey, products, maxItems = 4 }) {
  injectCSS();
  if (!products || products.length === 0) return null;

  const CAT_META = {
    shirt: { label: "👕 Shirts & Tops", emoji: "👕" },
    pants: { label: "👖 Pants & Bottoms", emoji: "👖" },
    shoes: { label: "👟 Shoes", emoji: "👟" },
    ethnic: { label: "🥻 Ethnic Wear", emoji: "🥻" },
    accessories: { label: "💍 Accessories", emoji: "💍" },
    watch: { label: "⌚ Watches", emoji: "⌚" },
    blazer: { label: "🧥 Blazers", emoji: "🧥" },
    dress: { label: "👗 Dresses", emoji: "👗" },
    cleanser: { label: "🧴 Cleanser", emoji: "🧴" },
    toner: { label: "💧 Toner", emoji: "💧" },
    serum_day: { label: "☀️ Day Serum", emoji: "☀️" },
    serum_night: { label: "🌙 Night Serum", emoji: "🌙" },
    moisturizer: { label: "🫧 Moisturizer", emoji: "🫧" },
    sunscreen: { label: "🌞 Sunscreen", emoji: "🌞" },
    eye_cream: { label: "👁️ Eye Cream", emoji: "👁️" },
    spot_treatment: { label: "🎯 Spot Treatment", emoji: "🎯" },
  };

  const meta = CAT_META[categoryKey] || {
    label: categoryKey.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
    emoji: "🛍",
  };

  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{
        fontSize: 10, fontWeight: 700, letterSpacing: ".2em",
        textTransform: "uppercase", color: "#8a7a6a",
        marginBottom: 10, fontFamily: "'DM Sans', sans-serif",
        display: "flex", alignItems: "center", gap: 6,
      }}>
        <span>{meta.emoji}</span> {meta.label}
      </div>
      <div className="pc-grid">
        {products.slice(0, maxItems).map((p, i) => (
          <ProductCard key={i} product={p} />
        ))}
      </div>
    </div>
  );
}