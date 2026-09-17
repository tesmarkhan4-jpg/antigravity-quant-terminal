"""
FastAPI Backend Server
Coordinates:
- Multi-Pair Opportunity Radar (12 Top Crypto Pairs)
- Order Book Whale Liquidity Radar (Live Binance Depth)
- 12-Point Institutional Checklist & 5-Rule Pre-Trade Safety Gatekeeper
- Autonomous Dual-Bid Execution (Slot 1 & Slot 2)
- Self-Learning AI Engine (SQLite Adaptive Recalibration)
- Realtime WebSockets & Dashboard API
"""
import os
import sys
import asyncio
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from market_data import (
    fetch_klines, fetch_multi_pair_klines, fetch_ticker_price,
    fetch_24h_stats, fetch_order_book_depth, fetch_1h_trend,
    fetch_order_flow_cvd, fetch_mtf_confluence,
    SUPPORTED_SYMBOLS, INTERVALS
)
from indicators import evaluate_expert_checklist
from ai_trader import ai_brain
from trade_engine import trade_engine, PKR_RATE
from learning_engine import learning_engine

app = FastAPI(title="Antigravity Quant AI High-Predictability Trading Terminal", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections: List[WebSocket] = []

# System State
current_symbol = "BTCUSDT"
current_interval = "15m"
latest_candles = []
latest_analysis = {}
latest_ai_decision = {}
latest_order_book = {}
multi_pair_radar_data = []

class OrderRequest(BaseModel):
    symbol: str
    type: str  # LONG or SHORT
    entry: float
    tp: float
    sl: float
    reason: str = "Manual Entry"
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    tp3: Optional[float] = None

class CloseRequest(BaseModel):
    position_id: str
    price: float = 0.0

class SettingsRequest(BaseModel):
    auto_trade: bool = True
    risk_pct: float = 1.0
    gemini_key: Optional[str] = ""
    pkr_rate: Optional[float] = None
    daily_target_pkr: Optional[float] = None

class ExchangeConfigRequest(BaseModel):
    trading_mode: str  # "SIMULATED_PAPER", "BINANCE_TESTNET", "BINANCE_LIVE"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    test_connection: Optional[bool] = False

@app.on_event("startup")
async def startup_event():
    print("[Server] Starting High-Predictability Multi-Pair Scanner and Dual-Bid Engine...")
    asyncio.create_task(market_monitoring_loop())

async def market_monitoring_loop():
    """Background task scanning all 12 pairs, order book depth, and gatekeeper rules."""
    global latest_candles, latest_analysis, latest_ai_decision, latest_order_book, current_symbol, current_interval, multi_pair_radar_data
    
    symbols_list = list(SUPPORTED_SYMBOLS.keys())
    last_ai_time = 0.0
    await asyncio.sleep(0.5)

    while True:
        try:
            # 1. Fetch live Order Book depth, 1H HTF trend, MTF confluence, and CVD Order Flow for active symbol
            ob_active = fetch_order_book_depth(current_symbol, limit=20)
            htf_active = fetch_1h_trend(current_symbol).get("trend", "NEUTRAL")
            mtf_active = fetch_mtf_confluence(current_symbol)
            flow_active = fetch_order_flow_cvd(current_symbol)
            latest_order_book = ob_active

            # 2. Fetch candles for all 12 pairs in parallel
            multi_candles = fetch_multi_pair_klines(symbols_list, current_interval, limit=60)
            radar_entries = []

            for sym, candles in multi_candles.items():
                if not candles or len(candles) < 20:
                    continue
                
                curr_price = candles[-1]["close"]
                prev_close = candles[0]["close"]
                change_pct = round(((curr_price - prev_close) / prev_close) * 100, 2) if prev_close else 0.0
                
                # Check active positions on tick (TP1, TP2, TP3 runner, Stop Loss)
                auto_closed = trade_engine.update_positions_on_tick(sym, curr_price)
                if auto_closed:
                    for ac in auto_closed:
                        print(f"[AUTONOMOUS EXIT] {ac['id']} ({ac['symbol']}) executed {ac['outcome']} @ ${ac['exit_price']} | Realized PnL: ${ac['realized_pnl']:+.2f} ({ac['realized_pnl_pkr']:+,.0f} PKR)")

                # Fetch order book depth & MTF for candidate
                ob_sym = ob_active if sym == current_symbol else {"bid_pct": 50.0, "ask_pct": 50.0, "bid_ask_ratio": 1.0}
                htf_sym = htf_active if sym == current_symbol else "NEUTRAL"
                mtf_sym = mtf_active if sym == current_symbol else None
                flow_sym = flow_active if sym == current_symbol else None

                chk = evaluate_expert_checklist(candles, order_book=ob_sym, htf_trend=htf_sym, mtf_data=mtf_sym, order_flow=flow_sym)
                opp_score = chk.get("opportunity_score", 50)
                win_prob = chk.get("predicted_win_probability", 70.0)
                gk = chk.get("gatekeeper", {})

                net_score = chk.get("net_score", 0.0)
                if net_score >= 2.5 and gk.get("all_passed", False):
                    verdict = "STRONG BUY"
                    action = "LONG"
                elif net_score >= 1.0:
                    verdict = "BUY"
                    action = "LONG"
                elif net_score <= -2.5 and gk.get("all_passed", False):
                    verdict = "STRONG SELL"
                    action = "SHORT"
                elif net_score <= -1.0:
                    verdict = "SELL"
                    action = "SHORT"
                else:
                    verdict = "WAIT / NEUTRAL"
                    action = "HOLD"

                s_trade = chk.get("suggested_trade", {})
                radar_entries.append({
                    "symbol": sym,
                    "name": SUPPORTED_SYMBOLS.get(sym, sym),
                    "price": curr_price,
                    "change_pct": change_pct,
                    "opp_score": opp_score,
                    "win_prob": win_prob,
                    "verdict": verdict,
                    "confidence": min(95, int(win_prob)),
                    "action": action,
                    "tp": s_trade.get("long_tp", 0.0) if action == "LONG" else s_trade.get("short_tp", 0.0),
                    "sl": s_trade.get("long_sl", 0.0) if action == "LONG" else s_trade.get("short_sl", 0.0),
                    "tp1": s_trade.get("long_tp1", 0.0) if action == "LONG" else s_trade.get("short_tp1", 0.0),
                    "tp2": s_trade.get("long_tp2", 0.0) if action == "LONG" else s_trade.get("short_tp2", 0.0),
                    "tp3": s_trade.get("long_tp3", 0.0) if action == "LONG" else s_trade.get("short_tp3", 0.0),
                    "dominant_pattern": chk.get("dominant_pattern", "Standard"),
                    "multiplier": chk.get("pattern_multiplier", 1.0),
                    "gatekeeper_passed": gk.get("all_passed", False),
                    "candles": candles,
                    "analysis": chk
                })

            radar_entries.sort(key=lambda x: x["opp_score"], reverse=True)
            multi_pair_radar_data = radar_entries

            # Update active chart data
            selected_entry = next((r for r in radar_entries if r["symbol"] == current_symbol), None)
            if selected_entry:
                latest_candles = selected_entry["candles"]
                latest_analysis = selected_entry["analysis"]
            elif radar_entries:
                latest_candles = radar_entries[0]["candles"]
                latest_analysis = radar_entries[0]["analysis"]
                current_symbol = radar_entries[0]["symbol"]

            # Run deep institutional AI reasoning for active chart with 15s cadence to stay within free API rate limits
            now_ts = asyncio.get_event_loop().time()
            if latest_analysis and (now_ts - last_ai_time >= 15.0 or not latest_ai_decision):
                latest_ai_decision = await asyncio.to_thread(ai_brain.analyze_market, current_symbol, current_interval, latest_analysis)
                last_ai_time = now_ts

            # 3. Autonomous Quantitative Multi-Pair Dual-Bid Execution (Enforcing Confluence, 3-Tier TP Ladder & High Win Prob)
            if trade_engine.auto_trade_enabled and not trade_engine.circuit_breaker_triggered:
                available_slots = trade_engine.max_slots - len(trade_engine.positions)
                existing_symbols = {p["symbol"] for p in trade_engine.positions}

                if available_slots > 0:
                    for candidate in radar_entries:
                        if available_slots <= 0:
                            break
                        
                        sym = candidate["symbol"]
                        if sym in existing_symbols:
                            continue  # Do not duplicate symbol in both slots

                        # High-Probability Execution Filter: Directional edge (LONG or SHORT) with Win Prob >= 62% and learned pattern health
                        is_actionable = candidate["action"] in ["LONG", "SHORT"]
                        has_statistical_edge = candidate["win_prob"] >= 62 and candidate.get("confidence", 60) >= 60
                        pattern_healthy = candidate.get("multiplier", 1.0) >= 0.90

                        if is_actionable and has_statistical_edge and pattern_healthy and candidate.get("gatekeeper_passed", False):
                            # Pin live execution price and levels
                            live_p = fetch_ticker_price(sym) if sym != current_symbol else candidate["price"]
                            if not live_p or live_p <= 0:
                                live_p = candidate["price"]

                            sl_dist = abs(candidate["price"] - candidate["sl"]) if candidate.get("sl") else (live_p * 0.012)
                            sl_dist = max(sl_dist, live_p * 0.006)
                            dec_prec = 5 if live_p < 0.1 else (4 if live_p < 2.0 else 2)

                            if candidate["action"] == "LONG":
                                entry_p = live_p
                                sl_p = round(live_p - sl_dist, dec_prec)
                                tp1_p = round(live_p + (sl_dist * 1.2), dec_prec)
                                tp2_p = round(live_p + (sl_dist * 2.0), dec_prec)
                                tp3_p = round(live_p + (sl_dist * 3.5), dec_prec)
                                tp_p = tp2_p
                            else:
                                entry_p = live_p
                                sl_p = round(live_p + sl_dist, dec_prec)
                                tp1_p = round(live_p - (sl_dist * 1.2), dec_prec)
                                tp2_p = round(live_p - (sl_dist * 2.0), dec_prec)
                                tp3_p = round(live_p - (sl_dist * 3.5), dec_prec)
                                tp_p = tp2_p

                            res = trade_engine.open_position(
                                sym,
                                candidate["action"],
                                entry_p,
                                tp_p,
                                sl_p,
                                f"Autonomous High-Probability: {candidate['verdict']} ({candidate['win_prob']}% Win Prob | {candidate['dominant_pattern']})",
                                candidate["analysis"],
                                tp1=tp1_p,
                                tp2=tp2_p,
                                tp3=tp3_p
                            )
                            if res.get("success"):
                                available_slots -= 1
                                existing_symbols.add(sym)
                                print(f"[Autonomous Dual-Bid] Placed {candidate['action']} on {sym} @ ${entry_p:,.4f} (Win Prob: {candidate['win_prob']}%, Opp Score: {candidate['opp_score']}) with 3-Tier TP Ladder!")

            # 4. Broadcast to all active WebSocket clients
            if active_connections:
                learning_stats = learning_engine.get_learning_summary()
                clean_radar = [
                    {
                        "symbol": r["symbol"], "name": r["name"], "price": r["price"],
                        "change_pct": r["change_pct"], "opp_score": r["opp_score"],
                        "win_prob": r["win_prob"], "verdict": r["verdict"],
                        "confidence": r["confidence"], "action": r["action"],
                        "pattern": r["dominant_pattern"], "multiplier": r["multiplier"],
                        "gatekeeper_passed": r["gatekeeper_passed"]
                    }
                    for r in radar_entries
                ]

                payload = {
                    "type": "TICK",
                    "symbol": current_symbol,
                    "interval": current_interval,
                    "current_price": latest_candles[-1]["close"] if latest_candles else 0.0,
                    "candles": latest_candles[-60:] if latest_candles else [],
                    "analysis": latest_analysis,
                    "ai": latest_ai_decision,
                    "order_book": latest_order_book,
                    "gatekeeper": latest_analysis.get("gatekeeper", {}),
                    "predicted_win_probability": latest_analysis.get("predicted_win_probability", 75.0),
                    "regime": latest_analysis.get("regime", {}),
                    "mtf": latest_analysis.get("mtf_data", {}),
                    "order_flow": latest_analysis.get("order_flow", {}),
                    "kelly": latest_analysis.get("kelly", {}),
                    "radar": clean_radar,
                    "learning": learning_stats,
                    "account": trade_engine.get_account_summary(),
                    "positions": trade_engine.positions,
                    "history": trade_engine.trade_history[:10]
                }
                
                dead = []
                for conn in active_connections:
                    try:
                        await conn.send_text(json.dumps(payload))
                    except Exception:
                        dead.append(conn)
                for d in dead:
                    if d in active_connections:
                        active_connections.remove(d)

        except Exception as e:
            print(f"[High-Predictability Loop Error] {e}")

        await asyncio.sleep(2.5)

# --- REST APIs ---

@app.get("/api/status")
async def get_status():
    global current_symbol, current_interval, latest_candles, latest_analysis, latest_ai_decision, latest_order_book, multi_pair_radar_data
    return {
        "symbol": current_symbol,
        "interval": current_interval,
        "supported_symbols": SUPPORTED_SYMBOLS,
        "intervals": INTERVALS,
        "candles": latest_candles[-60:] if latest_candles else [],
        "analysis": latest_analysis,
        "ai": latest_ai_decision,
        "order_book": latest_order_book,
        "gatekeeper": latest_analysis.get("gatekeeper", {}),
        "predicted_win_probability": latest_analysis.get("predicted_win_probability", 75.0),
        "radar": [
            {
                "symbol": r["symbol"], "name": r["name"], "price": r["price"],
                "change_pct": r["change_pct"], "opp_score": r["opp_score"],
                "win_prob": r["win_prob"], "verdict": r["verdict"],
                "confidence": r["confidence"], "action": r["action"]
            }
            for r in multi_pair_radar_data
        ],
        "learning": learning_engine.get_learning_summary(),
        "account": trade_engine.get_account_summary(),
        "positions": trade_engine.positions,
        "history": trade_engine.trade_history
    }

@app.get("/api/radar")
async def get_radar():
    return {"radar": multi_pair_radar_data}

@app.get("/api/depth")
async def get_depth():
    return {"order_book": latest_order_book}

@app.get("/api/learning")
async def get_learning():
    return learning_engine.get_learning_summary()

@app.post("/api/symbol")
async def change_symbol(data: Dict[str, str]):
    global current_symbol, current_interval, latest_candles, latest_order_book
    if "symbol" in data and data["symbol"] in SUPPORTED_SYMBOLS:
        current_symbol = data["symbol"]
    if "interval" in data and data["interval"] in INTERVALS:
        current_interval = data["interval"]
    latest_candles = fetch_klines(current_symbol, current_interval, limit=100)
    latest_order_book = fetch_order_book_depth(current_symbol, limit=20)
    return {"success": True, "symbol": current_symbol, "interval": current_interval}

@app.post("/api/order")
async def place_order(order: OrderRequest):
    res = trade_engine.open_position(
        symbol=order.symbol,
        position_type=order.type,
        current_price=order.entry,
        tp=order.tp,
        sl=order.sl,
        reason=order.reason,
        tp1=order.tp1,
        tp2=order.tp2,
        tp3=order.tp3
    )
    return res

@app.post("/api/close")
async def close_order(data: CloseRequest):
    pos_id = data.position_id
    closed = trade_engine.manual_close_position(pos_id)
    if closed:
        account_summary = trade_engine.get_account_summary()
        learning_summary = learning_engine.get_learning_summary()
        payload = {
            "type": "TICK",
            "account": account_summary,
            "positions": trade_engine.positions,
            "history": trade_engine.trade_history[:10],
            "learning": learning_summary,
            "closed_trade": closed
        }
        # Instant WebSocket broadcast to all connected UI clients
        dead = []
        for conn in active_connections:
            try:
                await conn.send_text(json.dumps(payload))
            except Exception:
                dead.append(conn)
        for d in dead:
            if d in active_connections:
                active_connections.remove(d)

        return {
            "success": True,
            "trade": closed,
            "account": account_summary,
            "positions": trade_engine.positions,
            "history": trade_engine.trade_history[:10],
            "learning": learning_summary
        }
    return {"success": False, "message": "Position not found"}

@app.post("/api/close_all")
async def close_all_orders():
    closed_list = []
    for pos in list(trade_engine.positions):
        closed = trade_engine.manual_close_position(pos["id"])
        if closed:
            closed_list.append(closed)
            
    account_summary = trade_engine.get_account_summary()
    learning_summary = learning_engine.get_learning_summary()
    payload = {
        "type": "TICK",
        "account": account_summary,
        "positions": trade_engine.positions,
        "history": trade_engine.trade_history[:10],
        "learning": learning_summary
    }
    dead = []
    for conn in active_connections:
        try:
            await conn.send_text(json.dumps(payload))
        except Exception:
            dead.append(conn)
    for d in dead:
        if d in active_connections:
            active_connections.remove(d)

    return {
        "success": True,
        "closed_count": len(closed_list),
        "account": account_summary,
        "positions": trade_engine.positions,
        "history": trade_engine.trade_history[:10],
        "learning": learning_summary
    }

@app.post("/api/reset_account")
def reset_account():
    trade_engine.reset_account(initial_balance=200.0)
    return {"success": True, "account": trade_engine.get_account_summary()}

@app.post("/api/settings")
def update_settings(settings: SettingsRequest):
    trade_engine.auto_trade_enabled = settings.auto_trade
    trade_engine.risk_per_trade_percent = max(min(settings.risk_pct, 5.0), 0.5)
    if settings.pkr_rate and settings.pkr_rate > 0:
        global PKR_RATE
        PKR_RATE = settings.pkr_rate
        trade_engine.pkr_rate = settings.pkr_rate
    if settings.daily_target_pkr and settings.daily_target_pkr > 0:
        trade_engine.daily_target_pkr_max = settings.daily_target_pkr
        trade_engine.daily_target_pkr_min = settings.daily_target_pkr * 0.5
    if settings.gemini_key:
        ai_brain.anthropic_key = settings.gemini_key
    return {"success": True, "account": trade_engine.get_account_summary()}

@app.get("/api/system_status")
async def get_system_status():
    return {
        "status": "ONLINE",
        "symbol": current_symbol,
        "interval": current_interval,
        "account": trade_engine.get_account_summary(),
        "regime": latest_analysis.get("regime", {}),
        "mtf": latest_analysis.get("mtf_data", {}),
        "order_flow": latest_analysis.get("order_flow", {}),
        "open_positions": len(trade_engine.positions),
        "history_count": len(trade_engine.trade_history)
    }

@app.post("/api/reset_circuit")
def reset_circuit():
    trade_engine.reset_circuit_breaker()
    return {"success": True, "message": "Circuit breaker reset."}

def save_env_config(key: str = None, secret: str = None, mode: str = None):
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if not os.path.exists(env_path):
            return
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        has_mode = False
        for line in lines:
            if line.startswith("BINANCE_API_KEY=") and key:
                new_lines.append(f"BINANCE_API_KEY={key}\n")
            elif line.startswith("BINANCE_API_SECRET=") and secret:
                new_lines.append(f"BINANCE_API_SECRET={secret}\n")
            elif line.startswith("TRADING_MODE="):
                has_mode = True
                new_lines.append(f"TRADING_MODE={mode or trade_engine.trading_mode}\n")
            else:
                new_lines.append(line)
        if not has_mode and mode:
            new_lines.append(f"TRADING_MODE={mode}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"[Server] Note saving .env: {e}")

@app.get("/api/exchange_config")
def get_exchange_config():
    masked_key = ""
    if trade_engine.binance_api_key:
        k = trade_engine.binance_api_key
        masked_key = k[:6] + "..." + k[-4:] if len(k) > 10 else "***"
    return {
        "trading_mode": trade_engine.trading_mode,
        "is_real_trading": trade_engine.trading_mode == "BINANCE_LIVE",
        "exchange_connected": trade_engine.exchange_connected,
        "has_keys": bool(trade_engine.binance_api_key and trade_engine.binance_api_secret),
        "masked_key": masked_key,
        "account": trade_engine.get_account_summary()
    }

@app.get("/api/binance_wallet")
def get_binance_wallet():
    trade_engine.check_live_binance_balance()
    return {
        "success": True,
        "trading_mode": trade_engine.trading_mode,
        "is_real_trading": trade_engine.trading_mode == "BINANCE_LIVE",
        "live_usdt_balance": trade_engine.live_usdt_balance,
        "wallet_assets": trade_engine.live_wallet_assets,
        "connected": trade_engine.exchange_connected
    }

class ModeToggleRequest(BaseModel):
    mode: str  # "BINANCE_LIVE" or "SIMULATED_PAPER"

@app.post("/api/toggle_mode")
async def toggle_trading_mode(req: ModeToggleRequest):
    new_mode = "BINANCE_LIVE" if req.mode.upper() in ["REAL", "LIVE", "BINANCE_LIVE"] else ("BINANCE_TESTNET" if "TESTNET" in req.mode.upper() else "SIMULATED_PAPER")
    trade_engine.trading_mode = new_mode
    save_env_config(mode=new_mode)
    
    connected = False
    msg = ""
    if new_mode in ["BINANCE_LIVE", "BINANCE_TESTNET"]:
        if not (trade_engine.binance_api_key and trade_engine.binance_api_secret):
            return {"success": False, "message": f"No Binance API keys configured for {new_mode}. Enter keys in Settings first."}
        r, err = trade_engine.binance_signed_request("/api/v3/account", method="GET", timeout=12)
        if r is not None and r.status_code == 200:
            connected = True
            trade_engine.exchange_connected = True
            trade_engine.last_balance_check = 0
            trade_engine.check_live_binance_balance()
            msg = f"{new_mode} Active! Account verified (USDT: ${trade_engine.live_usdt_balance:.2f})"
        elif r is not None:
            connected = False
            trade_engine.exchange_connected = False
            try:
                err_json = r.json()
                code = err_json.get("code")
                api_msg = err_json.get("msg", r.text[:80])
                if code == -2015:
                    msg = "Binance Auth Failed (-2015): Invalid API-key, IP restriction, or missing Spot permission."
                else:
                    msg = f"Binance Auth Failed ({code}): {api_msg}"
            except Exception:
                msg = f"Binance Auth Failed: {r.text[:80]}"
        else:
            connected = False
            trade_engine.exchange_connected = False
            msg = f"Connection error: {err}"
    else:
        connected = True
        trade_engine.exchange_connected = True
        msg = "DEMO SIMULATION Mode Active ($200 Account Guard - Zero Risk)"

    return {
        "success": True,
        "trading_mode": trade_engine.trading_mode,
        "is_real_trading": trade_engine.trading_mode == "BINANCE_LIVE",
        "is_testnet": trade_engine.trading_mode == "BINANCE_TESTNET",
        "connected": connected,
        "message": msg,
        "account": trade_engine.get_account_summary()
    }

@app.post("/api/exchange_config")
async def update_exchange_config(req: ExchangeConfigRequest):
    trade_engine.trading_mode = req.trading_mode
    key = (req.api_key or req.binance_api_key or "").strip()
    secret = (req.api_secret or req.binance_api_secret or "").strip()
    if key:
        trade_engine.binance_api_key = key
    if secret:
        trade_engine.binance_api_secret = secret
        
    save_env_config(key=trade_engine.binance_api_key, secret=trade_engine.binance_api_secret, mode=req.trading_mode)

    connected = False
    msg = ""
    if req.trading_mode in ["BINANCE_TESTNET", "BINANCE_LIVE"]:
        if not trade_engine.binance_api_key or not trade_engine.binance_api_secret:
            connected = False
            msg = f"{req.trading_mode} selected, but API Key / Secret is missing. Please paste your Binance keys above."
        else:
            r, err = trade_engine.binance_signed_request("/api/v3/account", method="GET", timeout=12)
            if r is not None and r.status_code == 200:
                connected = True
                trade_engine.exchange_connected = True
                trade_engine.last_balance_check = 0
                trade_engine.check_live_binance_balance()
                msg = f"{req.trading_mode} Authenticated: Binance Spot Account Connected! (USDT: ${trade_engine.live_usdt_balance:.2f})"
            elif r is not None:
                connected = False
                trade_engine.exchange_connected = False
                try:
                    err_json = r.json()
                    code = err_json.get("code")
                    api_msg = err_json.get("msg", r.text[:80])
                    if code == -2015:
                        msg = "Binance Auth Error (-2015): Invalid API-key, IP restriction, or missing Spot Trading permission. Verify permissions in Binance API Management."
                    else:
                        msg = f"Binance Error ({code}): {api_msg}"
                except Exception:
                    msg = f"Binance Error ({r.status_code}): {r.text[:80]}"
            else:
                connected = False
                trade_engine.exchange_connected = False
                msg = f"Connection timeout: {err}. Binance clusters unreachable within 12s."
    else:
        connected = True
        trade_engine.exchange_connected = True
        msg = "Demo Paper Trading Active ($200 Virtual Capital - Zero Risk)"

    trade_engine.exchange_connected = connected
    return {
        "success": True,
        "trading_mode": trade_engine.trading_mode,
        "is_real_trading": trade_engine.trading_mode == "BINANCE_LIVE",
        "is_testnet": trade_engine.trading_mode == "BINANCE_TESTNET",
        "connected": connected,
        "message": msg,
        "account": trade_engine.get_account_summary()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        payload = {
            "type": "INITIAL",
            "symbol": current_symbol,
            "interval": current_interval,
            "candles": latest_candles[-60:] if latest_candles else [],
            "analysis": latest_analysis,
            "ai": latest_ai_decision,
            "order_book": latest_order_book,
            "gatekeeper": latest_analysis.get("gatekeeper", {}),
            "predicted_win_probability": latest_analysis.get("predicted_win_probability", 75.0),
            "regime": latest_analysis.get("regime", {}),
            "mtf": latest_analysis.get("mtf_data", {}),
            "order_flow": latest_analysis.get("order_flow", {}),
            "kelly": latest_analysis.get("kelly", {}),
            "account": trade_engine.get_account_summary(),
            "radar": [
                {
                    "symbol": r["symbol"], "name": r["name"], "price": r["price"],
                    "change_pct": r["change_pct"], "opp_score": r["opp_score"],
                    "win_prob": r["win_prob"], "verdict": r["verdict"],
                    "confidence": r["confidence"], "action": r["action"],
                    "pattern": r.get("dominant_pattern", "N/A"), "multiplier": r.get("multiplier", 1.0),
                    "gatekeeper_passed": r.get("gatekeeper_passed", False)
                }
                for r in multi_pair_radar_data
            ],
            "learning": learning_engine.get_learning_summary(),
            "positions": trade_engine.positions,
            "history": trade_engine.trade_history
        }
        await websocket.send_text(json.dumps(payload))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)

web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
os.makedirs(web_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=web_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    cloud_port = int(os.environ.get("PORT", 8500))
    uvicorn.run(app, host="0.0.0.0", port=cloud_port)
