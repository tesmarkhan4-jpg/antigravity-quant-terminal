/**
 * Antigravity Quant AI - Institutional Cyber-Quant Trading Terminal
 * High-Predictability Real & Demo Execution Engine
 */

document.addEventListener("DOMContentLoaded", () => {
  // Application State
  let currentSymbol = "BTCUSDT";
  let currentInterval = "15m";
  let chart = null;
  let candleSeries = null;
  let ema50Series = null;
  let ema200Series = null;
  let volumeSeries = null;
  let ws = null;
  let isSoundEnabled = true;
  let latestAiData = null;
  let latestPrice = 0.0;
  let prevPrice = 0.0;

  // Institutional Price Formatting Utility (Crypto Precision)
  function formatCryptoPrice(val) {
    if (val === undefined || val === null || isNaN(val)) return "$0.00";
    const num = parseFloat(val);
    if (num === 0) return "$0.00";
    if (num < 0.001) return `$${num.toFixed(6)}`;
    if (num < 0.1) return `$${num.toFixed(5)}`;
    if (num < 2.0) return `$${num.toFixed(4)}`;
    if (num < 50.0) return `$${num.toFixed(3)}`;
    if (num < 1000.0) return `$${num.toFixed(2)}`;
    return `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  // Header & Global DOM Elements
  const symbolSelect = document.getElementById("symbolSelect");
  const tfButtons = document.querySelectorAll(".tf-btn");
  const tickerSymbol = document.getElementById("tickerSymbol");
  const tickerPrice = document.getElementById("tickerPrice");
  const tickerChange = document.getElementById("tickerChange");
  const engineStatusText = document.getElementById("engineStatusText");
  const autoTradeToggle = document.getElementById("autoTradeToggle");
  const autoBadgeText = document.getElementById("autoBadgeText");
  const soundToggleBtn = document.getElementById("soundToggleBtn");
  const quickPairBar = document.getElementById("quickPairBar");
  const headerWalletUsdt = document.getElementById("headerWalletUsdt");
  const walletBalanceChip = document.getElementById("walletBalanceChip");
  const btnEmergencyCloseAll = document.getElementById("btnEmergencyCloseAll");

  // Real vs Demo Controls
  const btnSelectDemo = document.getElementById("btnSelectDemo");
  const btnSelectReal = document.getElementById("btnSelectReal");
  const modePill = document.getElementById("modePill");
  const modePillText = document.getElementById("modePillText");
  const kpiModeBadge = document.getElementById("kpiModeBadge");

  // KPI Performance Cards
  const balanceUsd = document.getElementById("balanceUsd");
  const balancePkr = document.getElementById("balancePkr");
  const targetProgressPct = document.getElementById("targetProgressPct");
  const progressBarFill = document.getElementById("progressBarFill");
  const dailyPnlPkr = document.getElementById("dailyPnlPkr");
  const dailyPnlUsd = document.getElementById("dailyPnlUsd");
  const predictedWinProbVal = document.getElementById("predictedWinProbVal");
  const macroSentimentTag = document.getElementById("macroSentimentTag");
  const closedTradesCount = document.getElementById("closedTradesCount");
  const openPositionsBadge = document.getElementById("openPositionsBadge");
  const openPnlUsd = document.getElementById("openPnlUsd");
  const openPnlPkr = document.getElementById("openPnlPkr");
  const equityUsd = document.getElementById("equityUsd");
  const equityPkr = document.getElementById("equityPkr");

  // Radar & Order Flow DOM
  const radarTableBody = document.getElementById("radarTableBody");
  const regimeBadge = document.getElementById("regimeBadge");
  const cvdPill = document.getElementById("cvdPill");
  const mtfScoreBadge = document.getElementById("mtfScoreBadge");
  const mtf4h = document.getElementById("mtf4h");
  const mtf1h = document.getElementById("mtf1h");
  const mtf15m = document.getElementById("mtf15m");
  const mtf5m = document.getElementById("mtf5m");

  // Chart Elements
  const activeChartTitle = document.getElementById("activeChartTitle");
  const toggleEma50 = document.getElementById("toggleEma50");
  const toggleEma200 = document.getElementById("toggleEma200");
  const resetZoomBtn = document.getElementById("resetZoomBtn");

  // Dual Slots & Manual Trading
  const slotsIndicatorPill = document.getElementById("slotsIndicatorPill");
  const slot1Box = document.getElementById("slot1Box");
  const slot1Status = document.getElementById("slot1Status");
  const slot1Body = document.getElementById("slot1Body");
  const slot2Box = document.getElementById("slot2Box");
  const slot2Status = document.getElementById("slot2Status");
  const slot2Body = document.getElementById("slot2Body");
  const btnManualLong = document.getElementById("btnManualLong");
  const btnManualShort = document.getElementById("btnManualShort");
  const btnCloseAll = document.getElementById("btnCloseAll");
  const riskSlider = document.getElementById("riskSlider");
  const riskPctLabel = document.getElementById("riskPctLabel");

  // Gatekeeper & Whale Depth
  const gatekeeperOverallBadge = document.getElementById("gatekeeperOverallBadge");
  const gatekeeperRulesContainer = document.getElementById("gatekeeperRulesContainer");
  const depthBidBar = document.getElementById("depthBidBar");
  const depthAskBar = document.getElementById("depthAskBar");
  const depthBidLabel = document.getElementById("depthBidLabel");
  const depthAskLabel = document.getElementById("depthAskLabel");
  const whaleSupportPrice = document.getElementById("whaleSupportPrice");
  const whaleResistancePrice = document.getElementById("whaleResistancePrice");
  const whaleSupportQty = document.getElementById("whaleSupportQty");
  const whaleResistanceQty = document.getElementById("whaleResistanceQty");
  const obRatioBadge = document.getElementById("obRatioBadge");

  // AI Brain & Checklist
  const aiEngineTag = document.getElementById("aiEngineTag");
  const aiVerdictBanner = document.getElementById("aiVerdictBanner");
  const aiActionTitle = document.getElementById("aiActionTitle");
  const confidenceNum = document.getElementById("confidenceNum");
  const aiReasonText = document.getElementById("aiReasonText");
  const aiEntryPrice = document.getElementById("aiEntryPrice");
  const aiTpPrice = document.getElementById("aiTpPrice");
  const aiSlPrice = document.getElementById("aiSlPrice");
  const aiRrRatio = document.getElementById("aiRrRatio");
  const quantNetScore = document.getElementById("quantNetScore");
  const checklistContainer = document.getElementById("checklistContainer");
  const learnedPatternsList = document.getElementById("learnedPatternsList");
  const recentAuditsList = document.getElementById("recentAuditsList");

  // Tables
  const positionsTableBody = document.getElementById("positionsTableBody");
  const activePositionsCount = document.getElementById("activePositionsCount");
  const historyTableBody = document.getElementById("historyTableBody");

  // Circuit Breaker & Daily Target Ceilings
  const circuitAlertBanner = document.getElementById("circuitAlertBanner");
  const resetCircuitBtn = document.getElementById("resetCircuitBtn");
  const dailyTargetBanner = document.getElementById("dailyTargetBanner");
  const resumeTargetBtn = document.getElementById("resumeTargetBtn");

  // Settings Modal
  const openSettingsBtn = document.getElementById("openSettingsBtn");
  const settingsModal = document.getElementById("settingsModal");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const cancelSettingsBtn = document.getElementById("cancelSettingsBtn");
  const saveSettingsBtn = document.getElementById("saveSettingsBtn");
  const tradingModeSelect = document.getElementById("tradingModeSelect");
  const binanceApiKeyInput = document.getElementById("apiKeyInput") || document.getElementById("binanceApiKeyInput");
  const binanceApiSecretInput = document.getElementById("apiSecretInput") || document.getElementById("binanceApiSecretInput");
  const pkrRateInput = document.getElementById("pkrRateInput");
  const dailyTargetPkrInput = document.getElementById("dailyTargetPkrInput");
  const maxRiskPctInput = document.getElementById("maxRiskPctInput");
  const testExchangeBtn = document.getElementById("testExchangeBtn");
  const exchangeStatusMsg = document.getElementById("exchangeStatusMsg");
  const modalExchangeBadge = document.getElementById("modalExchangeBadge");
  const modalWalletTotal = document.getElementById("modalWalletTotal");
  const walletAssetsTableBody = document.getElementById("walletAssetsTableBody");
  const modalStatusBanner = document.getElementById("modalStatusBanner");

  // =========================================================================
  // 1. TRADINGVIEW LIGHTWEIGHT CHARTS (CYBER-QUANT DARK THEME)
  // =========================================================================
  function initChart() {
    const chartContainer = document.getElementById("tradingviewChart");
    if (!chartContainer) return;

    chart = LightweightCharts.createChart(chartContainer, {
      layout: {
        background: { color: "transparent" },
        textColor: "#94A3B8",
        fontSize: 11,
        fontFamily: "'Inter', sans-serif"
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.04)" },
        horzLines: { color: "rgba(255, 255, 255, 0.04)" }
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: { color: "#6366F1", width: 1, style: 2, labelBackgroundColor: "#4F46E5" },
        horzLine: { color: "#6366F1", width: 1, style: 2, labelBackgroundColor: "#4F46E5" }
      },
      rightPriceScale: {
        borderColor: "rgba(255, 255, 255, 0.08)",
        scaleMargins: { top: 0.1, bottom: 0.2 }
      },
      timeScale: {
        borderColor: "rgba(255, 255, 255, 0.08)",
        timeVisible: true,
        secondsVisible: false
      }
    });

    candleSeries = chart.addCandlestickSeries({
      upColor: "#10B981",
      downColor: "#F43F5E",
      borderVisible: false,
      wickUpColor: "#10B981",
      wickDownColor: "#F43F5E"
    });

    volumeSeries = chart.addHistogramSeries({
      color: "rgba(99, 102, 241, 0.25)",
      priceFormat: { type: "volume" },
      priceScaleId: "",
      scaleMargins: { top: 0.82, bottom: 0 }
    });

    ema50Series = chart.addLineSeries({
      color: "#3B82F6",
      lineWidth: 2,
      title: "50 EMA"
    });

    ema200Series = chart.addLineSeries({
      color: "#EAB308",
      lineWidth: 2,
      title: "200 EMA"
    });

    const resizeObserver = new ResizeObserver(entries => {
      if (entries.length === 0 || !entries[0].contentRect) return;
      const { width, height } = entries[0].contentRect;
      chart.applyOptions({ width, height });
    });
    resizeObserver.observe(chartContainer);
  }

  function updateChartCandles(candles) {
    if (!candles || candles.length === 0 || !candleSeries) return;

    const formattedCandles = candles.map(c => ({
      time: c.time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close
    }));

    const formattedVolume = candles.map(c => ({
      time: c.time,
      value: c.volume,
      color: c.close >= c.open ? "rgba(16, 185, 129, 0.35)" : "rgba(244, 63, 94, 0.35)"
    }));

    candleSeries.setData(formattedCandles);
    volumeSeries.setData(formattedVolume);

    const closes = candles.map(c => c.close);
    if (closes.length >= 50 && ema50Series) {
      const ema50 = calculateEmaSeries(closes, 50);
      ema50Series.setData(candles.map((c, i) => ({ time: c.time, value: ema50[i] })));
    }
    if (closes.length >= 200 && ema200Series) {
      const ema200 = calculateEmaSeries(closes, 200);
      ema200Series.setData(candles.map((c, i) => ({ time: c.time, value: ema200[i] })));
    }
  }

  function calculateEmaSeries(prices, period) {
    const k = 2 / (period + 1);
    let ema = prices[0];
    return prices.map(p => {
      ema = p * k + ema * (1 - k);
      return Math.round(ema * 100) / 100;
    });
  }

  // =========================================================================
  // 2. REALTIME WEBSOCKET & DATA ENGINE
  // =========================================================================
  function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      if (engineStatusText) {
        engineStatusText.textContent = "AI Quant Live";
        engineStatusText.style.color = "#34D399";
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleStreamPayload(msg);
      } catch (err) {
        console.error("WebSocket message decode error:", err);
      }
    };

    ws.onclose = () => {
      if (engineStatusText) {
        engineStatusText.textContent = "Reconnecting...";
        engineStatusText.style.color = "#F59E0B";
      }
      setTimeout(connectWebSocket, 1500);
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      ws.close();
    };
  }

  function handleStreamPayload(data) {
    if (!data) return;

    // 1. Ticker Header Update
    if (data.current_price || (data.candles && data.candles.length > 0)) {
      const price = data.current_price || data.candles[data.candles.length - 1].close;
      updateTickerPrice(price);
    }

    // 2. Chart Candlesticks
    if (data.candles) {
      updateChartCandles(data.candles);
    }

    // 3. KPI Performance Cards & Wallet
    if (data.account) {
      updateAccountKpis(data.account);
      renderDualSlots(data.account);
    }

    // 4. Multi-Pair Opportunity Radar & Quick Chips
    if (data.radar) {
      renderRadar(data.radar);
      renderQuickPairBar(data.radar);
    }

    // 5. Order Book Depth & Whale Walls
    if (data.order_book) {
      renderOrderBookDepth(data.order_book);
    }

    // 6. 5-Rule Pre-Trade Gatekeeper
    if (data.gatekeeper) {
      renderGatekeeper(data.gatekeeper);
    }

    // 7. 12-Point Institutional Checklist
    if (data.analysis) {
      renderChecklist(data.analysis);
    }

    // 8. AI Senior Trader Brain
    if (data.ai) {
      latestAiData = data.ai;
      updateAiDecisionCard(data.ai);
    }

    // 9. Telemetry (Regime, CVD, MTF, Mode Sync)
    renderInstitutionalTelemetry(data);

    // 10. Tables: Positions & History
    if (data.positions) {
      renderPositionsTable(data.positions);
    }
    if (data.history) {
      renderHistoryTable(data.history);
    }

    // 11. Self-Learning Weights
    if (data.learning) {
      renderLearningWidget(data.learning);
    }
  }

  // =========================================================================
  // 3. REAL VS DEMO MODE SYNCHRONIZATION
  // =========================================================================
  function syncModeButtons(mode, account) {
    const isLive = mode === "BINANCE_LIVE";

    if (btnSelectDemo) btnSelectDemo.classList.toggle("active", !isLive);
    if (btnSelectReal) btnSelectReal.classList.toggle("active", isLive);

    if (modePill && modePillText) {
      modePill.className = "mode-pill";
      if (isLive) {
        modePill.classList.add("live");
        modePillText.textContent = "REAL BINANCE LIVE";
      } else if (mode === "BINANCE_TESTNET") {
        modePill.classList.add("testnet");
        modePillText.textContent = "TESTNET SANDBOX";
      } else {
        modePill.classList.add("paper");
        modePillText.textContent = "DEMO SIMULATION";
      }
    }

    if (kpiModeBadge) {
      if (isLive) {
        kpiModeBadge.textContent = "REAL BINANCE LIVE";
        kpiModeBadge.className = "badge-tag mode-indicator-badge success";
      } else {
        kpiModeBadge.textContent = "DEMO SANDBOX";
        kpiModeBadge.className = "badge-tag mode-indicator-badge";
      }
    }

    if (tradingModeSelect) {
      tradingModeSelect.value = mode || "SIMULATED_PAPER";
    }
    if (modalExchangeBadge) {
      modalExchangeBadge.textContent = (mode || "SIMULATED_PAPER").replace(/_/g, " ");
    }
  }

  async function switchTradingMode(targetMode) {
    const isTargetReal = targetMode === "BINANCE_LIVE";
    if (isTargetReal && btnSelectReal) btnSelectReal.style.opacity = "0.6";
    if (!isTargetReal && btnSelectDemo) btnSelectDemo.style.opacity = "0.6";

    try {
      const res = await fetch("/api/toggle_mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: targetMode })
      });
      const data = await res.json();
      if (data.success) {
        playNotificationSound();
        syncModeButtons(data.trading_mode, data.account);
        if (data.account) {
          updateAccountKpis(data.account);
          renderDualSlots(data.account);
        }
      } else {
        alert(data.message || "Could not switch mode");
        if (isTargetReal) {
          settingsModal.classList.remove("hidden");
        }
      }
    } catch (err) {
      console.error("Error toggling mode:", err);
    } finally {
      if (btnSelectDemo) btnSelectDemo.style.opacity = "1";
      if (btnSelectReal) btnSelectReal.style.opacity = "1";
    }
  }

  if (btnSelectDemo) {
    btnSelectDemo.addEventListener("click", () => switchTradingMode("SIMULATED_PAPER"));
  }
  if (btnSelectReal) {
    btnSelectReal.addEventListener("click", () => switchTradingMode("BINANCE_LIVE"));
  }
  if (modePill) {
    modePill.addEventListener("click", () => {
      const isCurrentlyReal = btnSelectReal && btnSelectReal.classList.contains("active");
      switchTradingMode(isCurrentlyReal ? "SIMULATED_PAPER" : "BINANCE_LIVE");
    });
  }

  // =========================================================================
  // 4. TICKER & QUICK CHIPS
  // =========================================================================
  function updateTickerPrice(price) {
    if (!price || price <= 0) return;
    latestPrice = price;

    if (tickerPrice) {
      tickerPrice.textContent = `$${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
      if (prevPrice > 0) {
        if (price > prevPrice) {
          tickerPrice.style.color = "#34D399";
        } else if (price < prevPrice) {
          tickerPrice.style.color = "#F43F5E";
        }
        setTimeout(() => { if (tickerPrice) tickerPrice.style.color = "#FFFFFF"; }, 600);
      }
      prevPrice = price;
    }
  }

  function renderQuickPairBar(radar) {
    if (!quickPairBar || !radar || radar.length === 0) return;

    quickPairBar.innerHTML = "";
    radar.forEach(pair => {
      const chip = document.createElement("div");
      chip.className = `quick-pair-chip ${pair.symbol === currentSymbol ? 'active' : ''}`;
      chip.setAttribute("data-sym", pair.symbol);

      const changeClass = pair.change_pct >= 0 ? "text-success" : "text-danger";
      const shortSym = pair.symbol.replace("USDT", "");

      chip.innerHTML = `
        <span class="chip-sym">${shortSym}</span>
        <span class="chip-price mono">$${pair.price >= 1 ? pair.price.toLocaleString(undefined, { minimumFractionDigits: 2 }) : pair.price.toFixed(4)}</span>
        <span class="${changeClass} mono" style="font-size: 0.68rem; font-weight: 700;">${pair.change_pct >= 0 ? '+' : ''}${pair.change_pct}%</span>
      `;

      chip.addEventListener("click", () => selectSymbol(pair.symbol));
      quickPairBar.appendChild(chip);
    });
  }

  async function selectSymbol(sym) {
    if (sym === currentSymbol) return;
    currentSymbol = sym;
    if (symbolSelect) symbolSelect.value = sym;
    if (tickerSymbol) tickerSymbol.textContent = `${sym.replace("USDT", "")}/USDT`;
    if (activeChartTitle) activeChartTitle.textContent = "Candlestick Chart";

    await fetch("/api/symbol", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: currentSymbol, interval: currentInterval })
    });
  }

  // =========================================================================
  // 5. UPDATE KPI PERFORMANCE CARDS & WALLET
  // =========================================================================
  function updateAccountKpis(acc) {
    if (!acc) return;

    // Display Balance based on Real vs Demo
    if (balanceUsd) {
      if (acc.is_real_trading && acc.live_usdt_balance !== undefined) {
        balanceUsd.textContent = `$${acc.live_usdt_balance.toFixed(2)}`;
      } else {
        balanceUsd.textContent = `$${acc.balance_usd.toFixed(2)}`;
      }
    }
    if (balancePkr) {
      const pkrVal = acc.is_real_trading ? (acc.live_usdt_balance || 0) * (acc.pkr_rate || 280) : acc.balance_pkr;
      balancePkr.textContent = `${Math.round(pkrVal).toLocaleString()} PKR`;
    }

    if (headerWalletUsdt) {
      const usdt = acc.live_usdt_balance !== undefined ? acc.live_usdt_balance : 0.0;
      headerWalletUsdt.textContent = `$${usdt.toFixed(2)} USDT`;
    }

    if (equityUsd) equityUsd.textContent = `Equity: $${acc.equity_usd.toFixed(2)}`;
    if (equityPkr) equityPkr.textContent = `${acc.equity_pkr.toLocaleString()} PKR`;

    if (targetProgressPct) targetProgressPct.textContent = `${acc.target_progress_pct}%`;
    if (progressBarFill) progressBarFill.style.width = `${acc.target_progress_pct}%`;

    if (dailyPnlUsd) dailyPnlUsd.textContent = `${acc.daily_pnl_usd >= 0 ? "+" : ""}$${acc.daily_pnl_usd.toFixed(2)}`;
    if (dailyPnlPkr) {
      dailyPnlPkr.textContent = `${acc.daily_pnl_pkr >= 0 ? "+" : ""}${acc.daily_pnl_pkr.toLocaleString()} PKR`;
      dailyPnlPkr.className = acc.daily_pnl_usd >= 0 ? "mono text-success" : "mono text-danger";
    }

    if (closedTradesCount) closedTradesCount.textContent = `${acc.total_trades} Closed`;
    if (openPositionsBadge) openPositionsBadge.textContent = `${acc.open_positions_count}/2 Slots`;

    if (openPnlUsd) {
      openPnlUsd.textContent = `${acc.unrealized_pnl_usd >= 0 ? "+" : ""}$${acc.unrealized_pnl_usd.toFixed(2)}`;
      openPnlUsd.className = acc.unrealized_pnl_usd >= 0 ? "kpi-main-val mono text-success" : "kpi-main-val mono text-danger";
    }
    if (openPnlPkr) {
      openPnlPkr.textContent = `${acc.unrealized_pnl_pkr >= 0 ? "+" : ""}${acc.unrealized_pnl_pkr.toLocaleString()} PKR`;
      openPnlPkr.className = acc.unrealized_pnl_pkr >= 0 ? "kpi-sub-val mono text-success" : "kpi-sub-val mono text-danger";
    }

    if (autoTradeToggle) {
      autoTradeToggle.checked = acc.auto_trade_enabled;
      if (autoBadgeText) {
        autoBadgeText.textContent = acc.auto_trade_enabled ? "ON" : "OFF";
        autoBadgeText.className = acc.auto_trade_enabled ? "auto-badge active" : "auto-badge";
      }
    }

    if (circuitAlertBanner) {
      if (acc.circuit_breaker_triggered) circuitAlertBanner.classList.remove("hidden");
      else circuitAlertBanner.classList.add("hidden");
    }

    if (dailyTargetBanner) {
      if (acc.daily_target_reached) {
        dailyTargetBanner.style.display = "flex";
        dailyTargetBanner.classList.remove("hidden");
      } else {
        dailyTargetBanner.style.display = "none";
        dailyTargetBanner.classList.add("hidden");
      }
    }

    // Render Wallet Assets in Modal
    if (acc.wallet_assets) {
      renderWalletAssetsModal(acc.wallet_assets, acc.live_usdt_balance);
    }
  }

  function renderWalletAssetsModal(assets, usdtBal) {
    if (!walletAssetsTableBody) return;
    if (modalWalletTotal) {
      modalWalletTotal.textContent = `Free USDT: $${(usdtBal || 0).toFixed(2)}`;
    }

    if (!assets || assets.length === 0) {
      walletAssetsTableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 14px;">
            0 assets found with non-zero balances. Deposit USDT on Binance Spot to execute live trades.
          </td>
        </tr>
      `;
      return;
    }

    walletAssetsTableBody.innerHTML = "";
    assets.forEach(a => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><strong style="color: #FFFFFF;">${a.asset}</strong></td>
        <td class="mono text-success">${a.free}</td>
        <td class="mono text-muted">${a.locked}</td>
        <td class="mono"><strong>${a.total}</strong></td>
      `;
      walletAssetsTableBody.appendChild(row);
    });
  }

  // =========================================================================
  // 6. DUAL-BID POSITION SLOTS & 3-TIER LADDER
  // =========================================================================
  function renderDualSlots(acc) {
    const s1 = acc.slot_1;
    const s2 = acc.slot_2;
    if (slotsIndicatorPill) {
      slotsIndicatorPill.textContent = `${acc.available_slots} Slots Available`;
    }

    // Slot 1
    if (s1) {
      slot1Box.className = "slot-box active";
      slot1Status.textContent = "ACTIVE";
      slot1Status.className = "slot-status-tag occupied";
      slot1Body.innerHTML = buildSlotBodyHtml(s1);
    } else {
      slot1Box.className = "slot-box";
      slot1Status.textContent = "VACANT";
      slot1Status.className = "slot-status-tag vacant";
      slot1Body.innerHTML = `
        <div class="empty-slot-wrap">
          <span class="empty-slot-icon">🔍</span>
          <div class="empty-slot-text">Scanning 12 pairs for #1 Highest-Conviction A+ Setup...</div>
          <div class="empty-slot-sub">Auto 1:2 R:R Guard & 3-Tier Take-Profit Ladder Armed</div>
        </div>`;
    }

    // Slot 2
    if (s2) {
      slot2Box.className = "slot-box active";
      slot2Status.textContent = "ACTIVE";
      slot2Status.className = "slot-status-tag occupied";
      slot2Body.innerHTML = buildSlotBodyHtml(s2);
    } else {
      slot2Box.className = "slot-box";
      slot2Status.textContent = "VACANT";
      slot2Status.className = "slot-status-tag vacant";
      slot2Body.innerHTML = `
        <div class="empty-slot-wrap">
          <span class="empty-slot-icon">🔍</span>
          <div class="empty-slot-text">Scanning 12 pairs for #2 Highest-Conviction A+ Setup...</div>
          <div class="empty-slot-sub">Trailing Breakeven Shield & Runner Mode Ready</div>
        </div>`;
    }

  }

  function buildSlotBodyHtml(pos) {
    const isProfit = pos.unrealized_pnl >= 0;
    const pnlClass = isProfit ? "text-success" : "text-danger";
    const pkrText = `${pos.unrealized_pnl_pkr >= 0 ? "+" : ""}${Math.round(pos.unrealized_pnl_pkr).toLocaleString()} PKR`;
    const closeBtnHtml = isProfit
      ? `<button class="btn-close-pos btn-profit-take" data-id="${pos.id}">⚡ Lock Profit (${pkrText})</button>`
      : `<button class="btn-close-pos" data-id="${pos.id}">Close</button>`;

    return `
      <div class="active-slot-details">
        <div class="slot-sym-row">
          <span class="slot-symbol-text">${pos.symbol} <span class="pos-type-tag ${pos.type === 'LONG' ? 'long' : 'short'}">${pos.type}</span></span>
          ${closeBtnHtml}
        </div>
        ${pos.breakeven_locked ? '<div class="shield-tag"><span class="shield-icon">🛡️</span> Breakeven Shield Active (0 Risk)</div>' : ''}
        <div class="slot-meta-row">
          Entry: <strong class="mono text-white">${formatCryptoPrice(pos.entry_price)}</strong> | Live: <strong class="mono text-white">${formatCryptoPrice(pos.current_price)}</strong>
        </div>
        <div class="slot-pnl-row">
          <span class="${pnlClass} mono slot-pnl-main">
            ${pos.unrealized_pnl >= 0 ? "+" : ""}$${pos.unrealized_pnl.toFixed(2)} (${pos.roi_pct}%)
          </span>
          <span class="${pnlClass} mono slot-pnl-pkr">
            ${pkrText}
          </span>
        </div>
        ${buildTpLadderHtml(pos)}
      </div>
    `;
  }

  function buildTpLadderHtml(pos) {
    if (!pos) return "";
    const tp1Hit = pos.tp1_hit;
    const tp2Hit = pos.tp2_hit;
    const runnerActive = pos.trailing_active;
    const tp1Price = pos.tp1 ? formatCryptoPrice(pos.tp1) : "1.2R";
    const tp2Price = pos.tp2 ? formatCryptoPrice(pos.tp2) : "2.0R";
    const tp3Price = pos.tp3 ? formatCryptoPrice(pos.tp3) : "3.5R";

    return `
      <div class="tp-ladder-container">
        <div class="tp-ladder-title-row">
          <span>3-Tier Profit Ladder</span>
          <span class="ladder-status">${runnerActive ? '🚀 Trailing Runner' : (pos.breakeven_locked ? '🛡️ BE Shield' : 'Arming TP1')}</span>
        </div>
        <div class="tp-ladder-steps">
          <div class="tp-step-box ${tp1Hit ? 'hit' : ''}">
            <span class="step-label">TP1 (40%)</span>
            <span class="step-price mono">${tp1Hit ? '✓ Banked' : tp1Price}</span>
          </div>
          <div class="tp-step-box ${tp2Hit ? 'hit' : ''}">
            <span class="step-label">TP2 (40%)</span>
            <span class="step-price mono">${tp2Hit ? '✓ Banked' : tp2Price}</span>
          </div>
          <div class="tp-step-box runner ${runnerActive ? 'active' : ''}">
            <span class="step-label">Runner (20%)</span>
            <span class="step-price mono">${runnerActive ? '🚀 Trailing' : tp3Price}</span>
          </div>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 7. MULTI-PAIR RADAR & MARKET DEPTH
  // =========================================================================
  function renderRadar(radar) {
    if (!radarTableBody || !radar) return;

    radarTableBody.innerHTML = "";
    radar.forEach((pair, idx) => {
      const row = document.createElement("tr");
      const changeClass = pair.change_pct >= 0 ? "text-success mono" : "text-danger mono";
      const scoreColor = pair.opp_score >= 80 ? "#10B981" : (pair.opp_score >= 65 ? "#38BDF8" : "#94A3B8");
      const shortSym = pair.symbol.replace("USDT", "");
      const actionBadge = pair.action || (pair.verdict.includes("BUY") ? "LONG" : (pair.verdict.includes("SELL") ? "SHORT" : "WAIT"));
      const badgeClass = actionBadge === "LONG" ? "success" : (actionBadge === "SHORT" ? "text-danger" : "");

      row.className = "radar-row-interactive";
      row.style.cursor = "pointer";
      row.title = `Click to load ${pair.symbol} live chart`;
      row.innerHTML = `
        <td style="width: 24px; padding-left: 2px;"><strong style="color:#818CF8;">#${idx + 1}</strong></td>
        <td><strong class="text-white">${shortSym}</strong></td>
        <td><span class="mono font-semibold">${formatCryptoPrice(pair.price)}</span></td>
        <td class="${changeClass}">${pair.change_pct >= 0 ? '+' : ''}${pair.change_pct}%</td>
        <td style="text-align: right; padding-right: 6px;">
          <div style="display:inline-flex; align-items:center; gap:6px;">
            <strong class="mono" style="color: ${scoreColor}; font-size: 0.82rem;">${pair.opp_score}</strong>
            <span class="badge-tag ${badgeClass}" style="font-size: 0.66rem; font-weight: 800; padding: 2px 6px;">${actionBadge}</span>
          </div>
        </td>
      `;
      row.addEventListener("click", () => {
        selectSymbol(pair.symbol);
      });
      radarTableBody.appendChild(row);
    });
  }

  function renderOrderBookDepth(ob) {
    if (!ob) return;
    const bidPct = Math.max(10, Math.min(90, ob.bid_pct || 50));
    const askPct = Math.max(10, Math.min(90, ob.ask_pct || 50));

    if (depthBidBar) depthBidBar.style.width = `${bidPct}%`;
    if (depthAskBar) depthAskBar.style.width = `${askPct}%`;
    if (depthBidLabel) depthBidLabel.textContent = `Bids: ${bidPct.toFixed(1)}%`;
    if (depthAskLabel) depthAskLabel.textContent = `Asks: ${askPct.toFixed(1)}%`;

    if (obRatioBadge) {
      obRatioBadge.textContent = `${ob.bid_ask_ratio || 1.0}x Ratio`;
      if ((ob.bid_ask_ratio || 1.0) > 1.2) obRatioBadge.className = "badge-tag success";
      else if ((ob.bid_ask_ratio || 1.0) < 0.8) obRatioBadge.className = "badge-tag text-danger";
      else obRatioBadge.className = "badge-tag";
    }

    const sup = ob.whale_support_wall || ob.whale_support;
    if (whaleSupportPrice && sup) {
      whaleSupportPrice.textContent = formatCryptoPrice(sup.price || 0);
    }
    if (whaleSupportQty && sup) {
      whaleSupportQty.textContent = `${(sup.qty || 0).toLocaleString()} units`;
    }

    const res = ob.whale_resistance_wall || ob.whale_resistance;
    if (whaleResistancePrice && res) {
      whaleResistancePrice.textContent = formatCryptoPrice(res.price || 0);
    }
    if (whaleResistanceQty && res) {
      whaleResistanceQty.textContent = `${(res.qty || 0).toLocaleString()} units`;
    }
  }

  function renderGatekeeper(gk) {
    if (!gk) return;

    if (gatekeeperOverallBadge) {
      if (gk.all_passed) {
        gatekeeperOverallBadge.textContent = "✓ 5/5 READY";
        gatekeeperOverallBadge.className = "gatekeeper-status-badge passed";
      } else {
        const passedCount = gk.passed_count !== undefined ? gk.passed_count : (gk.pass_count || 0);
        const total = gk.total_rules || 5;
        gatekeeperOverallBadge.textContent = `✕ ${passedCount}/${total} BLOCKED`;
        gatekeeperOverallBadge.className = "gatekeeper-status-badge blocked";
      }
    }

    if (predictedWinProbVal && gk.predicted_win_probability !== undefined) {
      predictedWinProbVal.textContent = `${gk.predicted_win_probability}%`;
    }

    if (gatekeeperRulesContainer && gk.rules) {
      gatekeeperRulesContainer.innerHTML = "";
      gk.rules.forEach(r => {
        const item = document.createElement("div");
        item.className = `gatekeeper-rule-item ${r.passed ? 'passed' : 'blocked'}`;
        item.innerHTML = `
          <div class="gatekeeper-rule-header">
            <span class="gatekeeper-rule-name">${r.name}</span>
            <span class="gatekeeper-rule-status mono">${r.passed ? 'PASS ✓' : 'BLOCKED ✕'}</span>
          </div>
          <div class="gatekeeper-rule-detail">${r.detail}</div>
        `;
        gatekeeperRulesContainer.appendChild(item);
      });
    }
  }

  function renderChecklist(analysis) {
    if (!analysis || !analysis.checklist) return;

    if (quantNetScore) {
      quantNetScore.textContent = `${analysis.net_score >= 0 ? "+" : ""}${analysis.net_score.toFixed(1)}`;
      quantNetScore.className = analysis.net_score > 1.0 ? "score-badge text-success mono" : (analysis.net_score < -1.0 ? "score-badge text-danger mono" : "score-badge text-muted mono");
    }

    if (checklistContainer) {
      checklistContainer.innerHTML = "";
      analysis.checklist.forEach(item => {
        const card = document.createElement("div");
        let typeClass = "neutral";
        let icon = "—";
        if (item.status === "PASS_BULL") { typeClass = "bullish"; icon = "✓"; }
        else if (item.status === "PASS_BEAR") { typeClass = "bearish"; icon = "✕"; }

        card.className = `check-item ${typeClass}`;
        card.innerHTML = `
          <div class="check-icon-box">${icon}</div>
          <div class="check-details">
            <div class="check-top-row">
              <span class="check-title">${item.id}. ${item.name}</span>
              <span class="check-value-tag mono">${item.value}</span>
            </div>
            <p class="check-desc">${item.detail}</p>
          </div>
        `;
        checklistContainer.appendChild(card);
      });
    }
  }

  function updateAiDecisionCard(ai) {
    if (!ai) return;

    if (aiEngineTag) aiEngineTag.textContent = ai.engine || "Anthropic Claude 3.5 Sonnet";
    if (aiActionTitle) aiActionTitle.textContent = ai.signal;
    if (confidenceNum) confidenceNum.textContent = `${ai.confidence}%`;
    if (aiReasonText) aiReasonText.textContent = ai.reason;
    if (aiRrRatio) aiRrRatio.textContent = ai.rr || "1:2.0";

    if (macroSentimentTag && ai.sentiment) {
      macroSentimentTag.textContent = ai.sentiment;
      if (ai.sentiment.toLowerCase().includes("greed")) macroSentimentTag.className = "text-success";
      else if (ai.sentiment.toLowerCase().includes("fear")) macroSentimentTag.className = "text-danger";
      else macroSentimentTag.className = "text-muted";
    }

    if (aiVerdictBanner) {
      aiVerdictBanner.className = "ai-verdict-banner";
      if (ai.signal.includes("BUY")) aiVerdictBanner.classList.add("buy");
      else if (ai.signal.includes("SELL")) aiVerdictBanner.classList.add("sell");
      else aiVerdictBanner.classList.add("wait");
    }

    if (ai.entry && aiEntryPrice) {
      aiEntryPrice.textContent = formatCryptoPrice(ai.entry);
      aiTpPrice.textContent = formatCryptoPrice(ai.tp);
      aiSlPrice.textContent = formatCryptoPrice(ai.sl);
    }
  }

  function renderInstitutionalTelemetry(data) {
    if (!data) return;

    // 1. Regime
    if (regimeBadge && data.regime) {
      const reg = data.regime.regime || "EVALUATING";
      regimeBadge.innerHTML = `<span class="regime-dot"></span> REGIME: ${reg.replace(/_/g, " ")}`;
    }

    // 2. CVD Flow
    if (cvdPill && data.order_flow) {
      const of = data.order_flow;
      let biasLabel = "Balanced";
      if (of.flow_bias) {
        if (of.flow_bias.includes("DISTRIBUTION")) biasLabel = "Distribution";
        else if (of.flow_bias.includes("ACCUMULATION")) biasLabel = "Accumulation";
        else if (of.flow_bias.includes("ABSORPTION")) biasLabel = "Absorption";
        else biasLabel = of.flow_bias.replace(/INSTITUTIONAL_/g, "").replace(/_/g, " ");
      }
      const buyPct = of.taker_buy_pct !== undefined ? of.taker_buy_pct : 50;
      const shortBias = biasLabel === "Accumulation" ? "Accum" : (biasLabel === "Distribution" ? "Distrib" : biasLabel);
      cvdPill.textContent = `${shortBias} (${buyPct}% Buy)`;
      if (buyPct >= 60) cvdPill.className = "badge-tag success";
      else if ((of.taker_sell_pct || (100 - buyPct)) >= 60) cvdPill.className = "badge-tag text-danger";
      else cvdPill.className = "badge-tag";
    }

    // 3. MTF
    if (data.mtf) {
      const m = data.mtf;
      if (mtfScoreBadge) {
        const s = m.alignment_score || 0;
        mtfScoreBadge.textContent = `${s >= 0 ? "+" : ""}${s.toFixed(1)} MTF`;
        mtfScoreBadge.className = `mtf-score-tag mono ${s > 0 ? 'positive' : (s < 0 ? 'negative' : '')}`;
      }
      if (m.status_by_tf) {
        updateMtfCell(mtf4h, "4H", m.status_by_tf["4h"]);
        updateMtfCell(mtf1h, "1H", m.status_by_tf["1h"]);
        updateMtfCell(mtf15m, "15M", m.status_by_tf["15m"]);
        updateMtfCell(mtf5m, "5M", m.status_by_tf["5m"]);
      }
    }

    // 4. Mode Synchronization
    if (data.account) {
      syncModeButtons(data.account.trading_mode, data.account);
    }
  }

  function updateMtfCell(el, tf, status) {
    if (!el) return;
    const st = status || "NEUTRAL";
    const stClass = st === "BULLISH" ? "bullish" : (st === "BEARISH" ? "bearish" : "");
    el.innerHTML = `<span class="tf-name">${tf}</span><span class="tf-status ${stClass}">${st}</span>`;
  }

  // =========================================================================
  // 8. TABLES & SELF-LEARNING
  // =========================================================================
  function renderPositionsTable(positions) {
    if (activePositionsCount) activePositionsCount.textContent = `${positions.length} Active`;
    if (!positionsTableBody) return;

    if (!positions || positions.length === 0) {
      positionsTableBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="11">No active positions. Dual-bid auto execution will appear here.</td>
        </tr>`;
      return;
    }

    positionsTableBody.innerHTML = "";
    positions.forEach(pos => {
      const row = document.createElement("tr");
      const isLong = pos.type === "LONG";
      const pnlClass = pos.unrealized_pnl >= 0 ? "text-success mono" : "text-danger mono";

      row.innerHTML = `
        <td><strong style="color: #6366F1;">Slot ${pos.slot_num || 1}</strong></td>
        <td><strong class="mono text-white">${pos.id}</strong></td>
        <td><span class="pos-type-tag ${isLong ? 'long' : 'short'}">${pos.type}</span></td>
        <td><strong class="text-white">${pos.symbol}</strong></td>
        <td class="mono">${formatCryptoPrice(pos.entry_price)}</td>
        <td class="mono">${formatCryptoPrice(pos.current_price)}</td>
        <td class="text-success mono font-semibold">${formatCryptoPrice(pos.tp)}</td>
        <td class="text-danger mono font-semibold">${formatCryptoPrice(pos.sl)}</td>
        <td class="${pnlClass}"><strong>${pos.unrealized_pnl >= 0 ? "+" : ""}$${pos.unrealized_pnl.toFixed(2)}</strong> (${pos.roi_pct}%)</td>
        <td class="${pnlClass}">${pos.unrealized_pnl_pkr >= 0 ? "+" : ""}${Math.round(pos.unrealized_pnl_pkr).toLocaleString()} PKR</td>
        <td>
          <button class="btn-close-pos ${pos.unrealized_pnl >= 0 ? 'btn-profit-take' : ''}" data-id="${pos.id}">
            ${pos.unrealized_pnl >= 0 ? '⚡ Lock Profit' : 'Close'}
          </button>
        </td>
      `;
      positionsTableBody.appendChild(row);
    });
  }

  function renderHistoryTable(history) {
    if (!historyTableBody) return;
    if (!history || history.length === 0) {
      historyTableBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="7">Trade execution history will be recorded here.</td>
        </tr>`;
      return;
    }

    historyTableBody.innerHTML = "";
    history.slice(0, 10).forEach(trd => {
      const row = document.createElement("tr");
      const pnlClass = trd.realized_pnl >= 0 ? "text-success mono" : "text-danger mono";

      row.innerHTML = `
        <td class="mono text-muted">${trd.close_time}</td>
        <td><strong class="mono text-white">${trd.id} <span style="font-size:0.7rem; color:#818CF8; font-weight:700;">(${trd.symbol || ''})</span></strong></td>
        <td><span class="pos-type-tag ${trd.type === 'LONG' ? 'long' : 'short'}">${trd.type}</span></td>
        <td class="mono">${formatCryptoPrice(trd.exit_price)}</td>
        <td><span class="badge-tag ${trd.outcome === 'TAKE_PROFIT' || trd.outcome.includes('PROFIT') || trd.realized_pnl > 0 ? 'success' : ''}">${trd.outcome}</span></td>
        <td class="${pnlClass}"><strong>${trd.realized_pnl >= 0 ? "+" : ""}$${trd.realized_pnl.toFixed(2)}</strong></td>
        <td class="${pnlClass}">${trd.realized_pnl_pkr >= 0 ? "+" : ""}${Math.round(trd.realized_pnl_pkr).toLocaleString()} PKR</td>
      `;
      historyTableBody.appendChild(row);
    });
  }

  function renderLearningWidget(learning) {
    if (!learning) return;

    if (learning.patterns && learnedPatternsList) {
      learnedPatternsList.innerHTML = "";
      learning.patterns.forEach(p => {
        const row = document.createElement("div");
        row.className = "pattern-row";
        row.innerHTML = `
          <div style="display: flex; align-items: center; gap: 6px;">
            <span class="pattern-name">${p.name}</span>
            <span class="pattern-weight-tag">${p.weight}x Boost</span>
          </div>
          <span class="pattern-rate-pill mono">${p.win_rate}% Win (${p.wins}W / ${p.losses}L)</span>
        `;
        learnedPatternsList.appendChild(row);
      });
    }

    if (learning.recent_audits && recentAuditsList) {
      if (learning.recent_audits.length > 0) {
        recentAuditsList.innerHTML = "";
        learning.recent_audits.slice(0, 5).forEach(a => {
          const item = document.createElement("div");
          item.style.padding = "6px 8px";
          item.style.marginBottom = "4px";
          item.style.background = "rgba(0,0,0,0.25)";
          item.style.borderRadius = "4px";
          item.style.fontSize = "0.72rem";
          item.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
              <strong class="mono" style="color:#FFF;">${a.id} (${a.symbol})</strong>
              <span class="${a.pnl_usd >= 0 ? 'text-success mono' : 'text-danger mono'}">${a.pnl_usd >= 0 ? '+' : ''}$${a.pnl_usd.toFixed(2)}</span>
            </div>
            <div style="color:var(--text-muted); font-size:0.68rem;">${a.post_mortem || a.ai_reason}</div>
          `;
          recentAuditsList.appendChild(item);
        });
      }
    }
  }

  // =========================================================================
  // 9. MANUAL EXECUTION & INTERACTIONS
  // =========================================================================
  symbolSelect.addEventListener("change", () => selectSymbol(symbolSelect.value));

  tfButtons.forEach(btn => {
    btn.addEventListener("click", async () => {
      tfButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentInterval = btn.getAttribute("data-tf");
      await fetch("/api/symbol", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: currentSymbol, interval: currentInterval })
      });
    });
  });

  autoTradeToggle.addEventListener("change", async () => {
    const isEnabled = autoTradeToggle.checked;
    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        auto_trade: isEnabled,
        risk_pct: parseFloat(riskSlider.value)
      })
    });
    autoBadgeText.textContent = isEnabled ? "ON" : "OFF";
    autoBadgeText.className = isEnabled ? "auto-badge active" : "auto-badge";
    playNotificationSound();
  });

  riskSlider.addEventListener("input", async () => {
    const riskVal = parseFloat(riskSlider.value);
    const riskDollar = (200 * (riskVal / 100)).toFixed(2);
    riskPctLabel.textContent = `${riskVal.toFixed(1)}% ($${riskDollar} / slot)`;

    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        auto_trade: autoTradeToggle.checked,
        risk_pct: riskVal
      })
    });
  });

  if (btnManualLong) {
    btnManualLong.addEventListener("click", async () => {
      if (!latestPrice) return;
      btnManualLong.disabled = true;
      const prevText = btnManualLong.textContent;
      btnManualLong.textContent = "Submitting...";
      try {
        const sl = latestAiData && latestAiData.sl > 0 ? latestAiData.sl : latestPrice * 0.99;
        const tp = latestAiData && latestAiData.tp > 0 ? latestAiData.tp : latestPrice * 1.02;

        const res = await fetch("/api/order", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol: currentSymbol,
            type: "LONG",
            entry: latestPrice,
            tp: tp,
            sl: sl,
            reason: "Manual Long Execution"
          })
        });
        const json = await res.json();
        if (json.success) playNotificationSound();
        else alert(json.message);
      } catch (err) {
        console.error("Manual Long Error:", err);
      } finally {
        btnManualLong.disabled = false;
        btnManualLong.textContent = prevText;
      }
    });
  }

  if (btnManualShort) {
    btnManualShort.addEventListener("click", async () => {
      if (!latestPrice) return;
      btnManualShort.disabled = true;
      const prevText = btnManualShort.textContent;
      btnManualShort.textContent = "Submitting...";
      try {
        const sl = latestAiData && latestAiData.sl > 0 ? latestAiData.sl : latestPrice * 1.01;
        const tp = latestAiData && latestAiData.tp > 0 ? latestAiData.tp : latestPrice * 0.98;

        const res = await fetch("/api/order", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol: currentSymbol,
            type: "SHORT",
            entry: latestPrice,
            tp: tp,
            sl: sl,
            reason: "Manual Short Execution"
          })
        });
        const json = await res.json();
        if (json.success) playNotificationSound();
        else alert(json.message);
      } catch (err) {
        console.error("Manual Short Error:", err);
      } finally {
        btnManualShort.disabled = false;
        btnManualShort.textContent = prevText;
      }
    });
  }

  if (resumeTargetBtn) {
    resumeTargetBtn.addEventListener("click", async () => {
      resumeTargetBtn.disabled = true;
      resumeTargetBtn.textContent = "Resuming...";
      try {
        const res = await fetch("/api/reset_daily_target", { method: "POST" });
        const data = await res.json();
        if (data.success && data.account) {
          updateAccountUI(data.account);
          if (dailyTargetBanner) {
            dailyTargetBanner.style.display = "none";
            dailyTargetBanner.classList.add("hidden");
          }
        }
      } catch (err) {
        console.error("Resume error:", err);
      } finally {
        resumeTargetBtn.disabled = false;
        resumeTargetBtn.textContent = "Resume / Next Session";
      }
    });
  }

  async function closePosition(positionId, btn) {
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Securing...";
      btn.style.opacity = "0.7";
    }

    try {
      const res = await fetch("/api/close", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ position_id: positionId })
      });
      const data = await res.json();
      if (data.success) {
        playNotificationSound();
        if (data.account) {
          updateAccountKpis(data.account);
          renderDualSlots(data.account);
        }
        if (data.positions) renderPositionsTable(data.positions);
        if (data.history) renderHistoryTable(data.history);
      } else {
        alert(data.message || "Failed to close position");
        if (btn) {
          btn.disabled = false;
          btn.textContent = "Close";
          btn.style.opacity = "1";
        }
      }
    } catch (err) {
      console.error("Instant close error:", err);
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Close";
        btn.style.opacity = "1";
      }
    }
  }

  // Delegated click event listener for manual close / lock profit buttons
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-close-pos");
    if (btn) {
      const id = btn.getAttribute("data-id");
      if (id) {
        e.preventDefault();
        e.stopPropagation();
        closePosition(id, btn);
      }
    }
  });

  async function closeAllPositions() {
    if (!confirm("Are you sure you want to CLOSE ALL open dual-slot positions and bank profits?")) return;
    try {
      const res = await fetch("/api/close_all", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        playNotificationSound();
        if (data.account) {
          updateAccountKpis(data.account);
          renderDualSlots(data.account);
        }
        if (data.positions) renderPositionsTable(data.positions);
        if (data.history) renderHistoryTable(data.history);
      }
    } catch (err) {
      console.error("Close all error:", err);
    }
  }

  if (btnCloseAll) btnCloseAll.addEventListener("click", closeAllPositions);
  if (btnEmergencyCloseAll) btnEmergencyCloseAll.addEventListener("click", closeAllPositions);

  if (resetCircuitBtn) {
    resetCircuitBtn.addEventListener("click", async () => {
      await fetch("/api/reset_circuit", { method: "POST" });
      if (circuitAlertBanner) circuitAlertBanner.classList.add("hidden");
    });
  }

  if (toggleEma50) {
    toggleEma50.addEventListener("change", () => {
      if (ema50Series) ema50Series.applyOptions({ visible: toggleEma50.checked });
    });
  }

  if (toggleEma200) {
    toggleEma200.addEventListener("change", () => {
      if (ema200Series) ema200Series.applyOptions({ visible: toggleEma200.checked });
    });
  }

  if (resetZoomBtn) {
    resetZoomBtn.addEventListener("click", () => {
      if (chart) chart.timeScale().fitContent();
    });
  }

  // =========================================================================
  // 10. SETTINGS MODAL & BINANCE WALLET
  // =========================================================================
  async function loadSettingsData() {
    settingsModal.classList.remove("hidden");
    try {
      const res = await fetch("/api/exchange_config");
      const cfg = await res.json();
      if (cfg) {
        if (tradingModeSelect) tradingModeSelect.value = cfg.trading_mode || "SIMULATED_PAPER";
        if (modalExchangeBadge) modalExchangeBadge.textContent = (cfg.trading_mode || "SIMULATED_PAPER").replace(/_/g, " ");
        if (cfg.has_keys && binanceApiKeyInput) {
          binanceApiKeyInput.placeholder = `Active in System (${cfg.masked_key})`;
        }
        if (cfg.has_keys && binanceApiSecretInput) {
          binanceApiSecretInput.placeholder = "Active in System (••••••••••••••••)";
        }
        if (cfg.account) {
          if (pkrRateInput && cfg.account.pkr_rate) pkrRateInput.value = cfg.account.pkr_rate;
          if (dailyTargetPkrInput && cfg.account.daily_target_pkr_max) dailyTargetPkrInput.value = cfg.account.daily_target_pkr_max;
          if (maxRiskPctInput && cfg.account.risk_per_trade_pct) maxRiskPctInput.value = cfg.account.risk_per_trade_pct;
        }
        if (exchangeStatusMsg) {
          if (cfg.exchange_connected) {
            exchangeStatusMsg.textContent = `Online: Binance API Connected (${cfg.trading_mode})`;
            exchangeStatusMsg.style.color = "#34D399";
          } else {
            exchangeStatusMsg.textContent = "Gateway Standby";
            exchangeStatusMsg.style.color = "#94A3B8";
          }
        }
      }

      // Fetch live wallet balances breakdown
      const wRes = await fetch("/api/binance_wallet");
      const wData = await wRes.json();
      if (wData.success && wData.wallet_assets) {
        renderWalletAssetsModal(wData.wallet_assets, wData.live_usdt_balance);
      }
    } catch (e) {
      console.error("Settings load error:", e);
    }
  }

  if (openSettingsBtn) openSettingsBtn.addEventListener("click", loadSettingsData);
  if (walletBalanceChip) walletBalanceChip.addEventListener("click", loadSettingsData);

  if (closeModalBtn) closeModalBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
  if (cancelSettingsBtn) cancelSettingsBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
  if (settingsModal) {
    settingsModal.addEventListener("click", (e) => {
      if (e.target === settingsModal) settingsModal.classList.add("hidden");
    });
  }

  if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener("click", async () => {
      try {
        saveSettingsBtn.textContent = "Verifying & Saving...";
        saveSettingsBtn.disabled = true;
        if (modalStatusBanner) {
          modalStatusBanner.style.display = "none";
          modalStatusBanner.textContent = "";
        }

        const mode = tradingModeSelect ? tradingModeSelect.value : "SIMULATED_PAPER";
        const binanceKey = binanceApiKeyInput ? binanceApiKeyInput.value.trim() : "";
        const binanceSecret = binanceApiSecretInput ? binanceApiSecretInput.value.trim() : "";
        const pkrRate = pkrRateInput ? parseFloat(pkrRateInput.value) : 280;
        const dailyTarget = dailyTargetPkrInput ? parseFloat(dailyTargetPkrInput.value) : 3000;
        const riskPct = maxRiskPctInput ? parseFloat(maxRiskPctInput.value) : (riskSlider ? parseFloat(riskSlider.value) : 1.0);

        // 1. Save general risk & settings
        await fetch("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            auto_trade: autoTradeToggle ? autoTradeToggle.checked : true,
            risk_pct: riskPct,
            pkr_rate: pkrRate,
            daily_target_pkr: dailyTarget
          })
        });

        // 2. Save exchange configuration
        const res = await fetch("/api/exchange_config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            trading_mode: mode,
            binance_api_key: binanceKey,
            binance_api_secret: binanceSecret
          })
        });
        const data = await res.json();

        playNotificationSound();
        if (data.success) {
          syncModeButtons(data.trading_mode, data.account);
          if (modalExchangeBadge) modalExchangeBadge.textContent = (data.trading_mode || "SIMULATED_PAPER").replace(/_/g, " ");

          if (modalStatusBanner) {
            modalStatusBanner.style.display = "block";
            if (data.connected) {
              modalStatusBanner.style.background = "rgba(16, 185, 129, 0.15)";
              modalStatusBanner.style.border = "1px solid #10B981";
              modalStatusBanner.style.color = "#34D399";
              modalStatusBanner.innerHTML = `<strong>✓ Configuration Applied!</strong><br>${data.message}`;
              // Gracefully close modal after 1.5 seconds on verified connection
              setTimeout(() => {
                settingsModal.classList.add("hidden");
              }, 1500);
            } else {
              modalStatusBanner.style.background = "rgba(245, 158, 11, 0.15)";
              modalStatusBanner.style.border = "1px solid #F59E0B";
              modalStatusBanner.style.color = "#FCD34D";
              modalStatusBanner.innerHTML = `<strong>⚠️ Mode Saved: ${data.trading_mode}</strong><br>${data.message}`;
            }
          }

          // Fetch updated wallet balances
          const wRes = await fetch("/api/binance_wallet");
          const wData = await wRes.json();
          if (wData.success && wData.wallet_assets) {
            renderWalletAssetsModal(wData.wallet_assets, wData.live_usdt_balance);
          }
        }
      } catch (err) {
        console.error("Save settings error:", err);
        if (modalStatusBanner) {
          modalStatusBanner.style.display = "block";
          modalStatusBanner.style.background = "rgba(239, 68, 68, 0.15)";
          modalStatusBanner.style.border = "1px solid #EF4444";
          modalStatusBanner.style.color = "#FCA5A5";
          modalStatusBanner.innerHTML = `<strong>Failed to save settings:</strong> ${err.message}`;
        }
      } finally {
        saveSettingsBtn.textContent = "Save & Apply Configuration";
        saveSettingsBtn.disabled = false;
      }
    });
  }

  if (testExchangeBtn) {
    testExchangeBtn.addEventListener("click", async () => {
      testExchangeBtn.disabled = true;
      testExchangeBtn.textContent = "Pinging...";
      if (exchangeStatusMsg) {
        exchangeStatusMsg.textContent = "Pinging Binance REST gateway...";
        exchangeStatusMsg.style.color = "#94A3B8";
      }

      try {
        const mode = tradingModeSelect ? tradingModeSelect.value : "SIMULATED_PAPER";
        const res = await fetch("/api/exchange_config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            trading_mode: mode,
            binance_api_key: binanceApiKeyInput ? binanceApiKeyInput.value.trim() : "",
            binance_api_secret: binanceApiSecretInput ? binanceApiSecretInput.value.trim() : "",
            test_connection: true
          })
        });
        const data = await res.json();
        if (data.success && data.connected) {
          if (exchangeStatusMsg) {
            exchangeStatusMsg.textContent = `Online: ${data.message}`;
            exchangeStatusMsg.style.color = "#34D399";
          }
          if (data.account && data.account.wallet_assets) {
            renderWalletAssetsModal(data.account.wallet_assets, data.account.live_usdt_balance);
          }
        } else {
          if (exchangeStatusMsg) {
            exchangeStatusMsg.textContent = `Error: ${data.message}`;
            exchangeStatusMsg.style.color = "#F43F5E";
          }
        }
      } catch (err) {
        if (exchangeStatusMsg) {
          exchangeStatusMsg.textContent = "Connection failed";
          exchangeStatusMsg.style.color = "#F43F5E";
        }
      } finally {
        testExchangeBtn.disabled = false;
        testExchangeBtn.textContent = "Ping Binance API";
      }
    });
  }

  function playNotificationSound() {
    if (!isSoundEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, audioCtx.currentTime + 0.15);

      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);

      osc.connect(gain);
      gain.connect(audioCtx.destination);

      osc.start();
      osc.stop(audioCtx.currentTime + 0.35);
    } catch (e) {}
  }

  soundToggleBtn.addEventListener("click", () => {
    isSoundEnabled = !isSoundEnabled;
    soundToggleBtn.style.opacity = isSoundEnabled ? "1" : "0.5";
  });

  // =========================================================================
  // 11. BINANCE WALLET & REAL VS DEMO MODE INTEGRATION
  // =========================================================================
  function renderWalletAssetsModal(assets, liveUsdt) {
    const tableBody = document.getElementById("walletAssetsTableBody");
    const modalWalletTotal = document.getElementById("modalWalletTotal");
    const parsedUsdt = (liveUsdt !== undefined && liveUsdt !== null) ? parseFloat(liveUsdt) : 0.0;
    
    if (modalWalletTotal) {
      modalWalletTotal.textContent = `Free USDT: $${parsedUsdt.toFixed(2)}`;
    }
    if (headerWalletUsdt) {
      headerWalletUsdt.textContent = `$${parsedUsdt.toFixed(2)} USDT`;
    }
    if (!tableBody) return;
    if (!assets || assets.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="padding:12px;">No non-zero spot balances found on Binance.</td></tr>`;
      return;
    }
    tableBody.innerHTML = assets.map(a => {
      const free = parseFloat(a.free || 0);
      const locked = parseFloat(a.locked || 0);
      const total = free + locked;
      return `
        <tr>
          <td><span class="mono fw-bold text-primary">${a.asset}</span></td>
          <td class="mono ${free > 0 ? 'text-bull' : ''}">${free.toFixed(4)}</td>
          <td class="mono text-muted">${locked.toFixed(4)}</td>
          <td class="mono fw-bold">${total.toFixed(4)}</td>
        </tr>
      `;
    }).join("");
  }

  function syncModeButtons(mode, account) {
    const isReal = (mode === "BINANCE_LIVE" || mode === "REAL");
    if (btnSelectReal && btnSelectDemo) {
      if (isReal) {
        btnSelectReal.classList.add("active");
        btnSelectDemo.classList.remove("active");
      } else {
        btnSelectDemo.classList.add("active");
        btnSelectReal.classList.remove("active");
      }
    }
    if (modePill && modePillText) {
      if (isReal) {
        modePill.classList.remove("paper");
        modePill.classList.add("real");
        modePillText.textContent = "BINANCE LIVE";
      } else {
        modePill.classList.remove("real");
        modePill.classList.add("paper");
        modePillText.textContent = "DEMO SIMULATION";
      }
    }
    if (kpiModeBadge) {
      if (isReal) {
        kpiModeBadge.className = "kpi-badge real-badge";
        kpiModeBadge.textContent = "BINANCE LIVE";
      } else {
        kpiModeBadge.className = "kpi-badge demo-badge";
        kpiModeBadge.textContent = "DEMO PAPER";
      }
    }
    if (tradingModeSelect) {
      tradingModeSelect.value = isReal ? "BINANCE_LIVE" : "SIMULATED_PAPER";
    }
    if (account) {
      updateAccountKpis(account);
      if (account.live_usdt_balance !== undefined && headerWalletUsdt) {
        headerWalletUsdt.textContent = `$${parseFloat(account.live_usdt_balance).toFixed(2)} USDT`;
      }
    }
  }

  async function toggleTradingMode(targetMode) {
    try {
      const modeStr = (targetMode === "REAL" || targetMode === "BINANCE_LIVE") ? "REAL" : "DEMO";
      const res = await fetch("/api/toggle_mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: modeStr })
      });
      const data = await res.json();
      if (data && data.success) {
        syncModeButtons(data.trading_mode, data.account);
        playNotificationSound();
        fetchBinanceWallet();
      }
    } catch (err) {
      console.error("Failed to toggle trading mode:", err);
    }
  }

  async function fetchBinanceWallet() {
    try {
      const res = await fetch("/api/binance_wallet");
      const data = await res.json();
      if (data && (data.success || data.status === "online")) {
        const usdt = data.usdt_balance !== undefined ? data.usdt_balance : data.live_usdt_balance;
        if (headerWalletUsdt) {
          headerWalletUsdt.textContent = `$${parseFloat(usdt || 0).toFixed(2)} USDT`;
        }
        const assets = data.assets || data.wallet_assets || [];
        renderWalletAssetsModal(assets, usdt);
      }
    } catch (err) {
      console.error("Failed to fetch Binance wallet:", err);
    }
  }

  if (btnSelectDemo) {
    btnSelectDemo.addEventListener("click", () => toggleTradingMode("DEMO"));
  }
  if (btnSelectReal) {
    btnSelectReal.addEventListener("click", () => toggleTradingMode("REAL"));
  }
  if (modePill) {
    modePill.addEventListener("click", () => {
      const isCurrentlyReal = modePill.classList.contains("real");
      toggleTradingMode(isCurrentlyReal ? "DEMO" : "REAL");
    });
  }

  // Initial fetch of config and wallet balances
  fetch("/api/exchange_config")
    .then(r => r.json())
    .then(cfg => {
      if (cfg) syncModeButtons(cfg.trading_mode, null);
    })
    .catch(() => {});
  fetchBinanceWallet();

  // Initialize
  initChart();
  connectWebSocket();
});
