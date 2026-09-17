# 🚀 Antigravity Quant AI - Institutional Trading Terminal

A high-predictability, autonomous dual-bid algorithmic cryptocurrency trading workstation powered by FastAPI, WebSockets, TradingView Lightweight Charts, and Bayesian regime-conditioned self-learning.

---

## 🌟 Core Architecture & Features
- **Institutional Dual-Bid Architecture**: Dedicated 2-slot autonomous position manager with dynamic ATR bracket stops, multi-stage partial take profits (40% at TP1, 40% at TP2, runner at TP3), and strict 1% max capital risk.
- **12-Pair Realtime Scanner**: Microsecond radar scanning top liquid pairs concurrently with institutional order book whale wall detection and CVD (Cumulative Volume Delta) flow tracking.
- **5-Rule Mandatory Pre-Trade Gatekeeper**: Multi-timeframe trend filter, order book liquidity imbalance verification, volatility corridor checks, and 1:2 R:R enforcement.
- **Bayesian Self-Learning Engine**: Dynamically adapts pattern weights and sizing multipliers based on real trade win rates and execution streaks across ranging, breakout, and trend regimes.
- **Interactive Cyber-Quant Interface**: High-density 60 FPS real-time terminal with live candlestick charting, interactive EMA toggles, and manual profit locking.

---

## 🌐 24/7 Free Cloud Deployment Guide

### Option 1: Render.com (Recommended - 1-Click Setup)
1. Fork or push this repository to your GitHub account (instructions below).
2. Go to [Render.com](https://render.com/) and create a free account (Sign in with GitHub).
3. Click **New +** → **Web Service** → Connect your repository `antigravity-quant-terminal`.
4. Render will automatically detect the settings from `render.yaml`:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
5. In the **Environment Variables** section, optionally add your keys:
   - `BINANCE_API_KEY`
   - `BINANCE_API_SECRET`
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `TRADING_MODE`: `SIMULATED_PAPER` (or `BINANCE_LIVE`)
6. Click **Create Web Service**. Your terminal will be live at `https://your-app-name.onrender.com`.

> 💡 **How to Keep Render 24/7 Awake for Free**:
> Render free web services spin down after 15 minutes of zero HTTP traffic. To keep it running **24/7/365 without sleeping**:
> 1. Create a free account at [cron-job.org](https://cron-job.org/) or [UptimeRobot.com](https://uptimerobot.com/).
> 2. Add an HTTP monitor pointing to `https://your-app-name.onrender.com/api/status` every **10 minutes**.
> 3. Your trading engine, scanner, and WebSocket terminal will stay awake 24/7 continuously!

---

### Option 2: Koyeb (True Always-On Free Nano Instance)
1. Go to [Koyeb.com](https://www.koyeb.com/) and create a free account.
2. Click **Create App** → **GitHub**.
3. Select your repository. Koyeb will automatically use the included `Dockerfile`.
4. Click **Deploy**. Koyeb free instances **do not spin down or sleep**, running 24/7 continuously with native WebSockets.

---

## 💻 Running Locally
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run local development server
python -m uvicorn server.main:app --host 127.0.0.1 --port 8500
```
Open your browser to `http://127.0.0.1:8500`.
