# websockets/endpoints.py
# This module defines the main WebSocket endpoint and all the message handling
# logic for the trading game (creating/joining lobbies, starting games, orders, etc.).

from __future__ import annotations

import asyncio
import time
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect, Query

from config import ASSETS
from domain.models import LobbyState, PlayerState
from domain.execution import execute_market
from domain.portfolio import snapshot_portfolio, leaderboard
from websockets.utils import send_json_safe, broadcast_lobby, lobby_state_payload
from websockets.ticker import lobby_ticker
from state import (
    clients,
    user_by_ws,
    ws_by_user,
    lobbies,
    lobby_by_user,
    gen_user_id,
    gen_lobby_id,
)


# Main WebSocket endpoint: one connection per browser/client.
# Optionally restores a userId if the client reconnects with ?userId=...
async def ws_endpoint(ws: WebSocket,
                      userId: Optional[str] = Query(default=None)):
  await ws.accept()          # Accept the WebSocket connection (handshake done)
  clients.add(ws)            # Track this WebSocket in the global set of clients

  # assign / restore userId
  uid = userId if userId else gen_user_id()  # Reuse provided userId or generate a new one
  user_by_ws[ws] = uid                       # Map WebSocket -> userId
  ws_by_user[uid] = ws                       # Map userId  -> WebSocket

  # greet
  await send_json_safe(ws, {"type": "HELLO", "userId": uid})  # Initial hello message to client

  try:
    # Main receive loop: handle messages from this client until disconnect/error
    while True:
      msg = await ws.receive_json()   # Receive JSON message from client
      mtype = msg.get("type")         # Message type (CREATE_LOBBY, ORDER, PING, etc.)

      # ---------------------- CREATE_LOBBY ----------------------
      if mtype == "CREATE_LOBBY":
        # Determine player name and lobby rules (with defaults)
        name = msg.get("name") or f"User-{uid[:4]}"
        rules = msg.get("rules") or {}
        lobby_id = gen_lobby_id()  # Unique lobby ID
        lobby = LobbyState(lobby_id, host_id=uid, rules=rules)
        lobbies[lobby_id] = lobby  # Register lobby globally

        # ensure player object
        if uid not in lobby.players:
          lobby.players[uid] = PlayerState(uid, name,
                                           lobby.rules["startingCapital"])
        lobby.players[uid].ready = False
        lobby_by_user[uid] = lobby_id  # Remember which lobby this user is in

        # FIX: build invite URL using ws.url.scheme and headers['host']
        scheme = getattr(ws.url, "scheme", "ws")  # 'ws' or 'wss'
        http_scheme = "https" if scheme == "wss" else "http"
        host = ws.headers.get("host", "")
        invite_url = f"{http_scheme}://{host}/?join={lobby_id}"

        # Send invite info back to the host and broadcast lobby state to all players
        await send_json_safe(ws, {
            "type": "INVITE_CODE",
            "lobbyId": lobby_id,
            "inviteUrl": invite_url,
        })
        await broadcast_lobby(lobby, lobby_state_payload(lobby))

      # ---------------------- JOIN_LOBBY ----------------------
      elif mtype == "JOIN_LOBBY":
        lobby_id = (msg.get("lobbyId") or "").upper()  # Normalize ID
        name = msg.get("name") or f"User-{uid[:4]}"
        lobby = lobbies.get(lobby_id)
        if not lobby:
          # Lobby does not exist
          await send_json_safe(ws, {
              "type": "ERROR",
              "code": "lobby_not_found"
          })
          continue
        if lobby.status != "LOBBY":
          # Lobby already running or closed, can't join
          await send_json_safe(ws, {
              "type": "ERROR",
              "code": "lobby_not_joinable"
          })
          continue

        # Ensure player object in this lobby
        if uid not in lobby.players:
          lobby.players[uid] = PlayerState(uid, name,
                                           lobby.rules["startingCapital"])
        else:
          lobby.players[uid].name = name
        lobby.players[uid].ready = False
        lobby_by_user[uid] = lobby_id

        # Broadcast updated lobby state (new player joined)
        await broadcast_lobby(lobby, lobby_state_payload(lobby))

      # ---------------------- SET_READY ----------------------
      elif mtype == "SET_READY":
        # Find which lobby this user belongs to
        lobby_id = lobby_by_user.get(uid)
        if not lobby_id: continue
        lobby = lobbies.get(lobby_id)
        if not lobby or lobby.status != "LOBBY": continue
        # Update ready flag
        ready = bool(msg.get("ready", False))
        pl = lobby.players.get(uid)
        if pl:
          pl.ready = ready
          # Notify all players of updated ready states
          await broadcast_lobby(lobby, lobby_state_payload(lobby))

      # ---------------------- START_GAME ----------------------
      elif mtype == "START_GAME":
        lobby_id = lobby_by_user.get(uid)
        if not lobby_id: continue
        lobby = lobbies.get(lobby_id)
        if not lobby or lobby.status != "LOBBY": continue
        # Only the host can start the game
        if uid != lobby.host_id:
          await send_json_safe(ws, {"type": "ERROR", "code": "not_host"})
          continue
        # require everyone ready
        if not lobby.players or not all(p.ready
                                        for p in lobby.players.values()):
          await send_json_safe(ws, {
              "type": "ERROR",
              "code": "players_not_ready"
          })
          continue
        # Transition lobby to RUNNING state and start ticker task
        lobby.status = "RUNNING"
        await broadcast_lobby(lobby, lobby_state_payload(lobby))
        if not lobby.ticker_task:
          lobby.ticker_task = asyncio.create_task(lobby_ticker(lobby))

      # ---------------------- ORDER ----------------------
      elif mtype == "ORDER":
        lobby_id = lobby_by_user.get(uid)
        if not lobby_id: continue
        lobby = lobbies.get(lobby_id)
        if not lobby or lobby.status != "RUNNING": continue
        # Extract order params
        asset = msg.get("asset")
        side = msg.get("side")
        qty = int(msg.get("qty", 0) or 0)
        # Basic validation of input
        if asset not in ASSETS or side not in ("BUY", "SELL") or qty <= 0:
          await send_json_safe(ws, {
              "type": "ORDER_REJECT",
              "reason": "invalid"
          })
          continue
        pl = lobby.players.get(uid)
        if not pl:
          await send_json_safe(ws, {
              "type": "ORDER_REJECT",
              "reason": "player_not_found"
          })
          continue
        # Execute market order using domain logic
        ok, reason = execute_market(lobby, pl, asset, side, qty)
        if ok:
          # Acknowledge accepted order and send updated portfolio + leaderboard
          await send_json_safe(
              ws, {
                  "type": "ORDER_ACCEPTED",
                  "asset": asset,
                  "side": side,
                  "qty": qty,
                  "price": round(lobby.prices[asset], 2)
              })
          await send_json_safe(ws, snapshot_portfolio(lobby, pl))
          await broadcast_lobby(lobby, leaderboard(lobby))
        else:
          # Order rejected with reason
          await send_json_safe(ws, {
              "type": "ORDER_REJECT",
              "reason": reason or "unknown"
          })

      # ---------------------- LEAVE_LOBBY ----------------------
      elif mtype == "LEAVE_LOBBY":
        lobby_id = lobby_by_user.get(uid)
        if not lobby_id: continue
        lobby = lobbies.get(lobby_id)
        if not lobby: continue
        # Remove player from lobby and update mapping
        lobby.players.pop(uid, None)
        lobby_by_user.pop(uid, None)
        # Broadcast new lobby state to remaining players
        await broadcast_lobby(lobby, lobby_state_payload(lobby))

      # ---------------------- PING / PONG ----------------------
      elif mtype == "PING":
        # Latency/health check: respond with PONG and current timestamp
        await send_json_safe(ws, {"type": "PONG", "ts": time.time()})

      else:
        # ignore unknown
        pass

  except WebSocketDisconnect:
    # Client closed the connection gracefully
    pass
  except Exception:
    # Any other unexpected error in this handler
    pass
  finally:
    # cleanup maps
    clients.discard(ws)                   # Remove from global clients set
    uid = user_by_ws.pop(ws, None)        # Remove WebSocket -> userId mapping
    if uid and ws_by_user.get(uid) is ws:
      ws_by_user.pop(uid, None)           # Remove userId -> WebSocket mapping if same ws
    # we keep the player in the lobby for reconnection (by userId)
