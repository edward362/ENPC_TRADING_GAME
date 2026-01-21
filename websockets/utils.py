# websockets/utils.py

from __future__ import annotations   # Allows forward references in type hints (avoids circular imports)

from typing import TYPE_CHECKING
from fastapi import WebSocket

# Imported only during type checking to avoid runtime circular dependencies
if TYPE_CHECKING:
    from domain.models import LobbyState

from state import ws_by_user   # Global mapping: user_id -> WebSocket connection


async def send_json_safe(ws: WebSocket, payload: dict):
  """
  Safely send a JSON payload to a WebSocket client.
  If the client disconnected or an error occurs, silently ignore it.
  """
  try:
    await ws.send_json(payload)   # Send JSON message to this WebSocket
  except Exception:
    pass                           # Avoid crashing due to disconnects


async def broadcast_lobby(lobby: LobbyState, payload: dict): #broadcasting = sending the same message to many users at once 
  """
  Send the same payload to every connected player in the lobby.
  Iterates through all players and looks up their WebSocket in ws_by_user.
  """
  for uid, pl in list(lobby.players.items()):   # Loop over players in lobby
    ws = ws_by_user.get(uid)                    # WebSocket for this user, if connected
    if ws:
      await send_json_safe(ws, payload)         # Send payload safely


def lobby_state_payload(lobby: LobbyState):
  """
  Build a JSON-serializable dictionary representing the current lobby state.
  This is what gets sent to clients to update their UI.
  """
  return {
      "type":
      "LOBBY_STATE",
      "lobbyId":
      lobby.lobby_id,
      "status":
      lobby.status,
      "hostId":
      lobby.host_id,
      "rules":
      lobby.rules,
      "players": [{
          "userId": uid,
          "name": pl.name,
          "ready": pl.ready
      } for uid, pl in lobby.players.items()],   # Serialize each player
      "seed":
      lobby.seed
  }
