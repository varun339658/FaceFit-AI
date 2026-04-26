# FaceFit AI — Personalized Style & Skincare Intelligence Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react" />
  <img src="https/img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb" />
  <img src="https://img.shields.io/badge/LangChain-RAG-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Groq-LLaMA_3.3_70B-red?style=flat-square" />
</p>

> **FaceFit AI** is a full-stack AI-powered personal styling and skincare platform. Upload a selfie once — the system analyzes your face shape, skin tone, and skin conditions using computer vision, then gives you hyper-personalized outfit recommendations, skincare routines, wardrobe planning, and much more. Everything is tailored to you.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Core Features](#core-features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Feature Deep-Dive](#feature-deep-dive)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Getting Started](#getting-started)
- [Screenshots / UI Overview](#ui-overview)

---

## What It Does

FaceFit AI solves a real problem: most people don't know what clothes or skincare products actually work for their specific features. FaceFit fixes this by:

1. **Scanning your face once** — detects face shape, skin tone, acne, dark circles, dark spots using MediaPipe + YOLO
2. **Remembering your profile forever** — JWT auth, MongoDB persistence
3. **Giving AI-powered, skin-tone-aware outfit recommendations** from 20+ event types
4. **Managing your digital wardrobe** — upload clothes, get AI mix-and-match combinations
5. **Building a skincare routine** — ingredient-level recommendations using RAG + dermatology knowledge
6. **Tracking skin progress week over week** — before/after charts, trend analysis
7. **Scheduling outfit reminders** — WhatsApp + email notifications via Twilio + Gmail
8. **Planning events** — full outfit + skincare timeline for any upcoming event
9. **Analyzing your outfit photos** — AI rates your look 1–10 with specific improvement tips
10. **Virtual try-on** — live webcam accessory overlay (sunglasses, earrings, bracelets, rings, necklaces, hats)

---

## Core Features

### 🧠 AI Stylist Chatbot
- Conversational interface powered by **LLaMA 3.3 70B via Groq**
- Intent classifier routes messages to: outfit planning, skincare, wardrobe, gap analysis, weekly planner, style aesthetics, grooming, trends, color theory
- Context-aware: remembers conversation history (last 16 turns)
- Gender-aware: male users never get necklace/earrings suggestions; female users never get watches/sunglasses
- Event-aware: gym outfits never contain ethnic wear; wedding outfits never contain track pants

### 👗 Smart Wardrobe / Digital Closet
- Upload clothing photos → **Groq Vision (LLaMA 4 Scout/Maverick)** auto-detects: category, color, style, formality, occasion tags
- CV2 fallback detector if vision model is unavailable
- **Mix & Match Engine**: AI generates 4–6 distinct styled outfit combinations ranked by color harmony score (1–3)
- **Event-filtered wardrobe**: gym items are excluded from wedding suggestions, ethnic items excluded from gym
- **Style Gap Analysis**: shows exactly which events you're prepared for and what's missing
- **Multi-outfit planner**: 2–3 complete outfit options per event
- Color compatibility matrix with 100+ verified color pairs

### 🧴 AI Skincare Engine
- **YOLO v8** detects acne, dark circles, dark spots from face scan
- **RAG pipeline** (ChromaDB + SentenceTransformer + LangChain) retrieves relevant dermatology knowledge
- Generates ingredient-specific product search queries (e.g., "salicylic acid 2% BHA night serum for acne pore exfoliation India")
- Key rule enforced in code: acne → night serum is ALWAYS salicylic acid, never retinol
- Condition-specific explainer: plain-English breakdown of each skin condition with "use these" / "avoid these" ingredient lists
- **Weekly scan tracker**: upload selfies weekly, AI tracks acne count / dark circle count / dark spot count over time with bar charts and trend messages

### 🛍️ Product Search Engine
- Google Shopping API via **Serper** with dual API key rotation and caching
- Products fetched in parallel across all outfit categories
- Image resolution: tries CDN URLs first, falls back to weserv proxy for CORS safety
- **Budget filter**: users set ₹min–₹max, all products auto-filtered
- **Brand preference**: users save favourite brands (Zara, FabIndia, Nike…), injected into every search query
- **Price drop alerts**: save products, get WhatsApp + email alerts when price drops
- **Replace Item system**: AI replaces a single outfit category without touching the rest; learns from accept/reject feedback

### 📅 Outfit Scheduler
- Plan outfit → set date/time → get email (HTML) + WhatsApp reminder + Google Calendar event
- Twilio sandbox integration with detailed error messages for opt-in failures
- Imgur + Cloudinary + PUBLIC_BASE_URL image hosting fallback chain for WhatsApp media
- APScheduler background jobs (IST timezone)
- Full reminder management: list, delete, reschedule

### 🗓️ AI Event Planner
- Tell the AI about any upcoming event ("I have a wedding in 3 days")
- Returns: main outfit + backup outfit (with real wardrobe images), day-by-day skincare timeline, shopping list with real products, day-of checklist, grooming tips
- All wardrobe items shown with their actual uploaded photos
- Outfit slots match wardrobe items by color/name similarity scoring

### 📸 Occasion Photo Analyzer
- Upload any outfit photo → AI rates it 1–10 across 5 dimensions: color harmony, event appropriateness, fit quality, skin-tone match, style cohesion
- Identifies what went wrong and gives specific fix instructions
- Suggests a complete alternative outfit with real product recommendations
- Gender-aware: men never get necklace/earring suggestions in alternative outfits

### 🧍 Body Shape Detection
- MediaPipe Pose detects shoulder width, hip width, waist width ratios
- Classifies into: hourglass, rectangle, pear, apple, inverted triangle
- Returns curated outfit advice ("what works" / "what to avoid") + products specific to that shape

### ◉ Virtual Try-On
- Live webcam feed with real-time accessory overlay using MediaPipe Face Mesh + Hand tracking
- Supports: sunglasses, earrings, bracelet, ring, necklace, hat
- Background removal via **rembg** before overlaying
- Precise landmark-based placement (ear lobes for earrings, wrist for bracelet, ring finger for ring)

### 📊 Style Gap Analysis
- Maps your wardrobe against 20+ event types
- Tells you exactly which categories are missing for each event
- One-tap "Shop" button links to Myntra/Amazon for missing items

### 🎨 Color Palette Wheel
- Visual color harmony display for any outfit combination
- HSL-based harmony scoring: complementary, analogous, triadic detection
- Accent color suggestions per skin tone

### 🎨 Style Aesthetics Guide
- 10 aesthetics supported: Old Money, Streetwear, Minimalist, Athleisure, Boho, Indo Western, Smart Casual, Preppy, Hypebeast, Formal
- Each aesthetic has gender-specific product queries, key colors, key pieces, and items to avoid

### 🌤️ Weather-Aware Outfits
- Open-Meteo API (free, no key) fetches real-time weather for any Indian city
- Returns fabric tips, carry tips, color tips, outfit filters
- Injected into both formula selection and LLM narrative prompt
- Hot weather → recommends linen/cotton; rainy → avoids suede; cold → recommends layering

### 🤖 AI Outfit Image Generator
- Generates photorealistic outfit visualization using **Pollinations.ai (Flux model)**
- Builds highly specific prompts from outfit item details + skin tone + gender
- Falls back to Google Images fashion search if generation fails
- Retry with different seeds for best results

### 💬 WhatsApp Chatbot (webhook)
- Twilio webhook handles inbound WhatsApp messages
- Same AI stylist accessible via WhatsApp
- Looks up user profile by phone number from MongoDB

### 🧠 Style Learning System
- Records every "Love it" / "Replace this" interaction
- Builds per-user preference profile: liked colors, disliked colors, liked styles
- Rejected colors injected as `-color` hints in future product searches
- Style Preferences tab shows the user what the AI has learned about them

### 📈 Skin Progress Tracker
- Weekly scan workflow with face detection validation
- Before/after comparison with delta labels (↑/↓ counts)
- Bar chart per condition across all weeks
- Note system: add personal notes to each scan week
- AI trend message: "Your acne has decreased by 3 spots over 4 weeks — keep it up!"

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Web Framework | Flask 3.0 (Python) |
| AI Chat | Groq API — LLaMA 3.3 70B Versatile |
| Vision (clothing) | Groq Vision — LLaMA 4 Scout / Maverick |
| RAG Pipeline | LangChain + ChromaDB + SentenceTransformer (all-MiniLM-L6-v2) |
| Face Analysis | MediaPipe Face Mesh + Face Detection |
| Pose Analysis | MediaPipe Pose |
| Skin Detection | YOLO v8 (custom trained — acne, dark circles, dark spots) |
| Product Search | Serper API (Google Shopping + Images) |
| Database | MongoDB Atlas |
| Auth | Flask-JWT-Extended |
| Email | Gmail SMTP (smtplib) |
| WhatsApp | Twilio REST API |
| Scheduler | APScheduler (Background) |
| Image Generation | Pollinations.ai (Flux) |
| Background Removal | rembg |
| Weather | Open-Meteo API |
| Virtual Try-On | OpenCV + MediaPipe + rembg |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React 18 (Vite) |
| Routing | React Router v6 |
| HTTP Client | Axios |
| Styling | Inline CSS + CSS-in-JS (zero external UI libraries) |
| Charts | SVG-based custom bar charts |
| Fonts | Google Fonts (Cormorant Garamond + DM Sans) |
| Voice Input | Web Speech API (browser-native) |
| Camera | MediaStream API + MJPEG stream |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| Database | MongoDB Atlas (cloud) |
| Image Hosting | Imgur API / Cloudinary / Public server |
| Tunnel (dev) | ngrok |
| Model Files | YOLOv8 weights (`models/best.pt`) |

---

## System Architecture

```
User (Browser / WhatsApp)
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│  Chatbot │ Closet │ EventPlanner │ PhotoAnalyzer │ TryOn   │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API (axios)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask Backend                             │
│  /chat  /outfits  /closet  /skin  /scheduler  /auth  ...   │
└──────────────┬──────────────────────┬───────────────────────┘
               │                      │
    ┌──────────▼───────────┐  ┌───────▼──────────────────────┐
    │    AI / ML Layer     │  │       Data Layer              │
    │  Groq LLaMA 3.3 70B  │  │  MongoDB Atlas                │
    │  Groq Vision          │  │  - face_analysis              │
    │  YOLO v8 (skin)       │  │  - wardrobe                   │
    │  MediaPipe (pose/face)│  │  - outfit_reminders           │
    │  ChromaDB (RAG)       │  │  - saved_products             │
    │  SentenceTransformer  │  │  - user_brands / budgets      │
    └──────────────────────┘  │  - user_style_prefs           │
                               └───────────────────────────────┘
               │
    ┌──────────▼──────────────────────────────────────────────┐
    │               External APIs                              │
    │  Serper (Google Shopping) │ Open-Meteo (weather)         │
    │  Twilio (WhatsApp/SMS)    │ Gmail SMTP                   │
    │  Imgur / Cloudinary       │ Pollinations.ai (images)     │
    │  Google Calendar API      │                              │
    └─────────────────────────────────────────────────────────┘
```

---

## Feature Deep-Dive

### Face Scan & Registration Flow
1. User uploads selfie → `/register`
2. MediaPipe checks face is detected (rejects non-face images with 422)
3. YOLO v8 detects skin conditions (acne count, dark circles, dark spots)
4. MediaPipe Face Mesh extracts face shape (oval / round / square / heart)
5. OpenCV HSV analysis classifies skin tone (light / medium / dark)
6. MediaPipe Pose attempts body shape detection from the same image
7. All data saved to MongoDB → JWT issued → user redirected to chat

### Chatbot Intent Classification
The classifier (`_classify()`) routes messages through 10 priority levels:
1. Style aesthetics keywords (Old Money, Streetwear…)
2. Weekly planner / Gap analysis
3. Color theory / Grooming / Trends
4. Closet keywords → wardrobe actions
5. Ethnic keywords → wardrobe-first with ethnic filter
6. Event keywords → closet if wardrobe exists, else products
7. Skincare keywords
8. Fashion keywords
9. Both keywords
10. Affirmations / General chat

### Color Harmony Scoring
The `_color_pair_score()` function rates any two colors 1–3:
- **3** = Perfect match (navy + white, black + mustard, teal + cream…)
- **2** = Good combo (olive + khaki, black + navy…)
- **1** = Wearable / neutral
100+ color pairs are hardcoded from fashion color theory.

### Event-Based Outfit Validation
Each event has explicit forbidden keywords:
- **gym** → forbids: kurta, blazer, jeans, oxford, loafer, ethnic wear
- **beach** → forbids: formal, kurta, sherwani, blazer, suit
- **interview** → forbids: track pant, jogger, graphic tee, ethnic, kurta
- **office** → forbids: track pant, jogger, gym wear, graphic tee

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register user + full face analysis |
| GET | `/auth/me` | Get profile from JWT |
| POST | `/chat` | AI stylist chatbot |
| POST | `/outfits` | Weather-aware outfit recommendations |
| POST | `/closet/add` | Upload clothing item (AI auto-detects) |
| GET | `/closet/<user_id>` | Get all wardrobe items |
| DELETE | `/closet/<user_id>/<item_id>` | Remove wardrobe item |
| POST | `/closet/multi-outfit` | 2–3 outfit combos for an event |
| GET | `/closet/mix-match/<user_id>` | AI mix & match all combinations |
| GET | `/closet/gap-analysis/<user_id>` | Style gap report |
| GET | `/closet/color-palette/<user_id>` | Color harmony visualization |
| POST | `/skin/scan` | Weekly skin progress scan |
| GET | `/skin/progress/<user_id>` | Skin history + charts |
| POST | `/skin/explain` | Plain-English condition explanations |
| POST | `/products` | Skincare product recommendations |
| GET | `/products/saved/<user_id>` | Saved products / price alerts |
| POST | `/products/save` | Save product for price tracking |
| POST | `/products/price-check` | Manual price check |
| POST | `/scheduler/remind` | Schedule outfit reminder |
| GET | `/scheduler/reminders/<user_id>` | List all reminders |
| DELETE | `/scheduler/remind/<id>` | Cancel reminder |
| POST | `/detect-body-shape` | Body shape analysis from photo |
| POST | `/analyze-outfit-photo` | Rate outfit 1–10 + suggestions |
| POST | `/event-planner/plan` | Full AI event plan |
| GET | `/preferences/brands/<user_id>` | Get saved brands |
| POST | `/preferences/brands/<user_id>` | Add brands |
| GET | `/preferences/budget/<user_id>` | Get budget range |
| POST | `/preferences/budget/<user_id>` | Set budget range |
| POST | `/upload-accessory` | Upload accessory for try-on |
| GET | `/virtual-tryon` | Live webcam MJPEG stream |
| POST | `/search-outfit` | Upload image → find similar products |
| POST | `/outfit/replace-item` | AI replace single outfit item |
| POST | `/outfit/feedback` | Record style preference |
| GET | `/outfit/preferences/<user_id>` | Get learned style profile |
| POST | `/whatsapp/webhook` | Twilio WhatsApp webhook |

---

## Project Structure

```
facefit-ai/
│
├── app.py                          # Flask app entry point, blueprint registration
│
├── routes/
│   ├── auth_routes.py              # JWT auth: /auth/me, /auth/refresh, /auth/logout
│   ├── register_routes.py          # User registration + face scan + body shape
│   ├── chatbot_routes.py           # POST /chat
│   ├── fashion_routes.py           # POST /outfits (weather-aware)
│   ├── closet_routes.py            # Digital wardrobe CRUD + mix & match
│   ├── product_routes.py           # Skincare products
│   ├── skin_routes.py              # Skin recommendation
│   ├── skin_explain_route.py       # Condition explainer
│   ├── vision_routes.py            # Face analysis + outfit image search
│   ├── outfit_image_routes.py      # AI outfit image generation
│   ├── outfit_scheduler_routes.py  # Outfit reminders
│   ├── body_shape_routes.py        # Body shape detection
│   ├── budget_brand_routes.py      # Budget & brand preferences
│   ├── saved_products_routes.py    # Price drop alerts
│   ├── virtual_tryon_routes.py     # Live webcam try-on
│   ├── event_planner_routes.py     # AI event planner
│   ├── occasion_photo_analyzer_routes.py  # Outfit photo rating
│   ├── preference_routes.py        # Style learning preferences
│   └── whatsapp_webhook_routes.py  # Twilio WhatsApp
│
├── services/
│   ├── chat_service.py             # Core chatbot logic + intent classifier
│   ├── closet_agent.py             # Wardrobe AI: mix & match, outfit planning, gap analysis
│   ├── fashion_rag_service.py      # Fashion RAG + outfit formula library
│   ├── skin_rag_service.py         # Skincare RAG + routine generation
│   ├── skin_explainer_service.py   # Skin condition explainer
│   ├── product_service.py          # Serper product search + budget/brand filters
│   ├── vision_service.py           # YOLO + MediaPipe face analysis
│   ├── outfit_scheduler_service.py # Email/WhatsApp/Calendar reminder engine
│   ├── budget_brand_service.py     # Budget filter + brand preference logic
│   ├── weather_service.py          # Open-Meteo weather + outfit filters
│   ├── color_palette_service.py    # HSL color harmony analysis
│   └── complete_outfit_service.py  # Uploaded item → complete outfit engine
│
├── models/
│   └── best.pt                     # YOLOv8 custom model (acne, dark circles, dark spots)
│
├── rag_data/
│   ├── fashion_knowledge.txt       # Color theory, occasion rules, styling guide (~800 lines)
│   └── skincare_knowledge.txt      # Dermatology knowledge, ingredients, routines
│
├── uploads/                        # Uploaded images (served via /uploads/<filename>)
│
└── utils/
    └── db.py                       # MongoDB connection + shared collections
│
├── src/ (React frontend)
│   ├── pages/
│   │   ├── Chatbot.jsx             # Main chat UI + all feature tabs
│   │   ├── Register.jsx            # Registration + face validation
│   │   ├── Products.jsx            # Products display page
│   │   ├── Dashboard.jsx           # Face analysis dashboard
│   │   ├── TryOnPage.jsx           # Virtual try-on UI
│   │   ├── OutfitScheduler.jsx     # Reminder scheduling UI
│   │   ├── SkinProgress.jsx        # Weekly scan tracker
│   │   ├── SavedProducts.jsx       # Price alert management
│   │   ├── EventPlanner.jsx        # AI event planner UI
│   │   ├── OutfitPhotoAnalyzer.jsx # Outfit photo rating UI
│   │   ├── BodyShapeDetector.jsx   # Body shape upload + results
│   │   ├── BudgetBrandPanel.jsx    # Budget/brand preferences
│   │   ├── ColorPaletteWheel.jsx   # Color harmony visualization
│   │   ├── OutfitImageGenerator.jsx# AI outfit image generation
│   │   ├── VoiceInput.jsx          # Web Speech API mic button
│   │   ├── WeatherBanner.jsx       # Weather context strip
│   │   ├── ReplaceItem.jsx         # Item replacement + learning
│   │   ├── StylePreferences.jsx    # Learned style profile
│   │   ├── SkinConditionExplainer.jsx  # Skin condition cards
│   │   └── ProductCard.jsx         # Universal product card
│   └── App.jsx                     # Router setup
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Groq API (LLaMA 3.3 70B + Vision)
GROQ_API_KEY=your_groq_api_key

# MongoDB Atlas
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority

# JWT
JWT_SECRET_KEY=your_long_random_secret

# Serper (Google Shopping API) — dual keys for rotation
SERPER_API_KEY_1=your_serper_key_1
SERPER_API_KEY_2=your_serper_key_2

# Gmail (for email reminders)
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password

# Twilio (WhatsApp reminders)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Image hosting (for WhatsApp media)
IMGUR_CLIENT_ID=your_imgur_client_id
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Public URL (ngrok or deployed server for WhatsApp image URLs)
PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.app

# Google Calendar (optional)
GOOGLE_TOKEN_JSON=token.json
GOOGLE_CREDENTIALS_JSON=credentials.json
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB Atlas account (free tier works)
- Webcam (for virtual try-on feature)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/facefit-ai.git
cd facefit-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install flask flask-cors flask-jwt-extended pymongo langchain langchain-groq \
  langchain-community langchain-text-splitters langchain-huggingface chromadb \
  sentence-transformers mediapipe opencv-python ultralytics rembg pillow \
  requests apscheduler twilio python-dotenv pytz

# Place your YOLO model
# Put your trained best.pt into models/best.pt

# Start the backend
python app.py
# Runs on http://localhost:5000
```

### Frontend Setup

```bash
cd facefit-frontend  # or wherever your React code lives

npm install
npm run dev
# Runs on http://localhost:5173
```

### WhatsApp Setup (optional)
1. Create a Twilio account and get Sandbox credentials
2. Configure webhook URL: `POST https://your-url/whatsapp/webhook`
3. Users must send "join \<keyword\>" to +14155238886 to opt in
4. Run ngrok: `ngrok http 5000` and set `PUBLIC_BASE_URL` in `.env`

---

## UI Overview

The React frontend is a single-page app with these main tabs in the chat interface:

| Tab | Description |
|-----|-------------|
| **AI Stylist** | Main chat interface with outfit + skincare recommendations |
| **Digital Closet** | Upload clothes, mix & match, plan outfits, gap analysis |
| **Event Planner** | Full AI plan for any upcoming event |
| **Photo Analyzer** | Upload outfit photo → rated 1–10 with improvements |
| **Body Shape** | Upload full-body photo → shape detection + outfit advice |
| **Skin Progress** | Weekly scan tracker with charts |
| **Budget/Brands** | Set price range and favourite brands |
| **Price Alerts** | Saved products with price drop monitoring |
| **Scheduler** | Schedule outfit reminders via email/WhatsApp |
| **Try-On** | Live webcam accessory overlay |
| **My Style** | View what the AI has learned about your style |

---

## Key Design Decisions

**No external UI libraries** — the entire frontend is hand-crafted with inline CSS and CSS-in-JS, giving full control over the luxury aesthetic (Cormorant Garamond serif headings, gold `#c8a55a` accent, warm cream backgrounds).

**RAG over pure LLM** — skincare and fashion knowledge is stored in text files and indexed into ChromaDB. This means the AI never hallucinates ingredient names or styling rules — it retrieves from verified knowledge.

**Event-based outfit validation** — a hard-coded rule system ensures no inappropriate outfit mixing (gym clothes at weddings, ethnic wear at the gym). This runs both on wardrobe filtering and on product query sanitization.

**Dual-mode outfit response** — every closet query returns both a "From Your Wardrobe" section and a "Shop New" section simultaneously, giving the user maximum choice.

**Skin condition deduplication** — YOLO detects the same condition N times per frame. The backend deduplicates before any LLM call, so "acne acne acne acne" becomes just "acne".

---

## License

MIT License. See `LICENSE` for details.

---

## Author

Built by **Varun Reddy Mandadi** — a full-stack AI project combining computer vision, RAG, LLMs, real-time streaming, and a luxury fashion-forward UI into one cohesive platform.

---

*FaceFit AI — Your face. Your style.*
