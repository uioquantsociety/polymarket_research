"""
Download public market data from Polymarket (no login or API key needed).

APIs used (docs: https://docs.polymarket.com):
  - Gamma API (https://gamma-api.polymarket.com): market information.
  - CLOB API  (https://clob.polymarket.com): price history and order books.
  - Data API  (https://data-api.polymarket.com): every single trade.

All times are in UTC.

Example:
    prices = get_btc_5m_prices("2026-10-20 08:55")
"""

import json

import pandas as pd
import requests

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"


def get_json(url, params=None):
    """Send a GET request and return the JSON answer (stops with an error on failure)."""
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def btc_5m_slug(window_start):
    """
    Build the slug (name) of a "Bitcoin Up or Down" 5-minute market.

    window_start is the start of the 5-minute window as UTC text, e.g. "2026-10-20 08:55".
    The slug is "btc-updown-5m-" + the start time in Unix seconds.
    """
    unix_seconds = int(pd.Timestamp(window_start, tz="UTC").timestamp())
    return "btc-updown-5m-" + str(unix_seconds)


def get_market(slug):
    """
    Get one market from the Gamma API.

    Returns a dict with: question, condition_id, window_start, window_end, winner and token_ids.
    winner is "Up" or "Down" (None if the market is not resolved yet).
    token_ids maps each outcome to its token id, e.g. {"Up": "1148...", "Down": "7983..."}.
    """
    m = get_json(GAMMA_URL + "/markets/slug/" + slug)

    # "v2" markets list their token ids in positionIds, older ones in clobTokenIds (JSON text).
    if m.get("version") == "v2":
        token_ids = m["positionIds"]
    else:
        token_ids = json.loads(m["clobTokenIds"])
    outcomes = json.loads(m["outcomes"])  # e.g. ["Up", "Down"]

    # After resolution, outcomePrices is ["1", "0"] (Up won) or ["0", "1"] (Down won).
    outcome_prices = json.loads(m.get("outcomePrices") or "[]")
    winner = None
    if m["closed"] and "1" in outcome_prices:
        winner = outcomes[outcome_prices.index("1")]

    return {
        "question": m["question"],
        "condition_id": m["conditionId"],
        "window_start": pd.Timestamp(m["eventStartTime"]),
        "window_end": pd.Timestamp(m["endDate"]),
        "winner": winner,
        "token_ids": {outcome: str(t) for outcome, t in zip(outcomes, token_ids)},
    }


def get_price_history(token_id, start, end):
    """
    Get the price of one token from the CLOB API, one point per minute.

    Returns a DataFrame with columns: timestamp, price.
    """
    params = {
        "market": token_id,
        "startTs": int(start.timestamp()),
        "endTs": int(end.timestamp()),
        "fidelity": 1,  # minutes between points
    }
    history = get_json(CLOB_URL + "/prices-history", params)["history"]

    # "t" is Unix time in seconds, "p" is the price.
    df = pd.DataFrame(history, columns=["t", "p"]).rename(columns={"t": "timestamp", "p": "price"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    return df


def get_btc_5m_prices(window_start, minutes_before=0):
    """
    Get the "Up" and "Down" prices of one Bitcoin 5-minute market, one point per minute.

    The prices go from minutes_before the window starts until the window ends.
    Returns a DataFrame with columns: timestamp, up, down.
    """
    market = get_market(btc_5m_slug(window_start))
    start = market["window_start"] - pd.Timedelta(minutes=minutes_before)
    end = market["window_end"]

    up = get_price_history(market["token_ids"]["Up"], start, end)
    down = get_price_history(market["token_ids"]["Down"], start, end)

    # The two tokens are priced a few seconds apart, so round to whole minutes before joining.
    up["timestamp"] = up["timestamp"].dt.floor("min")
    down["timestamp"] = down["timestamp"].dt.floor("min")
    return up.merge(down, on="timestamp", suffixes=("_up", "_down")).rename(
        columns={"price_up": "up", "price_down": "down"})


def get_trades(condition_id):
    """
    Get every trade in one market from the Data API (to the second, much finer than prices).

    Returns a DataFrame with columns: timestamp, outcome, side, price, size, sorted by time.
    We keep no information about who traded.
    """
    # The API gives at most 1000 trades per call, so we ask page by page.
    trades = []
    while True:
        params = {"market": condition_id, "limit": 1000, "offset": len(trades)}
        page = get_json("https://data-api.polymarket.com/trades", params)
        trades += page
        if len(page) < 1000:
            break

    df = pd.DataFrame(trades, columns=["timestamp", "outcome", "side", "price", "size"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    return df.sort_values("timestamp", ignore_index=True)


def get_order_book(token_id):
    """
    Get the current order book of one token from the CLOB API.

    Only works while the market is open (closed markets give a 404 error).
    Returns a DataFrame with columns: side, price, size.
    """
    book = get_json(CLOB_URL + "/book", {"token_id": token_id})

    bids = pd.DataFrame(book["bids"], columns=["price", "size"]).assign(side="bid")
    asks = pd.DataFrame(book["asks"], columns=["price", "size"]).assign(side="ask")
    df = pd.concat([bids, asks], ignore_index=True)

    # Prices and sizes come as text, so convert them to numbers.
    df[["price", "size"]] = df[["price", "size"]].astype(float)
    return df[["side", "price", "size"]]
