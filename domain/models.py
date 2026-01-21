# domain/models.py
from __future__ import annotations

import asyncio
import random
from typing import Dict, Optional

# central game constants live in config.py
from config import (
    ASSETS,
    DEFAULT_STARTING_CASH,
    DEFAULT_TICK_SECONDS,
    DEFAULT_DURATION_SEC,
)


class PlayerState:
    """
    Represents the full trading state of a single player connected to the game.
    
    This object tracks all important aspects of a player's account:
    - identity (user_id, name)
    - readiness state (e.g. whether they've clicked "Ready" in a lobby)
    - available cash
    - open positions per asset
    - realized profit and loss (PnL)
    - closed trade history

    It acts as the in-memory equivalent of a trading account, updated in real time
    as orders are executed, positions are opened/closed, and PnL is generated.

    Parameters
    ----------
    user_id : str
        Unique identifier for this player (WebSocket session ID, UUID, etc.).
    
    name : str
        Display name of the player, used for UI and lobby representation.

    starting_cash : float
        Initial cash balance assigned to the player at the start of the session.
        This is the maximum amount they can allocate to open positions.

    Attributes
    ----------
    user_id : str
        The unique ID identifying the player inside the game.

    name : str
        Player’s name (for scoreboard, UI display, chat, etc.).

    ready : bool
        Whether the player has indicated they are ready (e.g., in a game lobby).
        Defaults to False until explicitly set by game logic.

    cash : float
        Current available cash in the player’s account.
        This is reduced when opening positions and increased when positions close.

    positions : Dict[str, Dict]
        A dictionary mapping each tradable asset symbol to its position state.
        The structure is:
        
        positions[asset] = {
            "qty": int,
                Current net quantity (positive = long, negative = short).
            
            "avg": float,
                Volume-weighted average entry price for the open position.
                If qty = 0, avg = 0.0 by convention.
            
            "entry_ts": Optional[float]
                Timestamp of when the position was first opened.
                Useful for later analytics or enforcing holding time rules.
        }
        
        All assets start with zero quantity, zero average price, and no timestamp.

    realized_pnl : float
        Cumulative profit or loss from all closed trades.
        Updated whenever a position is closed or partially closed.

    trades : list
        A history of all fully-closed trades.
        Each element is typically a dict containing:
        - asset symbol
        - entry price
        - exit price
        - quantity
        - realized pnl
        - timestamps
        
        This structure is useful for UI display, analytics, or post-game summaries.

    Notes
    -----
    This class stores **only** the player's state — it does not perform execution
    logic itself. Execution and PnL updates are handled elsewhere, typically inside
    `domain.execution` and written back into the `PlayerState` instance.

    This keeps the architecture clean: PlayerState = storage, Execution = logic.
    """
    def __init__(self, user_id: str, name: str, starting_cash: float):
        self.user_id = user_id
        self.name = name
        self.ready = False
        self.cash = float(starting_cash)
        # positions[a] = {"qty": int, "avg": float, "entry_ts": Optional[float]}
        self.positions: Dict[str, Dict] = {
            a: {"qty": 0, "avg": 0.0, "entry_ts": None} for a in ASSETS
        }
        self.realized_pnl: float = 0.0
        self.trades: list = []  # closed trades


