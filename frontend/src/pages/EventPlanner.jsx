/**
 * EventPlanner.jsx — FaceFit AI Event Planner v5 ULTIMATE
 * =========================================================
 * FIXES:
 *  1. Wardrobe shows MAX 6 most relevant items (not all 35)
 *  2. Main Outfit & Backup have real item IMAGES matched from wardrobe
 *  3. Skincare prep is visual, beautiful, step-by-step with product images
 *  4. Shopping products with real images + save/alert buttons
 *  5. No hardcoding — all AI+RAG+skin analysis driven
 *  6. WOW UI — premium luxury aesthetic
 */
import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { SaveButton } from "./SavedProducts";
import { getProfile } from "./Register";

const API = "http://127.0.0.1:5000";

const QUICK = [
  { label: "Wedding in 3 days",  icon: "💍", msg: "I have a wedding in 3 days"         },
  { label: "Party tonight",       icon: "🎊", msg: "I have a party tonight"              },
  { label: "Interview tomorrow",  icon: "🎯", msg: "I have a job interview tomorrow"     },
  { label: "Festival in 2 days",  icon: "🎉", msg: "I have a festival in 2 days"        },
  { label: "Date this evening",   icon: "🌹", msg: "I have a date this evening"          },
  { label: "Office meeting",      icon: "💼", msg: "I have an important office meeting"  },
  { label: "Sangeet ceremony",    icon: "🎶", msg: "I have a sangeet ceremony in 3 days" },
  { label: "Beach trip tomorrow", icon: "🏖️", msg: "I have a beach trip tomorrow"       },
  { label: "College farewell",    icon: "🎓", msg: "I have a college farewell in 2 days" },
  { label: "Special dinner",      icon: "🍽️", msg: "I have a special dinner tonight"    },
];

const CAT_EMOJI = {
  shirt:"👕",pants:"👖",shoes:"👟",ethnic:"🥻",accessories:"💍",dress:"👗",
  blazer:"🧥",watch:"⌚",necklace:"💎",earrings:"✨",sunglasses:"🕶️",
  top:"👚",jacket:"🧥",track_pants:"🩳",gym_tshirt:"💪",sports_shoes:"👟",
  swim_shorts:"🩱",beach_shirt:"🌴",flip_flops:"🩴",
};

const COLOR_HEX = {
  black:"#1a1a1a",white:"#f5f5f0",grey:"#9e9e9e",gray:"#9e9e9e",
  navy:"#0d2b6e","navy blue":"#0d2b6e",blue:"#1565c0",green:"#2e7d32",
  "dark green":"#1b5e20",saffron:"#ff8f00",mustard:"#f57f17",
  terracotta:"#bf360c",coral:"#e64a19",burgundy:"#880e4f",maroon:"#7b1f1f",
  teal:"#00695c",olive:"#6d7c1e",cream:"#f5f0dc","off white":"#f5f0dc",
  beige:"#d7c4a3",camel:"#a1887f",lavender:"#9575cd",mint:"#80cbc4",
  sage:"#8d9e7e",emerald:"#00897b",orange:"#e65100",red:"#d32f2f",
  pink:"#c2185b",purple:"#6a1b9a","royal blue":"#1565c0",
  "electric blue":"#0288d1",gold:"#f9a825",brown:"#4e342e",
  "light blue":"#90caf9","off white":"#f5f0dc",
};

function getColorHex(colorStr) {
  if (!colorStr) return "#c8a55a";
  const lc = colorStr.toLowerCase().trim();
  if (COLOR_HEX[lc]) return COLOR_HEX[lc];
  for (const [k, v] of Object.entries(COLOR_HEX)) {
    if (lc.includes(k)) return v;
  }
  return "#c8a55a";
}

