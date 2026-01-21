// js/leaderboard.js
// Rendering the leaderboard modal with Bloomberg-style design

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
 * Format P&L value with sign
 * @param {number} value - The P&L value
 * @returns {string} - Formatted string with sign
 */
function formatPnL(value) {
  return (value >= 0 ? '+' : '') + value.toFixed(2);
}

/**
 * Shows the leaderboard modal
 */
export function showLeaderboard() {
  const modal = byId("leaderboardModal");
  if (modal) {
    modal.classList.remove("hidden");
  }
}

/**
 * Hides the leaderboard modal
 */
export function hideLeaderboard() {
  const modal = byId("leaderboardModal");
  if (modal) {
    modal.classList.add("hidden");
  }
}

/**
 * Toggles the leaderboard modal visibility
 */
export function toggleLeaderboard() {
  const modal = byId("leaderboardModal");
  if (modal) {
    modal.classList.toggle("hidden");
  }
}

/**
 * Renders the leaderboard table with rankings and color-coded performance
 *
 * @param {Object} lb - Leaderboard object from backend
 * @param {Array<{name:string, equity:number, realizedPnL:number}>} lb.rows
 */
export function renderLeaderboard(lb) {
  const tb = byId("lb_rows");
  if (!tb) return;
  
  tb.innerHTML = "";

  (lb.rows || []).forEach((r, index) => {
    const tr = document.createElement("tr");
    
    // Calculate performance percentage (assuming starting capital from equity + realized)
    const totalPnL = r.realizedPnL;
    const performance = totalPnL;
    
    const pnlClass = getPnLClass(r.realizedPnL);
    const perfClass = getPnLClass(performance);
    
    // Add medal emoji for top 3
    let rankDisplay = (index + 1).toString();
    if (index === 0) rankDisplay = '🥇 1';
    else if (index === 1) rankDisplay = '🥈 2';
    else if (index === 2) rankDisplay = '🥉 3';

    tr.innerHTML = `
      <td><strong>${rankDisplay}</strong></td>
      <td><strong>${r.name}</strong></td>
      <td>${r.equity.toFixed(2)}</td>
      <td class="${pnlClass}">${formatPnL(r.realizedPnL)}</td>
      <td class="${perfClass}"><strong>${formatPnL(performance)}</strong></td>
    `;

    // Highlight top 3 with subtle background
    if (index < 3) {
      tr.style.background = 'rgba(255, 149, 0, 0.1)';
    }

    tb.appendChild(tr);
  });
}
