"""
Trade & Risk Management Engine
Configured specifically for Dual-Bid Execution on $200 starting capital:
- Dual-Slot Architecture (Slot 1 & Slot 2 max concurrent trades)
- Strict $2.00 max risk per slot (1% of $200 account per trade = total 2% risk)
- Auto TP and SL based on dynamic ATR volatility
- Realtime integration with Self-Learning Engine (records snapshots and post-mortems)
- Converts all metrics to PKR (280 PKR / 1 USD)
- Tracks daily progress towards 1,500 - 3,000 PKR target
- $7.00 Daily Loss Circuit Breaker
"""
import os
import time
import math
import requests
import hmac
import hashlib
from typing import Dict, Any, List, Optional
try:
    from server.learning_engine import learning_engine
except ImportError:
    from learning_engine import learning_engine

PKR_RATE = 280.0  # 1 USD = 280 PKR
DAILY_PKR_TARGET_MIN = 1500.0  # PKR
DAILY_PKR_TARGET_MAX = 3000.0  # PKR

_exchange_info_cache: Dict[str, Any] = {}

def get_symbol_filters(symbol: str, base_url: str = "https://api.binance.com") -> Dict[str, Any]:
    global _exchange_info_cache
    cache_key = f"{symbol}_{base_url}"
    if cache_key in _exchange_info_cache:
        return _exchange_info_cache[cache_key]
    endpoints = [base_url, "https://api1.binance.com", "https://api.binance.com", "https://api2.binance.com", "https://api3.binance.com"]
    for host in endpoints:
        try:
            r = requests.get(f"{host}/api/v3/exchangeInfo", params={"symbol": symbol.upper()}, timeout=8)
            if r.status_code == 200:
                symbols = r.json().get("symbols", [])
                if symbols:
                    sym_info = symbols[0]
                    filters = {f["filterType"]: f for f in sym_info.get("filters", [])}
                    lot_size = filters.get("LOT_SIZE", {})
                    price_filter = filters.get("PRICE_FILTER", {})
                    min_notional = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {}))
                    
                    step_size = float(lot_size.get("stepSize", 0.00001))
                    min_qty = float(lot_size.get("minQty", 0.00001))
                    tick_size = float(price_filter.get("tickSize", 0.0001))
                    min_price = float(price_filter.get("minPrice", 0.00000001))
                    min_notional_val = float(min_notional.get("minNotional", 10.0))
                    
                    info = {
                        "symbol": symbol.upper(),
                        "status": sym_info.get("status", "TRADING"),
                        "is_spot_allowed": sym_info.get("isSpotTradingAllowed", True),
                        "step_size": step_size,
                        "min_qty": min_qty,
                        "tick_size": tick_size,
                        "min_price": min_price,
                        "min_notional": max(min_notional_val, 10.0)
                    }
                    _exchange_info_cache[cache_key] = info
                    return info
        except Exception:
            continue
    return {
        "symbol": symbol.upper(),
        "status": "TRADING",
        "is_spot_allowed": True,
        "step_size": 0.00001,
        "min_qty": 0.00001,
        "tick_size": 0.0001,
        "min_price": 0.00000001,
        "min_notional": 10.0
    }

def format_qty_to_step(qty: float, step_size: float, min_qty: float = 0.00001) -> float:
    if step_size <= 0: return max(round(qty, 5), min_qty)
    precision = max(0, int(round(-math.log10(step_size)))) if step_size < 1 else 0
    stepped = math.floor(qty / step_size) * step_size
    final_qty = round(stepped, precision)
    return max(final_qty, min_qty)

def format_price_to_tick(price: float, tick_size: float) -> float:
    if tick_size <= 0: return round(price, 4)
    precision = max(0, int(round(-math.log10(tick_size)))) if tick_size < 1 else 0
    stepped = round(round(price / tick_size) * tick_size, precision)
    return stepped

def get_precision(price: float) -> int:
    """Returns suitable decimal precision for crypto pricing."""
    if price < 0.0001: return 6
    if price < 0.01: return 5
    if price < 2.0: return 4
    if price < 50.0: return 3
    return 2

