# domain/pricing.py
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from config import ASSETS, PRICE_TICK

if TYPE_CHECKING:
    from domain.models import LobbyState


def round_tick(x: float, tick: float = PRICE_TICK) -> float:
  """
    Rounds a price to the nearest valid tick size imposed by the market.

    Many markets (futures, FX, equities) restrict prices to discrete increments
    called tick sizes. This helper function ensures that any computed or simulated
    price is snapped to the closest valid tick multiple.

    Parameters
    ----------
    x : float
        The input price to be rounded.

    tick : float, optional
        The minimum price increment allowed by the market.
        Defaults to PRICE_TICK, a global configuration constant.

    Returns
    -------
    float
        The price rounded to the nearest tick, with a minimum value of `tick`.

        Formally:
            round(x / tick) * tick
        but never less than `tick`.

    Notes
    -----
    - The `max(tick, ...)` guard ensures that the returned price is never zero
      or negative, which can happen in simulations if random noise pushes the
      model too low.
      
    - This function is typically used by the price simulation engine to keep
      prices realistic and exchange-compliant.

    Examples
    --------
    If tick = 0.5:

    Input:  x = 10.23  
    Output: 10.0   (rounded to nearest 0.5)

    Input:  x = 0.12  
    Output: 0.5    (minimum tick enforced)
  """
  return max(tick, round(x / tick) * tick)


def step_prices(lobby: LobbyState):
  """
    Advances the simulated market prices of all assets by one time step.

    This function applies a simple stochastic price model combining:
    - a deterministic drift component (trend),
    - a random Gaussian shock (volatility),
    - asset-specific parameters (different drift and sigma per asset),
    - and rounding to the market tick size.

    It updates `lobby.prices` in place and is intended to be called repeatedly
    by the real-time ticker task (e.g. every tickSeconds).

    Model Description
    -----------------
    For each asset a:
        p_t     = current price
        drift   = asset-specific drift rate (annualized-style simplified)
        sigma   = asset-specific volatility parameter
        eps     = Gaussian noise scaled to the size of a small timestep

    The price update formula is:

        new_price = p_t * (1 + drift/30 + eps)

    where:
        eps = z * sigma / sqrt(30)

    and z is a standard normal random variable drawn using the
    Box–Muller transform:

        z = sqrt(-2 ln u1) * cos(2π u2)

    u1 and u2 are uniform random variables from the lobby's RNG,
    ensuring each lobby has its own independent market simulation.

    After computing the raw price, the result is snapped to the nearest
    valid tick size using `round_tick`.

    Parameters
    ----------
    lobby : LobbyState
        The lobby whose price dictionary (`lobby.prices`) is updated.
        It provides:
        - `lobby.prices` : current price per asset
        - `lobby.rng`    : random number generator unique to the lobby

    Returns
    -------
    None
        Prices are modified in-place inside `lobby.prices`.

    Notes
    -----
    - GOLD and RICE are modeled with lower volatility (sigma = 0.15),
      while other assets receive higher volatility (0.30).
    - GOLD also receives a lower drift (0.02) to simulate a more stable commodity.
    - The division by 30 approximates converting annualized parameters into
      per-tick increments for a 30-step cycle (not strictly realistic, but
      suitable for a game-level simulation).
    - The `max(1e-9, u1)` guard prevents log(0) inside the Box–Muller transform.
    - Each call to this function represents *one simulation tick*,
      typically triggered by an asyncio task running at fixed intervals.

    Example (conceptual)
    --------------------
    If GOLD = 100.0 and a small positive shock occurs,
    you may get something like:

        new_price ≈ 100.0 * (1 + 0.02/30 + eps)

    followed by rounding to the nearest tick.
  """
  rng = lobby.rng
  for a in ASSETS:
    p = lobby.prices[a]
    drift = 0.02 if a == "GOLD" else 0.05
    sigma = 0.15 if a in ("GOLD", "RICE") else 0.30
    u1 = max(1e-9, rng.random())
    u2 = rng.random()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)
    eps = z * sigma / math.sqrt(30)
    newp = p * (1 + drift / 30 + eps)
    lobby.prices[a] = round_tick(newp, PRICE_TICK)
