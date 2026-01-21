// ui.js
// Pure UI helpers: DOM access, status badges, lobby/game toggles, players list.

/**
 * Convenience helper to get an element by its ID.
 *
 * @param {string} id
 * @returns {HTMLElement|null}
 */
export function byId(id) {
  return document.getElementById(id);
}

/**
 * Logs a message to the on-screen log display.
 * Prepends each log entry with a timestamp.
 * Supports HTML for colored messages.
 *
 * @param {string} m - Message (can include HTML)
 */
export function log(m) {
  const el = byId("log");
  if (!el) return;
  
  const time = new Date().toLocaleTimeString();
  const logEntry = document.createElement("div");
  logEntry.className = "log-entry";
  logEntry.innerHTML = `<span style="color: #6b7280;">[${time}]</span> ${m}`;
  
  // Prepend to top
  el.insertBefore(logEntry, el.firstChild);
  
  // Keep only last 50 entries for performance
  while (el.children.length > 50) {
    el.removeChild(el.lastChild);
  }
}

/**
 * Updates the UI indicator showing the WebSocket connection status.
 *
 * @param {boolean} ok
 */
export function setWsStatus(ok) {
  const s = byId("wsStatus");
  if (!s) return;
  s.textContent = ok ? "connected" : "disconnected";
  s.className = "badge " + (ok ? "green" : "red");
}

/**
 * Shows or hides the lobby card section.
 *
 * @param {boolean} show
 */
export function showLobbyCard(show) {
  const el = byId("lobbyCard");
  if (!el) return;
  el.classList.toggle("hidden", !show);
  
  // Hide setup screen when showing lobby
  if (show) {
    const setup = byId("setupScreen");
    if (setup) setup.classList.add("hidden");
  }
}

/**
 * Shows or hides the main game area UI.
 *
 * @param {boolean} show
 */
export function showGameArea(show) {
  const el = byId("gameArea");
  if (!el) return;
  el.classList.toggle("hidden", !show);
  
  // Hide other screens when showing game area
  if (show) {
    const setup = byId("setupScreen");
    const lobby = byId("lobbyCard");
    if (setup) setup.classList.add("hidden");
    if (lobby) lobby.classList.add("hidden");
  }
}

/**
 * Hides the setup screen (after lobby creation)
 */
export function hideSetupScreen() {
  const el = byId("setupScreen");
  if (el) el.classList.add("hidden");
}

/**
 * Syncs KPI values to top bar for compact display
 */
export function syncTopBarKPIs() {
  const cash = byId("k_cash");
  const equity = byId("k_equity");
  const upnl = byId("k_upnl");
  const rpnl = byId("k_rpnl");
  
  const cashTop = byId("k_cash_top");
  const equityTop = byId("k_equity_top");
  const pnlTop = byId("k_pnl_top");
  
  if (cash && cashTop) cashTop.textContent = cash.textContent;
  if (equity && equityTop) equityTop.textContent = equity.textContent;
  
  if (upnl && rpnl && pnlTop) {
    const totalPnL = parseFloat(upnl.textContent.replace(/[^0-9.-]/g, '')) + 
                     parseFloat(rpnl.textContent.replace(/[^0-9.-]/g, ''));
    const pnlStr = (totalPnL >= 0 ? '+' : '') + totalPnL.toFixed(2);
    pnlTop.textContent = pnlStr;
    pnlTop.className = 'pnl-value ' + (totalPnL >= 0 ? 'positive' : 'negative');
  }
}

/**
 * Renders the list of players inside the lobby.
 *
 * @param {Array<{name: string, userId: string, ready: boolean}>} list
 */
export function renderPlayers(list) {
  const tb = byId("playersTbody");
  if (!tb) return;
  tb.innerHTML = "";

  (list || []).forEach((p) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${p.name}</td>
      <td class="muted">${p.userId}</td>
      <td>${p.ready ? "✅" : "❌"}</td>
    `;
    tb.appendChild(tr);
  });
}
