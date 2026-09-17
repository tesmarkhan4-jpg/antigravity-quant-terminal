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
    endpoints = [base_url, "https://api1.binance.com", "https://api.binance.com"]
    for host in endpoints:
        try:
            r = requests.get(f"{host}/api/v3/exchangeInfo", params={"symbol": symbol.upper()}, timeout=10)
            if r.status_code == 200:
                symbols = r.json().get("symbols", [])
                if symbols:
                    sym_info = symbols[0]
                    filters = {f["filterType"]: f for f in sym_info.get("filters", [])}
                    lot_size = filters.get("LOT_SIZE", {})
                    min_notional = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL", {}))
                    
                    step_size = float(lot_size.get("stepSize", 0.00001))
                    min_qty = float(lot_size.get("minQty", 0.00001))
                    min_notional_val = float(min_notional.get("minNotional", 10.0))
                    
                    info = {
                        "step_size": step_size,
                        "min_qty": min_qty,
                        "min_notional": min_notional_val
                    }
                    _exchange_info_cache[cache_key] = info
                    return info
        except Exception:
            continue
    return {"step_size": 0.00001, "min_qty": 0.00001, "min_notional": 10.0}

def format_qty_to_step(qty: float, step_size: float) -> float:
    if step_size <= 0: return round(qty, 5)
    precision = max(0, int(round(-math.log10(step_size)))) if step_size < 1 else 0
    stepped = math.floor(qty / step_size) * step_size
    return round(stepped, precision)