class LobbyState:
    """
    Represents the full server-side state of a trading lobby (game room).

    A LobbyState controls:
    - which players are inside the lobby,
    - the rules of the match (starting capital, tick speed, duration),
    - the market simulation parameters,
    - the current lifecycle state of the lobby (LOBBY → RUNNING → ENDED),
    - the real-time price engine used during the session,
    - the WebSocket ticker task that drives continuous price updates.

    This class is essentially the “game instance”: each lobby runs an independent
    trading simulation with its own random number generator, price paths, players,
    rules, and timing. The WebSocket handler uses this object to coordinate all
    actions inside the lobby.

    Parameters
    ----------
    lobby_id : str
        Unique identifier for this lobby. Created when a new game room is made.
        Used to route WebSocket connections to the correct lobby instance.

    host_id : str
        The user ID of the player who created the lobby. This player typically
        has permission to start the game and modify lobby rules.

    rules : dict
        A dictionary containing user-specified lobby settings. Missing fields
        are automatically filled using default configuration constants.

        Expected keys:
        - "startingCapital": initial cash allocated to each player
        - "tickSeconds": number of seconds between price updates
        - "durationSec": total duration of the match in seconds

    Attributes
    ----------
    lobby_id : str
        Unique ID assigned to this lobby instance.

    host_id : str
        The ID of the player who created the lobby.

    status : str
        Represents the lifecycle state of the lobby.
        Possible values:
        - "LOBBY"   : players can join, adjust rules, ready up
        - "RUNNING" : trading session is active, ticker is broadcasting prices
        - "ENDED"   : trading session is finished, PnL cannot change anymore

    rules : dict
        Dictionary storing all gameplay parameters. After initialization,
        it is guaranteed to contain:

        {
            "startingCapital": float,
            "tickSeconds": int,
            "durationSec": int
        }

        These rules are used when creating PlayerState objects and scheduling
        the real-time price ticker.

    seed : int
        Random seed used to create the RNG for deterministic market simulation.
        Using a fixed seed allows the same lobby to replay identical price paths
        for debugging or replays.

    rng : random.Random
        A dedicated random number generator instance for this lobby. Ensures
        that price updates are independent across different lobbies.

    prices : Dict[str, float]
        A dictionary mapping each asset symbol to its current simulated price.
        Initialized at 100.0 for each asset. Updated continuously by the ticker.

    players : Dict[str, PlayerState]
        Mapping from user_id → PlayerState object.
        Represents every player currently inside the lobby.
        PlayerState instances track cash, positions, trades, and PnL.

    start_ts : Optional[float]
        UNIX timestamp marking when the trading session officially begins.
        Set when the host starts the game.

    end_ts : Optional[float]
        UNIX timestamp marking when the session is scheduled to end.
        Calculated from start_ts + durationSec.

    ticker_task : Optional[asyncio.Task]
        A background asyncio Task responsible for broadcasting price updates
        at fixed intervals (tickSeconds). This task is created by the WebSocket
        handler once the game transitions from LOBBY → RUNNING.

        If the lobby ends or all players disconnect, this task must be cancelled
        to avoid orphaned background operations.

    Notes
    -----
    - LobbyState does **not** directly send data to clients. Instead, the
      WebSocket handler reads/modifies this object and handles communication.
    
    - All real-time price generation happens outside LobbyState, typically inside
      a ticker loop that updates `self.prices` and writes results to each
      player's WebSocket connection.

    - Because multiple players share a single lobby, LobbyState is the canonical
      source of truth for the trading session: price data, timing, and players
      all live inside this object.

    - The async ticker task depends on an asyncio event loop. It is created,
      awaited, and cancelled from within the WebSocket connection logic.
    """
    
    def __init__(self, lobby_id: str, host_id: str, rules: dict):
        self.lobby_id = lobby_id
        self.host_id = host_id
        self.status = "LOBBY"  # LOBBY | RUNNING | ENDED
        self.rules = {
            "startingCapital": float(rules.get("startingCapital", DEFAULT_STARTING_CASH)),
            "tickSeconds": int(rules.get("tickSeconds", DEFAULT_TICK_SECONDS)),
            "durationSec": int(rules.get("durationSec", DEFAULT_DURATION_SEC)),
        }
        # market
        self.seed = random.randint(1, 10_000)
        self.rng = random.Random(self.seed)
        self.prices = {a: 100.0 for a in ASSETS}
        # players
        self.players: Dict[str, PlayerState] = {}  # userId -> PlayerState
        # timing
        self.start_ts: Optional[float] = None
        self.end_ts: Optional[float] = None
        # async ticker task (created by WS handler)
        self.ticker_task: Optional[asyncio.Task] = None
