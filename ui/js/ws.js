// js/ws.js
// Handles WebSocket connection & routes server messages to the UI modules.

/* -------------------- Imports -------------------- */

import {
  byId,
  log,
  setWsStatus,
  showLobbyCard,
  showGameArea,
  renderPlayers,
} from "./ui.js";

import { initMarket, updatePrices } from "./market.js";
import { renderPortfolio } from "./portfolio.js";
import { renderLeaderboard } from "./leaderboard.js";
import { initChart, pushTickToHistory } from "./chart.js";
import { DEFAULTS } from "./constants.js";

/* -------------------- State -------------------- */

let ws = null;
let userId = null;
let lobbyId = null;
let isHost = false;

const WS_BASE_URL = window.location.origin.replace(/^http/, "ws") + "/ws";

/* -------------------- Helpers -------------------- */

function ensureConnected() {
  return ws && ws.readyState === WebSocket.OPEN;
}

function handleOrder({ asset, qty, side }) {
  if (!ensureConnected()) {
    log("Not connected.");
    return;
  }
  if (!qty || qty <= 0) {
    log("Enter a positive quantity.");
    return;
  }

  ws.send(
    JSON.stringify({
      type: "ORDER",
      asset,
      side,
      qty,
    })
  );
}

/* -------------------- Public API (used by app.js) -------------------- */

export function connectWS() {
  if (ensureConnected()) return;

  const qs = userId ? `?userId=${encodeURIComponent(userId)}` : "";
  const url = `${WS_BASE_URL}${qs}`;
  console.log("ws.js: Connecting WebSocket to:", url);

  ws = new WebSocket(url);

  ws.onopen = () => {
    setWsStatus(true);
    log("WebSocket connected");
  };

  ws.onclose = () => {
    setWsStatus(false);
    log("WebSocket disconnected");
  };

  ws.onerror = (err) => {
    setWsStatus(false);
    console.error("WebSocket error:", err);
    log("WebSocket error (see console).");
  };

  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);

    switch (msg.type) {
      case "HELLO":
        userId = msg.userId;
        byId("userIdBox").textContent = `userId: ${userId}`;
        break;

      case "INVITE_CODE":
        lobbyId = msg.lobbyId;
        byId("inviteBox").textContent = `Invite code: ${lobbyId}`;
        break;

      case "LOBBY_STATE":
        showLobbyCard(true);
        lobbyId = msg.lobbyId;
        byId("lobbyIdTxt").textContent = msg.lobbyId;
        byId("lobbyStatus").textContent = msg.status;
        byId("hostIdTxt").textContent = msg.hostId;
        
        // Update compact lobby info
        byId("inviteBox").textContent = msg.lobbyId;

        byId("ruleCap").textContent =
          msg.rules.startingCapital ?? msg.rules["startingCapital"];
        byId("ruleTick").textContent =
          msg.rules.tickSeconds ?? msg.rules["tickSeconds"];
        byId("ruleDur").textContent =
          msg.rules.durationSec ?? msg.rules["durationSec"];

        renderPlayers(msg.players);

        isHost = userId === msg.hostId;
        byId("btnStart").disabled = !(isHost && msg.status === "LOBBY");
        break;

      case "GAME_STARTED":
        // Hide all other screens and show only game area
        showGameArea(true);
        
        const lobbyStatus = byId("lobbyStatus");
        if (lobbyStatus) lobbyStatus.textContent = "RUNNING";

        initChart();
        initMarket(handleOrder);
        
        console.log("✓ Game started - trading interface active");
        break;

      case "GAME_ENDED":
        byId("lobbyStatus").textContent = "ENDED";
        log("Game ended.");
        break;

      case "TICK":
        updatePrices(msg.prices);
        byId("timeLeft").textContent = msg.remainingSec ?? "-";
        pushTickToHistory(msg.prices);
        break;

      case "PORTFOLIO":
        renderPortfolio(msg);
        break;

      case "LEADERBOARD":
        renderLeaderboard(msg);
        break;

      case "ORDER_ACCEPTED":
        log(
          `<span class="log-entry success">✓ ORDER ACCEPTED: ${msg.side} ${msg.asset} x${msg.qty} @ ${msg.price}</span>`
        );
        break;

      case "ORDER_REJECT":
        log(`<span class="log-entry error">✗ ORDER REJECTED: ${msg.reason}</span>`);
        break;

      default:
        // log("Unknown WS message: " + msg.type);
        break;
    }
  };
}

export function createLobby() {
  if (!ensureConnected()) {
    log("Not connected (cannot create lobby).");
    return;
  }

  const name = byId("name").value || "";
  ws.send(
    JSON.stringify({
      type: "CREATE_LOBBY",
      name,
      rules: {
        startingCapital: DEFAULTS.startingCapital,
        tickSeconds: DEFAULTS.tickSeconds,
        durationSec: DEFAULTS.durationSec,
      },
    })
  );
}

export function joinLobby() {
  if (!ensureConnected()) {
    log("Not connected (cannot join lobby).");
    return;
  }

  const name = byId("name").value || "";
  const code = (byId("joinCode").value || "").toUpperCase();

  if (!code) {
    alert("Enter a lobby code.");
    return;
  }

  ws.send(
    JSON.stringify({
      type: "JOIN_LOBBY",
      lobbyId: code,
      name,
    })
  );
}

export function setReady() {
  if (!ensureConnected()) {
    log("Not connected (cannot set ready).");
    return;
  }

  ws.send(
    JSON.stringify({
      type: "SET_READY",
      ready: byId("readyChk").checked,
    })
  );
}

export function startGame() {
  if (!ensureConnected()) {
    log("Not connected (cannot start game).");
    return;
  }
  if (!isHost) {
    log("Only the host can start the game.");
    return;
  }

  ws.send(JSON.stringify({ type: "START_GAME" }));
}
