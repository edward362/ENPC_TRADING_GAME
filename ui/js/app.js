// js/app.js
// Entry point: wires DOM elements to the game logic modules.

import { byId } from "./ui.js";
import { connectWS, createLobby, joinLobby, setReady, startGame } from "./ws.js";
import { updateChartAsset } from "./chart.js";
import { toggleLeaderboard, hideLeaderboard } from "./leaderboard.js";
import { initTicker } from "./ticker.js";

window.addEventListener("DOMContentLoaded", () => {
  console.log("Bloomberg Terminal: Initializing...");

  // Helper to bind clicks and log
  function bindClick(elem, label, handler) {
    if (!elem) {
      console.warn(`⚠️ Element for '${label}' not found`);
      return;
    }
    elem.addEventListener("click", (e) => {
      e.preventDefault();
      console.log(`▶ '${label}' clicked`);
      handler();
    });
    console.log(`✔ Bound '${label}'`);
  }

  // --- Setup Screen Controls ---

  // Connect
  const btnConnect = byId("btnConnect");
  bindClick(btnConnect, "Connect", connectWS);

  // Create Lobby
  const btnCreate = byId("btnCreate");
  bindClick(btnCreate, "Create Lobby", createLobby);

  // Join Lobby
  const btnJoin = byId("btnJoin");
  bindClick(btnJoin, "Join Lobby", joinLobby);

  // Ready checkbox
  const readyChk = byId("readyChk");
  if (readyChk) {
    readyChk.addEventListener("change", () => {
      console.log("▶ 'Ready' checkbox changed");
      setReady();
    });
    console.log("✔ Bound 'Ready checkbox'");
  } else {
    console.warn("⚠️ 'readyChk' not found");
  }

  // Start Game
  const btnStart = byId("btnStart");
  bindClick(btnStart, "Start Game", () => {
    startGame();
    // Initialize ticker when game starts
    setTimeout(() => initTicker(), 1000);
  });

  // --- Main Terminal Controls ---

  // Asset selector updates the chart
  const assetSel = byId("assetSel");
  if (assetSel) {
    assetSel.addEventListener("change", () => {
      console.log("▶ Asset changed to", assetSel.value);
      updateChartAsset(assetSel.value);
    });
    console.log("✔ Bound 'assetSel' change");
  } else {
    console.warn("⚠️ 'assetSel' not found");
  }

  // Leaderboard button
  const btnLeaderboard = byId("btnLeaderboard");
  bindClick(btnLeaderboard, "Toggle Leaderboard", toggleLeaderboard);

  // Close leaderboard button
  const btnCloseLeaderboard = byId("btnCloseLeaderboard");
  bindClick(btnCloseLeaderboard, "Close Leaderboard", hideLeaderboard);

  // Close leaderboard when clicking overlay
  const leaderboardModal = byId("leaderboardModal");
  if (leaderboardModal) {
    leaderboardModal.addEventListener("click", (e) => {
      // Only close if clicking the overlay itself, not the content
      if (e.target === leaderboardModal || e.target.classList.contains('modal-overlay')) {
        hideLeaderboard();
      }
    });
  }

  // --- Keyboard Shortcuts (Bloomberg-style) ---
  document.addEventListener("keydown", (e) => {
    // Ignore if typing in an input field
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
      return;
    }

    switch (e.key.toLowerCase()) {
      case 'l':
        // Toggle leaderboard
        e.preventDefault();
        toggleLeaderboard();
        console.log("⌨ Keyboard: Toggled leaderboard");
        break;

      case 'escape':
        // Close leaderboard
        hideLeaderboard();
        break;

      case '1':
      case '2':
      case '3':
      case '4':
      case '5':
        // Quick switch chart asset (1-5)
        e.preventDefault();
        const assets = ['OIL', 'GOLD', 'ELECTRONICS', 'RICE', 'PLUMBER'];
        const assetIndex = parseInt(e.key) - 1;
        if (assetIndex >= 0 && assetIndex < assets.length) {
          const asset = assets[assetIndex];
          if (assetSel) {
            assetSel.value = asset;
            updateChartAsset(asset);
            console.log(`⌨ Keyboard: Switched to ${asset}`);
          }
        }
        break;

      case 'h':
        // Show help tooltip
        e.preventDefault();
        showKeyboardHelp();
        break;
    }
  });

  // --- Parse ?join=CODE from URL to prefill join input ---
  const url = new URL(window.location.href);
  const j = url.searchParams.get("join");
  if (j) {
    const joinInput = byId("joinCode");
    if (joinInput) {
      joinInput.value = j;
      console.log("Prefilled joinCode from URL:", j);
    }
  }

  console.log("Bloomberg Terminal: Ready");
  console.log("Keyboard shortcuts: [L] Leaderboard | [1-5] Switch Asset | [ESC] Close | [H] Help");
});

/**
 * Show keyboard shortcuts help
 */
function showKeyboardHelp() {
  const helpText = `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BLOOMBERG TERMINAL SHORTCUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[L]     Toggle Leaderboard
[1-5]   Quick Switch Asset
[ESC]   Close Modal
[H]     Show This Help

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  `;
  
  console.log(helpText);
  
  // Could also show in UI as a toast/notification
  const modal = byId("leaderboardModal");
  if (modal && !modal.classList.contains("hidden")) {
    // If leaderboard is open, just log to console
    return;
  }
  
  // Show brief notification
  showNotification("Press [L] for Leaderboard | [1-5] to switch assets | [H] for help", "info");
}

/**
 * Show a temporary notification
 * @param {string} message 
 * @param {string} type - 'info', 'success', 'error'
 */
function showNotification(message, type = "info") {
  // Create notification element
  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    background: #0f1419;
    border: 1px solid #ff9500;
    color: #e8eaed;
    padding: 12px 20px;
    border-radius: 4px;
    font-family: 'Consolas', monospace;
    font-size: 12px;
    z-index: 10000;
    animation: slideInRight 0.3s ease-out;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  `;
  
  document.body.appendChild(notification);
  
  // Auto-remove after 3 seconds
  setTimeout(() => {
    notification.style.animation = "slideOutRight 0.3s ease-in";
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 3000);
}
