"""
Market Data Engine
Fetches live OHLCV candlestick data and real-time prices from Binance Public API.
Zero API keys needed for public market data.
"""
import time
import requests
from typing import List, Dict, Any, Optional

from concurrent.futures import ThreadPoolExecutor

BINANCE_ENDPOINTS = [
    "https://api.binance.com/api/v3",
    "https://api1.binance.com/api/v3",
    "https://api2.binance.com/api/v3",
    "https://api3.binance.com/api/v3"
]

# In-memory cache for uninterrupted streaming
_last_known_candles: Dict[str, List[Dict[str, Any]]] = {}

# Top 24 High-Volatility & Liquid Binance Pairs for Multi-Currency Scanner
SUPPORTED_SYMBOLS = {
    # Top Major Liquid Anchors
    "BTCUSDT": "BTC / USDT (Bitcoin)",
    "ETHUSDT": "ETH / USDT (Ethereum)",
    "SOLUSDT": "SOL / USDT (Solana)",
    "BNBUSDT": "BNB / USDT (Binance Coin)",
    "XRPUSDT": "XRP / USDT (Ripple)",
    "ADAUSDT": "ADA / USDT (Cardano)",
    "AVAXUSDT": "AVAX / USDT (Avalanche)",
    "LINKUSDT": "LINK / USDT (Chainlink)",
    "NEARUSDT": "NEAR / USDT (NEAR Protocol)",
    "SUIUSDT": "SUI / USDT (Sui)",
    "APTUSDT": "APT / USDT (Aptos)",
    "INJUSDT": "INJ / USDT (Injective)",
    "MATICUSDT": "MATIC / USDT (Polygon)",
    "FTMUSDT": "FTM / USDT (Fantom)",
    # High-Beta Volatility & Fast Scalping Movers
    "DOGEUSDT": "DOGE / USDT (Dogecoin)",
    "PEPEUSDT": "PEPE / USDT (Pepe)",
    "SHIBUSDT": "SHIB / USDT (Shiba Inu)",
    "WIFUSDT": "WIF / USDT (dogwifhat)",
    "FETUSDT": "FET / USDT (Artificial Superintelligence)",
    "RENDERUSDT": "RENDER / USDT (Render)",
    "TAOUSDT": "TAO / USDT (Bittensor)",
    "TIAUSDT": "TIA / USDT (Celestia)",
    "ARBUSDT": "ARB / USDT (Arbitrum)",
    "OPUSDT": "OP / USDT (Optimism)"
}

INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1d"]

