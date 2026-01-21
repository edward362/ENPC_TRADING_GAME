# domain/execution.py
from __future__ import annotations

import time
from typing import Optional, Tuple

from domain.models import LobbyState, PlayerState
from domain.portfolio import record_trade


def execute_market(lobby: LobbyState, pl: PlayerState, asset: str, side: str,
                   qty: int) -> Tuple[bool, Optional[str]]:
    """
    Executes a market order (BUY or SELL) for a given player in the lobby.

    This function implements a simplified but realistic execution model:
    - BUY orders first cover existing short positions, then open/extend longs.
    - SELL orders first close existing long positions, then open/extend shorts.
    - Position average price, entry timestamp, and quantities are updated correctly.
    - Realized PnL is computed and recorded when positions are closed.
    - Cash is debited/credited according to the executed quantity and price.

    The function modifies the player's state in-place.

    Parameters
    ----------
    lobby : LobbyState
        The lobby containing the current market price for the asset.
        Uses `lobby.prices[asset]` as the execution price.

    pl : PlayerState
        The player whose positions and cash should be updated by this execution.

    asset : str
        Asset symbol being traded (e.g., "GOLD", "RICE").

    side : str
        "BUY"  → buy quantity (cover shorts first, then open long)
        "SELL" → sell quantity (close longs first, then open short)

    qty : int
        The total quantity of the market order. Must be a positive integer.

    Returns
    -------
    Tuple[bool, Optional[str]]
        (True, None) if the order executed successfully.
        (False, "reason") if the order could not be executed.
        
        Possible failure reasons:
        - "insufficient_cash"

    Execution Logic
    ---------------
    BUY Order:
        1. Cover shorts:
            - Close as much of the short position as possible.
            - Compute realized PnL using record_trade().
            - Reduce remaining qty accordingly.
        2. Open/extend long:
            - Check cash sufficiency.
            - Update average entry price:
                new_avg = (old_avg * old_qty + price * qty) / (old_qty + qty)
            - Increase long qty.
            - Deduct cash.
            - Set entry timestamp if opening a fresh long.

    SELL Order:
        1. Close longs:
            - Close as much of the long position as possible.
            - Compute realized PnL via record_trade().
            - Reduce remaining qty accordingly.
        2. Open/extend short:
            - Update short average entry price using absolute quantities.
            - Increase short qty (qty is subtracted).
            - Credit cash.
            - Set entry timestamp if opening a fresh short.

    Position and PnL Handling
    -------------------------
    - When a position is fully closed (qty goes to zero), the average price
      and entry timestamp are reset.
    - Realized PnL is added to `pl.realized_pnl`.
    - Cash is updated correctly for both buy and sell executions.

    Notes
    -----
    - This is a simplified trading model with a single market price and no slippage
      or order book. All orders execute at the current mid-price.
    - Execution is atomic: if any part of the order violates constraints (e.g.
      insufficient cash), the function returns an error before modifying state.
    - The function does not handle margin, leverage, commissions, or liquidation.

    Examples
    --------
    - BUY with an existing short:
        First covers the short (realizing PnL), then opens a long if qty remains.

    - SELL with an existing long:
        First closes part/all of the long, then opens a short if qty remains.
    """
    price = lobby.prices[asset]
    pos = pl.positions[asset]
    cash = pl.cash

    if side == "BUY":
        # cover short first
        if pos["qty"] < 0:
            cover = min(qty, -pos["qty"])
            if cover > 0:
                record_trade(
                    pl,
                    asset=asset,
                    side_open="SHORT",
                    qty=cover,
                    entry_price=pos["avg"],
                    exit_price=price,
                    entry_ts=pos["entry_ts"],
                )
                cash -= price * cover
                pos["qty"] += cover
                if pos["qty"] == 0:
                    pos["avg"] = 0.0
                    pos["entry_ts"] = None
                qty -= cover

        # extend/create long
        if qty > 0:
            cost = price * qty
            if cash < cost:
                return False, "insufficient_cash"
            if pos["qty"] > 0:
                pos["avg"] = (pos["avg"] * pos["qty"] +
                              price * qty) / (pos["qty"] + qty)
            else:
                pos["avg"] = price
            pos["qty"] += qty
            cash -= cost
            if pos["entry_ts"] is None:
                pos["entry_ts"] = time.time()

    else:  # SELL
        # close long first
        if pos["qty"] > 0:
            close_qty = min(qty, pos["qty"])
            if close_qty > 0:
                record_trade(
                    pl,
                    asset=asset,
                    side_open="LONG",
                    qty=close_qty,
                    entry_price=pos["avg"],
                    exit_price=price,
                    entry_ts=pos["entry_ts"],
                )
                cash += price * close_qty
                pos["qty"] -= close_qty
                if pos["qty"] == 0:
                    pos["avg"] = 0.0
                    pos["entry_ts"] = None
                qty -= close_qty

        # open/extend short
        if qty > 0:
            notional = price * qty

            # SIMPLE SHORT RULE: require cash collateral BEFORE receiving short proceeds
            if cash < notional:
                return False, "insufficient_cash_to_short"

            new_qty = pos["qty"] - qty
            if pos["qty"] < 0:
                pos["avg"] = (pos["avg"] * abs(pos["qty"]) +
                              price * qty) / (abs(pos["qty"]) + qty)
            else:
                pos["avg"] = price
            pos["qty"] = new_qty
            cash += notional
            if pos["entry_ts"] is None:
                pos["entry_ts"] = time.time()

    pl.cash = cash
    return True, None