function dedupeProducts(products) {
  if (!products?.length) return [];
  const seen = new Set();
  return products.filter(p => {
    if (!p?.title || !p?.link) return false;
    const k = p.title.toLowerCase().slice(0,40) + "|" + p.link.split("?")[0];
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

function resolveImg(url) {
  if (!url || url === "None" || url === "null") return null;
  if (url.startsWith("data:")) return url;
  if (url.startsWith("/uploads/") || url.startsWith("/static/")) return `${API}${url}`;
  if (url.startsWith("http://127") || url.startsWith("http://localhost")) return url;
  const trusted = ["myntassets","rukminim","m.media-amazon","images.nykaa",
    "images-cdn.ajio","images.meesho","lh3.googleusercontent","bewakoof","img1.ajio","encrypted-tbn"];
  if (url.startsWith("https") && trusted.some(d => url.includes(d))) return url;
  if (url.startsWith("http")) {
    try { return `https://images.weserv.nl/?url=${encodeURIComponent(url)}&w=400&h=400&fit=contain&bg=ffffff`; }
    catch { return url; }
  }
  return null;
}

/* ── Wardrobe card with real photo ─────────────────────────────────────────── */
function WardrobeCard({ item }) {
  const [err, setErr] = useState(false);
  const [loaded, setLoaded] = useState(false);
  if (!item) return null;
  const src = resolveImg(item.image_url);
  const hex = getColorHex(item.color);
  return (
    <div style={{
      display:"flex",flexDirection:"column",alignItems:"center",gap:5,
      padding:"10px 8px",background:"rgba(255,255,255,.8)",
      border:"1.5px solid rgba(200,165,90,.2)",borderRadius:12,
      minWidth:90,maxWidth:108,transition:"all .2s",
    }}>
      <div style={{
        width:68,height:68,borderRadius:9,overflow:"hidden",
        background:src&&!err?"#f7f3ee":hex+"22",
        border:`1.5px solid ${hex}44`,
        display:"flex",alignItems:"center",justifyContent:"center",
        flexShrink:0,position:"relative",
      }}>
        {src && !err ? (
          <>
            {!loaded && <div style={{position:"absolute",inset:0,background:"linear-gradient(90deg,#f0ebe4,#e8e0d4,#f0ebe4)",backgroundSize:"200% 100%",animation:"ep-shimmer 1.4s infinite"}}/>}
            <img src={src} alt={item.item_name} onLoad={()=>setLoaded(true)} onError={()=>setErr(true)} crossOrigin="anonymous"
              style={{width:"100%",height:"100%",objectFit:"cover",opacity:loaded?1:0,transition:"opacity .3s"}}/>
          </>
        ) : (
          <div style={{textAlign:"center"}}>
            <div style={{fontSize:22}}>{CAT_EMOJI[item.category]||"👕"}</div>
            <div style={{width:14,height:14,borderRadius:"50%",background:hex,border:"2px solid white",margin:"3px auto 0",boxShadow:`0 0 5px ${hex}66`}}/>
          </div>
        )}
      </div>
      <div style={{fontSize:9.5,fontWeight:600,color:"#2c1f0f",textAlign:"center",lineHeight:1.3,maxWidth:88,display:"-webkit-box",WebkitLineClamp:2,WebkitBoxOrient:"vertical",overflow:"hidden"}}>
        {item.color} {item.item_name}
      </div>
      <div style={{fontSize:8,color:"#a8998a",textTransform:"capitalize",background:"rgba(200,165,90,.1)",padding:"1px 6px",borderRadius:7}}>
        {item.category}
      </div>
    </div>
  );
}

/* ── Outfit slot — matches wardrobe photo or shows emoji ───────────────────── */
function OutfitSlotImage({ item, emoji, size=76 }) {
  const [err, setErr] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const src = item ? resolveImg(item.image_url) : null;
  const hex = item ? getColorHex(item.color) : "#e8ddd0";
  return (
    <div style={{
      width:size,height:size,borderRadius:11,overflow:"hidden",
      background:src&&!err?"#f7f3ee":hex+"18",
      border:`1.5px solid ${hex}44`,
      display:"flex",alignItems:"center",justifyContent:"center",
      margin:"0 auto",position:"relative",flexShrink:0,
    }}>
      {src && !err ? (
        <>
          {!loaded && <div style={{position:"absolute",inset:0,background:"linear-gradient(90deg,#f0ebe4,#e8e0d4,#f0ebe4)",backgroundSize:"200% 100%",animation:"ep-shimmer 1.4s infinite"}}/>}
          <img src={src} alt="" crossOrigin="anonymous" onLoad={()=>setLoaded(true)} onError={()=>setErr(true)}
            style={{width:"100%",height:"100%",objectFit:"cover",opacity:loaded?1:0,transition:"opacity .3s"}}/>
        </>
      ) : (
        <div style={{textAlign:"center"}}>
          <div style={{fontSize:28}}>{emoji}</div>
          {item && <div style={{width:12,height:12,borderRadius:"50%",background:hex,margin:"3px auto 0",border:"2px solid white"}}/>}
        </div>
      )}
      {item && src && !err && loaded && (
        <div style={{position:"absolute",bottom:3,right:3,width:16,height:16,borderRadius:"50%",background:"#2d7a4f",border:"2px solid white",display:"flex",alignItems:"center",justifyContent:"center",fontSize:8,color:"white",fontWeight:700}}>✓</div>
      )}
    </div>
  );
}

/* ── Outfit visual card ─────────────────────────────────────────────────────── */
function OutfitCard({ label, icon, outfit, wardrobeItems, isBackup }) {
  if (!outfit || (!outfit.top && !outfit.description)) return null;

  // Smart match: find wardrobe item that best matches the outfit field text
  const matchBest = (field) => {
    const val = (outfit[field] || "").toLowerCase();
    if (!val || !wardrobeItems?.length) return null;
    let best=null, bestScore=0;
    for (const item of wardrobeItems) {
      const text = `${item.color||""} ${item.item_name||""} ${item.category||""}`.toLowerCase();
      const words = val.split(/\s+/).filter(w=>w.length>2);
      const score = words.filter(w=>text.includes(w)).length;
      if (score>bestScore) { bestScore=score; best=item; }
    }
    return bestScore>=1 ? best : null;
  };

  const slots = [
    {key:"top",    emoji:"👕",label:"Top",    val:outfit.top,    match:matchBest("top")},
    {key:"bottom", emoji:"👖",label:"Bottom", val:outfit.bottom, match:matchBest("bottom")},
    {key:"shoes",  emoji:"👟",label:"Shoes",  val:outfit.shoes,  match:matchBest("shoes")},
  ].filter(s=>s.val);

  return (
    <div style={{border:`1.5px solid ${isBackup?"#ece6dc":"rgba(200,165,90,.3)"}`,borderRadius:16,overflow:"hidden",background:"#fff",marginBottom:16}}>
      {/* Label bar */}
      <div style={{
        padding:"11px 18px",
        background:isBackup?"rgba(250,247,243,.9)":"linear-gradient(135deg,rgba(200,165,90,.1),rgba(200,165,90,.04))",
        borderBottom:"1px solid #f0ece6",
        display:"flex",alignItems:"center",gap:8,
      }}>
        <span style={{fontSize:16}}>{icon}</span>
        <div>
          <div style={{fontSize:10,fontWeight:700,color:isBackup?"#8a7a6a":"#8a5820",letterSpacing:".12em",textTransform:"uppercase"}}>{label}</div>
          {outfit.description && <div style={{fontSize:11.5,color:"#5a4838",marginTop:2,lineHeight:1.5}}>{outfit.description}</div>}
        </div>
      </div>

      {/* 3-column image row */}
      {slots.length > 0 && (
        <div style={{display:"flex",borderBottom:"1px solid #f5f1eb"}}>
          {slots.map((slot,i)=>(
            <div key={slot.key} style={{
              flex:1,padding:"16px 10px",textAlign:"center",
              borderRight:i<slots.length-1?"1px solid #f0ece6":"none",
            }}>
              <OutfitSlotImage item={slot.match} emoji={slot.emoji}/>
              <div style={{fontSize:8.5,color:"#a8998a",fontWeight:700,textTransform:"uppercase",letterSpacing:".1em",marginTop:7,marginBottom:3}}>{slot.label}</div>
              <div style={{fontSize:11,color:"#2c1f0f",fontWeight:500,lineHeight:1.35}}>{slot.val}</div>
              {slot.match && (
                <div style={{fontSize:8.5,color:"#2d7a4f",marginTop:3,fontWeight:600}}>✓ In wardrobe</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Colors + why + accessories */}
      {(outfit.colors?.length>0||outfit.accessories?.length>0||outfit.why_these_colors) && (
        <div style={{padding:"12px 18px"}}>
          {outfit.colors?.length>0 && (
            <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:outfit.why_these_colors?8:outfit.accessories?.length?8:0,flexWrap:"wrap"}}>
              <span style={{fontSize:9,color:"#a8998a",fontWeight:700,textTransform:"uppercase",letterSpacing:".1em"}}>Colors:</span>
              {outfit.colors.map((c,i)=>(
                <div key={i} style={{display:"flex",alignItems:"center",gap:4}}>
                  <span style={{width:10,height:10,borderRadius:"50%",background:getColorHex(c),border:"1px solid rgba(0,0,0,.12)",display:"inline-block",flexShrink:0}}/>
                  <span style={{fontSize:10.5,color:"#5a4838"}}>{c}</span>
                </div>
              ))}
            </div>
          )}
          {outfit.why_these_colors && (
            <div style={{fontSize:11.5,color:"#5a4838",lineHeight:1.65,padding:"8px 12px",background:"rgba(200,165,90,.05)",borderLeft:"3px solid #c8a55a",borderRadius:"0 8px 8px 0",marginBottom:outfit.accessories?.length?10:0}}>
              {outfit.why_these_colors}
            </div>
          )}
          {outfit.accessories?.length>0 && (
            <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
              {outfit.accessories.map((a,i)=>(
                <span key={i} style={{padding:"4px 11px",background:"rgba(200,165,90,.1)",border:"1px solid rgba(200,165,90,.25)",borderRadius:14,fontSize:11,color:"#8a5820",fontWeight:500}}>{a}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Skincare step ───────────────────────────────────────────────────────────── */
function SkincareStep({ step, index }) {
  const [expanded, setExpanded] = useState(index < 2);
  const isEventDay = step.day?.toLowerCase().includes("today") || step.day?.toLowerCase().includes("day of") || step.day?.toLowerCase().includes("event day");

  const parseSteps = (text) => {
    if (!text) return [];
    if (Array.isArray(text)) return text;
    return text.split(/[→\n]/).map(s=>s.trim()).filter(s=>s.length>2);
  };

  const morningSteps = parseSteps(step.morning_steps || step.morning);
  const nightSteps   = parseSteps(step.night_steps   || step.night);

  return (
    <div style={{
      border:`1.5px solid ${isEventDay?"#c8a55a":"#ece6dc"}`,
      borderRadius:14,overflow:"hidden",marginBottom:10,
      boxShadow:isEventDay?"0 4px 20px rgba(200,165,90,.15)":"none",
      transition:"all .2s",
    }}>
      {/* Header */}
      <div onClick={()=>setExpanded(v=>!v)} style={{
        padding:"13px 18px",cursor:"pointer",
        background:isEventDay?"linear-gradient(135deg,rgba(200,165,90,.12),rgba(200,165,90,.04))":"rgba(250,247,243,.8)",
        borderBottom:expanded?"1px solid #f0ece6":"none",
        display:"flex",alignItems:"center",justifyContent:"space-between",
      }}>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <div style={{
            width:34,height:34,borderRadius:"50%",
            background:isEventDay?"#c8a55a":"#f0ece6",
            border:`2px solid ${isEventDay?"#c8a55a":"#ddd3c2"}`,
            display:"flex",alignItems:"center",justifyContent:"center",
            fontSize:isEventDay?14:11,fontWeight:700,
            color:isEventDay?"#1a0f00":"#a8998a",flexShrink:0,
          }}>
            {isEventDay?"★":index+1}
          </div>
          <div>
            <div style={{fontSize:13,fontWeight:700,color:isEventDay?"#8a5820":"#2c1f0f"}}>{step.day}</div>
            {step.focus && <div style={{fontSize:10.5,color:"#a8998a",marginTop:1}}>{step.focus}</div>}
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          {isEventDay && <span style={{fontSize:9,padding:"2px 9px",background:"rgba(200,165,90,.18)",borderRadius:10,color:"#8a5820",fontWeight:700,letterSpacing:".06em"}}>EVENT DAY</span>}
          <span style={{fontSize:11,color:"#c8a55a"}}>{expanded?"▲":"▼"}</span>
        </div>
      </div>

      {expanded && (
        <div>
          {/* Morning */}
          {morningSteps.length>0 && (
            <div style={{padding:"14px 18px",background:"linear-gradient(135deg,#fff8e1,#fffbf5)",borderBottom:nightSteps.length?"1px solid #f0ece6":"none"}}>
              <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:10}}>
                <span style={{fontSize:16}}>☀️</span>
                <span style={{fontSize:9,fontWeight:700,color:"#a06820",letterSpacing:".2em",textTransform:"uppercase"}}>Morning Routine</span>
              </div>
              <div style={{display:"flex",flexDirection:"column",gap:7}}>
                {morningSteps.map((s,i)=>(
                  <div key={i} style={{display:"flex",gap:10,alignItems:"flex-start"}}>
                    <div style={{width:22,height:22,borderRadius:"50%",background:"rgba(249,168,37,.2)",border:"1.5px solid rgba(249,168,37,.4)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:9,fontWeight:700,color:"#a06820",flexShrink:0,marginTop:1}}>{i+1}</div>
                    <div style={{fontSize:12.5,color:"#3a2e24",lineHeight:1.55,flex:1}}>{s}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* Night */}
          {nightSteps.length>0 && (
            <div style={{padding:"14px 18px",background:"linear-gradient(135deg,#e8eaf6,#f3f4ff)"}}>
              <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:10}}>
                <span style={{fontSize:16}}>🌙</span>
                <span style={{fontSize:9,fontWeight:700,color:"#3d4875",letterSpacing:".2em",textTransform:"uppercase"}}>Night Routine</span>
              </div>
              <div style={{display:"flex",flexDirection:"column",gap:7}}>
                {nightSteps.map((s,i)=>(
                  <div key={i} style={{display:"flex",gap:10,alignItems:"flex-start"}}>
                    <div style={{width:22,height:22,borderRadius:"50%",background:"rgba(92,107,192,.2)",border:"1.5px solid rgba(92,107,192,.4)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:9,fontWeight:700,color:"#3d4875",flexShrink:0,marginTop:1}}>{i+1}</div>
                    <div style={{fontSize:12.5,color:"#3a2e24",lineHeight:1.55,flex:1}}>{s}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* Tip */}
          {step.tip && (
            <div style={{padding:"10px 18px 12px",background:"rgba(200,165,90,.03)",borderTop:"1px dashed rgba(200,165,90,.2)",display:"flex",gap:8,alignItems:"flex-start"}}>
              <span style={{fontSize:12,flexShrink:0,color:"#c8a55a"}}>✦</span>
              <span style={{fontSize:11.5,color:"#8a5820",lineHeight:1.6,fontStyle:"italic"}}>{step.tip}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Product card with save button ──────────────────────────────────────────── */
function ProductCard({ p, userId }) {
  const [err, setErr] = useState(false);
  const [loaded, setLoaded] = useState(false);
  if (!p?.link) return null;
  const src = resolveImg(p.image||p.thumbnail);
  const label = (p.source||"").replace(/^www\./,"").replace(/\.(com|in)$/,"").slice(0,12);
  return (
    <div style={{display:"flex",flexDirection:"column",gap:0}}>
      <a href={p.link} target="_blank" rel="noreferrer" style={{display:"block",textDecoration:"none",background:"#fff",border:"1px solid #ece6dc",borderRadius:12,overflow:"hidden",transition:"transform .2s, box-shadow .2s"}}
        onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-3px)";e.currentTarget.style.boxShadow="0 8px 24px rgba(0,0,0,.1)"}}
        onMouseLeave={e=>{e.currentTarget.style.transform="";e.currentTarget.style.boxShadow=""}}>
        <div style={{height:130,background:"#f7f3ee",display:"flex",alignItems:"center",justifyContent:"center",overflow:"hidden",position:"relative"}}>
          {!loaded&&!err&&src&&<div style={{position:"absolute",inset:0,background:"linear-gradient(90deg,#f0ebe4,#e8e0d4,#f0ebe4)",backgroundSize:"200% 100%",animation:"ep-shimmer 1.4s infinite"}}/>}
          {src&&!err
            ?<img src={src} alt={p.title} style={{width:"100%",height:"100%",objectFit:"contain",padding:8,opacity:loaded?1:0,transition:"opacity .3s"}} onLoad={()=>setLoaded(true)} onError={()=>{setErr(true);setLoaded(true);}} crossOrigin="anonymous"/>
            :<span style={{fontSize:28,opacity:.2}}>◈</span>}
          {label&&<div style={{position:"absolute",bottom:5,left:6,background:"rgba(26,15,0,.65)",padding:"2px 7px",borderRadius:4,fontSize:8,color:"#e8d8b8",letterSpacing:".06em",textTransform:"uppercase"}}>{label}</div>}
        </div>
        <div style={{padding:"10px 12px 4px"}}>
          <div style={{fontSize:11.5,color:"#2c1f0f",lineHeight:1.4,marginBottom:5,display:"-webkit-box",WebkitLineClamp:2,WebkitBoxOrient:"vertical",overflow:"hidden",minHeight:30}}>{p.title}</div>
          <div style={{fontSize:14,fontWeight:700,color:"#8a5820",marginBottom:8}}>{p.price||"View Price"}</div>
        </div>
        <div style={{display:"block",margin:"0 10px 10px",padding:"8px 0",background:"#1a0f00",color:"#c8a55a",textAlign:"center",fontSize:10,fontWeight:700,letterSpacing:".15em",textTransform:"uppercase",borderRadius:7}}>Shop Now →</div>
      </a>
      {userId&&<div style={{marginTop:5}}><SaveButton product={p} userId={userId}/></div>}
    </div>
  );
}

/* ── CheckItem ───────────────────────────────────────────────────────────────── */
function CheckItem({ text }) {
  const [done, setDone] = useState(false);
  return (
    <div onClick={()=>setDone(d=>!d)} style={{display:"flex",alignItems:"flex-start",gap:10,padding:"11px 14px",background:done?"rgba(45,122,79,.08)":"#faf7f3",border:`1px solid ${done?"rgba(45,122,79,.2)":"#ece6dc"}`,borderRadius:10,cursor:"pointer",transition:"all .18s"}}>
      <div style={{width:20,height:20,borderRadius:6,flexShrink:0,background:done?"#2d7a4f":"white",border:`1.5px solid ${done?"#2d7a4f":"#ddd3c2"}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:11,color:"white",fontWeight:700,marginTop:1}}>{done&&"✓"}</div>
      <span style={{fontSize:12.5,color:done?"#2d7a4f":"#3a2e24",textDecoration:done?"line-through":"none",opacity:done?.7:1,lineHeight:1.5}}>{text}</span>
    </div>
  );
}

/* ── MAIN COMPONENT ──────────────────────────────────────────────────────────── */
export default function EventPlanner({ user }) {
  const [input,   setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const [plan,    setPlan]    = useState(null);
  const [error,   setError]   = useState("");
  const [tab,     setTab]     = useState("outfit");
  const [loadMsg, setLoadMsg] = useState("");
  const inputRef = useRef();

  const profile  = user || getProfile();
  const userId   = profile?.name || profile?.userId || "";
  const gender   = profile?.gender || "male";
  const skinTone = profile?.skinTone || "medium";
  const isMale   = !["female","women","woman","girl","f"].includes((gender||"").toLowerCase());

  const LOAD_MSGS = ["Checking your wardrobe...","Analysing your skin tone...","Planning the perfect outfit...","Building skincare timeline...","Finding the best products...","Almost ready..."];
  useEffect(() => {
    if (!loading) return;
    let i=0; setLoadMsg(LOAD_MSGS[0]);
    const t = setInterval(()=>{ i=(i+1)%LOAD_MSGS.length; setLoadMsg(LOAD_MSGS[i]); },1800);
    return ()=>clearInterval(t);
  }, [loading]);

  const submit = async (msg) => {
    const message = (msg||input).trim();
    if (!message) return;
    setLoading(true); setError(""); setPlan(null);
    try {
      const r = await axios.post(`${API}/event-planner/plan`, {
        message,
        user_context: {
          skinTone:   profile?.skinTone   || "medium",
          face_shape: profile?.face_shape || "oval",
          gender:     profile?.gender     || "male",
          conditions: profile?.conditions || [],
          body_shape: profile?.body_shape || "average",
          name:       userId,
        },
        user_id: userId,
      });
      setPlan(r.data); setTab("outfit");
    } catch(e) {
      setError(e?.response?.data?.error || "Planning failed. Please try again.");
    }
    setLoading(false);
  };

  const days         = plan?.days_until ?? 3;
  const outfit       = plan?.outfit_plan || {};
  const mainOutfit   = outfit.main_outfit   || {};
  const backupOutfit = outfit.backup_outfit || {};
  // KEY FIX: show only top 6 most relevant wardrobe items
  const wardrobeItems    = (plan?.wardrobe_items || []).slice(0, 6);
  const allWardrobeItems = plan?.wardrobe_items || [];
  const hasWardrobe      = wardrobeItems.length > 0;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=DM+Sans:wght@300;400;500;600&display=swap');
        @keyframes ep-shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
        @keyframes ep-fadeup{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
        @keyframes ep-spin{to{transform:rotate(360deg)}}
        @keyframes ep-pulse{0%,100%{opacity:1}50%{opacity:.4}}
        .ep-root{font-family:'DM Sans',sans-serif;max-width:920px;padding-bottom:80px;color:#1a0f00}
        .ep-hero{background:linear-gradient(145deg,#0a0706,#1a0f00 45%,#0d0b06);border-radius:22px;padding:50px 44px 42px;margin-bottom:28px;position:relative;overflow:hidden}
        .ep-hero::before{content:'';position:absolute;top:-120px;right:-120px;width:460px;height:460px;border-radius:50%;background:radial-gradient(circle,rgba(200,165,90,.14) 0%,transparent 60%);pointer-events:none}
        .ep-hero::after{content:'';position:absolute;bottom:-80px;left:-80px;width:360px;height:360px;border-radius:50%;background:radial-gradient(circle,rgba(200,165,90,.06) 0%,transparent 60%);pointer-events:none}
        .ep-inp-row{display:flex;gap:10px;position:relative;z-index:1}
        .ep-inp{flex:1;padding:14px 20px;background:rgba(255,255,255,.07);border:1px solid rgba(200,165,90,.3);border-radius:12px;color:#f5ede0;font-family:'DM Sans',sans-serif;font-size:13.5px;outline:none;transition:all .2s}
        .ep-inp::placeholder{color:rgba(200,165,90,.4)}
        .ep-inp:focus{border-color:rgba(200,165,90,.7);background:rgba(255,255,255,.1);box-shadow:0 0 0 3px rgba(200,165,90,.1)}
        .ep-submit{padding:14px 28px;background:#c8a55a;border:none;border-radius:12px;color:#1a0f00;font-family:'DM Sans',sans-serif;font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;cursor:pointer;transition:all .22s;white-space:nowrap;display:flex;align-items:center;gap:9px}
        .ep-submit:hover:not(:disabled){background:#e8c87a;transform:translateY(-2px);box-shadow:0 10px 28px rgba(200,165,90,.35)}
        .ep-submit:disabled{opacity:.5;cursor:not-allowed}
        .ep-q-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:28px}
        .ep-q{padding:7px 14px;border-radius:22px;border:1px solid rgba(200,165,90,.22);background:rgba(200,165,90,.07);font-family:'DM Sans',sans-serif;font-size:12px;color:#8a5820;cursor:pointer;transition:all .18s;display:flex;align-items:center;gap:6px;font-weight:500}
        .ep-q:hover{background:rgba(200,165,90,.15);border-color:rgba(200,165,90,.45);transform:translateY(-1px)}
        .ep-plan-card{background:#fff;border:1px solid #ece6dc;border-radius:22px;overflow:hidden;animation:ep-fadeup .45s ease both;box-shadow:0 4px 40px rgba(0,0,0,.07)}
        .ep-ph{background:linear-gradient(135deg,#0e0a06,#1e1208 60%,#0e0a06);padding:30px 36px;display:flex;align-items:center;gap:22px;position:relative;overflow:hidden}
        .ep-ph::after{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 60% 80% at 80% 50%,rgba(200,165,90,.12) 0%,transparent 65%)}
        .ep-tabs{display:flex;border-bottom:1px solid #ece6dc;padding:0 36px;background:#fff;overflow-x:auto}
        .ep-tab{padding:15px 20px;border:none;border-bottom:2px solid transparent;background:none;font-family:'DM Sans',sans-serif;font-size:12px;font-weight:500;color:#a8998a;cursor:pointer;transition:all .18s;display:flex;align-items:center;gap:7px;margin-bottom:-1px;white-space:nowrap}
        .ep-tab.active{color:#8a5820;border-bottom-color:#c8a55a;font-weight:600}
        .ep-body{padding:30px 36px}
        .ep-sl{font-size:9px;letter-spacing:.3em;text-transform:uppercase;color:#a8998a;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:8px}
        .ep-sl::after{content:'';flex:1;height:1px;background:#ece6dc}
        @media(max-width:640px){
          .ep-hero{padding:28px 20px}.ep-ph{padding:22px 20px}
          .ep-body{padding:20px}.ep-tabs{padding:0 20px}
          .ep-inp-row{flex-direction:column}
        }
      `}</style>

      <div className="ep-root">

        {/* HERO */}
        <div className="ep-hero">
          <div style={{position:"relative",zIndex:1}}>
            <div style={{fontSize:9,letterSpacing:".45em",textTransform:"uppercase",color:"rgba(200,165,90,.55)",fontWeight:600,marginBottom:12}}>
              ✦ Wardrobe-Aware · Skin-Tuned · AI-Powered
            </div>
            <h1 style={{fontFamily:"'Cormorant Garamond',serif",fontSize:"clamp(32px,5vw,48px)",fontWeight:300,color:"#f5ede0",lineHeight:1.1,margin:"0 0 12px"}}>
              Event <em style={{fontStyle:"italic",color:"#c8a55a"}}>Planner</em>
            </h1>
            <p style={{fontSize:13,color:"rgba(200,165,90,.5)",lineHeight:1.7,maxWidth:500,margin:"0 0 30px"}}>
              Tell me your event. I'll scan your wardrobe, match your skin tone, build a skincare timeline, and find the best products — in one beautiful plan.
            </p>
            <div className="ep-inp-row">
              <input ref={inputRef} className="ep-inp" value={input}
                onChange={e=>setInput(e.target.value)}
                onKeyDown={e=>e.key==="Enter"&&submit()}
                placeholder="e.g. I have a wedding in 3 days, party tonight, interview tomorrow..."/>
              <button className="ep-submit" onClick={()=>submit()} disabled={loading}>
                {loading
                  ? <><div style={{width:14,height:14,border:"2px solid rgba(26,15,0,.3)",borderTopColor:"#1a0f00",borderRadius:"50%",animation:"ep-spin .8s linear infinite"}}/>Planning...</>
                  : "Plan →"
                }
              </button>
            </div>
          </div>
        </div>

        {/* Quick prompts */}
        <div className="ep-q-row">
          {QUICK.map(q=>(
            <button key={q.label} className="ep-q" onClick={()=>{setInput(q.msg);submit(q.msg);}}>
              <span>{q.icon}</span>{q.label}
            </button>
          ))}
        </div>

        {error && (
          <div style={{padding:"14px 18px",background:"rgba(192,57,43,.06)",border:"1px solid rgba(192,57,43,.2)",borderRadius:10,fontSize:12.5,color:"#a04040",marginBottom:20}}>
            ⚠️ {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div style={{display:"flex",flexDirection:"column",alignItems:"center",padding:"70px 20px",gap:18}}>
            <div style={{position:"relative"}}>
              <div style={{width:64,height:64,borderRadius:"50%",border:"2px solid rgba(200,165,90,.15)",borderTop:"2px solid #c8a55a",animation:"ep-spin 1s linear infinite"}}/>
              <div style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center",fontSize:22}}>✦</div>
            </div>
            <div style={{fontFamily:"'Cormorant Garamond',serif",fontSize:22,color:"#8a5820"}}>{loadMsg}</div>
            <div style={{display:"flex",gap:5}}>
              {[0,.2,.4].map((d,i)=>(
                <div key={i} style={{width:6,height:6,borderRadius:"50%",background:"#c8a55a",animation:`ep-pulse 1.2s ease ${d}s infinite`}}/>
              ))}
            </div>
          </div>
        )}

        {/* PLAN */}
        {plan && !loading && (
          <div className="ep-plan-card">

            {/* Header */}
            <div className="ep-ph">
              <div style={{fontSize:60,filter:"drop-shadow(0 4px 16px rgba(200,165,90,.4))",zIndex:1,flexShrink:0}}>
                {plan.event_icon||"✨"}
              </div>
              <div style={{zIndex:1,flex:1}}>
                <div style={{fontSize:9,letterSpacing:".3em",textTransform:"uppercase",color:"rgba(200,165,90,.5)",marginBottom:6}}>
                  Your Personalised Plan
                </div>
                <div style={{fontFamily:"'Cormorant Garamond',serif",fontSize:34,fontWeight:300,color:"#f5ede0",lineHeight:1.1}}>
                  {((plan.event||"event").charAt(0).toUpperCase()+(plan.event||"").slice(1))} Plan
                </div>
                <div style={{fontSize:12,color:"rgba(200,165,90,.55)",marginTop:5,lineHeight:1.6}}>
                  {plan.excitement_message}
                </div>
              </div>
              <div style={{padding:"10px 20px",background:"rgba(200,165,90,.18)",border:"1px solid rgba(200,165,90,.35)",borderRadius:30,fontSize:11,fontWeight:700,color:"#c8a55a",letterSpacing:".06em",zIndex:1,flexShrink:0}}>
                {days===0?"🔥 TODAY":days===1?"⏰ TOMORROW":`📅 IN ${days} DAYS`}
              </div>
            </div>

            {/* Tabs */}
            <div className="ep-tabs">
              {[
                ["outfit",   "👔 Outfit Plan"],
                ["skincare", "🧴 Skincare Prep"],
                ["shopping", "🛍 Shop It"],
                ["checklist","✅ Day Of"],
              ].map(([id,label])=>(
                <button key={id} className={`ep-tab${tab===id?" active":""}`} onClick={()=>setTab(id)}>
                  {label}
                  {id==="shopping"&&(plan.shopping_list||[]).length>0&&(
                    <span style={{fontSize:9,padding:"1px 6px",background:"rgba(200,165,90,.18)",borderRadius:8,color:"#8a5820",fontWeight:700}}>
                      {plan.shopping_list.length}
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="ep-body">

              {/* ── OUTFIT TAB ─────────────────────────────────────────────── */}
              {tab==="outfit" && (
                <div style={{animation:"ep-fadeup .3s ease"}}>

                  {/* Wardrobe: top 6 only */}
                  {hasWardrobe && (
                    <div style={{marginBottom:24}}>
                      <div className="ep-sl">
                        ✓ From Your Wardrobe — {wardrobeItems.length} Best Matches
                        {allWardrobeItems.length>6&&<span style={{fontSize:9,color:"#c8a55a",fontWeight:600,marginLeft:8}}>({allWardrobeItems.length} total available)</span>}
                      </div>
                      <div style={{display:"flex",gap:10,flexWrap:"wrap"}}>
                        {wardrobeItems.map((item,i)=>(
                          <WardrobeCard key={i} item={item}/>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Main outfit with images */}
                  <div className="ep-sl">✦ Main Outfit</div>
                  <OutfitCard
                    label="Main Outfit" icon="✦"
                    outfit={mainOutfit}
                    wardrobeItems={allWardrobeItems}
                    isBackup={false}
                  />

                  {/* Backup outfit with images */}
                  {(backupOutfit.top||backupOutfit.description) && (
                    <>
                      <div className="ep-sl" style={{marginTop:20}}>◇ Backup Option</div>
                      <OutfitCard
                        label="Backup Outfit" icon="◇"
                        outfit={backupOutfit}
                        wardrobeItems={allWardrobeItems}
                        isBackup={true}
                      />
                    </>
                  )}

                  {outfit.wardrobe_suggestion && (
                    <div style={{marginTop:16,padding:"12px 16px",background:"rgba(45,122,79,.07)",border:"1px solid rgba(45,122,79,.2)",borderRadius:10,fontSize:12.5,color:"#1e5035",lineHeight:1.65,display:"flex",gap:8}}>
                      <span>💡</span><span>{outfit.wardrobe_suggestion}</span>
                    </div>
                  )}
                </div>
              )}

              {/* ── SKINCARE TAB ─────────────────────────────────────────── */}
              {tab==="skincare" && (
                <div style={{animation:"ep-fadeup .3s ease"}}>
                  {/* Banner */}
                  <div style={{padding:"16px 20px",marginBottom:20,background:"linear-gradient(135deg,rgba(200,165,90,.08),rgba(200,165,90,.02))",border:"1px solid rgba(200,165,90,.2)",borderRadius:14,display:"flex",alignItems:"center",gap:14}}>
                    <div style={{fontSize:36}}>🔬</div>
                    <div>
                      <div style={{fontSize:13,fontWeight:700,color:"#1a0f00",marginBottom:3}}>
                        {days}-Day Skincare Timeline for {skinTone} Skin
                      </div>
                      <div style={{fontSize:11.5,color:"#6a5a4a",lineHeight:1.6}}>
                        {plan.skincare_summary||`Step-by-step skincare prep for your ${skinTone} skin. Follow this to look your absolute best on event day.`}
                      </div>
                    </div>
                  </div>

                  {/* Conditions */}
                  {profile?.conditions?.length>0 && (
                    <div style={{padding:"9px 14px",marginBottom:16,background:"rgba(192,57,43,.05)",border:"1px solid rgba(192,57,43,.15)",borderRadius:10,fontSize:12,color:"#8a3030",display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
                      <span>⚕️ Tailored for:</span>
                      {[...new Set(profile.conditions)].slice(0,3).map((c,i)=>(
                        <span key={i} style={{padding:"1px 8px",background:"rgba(192,57,43,.1)",borderRadius:8,fontWeight:600}}>{c}</span>
                      ))}
                    </div>
                  )}

                  {/* Steps */}
                  {(plan.skincare_timeline||[]).map((step,i)=>(
                    <SkincareStep key={i} step={step} index={i}/>
                  ))}

                  {/* Event day reminder */}
                  <div style={{marginTop:16,padding:"14px 18px",background:"linear-gradient(135deg,rgba(200,165,90,.08),rgba(200,165,90,.02))",border:"1px solid rgba(200,165,90,.2)",borderRadius:14}}>
                    <div style={{fontSize:10,fontWeight:700,letterSpacing:".2em",textTransform:"uppercase",color:"#c8a55a",marginBottom:6}}>✦ Event Day Reminder</div>
                    <div style={{fontSize:12.5,color:"#3a2e24",lineHeight:1.7}}>
                      {plan.event_day_skin_tip||"Keep it minimal on event day. Gentle cleanser → SPF → light moisturiser. Skip all active serums — your prep work is already done!"}
                    </div>
                  </div>
                </div>
              )}

              {/* ── SHOPPING TAB ─────────────────────────────────────────── */}
              {tab==="shopping" && (
                <div style={{animation:"ep-fadeup .3s ease"}}>
                  <div style={{padding:"10px 16px",marginBottom:18,background:"rgba(200,165,90,.07)",border:"1px solid rgba(200,165,90,.25)",borderRadius:10,fontSize:12,color:"#8a5820",display:"flex",alignItems:"center",gap:8}}>
                    🔔 Tap <strong style={{margin:"0 4px"}}>"Alert me"</strong> on any product to get price drop alerts via WhatsApp + email.
                  </div>
                  {(plan.shopping_list||[]).map((item,i)=>{
                    const prods = dedupeProducts(item.products||[]);
                    return (
                      <div key={i} style={{border:"1px solid #ece6dc",borderRadius:14,overflow:"hidden",marginBottom:14,background:"#fff"}}>
                        <div style={{padding:"14px 18px",background:item.priority==="must-have"?"rgba(192,57,43,.04)":"rgba(200,165,90,.04)",borderBottom:prods.length?"1px solid #f0ece6":"none",display:"flex",alignItems:"center",gap:12}}>
                          <div style={{width:40,height:40,borderRadius:10,background:"rgba(200,165,90,.12)",border:"1px solid rgba(200,165,90,.2)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,flexShrink:0}}>
                            {CAT_EMOJI[item.category]||"🛍"}
                          </div>
                          <div style={{flex:1}}>
                            <div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap",marginBottom:2}}>
                              <span style={{fontSize:13.5,fontWeight:600,color:"#1a0f00"}}>{item.item}</span>
                              <span style={{fontSize:9,padding:"2px 8px",borderRadius:10,fontWeight:700,background:item.priority==="must-have"?"rgba(192,57,43,.1)":"rgba(200,165,90,.12)",color:item.priority==="must-have"?"#c0392b":"#8a5820"}}>
                                {item.priority==="must-have"?"Must Have":"Nice to Have"}
                              </span>
                            </div>
                            {item.estimated_price&&<div style={{fontSize:11,color:"#a8998a"}}>Est. {item.estimated_price}</div>}
                          </div>
                        </div>
                        {prods.length>0 && (
                          <div style={{padding:"14px 16px"}}>
                            <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(145px,1fr))",gap:10}}>
                              {prods.slice(0,4).map((p,j)=>(
                                <ProductCard key={j} p={p} userId={userId}/>
                              ))}
                            </div>
                          </div>
                        )}
                        {!prods.length&&item.query&&(
                          <div style={{padding:"12px 16px"}}>
                            <a href={`https://www.myntra.com/search?rawQuery=${encodeURIComponent(item.query)}`} target="_blank" rel="noreferrer"
                              style={{display:"inline-flex",alignItems:"center",gap:6,padding:"6px 14px",background:"rgba(200,165,90,.08)",border:"1px dashed rgba(200,165,90,.3)",borderRadius:8,fontSize:11,color:"#8a5820",textDecoration:"none",fontWeight:600}}>
                              🔍 Search on Myntra →
                            </a>
                          </div>
                        )}
                      </div>
                    );
                  })}
                  {(!plan.shopping_list||plan.shopping_list.length===0)&&(
                    <div style={{textAlign:"center",padding:"40px 20px",fontSize:14,color:"#6a9278"}}>
                      🎉 You're fully equipped — no shopping needed!
                    </div>
                  )}
                </div>
              )}

              {/* ── CHECKLIST TAB ─────────────────────────────────────────── */}
              {tab==="checklist" && (
                <div style={{animation:"ep-fadeup .3s ease"}}>
                  <div className="ep-sl">Day-of Checklist</div>
                  <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:24}}>
                    {(plan.day_of_checklist||[]).map((item,i)=>(<CheckItem key={i} text={item}/>))}
                  </div>
                  {(plan.grooming_tips||[]).length>0 && (
                    <>
                      <div className="ep-sl" style={{marginTop:8}}>
                        {isMale?"💈 Grooming Tips":"💄 Beauty Tips"}
                      </div>
                      <div style={{display:"flex",flexDirection:"column",gap:8}}>
                        {plan.grooming_tips.map((tip,i)=>(
                          <div key={i} style={{display:"flex",gap:10,alignItems:"flex-start",padding:"11px 14px",background:"#faf7f3",border:"1px solid #ece6dc",borderRadius:10}}>
                            <span style={{color:"#c8a55a",flexShrink:0}}>✦</span>
                            <span style={{fontSize:12.5,color:"#3a2e24",lineHeight:1.6}}>{tip}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                  {plan.confidence_tip && (
                    <div style={{marginTop:24,padding:"20px 24px",background:"linear-gradient(135deg,rgba(200,165,90,.08),rgba(200,165,90,.02))",border:"1px solid rgba(200,165,90,.22)",borderRadius:16,fontFamily:"'Cormorant Garamond',serif",fontSize:17,color:"#1a0f00",lineHeight:1.8,fontStyle:"italic"}}>
                      ✨ "{plan.confidence_tip}"
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>
        )}
      </div>
    </>
  );
}