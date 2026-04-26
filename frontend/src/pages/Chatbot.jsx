/**
 * Chatbot.jsx — FaceFit AI (FULLY UPDATED with all features)
 * =================================================================
 * FIXES APPLIED (from WardrobeImageFix.js):
 *  - proxyImage: now correctly prepends API base for "/uploads/" and "/static/" paths
 *  - WardrobeItemCard: fixed URL resolution for relative backend paths
 *  - OutfitItemThumb: fixed URL resolution
 *  - ClosetTab wardrobe grid: fixed URL resolution
 *
 * FEATURES:
 *  1. VoiceInput mic button in input bar (Web Speech API)
 *  2. BudgetBrandPanel tab for budget filter + brand preferences
 *  3. ColorPaletteWheel shown after mix & match results
 *  4. OutfitImageGenerator in MultiOutfitCard
 *  5. BodyShapeDetector tab
 *  6. SkinConditionExplainer integrated in SkinProgress.jsx (separate file)
 *  7. EventPlanner tab — AI Event Planner
 *  8. OutfitPhotoAnalyzer tab — Occasion Photo Analyzer
 */

import { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import OutfitScheduler from "./OutfitScheduler";
import SkinProgress from "./SkinProgress";
import SavedProducts, { SaveButton } from "./SavedProducts";
import WeatherBanner from "./WeatherBanner";
import { getProfile, restoreSession, logout } from "./Register";

import VoiceInput            from "./VoiceInput";
import BudgetBrandPanel      from "./BudgetBrandPanel";
import ColorPaletteWheel     from "./ColorPaletteWheel";
import OutfitImageGenerator  from "./OutfitImageGenerator";
import BodyShapeDetector     from "./BodyShapeDetector";
import BudgetBrandChatPanel, { useBudgetBrand } from "./BudgetBrandChatPanel";
import EventPlanner          from "./EventPlanner";
import OutfitPhotoAnalyzer   from "./OutfitPhotoAnalyzer";

import ReplaceItem from "./ReplaceItem";
import StylePreferences from "./StylePreferences";

const API = "http://127.0.0.1:5000";

const getUser = () => getProfile();

// ── FIXED proxyImage ─────────────────────────────────────────────────────────
// ROOT CAUSE: backend returns "/uploads/filename.jpg" (relative path).
// FIX: always prepend API base when URL starts with "/" (relative backend path).
const proxyImage = (url) => {
  if (!url) return null;
  if (url.startsWith("data:")) return url;
  // Fix: backend returns "/uploads/xxx.jpg" or "/static/xxx" → prepend API
  if (url.startsWith("/uploads/") || url.startsWith("/static/")) {
    return `${API}${url}`;
  }
  if (url.startsWith(API)) return url;
  if (url.startsWith("http://127") || url.startsWith("http://localhost")) return url;
  if (url.includes("encrypted-tbn") || url.includes("googleusercontent")) return url;
  // External URLs → proxy through weserv to avoid CORS
  try {
    return `https://images.weserv.nl/?url=${encodeURIComponent(url)}&w=300&h=300&fit=contain&bg=ffffff`;
  } catch { return url; }
};

// ── Shared image URL resolver (used by all wardrobe/closet components) ────────
// Handles both absolute and relative paths from the backend.
const resolveItemImageUrl = (image_url) => {
  if (!image_url) return null;
  if (image_url.startsWith("http")) return image_url;
  // Relative path → prepend API base, ensure leading slash
  return `${API}${image_url.startsWith("/") ? "" : "/"}${image_url}`;
};

const CAT_LABELS = {
  shirt:"Shirt",pants:"Bottoms",shoes:"Shoes",watch:"Watch",bracelet:"Bracelet",
  sunglasses:"Sunglasses",top:"Top",necklace:"Necklace",earrings:"Earrings",dress:"Dress",
  ethnic:"Ethnic Wear",accessories:"Accessories",blazer:"Blazer",jacket:"Jacket",
  track_pants:"Track Pants",gym_tshirt:"Gym T-Shirt",sports_shoes:"Sports Shoes",
  gym_shorts:"Gym Shorts",swim_shorts:"Swim Shorts",beach_shirt:"Beach Shirt",flip_flops:"Flip Flops",
  cleanser:"Cleanser",toner:"Toner",serum_day:"Day Serum",serum_night:"Night Serum",
  moisturizer:"Moisturizer",sunscreen:"Sunscreen",eye_cream:"Eye Cream",
  spot_treatment:"Spot Treatment",brightening_serum:"Brightening Serum",face_oil:"Face Oil",
};

const CAT_ICONS = {
  shirt:"👕",pants:"👖",shoes:"👟",watch:"⌚",bracelet:"📿",sunglasses:"🕶️",top:"👚",
  necklace:"📿",earrings:"✨",dress:"👗",ethnic:"🥻",accessories:"💍",blazer:"🧥",jacket:"🧥",
  track_pants:"🩳",gym_tshirt:"💪",sports_shoes:"👟",gym_shorts:"🩳",swim_shorts:"🩱",
  beach_shirt:"🌴",flip_flops:"🩴",cleanser:"🧴",toner:"💧",serum_day:"☀️",serum_night:"🌙",
  moisturizer:"🫧",sunscreen:"🌞",eye_cream:"👁️",spot_treatment:"🎯",brightening_serum:"✨",face_oil:"🌿",
};

const SKINCARE_CATS = new Set([
  "cleanser","toner","serum_day","serum_night","moisturizer","sunscreen",
  "eye_cream","spot_treatment","brightening_serum","face_oil",
]);

const FASHION_ORDER = [
  "gym_tshirt","track_pants","gym_shorts","sports_shoes",
  "swim_shorts","beach_shirt","flip_flops",
  "ethnic","dress","shirt","top","pants","blazer","jacket","shoes",
  "watch","bracelet","necklace","earrings","sunglasses","accessories",
];

const CLOSET_CAT_ICONS = { shirt:"👕",pants:"👖",shoes:"👟",accessories:"💍",ethnic:"🥻",dress:"👗",sunglasses:"🕶️",watch:"⌚" };

const ALL_EVENTS = [
  {id:"casual",label:"Casual Day",icon:"😊"},{id:"college",label:"College",icon:"🎓"},
  {id:"office",label:"Office",icon:"💼"},{id:"interview",label:"Interview",icon:"🎯"},
  {id:"date",label:"Date Night",icon:"🌹"},{id:"party",label:"Party",icon:"🎊"},
  {id:"wedding",label:"Wedding",icon:"💍"},{id:"festival",label:"Festival",icon:"🎉"},
  {id:"gym",label:"Gym",icon:"💪"},{id:"beach",label:"Beach",icon:"🏖️"},
  {id:"travel",label:"Travel",icon:"✈️"},{id:"dinner",label:"Dinner",icon:"🍽️"},
  {id:"brunch",label:"Brunch",icon:"☕"},{id:"concert",label:"Concert",icon:"🎸"},
  {id:"puja",label:"Puja/Temple",icon:"🪔"},{id:"sangeet",label:"Sangeet",icon:"🎶"},
];

const EVENT_OUTFIT_RULES = {
  gym:       {valid:["track_pants","gym_tshirt","sports_shoes","gym_shorts"],invalid:["ethnic","blazer","necklace","earrings","dress"]},
  beach:     {valid:["beach_shirt","swim_shorts","flip_flops"],invalid:["ethnic","blazer","formal"]},
  interview: {valid:["shirt","pants","blazer","shoes","watch"],invalid:["track_pants","gym_tshirt","flip_flops","gym_shorts"]},
  office:    {valid:["shirt","pants","blazer","shoes","watch"],invalid:["track_pants","gym_tshirt","flip_flops"]},
  wedding:   {valid:["ethnic","dress","shoes","accessories"],preferred:["ethnic"]},
  festival:  {valid:["ethnic","shirt","pants","shoes","accessories"],preferred:["ethnic"]},
  casual:    {valid:["shirt","pants","shoes","top","dress"]},
};

const STYLE_AESTHETICS = {
  "old money":         {icon:"👔",desc:"Quiet luxury — tailored blazers, polo shirts, chinos, loafers. Muted tones: navy, camel, cream.",colors:["navy","camel","cream","hunter green","burgundy"],pieces:["Polo shirt","Tailored chinos","Oxford shoes or loafers","Blazer","Classic watch"],avoid:["Logos","Loud prints","Streetwear"]},
  "streetwear":        {icon:"🧢",desc:"Oversized silhouettes, graphic tees, cargo pants, chunky sneakers.",colors:["black","white","grey","electric blue","red"],pieces:["Oversized graphic tee","Cargo pants","Chunky sneakers","Bucket hat","Puffer jacket"],avoid:["Formal shoes","Slim trousers","Blazers"]},
  "minimalist":        {icon:"⬜",desc:"Less is more. Clean lines, neutral tones, quality basics.",colors:["white","black","grey","cream","beige"],pieces:["Plain white tee","Straight-leg trousers","Clean white sneakers","Simple watch","Minimal accessories"],avoid:["Bold prints","Heavy branding","Statement accessories"]},
  "athleisure":        {icon:"🏃",desc:"Athletic + leisure — joggers, hoodies, sports tops.",colors:["black","grey","navy","electric blue","coral"],pieces:["Slim jogger","Sports tee or hoodie","Crisp sneakers","Athletic watch"],avoid:["Formal blazers","Leather shoes","Ethnic wear"]},
  "formal":            {icon:"👔",desc:"Business formal. Suits, blazers, formal shoes.",colors:["navy","charcoal","black","white","grey"],pieces:["Crisp formal shirt","Tailored trousers","Derby shoes","Blazer","Classic watch"],avoid:["Casual tees","Sneakers","Denim"]},
  "boho":              {icon:"🌸",desc:"Bohemian — flowy fabrics, earthy tones, ethnic prints.",colors:["terracotta","mustard","cream","olive","rust"],pieces:["Flowy kurta","Linen pants","Kolhapuri sandals","Layered accessories"],avoid:["Formal blazers","Structured tailoring"]},
  "smart casual":      {icon:"🧥",desc:"The sweet spot between formal and casual.",colors:["navy","white","grey","olive","camel"],pieces:["Dark slim jeans","Oxford or linen shirt","Loafers or clean sneakers","Optional blazer"],avoid:["Track pants","Gym wear","Heavy graphics"]},
  "indo western":      {icon:"🥻",desc:"East meets West — kurta with jeans, embroidered blazers.",colors:["navy","cream","black","mustard","emerald"],pieces:["Kurta with slim jeans","Embroidered nehru jacket","Churidar","Jutti or oxford shoes"],avoid:["Full western only or full ethnic only"]},
  "preppy":            {icon:"🎓",desc:"College campus inspired — polos, chinos, pastel shirts.",colors:["navy","pastel blue","white","salmon","mint"],pieces:["Polo shirt","Chino pants","Boat shoes","Striped tee","Clean watch"],avoid:["Heavy streetwear","Loud graphics"]},
  "hypebeast":         {icon:"🔥",desc:"Bold logos, limited pieces, sneaker culture.",colors:["black","white","red","yellow","neon"],pieces:["Statement graphic tee","Slim joggers","Limited sneakers","Cap or beanie"],avoid:["Formal wear","Muted tones"]},
};

const CHIPS = (user) => {
  const isF = ["female","women","woman","girl","f"].includes((user?.gender||"").toLowerCase());
  return [
    {label:"My skincare routine",icon:"🧴"},{label:"Outfit for college",icon:"🎓"},
    {label:"Old Money style for me",icon:"👔"},{label:"Mix & match from my wardrobe",icon:"✨"},
    {label:"Plan outfit for a wedding",icon:"💍"},{label:"Festival outfit from my closet",icon:"🎉"},
    {label:"What colours suit my skin?",icon:"🎨"},{label:`${isF?"Kurti":"Kurta"} for festival`,icon:"🥻"},
    {label:"Streetwear aesthetic for me",icon:"🧢"},{label:"Gym outfit for me",icon:"💪"},
    {label:"Closet gap analysis",icon:"📊"},{label:"Schedule an outfit reminder",icon:"🔔"},
  ];
};

const validateOutfitForEvent = (items, eventId) => {
  const rules = EVENT_OUTFIT_RULES[eventId];
  if (!rules) return {valid:true,warnings:[]};
  const warnings = [];
  const itemNames = items.map(i => `${i.item_name||""} ${i.category||""}`.toLowerCase());
  if (rules.invalid) {
    for (const inv of rules.invalid) {
      if (itemNames.some(n => n.includes(inv.replace("_"," ")))) {
        warnings.push(`⚠️ ${inv.replace("_"," ")} is not ideal for ${eventId}`);
      }
    }
  }
  return {valid:warnings.length===0,warnings};
};

const COLOR_SWATCHES = {
  black:"#1a1a1a",white:"#f5f5f0",grey:"#9e9e9e",gray:"#9e9e9e",red:"#d32f2f",
  blue:"#1565c0",green:"#2e7d32",yellow:"#f9a825",orange:"#e65100",pink:"#c2185b",
  purple:"#6a1b9a",brown:"#4e342e",beige:"#d7c4a3",cream:"#f5f0dc",navy:"#0d2b6e",
  "navy blue":"#0d2b6e","dark green":"#1b5e20","off white":"#f5f0dc","dark grey":"#424242",
  maroon:"#880e4f",teal:"#00695c",olive:"#827717",mustard:"#f57f17",
  burgundy:"#880e4f",emerald:"#1b5e20","royal blue":"#1565c0",
  "electric blue":"#0288d1",coral:"#e64a19",gold:"#f9a825",
  saffron:"#ff8f00",terracotta:"#bf360c",camel:"#a1887f","forest green":"#2e7d32",
};

const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=DM+Sans:wght@300;400;500;600&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body, #root { height: 100%; }
  body { font-family: 'DM Sans', sans-serif; background: #f7f3ee; color: #2c1f0f; }
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #ddd3c2; border-radius: 4px; }
  @keyframes fadeUp { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
  @keyframes shimmer { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes blink { 0%,100%{opacity:.3;transform:scale(.9)} 50%{opacity:1;transform:scale(1.1)} }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
  @keyframes slideIn { from { opacity:0; transform:translateX(-8px); } to { opacity:1; transform:translateX(0); } }
  @keyframes slideUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }
  @keyframes glow { 0%,100%{box-shadow:0 0 8px rgba(200,165,90,.3)} 50%{box-shadow:0 0 20px rgba(200,165,90,.6)} }
  @keyframes micPulse { 0%,100%{box-shadow:0 0 0 0 rgba(200,165,90,.4)} 70%{box-shadow:0 0 0 8px rgba(200,165,90,0)} }
  .facefit-root { height:100vh; display:flex; flex-direction:column; background:#f7f3ee; overflow:hidden; }
  .ff-header { display:flex; align-items:center; justify-content:space-between; padding:0 28px; height:62px; background:#fff; border-bottom:1px solid #ece6dc; flex-shrink:0; box-shadow:0 1px 16px rgba(0,0,0,.04); gap:12px; }
  .ff-brand { display:flex; align-items:center; gap:12px; }
  .ff-logo { width:38px; height:38px; background:linear-gradient(135deg,#1a0f00,#3a2010); border-radius:8px; display:flex; align-items:center; justify-content:center; color:#c8a55a; font-size:18px; box-shadow:0 2px 10px rgba(0,0,0,.18); flex-shrink:0; }
  .ff-brand-text { line-height:1.2; }
  .ff-eyebrow { font-size:8px; letter-spacing:.35em; color:#b0a090; text-transform:uppercase; font-weight:500; }
  .ff-wordmark { font-family:'Cormorant Garamond',serif; font-size:22px; font-weight:400; color:#1a0f00; letter-spacing:.02em; }
  .ff-header-right { display:flex; align-items:center; gap:10px; flex-shrink:0; }
  .ff-profile { display:flex; align-items:center; gap:9px; padding:6px 14px; border:1px solid #ece6dc; border-radius:30px; background:#faf7f3; }
  .ff-dot { width:7px; height:7px; border-radius:50%; background:#6fc897; flex-shrink:0; animation:pulse 2s ease infinite; }
  .ff-profile-name { font-size:12.5px; font-weight:600; color:#2c1f0f; }
  .ff-profile-meta { font-size:10px; color:#a8998a; margin-top:1px; }
  .ff-logout-btn { padding:6px 14px; border:1px solid #ece6dc; background:#fff; border-radius:20px; font-size:11px; font-family:'DM Sans',sans-serif; cursor:pointer; color:#8a7a6a; font-weight:600; transition:all .18s; white-space:nowrap; }
  .ff-logout-btn:hover { border-color:#c8a55a; color:#8a5820; background:rgba(200,165,90,.06); }
  .ff-tabs { display:flex; background:#fff; border-bottom:1px solid #ece6dc; padding:0 28px; flex-shrink:0; overflow-x:auto; }
  .ff-tab { padding:13px 18px; border:none; border-bottom:2px solid transparent; background:transparent; font-family:inherit; font-size:12px; font-weight:500; color:#9a8a7a; cursor:pointer; transition:all .18s; display:flex; align-items:center; gap:7px; letter-spacing:.03em; white-space:nowrap; flex-shrink:0; }
  .ff-tab.active { color:#8a5820; border-bottom-color:#c8a55a; }
  .ff-tab-badge { min-width:18px; height:18px; padding:0 5px; border-radius:9px; background:rgba(200,165,90,.18); color:#8a5820; font-size:9px; font-weight:700; display:flex; align-items:center; justify-content:center; }
  .ff-tab-new { font-size:7px; padding:1px 5px; background:linear-gradient(135deg,#c8a55a,#e8c87a); color:#1a0f00; border-radius:6px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
  .ff-chat { flex:1; overflow-y:auto; padding:28px 28px 12px; }
  .ff-msg { animation:fadeUp .25s ease both; margin-bottom:22px; display:flex; gap:12px; }
  .ff-msg.user { flex-direction:row-reverse; }
  .ff-avatar { width:32px; height:32px; border-radius:50%; flex-shrink:0; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:600; margin-top:2px; }
  .ff-avatar.bot { background:linear-gradient(135deg,#1a0f00,#3a2010); color:#c8a55a; }
  .ff-avatar.user { background:linear-gradient(135deg,#c8a55a,#e8c87a); color:#1a0f00; }
  .ff-bubble { max-width:780px; }
  .ff-bubble.user { align-items:flex-end; }
  .ff-sender { font-size:9px; letter-spacing:.22em; font-weight:600; text-transform:uppercase; color:#b0a090; margin-bottom:6px; }
  .ff-sender.user-sender { text-align:right; color:#c8a55a; }
  .ff-text { padding:14px 18px; border-radius:12px; font-size:13.5px; line-height:1.75; color:#2c1f0f; }
  .ff-text.bot { background:#fff; border:1px solid #ece6dc; border-radius:4px 12px 12px 12px; box-shadow:0 2px 12px rgba(0,0,0,.05); }
  .ff-text.user { background:linear-gradient(135deg,#8a5820,#c8a55a); color:#fff; border-radius:12px 4px 12px 12px; box-shadow:0 4px 18px rgba(138,88,32,.25); }
  .ff-typing { display:flex; align-items:center; gap:5px; padding:14px 18px; background:#fff; border:1px solid #ece6dc; border-radius:4px 12px 12px 12px; width:fit-content; }
  .ff-dot-t { width:6px; height:6px; border-radius:50%; background:#c8a55a; animation:blink 1.2s ease infinite; }
  .ff-dot-t:nth-child(2){animation-delay:.2s} .ff-dot-t:nth-child(3){animation-delay:.4s}
  .ff-chips { display:flex; gap:7px; padding:6px 28px 14px; flex-wrap:wrap; flex-shrink:0; overflow-x:auto; }
  .ff-chip { padding:7px 14px; border:1px solid #ddd3c2; background:#fff; font-family:inherit; font-size:12px; color:#7a6a5a; cursor:pointer; border-radius:20px; transition:all .18s; white-space:nowrap; display:flex; align-items:center; gap:6px; flex-shrink:0; }
  .ff-chip:hover { border-color:#c8a55a; color:#8a5820; background:rgba(200,165,90,.06); transform:translateY(-1px); }
  .ff-input-bar { display:flex; gap:10px; padding:12px 28px 18px; background:#fff; border-top:1px solid #ece6dc; flex-shrink:0; align-items:center; }
  .ff-input { flex:1; padding:12px 16px; border:1px solid #ddd3c2; background:#faf7f3; font-family:inherit; font-size:13.5px; color:#2c1f0f; outline:none; border-radius:8px; transition:border-color .2s,box-shadow .2s; }
  .ff-input:focus { border-color:#c8a55a; box-shadow:0 0 0 3px rgba(200,165,90,.12); background:#fff; }
  .ff-input::placeholder { color:#c4b4a4; }
  .ff-send { padding:0 24px; height:46px; background:#1a0f00; border:none; color:#c8a55a; font-family:inherit; font-size:11px; font-weight:700; letter-spacing:.22em; text-transform:uppercase; cursor:pointer; border-radius:8px; transition:all .2s; display:flex; align-items:center; gap:8px; white-space:nowrap; }
  .ff-send:hover:not(:disabled) { background:#c8a55a; color:#1a0f00; }
  .ff-send:disabled { opacity:.4; cursor:not-allowed; }
  .ff-section-label { font-size:9px; letter-spacing:.28em; text-transform:uppercase; font-weight:700; margin-bottom:12px; margin-top:18px; }
  .ff-prod-tabs { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:14px; padding-bottom:12px; border-bottom:1px solid #ece6dc; }
  .ff-prod-tab { padding:5px 12px; border-radius:20px; border:1px solid #ddd3c2; background:transparent; font-family:inherit; font-size:11px; color:#8a7a6a; cursor:pointer; transition:all .15s; display:flex; align-items:center; gap:5px; }
  .ff-prod-tab.active { background:rgba(200,165,90,.14); border-color:#c8a55a; color:#8a5820; font-weight:600; }
  .ff-prod-tab-count { font-size:9px; padding:1px 5px; border-radius:8px; font-weight:700; }
  .ff-prod-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(148px,1fr)); gap:10px; }
  .ff-prod-card { display:block; text-decoration:none; background:#fff; border:1px solid #ece6dc; border-radius:10px; overflow:hidden; transition:transform .2s,box-shadow .2s; }
  .ff-prod-card:hover { transform:translateY(-3px); box-shadow:0 10px 28px rgba(0,0,0,.1); }
  .ff-prod-img { height:148px; background:#f7f3ee; display:flex; align-items:center; justify-content:center; overflow:hidden; position:relative; }
  .ff-prod-source { position:absolute; bottom:6px; left:6px; background:rgba(26,15,0,.65); backdrop-filter:blur(4px); padding:2px 7px; border-radius:3px; font-size:8px; color:#e8d8b8; letter-spacing:.06em; text-transform:uppercase; }
  .ff-prod-info { padding:10px 12px 14px; }
  .ff-prod-title { font-size:11.5px; color:#3a2e24; line-height:1.4; margin-bottom:7px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; min-height:30px; }
  .ff-prod-price { font-size:14px; font-weight:700; color:#8a5820; }
  .ff-routine { margin-top:16px; padding:18px 20px; background:rgba(200,165,90,.04); border:1px solid rgba(200,165,90,.2); border-radius:12px; }
  .ff-routine-grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:14px; }
  .ff-routine-col-title { font-size:9px; letter-spacing:.22em; text-transform:uppercase; color:#8a7a6a; font-weight:600; margin-bottom:10px; }
  .ff-routine-step { display:flex; gap:10px; margin-bottom:8px; align-items:flex-start; }
  .ff-routine-num { font-size:9px; color:#c8a55a; font-weight:700; min-width:14px; padding-top:3px; }
  .ff-routine-text { font-size:12px; color:#4a3828; line-height:1.55; }
  .ff-wardrobe-item { display:flex; align-items:center; gap:10px; padding:10px 14px; background:rgba(111,200,151,.07); border:1px solid rgba(111,200,151,.2); border-radius:10px; min-width:180px; }
  .ff-wardrobe-img { width:52px; height:52px; object-fit:cover; border-radius:7px; background:#f0ece6; flex-shrink:0; }
  .ff-wardrobe-emoji { width:52px; height:52px; border-radius:7px; background:rgba(200,165,90,.1); display:flex; align-items:center; justify-content:center; font-size:22px; flex-shrink:0; }
  .ff-wardrobe-name { font-size:12px; font-weight:600; color:#1e5035; }
  .ff-wardrobe-meta { font-size:10px; color:#6a9278; margin-top:2px; }
  .ff-dual-options { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:16px; max-width:780px; }
  .ff-option-card { border-radius:12px; overflow:hidden; border:1px solid #ece6dc; }
  .ff-option-header { padding:10px 16px; display:flex; align-items:center; gap:8px; font-size:10px; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
  .ff-option-header.closet { background:rgba(111,200,151,.12); color:#1e5035; border-bottom:1px solid rgba(111,200,151,.2); }
  .ff-option-header.new { background:rgba(200,165,90,.1); color:#8a5820; border-bottom:1px solid rgba(200,165,90,.2); }
  .ff-option-body { padding:12px 14px; background:#fff; }
  .ff-event-badge { display:inline-flex; align-items:center; gap:7px; padding:5px 14px; border-radius:20px; margin-bottom:14px; background:rgba(200,165,90,.1); border:1px solid rgba(200,165,90,.3); font-size:11px; font-weight:600; color:#8a5820; letter-spacing:.04em; }
  .ff-combo { border:1px solid #ece6dc; border-radius:10px; overflow:hidden; margin-bottom:12px; }
  .ff-combo-header { padding:10px 14px; border-bottom:1px solid rgba(0,0,0,.05); display:flex; justify-content:space-between; align-items:center; }
  .ff-combo-body { padding:12px 14px; }
  .ff-gap-section { margin-top:16px; max-width:780px; }
  .ff-gap-card { border:1px solid #ece6dc; border-radius:10px; background:#fff; padding:14px 16px; margin-bottom:10px; display:flex; align-items:flex-start; gap:12px; border-left:3px solid rgba(200,165,90,.3); transition:box-shadow .18s; }
  .ff-gap-card:hover { box-shadow:0 4px 14px rgba(0,0,0,.06); }
  .ff-gap-icon { font-size:22px; flex-shrink:0; }
  .ff-gap-event { font-size:12.5px; font-weight:600; color:#2c1f0f; margin-bottom:4px; }
  .ff-gap-missing { display:flex; gap:6px; flex-wrap:wrap; }
  .ff-gap-pill { font-size:10px; padding:3px 9px; border-radius:10px; font-weight:600; }
  .ff-gap-pill.high { background:rgba(220,50,50,.1); color:#c02020; }
  .ff-gap-pill.low { background:rgba(200,165,90,.12); color:#8a5820; }
  .ff-ready-grid { display:flex; gap:7px; flex-wrap:wrap; margin-top:14px; }
  .ff-ready-pill { padding:5px 12px; background:rgba(111,200,151,.12); border:1px solid rgba(111,200,151,.3); border-radius:20px; font-size:11px; font-weight:600; color:#1e5035; }
  .ff-closet { flex:1; overflow-y:auto; padding:24px 28px; }
  .ff-closet-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:12px; margin-top:14px; }
  .ff-closet-card { border:1px solid #ece6dc; border-radius:10px; overflow:hidden; background:#fff; transition:transform .2s,box-shadow .2s; cursor:pointer; }
  .ff-closet-card:hover { transform:translateY(-2px); box-shadow:0 6px 20px rgba(0,0,0,.08); }
  .ff-closet-card-img { height:130px; background:#f7f3ee; display:flex; align-items:center; justify-content:center; overflow:hidden; position:relative; }
  .ff-closet-del { position:absolute; top:6px; right:6px; width:24px; height:24px; background:rgba(200,50,50,.85); border:none; border-radius:50%; color:#fff; font-size:11px; cursor:pointer; display:flex; align-items:center; justify-content:center; opacity:0; transition:opacity .2s; }
  .ff-closet-card:hover .ff-closet-del { opacity:1; }
  .ff-closet-card-info { padding:8px 10px 11px; }
  .ff-closet-card-name { font-size:11px; font-weight:600; color:#2c1f0f; }
  .ff-closet-card-meta { font-size:10px; color:#a8998a; margin-top:2px; }
  .ff-upload-zone { border:1.5px dashed #ddd3c2; border-radius:12px; padding:32px 20px; text-align:center; cursor:pointer; transition:all .2s; background:#faf7f3; }
  .ff-upload-zone:hover { border-color:#c8a55a; background:rgba(200,165,90,.04); }
  .ff-event-grid { display:flex; gap:7px; flex-wrap:wrap; margin-top:12px; }
  .ff-event-chip { padding:7px 13px; border:1px solid #ddd3c2; background:#fff; border-radius:20px; font-family:inherit; font-size:11.5px; color:#6a5a4a; cursor:pointer; transition:all .18s; display:flex; align-items:center; gap:6px; }
  .ff-event-chip:hover,.ff-event-chip.active { border-color:#c8a55a; color:#8a5820; background:rgba(200,165,90,.08); }
  .ff-btn-primary { padding:11px 28px; background:#1a0f00; color:#c8a55a; border:none; border-radius:8px; font-family:inherit; font-size:12px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; cursor:pointer; transition:all .2s; }
  .ff-btn-primary:hover:not(:disabled) { background:#c8a55a; color:#1a0f00; }
  .ff-btn-primary:disabled { opacity:.4; cursor:not-allowed; }
  .ff-outfit-strip { display:flex; gap:10px; overflow-x:auto; padding-bottom:8px; margin-top:14px; }
  .ff-outfit-strip::-webkit-scrollbar { height:3px; }
  .ff-outfit-strip::-webkit-scrollbar-thumb { background:#ddd3c2; border-radius:3px; }
  .ff-multi-outfit-card { min-width:220px; max-width:240px; flex-shrink:0; border:1.5px solid #ece6dc; border-radius:14px; overflow:hidden; background:#fff; transition:all .2s; }
  .ff-multi-outfit-card:hover { border-color:#c8a55a; box-shadow:0 8px 24px rgba(200,165,90,.15); transform:translateY(-2px); }
  .ff-multi-outfit-card.best { border-color:rgba(111,200,151,.5); }
  .ff-outfit-card-header { padding:9px 12px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #f0ece6; }
  .ff-outfit-card-num { font-size:9px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:#8a7a6a; }
  .ff-outfit-card-score { font-size:9px; font-weight:700; padding:2px 8px; border-radius:10px; }
  .ff-outfit-card-score.score3 { background:rgba(111,200,151,.15); color:#1e5035; }
  .ff-outfit-card-score.score2 { background:rgba(200,165,90,.15); color:#8a5820; }
  .ff-outfit-card-score.score1 { background:rgba(184,168,152,.15); color:#6a5a4a; }
  .ff-outfit-items-row { display:flex; gap:5px; padding:10px 10px 6px; flex-wrap:wrap; }
  .ff-outfit-item-thumb { display:flex; flex-direction:column; align-items:center; gap:3px; }
  .ff-outfit-item-img { width:58px; height:58px; border-radius:8px; object-fit:cover; background:#f7f3ee; border:1px solid #ece6dc; }
  .ff-outfit-item-emoji { width:58px; height:58px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:20px; border:1px solid #ece6dc; background:rgba(200,165,90,.06); }
  .ff-outfit-item-label { font-size:9px; color:#a8998a; text-align:center; max-width:58px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .ff-outfit-tip { padding:8px 12px 12px; font-size:11px; color:#5a4838; font-style:italic; line-height:1.5; border-top:1px solid #f5f1eb; }
  .ff-plan-event-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(108px,1fr)); gap:8px; margin-top:14px; }
  .ff-plan-event-btn { padding:14px 8px 12px; border:1.5px solid #ece6dc; background:#fff; border-radius:14px; font-family:inherit; cursor:pointer; transition:all .22s; display:flex; flex-direction:column; align-items:center; gap:6px; }
  .ff-plan-event-btn:hover { border-color:#c8a55a; background:rgba(200,165,90,.05); transform:translateY(-3px); box-shadow:0 8px 20px rgba(200,165,90,.15); }
  .ff-plan-event-btn.active { border-color:#c8a55a; background:linear-gradient(135deg,rgba(200,165,90,.12),rgba(200,165,90,.04)); box-shadow:0 4px 16px rgba(200,165,90,.2); }
  .ff-plan-event-icon { font-size:24px; line-height:1; }
  .ff-plan-event-label { font-size:10px; font-weight:600; color:#5a4838; text-align:center; letter-spacing:.02em; }
  .ff-mm-combo { border:1px solid #ece6dc; border-radius:12px; overflow:hidden; margin-bottom:12px; background:#fff; transition:all .2s; }
  .ff-mm-combo:hover { transform:translateY(-2px); box-shadow:0 6px 20px rgba(0,0,0,.08); border-color:#c8a55a; }
  .ff-mm-combo-header { padding:10px 14px; display:flex; justify-content:space-between; align-items:center; background:rgba(250,247,243,.9); border-bottom:1px solid #f0ece6; }
  .ff-mm-combo-body { padding:12px 14px; display:flex; align-items:flex-start; gap:10px; flex-wrap:wrap; }
  .ff-style-card { padding:16px 18px; background:#fff; border:1px solid #ece6dc; border-radius:14px; margin-top:14px; max-width:680px; }
  .ff-style-header { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
  .ff-style-icon { font-size:26px; }
  .ff-style-name { font-family:'Cormorant Garamond',serif; font-size:20px; color:#1a0f00; }
  .ff-style-pieces { display:flex; gap:7px; flex-wrap:wrap; margin-top:10px; }
  .ff-style-pill { font-size:11px; padding:4px 11px; border-radius:14px; font-weight:600; }
  .ff-style-pill.piece { background:rgba(200,165,90,.1); color:#8a5820; border:1px solid rgba(200,165,90,.2); }
  .ff-style-pill.avoid { background:rgba(200,50,50,.07); color:#c02020; border:1px solid rgba(200,50,50,.15); }
  .ff-outfit-warning { padding:8px 12px; background:rgba(255,165,0,.08); border:1px solid rgba(255,165,0,.25); border-radius:8px; font-size:11.5px; color:#8a5820; margin-top:8px; display:flex; gap:8px; align-items:flex-start; }
  .ff-tryon-container { flex:1; overflow:auto; padding:24px 28px; }
  .ff-scheduler { flex:1; overflow-y:auto; }
  .ff-full-tab { flex:1; overflow-y:auto; }
  .ff-feature-tab { flex:1; overflow-y:auto; padding:0 28px 24px; }
  @media (max-width: 640px) {
    .ff-header { padding:0 16px; }
    .ff-chat, .ff-chips, .ff-input-bar, .ff-closet, .ff-scheduler, .ff-tryon-container, .ff-full-tab, .ff-feature-tab { padding-left:16px; padding-right:16px; }
    .ff-tabs { padding-left:16px; }
    .ff-routine-grid { grid-template-columns:1fr; }
    .ff-prod-grid { grid-template-columns:repeat(2,1fr); }
    .ff-dual-options { grid-template-columns:1fr; }
  }
`;

// ── Sub-components ────────────────────────────────────────────────────────────

const FormattedText = ({ text }) => {
  if (!text) return null;
  return (
    <div style={{ fontSize: 13.5, lineHeight: 1.75, color: "inherit" }}>
      {text.split("\n").map((line, i) => (
        <div key={i} style={{ marginBottom: line.trim() ? 3 : 0 }}>
          {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
            part.startsWith("**") && part.endsWith("**")
              ? <strong key={j} style={{ fontWeight: 700 }}>{part.slice(2, -2)}</strong>
              : <span key={j}>{part}</span>
          )}
        </div>
      ))}
    </div>
  );
};

const ProductCard = ({ p, userId }) => {
  const [err, setErr] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const src = proxyImage(p.image);
  const label = (p.source || "shop").replace(/www\.|\\.com|\\.in/g, "").slice(0, 12);
  return (
    <div style={{ position: "relative" }}>
      <a href={p.link} target="_blank" rel="noreferrer" className="ff-prod-card">
        <div className="ff-prod-img">
          {!loaded && !err && src && (
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(90deg,#f0ebe4,#e8e0d4,#f0ebe4)", backgroundSize: "200% 100%", animation: "shimmer 1.4s infinite" }} />
          )}
          {!err && src
            ? <img src={src} alt={p.title}
                style={{ width: "100%", height: "100%", objectFit: "contain", opacity: loaded ? 1 : 0, transition: "opacity .25s" }}
                onLoad={() => setLoaded(true)} onError={() => { setErr(true); setLoaded(true); }} crossOrigin="anonymous" />
            : <div style={{ fontSize: 30, opacity: .12 }}>◈</div>
          }
          <div className="ff-prod-source">{label}</div>
        </div>
        <div className="ff-prod-info">
          <div className="ff-prod-title">{p.title}</div>
          <div className="ff-prod-price">{p.price || "View Price"}</div>
        </div>
      </a>
      {userId && (
        <div style={{ padding: "0 10px 10px" }}><SaveButton product={p} userId={userId} /></div>
      )}
    </div>
  );
};

const ProductGrid = ({ products: initialProducts, label, userId, user, event: eventId }) => {
  const [products, setProducts] = useState(initialProducts || {});

  // Sync when parent updates
  useEffect(() => {
    setProducts(initialProducts || {});
  }, [JSON.stringify(initialProducts)]);

  const handleReplaced = (cat, newProds) => {
    setProducts(prev => ({ ...prev, [cat]: newProds }));
  };

  const allCats = Object.keys(products || {}).filter(k => (products[k]?.length || 0) > 0);
  const sorted = [...allCats].sort((a, b) => {
    const aS = SKINCARE_CATS.has(a), bS = SKINCARE_CATS.has(b);
    if (aS && !bS) return 1; if (!aS && bS) return -1;
    const aI = FASHION_ORDER.indexOf(a), bI = FASHION_ORDER.indexOf(b);
    if (aI >= 0 && bI >= 0) return aI - bI;
    if (aI >= 0) return -1; if (bI >= 0) return 1;
    return 0;
  });

  const [tab, setTab] = useState(sorted[0] || "");
  useEffect(() => {
    if (sorted.length && !sorted.includes(tab)) setTab(sorted[0]);
  }, [JSON.stringify(sorted)]);

  if (!sorted.length) return null;

  return (
    <div style={{ marginTop: 16, width: "100%", maxWidth: 780 }}>
      {label && <div className="ff-section-label" style={{ color: "#8a7a6a" }}>{label}</div>}
      <div className="ff-prod-tabs">
        {sorted.map(c => {
          const isActive = tab === c;
          return (
            <button key={c} className={`ff-prod-tab${isActive ? " active" : ""}`} onClick={() => setTab(c)}>
              <span style={{ fontSize: 13 }}>{CAT_ICONS[c] || "◈"}</span>
              {CAT_LABELS[c] || c}
              <span className="ff-prod-tab-count" style={{ background: isActive ? "#c8a55a" : "#ece6dc", color: isActive ? "#fff" : "#8a7a6a" }}>
                {products[c]?.length}
              </span>
            </button>
          );
        })}
      </div>
      <div className="ff-prod-grid">
        {(products[tab] || []).slice(0, 6).map((p, i) => (
          <ProductCard key={i} p={p} userId={userId} />
        ))}
      </div>
      {/* Replace Item + Learning System */}
      <ReplaceItem
        category={tab}
        currentProducts={products[tab] || []}
        userContext={user}
        userId={userId}
        event={eventId}
        onReplaced={handleReplaced}
      />
    </div>
  );
};

const RoutineCard = ({ routine }) => {
  if (!routine?.morning?.length && !routine?.night?.length) return null;
  return (
    <div className="ff-routine">
      <div className="ff-section-label" style={{ color: "#c8a55a" }}>✦ Your Personalized Routine</div>
      <div className="ff-routine-grid">
        {["morning","night"].filter(t => routine[t]?.length > 0).map(t => (
          <div key={t}>
            <div className="ff-routine-col-title">{t === "morning" ? "☀ Morning" : "◑ Night"}</div>
            {routine[t].map((step, i) => (
              <div key={i} className="ff-routine-step">
                <span className="ff-routine-num">{i + 1}</span>
                <span className="ff-routine-text">{step}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

// ── FIXED WardrobeItemCard ────────────────────────────────────────────────────
// Uses resolveItemImageUrl() to correctly handle both absolute and relative paths.
const WardrobeItemCard = ({ item }) => {
  const [imgErr, setImgErr] = useState(false);
  if (!item) return null;

  const src = resolveItemImageUrl(item.image_url);
  const swatchColor = COLOR_SWATCHES[(item.color || "").toLowerCase().split(" ").pop()] || COLOR_SWATCHES[item.color?.toLowerCase()] || "#c8a55a";
  const showImg = src && !imgErr;

  return (
    <div className="ff-wardrobe-item">
      {showImg
        ? <img
            src={src}
            alt={item.item_name}
            className="ff-wardrobe-img"
            onError={() => setImgErr(true)}
            crossOrigin="anonymous"
          />
        : <div className="ff-wardrobe-emoji" style={{ background: swatchColor + "22", border: `2px solid ${swatchColor}44` }}>
            <span style={{ fontSize: 20 }}>{CLOSET_CAT_ICONS[item.category] || "👕"}</span>
          </div>
      }
      <div>
        <div className="ff-wardrobe-name">{item.item_name}</div>
        <div className="ff-wardrobe-meta" style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: swatchColor, flexShrink: 0 }} />
          {item.color} · {item.formality || "casual"}
        </div>
      </div>
    </div>
  );
};

// ── FIXED OutfitItemThumb ─────────────────────────────────────────────────────
const OutfitItemThumb = ({ cat, item }) => {
  const [imgErr, setImgErr] = useState(false);
  if (!item) return null;

  const src = resolveItemImageUrl(item.image_url);
  const swatchColor = COLOR_SWATCHES[(item.color || "").toLowerCase().split(" ").pop()] || COLOR_SWATCHES[item.color?.toLowerCase()] || "#c8a55a";

  return (
    <div className="ff-outfit-item-thumb">
      {src && !imgErr
        ? <img
            src={src}
            alt={item.item_name}
            className="ff-outfit-item-img"
            onError={() => setImgErr(true)}
            crossOrigin="anonymous"
          />
        : <div className="ff-outfit-item-emoji" style={{ background: swatchColor + "18", borderColor: swatchColor + "44" }}>
            {CLOSET_CAT_ICONS[item.category] || CAT_ICONS[cat] || "👕"}
          </div>
      }
      <span className="ff-outfit-item-label">{item.item_name || cat}</span>
    </div>
  );
};

const OutfitValidationBanner = ({ items, eventId }) => {
  if (!eventId || !items || items.length === 0) return null;
  const { warnings } = validateOutfitForEvent(items, eventId);
  if (warnings.length === 0) return null;
  return (
    <div className="ff-outfit-warning">
      <span>⚠️</span>
      <div>
        <strong style={{ display: "block", marginBottom: 3, fontSize: 11 }}>Outfit Note</strong>
        {warnings.map((w, i) => <div key={i} style={{ fontSize: 11, opacity: .9 }}>{w}</div>)}
      </div>
    </div>
  );
};

const MultiOutfitCard = ({ outfit, idx, isFirst, eventId, user }) => {
  const { items = {}, color_score = 2, color_label = "Good combo", styling_tip } = outfit;
  const scoreClass = color_score >= 3 ? "score3" : color_score >= 2 ? "score2" : "score1";
  const parts = Object.entries(items).filter(([, v]) => v);
  const allItems = Object.values(items).filter(Boolean);
  return (
    <div className={`ff-multi-outfit-card${isFirst ? " best" : ""}`}>
      <div className="ff-outfit-card-header">
        <span className="ff-outfit-card-num">{isFirst ? "✦ Best Look" : `Look #${idx + 1}`}</span>
        <span className={`ff-outfit-card-score ${scoreClass}`}>{color_label}</span>
      </div>
      <div className="ff-outfit-items-row">
        {parts.map(([cat, item], i) => <OutfitItemThumb key={i} cat={cat} item={item} />)}
      </div>
      {styling_tip && <div className="ff-outfit-tip">"{styling_tip}"</div>}
      {eventId && (
        <div style={{ padding: "0 8px 8px" }}>
          <OutfitValidationBanner items={allItems} eventId={eventId} />
        </div>
      )}
      <div style={{ padding: "4px 12px 12px" }}>
        <OutfitImageGenerator
          outfit={outfit}
          gender={user?.gender || "male"}
          skinTone={user?.skinTone || "medium"}
          event={eventId || "casual"}
        />
      </div>
    </div>
  );
};

const MultiOutfitResult = ({ result, eventId, user }) => {
  if (!result) return null;
  const { outfits = [], event_icon, event_vibe, outfit_plan, missing_categories = [], missing_products = {} } = result;
  const hasMissingProducts = Object.keys(missing_products).length > 0;
  return (
    <div style={{ marginTop: 16, maxWidth: 780 }}>
      {event_vibe && <div className="ff-event-badge">{event_icon} {event_vibe}</div>}
      {outfit_plan && (
        <div style={{ fontSize: 13, color: "#2c1f0f", lineHeight: 1.75, marginBottom: 12, padding: "12px 16px", background: "rgba(200,165,90,.04)", borderLeft: "3px solid #c8a55a", borderRadius: "0 8px 8px 0" }}>
          {outfit_plan}
        </div>
      )}
      {outfits.length > 0 && (
        <>
          <div className="ff-section-label" style={{ color: "#6fc897" }}>✓ Your Outfit Options From Wardrobe</div>
          <div className="ff-outfit-strip">
            {outfits.map((outfit, i) => (
              <MultiOutfitCard key={i} outfit={outfit} idx={i} isFirst={i === 0} eventId={eventId} user={user} />
            ))}
          </div>
        </>
      )}
      {missing_categories.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div className="ff-section-label" style={{ color: "#c8a55a" }}>🛍 Shop To Complete This Look</div>
          <div style={{ display: "flex", gap: 7, flexWrap: "wrap", marginBottom: hasMissingProducts ? 16 : 0 }}>
            {missing_categories.map((c, i) => (
              <span key={i} style={{ fontSize: 11.5, padding: "5px 13px", background: "rgba(200,165,90,.1)", color: "#8a5820", borderRadius: 16, fontWeight: 600, border: "1px solid rgba(200,165,90,.25)", display: "flex", alignItems: "center", gap: 5 }}>
                {CAT_ICONS[c] || "◈"} {CAT_LABELS[c] || c}
              </span>
            ))}
          </div>
          {hasMissingProducts && <ProductGrid products={missing_products} />}
        </div>
      )}
    </div>
  );
};

const StyleAestheticCard = ({ styleName }) => {
  const aesthetic = STYLE_AESTHETICS[styleName?.toLowerCase()];
  if (!aesthetic) return null;
  return (
    <div className="ff-style-card" style={{ animation: "slideUp .3s ease both" }}>
      <div className="ff-style-header">
        <span className="ff-style-icon">{aesthetic.icon}</span>
        <div>
          <div className="ff-style-name">{styleName?.replace(/\b\w/g, c => c.toUpperCase())} Aesthetic</div>
          <div style={{ fontSize: 11, color: "#a8998a", marginTop: 2 }}>Style Guide</div>
        </div>
      </div>
      <div style={{ fontSize: 12.5, color: "#4a3828", lineHeight: 1.65, marginBottom: 12 }}>{aesthetic.desc}</div>
      <div>
        <div style={{ fontSize: 9, letterSpacing: ".2em", color: "#8a7a6a", textTransform: "uppercase", fontWeight: 700, marginBottom: 6 }}>Key Colors</div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
          {aesthetic.colors.map((c, i) => {
            const hex = COLOR_SWATCHES[c] || "#c8a55a";
            return (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <span style={{ width: 14, height: 14, borderRadius: "50%", background: hex, border: "1.5px solid rgba(0,0,0,.1)", display: "inline-block" }} />
                <span style={{ fontSize: 10, color: "#5a4838", fontWeight: 500 }}>{c}</span>
              </div>
            );
          })}
        </div>
        <div style={{ fontSize: 9, letterSpacing: ".2em", color: "#8a7a6a", textTransform: "uppercase", fontWeight: 700, marginBottom: 6 }}>Essential Pieces</div>
        <div className="ff-style-pieces">
          {aesthetic.pieces.map((p, i) => <span key={i} className="ff-style-pill piece">{p}</span>)}
        </div>
        <div style={{ fontSize: 9, letterSpacing: ".2em", color: "#a8998a", textTransform: "uppercase", fontWeight: 700, margin: "10px 0 6px" }}>Avoid</div>
        <div className="ff-style-pieces">
          {aesthetic.avoid.map((p, i) => <span key={i} className="ff-style-pill avoid">✕ {p}</span>)}
        </div>
      </div>
    </div>
  );
};

const DualOutfitResult = ({ closetResult, newProducts, eventLabel, gender, eventId, userId }) => {
  if (!closetResult && !newProducts) return null;
  const available = closetResult?.available_items || {};
  const availList = Object.values(available).filter(Boolean);
  const missing   = closetResult?.missing_categories || [];
  const isMale    = !["female","women","woman","girl","f"].includes((gender||"").toLowerCase());
  const newProdsFiltered = newProducts ? Object.fromEntries(
    Object.entries(newProducts).filter(([k]) => {
      if (isMale && ["necklace","earrings"].includes(k)) return false;
      return true;
    })
  ) : null;
  return (
    <div style={{ marginTop: 16, maxWidth: 780 }}>
      {eventLabel && <div className="ff-event-badge">{eventLabel}</div>}
      <div className="ff-dual-options">
        <div className="ff-option-card">
          <div className="ff-option-header closet">✓ From Your Closet</div>
          <div className="ff-option-body">
            {closetResult?.outfit_plan && (
              <div style={{ fontSize: 12.5, color: "#2c1f0f", lineHeight: 1.7, marginBottom: 12, padding: "10px 12px", background: "rgba(111,200,151,.06)", borderLeft: "3px solid #6fc897", borderRadius: "0 6px 6px 0" }}>
                {closetResult.outfit_plan}
              </div>
            )}
            {availList.length > 0
              ? <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                  {availList.map((item, i) => <WardrobeItemCard key={i} item={item} />)}
                </div>
              : <div style={{ fontSize: 12, color: "#a8998a", padding: "8px 0" }}>No matching items found. Upload more clothes!</div>
            }
            {eventId && availList.length > 0 && <OutfitValidationBanner items={availList} eventId={eventId} />}
            {missing.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 10, letterSpacing: ".1em", color: "#c8a55a", fontWeight: 700, textTransform: "uppercase", marginBottom: 5 }}>Missing</div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {missing.map((c, i) => (
                    <span key={i} style={{ fontSize: 10.5, padding: "3px 9px", background: "rgba(200,165,90,.1)", color: "#8a5820", borderRadius: 10, fontWeight: 600 }}>
                      {CAT_ICONS[c] || "◈"} {CAT_LABELS[c] || c}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="ff-option-card">
          <div className="ff-option-header new">✦ Shop New Outfit</div>
          <div className="ff-option-body">
            <div style={{ fontSize: 12, color: "#7a6a5a", marginBottom: 10, lineHeight: 1.5 }}>Fresh picks curated for your skin tone &amp; this event</div>
            {newProdsFiltered && Object.keys(newProdsFiltered).length > 0
              ? <ProductGrid products={newProdsFiltered} userId={userId} />
              : <div style={{ fontSize: 12, color: "#a8998a" }}>Loading picks...</div>
            }
          </div>
        </div>
      </div>
    </div>
  );
};

const ClosetFoundItems = ({ items }) => {
  if (!items?.length) return null;
  return (
    <div style={{ marginTop: 16, maxWidth: 780 }}>
      <div className="ff-section-label" style={{ color: "#6fc897" }}>✓ Found in Your Wardrobe</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 9 }}>
        {items.map((item, i) => <WardrobeItemCard key={i} item={item} />)}
      </div>
    </div>
  );
};

const GapAnalysisDisplay = ({ gapData }) => {
  const [shopFor, setShopFor] = useState(null);
  const [shopProds, setShopProds] = useState({});
  if (!gapData) return null;
  const { gaps = {}, ready_events = [], high_priority_gaps = [] } = gapData;
  const gapEntries = Object.entries(gaps);
  return (
    <div className="ff-gap-section">
      <div className="ff-section-label" style={{ color: "#8a5820" }}>📊 Your Style Gap Report</div>
      {gapEntries.length === 0
        ? <div style={{ fontSize: 13, color: "#6fc897", fontWeight: 600, padding: "12px 0" }}>✦ You're fully equipped for all events!</div>
        : <>
            {high_priority_gaps.length > 0 && (
              <div style={{ fontSize: 11.5, color: "#c84040", background: "rgba(200,64,64,.06)", border: "1px solid rgba(200,64,64,.15)", borderRadius: 8, padding: "8px 14px", marginBottom: 14, fontWeight: 500 }}>
                🚨 High priority: {high_priority_gaps.slice(0, 4).join(", ")} — missing 2+ key items
              </div>
            )}
            {gapEntries.map(([event, info]) => (
              <div key={event} className="ff-gap-card" style={{ borderLeft: info.urgency === "high" ? "3px solid rgba(200,64,64,.4)" : "3px solid rgba(200,165,90,.3)" }}>
                <div className="ff-gap-icon">{info.icon}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                    <div className="ff-gap-event">
                      {event.charAt(0).toUpperCase() + event.slice(1)}
                      <span style={{ fontSize: 10.5, color: "#a8998a", fontWeight: 400, marginLeft: 6 }}>{info.vibe}</span>
                    </div>
                    <button onClick={() => {
                      const links = {};
                      (info.missing || []).forEach(m => {
                        const q = (info.search_cats || {})[m] || `${m} India`;
                        links[m] = { query: q, link: `https://www.myntra.com/search?rawQuery=${encodeURIComponent(q)}` };
                      });
                      setShopFor(shopFor === event ? null : event);
                      setShopProds(p => ({ ...p, [event]: links }));
                    }} style={{ fontSize: 10, padding: "3px 10px", border: "1px solid #c8a55a", borderRadius: 12, background: "rgba(200,165,90,.08)", color: "#8a5820", cursor: "pointer", fontFamily: "inherit", fontWeight: 600 }}>
                      {shopFor === event ? "Hide" : "🛍 Shop"}
                    </button>
                  </div>
                  <div className="ff-gap-missing">
                    {(info.missing || []).map((m, i) => (
                      <span key={i} className={`ff-gap-pill ${info.urgency}`}>{CAT_ICONS[m] || "◈"} {CAT_LABELS[m] || m}</span>
                    ))}
                  </div>
                  {shopFor === event && shopProds[event] && (
                    <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                      {Object.entries(shopProds[event]).map(([cat, data]) => (
                        <a key={cat} href={data.link} target="_blank" rel="noreferrer"
                          style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 12px", background: "#fff", border: "1px solid #ece6dc", borderRadius: 8, textDecoration: "none" }}>
                          <span style={{ fontSize: 14 }}>{CAT_ICONS[cat] || "◈"}</span>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 11.5, color: "#2c1f0f", fontWeight: 600 }}>{CAT_LABELS[cat] || cat}</div>
                            <div style={{ fontSize: 10, color: "#a8998a" }}>{data.query?.slice(0, 50)}...</div>
                          </div>
                          <span style={{ fontSize: 10, color: "#c8a55a", fontWeight: 700 }}>Shop →</span>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </>
      }
      {ready_events.length > 0 && (
        <>
          <div className="ff-section-label" style={{ color: "#6fc897", marginTop: 20 }}>✓ Events You're Ready For ({ready_events.length})</div>
          <div className="ff-ready-grid">
            {ready_events.map((ev, i) => {
              const evObj = ALL_EVENTS.find(e => e.id === ev);
              return <span key={i} className="ff-ready-pill">{evObj?.icon || "✦"} {ev}</span>;
            })}
          </div>
        </>
      )}
    </div>
  );
};

const TypingIndicator = () => (
  <div className="ff-msg" style={{ marginBottom: 22 }}>
    <div className="ff-avatar bot">✦</div>
    <div className="ff-bubble">
      <div className="ff-sender">FaceFit Stylist</div>
      <div className="ff-typing">
        <div className="ff-dot-t" /><div className="ff-dot-t" /><div className="ff-dot-t" />
      </div>
    </div>
  </div>
);

const detectStyleAesthetic = (text) => {
  if (!text) return null;
  const tl = text.toLowerCase();
  for (const key of Object.keys(STYLE_AESTHETICS)) {
    if (tl.includes(key)) return key;
  }
  return null;
};

const BotMessage = ({ m, user }) => {
  if (m.role === "user") {
    return (
      <div className="ff-msg user">
        <div className="ff-avatar user">Y</div>
        <div className="ff-bubble" style={{ alignItems: "flex-end", display: "flex", flexDirection: "column" }}>
          <div className="ff-sender user-sender">You</div>
          <div className="ff-text user"><FormattedText text={m.text} /></div>
        </div>
      </div>
    );
  }
  const d = m.data || {};
  const gender = user?.gender || "male";
  const userId = user?.name || "";
  const styleAesthetic = detectStyleAesthetic(m.text);
  return (
    <div className="ff-msg">
      <div className="ff-avatar bot">✦</div>
      <div className="ff-bubble" style={{ flex: 1, minWidth: 0 }}>
        <div className="ff-sender">FaceFit Stylist</div>
        <div className="ff-text bot"><FormattedText text={m.text} /></div>
        {styleAesthetic && <StyleAestheticCard styleName={styleAesthetic} />}
        {d.weather?.summary && <WeatherBanner weather={d.weather} />}
        {d.routine && <RoutineCard routine={d.routine} />}
        {d.gap_analysis && <GapAnalysisDisplay gapData={d.gap_analysis} />}
        {d.closet_found_items?.length > 0 && !d.dual_outfit && <ClosetFoundItems items={d.closet_found_items} />}
        {d.dual_outfit && (
          <DualOutfitResult
            closetResult={d.dual_outfit.closet}
            newProducts={d.dual_outfit.new_products}
            eventLabel={d.dual_outfit.event_label}
            eventId={d.event}
            gender={gender}
            userId={userId}
          />
        )}
        {d.closet_outfit && !d.dual_outfit && (
          <div style={{ marginTop: 16, maxWidth: 780 }}>
            {d.closet_outfit.event_vibe && <div className="ff-event-badge">{d.closet_outfit.event_icon} {d.closet_outfit.event_vibe}</div>}
            {d.closet_outfit.outfit_plan && (
              <div style={{ fontSize: 13.5, color: "#2c1f0f", lineHeight: 1.75, marginBottom: 16, padding: "14px 16px", background: "rgba(200,165,90,.04)", borderLeft: "3px solid #c8a55a", borderRadius: "0 8px 8px 0" }}>
                {d.closet_outfit.outfit_plan}
              </div>
            )}
            {Object.values(d.closet_outfit.available_items || {}).filter(Boolean).length > 0 && (
              <div style={{ marginBottom: 18 }}>
                <div className="ff-section-label" style={{ color: "#6fc897" }}>✓ Found in Your Wardrobe</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 9 }}>
                  {Object.values(d.closet_outfit.available_items).filter(Boolean).map((item, i) => <WardrobeItemCard key={i} item={item} />)}
                </div>
              </div>
            )}
          </div>
        )}
        {d.mix_match?.combinations?.length > 0 && (
          <div style={{ marginTop: 16, maxWidth: 780 }}>
            <div className="ff-section-label" style={{ color: "#c8a55a" }}>✦ Your Best Combinations</div>
            {d.mix_match.combinations.slice(0, 6).map((c, i) => {
              const scoreMap = { 3:{color:"#5aaa7a",bg:"rgba(90,170,122,.06)",border:"rgba(90,170,122,.2)"}, 2:{color:"#c8a55a",bg:"rgba(200,165,90,.06)",border:"rgba(200,165,90,.2)"}, 1:{color:"#b8a898",bg:"rgba(184,168,152,.06)",border:"rgba(184,168,152,.15)"} };
              const s = scoreMap[c.color_score] || scoreMap[1];
              return (
                <div key={i} className="ff-combo" style={{ background: s.bg, borderColor: s.border }}>
                  <div className="ff-combo-header">
                    <div>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "#4a3828", display: "block" }}>{c.outfit_name || `Look #${i + 1}`}</span>
                      {c.event && <span style={{ fontSize: 9, color: "#a8998a" }}>for {c.event}</span>}
                    </div>
                    <span style={{ fontSize: 10, fontWeight: 700, color: s.color, background: `${s.color}18`, padding: "2px 10px", borderRadius: 12, flexShrink: 0 }}>{c.color_label}</span>
                  </div>
                  <div className="ff-combo-body">
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {[c.top, c.bottom, c.shoes].filter(Boolean).map((item, j) => <WardrobeItemCard key={j} item={item} />)}
                    </div>
                    {c.styling_tip && (
                      <div style={{ marginTop: 10, fontSize: 12, color: "#5a4838", fontStyle: "italic", borderLeft: "3px solid #c8a55a", paddingLeft: 10, lineHeight: 1.6 }}>
                        ✦ "{c.styling_tip}"
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <ColorPaletteWheel
              userId={userId}
              outfitItems={
                d.mix_match.combinations[0]
                  ? [d.mix_match.combinations[0].top, d.mix_match.combinations[0].bottom, d.mix_match.combinations[0].shoes].filter(Boolean)
                  : []
              }
              skinTone={user?.skinTone}
            />
          </div>
        )}
        {d.products && Object.keys(d.products).length > 0 && !d.dual_outfit && (
          <ProductGrid products={d.products} label="..." userId={userId} user={user} event={d.event} />
        )}
      </div>
    </div>
  );
};

// ── ClosetTab ─────────────────────────────────────────────────────────────────
const ClosetTab = ({ user }) => {
  const [items, setItems]                 = useState([]);
  const [loading, setLoading]             = useState(true);
  const [uploading, setUploading]         = useState(false);
  const [activeSection, setActiveSection] = useState("wardrobe");
  const [selEvent, setSelEvent]           = useState(null);
  const [outfit, setOutfit]               = useState(null);
  const [outfitLoading, setOutfitLoading] = useState(false);
  const [mixData, setMixData]             = useState(null);
  const [mixLoading, setMixLoading]       = useState(false);
  const [mixEvent, setMixEvent]           = useState("");
  const [gapData, setGapData]             = useState(null);
  const [gapLoading, setGapLoading]       = useState(false);
  const fileRef = useRef();

  const fetchItems = useCallback(async () => {
    if (!user?.name) return setLoading(false);
    try {
      const r = await axios.get(`${API}/closet/${user.name}`);
      setItems(r.data.items || []);
    } catch { setItems([]); }
    setLoading(false);
  }, [user?.name]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const handleUpload = async (file) => {
    if (!file || !user?.name) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("user_id", user.name);
    fd.append("image", file);
    try {
      await axios.post(`${API}/closet/add`, fd);
      await fetchItems();
    } catch { alert("Upload failed."); }
    setUploading(false);
  };

  const handleDelete = async (itemId) => {
    if (!window.confirm("Remove this item?")) return;
    try {
      await axios.delete(`${API}/closet/${user.name}/${itemId}`);
      await fetchItems();
    } catch { alert("Delete failed."); }
  };

  const planOutfit = async (eventId) => {
    setSelEvent(eventId);
    setOutfitLoading(true);
    setOutfit(null);
    try {
      const r = await axios.post(`${API}/closet/multi-outfit`, { user_id: user.name, event: eventId, user_context: user });
      setOutfit(r.data);
    } catch {
      try {
        const r2 = await axios.post(`${API}/closet/outfit-event`, { user_id: user.name, event: eventId, user_context: user });
        setOutfit({ ...r2.data, outfits: r2.data.available_items ? [{items: r2.data.available_items, color_score: 2, color_label: "Good combo"}] : [] });
      } catch { setOutfit(null); }
    }
    setOutfitLoading(false);
  };

  const loadMixMatch = async () => {
    if (!user?.name) return;
    setMixLoading(true);
    try {
      const params = new URLSearchParams({ skin_tone: user.skinTone || "medium" });
      if (mixEvent) params.append("event", mixEvent);
      const r = await axios.get(`${API}/closet/mix-match/${user.name}?${params}`);
      setMixData(r.data);
    } catch { setMixData(null); }
    setMixLoading(false);
  };

  const loadGapAnalysis = async () => {
    if (!user?.name) return;
    setGapLoading(true);
    try {
      const r = await axios.get(`${API}/closet/gap-analysis/${user.name}`);
      setGapData(r.data);
    } catch { setGapData(null); }
    setGapLoading(false);
  };

  useEffect(() => {
    if (activeSection === "gaps" && !gapData && !gapLoading) loadGapAnalysis();
    if (activeSection === "mixmatch" && !mixData && !mixLoading) loadMixMatch();
  }, [activeSection]);

  const sectionBtns = [
    {id:"wardrobe",label:"Wardrobe",icon:"◇"},{id:"plan",label:"Plan Outfit",icon:"✦"},
    {id:"mixmatch",label:"Mix & Match",icon:"♻"},{id:"gaps",label:"Gap Analyzer",icon:"📊"},
  ];

  return (
    <div className="ff-closet">
      <div style={{ display: "flex", gap: 6, marginBottom: 22, flexWrap: "wrap" }}>
        {sectionBtns.map(s => (
          <button key={s.id}
            className={`ff-event-chip${activeSection === s.id ? " active" : ""}`}
            style={activeSection === s.id ? { borderColor: "#c8a55a", color: "#8a5820", background: "rgba(200,165,90,.1)", fontWeight: 600, fontSize: 12 } : { fontSize: 12 }}
            onClick={() => setActiveSection(s.id)}>
            {s.icon} {s.label}
          </button>
        ))}
      </div>

      {/* ── WARDROBE SECTION ─────────────────────────────────────────────── */}
      {activeSection === "wardrobe" && (
        <>
          <div style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#1a0f00", marginBottom: 6 }}>
              Your Digital Wardrobe
              {items.length > 0 && <span style={{ fontSize: 11, color: "#a8998a", fontWeight: 400, marginLeft: 8 }}>{items.length} items</span>}
            </div>
            <div className="ff-upload-zone" onClick={() => fileRef.current?.click()}
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); handleUpload(e.dataTransfer.files[0]); }}>
              {uploading
                ? <div style={{ color: "#c8a55a", fontSize: 13 }}>
                    <div style={{ width: 20, height: 20, border: "2px solid #c8a55a", borderTopColor: "transparent", borderRadius: "50%", animation: "spin .8s linear infinite", margin: "0 auto 10px" }} />
                    Analysing your item with AI...
                  </div>
                : <>
                    <div style={{ fontSize: 26, marginBottom: 8 }}>+</div>
                    <div style={{ fontSize: 13, color: "#8a7a6a" }}>Drop clothing photo or <span style={{ color: "#c8a55a", fontWeight: 600 }}>click to upload</span></div>
                    <div style={{ fontSize: 11, color: "#a8998a", marginTop: 4 }}>AI detects garment, color &amp; style automatically</div>
                  </>
              }
              <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
                onChange={e => handleUpload(e.target.files[0])} />
            </div>
          </div>

          {loading
            ? <div style={{ color: "#a8998a", fontSize: 13, textAlign: "center", padding: "20px 0" }}>Loading your wardrobe...</div>
            : items.length === 0
              ? <div style={{ color: "#a8998a", fontSize: 13, textAlign: "center", padding: "20px 0" }}>Your wardrobe is empty. Upload your first item above!</div>
              : (
                // ── FIXED: wardrobe grid now uses resolveItemImageUrl ─────
                <div className="ff-closet-grid">
                  {items.map(item => {
                    const src = resolveItemImageUrl(item.image_url);
                    return (
                      <ClosetCard key={item.item_id} item={item} src={src} onDelete={handleDelete} />
                    );
                  })}
                </div>
              )
          }
        </>
      )}

      {/* ── PLAN OUTFIT SECTION ───────────────────────────────────────────── */}
      {activeSection === "plan" && (
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#1a0f00", marginBottom: 4 }}>Plan an Outfit</div>
          <div style={{ fontSize: 12, color: "#a8998a", marginBottom: 4 }}>Choose an occasion — I'll build 2–3 outfit combinations from your wardrobe.</div>
          {items.length === 0
            ? <div style={{ color: "#a8998a", fontSize: 13, padding: "24px 0", textAlign: "center" }}>Upload clothes first in the <strong>Wardrobe</strong> tab!</div>
            : <>
                <div className="ff-plan-event-grid">
                  {ALL_EVENTS.map(ev => (
                    <button key={ev.id} className={`ff-plan-event-btn${selEvent === ev.id ? " active" : ""}`} onClick={() => planOutfit(ev.id)}>
                      <span className="ff-plan-event-icon">{ev.icon}</span>
                      <span className="ff-plan-event-label">{ev.label}</span>
                    </button>
                  ))}
                </div>
                {outfitLoading && (
                  <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 10, color: "#c8a55a", fontSize: 13 }}>
                    <span style={{ width: 14, height: 14, border: "2px solid #c8a55a", borderTopColor: "transparent", borderRadius: "50%", display: "inline-block", animation: "spin .8s linear infinite" }} />
                    Building outfit options for {selEvent}...
                  </div>
                )}
                {outfit && !outfitLoading && (
                  <div style={{ marginTop: 22, padding: "20px 22px", background: "#fff", border: "1px solid #ece6dc", borderRadius: 14 }}>
                    <MultiOutfitResult result={outfit} eventId={selEvent} user={user} />
                    {outfit.outfits?.length > 0 && (
                      <ColorPaletteWheel userId={user?.name} skinTone={user?.skinTone} />
                    )}
                  </div>
                )}
              </>
          }
        </div>
      )}

      {/* ── MIX & MATCH SECTION ───────────────────────────────────────────── */}
      {activeSection === "mixmatch" && (
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#1a0f00", marginBottom: 3 }}>Mix &amp; Match</div>
              <div style={{ fontSize: 12, color: "#a8998a" }}>All combinations ranked by colour harmony</div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <select value={mixEvent} onChange={e => { setMixEvent(e.target.value); setMixData(null); }}
                style={{ padding: "6px 10px", border: "1px solid #ddd3c2", borderRadius: 8, fontFamily: "inherit", fontSize: 11, color: "#5a4838", background: "#faf7f3" }}>
                <option value="">All events</option>
                {ALL_EVENTS.map(ev => <option key={ev.id} value={ev.id}>{ev.icon} {ev.label}</option>)}
              </select>
              <button className="ff-btn-primary" style={{ padding: "8px 18px", fontSize: 10 }} onClick={loadMixMatch} disabled={mixLoading}>
                {mixLoading ? "..." : "Generate"}
              </button>
            </div>
          </div>
          {mixLoading && (
            <div style={{ color: "#c8a55a", fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 13, height: 13, border: "2px solid #c8a55a", borderTopColor: "transparent", borderRadius: "50%", display: "inline-block", animation: "spin .8s linear infinite" }} />
              Analysing wardrobe combinations...
            </div>
          )}
          {mixData && !mixLoading && (
            mixData.combinations?.length === 0
              ? <div style={{ color: "#a8998a", fontSize: 13, padding: "20px 0" }}>Upload tops and bottoms to see combinations!</div>
              : <>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                    <div style={{ fontSize: 11, color: "#a8998a" }}>{mixData.total} combinations · showing best {mixData.combinations?.length}</div>
                    {mixData.ai_powered && <span style={{ fontSize: 9, padding: "2px 8px", background: "rgba(111,200,151,.12)", border: "1px solid rgba(111,200,151,.3)", borderRadius: 10, color: "#1e5035", fontWeight: 700, letterSpacing: ".06em" }}>✦ AI STYLED</span>}
                  </div>
                  {mixData.combinations?.slice(0, 6).map((combo, i) => {
                    const scoreMap = { 3:{color:"#5aaa7a",bg:"rgba(90,170,122,.05)",border:"rgba(90,170,122,.2)"}, 2:{color:"#c8a55a",bg:"rgba(200,165,90,.05)",border:"rgba(200,165,90,.2)"}, 1:{color:"#b8a898",bg:"rgba(184,168,152,.05)",border:"rgba(184,168,152,.15)"} };
                    const s = scoreMap[combo.color_score] || scoreMap[1];
                    return (
                      <div key={i} className="ff-mm-combo" style={{ background: s.bg, borderColor: s.border }}>
                        <div className="ff-mm-combo-header">
                          <div>
                            <span style={{ fontSize: 10, fontWeight: 700, color: "#5a4838" }}>{combo.outfit_name || `Look #${i + 1}`}</span>
                            {combo.event && <span style={{ fontSize: 9, color: "#a8998a", display: "block" }}>for {combo.event}</span>}
                          </div>
                          <span style={{ fontSize: 10, fontWeight: 700, color: s.color, background: `${s.color}18`, padding: "2px 10px", borderRadius: 12 }}>{combo.color_label}</span>
                        </div>
                        <div className="ff-mm-combo-body">
                          {[combo.top, combo.bottom, combo.shoes].filter(Boolean).map((item, j) => <WardrobeItemCard key={j} item={item} />)}
                        </div>
                        {combo.styling_tip && (
                          <div style={{ padding: "8px 14px 12px", fontSize: 12, color: "#5a4838", fontStyle: "italic", borderTop: "1px solid #f5f1eb", lineHeight: 1.6 }}>
                            ✦ "{combo.styling_tip}"
                          </div>
                        )}
                      </div>
                    );
                  })}
                  {mixData.combinations?.length > 0 && (
                    <ColorPaletteWheel
                      userId={user?.name}
                      outfitItems={mixData.combinations[0] ? [mixData.combinations[0].top, mixData.combinations[0].bottom, mixData.combinations[0].shoes].filter(Boolean) : []}
                      skinTone={user?.skinTone}
                    />
                  )}
                </>
          )}
          {!mixData && !mixLoading && (
            <div style={{ padding: "32px 0", textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>♻</div>
              <div style={{ fontSize: 13, color: "#a8998a", marginBottom: 16 }}>
                {items.length === 0 ? "Upload clothes first!" : "Click Generate to see outfit combinations"}
              </div>
              {items.length > 0 && <button className="ff-btn-primary" onClick={loadMixMatch}>Generate Combinations</button>}
            </div>
          )}
        </div>
      )}

      {/* ── GAP ANALYSIS SECTION ─────────────────────────────────────────── */}
      {activeSection === "gaps" && (
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#1a0f00", marginBottom: 4 }}>Style Gap Analyzer</div>
          <div style={{ fontSize: 12, color: "#a8998a", marginBottom: 16 }}>See exactly what you're missing for each event type.</div>
          {gapLoading && <div style={{ color: "#c8a55a", fontSize: 13 }}>Analyzing your wardrobe...</div>}
          {gapData && <GapAnalysisDisplay gapData={gapData} />}
          {!gapLoading && !gapData && <div style={{ color: "#a8998a", fontSize: 13 }}>{items.length === 0 ? "Upload some clothes first!" : "Loading gap analysis..."}</div>}
        </div>
      )}
    </div>
  );
};

// ── FIXED ClosetCard (extracted for cleanliness, uses resolveItemImageUrl) ────
const ClosetCard = ({ item, src, onDelete }) => {
  const [imgErr, setImgErr] = useState(false);
  return (
    <div className="ff-closet-card">
      <div className="ff-closet-card-img">
        {src && !imgErr
          ? <img
              src={src}
              alt={item.item_name}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
              onError={() => setImgErr(true)}
              crossOrigin="anonymous"
            />
          : <div style={{ fontSize: 30, opacity: .4 }}>{CLOSET_CAT_ICONS[item.category] || "👕"}</div>
        }
        <button className="ff-closet-del" onClick={(e) => { e.stopPropagation(); onDelete(item.item_id); }}>✕</button>
      </div>
      <div className="ff-closet-card-info">
        <div className="ff-closet-card-name">{item.item_name}</div>
        <div className="ff-closet-card-meta">{item.color} · {item.formality || "casual"}</div>
      </div>
    </div>
  );
};

// ── TryOnTab ──────────────────────────────────────────────────────────────────
const TryOnTab = () => {
  const [activeType, setActiveType]     = useState(null);
  const [uploading, setUploading]       = useState(false);
  const [isStreaming, setIsStreaming]   = useState(false);
  const [uploadedName, setUploadedName] = useState("");
  const [streamKey, setStreamKey]       = useState(0);
  const fileRef = useRef();

  const ACCESSORY_TYPES = [
    {id:"sunglasses",label:"Sunglasses",icon:"🕶️",tip:"Works best with frontal face shot",color:"#0288d1"},
    {id:"earrings",label:"Earrings",icon:"💎",tip:"AI places at ear lobes precisely",color:"#c2185b"},
    {id:"necklace",label:"Necklace",icon:"📿",tip:"AI anchors below chin line",color:"#f57f17"},
    {id:"hat",label:"Hat / Cap",icon:"🧢",tip:"AI places above your forehead",color:"#2e7d32"},
    {id:"bracelet",label:"Bracelet",icon:"💛",tip:"Shows on your detected wrist",color:"#e65100"},
    {id:"ring",label:"Ring",icon:"💍",tip:"Tracks your ring finger in real time",color:"#6a1b9a"},
  ];

  const uploadAccessory = async (file) => {
    if (!file || !activeType) return;
    setUploading(true);
    const fd = new FormData();
    fd.append("image", file);
    fd.append("type", activeType);
    try {
      await axios.post(`${API}/upload-accessory`, fd);
      setUploadedName(file.name);
      setIsStreaming(true);
      setStreamKey(k => k + 1);
    } catch { alert("Upload failed."); }
    setUploading(false);
  };

  const reset = async () => {
    try { await axios.post(`${API}/reset-accessory`); } catch {}
    setIsStreaming(false);
    setUploadedName("");
  };

  const switchAccessory = (newType) => {
    setActiveType(newType);
    if (isStreaming) { setIsStreaming(false); setUploadedName(""); }
  };

  const selectedType = ACCESSORY_TYPES.find(t => t.id === activeType);

  return (
    <div className="ff-tryon-container">
      <div style={{ textAlign: "center", padding: "32px 24px", background: "linear-gradient(135deg,#1a0f00 0%,#3a2010 50%,#1a0f00 100%)", borderRadius: 18, marginBottom: 24, position: "relative", overflow: "hidden" }}>
        <div style={{ fontFamily: "'Cormorant Garamond',serif", fontSize: 28, color: "#c8a55a", position: "relative", zIndex: 1, marginBottom: 6 }}>◉ Virtual Try-On</div>
        <div style={{ fontSize: 12, color: "#a8998a", position: "relative", zIndex: 1, letterSpacing: ".04em" }}>AI-powered accessory overlay · Live camera · Zero downloads needed</div>
      </div>

      <div style={{ background: "#fff", border: "1.5px solid rgba(200,165,90,.3)", borderRadius: 16, padding: 24, marginBottom: 16 }}>
        <div style={{ fontSize: 9, letterSpacing: ".25em", textTransform: "uppercase", fontWeight: 700, color: "#c8a55a", marginBottom: 10, display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 20, height: 20, borderRadius: "50%", background: "#1a0f00", color: "#c8a55a", fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>1</span>
          Choose Your Accessory
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10 }}>
          {ACCESSORY_TYPES.map(t => (
            <button key={t.id} onClick={() => switchAccessory(t.id)}
              style={{ padding: "16px 10px 14px", border: `1.5px solid ${activeType === t.id ? "#c8a55a" : "#ece6dc"}`, background: activeType === t.id ? "linear-gradient(135deg,rgba(200,165,90,.12),rgba(200,165,90,.04))" : "#fff", borderRadius: 16, fontFamily: "inherit", cursor: "pointer", transition: "all .22s", display: "flex", flexDirection: "column", alignItems: "center", gap: 8, position: "relative" }}>
              <span style={{ fontSize: 28 }}>{t.icon}</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: "#4a3828" }}>{t.label}</span>
              <span style={{ fontSize: 9, color: "#a8998a", textAlign: "center", lineHeight: 1.4 }}>{t.tip}</span>
              {activeType === t.id && <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 3, background: t.color, borderRadius: "0 0 14px 14px" }} />}
            </button>
          ))}
        </div>
      </div>

      {activeType && !isStreaming && (
        <div style={{ background: "#fff", border: "1.5px solid rgba(200,165,90,.3)", borderRadius: 16, padding: 24, marginBottom: 16 }}>
          <div style={{ fontSize: 9, letterSpacing: ".25em", textTransform: "uppercase", fontWeight: 700, color: "#c8a55a", marginBottom: 10, display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 20, height: 20, borderRadius: "50%", background: "#1a0f00", color: "#c8a55a", fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>2</span>
            Upload {selectedType?.label} Image
          </div>
          <div onClick={() => fileRef.current?.click()} style={{ border: "1.5px dashed #c8a55a", borderRadius: 12, padding: "28px 20px", textAlign: "center", cursor: "pointer", background: "rgba(200,165,90,.02)", transition: "all .2s" }}>
            {uploading
              ? <div style={{ color: "#c8a55a" }}>
                  <div style={{ width: 24, height: 24, border: "2px solid #c8a55a", borderTopColor: "transparent", borderRadius: "50%", animation: "spin .8s linear infinite", margin: "0 auto 12px" }} />
                  <div style={{ fontSize: 13 }}>Removing background &amp; calibrating overlay...</div>
                </div>
              : <>
                  <div style={{ fontSize: 36, marginBottom: 10 }}>{selectedType?.icon}</div>
                  <div style={{ fontSize: 13, color: "#8a7a6a" }}>Drop PNG/JPG here or <span style={{ color: "#c8a55a", fontWeight: 600 }}>click to browse</span></div>
                  <div style={{ fontSize: 11, color: "#b0a090", marginTop: 6 }}>PNG with transparency · Max 10MB</div>
                </>
            }
            <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" style={{ display: "none" }}
              onChange={e => uploadAccessory(e.target.files[0])} />
          </div>
        </div>
      )}

      {isStreaming && (
        <div>
          <div style={{ background: "#fff", border: "1.5px solid rgba(200,165,90,.3)", borderRadius: 16, padding: 24 }}>
            <div style={{ fontSize: 9, letterSpacing: ".25em", textTransform: "uppercase", fontWeight: 700, color: "#c8a55a", marginBottom: 10, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 20, height: 20, borderRadius: "50%", background: "#1a0f00", color: "#c8a55a", fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>3</span>
              Live Try-On — {selectedType?.label}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, padding: "10px 14px", background: "rgba(111,200,151,.08)", border: "1px solid rgba(111,200,151,.25)", borderRadius: 10 }}>
              <span style={{ fontSize: 20 }}>{selectedType?.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#1e5035" }}>Active: {selectedType?.label}</div>
                <div style={{ fontSize: 10.5, color: "#6a9278" }}>{uploadedName}</div>
              </div>
              <button onClick={reset} style={{ padding: "5px 12px", border: "1px solid rgba(200,64,64,.3)", borderRadius: 8, background: "rgba(200,64,64,.06)", color: "#c02020", fontFamily: "inherit", fontSize: 10.5, cursor: "pointer", fontWeight: 600 }}>✕ Remove</button>
            </div>
            <div style={{ position: "relative", borderRadius: 16, overflow: "hidden", border: "2px solid #c8a55a", boxShadow: "0 12px 40px rgba(0,0,0,.2)" }}>
              <img key={streamKey} src={`${API}/virtual-tryon?t=${streamKey}`} alt="Live try-on"
                style={{ width: "100%", display: "block", maxHeight: 520, objectFit: "contain", background: "#111" }}
                onError={() => { setIsStreaming(false); alert("Camera stream unavailable."); }} />
              <div style={{ position: "absolute", top: 12, left: 12, display: "flex", alignItems: "center", gap: 6, padding: "5px 12px", background: "rgba(26,15,0,.8)", backdropFilter: "blur(8px)", borderRadius: 20 }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#6fc897", animation: "blink 1s ease infinite" }} />
                <span style={{ fontSize: 10, color: "#e8d8b8", letterSpacing: ".08em", fontWeight: 700, textTransform: "uppercase" }}>Live</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── MAIN CHATBOT COMPONENT ────────────────────────────────────────────────────
export default function Chatbot() {
  const navigate = useNavigate();
  const [user, setUser] = useState(getUser());
  const { prefs: budgetPrefs, reload: reloadPrefs, buildContext: buildBudgetContext } = useBudgetBrand(user?.name);
  useEffect(() => {
    restoreSession().then(profile => { if (profile) setUser(profile); });
  }, []);

  const handleLogout = async () => { await logout(); navigate("/"); };

  const welcomeMsg = user?.name
    ? `Welcome back, **${user.name}**! ✦  I know your profile — **${user.skinTone || "medium"} skin**, **${user.face_shape || "oval"} face**${user.conditions?.length ? ` · ${[...new Set(user.conditions)].slice(0, 2).join(", ")}` : ""}.\n\nWhat are we styling today?`
    : "Welcome to **FaceFit**! ✦\n\nComplete your face scan first, then I'll give you fully personalised outfit & skincare recommendations.";

  const [msgs, setMsgs]             = useState([{ role: "bot", text: welcomeMsg, data: {} }]);
  const [input, setInput]           = useState("");
  const [busy, setBusy]             = useState(false);
  const [activeTab, setActiveTab]   = useState("chat");
  const [closetCount, setClosetCount] = useState(0);
  const histRef  = useRef([]);
  const endRef   = useRef();
  const inputRef = useRef();

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  useEffect(() => {
    if (user?.name) {
      axios.get(`${API}/closet/${user.name}`).then(r => setClosetCount(r.data.total || 0)).catch(() => {});
    }
  }, [user?.name, activeTab]);

  const send = async (txt) => {
    const message = (txt || input).trim();
    if (!message || busy) return;

    // ── Tab-redirect shortcuts ──────────────────────────────────────────────
    if (/schedule.*outfit|outfit.*reminder|set.*reminder|remind.*outfit|outfit.*planner/i.test(message)) { setActiveTab("scheduler"); return; }
    if (/skin.*progress|track.*skin|skin.*track|weekly.*scan|scan.*progress/i.test(message)) { setActiveTab("skinprogress"); return; }
    if (/saved.*products|price.*alert|price.*drop|my.*saved|wishlist/i.test(message)) { setActiveTab("saved"); return; }
    if (/body.*shape|shape.*body|full body|body type/i.test(message)) { setActiveTab("bodyshape"); return; }
    if (/budget|brand.*preference|favourite.*brand|preferred.*brand|price.*filter/i.test(message)) { setActiveTab("preferences"); return; }
    if (/event.*plan|plan.*event|i have a (wedding|party|interview|festival|date|office|concert|sangeet|mehndi|haldi|reception|puja|trip|farewell)|upcoming (event|wedding|party)|outfit.*for.*(wedding|party|interview|festival|date)/i.test(message)) {
      setActiveTab("eventplanner"); return;
    }
    if (/analyze.*outfit|outfit.*analyz|rate.*outfit|outfit.*rate|photo.*analyz|check.*outfit/i.test(message)) {
      setActiveTab("photoanalyzer"); return;
    }

    setInput("");
    setMsgs(p => [...p, { role: "user", text: message, data: {} }]);
    histRef.current = [...histRef.current, { role: "user", content: message }].slice(-16);
    setBusy(true);

    if (/gap.*(analys|check|report)|what.*missing|wardrobe.*gap|style.*gap|closet.*gap/i.test(message)) {
      try {
        const r = await axios.get(`${API}/closet/gap-analysis/${user?.name || "guest"}`);
        const botText = `Here's your **Style Gap Report**, ${user?.name || "there"}!`;
        histRef.current = [...histRef.current, { role: "assistant", content: botText }].slice(-16);
        setMsgs(p => [...p, { role: "bot", text: botText, data: { gap_analysis: r.data } }]);
        setBusy(false); return;
      } catch (e) { console.error(e); }
    }

    if (/mix.*(and|&|n).*(match|wear)|match.*my.*wardrobe|combine.*my.*clothes|mix.*wardrobe/i.test(message)) {
      const evMatch = message.match(/for\s+(a\s+)?(\w+)/i)?.[2]?.toLowerCase() || "";
      try {
        const params = new URLSearchParams({ skin_tone: user?.skinTone || "medium" });
        if (evMatch && ALL_EVENTS.find(e => e.id === evMatch)) params.append("event", evMatch);
        const res = await axios.get(`${API}/closet/mix-match/${user?.name || "guest"}?${params}`);
        const data = res.data;
        const botText = data.total === 0
          ? `Your wardrobe needs more items! Upload some tops and bottoms in the **Closet tab** first.`
          : `Here are your best outfit combinations, **${user?.name}**! Found **${data.total} possible looks** — ranked by colour harmony.`;
        histRef.current = [...histRef.current, { role: "assistant", content: botText }].slice(-16);
        setMsgs(p => [...p, { role: "bot", text: botText, data: { mix_match: data } }]);
        setBusy(false); return;
      } catch (e) { console.error(e); }
    }

    const styleKey = detectStyleAesthetic(message);
    if (styleKey && /style|aesthetic|look|vibe|what is|explain|how to|outfit/i.test(message)) {
      const aesthetic = STYLE_AESTHETICS[styleKey];
      const botText = `**${styleKey.replace(/\b\w/g, c => c.toUpperCase())} aesthetic** — ${aesthetic.desc}\n\nHere's a complete style breakdown. Want me to find these items for your **${user?.skinTone || "medium"} skin tone**?`;
      histRef.current = [...histRef.current, { role: "assistant", content: botText }].slice(-16);
      setMsgs(p => [...p, { role: "bot", text: botText, data: { style_aesthetic: styleKey } }]);
      setBusy(false); return;
    }

    try {
      const res = await axios.post(`${API}/chat`, { message, user_context: user, history: histRef.current });
      const data = res.data;
      const botText = data.message || "I couldn't process that. Please try again.";
      histRef.current = [...histRef.current, { role: "assistant", content: botText }].slice(-16);
      const detectedEvent = data.event || (() => {
        const evMatch = ALL_EVENTS.find(ev => message.toLowerCase().includes(ev.id) || message.toLowerCase().includes(ev.label.toLowerCase()));
        return evMatch?.id || null;
      })();
      setMsgs(p => [...p, {
        role: "bot", text: botText,
        data: {
          products:           data.products || null,
          routine:            data.routine  || null,
          product_type:       data.product_type || null,
          closet_outfit:      data.closet_outfit || null,
          closet_found_items: data.closet_found_items || null,
          event:              detectedEvent,
          mix_match:          data.mix_match || null,
          dual_outfit:        data.dual_outfit || null,
          gap_analysis:       data.gap_analysis || null,
          weather:            data.weather || null,
        },
      }]);
    } catch (err) {
      console.error(err);
      setMsgs(p => [...p, { role: "bot", text: "Sorry, something went wrong. Please try again.", data: {} }]);
    }
    setBusy(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const showChips = msgs.length <= 1 && !busy;
  const chips = CHIPS(user);

  const TAB_CONFIG = [
    { id: "chat",          label: "AI Stylist",      icon: "◈"  },
    { id: "closet",        label: "Digital Closet",  icon: "◇",  badge: closetCount },
    { id: "eventplanner",  label: "Event Planner",   icon: "🗓", isNew: true },
    { id: "photoanalyzer", label: "Photo Analyzer",  icon: "📸", isNew: true },
    { id: "bodyshape",     label: "Body Shape",      icon: "🧍"  },
    { id: "skinprogress",  label: "Skin Progress",   icon: "📈"  },
    { id: "preferences",   label: "Budget/Brands",   icon: "⚙️"  },
    { id: "saved",         label: "Price Alerts",    icon: "🔔"  },
    { id: "scheduler",     label: "Scheduler",       icon: "🗓"  },
    { id: "tryon",         label: "Try-On",          icon: "◉"  },
    { id: "mystyle", label: "My Style", icon: "🎨" },
  ];

  return (
    <>
      <style>{CSS}</style>
      <div className="facefit-root">

        {/* HEADER */}
        <header className="ff-header">
          <div className="ff-brand">
            <div className="ff-logo">✦</div>
            <div className="ff-brand-text">
              <div className="ff-eyebrow">AI Style Intelligence</div>
              <div className="ff-wordmark">FaceFit</div>
            </div>
          </div>
          <div className="ff-header-right">
            {user?.name && (
              <div className="ff-profile">
                <div className="ff-dot" />
                <div>
                  <div className="ff-profile-name">{user.name}</div>
                  <div className="ff-profile-meta">
                    {user.skinTone || "—"} skin · {user.face_shape || "—"} face
                    {user.conditions?.length > 0 && ` · ${[...new Set(user.conditions)].slice(0, 2).join(", ")}`}
                  </div>
                </div>
              </div>
            )}
            <button className="ff-logout-btn" onClick={handleLogout}>Logout</button>
          </div>
        </header>

        {/* TABS */}
        <nav className="ff-tabs">
          {TAB_CONFIG.map(tab => (
            <button
              key={tab.id}
              className={`ff-tab${activeTab === tab.id ? " active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.icon} {tab.label}
              {tab.badge > 0 && <span className="ff-tab-badge">{tab.badge}</span>}
              {tab.isNew && <span className="ff-tab-new">NEW</span>}
            </button>
          ))}
        </nav>

        {/* ── CHAT TAB ─────────────────────────────────────────────────────── */}
        {activeTab === "chat" && (
          <>
            <div className="ff-chat">
              {msgs.map((m, i) => <BotMessage key={i} m={m} user={user} />)}
              {busy && <TypingIndicator />}
              <div ref={endRef} />
            </div>
            {showChips && (
              <div className="ff-chips">
                {chips.map((c, i) => (
                  <button key={i} className="ff-chip" onClick={() => send(c.label)}>
                    <span style={{ fontSize: 12 }}>{c.icon}</span>{c.label}
                  </button>
                ))}
              </div>
            )}
            <div className="ff-input-bar">
              <input
                ref={inputRef}
                className="ff-input"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
                placeholder="Ask about outfits, skincare, Old Money style, your wardrobe..."
                disabled={busy}
              />
              <VoiceInput
                onTranscript={(text) => {
                  setInput(text);
                  setTimeout(() => send(text), 300);
                }}
                disabled={busy}
              />
              <button className="ff-send" onClick={() => send()} disabled={busy || !input.trim()}>
                {busy
                  ? <span style={{ width: 13, height: 13, border: "1.5px solid currentColor", borderTopColor: "transparent", borderRadius: "50%", display: "inline-block", animation: "spin .8s linear infinite" }} />
                  : "Send →"
                }
              </button>
            </div>
          </>
        )}

        {/* ── CLOSET TAB ───────────────────────────────────────────────────── */}
        {activeTab === "closet" && <ClosetTab user={user} />}

        {/* ── EVENT PLANNER TAB ────────────────────────────────────────────── */}
        {activeTab === "eventplanner" && (
          <div className="ff-feature-tab">
            <EventPlanner user={user} />
          </div>
        )}

        {/* ── PHOTO ANALYZER TAB ───────────────────────────────────────────── */}
        {activeTab === "photoanalyzer" && (
          <div className="ff-feature-tab">
            <OutfitPhotoAnalyzer user={user} />
          </div>
        )}

        {/* ── BODY SHAPE TAB ───────────────────────────────────────────────── */}
        {activeTab === "bodyshape" && (
          <div className="ff-full-tab" style={{ padding: "24px 28px" }}>
            <h2 style={{ fontFamily: "'Cormorant Garamond',serif", fontWeight: 300, fontSize: 28, color: "#1a1208", margin: "0 0 6px" }}>
              Body <em style={{ fontStyle: "italic", color: "#c8a96e" }}>Shape</em> Analysis
            </h2>
            <p style={{ fontSize: 13, color: "#8a7a6a", marginBottom: 20, lineHeight: 1.65 }}>
              Upload a clear full-body photo. MediaPipe AI detects your body proportions and recommends outfits that flatter your shape.
            </p>
            <BodyShapeDetector user={user} onShapeDetected={(data) => console.log("Body shape:", data.body_shape)} />
          </div>
        )}

        {/* ── SKIN PROGRESS TAB ────────────────────────────────────────────── */}
        {activeTab === "skinprogress" && (
          <div className="ff-full-tab" style={{ padding: "0 28px" }}>
            <SkinProgress />
          </div>
        )}

        {/* ── BUDGET/BRANDS TAB ────────────────────────────────────────────── */}
        {activeTab === "preferences" && (
          <div className="ff-full-tab" style={{ padding: "24px 28px" }}>
            <h2 style={{ fontFamily: "'Cormorant Garamond',serif", fontWeight: 300, fontSize: 28, color: "#1a1208", margin: "0 0 6px" }}>
              My <em style={{ fontStyle: "italic", color: "#c8a96e" }}>Preferences</em>
            </h2>
            <p style={{ fontSize: 13, color: "#8a7a6a", marginBottom: 6 }}>
              Set your budget and save favourite brands. All product recommendations are automatically filtered and biased toward your preferences.
            </p>
            <BudgetBrandPanel userId={user?.name} onUpdate={() => console.log("Preferences updated")} />
          </div>
        )}

        {/* ── SAVED PRODUCTS TAB ───────────────────────────────────────────── */}
        {activeTab === "saved" && (
          <div className="ff-full-tab" style={{ padding: "0 28px" }}>
            <SavedProducts />
          </div>
        )}
        {/* ── MY STYLE TAB ─────────────────────────────────────────── */}
{activeTab === "mystyle" && (
  <div className="ff-full-tab" style={{ padding: "24px 28px" }}>
    <StylePreferences userId={user?.name} />
  </div>
)}
        {/* ── SCHEDULER TAB ────────────────────────────────────────────────── */}
        {activeTab === "scheduler" && (
          <div className="ff-scheduler">
            <OutfitScheduler user={user} />
          </div>
        )}

        {/* ── VIRTUAL TRY-ON TAB ───────────────────────────────────────────── */}
        {activeTab === "tryon" && <TryOnTab />}

      </div>
    </>
  );
}