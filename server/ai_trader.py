"""
Ensemble AI Trader Brain
Integrates:
1. Anthropic Claude 3.5 Sonnet - Elite Institutional Risk Gatekeeper & Predictability Analyst
2. Groq Cloud (Qwen-27B DeepSeek reasoning) - Blazing-fast Free Inference Engine
3. Order Book Whale Liquidity Depth (Whale Buy & Sell Walls)
4. Pre-Trade 5-Rule Safety Gatekeeper & Win Probability Predictor
5. Crypto Fear & Greed Macro Sentiment
"""
import os
import json
import re
import time
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class EnsembleAITraderBrain:
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "").strip()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        
        self.last_fng_fetch = 0
        self.cached_fng = {"value": "50", "classification": "Neutral"}
        self.analysis_cache: Dict[str, Any] = {}
        self.gemini_backoff_until = 0.0
        self.groq_backoff_until = 0.0
        self.claude_backoff_until = 0.0
        
        print(f"[AI Brain] Keys loaded - Gemini 2.5: {'Active' if self.gemini_key else 'None'} | Anthropic: {'Active' if self.anthropic_key else 'None'} | Groq: {'Active' if self.groq_key else 'None'}")

    def get_fear_and_greed_index(self) -> Dict[str, str]:
        """Fetches live Crypto Fear & Greed Index with 10-minute caching."""
        now = time.time()
        if now - self.last_fng_fetch > 600:
            try:
                r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=4)
                if r.status_code == 200:
                    d = r.json().get("data", [{}])[0]
                    self.cached_fng = {
                        "value": d.get("value", "50"),
                        "classification": d.get("value_classification", "Neutral")
                    }
                    self.last_fng_fetch = now
            except Exception as e:
                print(f"[AI Brain] Fear & Greed error: {e}")
        return self.cached_fng

    def analyze_market(self, symbol: str, interval: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs deep institutional AI analysis incorporating Order Book Whale Walls,
        Pre-Trade Safety Gatekeeper, and Macro Sentiment with rate-limit safe caching.
        """
        if not analysis_data.get("ready"):
            return {
                "signal": "WAIT / NEUTRAL",
                "action": "HOLD",
                "confidence": 50,
                "predicted_win_probability": 50.0,
                "entry": 0.0,
                "tp": 0.0,
                "sl": 0.0,
                "rr": "N/A",
                "reason": "Accumulating candlestick and order book depth...",
                "engine": "System Initializing",
                "sentiment": "Neutral",
                "whale_support": 0.0,
                "whale_resistance": 0.0
            }

        cache_key = f"{symbol}_{interval}"
        now = time.time()
        if cache_key in self.analysis_cache:
            cached_time, cached_res = self.analysis_cache[cache_key]
            if now - cached_time < 30.0:
                return cached_res

        fng = self.get_fear_and_greed_index()
        macro_sentiment = f"{fng['classification']} ({fng['value']}/100)"

        # Priority 1: Google Gemini 2.5 Flash (Institutional AI with native JSON mode)
        if self.gemini_key and now > self.gemini_backoff_until:
            try:
                res = self._call_gemini(symbol, interval, analysis_data, macro_sentiment)
                if res:
                    self.analysis_cache[cache_key] = (now, res)
                    return res
                else:
                    self.gemini_backoff_until = now + 60.0
            except Exception as e:
                print(f"[AI Brain] Gemini call exception: {e}")
                self.gemini_backoff_until = now + 60.0

        # Priority 2: Groq Cloud (Ultra-fast inference)
        if self.groq_key and now > self.groq_backoff_until:
            try:
                res = self._call_groq(symbol, interval, analysis_data, macro_sentiment)
                if res:
                    self.analysis_cache[cache_key] = (now, res)
                    return res
                else:
                    self.groq_backoff_until = now + 60.0
            except Exception as e:
                print(f"[AI Brain] Groq call exception: {e}")
                self.groq_backoff_until = now + 60.0

        # Priority 3: Anthropic Claude 3.5 Sonnet (When balance is active)
        if self.anthropic_key and now > self.claude_backoff_until:
            try:
                res = self._call_claude(symbol, interval, analysis_data, macro_sentiment)
                if res:
                    self.analysis_cache[cache_key] = (now, res)
                    return res
                else:
                    self.claude_backoff_until = now + 3600.0
            except Exception as e:
                print(f"[AI Brain] Claude call exception: {e}")
                self.claude_backoff_until = now + 3600.0

        # Fallback: 12-Factor Institutional Quantitative Algorithm
        fallback_res = self._quant_fallback(symbol, analysis_data, macro_sentiment)
        self.analysis_cache[cache_key] = (now, fallback_res)
        return fallback_res

    def _call_gemini(self, symbol: str, interval: str, data: Dict[str, Any], sentiment: str) -> Optional[Dict[str, Any]]:
        """Calls Google Gemini 2.5 Flash with deep institutional market context and native JSON parsing."""
        prompt = self._build_trader_prompt(symbol, interval, data, sentiment)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 800,
                "responseMimeType": "application/json"
            }
        }
        try:
            r = requests.post(url, json=body, timeout=8)
            if r.status_code == 200:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return self._parse_json_response(text, "Google Gemini 2.5 Flash (Institutional AI)", data, sentiment)
            else:
                if r.status_code == 429:
                    self.gemini_backoff_until = time.time() + 60.0
                print(f"[AI Brain] Gemini error ({r.status_code}): {r.text[:120]}")
                return None
        except Exception as e:
            print(f"[AI Brain] Gemini call exception: {e}")
            return None

    def _call_claude(self, symbol: str, interval: str, data: Dict[str, Any], sentiment: str) -> Optional[Dict[str, Any]]:
        """Calls Anthropic Claude Sonnet with full Order Book depth and Gatekeeper rules."""
        prompt = self._build_trader_prompt(symbol, interval, data, sentiment)
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        body = {
            "model": "claude-sonnet-4-6",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            r = requests.post(url, headers=headers, json=body, timeout=6)
            if r.status_code == 200:
                text = r.json().get("content", [{}])[0].get("text", "")
                return self._parse_json_response(text, "Anthropic Claude 3.5 Sonnet", data, sentiment)
            else:
                if "balance is too low" in r.text:
                    self.claude_backoff_until = time.time() + 7200.0  # Cool off for 2 hours
                print(f"[AI Brain] Claude error response ({r.status_code}): {r.text[:120]}")
                return None
        except Exception as e:
            print(f"[AI Brain] Claude call exception: {e}")
            return None

    def _call_groq(self, symbol: str, interval: str, data: Dict[str, Any], sentiment: str) -> Optional[Dict[str, Any]]:
        """Calls Groq Cloud with multi-model failover for lightning-fast hedge-fund level reasoning."""
        prompt = self._build_trader_prompt(symbol, interval, data, sentiment)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }
        # Try Meta's top institutional model first, then ultra-fast 8B, then Qwen
        models_to_try = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
        for model in models_to_try:
            body = {
                "model": model,
                "max_tokens": 800,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}]
            }
            try:
                r = requests.post(url, headers=headers, json=body, timeout=5)
                if r.status_code == 200:
                    text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    return self._parse_json_response(text, f"Groq {model} (Ultra AI)", data, sentiment)
                elif r.status_code == 429:
                    self.groq_backoff_until = time.time() + 60.0
                    print(f"[AI Brain] Groq rate limited (429), cooling down for 60s...")
                    break
                else:
                    print(f"[AI Brain] Groq {model} status {r.status_code}: {r.text[:100]}")
            except Exception as e:
                print(f"[AI Brain] Groq {model} exception: {e}")
        return None

    def _build_trader_prompt(self, symbol: str, interval: str, data: Dict[str, Any], sentiment: str) -> str:
        s = data.get("suggested_trade", {})
        ob = data.get("order_book", {})
        gk = data.get("gatekeeper", {})
        regime = data.get("regime", {})
        mtf = data.get("mtf_data", {})
        flow = data.get("order_flow", {})
        kelly = data.get("kelly", {})
        whale_sup = ob.get("whale_support_wall", {})
        whale_res = ob.get("whale_resistance_wall", {})
        
        return f"""
You are the Chief Quantitative Officer and Elite Hedge Fund Trader. Your primary directive is ABSOLUTE CAPITAL PRESERVATION, PREDICTABILITY, and CONSISTENT PROFIT HARVESTING.

Market Snapshot:
- Asset: {symbol} (Execution Timeframe: {interval})
- Current Price: ${data['current_price']:,.2f}
- 50 EMA: ${data['ema50']:,.2f} | 200 EMA: ${data['ema200']:,.2f}
- VWAP: ${data.get('vwap', data['current_price']):,.2f}
- Bollinger Bands: Lower ${data.get('bollinger', {}).get('lower', 0):,.2f} | Upper ${data.get('bollinger', {}).get('upper', 0):,.2f} | Squeeze: {data.get('bollinger', {}).get('squeeze', False)}
- RSI (14): {data['rsi']} | MACD Hist: {data['macd']['hist']}
- Fibonacci Golden Pocket (0.618): ${data.get('fibonacci', {}).get('fib_618', 0):,.2f}
- Dominant Candle Pattern: {data.get('dominant_pattern', 'Standard')} (Learned Multiplier: {data.get('pattern_multiplier', 1.0)}x)
- Volume Ratio: {data['vol_ratio']}x average
- ATR Volatility: ${data['atr']:,.2f}

Institutional Macro & Microstructure Intelligence:
- Statistical Market Regime: {regime.get('label', 'Consolidation')} (Optimal Edge: {regime.get('strategy', 'MEAN_REVERSION')})
- Multi-Timeframe Alignment (4H/1H/15m/5m): {mtf.get('verdict', 'NEUTRAL')} (Confluence Score: {mtf.get('alignment_score', 0)})
- Order Flow CVD: {flow.get('flow_bias', 'BALANCED')} (Taker Buyers: {flow.get('taker_buy_pct', 50)}% vs Taker Sellers: {flow.get('taker_sell_pct', 50)}%)
- Order Book Whale Depth: Bid/Ask Ratio {ob.get('bid_ask_ratio', 1.0)}x | Whale Support: ${whale_sup.get('price', 0):,.2f} | Whale Resistance: ${whale_res.get('price', 0):,.2f}
- Fractional Kelly Sizing: ${kelly.get('optimal_margin_usd', 25.0)} margin (Quarter-Kelly)
- 3-Tier Take-Profit Ladder: TP1 ${s.get('long_tp1', 0):,.2f} | TP2 ${s.get('long_tp2', 0):,.2f} | TP3 Runner ${s.get('long_tp3', 0):,.2f}

Pre-Trade Safety Gatekeeper Status:
- Rules Passed: {gk.get('passed_count', 0)}/5
- Gatekeeper Status: {gk.get('status_label', 'Checking')}
- Macro Crypto Sentiment: {sentiment}

Instructions:
1. Validate whether the Multi-Timeframe trend, Order Flow, and Technicals favor BUY, SELL, or HOLD.
2. If Gatekeeper has passed at least 3/5 rules and directional confluence exists, recommend a decisive BUY (LONG) or SELL (SHORT).
3. If market is in dead chop or heavy adverse divergence, output "WAIT / NEUTRAL" (HOLD).
4. Pin Stop-Loss safely behind structural support/resistance or ATR level, and align with the 3-Tier Take-Profit ladder.

Respond ONLY in valid JSON format with this exact structure:
{{
  "signal": "STRONG BUY",
  "action": "LONG",
  "confidence": 85,
  "predicted_win_probability": {data.get('predicted_win_probability', 75.0)},
  "entry": {data['current_price']},
  "tp": {s.get('long_tp', data['current_price'] * 1.02)},
  "sl": {s.get('long_sl', data['current_price'] * 0.99)},
  "rr": "1:2.0",
  "reason": "Institutional order wall and confluence summary."
}}
Valid values for signal: "STRONG BUY", "BUY", "WAIT / NEUTRAL", "SELL", "STRONG SELL".
Valid values for action: "LONG", "SHORT", "HOLD".
"""

    def _parse_json_response(self, text: str, engine_name: str, data: Dict[str, Any], sentiment: str) -> Optional[Dict[str, Any]]:
        try:
            clean_text = text.strip()
            # Strip reasoning model think tags
            if "</think>" in clean_text:
                clean_text = clean_text.split("</think>")[-1].strip()
            
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            else:
                start_idx = clean_text.find("{")
                end_idx = clean_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    clean_text = clean_text[start_idx:end_idx+1]

            parsed = json.loads(clean_text)
            parsed["engine"] = engine_name
            parsed["sentiment"] = sentiment
            ob = data.get("order_book", {})
            parsed["whale_support"] = ob.get("whale_support_wall", {}).get("price", 0.0)
            parsed["whale_resistance"] = ob.get("whale_resistance_wall", {}).get("price", 0.0)
            parsed["gatekeeper_passed"] = data.get("gatekeeper", {}).get("all_passed", False)
            return parsed
        except Exception as e:
            print(f"[AI Brain] JSON parse error: {e} | Raw text: {text[:100]}")
            return None

    def _quant_fallback(self, symbol: str, data: Dict[str, Any], sentiment: str) -> Dict[str, Any]:
        s = data.get("suggested_trade", {})
        net_score = data.get("net_score", 0.0)
        curr_price = data.get("current_price", 0.0)
        gk = data.get("gatekeeper", {})
        prob = data.get("predicted_win_probability", 65.0)
        passed_rules = gk.get("passed_count", 0)
        
        if (passed_rules >= 3 or gk.get("all_passed", False)) and net_score >= 0.8 and prob >= 60:
            sig = "BUY" if net_score < 2.5 else "STRONG BUY"
            act = "LONG"
            entry = s.get("long_entry", curr_price)
            tp = s.get("long_tp", curr_price * 1.02)
            sl = s.get("long_sl", curr_price * 0.99)
            reason = f"Institutional Long confirmed on {symbol}. Gatekeeper validated ({passed_rules}/5 rules) with buyer momentum confluence."
        elif (passed_rules >= 3 or gk.get("all_passed", False)) and net_score <= -0.8 and prob >= 60:
            sig = "SELL" if net_score > -2.5 else "STRONG SELL"
            act = "SHORT"
            entry = s.get("short_entry", curr_price)
            tp = s.get("short_tp", curr_price * 0.98)
            sl = s.get("short_sl", curr_price * 1.01)
            reason = f"Institutional Short confirmed on {symbol}. Gatekeeper validated ({passed_rules}/5 rules) with seller momentum confluence."
        else:
            sig = "WAIT / NEUTRAL"
            act = "HOLD"
            entry = curr_price
            tp = 0.0
            sl = 0.0
            reason = f"Monitoring market structure ({passed_rules}/5 rules passed). Waiting for clean directional breakout."

        ob = data.get("order_book", {})
        return {
            "signal": sig,
            "action": act,
            "confidence": min(max(round(prob), 50), 94),
            "predicted_win_probability": prob,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "rr": s.get("rr_ratio", "1:2.0"),
            "reason": reason,
            "engine": "Quant AI",
            "sentiment": sentiment,
            "whale_support": ob.get("whale_support_wall", {}).get("price", 0.0),
            "whale_resistance": ob.get("whale_resistance_wall", {}).get("price", 0.0),
            "gatekeeper_passed": gk.get("all_passed", False)
        }

ai_brain = EnsembleAITraderBrain()
