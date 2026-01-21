// js/portfolio.js
// Rendering of: KPIs, positions, trade history with Bloomberg-style color coding

import { byId } from "./ui.js";

/**
 * Apply color class based on P&L value
 * @param {number} value - The P&L value
 * @returns {string} - CSS class name
 */
function getPnLClass(value) {
  if (value > 0) return 'pnl-positive';
  if (value < 0) return 'pnl-negative';
  return 'pnl-neutral';
}

/**
 * Format P&L value with sign and color
 * @param {number} value - The P&L value
 * @returns {string} - Formatted string with sign
 */
function formatPnL(value) {
  return (value >= 0 ? '+' : '') + value.toFixed(2);
}

/**
 * Render the entire portfolio panel:
 * - Cash
 * - Equity
 * - uPnL (color-coded)
 * - rPnL (color-coded)
 * - Positions table (with P&L color coding)
 * - Trades table (with P&L color coding)
 *
 * @param {Object} p
 * @param {number} p.cash
 * @param {number} p.equity
 * @param {number} p.uPnL
 * @param {number} p.realizedPnL
 * @param {Array<Object>} [p.positions]
 * @param {Array<Object>} [p.trades]
 */
export function renderPortfolio(p) {
  if (!p) return;

  // --- KPI SECTION with color coding ---
  const cashEl = byId("k_cash");
  if (cashEl) {
    cashEl.textContent = p.cash.toFixed(2);
  }

  const equityEl = byId("k_equity");
  if (equityEl) {
    equityEl.textContent = p.equity.toFixed(2);
  }

  // Unrealized P&L with color
  const upnlEl = byId("k_upnl");
  if (upnlEl) {
    upnlEl.textContent = formatPnL(p.uPnL);
    upnlEl.className = 'kpi-value pnl-value ' + getPnLClass(p.uPnL);
  }

  // Realized P&L with color
  const rpnlEl = byId("k_rpnl");
  if (rpnlEl) {
    rpnlEl.textContent = formatPnL(p.realizedPnL);
    rpnlEl.className = 'kpi-value pnl-value ' + getPnLClass(p.realizedPnL);
  }

  // Sync to top bar in compact layout
  const cashTop = byId("k_cash_top");
  const equityTop = byId("k_equity_top");
  const pnlTop = byId("k_pnl_top");
  
  if (cashTop) cashTop.textContent = p.cash.toFixed(2);
  if (equityTop) equityTop.textContent = p.equity.toFixed(2);
  
  if (pnlTop) {
    const totalPnL = p.uPnL + p.realizedPnL;
    pnlTop.textContent = formatPnL(totalPnL);
    pnlTop.className = 'pnl-value ' + (totalPnL >= 0 ? 'positive' : 'negative');
  }

  // --- POSITIONS TABLE with P&L color coding ---
  const posTb = byId("pos_rows");
  if (!posTb) return;
  
  posTb.innerHTML = "";

  (p.positions || []).forEach((row) => {
    const tr = document.createElement("tr");
    
    // Calculate P&L percentage
    const pnlPct = ((row.price - row.avg) / row.avg) * 100;
    const pnlClass = getPnLClass(row.uPnL);

    tr.innerHTML = `
      <td><strong>${row.asset}</strong></td>
      <td>${row.qty}</td>
      <td>${row.avg.toFixed(2)}</td>
      <td>${row.price.toFixed(2)}</td>
      <td>${row.mktValue.toFixed(2)}</td>
      <td class="${pnlClass}">${formatPnL(row.uPnL)}</td>
      <td class="${pnlClass}">${formatPnL(pnlPct)}%</td>
    `;

    posTb.appendChild(tr);
  });

  // --- TRADES HISTORY TABLE with P&L color coding (COMPACT) ---
  const tradeTb = byId("trades_rows");
  if (!tradeTb) return;
  
  tradeTb.innerHTML = "";

  // Show most recent trades first, limit to 5 for compact layout
  (p.trades || []).slice().reverse().slice(0, 5).forEach((t) => {
    const ts = new Date(t.ts * 1000).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false 
    });
    const tr = document.createElement("tr");
    
    const realizedPnL = Number(t.realized_pnl);
    const pnlClass = getPnLClass(realizedPnL);

    // Color code the side (BUY=green, SELL=red for visual clarity)
    const sideClass = t.side_open === 'BUY' ? 'pnl-positive' : 'pnl-negative';

    // Compact display - fewer columns
    tr.innerHTML = `
      <td>${ts}</td>
      <td><strong>${t.asset}</strong></td>
      <td class="${sideClass}">${t.side_open}</td>
      <td>${t.qty}</td>
      <td class="${pnlClass}">${formatPnL(realizedPnL)}</td>
    `;

    tradeTb.appendChild(tr);
  });
}