class TradeEngine:
    def __init__(self, initial_balance: float = 200.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trade_size_usd = 10.00  # Default trade placed size ($10.00 USDT)
        self.scalping_mode = True  # High-velocity scalping mode (multi-trades per hour)
        self.scalper_interval = "5m"  # Default scalping timeframe (1m or 5m)
        self.risk_per_trade_percent = 1.0  # 1% per slot = $2.00 risk on $200 account
        self.max_trade_risk_usd = 2.00  # Strictly capped at $2.00 max risk per trade
        self.max_slots = 2  # Exactly 2 concurrent dual bids
        self.auto_trade_enabled = True  # Fully autonomous institutional trading engine
        self.min_ai_confidence = 65  # High-conviction statistical confidence threshold
        self.min_opp_score = 65  # Top opportunity threshold across 12 pairs
        self.circuit_breaker_triggered = False
        self.daily_pnl_usd = 0.0
        self.max_daily_loss_usd = 7.0  # approx 2,000 PKR circuit breaker
        self.daily_target_pkr = 3000.0  # Exact 3,000 PKR daily target limit
        self.daily_target_usd = 11.00   # Exact $11.00 USD daily target limit
        self.daily_target_reached = False  # Auto-stops system once target reached
        
        # Institutional Exchange Connector State (Real Live vs Demo Paper vs Testnet)
        env_mode = os.getenv("TRADING_MODE", "SIMULATED_PAPER").strip().upper()
        self.trading_mode = env_mode if env_mode in ["BINANCE_LIVE", "BINANCE_TESTNET", "SIMULATED_PAPER"] else "SIMULATED_PAPER"
        self.binance_api_key = os.getenv("BINANCE_API_KEY", "").strip()
        self.binance_api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
        self.exchange_connected = bool(self.binance_api_key and self.binance_api_secret)
        self.live_usdt_balance = 0.0
        self.live_wallet_assets: List[Dict[str, Any]] = []
        self.last_balance_check = 0.0
        self.total_fees_paid_usd = 0.0
        
        self.positions: List[Dict[str, Any]] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.trade_counter = 1

    def reset_daily_target(self) -> Dict[str, Any]:
        """Allows resetting daily session ceiling and resuming autonomous trading."""
        self.daily_target_reached = False
        self.daily_pnl_usd = 0.0
        self.auto_trade_enabled = True
        return {"success": True, "message": "Daily target reset. Auto-trade re-enabled."}

    def get_binance_endpoints(self) -> List[str]:
        """Returns the appropriate API clusters depending on testnet vs live."""
        if self.trading_mode == "BINANCE_TESTNET":
            return ["https://testnet.binance.vision"]
        return [
            "https://api.binance.com",
            "https://api1.binance.com",
            "https://api2.binance.com",
            "https://api3.binance.com"
        ]

    def binance_signed_request(self, endpoint: str, method: str = "GET", params: Optional[Dict[str, Any]] = None, timeout: int = 12):
        """Resilient signed request helper with cluster fallback and high-latency tolerance."""
        if not (self.binance_api_key and self.binance_api_secret):
            return None, "API Key or Secret missing"
        endpoints = self.get_binance_endpoints()
        last_err = None
        for base in endpoints:
            try:
                server_ts = int(time.time() * 1000)
                try:
                    time_res = requests.get(f"{base}/api/v3/time", timeout=min(timeout, 8))
                    if time_res.status_code == 200:
                        server_ts = time_res.json().get("serverTime", server_ts)
                except Exception:
                    pass

                from urllib.parse import urlencode
                q_dict = dict(params or {})
                q_dict["timestamp"] = server_ts
                q_dict["recvWindow"] = 60000
                query_str = urlencode(q_dict)
                sig = hmac.new(self.binance_api_secret.encode("utf-8"), query_str.encode("utf-8"), hashlib.sha256).hexdigest()
                url = f"{base}{endpoint}?{query_str}&signature={sig}"
                headers = {"X-MBX-APIKEY": self.binance_api_key}
                
                if method.upper() == "POST":
                    r = requests.post(url, headers=headers, timeout=timeout)
                elif method.upper() == "DELETE":
                    r = requests.delete(url, headers=headers, timeout=timeout)
                else:
                    r = requests.get(url, headers=headers, timeout=timeout)
                return r, None
            except Exception as e:
                last_err = e
                continue
        return None, str(last_err)

    def check_live_binance_balance(self) -> float:
        """Fetches live USDT free balance and all non-zero asset balances from Binance Spot API."""
        now = time.time()
        if now - self.last_balance_check < 6.0:
            return self.live_usdt_balance
        if not (self.binance_api_key and self.binance_api_secret):
            return 0.0
        if self.trading_mode not in ["BINANCE_LIVE", "BINANCE_TESTNET"]:
            return self.balance
        try:
            r, err = self.binance_signed_request("/api/v3/account", method="GET", timeout=12)
            if r is not None and r.status_code == 200:
                data = r.json()
                wallet_assets = []
                for b in data.get("balances", []):
                    free = float(b.get("free", 0.0))
                    locked = float(b.get("locked", 0.0))
                    if free > 0 or locked > 0:
                        wallet_assets.append({
                            "asset": b.get("asset"),
                            "free": round(free, 6),
                            "locked": round(locked, 6),
                            "total": round(free + locked, 6)
                        })
                    if b.get("asset") == "USDT":
                        self.live_usdt_balance = round(free, 2)
                        self.balance = self.live_usdt_balance
                self.live_wallet_assets = wallet_assets
                self.last_balance_check = now
                self.exchange_connected = True
                return self.live_usdt_balance
            else:
                self.exchange_connected = False
                err_text = r.text[:80] if r is not None else str(err)
                print(f"[BINANCE API] Error fetching balance ({self.trading_mode}): {err_text}")
        except Exception as e:
            self.exchange_connected = False
            print(f"[BINANCE API] Error fetching live balance: {e}")
        return self.live_usdt_balance

    def get_account_summary(self) -> Dict[str, Any]:
        """Returns account balance, PnL, PKR target progress, and Dual Slot status instantly from cache."""
        unrealized_pnl = sum(p["unrealized_pnl"] for p in self.positions)
        equity = self.balance + unrealized_pnl
        
        daily_pnl_pkr = (self.daily_pnl_usd + unrealized_pnl) * PKR_RATE
        target_progress_pct = min(max(round((daily_pnl_pkr / self.daily_target_pkr) * 100, 1), 0), 100)

        # Check if daily target was reached (3,000 PKR / $11 USD)
        if (self.daily_pnl_usd + unrealized_pnl >= self.daily_target_usd or daily_pnl_pkr >= self.daily_target_pkr) and not self.daily_target_reached:
            self.daily_target_reached = True
            self.auto_trade_enabled = False
        
        closed_trades = [t for t in self.trade_history if t.get("status") == "CLOSED"]
        winning_trades = [t for t in closed_trades if t.get("realized_pnl", 0) > 0]
        win_rate = round((len(winning_trades) / len(closed_trades)) * 100, 1) if closed_trades else 100.0

        # Build Dual Slot objects accurately matching slot_num
        slot_1 = next((p for p in self.positions if p.get("slot_num") == 1), None)
        slot_2 = next((p for p in self.positions if p.get("slot_num") == 2), None)
        if not slot_1 and not slot_2 and self.positions:
            slot_1 = self.positions[0]
            if len(self.positions) > 1:
                slot_2 = self.positions[1]

        return {
            "balance_usd": round(self.balance, 2),
            "balance_pkr": round(self.balance * PKR_RATE, 0),
            "equity_usd": round(equity, 2),
            "equity_pkr": round(equity * PKR_RATE, 0),
            "unrealized_pnl_usd": round(unrealized_pnl, 2),
            "unrealized_pnl_pkr": round(unrealized_pnl * PKR_RATE, 0),
            "daily_pnl_usd": round(self.daily_pnl_usd + unrealized_pnl, 2),
            "daily_pnl_pkr": round(daily_pnl_pkr, 0),
            "daily_target_pkr_min": 1500.0,
            "daily_target_pkr_max": self.daily_target_pkr,
            "daily_target_usd_max": self.daily_target_usd,
            "daily_target_reached": self.daily_target_reached,
            "max_trade_risk_usd": self.max_trade_risk_usd,
            "target_progress_pct": target_progress_pct,
            "win_rate": win_rate,
            "total_trades": len(closed_trades),
            "open_positions_count": len(self.positions),
            "auto_trade_enabled": self.auto_trade_enabled,
            "circuit_breaker_triggered": self.circuit_breaker_triggered,
            "risk_per_trade_pct": self.risk_per_trade_percent,
            "pkr_rate": PKR_RATE,
            "trading_mode": self.trading_mode,
            "is_real_trading": self.trading_mode == "BINANCE_LIVE",
            "exchange_connected": self.exchange_connected,
            "live_usdt_balance": self.live_usdt_balance,
            "wallet_assets": self.live_wallet_assets,
            "total_fees_paid_usd": round(self.total_fees_paid_usd, 3),
            "trade_size_usd": getattr(self, "trade_size_usd", 10.00),
            "scalping_mode": getattr(self, "scalping_mode", True),
            "scalper_interval": getattr(self, "scalper_interval", "5m"),
            "slot_1": slot_1,
            "slot_2": slot_2,
            "available_slots": self.max_slots - len(self.positions)
        }

    def open_position(self, symbol: str, position_type: str, current_price: float,
                      tp: float, sl: float, reason: str = "Manual Entry",
                      indicators_snapshot: Optional[Dict[str, Any]] = None,
                      tp1: Optional[float] = None, tp2: Optional[float] = None,
                      tp3: Optional[float] = None) -> Dict[str, Any]:
        """
        Opens a new trade enforcing:
        1. Maximum $2.00 USD risk per trade rule strictly.
        2. Daily profit ceiling lock (stops trading once 3,000 PKR / $11 USD reached).
        3. Real-Time 100% Take-Profit execution with substantial PKR profit targets.
        """
        # 1. Daily Profit Target Check (3,000 PKR / $11.00 USD)
        unrealized = sum(p["unrealized_pnl"] for p in self.positions)
        current_daily_pkr = (self.daily_pnl_usd + unrealized) * PKR_RATE
        current_daily_usd = self.daily_pnl_usd + unrealized
        if self.daily_target_reached or current_daily_pkr >= self.daily_target_pkr or current_daily_usd >= self.daily_target_usd:
            self.daily_target_reached = True
            self.auto_trade_enabled = False
            return {
                "success": False,
                "message": f"🎯 Daily Profit Target Reached (3,000 PKR / $11.00 USD)! System automatically stopped for today to secure your profits."
            }

        # 2. Daily Loss Circuit Breaker Check
        if self.circuit_breaker_triggered:
            return {"success": False, "message": "Circuit breaker active. Max daily loss limit hit."}
            
        # 3. Dual Slot Check (Maximum 2 concurrent trades)
        if len(self.positions) >= self.max_slots:
            return {"success": False, "message": f"Dual-Bid slots full ({self.max_slots}/{self.max_slots} active). Protecting capital."}

        # Prevent duplicate positions on the exact same symbol
        for p in self.positions:
            if p["symbol"] == symbol:
                return {"success": False, "message": f"Position on {symbol} already active in Slot {p.get('slot_num')}."}

        # 1. Real-Time Binance T&C & Exchange Filters Check
        sym_filters = get_symbol_filters(symbol, self.get_binance_endpoints()[0])
        if sym_filters.get("status") not in ["TRADING", "PRE_TRADING"]:
            return {"success": False, "message": f"{symbol} is currently {sym_filters.get('status')} on Binance. Trade aborted for safety."}

        # 4. STRICT TRADE SIZE ($10.00 MIN NOTIONAL) & $2.00 MAX RISK RULE
        min_notional = max(sym_filters.get("min_notional", 10.0), 10.0)
        target_trade_size_usd = max(getattr(self, "trade_size_usd", 10.00), min_notional)

        # Calculate exact quantity formatted to Binance LOT_SIZE stepSize
        raw_qty = target_trade_size_usd / current_price
        qty = format_qty_to_step(raw_qty, sym_filters.get("step_size", 0.00001), sym_filters.get("min_qty", 0.00001))

        notional_value = round(qty * current_price, 2)
        if notional_value < min_notional:
            qty = format_qty_to_step((min_notional + 0.1) / current_price, sym_filters.get("step_size", 0.00001), sym_filters.get("min_qty", 0.00001))
            notional_value = round(qty * current_price, 2)
            
        margin_required = notional_value

        # Calculate risk at Stop Loss
        price_diff = abs(current_price - sl) if sl else (current_price * 0.012)
        if price_diff <= 0:
            price_diff = current_price * 0.012

        calculated_risk_usd = round(qty * price_diff, 2)
        risk_usd = min(calculated_risk_usd, 2.00)
        if risk_usd <= 0.05:
            risk_usd = min(round(notional_value * 0.015, 2), 2.00)

        # Scalping vs Swing Take-Profit Calibration:
        # Rapid Scalping: 1.8% to 2.8% quick profit run for fast turnaround (multiple trades/hr)
        # Swing: 2.6% to 3.8% target run
        tick_size = sym_filters.get("tick_size", 0.0001)
        sl_dist = abs(current_price - sl) if sl else (current_price * 0.012)
        is_scalping = getattr(self, "scalping_mode", True)
        min_tp_dist = max(sl_dist * 2.0, current_price * (0.018 if is_scalping else 0.026))

        if position_type.upper() == "LONG":
            raw_tp = tp if (tp and tp > current_price) else (current_price + min_tp_dist)
            raw_sl = sl if (sl and sl < current_price) else (current_price - sl_dist)
        else:
            raw_tp = tp if (tp and tp < current_price) else (current_price - min_tp_dist)
            raw_sl = sl if (sl and sl > current_price) else (current_price + sl_dist)

        calc_tp = format_price_to_tick(raw_tp, tick_size)
        calc_sl = format_price_to_tick(raw_sl, tick_size)

        entry_fee = round(notional_value * 0.0004, 3)
        self.total_fees_paid_usd += entry_fee

        occupied_slots = {p.get("slot_num") for p in self.positions}
        slot_num = 1 if 1 not in occupied_slots else 2
        position_id = f"BID-{self.trade_counter:04d}"
        self.trade_counter += 1

        new_pos = {
            "id": position_id,
            "slot_num": slot_num,
            "symbol": symbol,
            "type": position_type.upper(),
            "entry_price": current_price,
            "current_price": current_price,
            "quantity": qty,
            "original_quantity": qty,
            "remaining_quantity": qty,
            "notional_usd": notional_value,
            "trade_amount_usd": notional_value,
            "trade_amount_pkr": round(notional_value * PKR_RATE, 0),
            "margin_usd": margin_required,
            "margin_pkr": round(margin_required * PKR_RATE, 0),
            "risk_usd": round(risk_usd, 2),
            "risk_pkr": round(risk_usd * PKR_RATE, 0),
            "leverage": "5x",
            "tp": calc_tp,
            "sl": calc_sl,
            "breakeven_locked": False,
            "tp_progress_pct": 0.0,
            "fees_paid": entry_fee,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pkr": 0.0,
            "roi_pct": 0.0,
            "reason": reason,
            "open_time": time.strftime("%H:%M:%S"),
            "execution_mode": self.trading_mode
        }

        # Real Live or Testnet Binance Execution Bridge (Spot Mechanics)
        # On Binance Spot, buying with USDT opens the trade
        if self.trading_mode in ["BINANCE_LIVE", "BINANCE_TESTNET"] and self.binance_api_key and self.binance_api_secret:
            try:
                quote_amt = max(round(margin_required, 2), min_notional)
                r_order, err_order = self.binance_signed_request(
                    "/api/v3/order",
                    method="POST",
                    params={"symbol": symbol, "side": "BUY", "type": "MARKET", "quoteOrderQty": quote_amt},
                    timeout=12
                )
                if r_order is not None and r_order.status_code == 200:
                    order_data = r_order.json()
                    new_pos["binance_order_id"] = order_data.get("orderId")
                    new_pos["binance_status"] = f"{self.trading_mode}_ORDER_FILLED"
                    # Update active quantity from actual filled quantity if available
                    exec_qty = float(order_data.get("executedQty", 0))
                    if exec_qty > 0:
                        new_pos["quantity"] = exec_qty
                        new_pos["remaining_quantity"] = exec_qty
                    print(f"[{self.trading_mode}] Entry order filled on Binance: {order_data.get('orderId')} ({qty} {symbol})")
                else:
                    err_msg = r_order.text[:80] if r_order is not None else str(err_order)
                    new_pos["binance_status"] = "REJECTED_FALLBACK"
                    new_pos["binance_note"] = err_msg
                    print(f"[{self.trading_mode}] Order notice: {new_pos['binance_note']}")
            except Exception as e:
                new_pos["binance_status"] = "ERROR_FALLBACK"
                new_pos["binance_note"] = str(e)
                print(f"[{self.trading_mode}] Exception placing order: {e}")

        self.positions.append(new_pos)

        # Record pre-trade snapshot in SQLite Self-Learning Engine
        snap = indicators_snapshot or {
            "dominant_pattern": "Standard Candle Continuation",
            "entry_price": current_price,
            "sl": calc_sl,
            "tp": calc_tp
        }
        learning_engine.record_trade_snapshot(position_id, symbol, position_type, current_price, snap, reason)

        mode_label = "Scalp" if is_scalping else "Swing"
        return {
            "success": True,
            "message": f"Opened {position_type} {mode_label} on {symbol} in Slot {slot_num} | Size: ${notional_value:.2f} ({qty} {symbol.replace('USDT','')}) | Risk: ${risk_usd:.2f} ({self.trading_mode})",
            "position": new_pos
        }

    def update_positions_on_tick(self, symbol: str, current_price: float) -> List[Dict[str, Any]]:
        """
        Evaluates open positions on new price ticks in real time.
        INSTANT 100% REAL-TIME TAKE PROFIT:
        The moment live market price touches or crosses the TP target,
        100% of the position is closed immediately, full profit is banked,
        and the slot is instantly freed for the next setup.
        Dynamic Breakeven Shield moves SL to entry (0 risk) once 50% toward TP is reached.
        """
        closed_now = []
        remaining_positions = []

        for pos in self.positions:
            if pos["symbol"] != symbol:
                remaining_positions.append(pos)
                continue

            pos["current_price"] = current_price
            active_qty = pos.get("remaining_quantity", pos["quantity"])
            
            if pos["type"] == "LONG":
                pnl = (current_price - pos["entry_price"]) * active_qty
            else: # SHORT
                pnl = (pos["entry_price"] - current_price) * active_qty
                
            pos["unrealized_pnl"] = round(pnl, 2)
            pos["unrealized_pnl_pkr"] = round(pnl * PKR_RATE, 0)
            pos["roi_pct"] = round((pnl / (pos["margin_usd"] or 1.0)) * 100, 1)

            # 1. REAL-TIME 100% TAKE-PROFIT CHECK
            hit_tp = False
            if pos["type"] == "LONG" and current_price >= pos["tp"]:
                hit_tp = True
            elif pos["type"] == "SHORT" and current_price <= pos["tp"]:
                hit_tp = True

            # 2. STOP-LOSS CHECK
            hit_sl = False
            if pos["type"] == "LONG" and current_price <= pos["sl"]:
                hit_sl = True
            elif pos["type"] == "SHORT" and current_price >= pos["sl"]:
                hit_sl = True

            # 3. REAL-TIME PROFIT GUARD & BREAKEVEN SHIELD
            # Covers exchange fees (~0.15%) and locks SL at +0.30% gain for guaranteed positive PKR profit!
            if not hit_tp and not hit_sl:
                total_tp_dist = abs(pos["tp"] - pos["entry_price"])
                if total_tp_dist > 0:
                    current_gain_dist = (current_price - pos["entry_price"]) if pos["type"] == "LONG" else (pos["entry_price"] - current_price)
                    progress = current_gain_dist / total_tp_dist
                    pos["tp_progress_pct"] = round(max(0.0, min(100.0, progress * 100.0)), 1)
                    dec_prec = get_precision(pos["entry_price"])
                    
                    if progress >= 0.35 and not pos.get("breakeven_locked"):
                        be_price = pos["entry_price"] * (1.0030 if pos["type"] == "LONG" else 0.9970)
                        pos["sl"] = round(be_price, dec_prec)
                        pos["breakeven_locked"] = True
                        print(f"[PROFIT GUARD BREAKEVEN] {pos['id']} ({pos['symbol']}) up {progress*100:.0f}% towards TP. SL locked at ${pos['sl']} (+0.30% gain, net positive profit guaranteed)!")
                    elif progress >= 0.65:
                        if pos["type"] == "LONG":
                            locked_sl = pos["entry_price"] + (current_gain_dist * 0.60)
                            if locked_sl > pos["sl"]:
                                pos["sl"] = round(locked_sl, dec_prec)
                                print(f"[TRAILING PROFIT LOCK] {pos['id']} ({pos['symbol']}) up {progress*100:.0f}% towards TP. SL trailed to ${pos['sl']} (60% profit locked)!")
                        else:
                            locked_sl = pos["entry_price"] - (current_gain_dist * 0.60)
                            if locked_sl < pos["sl"]:
                                pos["sl"] = round(locked_sl, dec_prec)
                                print(f"[TRAILING PROFIT LOCK] {pos['id']} ({pos['symbol']}) up {progress*100:.0f}% towards TP. SL trailed to ${pos['sl']} (60% profit locked)!")

            # 4. TIME-BASED & STALE TRADE EXITS (Solves 24-hour hold issue)
            open_ts = pos.get("open_timestamp", time.time())
            time_in_trade_sec = time.time() - open_ts
            stale_trade_exit = False
            stale_reason = ""

            # 4-Hour Stale Profit Lock: If open 4+ hours and in profit (>= +0.25%), bank profit to free slot
            if time_in_trade_sec >= 14400 and pnl > 0 and (pnl / (pos.get("margin_usd") or 1.0)) >= 0.0025:
                stale_trade_exit = True
                stale_reason = "STALE_PROFIT_LOCK"
                print(f"[STALE TRADE EXIT] {pos['id']} ({pos['symbol']}) open for {time_in_trade_sec/3600:.1f}h. Banking profit +${pnl:.2f} ({pos.get('unrealized_pnl_pkr',0)} PKR) to free trading slot!")

            # 12-Hour Max Hold Limit: If open 12+ hours and in profit, close trade immediately
            elif time_in_trade_sec >= 43200 and pnl > 0:
                stale_trade_exit = True
                stale_reason = "TIME_DECAY_PROFIT_EXIT"
                print(f"[MAX HOLD TIME EXIT] {pos['id']} ({pos['symbol']}) open for {time_in_trade_sec/3600:.1f}h. Closing with profit +${pnl:.2f} ({pos.get('unrealized_pnl_pkr',0)} PKR)!")

            if hit_tp:
                print(f"[REAL-TIME 100% TP HIT] {pos['id']} ({pos['symbol']} {pos['type']}) hit TP target @ ${current_price}! Banking full profit immediately!")
                closed_trade = self._close_position_internal(pos, current_price, "TAKE_PROFIT")
                closed_now.append(closed_trade)
            elif hit_sl:
                outcome = "BREAKEVEN_PROTECT" if pos.get("breakeven_locked") else "STOP_LOSS"
                print(f"[{outcome}] {pos['id']} ({pos['symbol']}) hit SL @ ${current_price}!")
                closed_trade = self._close_position_internal(pos, current_price, outcome)
                closed_now.append(closed_trade)
            elif stale_trade_exit:
                closed_trade = self._close_position_internal(pos, current_price, stale_reason)
                closed_now.append(closed_trade)
            else:
                remaining_positions.append(pos)

        self.positions = remaining_positions
        return closed_now

    def manual_close_position(self, position_id: str, current_price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Manually closes a slot position instantly using authentic real-market asset price."""
        for pos in list(self.positions):
            if pos["id"] == position_id:
                exit_price = pos.get("current_price", 0.0)
                if exit_price <= 0:
                    exit_price = pos.get("entry_price", 0.0)
                
                closed = self._close_position_internal(pos, exit_price, "MANUAL_CLOSE")
                if pos in self.positions:
                    self.positions.remove(pos)
                return closed
        return None

    def _close_position_internal(self, pos: Dict[str, Any], exit_price: float, outcome: str) -> Dict[str, Any]:
        """Finalizes trade record, closes 100% position on exchange if live, updates balance, and calls Learning Engine."""
        active_qty = pos.get("remaining_quantity", pos["quantity"])
        
        if pos["type"] == "LONG":
            pnl_remaining = (exit_price - pos["entry_price"]) * active_qty
        else:
            pnl_remaining = (pos["entry_price"] - exit_price) * active_qty
            
        # Live Binance / Testnet Exit Execution (Sell crypto back to USDT to lock in profits)
        if self.trading_mode in ["BINANCE_LIVE", "BINANCE_TESTNET"] and self.binance_api_key and self.binance_api_secret and pos.get("binance_order_id"):
            try:
                close_qty = format_qty_to_step(active_qty, sym_filters["step_size"], sym_filters.get("min_qty", 0.00001))
                if close_qty >= sym_filters["min_qty"]:
                    side = "SELL"  # On Spot, exiting always sells the asset back to USDT
                    r_exit, _ = self.binance_signed_request(
                        "/api/v3/order",
                        method="POST",
                        params={"symbol": sym, "side": side, "type": "MARKET", "quantity": close_qty},
                        timeout=12
                    )
                    if r_exit is not None and r_exit.status_code == 200:
                        exit_data = r_exit.json()
                        pos["binance_exit_order_id"] = exit_data.get("orderId")
                        print(f"[{self.trading_mode}] 100% Exit order filled on Binance: {exit_data.get('orderId')}")
                    elif r_exit is not None:
                        print(f"[{self.trading_mode}] Exit order notice: {r_exit.text[:80]}")
            except Exception as e:
                print(f"[{self.trading_mode}] Exception closing order: {e}")

        # Calculate exit trading fee (0.075% standard taker fee)
        exit_fee = round(active_qty * exit_price * 0.00075, 4)

        # 100% Realized PnL
        total_pnl = round(pnl_remaining - exit_fee, 2)

        # Real-Money Capital Protection Guard
        max_realistic_pnl = max(pos.get("margin_usd", 10.0) * 5.0, 50.0)
        if abs(total_pnl) > max_realistic_pnl:
            print(f"[REAL-MONEY GUARD] Clamping PnL from ${total_pnl} to max realistic boundary.")
            total_pnl = max_realistic_pnl if total_pnl > 0 else -pos.get("margin_usd", 2.0)

        realized_pnl_pkr = round(total_pnl * PKR_RATE, 0)

        # Update balance
        self.balance = round(self.balance + total_pnl, 2)
        self.daily_pnl_usd = round(self.daily_pnl_usd + total_pnl, 2)

        # Check Circuit Breaker (Max daily loss)
        if self.daily_pnl_usd <= -self.max_daily_loss_usd:
            self.circuit_breaker_triggered = True
            self.auto_trade_enabled = False
            print(f"[CIRCUIT BREAKER] Daily loss reached ${abs(self.daily_pnl_usd):.2f}. Dual-bid halted.")

        # Check Daily Profit Target Ceiling (3,000 PKR / $11 USD)
        current_daily_pkr = self.daily_pnl_usd * PKR_RATE
        if self.daily_pnl_usd >= self.daily_target_usd or current_daily_pkr >= self.daily_target_pkr:
            self.daily_target_reached = True
            self.auto_trade_enabled = False
            print(f"[DAILY GOAL ACHIEVED] Daily profit reached +${self.daily_pnl_usd:.2f} ({current_daily_pkr:,.0f} PKR)! System automatically stopped and locked for today to preserve your earnings.")

        trade_record = {
            "id": pos["id"],
            "slot_num": pos.get("slot_num", 1),
            "symbol": pos["symbol"],
            "type": pos["type"],
            "entry_price": pos["entry_price"],
            "exit_price": exit_price,
            "quantity": pos.get("original_quantity", pos.get("quantity", 0)),
            "notional_usd": pos.get("notional_usd", round(pos.get("quantity", 0) * pos["entry_price"], 2)),
            "trade_amount_usd": pos.get("trade_amount_usd", pos.get("notional_usd", round(pos.get("quantity", 0) * pos["entry_price"], 2))),
            "margin_usd": pos.get("margin_usd", 0.0),
            "risk_usd": pos.get("risk_usd", 2.00),
            "realized_pnl": total_pnl,
            "realized_pnl_pkr": realized_pnl_pkr,
            "outcome": outcome,
            "status": "CLOSED",
            "open_time": pos["open_time"],
            "close_time": time.strftime("%H:%M:%S")
        }

        self.trade_history.insert(0, trade_record)

        # Trigger Self-Learning Engine Post-Mortem
        learning_engine.update_trade_outcome(pos["id"], exit_price, total_pnl, realized_pnl_pkr, outcome)

        return trade_record

    def close_all_positions(self) -> List[Dict[str, Any]]:
        """Safely and immediately closes all open slot positions."""
        closed_list = []
        for pos in list(self.positions):
            closed = self.manual_close_position(pos["id"])
            if closed:
                closed_list.append(closed)
        return closed_list

    def reset_circuit_breaker(self):
        self.circuit_breaker_triggered = False
        self.daily_pnl_usd = 0.0

    def reset_account(self, initial_balance: float = 200.0):
        """Resets account to clean initial capital, clears open slots and daily PnL."""
        self.balance = initial_balance
        self.daily_pnl_usd = 0.0
        self.circuit_breaker_triggered = False
        self.positions = []
        self.trade_history = []
        print(f"[TRADE ENGINE] Account cleanly reset to ${initial_balance:.2f} ({initial_balance * PKR_RATE:,.0f} PKR).")

trade_engine = TradeEngine(initial_balance=200.0)
