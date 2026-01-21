# domain/pricing.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional

from config import ASSETS, PRICE_TICK

if TYPE_CHECKING:
    from domain.models import LobbyState


def round_tick(x: float, tick: float = PRICE_TICK) -> float:
    """
    Round a price to the nearest valid tick size and enforce a strictly positive minimum.

    Args:
        x: Raw price value.
        tick: Tick size to round to.

    Returns:
        The tick-rounded price, with a lower bound of `tick`.
    """
    return max(tick, round(x / tick) * tick)


@dataclass
class MarketState:
    """
    Per-asset market state for a simple regime-switching price process.

    The process alternates between:
      - RANGE: mean-reverting dynamics inside a support/resistance band.
      - TREND_UP / TREND_DOWN: directional movement toward a precomputed target,
        followed by a range rebuild around the reached (or prematurely ended) price.

    Attributes:
        regime: Current regime identifier: "RANGE", "TREND_UP", or "TREND_DOWN".
        price: Current unrounded price level.
        support: Lower boundary of the current (or most recent) range.
        resistance: Upper boundary of the current (or most recent) range.
        trend_low: Trend start level (derived from the last range boundary at breakout).
        trend_high: Trend target level (derived from last range width and direction).
        ticks_in_range: Number of ticks spent in the current RANGE regime.

    Notes:
        Fields named `trend_low` and `trend_high` are used as (start, target) levels.
        In a downward trend, the target level may be numerically below the start level.
    """

    # Regime: "RANGE", "TREND_UP", "TREND_DOWN"
    regime: str
    price: float

    # Range levels (valid in RANGE; also retained during TREND as last known range)
    support: float
    resistance: float

    # Trend levels (valid in TREND): start and target computed from last range
    trend_low: Optional[float] = None
    trend_high: Optional[float] = None

    # Counters
    ticks_in_range: int = 0

    # --- Tunable parameters ---
    # Range behaviour
    k_revert: float = 0.08          # mean reversion strength toward range center
    sigma0: float = 0.6             # base noise scale in RANGE
    alpha_edge: float = 1.2         # noise multiplier near range edges
    zone_frac: float = 0.12         # edge zone size as a fraction of range width
    rebound_push: float = 1.0       # additional drift away from edges (bounce effect)
    p_break0: float = 0.04          # initial breakout probability in edge zones
    p_break_slope: float = 0.0004   # breakout probability increase per tick in RANGE
    p_break_max: float = 0.22       # upper bound on breakout probability
    range_timeout: int = 220        # maximum ticks in RANGE before forcing a breakout

    # Trend behaviour (towards target)
    k_target: float = 0.06          # attraction strength toward trend target
    sigma_trend: float = 0.85       # noise scale in TREND
    target_lambda_min: float = 0.8  # min target distance multiplier (relative to last range width)
    target_lambda_max: float = 2.5  # max target distance multiplier (relative to last range width)
    target_zone_frac: float = 0.10  # target proximity threshold as a fraction of range width
    p_trend_end: float = 0.01       # probability of ending TREND early (independent of proximity)

    # Range rebuild after trend
    rebuild_width_frac: float = 1.0 # rebuild width multiplier based on previous range width
    width_jitter: float = 0.15      # symmetric jitter applied when rebuilding the range width


def _clamp(x: float, lo: float, hi: float) -> float:
    """
    Clamp a value to a closed interval [lo, hi].

    Args:
        x: Input value.
        lo: Lower bound.
        hi: Upper bound.

    Returns:
        The clamped value.
    """
    return max(lo, min(hi, x))


def _ensure_market_states(lobby: LobbyState) -> Dict[str, MarketState]:
    """
    Ensure `lobby.market_states` exists and contains a `MarketState` for each asset.

    This function creates `lobby.market_states` dynamically if absent, and initializes
    missing per-asset states using the current lobby price and a randomized initial
    range width. A subset of assets may start in a TREND regime based on `p_trend0`.

    Args:
        lobby: The lobby state providing prices, RNG, and configuration.

    Returns:
        A dictionary mapping asset symbol to its `MarketState`.
    """
    ms = getattr(lobby, "market_states", None)
    if ms is None:
        ms = {}
        setattr(lobby, "market_states", ms)

    # Initialize missing assets.
    for a in ASSETS:
        if a not in ms:
            p0 = float(lobby.prices[a])

            # Initial range width as a fraction of the price, with a minimum tick-based floor.
            w_frac = lobby.rng.uniform(0.02, 0.06)  # 2% to 6%
            w0 = max(PRICE_TICK * 10, p0 * w_frac)
            s0 = p0 - 0.5 * w0
            r0 = p0 + 0.5 * w0

            # Initial regime selection (applied only at initialization).
            u = lobby.rng.random()
            p_trend0 = 0.35
            if u < p_trend0:
                direction = "TREND_UP" if lobby.rng.random() < 0.5 else "TREND_DOWN"
                st = MarketState(
                    regime=direction,
                    price=p0,
                    support=s0,
                    resistance=r0,
                )
                _init_trend_from_last_range(st, lobby)
            else:
                st = MarketState(
                    regime="RANGE",
                    price=p0,
                    support=s0,
                    resistance=r0,
                )

            ms[a] = st

    return ms


