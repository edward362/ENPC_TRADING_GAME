# websockets/ticker.py
# This module defines the game's real-time "ticker" loop, which:
# - Advances prices at each tick
# - Broadcasts price updates to every player
# - Sends portfolio updates
# - Detects game end condition
# - Runs asynchronously until the game ends

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

# Used only for type hints; avoids circular imports at runtime
if TYPE_CHECKING:
    from domain.models import LobbyState

from domain.pricing import step_prices                   # Function to update asset prices
from domain.portfolio import snapshot_portfolio, leaderboard
from websockets.utils import send_json_safe, broadcast_lobby
from state import ws_by_user                             # Map: userId -> WebSocket


# Main ticker coroutine for a single lobby.
# It runs continuously until the game ends.
async def lobby_ticker(lobby: LobbyState):
  # Tick duration in seconds (how often prices update)
  tick_s = lobby.rules["tickSeconds"]

  # Game start and end timestamps
  lobby.start_ts = time.time()
  lobby.end_ts = lobby.start_ts + lobby.rules["durationSec"]

  # Notify all players that the game has started
  await broadcast_lobby(lobby, {
      "type": "GAME_STARTED",
      "startTs": lobby.start_ts,
      "endTs": lobby.end_ts
  })

  try:
    # Main ticker loop: runs once per tick_s seconds
    while True:
      now = time.time()

      # --------------- Check if game should end ---------------
      if now >= lobby.end_ts:
        lobby.status = "ENDED"

        # Notify clients that the game is over
        await broadcast_lobby(lobby, {
            "type": "GAME_ENDED",
            "lobbyId": lobby.lobby_id
        })

        # Send final leaderboard
        await broadcast_lobby(lobby, leaderboard(lobby))
        break

      # --------------- Update prices for this tick ---------------
      step_prices(lobby)   # Apply price movement algorithm

      # Broadcast TICK update to all players:
      # includes timestamps, current prices, and remaining time
      await broadcast_lobby(
          lobby, {
              "type": "TICK",
              "ts": now,
              "prices": lobby.prices,
              "remainingSec": int(lobby.end_ts - now)
          })

      # --------------- Send individual portfolio snapshots ---------------
      for uid, pl in lobby.players.items():
        ws = ws_by_user.get(uid)    # Player's WebSocket if connected
        if ws:
          await send_json_safe(ws, snapshot_portfolio(lobby, pl))

      # Also broadcast full-room leaderboard after updating portfolios
      await broadcast_lobby(lobby, leaderboard(lobby))

      # --------------- Wait until the next tick ---------------
      await asyncio.sleep(tick_s)

  finally:
    # Ticker has stopped; clear the task handle for cleanup
    lobby.ticker_task = None