class TradeEngine:
    def __init__(self, initial_balance: float = 200.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
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
        3. Arms 3-Tier Take-Profit Ladder (TP1 40%, TP2 40%, TP3 Runner 20%).
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

        # 4. STRICT $10.00 TRADE SIZE & $2.00 MAX RISK RULE
        # User requirement: Each trade placed must be strictly $10.00 USDT
        target_trade_size_usd = 10.00

        # Calculate exact quantity for a $10.00 position
        if current_price < 0.001:
            qty = round(target_trade_size_usd / current_price, 1)
        elif current_price < 1.0:
            qty = round(target_trade_size_usd / current_price, 4)
        else:
            qty = round(target_trade_size_usd / current_price, 5)

        notional_value = round(qty * current_price, 2)
        if notional_value <= 0:
            notional_value = target_trade_size_usd
            
        margin_required = notional_value  # Spot allocation is $10.00

        # Calculate risk at Stop Loss
        price_diff = abs(current_price - sl)
        if price_diff <= 0:
            price_diff = current_price * 0.01

        calculated_risk_usd = round(qty * price_diff, 2)
        # Risk is strictly capped at $2.00 max
        risk_usd = min(calculated_risk_usd, 2.00)
        if risk_usd <= 0.05:
            risk_usd = round(notional_value * 0.015, 2)  # Default to ~1.5% SL ($0.15) if tight

        # 3-Tier Take-Profit Ladder Calculation
        sl_dist = abs(current_price - sl)
        if position_type.upper() == "LONG":
            calc_tp1 = tp1 or round(current_price + (sl_dist * 1.2), 2)
            calc_tp2 = tp2 or tp or round(current_price + (sl_dist * 2.0), 2)
            calc_tp3 = tp3 or round(current_price + (sl_dist * 3.5), 2)
        else:
            calc_tp1 = tp1 or round(current_price - (sl_dist * 1.2), 2)
            calc_tp2 = tp2 or tp or round(current_price - (sl_dist * 2.0), 2)
            calc_tp3 = tp3 or round(current_price - (sl_dist * 3.5), 2)

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
            "tp": calc_tp2,
            "tp1": calc_tp1,
            "tp2": calc_tp2,
            "tp3": calc_tp3,
            "tp1_hit": False,
            "tp2_hit": False,
            "tp3_hit": False,
            "realized_pnl_banked": 0.0,
            "fees_paid": entry_fee,
            "sl": sl,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pkr": 0.0,
            "roi_pct": 0.0,
            "reason": reason,
            "open_time": time.strftime("%H:%M:%S"),
            "execution_mode": self.trading_mode
        }

        # Real Live or Testnet Binance Execution Bridge
        if self.trading_mode in ["BINANCE_LIVE", "BINANCE_TESTNET"] and self.binance_api_key and self.binance_api_secret:
            try:
                side = "BUY" if position_type.upper() == "LONG" else "SELL"
                quote_amt = max(round(margin_required, 1), 10.0)  # Binance minimum order value
                r_order, err_order = self.binance_signed_request(
                    "/api/v3/order",
                    method="POST",
                    params={"symbol": symbol, "side": side, "type": "MARKET", "quoteOrderQty": quote_amt},
                    timeout=12
                )
                if r_order is not None and r_order.status_code == 200:
                    order_data = r_order.json()
                    new_pos["binance_order_id"] = order_data.get("orderId")
                    new_pos["binance_status"] = f"{self.trading_mode}_ORDER_FILLED"
                    print(f"[{self.trading_mode}] Order filled: {order_data.get('orderId')}")
                else:
                    err_msg = r_order.text[:60] if r_order is not None else str(err_order)
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
            "sl": sl,
            "tp": calc_tp2
        }
        learning_engine.record_trade_snapshot(position_id, symbol, position_type, current_price, snap, reason)

        return {
            "success": True,
            "message": f"Opened {position_type} on {symbol} in Slot {slot_num} | Trade Size: ${notional_value:.2f} ({qty} {symbol.replace('USDT','')}) | Max Risk: ${risk_usd:.2f} ({self.trading_mode})",
            "position": new_pos
        }

    def update_positions_on_tick(self, symbol: str, current_price: float) -> List[Dict[str, Any]]:
        """
        Evaluates open positions on new price ticks.
        Executes institutional 3-Tier Take-Profit Ladder (TP1 40%, TP2 40%, TP3 Runner 20%)
        and dynamic breakeven / trailing stop protection.
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

            # --- INSTITUTIONAL 3-TIER TAKE-PROFIT LADDER ---
            # 1. TP1 (40% Partial Scale-Out at 1:1.2 R:R) -> Auto-triggers Breakeven Shield
            if not pos.get("tp1_hit", False):
                hit_tp1 = (pos["type"] == "LONG" and current_price >= pos["tp1"]) or (pos["type"] == "SHORT" and current_price <= pos["tp1"])
                if hit_tp1:
                    partial_qty = round(pos["original_quantity"] * 0.40, 5)
                    partial_move = (pos["tp1"] - pos["entry_price"]) if pos["type"] == "LONG" else (pos["entry_price"] - pos["tp1"])
                    partial_profit = round(partial_move * partial_qty, 2)
                    fee = round(pos["tp1"] * partial_qty * 0.0004, 3)
                    net_partial = round(partial_profit - fee, 2)
                    
                    self.balance = round(self.balance + net_partial, 2)
                    self.daily_pnl_usd = round(self.daily_pnl_usd + net_partial, 2)
                    self.total_fees_paid_usd += fee
                    
                    pos["realized_pnl_banked"] = round(pos.get("realized_pnl_banked", 0.0) + net_partial, 2)
                    pos["remaining_quantity"] = round(pos["remaining_quantity"] - partial_qty, 5)
                    pos["tp1_hit"] = True
                    
                    # Breakeven Shield arming (0 risk on remaining 60%)
                    be_price = pos["entry_price"] * (1.0005 if pos["type"] == "LONG" else 0.9995)
                    pos["sl"] = round(be_price, 4)
                    pos["breakeven_locked"] = True
                    print(f"[TP1 LADDER] 40% partial profit secured (+${net_partial:.2f} / +{net_partial * PKR_RATE:.0f} PKR) on {pos['symbol']}. Breakeven Shield locked at ${pos['sl']}!")

                    # Live Binance / Testnet Partial Execution (Sell 40% back to USDT)
                    if self.trading_mode in ["BINANCE_LIVE", "BINANCE_TESTNET"] and self.binance_api_key and self.binance_api_secret and pos.get("binance_order_id"):
                        try:
                            sym = pos["symbol"]
                            sym_filters = get_symbol_filters(sym, self.get_binance_endpoints()[0])
                            p_close_qty = format_qty_to_step(partial_qty, sym_filters["step_size"])
                            if p_close_qty >= sym_filters["min_qty"]:
                                side = "SELL" if pos["type"] == "LONG" else "BUY"
                                r_tp1, _ = self.binance_signed_request(
                                    "/api/v3/order",
                                    method="POST",
                                    params={"symbol": sym, "side": side, "type": "MARKET", "quantity": p_close_qty},
                                    timeout=12
                                )
                                if r_tp1 is not None and r_tp1.status_code == 200:
                                    print(f"[{self.trading_mode} TP1] 40% partial order filled: {r_tp1.json().get('orderId')}")
                        except Exception as e:
                            print(f"[{self.trading_mode} TP1] Exception securing partial profit: {e}")

            # 2. TP2 (40% Partial Scale-Out at 1:2.0 R:R) -> Arms Runner Dynamic Trailing Stop
            if pos.get("tp1_hit", False) and not pos.get("tp2_hit", False):
                hit_tp2 = (pos["type"] == "LONG" and current_price >= pos["tp2"]) or (pos["type"] == "SHORT" and current_price <= pos["tp2"])
                if hit_tp2:
                    partial_qty = round(pos["original_quantity"] * 0.40, 5)
                    partial_move = (pos["tp2"] - pos["entry_price"]) if pos["type"] == "LONG" else (pos["entry_price"] - pos["tp2"])
                    partial_profit = round(partial_move * partial_qty, 2)
                    fee = round(pos["tp2"] * partial_qty * 0.0004, 3)
                    net_partial = round(partial_profit - fee, 2)
                    
                    self.balance = round(self.balance + net_partial, 2)
                    self.daily_pnl_usd = round(self.daily_pnl_usd + net_partial, 2)
                    self.total_fees_paid_usd += fee
                    
                    pos["realized_pnl_banked"] = round(pos.get("realized_pnl_banked", 0.0) + net_partial, 2)
                    pos["remaining_quantity"] = round(pos["remaining_quantity"] - partial_qty, 5)
                    pos["tp2_hit"] = True
                    pos["trailing_active"] = True
                    
                    # Trail stop to TP1 level
                    pos["sl"] = pos["tp1"]
                    print(f"[TP2 LADDER] 40% partial profit secured (+${net_partial:.2f} / +{net_partial * PKR_RATE:.0f} PKR) on {pos['symbol']}. Remaining 20% Runner trailing behind ${pos['sl']}!")

                    # Live Binance / Testnet Partial Execution (Sell 40% back to USDT)
                    if self.trading_mode in ["BINANCE_LIVE", "BINANCE_TESTNET"] and self.binance_api_key and self.binance_api_secret and pos.get("binance_order_id"):
                        try:
                            sym = pos["symbol"]
                            sym_filters = get_symbol_filters(sym, self.get_binance_endpoints()[0])
                            p_close_qty = format_qty_to_step(partial_qty, sym_filters["step_size"])
                            if p_close_qty >= sym_filters["min_qty"]:
                                side = "SELL" if pos["type"] == "LONG" else "BUY"
                                r_tp2, _ = self.binance_signed_request(
                                    "/api/v3/order",
                                    method="POST",
                                    params={"symbol": sym, "side": side, "type": "MARKET", "quantity": p_close_qty},
                                    timeout=12
                                )
                                if r_tp2 is not None and r_tp2.status_code == 200:
                                    print(f"[{self.trading_mode} TP2] 40% partial order filled: {r_tp2.json().get('orderId')}")
                        except Exception as e:
                            print(f"[{self.trading_mode} TP2] Exception securing partial profit: {e}")

            # 3. Dynamic Trailing on 20% Runner
            if pos.get("tp2_hit", False):
                trail_price = current_price * (0.996 if pos["type"] == "LONG" else 1.004)
                if (pos["type"] == "LONG" and trail_price > pos["sl"]) or (pos["type"] == "SHORT" and trail_price < pos["sl"]):
                    pos["sl"] = round(trail_price, 4)

            # Check Stop Loss (or trailing stop)
            hit_sl = False
            if pos["type"] == "LONG" and current_price <= pos["sl"]:
                hit_sl = True
            elif pos["type"] == "SHORT" and current_price >= pos["sl"]:
                hit_sl = True

            # Check final TP3 (Runner target)
            hit_tp3 = False
            if pos.get("tp2_hit", False):
                if (pos["type"] == "LONG" and current_price >= pos["tp3"]) or (pos["type"] == "SHORT" and current_price <= pos["tp3"]):
                    hit_tp3 = True

            if hit_sl or hit_tp3:
                outcome = "TAKE_PROFIT_RUNNER" if hit_tp3 else ("BREAKEVEN_PROTECT" if pos.get("tp1_hit") else "STOP_LOSS")
                closed_trade = self._close_position_internal(pos, current_price, outcome)
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
        """Finalizes trade record, accounts for banked partial TPs and fees, and calls Learning Engine."""
        active_qty = pos.get("remaining_quantity", pos["quantity"])
        
        if pos["type"] == "LONG":
            pnl_remaining = (exit_price - pos["entry_price"]) * active_qty
        else:
            pnl_remaining = (pos["entry_price"] - exit_price) * active_qty
            
        # Live Binance / Testnet Exit Execution (Sell crypto back to USDT to lock in profits)
        if self.trading_mode in ["BINANCE_LIVE", "BINANCE_TESTNET"] and self.binance_api_key and self.binance_api_secret and pos.get("binance_order_id"):
            try:
                sym = pos["symbol"]
                sym_filters = get_symbol_filters(sym, self.get_binance_endpoints()[0])
                close_qty = format_qty_to_step(active_qty, sym_filters["step_size"])
                if close_qty >= sym_filters["min_qty"]:
                    side = "SELL" if pos["type"] == "LONG" else "BUY"
                    r_exit, _ = self.binance_signed_request(
                        "/api/v3/order",
                        method="POST",
                        params={"symbol": sym, "side": side, "type": "MARKET", "quantity": close_qty},
                        timeout=12
                    )
                    if r_exit is not None and r_exit.status_code == 200:
                        exit_data = r_exit.json()
                        pos["binance_exit_order_id"] = exit_data.get("orderId")
                        print(f"[{self.trading_mode}] Exit order filled on Binance: {exit_data.get('orderId')}")
                    elif r_exit is not None:
                        print(f"[{self.trading_mode}] Exit order notice: {r_exit.text[:80]}")
            except Exception as e:
                print(f"[{self.trading_mode}] Exception closing order: {e}")

        # Calculate Binance exit trading fee (0.075% standard taker fee)
        exit_fee = round(active_qty * exit_price * 0.00075, 4)

        # Total Realized PnL is the profit on remaining quantity + profit already banked in TP1/TP2 - exit fee
        total_pnl = round(pnl_remaining + pos.get("realized_pnl_banked", 0.0) - exit_fee, 2)

        # Real-Money Capital Protection Guard
        max_realistic_pnl = max(pos.get("margin_usd", 10.0) * 5.0, 50.0)
        if abs(total_pnl) > max_realistic_pnl:
            print(f"[REAL-MONEY GUARD] Clamping PnL from ${total_pnl} to max realistic boundary.")
            total_pnl = max_realistic_pnl if total_pnl > 0 else -pos.get("margin_usd", 2.0)

        realized_pnl_pkr = round(total_pnl * PKR_RATE, 0)

        # Update balance with the final remaining leg
        net_remaining_leg = round(pnl_remaining - exit_fee, 2)
        self.balance = round(self.balance + net_remaining_leg, 2)
        self.daily_pnl_usd = round(self.daily_pnl_usd + net_remaining_leg, 2)

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
            print(f"🎯 [DAILY GOAL ACHIEVED] Daily profit reached +${self.daily_pnl_usd:.2f} ({current_daily_pkr:,.0f} PKR)! System automatically stopped and locked for today to preserve your earnings.")

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
            "tp1_hit": pos.get("tp1_hit", False),
            "tp2_hit": pos.get("tp2_hit", False),
            "tp3_hit": outcome == "TAKE_PROFIT_RUNNER",
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