def fetch_multi_pair_klines(symbols: List[str], interval: str = "5m", limit: int = 60) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetches candles for multiple symbols concurrently using thread pool.
    Ensures the 24-pair radar updates with zero UI lag.
    """
    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(fetch_klines, s, interval, limit): s for s in symbols}
        for future in future_to_symbol:
            sym = future_to_symbol[future]
            try:
                data = future.result()
                results[sym] = data
            except Exception:
                results[sym] = _last_known_candles.get(f"{sym}_{interval}", [])
    return results

def fetch_klines(symbol: str = "BTCUSDT", interval: str = "15m", limit: int = 120) -> List[Dict[str, Any]]:
    """
    Fetches historical and live candlestick data with multi-endpoint fallback.
    Caches last known good candles to ensure seamless real-time charts.
    """
    cache_key = f"{symbol.upper()}_{interval}"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }
    
    for base_url in BINANCE_ENDPOINTS:
        try:
            url = f"{base_url}/klines"
            response = requests.get(url, params=params, timeout=8)
            if response.status_code == 200:
                raw_candles = response.json()
                candles = []
                for c in raw_candles:
                    candles.append({
                        "time": int(c[0] // 1000),  # seconds for TradingView chart
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": float(c[5]),
                        "close_time": int(c[6] // 1000)
                    })
                if candles:
                    _last_known_candles[cache_key] = candles
                    return candles
        except Exception:
            continue

    # Return cached data if network was slow on this tick
    return _last_known_candles.get(cache_key, [])

def fetch_order_book_depth(symbol: str = "BTCUSDT", limit: int = 20) -> Dict[str, Any]:
    """
    Fetches live Order Book depth from Binance to detect Whale Buy & Sell Walls.
    Computes Bid vs Ask institutional volume pressure.
    """
    params = {"symbol": symbol.upper(), "limit": limit}
    for base_url in BINANCE_ENDPOINTS:
        try:
            url = f"{base_url}/depth"
            r = requests.get(url, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                bids = data.get("bids", [])  # [[price, qty], ...]
                asks = data.get("asks", [])
                
                total_bid_vol = sum(float(b[1]) for b in bids)
                total_ask_vol = sum(float(a[1]) for a in asks)
                total_vol = total_bid_vol + total_ask_vol or 1.0
                
                bid_pct = round((total_bid_vol / total_vol) * 100, 1)
                ask_pct = round((total_ask_vol / total_vol) * 100, 1)
                ratio = round(total_bid_vol / (total_ask_vol or 0.0001), 2)
                
                # Identify Whale Walls (highest volume price level)
                whale_bid = max(bids, key=lambda x: float(x[1])) if bids else [0, 0]
                whale_ask = max(asks, key=lambda x: float(x[1])) if asks else [0, 0]
                
                return {
                    "total_bid_vol": round(total_bid_vol, 2),
                    "total_ask_vol": round(total_ask_vol, 2),
                    "bid_pct": bid_pct,
                    "ask_pct": ask_pct,
                    "bid_ask_ratio": ratio,
                    "whale_support_wall": {
                        "price": float(whale_bid[0]),
                        "qty": round(float(whale_bid[1]), 2)
                    },
                    "whale_resistance_wall": {
                        "price": float(whale_ask[0]),
                        "qty": round(float(whale_ask[1]), 2)
                    }
                }
        except Exception:
            continue

    return {
        "total_bid_vol": 100.0, "total_ask_vol": 100.0,
        "bid_pct": 50.0, "ask_pct": 50.0, "bid_ask_ratio": 1.0,
        "whale_support_wall": {"price": 0.0, "qty": 0.0},
        "whale_resistance_wall": {"price": 0.0, "qty": 0.0}
    }

def fetch_1h_trend(symbol: str = "BTCUSDT") -> Dict[str, Any]:
    """Fetches 1H Higher Timeframe candles to confirm institutional macro direction."""
    candles = fetch_klines(symbol, "1h", limit=50)
    if not candles or len(candles) < 20:
        return {"trend": "NEUTRAL", "ema50": 0.0, "ema200": 0.0}
    
    closes = [c["close"] for c in candles]
    curr = closes[-1]
    ema50 = sum(closes[-20:]) / 20.0
    
    if curr > ema50 and closes[-1] > closes[-5]:
        trend = "BULLISH"
    elif curr < ema50 and closes[-1] < closes[-5]:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"
        
    return {
        "trend": trend,
        "current_1h": curr,
        "ema50_1h": round(ema50, 2)
    }

def fetch_order_flow_cvd(symbol: str = "BTCUSDT", limit: int = 40) -> Dict[str, Any]:
    """
    Computes real-time Cumulative Volume Delta (CVD) and Taker Aggressiveness.
    m=False -> Taker Buy (aggressive buyer lifting ask)
    m=True  -> Taker Sell (aggressive seller hitting bid)
    """
    for base_url in BINANCE_ENDPOINTS:
        try:
            url = f"{base_url}/aggTrades"
            r = requests.get(url, params={"symbol": symbol.upper(), "limit": limit}, timeout=4)
            if r.status_code == 200:
                trades = r.json()
                buy_vol = sum(float(t["q"]) for t in trades if not t["m"])
                sell_vol = sum(float(t["q"]) for t in trades if t["m"])
                total_vol = buy_vol + sell_vol or 1.0
                delta = buy_vol - sell_vol
                buy_pct = round((buy_vol / total_vol) * 100, 1)
                sell_pct = round((sell_vol / total_vol) * 100, 1)
                
                if buy_pct >= 60.0:
                    bias = "INSTITUTIONAL_ACCUMULATION"
                elif sell_pct >= 60.0:
                    bias = "INSTITUTIONAL_DISTRIBUTION"
                else:
                    bias = "BALANCED_FLOW"

                return {
                    "cvd_delta": round(delta, 4),
                    "taker_buy_pct": buy_pct,
                    "taker_sell_pct": sell_pct,
                    "flow_bias": bias
                }
        except Exception:
            continue

    return {"cvd_delta": 0.0, "taker_buy_pct": 50.0, "taker_sell_pct": 50.0, "flow_bias": "BALANCED_FLOW"}

def fetch_mtf_confluence(symbol: str = "BTCUSDT") -> Dict[str, Any]:
    """
    Fetches 4H (Macro), 1H (Intermediate), 15m (Primary), and 5m (Micro) candles concurrently.
    Computes trend direction and EMA alignment across all 4 timeframes.
    """
    timeframes = ["4h", "1h", "15m", "5m"]
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {executor.submit(fetch_klines, symbol, tf, 50): tf for tf in timeframes}
        for f in future_map:
            tf = future_map[f]
            try:
                results[tf] = f.result()
            except Exception:
                results[tf] = []

    mtf_status = {}
    total_alignment_score = 0
    for tf in timeframes:
        candles = results.get(tf, [])
        if len(candles) >= 15:
            closes = [c["close"] for c in candles]
            curr = closes[-1]
            ema20 = sum(closes[-20:]) / len(closes[-20:])
            slope = closes[-1] - closes[-3]
            if curr > ema20 and slope > 0:
                direction = "BULLISH"
                score = 1
            elif curr < ema20 and slope < 0:
                direction = "BEARISH"
                score = -1
            else:
                direction = "NEUTRAL"
                score = 0
        else:
            direction = "NEUTRAL"
            score = 0

        # Weight higher timeframes more heavily
        weight = 3 if tf == "4h" else (2 if tf == "1h" else 1)
        total_alignment_score += score * weight
        mtf_status[tf] = direction

    # Alignment label
    if total_alignment_score >= 4:
        mtf_verdict = "STRONG_BULLISH_CONFLUENCE"
    elif total_alignment_score >= 2:
        mtf_verdict = "MODERATE_BULLISH"
    elif total_alignment_score <= -4:
        mtf_verdict = "STRONG_BEARISH_CONFLUENCE"
    elif total_alignment_score <= -2:
        mtf_verdict = "MODERATE_BEARISH"
    else:
        mtf_verdict = "MIXED_CHOPPY"

    return {
        "status_by_tf": mtf_status,
        "alignment_score": total_alignment_score,
        "verdict": mtf_verdict,
        "is_counter_trend_long": total_alignment_score < 0,
        "is_counter_trend_short": total_alignment_score > 0,
        "candles_1h": results.get("1h", []),
        "candles_4h": results.get("4h", [])
    }

def fetch_ticker_price(symbol: str = "BTCUSDT") -> Optional[float]:
    """Fetches the latest live price of a symbol."""
    for base_url in BINANCE_ENDPOINTS:
        try:
            url = f"{base_url}/ticker/price"
            res = requests.get(url, params={"symbol": symbol.upper()}, timeout=4)
            if res.status_code == 200:
                return float(res.json().get("price", 0.0))
        except Exception:
            continue
    return None

def fetch_24h_stats(symbol: str = "BTCUSDT") -> Dict[str, Any]:
    """Fetches 24-hour price change stats."""
    for base_url in BINANCE_ENDPOINTS:
        try:
            url = f"{base_url}/ticker/24hr"
            res = requests.get(url, params={"symbol": symbol.upper()}, timeout=4)
            if res.status_code == 200:
                d = res.json()
                return {
                    "symbol": symbol,
                    "lastPrice": float(d.get("lastPrice", 0)),
                    "priceChange": float(d.get("priceChange", 0)),
                    "priceChangePercent": float(d.get("priceChangePercent", 0)),
                    "highPrice": float(d.get("highPrice", 0)),
                    "lowPrice": float(d.get("lowPrice", 0)),
                    "volume": float(d.get("volume", 0)),
                    "quoteVolume": float(d.get("quoteVolume", 0))
                }
        except Exception:
            continue
    return {}

