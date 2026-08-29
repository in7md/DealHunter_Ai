<div align="center">

# 🎯 DealHunter AI

### Real-time car deal valuation radar for the Bahrain market — powered by Gemini AI.

[![Backend](https://img.shields.io/badge/Backend-Python%20%7C%20Starlette-3776AB?style=for-the-badge&logo=python&logoColor=white)](backend/)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2015%20%7C%20TypeScript-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](frontend/)
[![AI](https://img.shields.io/badge/AI-Gemini%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![PWA Ready](https://img.shields.io/badge/PWA-Mobile%20Ready-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)](frontend/public/manifest.json)

> **Scan. Score. Strike.** — DealHunter AI continuously crawls 7 Bahraini car marketplaces, runs each listing through a multi-factor scoring engine backed by real market data and Gemini AI, and streams winning deals to your screen in real time.

</div>

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          BROWSER / MOBILE (PWA)                         │
│                                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  Next.js 15 Frontend (Vercel)                                    │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │  │
│   │  │ DealCard │  │DealModal │  │  Navbar  │  │AudioNotification│  │  │
│   │  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │  │
│   │                  EventSource (SSE) ──────────────────────────►  │  │
│   └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────│────────────────────────────────────────┘
                                 │  HTTPS / Server-Sent Events
┌────────────────────────────────▼────────────────────────────────────────┐
│                     Python Backend (Render / Railway)                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Starlette + SSE-Starlette  /api/scanner/stream                 │   │
│  └────────────────────┬────────────────────────────────────────────┘   │
│                        │                                                │
│       ┌────────────────▼──────────────────┐                            │
│       │         Adapter Layer (7 sources)  │                            │
│       │  OpenSooq · YallaMotor · Dubizzle  │                            │
│       │  Carsbh · RighCars · Facebook ·    │                            │
│       │  Instagram VIP                     │                            │
│       └────────────────┬──────────────────┘                            │
│                        │ RawListing                                     │
│       ┌────────────────▼──────────────────┐                            │
│       │  Core Engine                       │                            │
│       │  ├─ text_parser   (Gemini Flash)   │                            │
│       │  ├─ market_engine (IQR / SQLite)   │                            │
│       │  ├─ deal_scorer   (6-axis score)   │                            │
│       │  ├─ ai_analyzer   (Gemini insights)│                            │
│       │  └─ deduplicator  (fingerprinting) │                            │
│       └────────────────┬──────────────────┘                            │
│                        │                                                │
│              ┌─────────▼─────────┐                                     │
│              │  SQLite Database   │                                     │
│              │  (deals, history)  │                                     │
│              └───────────────────┘                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

The **frontend** connects to the backend via a single persistent **Server-Sent Events (SSE)** connection. The backend scrapes, parses, scores, and pushes each `ScoredDeal` as a JSON event the moment it is ready — no polling, no page refreshes.

---

## ✨ Key Features

- 🕸️ **7-Source Multi-Adapter Scraper** — Simultaneously crawls OpenSooq, YallaMotor, Dubizzle, Carsbh, RighCars, Facebook Marketplace, and Instagram VIP car channels using `httpx` and `BeautifulSoup`.

- 🧠 **Gemini-Powered Text Parsing** — Unstructured Arabic & English listing text (title, description) is fed to Gemini Flash to extract structured fields: `make`, `model`, `year`, `price_bhd`, `mileage_km`.

- 📊 **IQR Market Pricing Engine** — For each `(make, model, year ± 1)` combination, the engine queries its own growing SQLite database, removes outliers using the **Interquartile Range (Tukey fence)** method, and computes a clean `market_median` price.

- 🎯 **6-Axis Deal Scoring** — Every listing is scored 0–100 across six independent dimensions:

  | Axis | Max | What it measures |
  |---|---|---|
  | Price Discount | 30 | How far below market the ask price is |
  | Profit Margin | 25 | Absolute net profit after estimated costs |
  | Data Confidence | 15 | Completeness of listing data |
  | Demand Velocity | 10 | Brand liquidity (Toyota/Lexus score higher) |
  | Repair Risk | 10 | Condition signals from Arabic description |
  | Negotiation Signal | 10 | Urgency keywords (`مستعجل`, `negotiable`) |

- 📡 **Live SSE Streaming** — Deals are pushed to the browser the instant they are scored via `sse-starlette`, with zero latency compared to polling. The frontend maintains a deduplication layer using `fingerprint_hash` + cross-platform (make/model/year/price) matching.

- 🔔 **Audio Notifications** — A chime plays automatically when a new high-score deal (≥ 80) arrives, so you never miss a great opportunity.

- 📱 **PWA — Installable on Android & iOS** — Full `manifest.json`, `theme-color`, Apple Web App meta tags, and `viewport-fit: cover` for notch displays. Add to home screen for a fullscreen, app-like experience.

- 🧹 **Smart Deduplication** — SHA-256 fingerprint hashing prevents the same listing appearing twice, even across sources (cross-platform duplicate detection by make / model / year / price).

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Runtime | Python 3.11 |
| Web Framework | Starlette (ASGI) |
| Server | Uvicorn |
| Streaming | sse-starlette |
| HTTP Scraping | httpx + BeautifulSoup4 |
| Browser Scraping | Playwright (for JS-rendered sources) |
| AI Parsing & Insights | Google Gemini Flash (via `google-generativeai`) |
| Database | SQLite + aiosqlite (async) |
| Config | python-dotenv |

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS v3 |
| Icons | Lucide React |
| Font | Geist (local, `next/font`) |
| Real-time | Browser `EventSource` API (SSE) |
| PWA | Web App Manifest + Apple meta tags |

---

## 🚀 Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- A [Google Gemini API key](https://aistudio.google.com/apikey) (free tier available)

---

### 1 — Clone the repository

```bash
git clone https://github.com/your-username/DealHunter_Ai.git
cd DealHunter_Ai
```

---

### 2 — Set up the Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Copy the environment template and fill in your key
copy .env.example .env
```

Edit `backend/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
FRONTEND_URL=http://localhost:3000
```

Start the backend:
```bash
uvicorn app.main:app --reload --port 8000
```

Backend is live at **http://localhost:8000** — verify with:
```bash
curl http://localhost:8000/
# → {"status": "DealHunter AI Backend Running"}
```

---

### 3 — Set up the Frontend

```bash
# Open a new terminal from the project root
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Frontend is live at **http://localhost:3000** 🎉

---

### 4 — (Optional) Test the SSE stream directly

```bash
curl -N http://localhost:8000/api/scanner/stream?sources=mock
```

You should see JSON deal events streaming in the terminal within seconds using the built-in `mock` adapter.

---

## ☁️ Cloud Deployment

The project is fully configured for free-tier deployment:

| Service | Platform | Cost |
|---|---|---|
| Frontend | Vercel | Free |
| Backend | Render or Railway | Free |
| Database | SQLite (bundled) | Free |
| AI | Gemini Flash API | Free tier |

**See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the complete step-by-step guide**, including:
- Exact Vercel CLI commands to deploy from your terminal
- Render Blueprint (`render.yaml`) for 1-click backend deploy
- How to securely set `GEMINI_API_KEY` and `FRONTEND_URL`
- How to link frontend ↔ backend CORS after deployment
- PWA "Add to Home Screen" test instructions for Android & iOS

---

## 📁 Project Structure

```
DealHunter_Ai/
├── backend/
│   ├── app/
│   │   ├── adapters/          # 7 source-specific scrapers
│   │   │   ├── opensooq_adapter.py
│   │   │   ├── yallamotor_adapter.py
│   │   │   ├── dubizzle_adapter.py
│   │   │   ├── carsbh_adapter.py
│   │   │   ├── righcars_adapter.py
│   │   │   ├── facebook_adapter.py
│   │   │   ├── instagram_adapter.py
│   │   │   └── mock_adapter.py
│   │   ├── core/              # Business logic pipeline
│   │   │   ├── text_parser.py    # Gemini-powered field extraction
│   │   │   ├── market_engine.py  # IQR pricing engine
│   │   │   ├── deal_scorer.py    # 6-axis scoring model
│   │   │   ├── ai_analyzer.py    # Gemini deal insights
│   │   │   └── deduplicator.py   # Fingerprint deduplication
│   │   ├── database/          # SQLite models & connection
│   │   ├── routes/            # API routes (scanner SSE)
│   │   ├── config.py          # Settings from .env
│   │   └── main.py            # Starlette app + CORS
│   ├── Procfile               # Render/Railway start command
│   ├── render.yaml            # Render Blueprint config
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── public/
│   │   ├── manifest.json      # PWA manifest
│   │   └── icons/             # App icons (192px, 512px)
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx     # PWA meta tags + viewport
│   │   │   └── page.tsx       # Main radar dashboard
│   │   ├── components/
│   │   │   ├── DealCard.tsx
│   │   │   ├── DealModal.tsx
│   │   │   ├── Navbar.tsx
│   │   │   └── AudioNotification.tsx
│   │   └── lib/
│   │       └── types.ts       # TypeScript interfaces
│   ├── .env.production        # Production API URL template
│   └── next.config.mjs
│
├── DEPLOYMENT.md              # Free hosting step-by-step guide
└── run_all.bat                # One-click local startup (Windows)
```

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you would like to change.

---

## 📄 License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">

Built with ❤️ in Bahrain 🇧🇭

**[⭐ Star this repo](https://github.com/your-username/DealHunter_Ai)** if DealHunter AI helped you find a great deal!

</div>
"# DealHunter_Ai" 
