# 🚀 DealHunter AI — Deployment Guide

Deploy the backend for free on **Render** (or Railway), and the frontend for free on **Vercel**. Total cost: **\$0/month**.

---

## Overview

```
[ Vercel (Next.js Frontend) ]  ──HTTPS──►  [ Render (Python Backend) ]
                                                      │
                                              [ SQLite Database ]
                                              [ Gemini AI API ]
```

---

## Part 1 — Deploy the Backend on Render (Free)

### Prerequisites
- A [Render account](https://render.com) (free signup, no card required)
- Your repository pushed to GitHub

### Step 1: Connect your repo to Render
1. Go to [render.com/dashboard](https://dashboard.render.com)
2. Click **New → Web Service**
3. Connect your GitHub account and select the `DealHunter_Ai` repository
4. Set **Root Directory** to `backend`

### Step 2: Configure the service
Render will auto-detect the `render.yaml` or `Procfile`. Confirm these settings:

| Setting | Value |
|---------|-------|
| **Name** | `dealhunter-backend` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free |

### Step 3: Set environment variables
In the Render dashboard → **Environment** tab, add:

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | Your Gemini API key |
| `FRONTEND_URL` | *(leave blank for now — fill after Vercel deploy)* |

Click **Save Changes** → **Manual Deploy**.

### Step 4: Copy your backend URL
After deployment, Render gives you a URL like:
```
https://dealhunter-backend.onrender.com
```
**Save this URL** — you will need it in Part 2.

> **Note:** Free Render services spin down after 15 minutes of inactivity and take ~30 seconds to cold-start on the next request. Upgrade to the Starter plan (\$7/mo) to keep it always-on.

---

## Alternative: Deploy Backend on Railway (Free Tier)

1. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub Repo**
2. Select your repository, set **Root Directory** to `backend`
3. Railway auto-detects the `Procfile`
4. Add environment variables: `GEMINI_API_KEY`, `FRONTEND_URL`
5. Your service URL will look like: `https://dealhunter-backend.up.railway.app`

---

## Part 2 — Deploy the Frontend on Vercel (Free)

### Prerequisites
- A [Vercel account](https://vercel.com) (free signup with GitHub)

### Step 1: Import your project
1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **Import Git Repository** → select `DealHunter_Ai`
3. Set **Root Directory** to `frontend`
4. Framework should auto-detect as **Next.js**

### Step 2: Add the backend URL environment variable
In the Vercel import wizard → **Environment Variables**:

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_API_URL` | `https://dealhunter-backend.onrender.com` (your Render URL from Part 1) |

> **Important:** The variable MUST start with `NEXT_PUBLIC_` so Next.js exposes it to the browser bundle.

### Step 3: Deploy
Click **Deploy**. Vercel builds and deploys your app. You will receive a URL like:
```
https://dealhunter-ai.vercel.app
```

---

## Part 3 — Link Frontend ↔ Backend (CORS)

### Update Backend CORS
1. Go back to your **Render dashboard** → **Environment**
2. Set `FRONTEND_URL` to your Vercel URL (e.g. `https://dealhunter-ai.vercel.app`)
3. Click **Save Changes** → Render will automatically redeploy

The backend `main.py` dynamically reads `FRONTEND_URL` and adds it to the CORS allow-list.

---

## Part 4 — PWA Installation (Mobile)

### Android (Chrome)
1. Open your Vercel URL in Chrome
2. Tap the **three-dot menu → Add to Home Screen**
3. Confirm — the app icon appears on your home screen
4. Opens fullscreen (no browser chrome)

### iOS (Safari)
1. Open your Vercel URL in Safari
2. Tap the **Share button → Add to Home Screen**
3. Confirm — the app icon appears on your home screen
4. Opens in standalone mode

> **Icon Setup:** Place your app icons at:
> - `frontend/public/icons/icon-192x192.png` (192×192 px)
> - `frontend/public/icons/icon-512x512.png` (512×512 px)
>
> You can generate these from any logo using [realfavicongenerator.net](https://realfavicongenerator.net)

---

## Environment Variable Summary

### Backend (`backend/.env` for local, Render dashboard for production)
```env
GEMINI_API_KEY=your_key_here
FRONTEND_URL=https://your-app.vercel.app
```

### Frontend (`frontend/.env.production` for local production build, Vercel dashboard for deployment)
```env
NEXT_PUBLIC_API_URL=https://dealhunter-backend.onrender.com
```

---

## Local Development (unchanged)

```bash
# Terminal 1 — Backend
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`, backend at `http://localhost:8000`.
The frontend automatically falls back to `http://localhost:8000` when `NEXT_PUBLIC_API_URL` is not set.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Backend cold-starts slowly on Render free tier | Normal — wait 30 seconds on first request |
| CORS errors in browser console | Make sure `FRONTEND_URL` in Render matches your exact Vercel URL (no trailing slash) |
| SSE stream drops frequently | Free Render instances have connection limits; upgrade to Starter or use Railway |
| Build fails on Vercel | Ensure **Root Directory** is set to `frontend`, not the repo root |
| `NEXT_PUBLIC_API_URL` undefined | Add it in Vercel → Project → Settings → Environment Variables, then redeploy |