def _init_trend_from_last_range(st: MarketState, lobby: LobbyState) -> None:
    """
    Initialize the trend start/target levels from the most recent range boundaries.

    The target distance is proportional to the most recent range width:
        target = boundary +/- lambda * width
    where `lambda` is sampled uniformly from [target_lambda_min, target_lambda_max].

    Args:
        st: The market state to update.
        lobby: The lobby state providing RNG and configuration.
    """
    width = max(PRICE_TICK * 10, st.resistance - st.support)
    lam = lobby.rng.uniform(st.target_lambda_min, st.target_lambda_max)

    if st.regime == "TREND_UP":
        L0 = st.resistance
        L1 = L0 + lam * width
        st.trend_low, st.trend_high = L0, L1
    elif st.regime == "TREND_DOWN":
        L0 = st.support
        L1 = L0 - lam * width
        st.trend_low, st.trend_high = L0, L1
    else:
        st.trend_low, st.trend_high = None, None


def _rebuild_range_around_price(st: MarketState, lobby: LobbyState) -> None:
    """
    Rebuild a new RANGE around the current price after a TREND ends.

    The new range width is derived from the prior range width, scaled by
    `rebuild_width_frac` and jittered by `width_jitter`, with a minimum floor.

    Args:
        st: The market state to update.
        lobby: The lobby state providing RNG and configuration.
    """
    prev_w = max(PRICE_TICK * 10, st.resistance - st.support)
    jitter = 1.0 + lobby.rng.uniform(-st.width_jitter, st.width_jitter)
    new_w = max(PRICE_TICK * 10, prev_w * st.rebuild_width_frac * jitter)

    st.support = st.price - 0.5 * new_w
    st.resistance = st.price + 0.5 * new_w
    st.regime = "RANGE"
    st.ticks_in_range = 0
    st.trend_low = None
    st.trend_high = None


def _tick_one_asset(st: MarketState, lobby: LobbyState) -> None:
    """
    Advance a single asset by one simulation tick.

    The update depends on the current regime:
      - TREND: moves toward a precomputed target with noise; may end near target
        or via an independent termination probability.
      - RANGE: mean-reverts toward the center with edge-dependent volatility;
        near edges, the process may bounce or break out into a trend.

    Args:
        st: The market state for the asset.
        lobby: The lobby state providing RNG and configuration.
    """
    rng = lobby.rng
    P = st.price
    S = st.support
    R = st.resistance
    width = max(PRICE_TICK * 10, R - S)

    def gauss() -> float:
        """
        Standard normal sample via Box-Muller using `rng.random()`.

        Returns:
            A single N(0, 1) draw.
        """
        u1 = max(1e-9, rng.random())
        u2 = rng.random()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)

    # ---------------- TREND ----------------
    if st.regime in ("TREND_UP", "TREND_DOWN"):
        # Ensure trend levels are available before computing the next step.
        if st.trend_low is None or st.trend_high is None:
            _init_trend_from_last_range(st, lobby)

        # The trend target level is stored in `trend_high` for both directions.
        target = st.trend_high

        # Drift toward the target plus additive noise.
        mu = st.k_target * (target - P)
        P_next = P + mu + st.sigma_trend * gauss()
        st.price = P_next

        # Termination: close enough to target (direction-dependent) or probabilistic end.
        tz = st.target_zone_frac * width
        near_target = (P_next >= target - tz) if st.regime == "TREND_UP" else (P_next <= target + tz)
        if near_target or (rng.random() < st.p_trend_end):
            _rebuild_range_around_price(st, lobby)
        return

    # ---------------- RANGE ----------------
    C = 0.5 * (S + R)

    # Normalized distance to the center (0 at center, 1 at the boundaries).
    edge = abs(P - C) / (0.5 * width)
    edge = _clamp(edge, 0.0, 1.0)

    # Edge-dependent volatility and mean-reversion drift.
    sigma = st.sigma0 * (1.0 + st.alpha_edge * edge)
    drift = -st.k_revert * (P - C)

    # Edge zones used to decide between bouncing and breakout.
    z = st.zone_frac * width
    in_upper_zone = P >= (R - z)
    in_lower_zone = P <= (S + z)

    # Breakout probability increases with time spent in RANGE, capped by `p_break_max`.
    p_break = st.p_break0 + st.p_break_slope * st.ticks_in_range
    p_break = _clamp(p_break, 0.0, st.p_break_max)

    # Edge handling: breakout into TREND or bounce back into the range.
    if in_upper_zone:
        if rng.random() < p_break:
            st.regime = "TREND_UP"
            _init_trend_from_last_range(st, lobby)
            return
        else:
            drift -= abs(st.rebound_push)
            sigma *= 1.25

    if in_lower_zone:
        if rng.random() < p_break:
            st.regime = "TREND_DOWN"
            _init_trend_from_last_range(st, lobby)
            return
        else:
            drift += abs(st.rebound_push)
            sigma *= 1.25

    # Range step: drift plus noise.
    P_next = P + drift + sigma * gauss()
    st.price = P_next
    st.ticks_in_range += 1

    # Timeout: force a breakout after prolonged ranging.
    if st.ticks_in_range > st.range_timeout:
        st.regime = "TREND_UP" if rng.random() < 0.5 else "TREND_DOWN"
        _init_trend_from_last_range(st, lobby)


def step_prices(lobby: LobbyState):
    """
    Advance all asset prices by one simulation tick.

    This function updates:
      - `lobby.prices[a]` for each asset `a` in `ASSETS` (tick-rounded),
      - `lobby.market_states[a]` (created on-demand and mutated in place).

    Args:
        lobby: The lobby state containing current prices and RNG.
    """
    market_states = _ensure_market_states(lobby)

    for a in ASSETS:
        st = market_states[a]
        _tick_one_asset(st, lobby)
        lobby.prices[a] = round_tick(st.price, PRICE_TICK)
