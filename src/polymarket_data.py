"""
Download public data about Polymarket's "Bitcoin Up or Down" 5-minute markets.

No login or API key is needed. All times are in UTC.

What you can get:
  Markets
    get_btc_5m_markets(start, end)  every resolved market in a period, with its winner
    get_market(slug)                details of one market
    btc_5m_slug(window_start)       the name (slug) of the market for a window
  Prices
    get_price_history(token_id, start, end)  price of "Up" or "Down", one point per minute
    get_btc_5m_prices(window_start)          "Up" and "Down" prices of one market, per minute
  Trades
    get_trades(condition_id)        every single trade in one market, to the second
  Order book
    get_order_book(token_id)        current bids and asks (only while the market is open)

Example:
    markets = get_btc_5m_markets("2026-10-01", "2026-10-02")
    trades = get_trades(markets["condition_id"][0])

APIs used (docs: https://docs.polymarket.com):
  - Gamma API (https://gamma-api.polymarket.com): market information
  - CLOB API  (https://clob.polymarket.com): price history and order books
  - Data API  (https://data-api.polymarket.com): trades
"""

import json
import time

import pandas as pd
import requests

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"
DATA_URL = "https://data-api.polymarket.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_json(url, params=None):
    """Send a GET request and return the JSON answer. Tries again if the API is busy or slow."""
    for attempt in range(5):
        try:
            response = requests.get(url, params=params, timeout=30)
        except requests.exceptions.Timeout:
            time.sleep(2 * (attempt + 1))
            continue
        if response.status_code != 429:  # 429 = "too many requests": wait and try again
            response.raise_for_status()
            return response.json()
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("No answer from " + url + " after 5 tries")


def btc_5m_slug(window_start):
    """
    Build the slug (name) of a "Bitcoin Up or Down" 5-minute market.

    window_start is the start of the 5-minute window, e.g. "2026-10-20 08:55" (UTC).
    The slug is "btc-updown-5m-" + the start time in Unix seconds.
    """
    unix_seconds = int(pd.to_datetime(window_start, utc=True).timestamp())
    return "btc-updown-5m-" + str(unix_seconds)


def find_winner(m):
    """Return "Up" or "Down" for a market from the Gamma API (None if not resolved yet)."""
    outcomes = json.loads(m["outcomes"])  # e.g. ["Up", "Down"]

    # After resolution, outcomePrices is ["1", "0"] (Up won) or ["0", "1"] (Down won).
    outcome_prices = json.loads(m.get("outcomePrices") or "[]")
    if m["closed"] and "1" in outcome_prices:
        return outcomes[outcome_prices.index("1")]
    return None


def find_token_ids(m):
    """Return {"Up": token id, "Down": token id} for a market from the Gamma API."""
    # "v2" markets list their token ids in positionIds, older ones in clobTokenIds (JSON text).
    if m.get("version") == "v2":
        token_ids = m["positionIds"]
    else:
        token_ids = json.loads(m["clobTokenIds"])
    outcomes = json.loads(m["outcomes"])  # e.g. ["Up", "Down"]
    return {outcome: str(t) for outcome, t in zip(outcomes, token_ids)}


# ---------------------------------------------------------------------------
# Markets
# ---------------------------------------------------------------------------

def get_btc_5m_markets(start, end):
    """
    Get every resolved Bitcoin 5-minute market between start and end (UTC, e.g. "2026-10-01").

    Fast: 100 markets per call, so one month takes a few seconds.
    Returns a DataFrame with one row per market and columns:
      window_start  = when the 5-minute window starts
      winner        = "Up" or "Down" (the true answer)
      condition_id  = id of the market (needed for get_trades)
      up_token_id   = id of the "Up" token (needed for prices and order books)
      down_token_id = id of the "Down" token
    """
    window_starts = pd.date_range(pd.to_datetime(start, utc=True), pd.to_datetime(end, utc=True),
                                  freq="5min", inclusive="left")

    rows = []
    for i in range(0, len(window_starts), 100):
        slugs = [btc_5m_slug(w) for w in window_starts[i:i + 100]]
        params = [("slug", s) for s in slugs] + [("closed", "true"), ("limit", 100)]
        for m in get_json(GAMMA_URL + "/markets", params):
            token_ids = find_token_ids(m)
            rows.append({
                "window_start": pd.Timestamp(m["eventStartTime"]),
                "winner": find_winner(m),
                "condition_id": m["conditionId"],
                "up_token_id": token_ids["Up"],
                "down_token_id": token_ids["Down"],
            })

    columns = ["window_start", "winner", "condition_id", "up_token_id", "down_token_id"]
    df = pd.DataFrame(rows, columns=columns).dropna()
    return df.sort_values("window_start", ignore_index=True)


def get_market(slug):
    """
    Get one market from the Gamma API.

    Returns a dict with: question, condition_id, window_start, window_end, winner and token_ids.
    winner is "Up" or "Down" (None if the market is not resolved yet).
    token_ids maps each outcome to its token id, e.g. {"Up": "1148...", "Down": "7983..."}.
    """
    m = get_json(GAMMA_URL + "/markets/slug/" + slug)
    return {
        "question": m["question"],
        "condition_id": m["conditionId"],
        "window_start": pd.Timestamp(m["eventStartTime"]),
        "window_end": pd.Timestamp(m["endDate"]),
        "winner": find_winner(m),
        "token_ids": find_token_ids(m),
    }


# ---------------------------------------------------------------------------
# Prices (one point per minute)
# ---------------------------------------------------------------------------

def get_price_history(token_id, start, end):
    """
    Get the price of one token between start and end, one point per minute.

    Careful: each point can be 30-60 seconds old, which is a long time in these markets.
    Use get_trades() if you need the price at an exact moment.
    Returns a DataFrame with columns: timestamp, price.
    """
    params = {
        "market": token_id,
        "startTs": int(pd.to_datetime(start, utc=True).timestamp()),
        "endTs": int(pd.to_datetime(end, utc=True).timestamp()),
        "fidelity": 1,  # minutes between points
    }
    history = get_json(CLOB_URL + "/prices-history", params)["history"]

    # "t" is Unix time in seconds, "p" is the price.
    df = pd.DataFrame(history, columns=["t", "p"]).rename(columns={"t": "timestamp", "p": "price"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    return df


def get_btc_5m_prices(window_start, minutes_before=0):
    """
    Get the "Up" and "Down" prices of one market, one point per minute.

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


# ---------------------------------------------------------------------------
# Trades (every single trade, to the second)
# ---------------------------------------------------------------------------

def get_trades(condition_id):
    """
    Get every trade in one market (often 1000+ trades per 5-minute market).

    Returns a DataFrame sorted by time, with columns:
      timestamp = when the trade happened (to the second)
      outcome   = "Up" or "Down" (which token was traded)
      side      = "BUY" or "SELL"
      price     = price of that token (0-1)
      size      = number of tokens
      up_price  = the same trade as a price of "Up" (a Down trade at 0.30 = Up at 0.70)
    We keep no information about who traded.
    """
    # The API gives at most 1000 trades per call. Each answer tells us where the next page starts.
    trades = []
    params = {"condition": condition_id, "limit": 1000}
    while True:
        answer = get_json(DATA_URL + "/v2/trades", params)
        trades += answer["data"]
        if not answer["pagination"]["has_more"]:
            break
        params["cursor"] = answer["pagination"]["next_cursor"]

    df = pd.DataFrame(trades, columns=["timestamp", "outcome", "side", "price", "size"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["up_price"] = df["price"].where(df["outcome"] == "Up", 1 - df["price"])
    return df.sort_values("timestamp", ignore_index=True)


# ---------------------------------------------------------------------------
# Order book (only while the market is open)
# ---------------------------------------------------------------------------

def get_order_book(token_id):
    """
    Get the current order book of one token.

    Only works while the market is open (closed markets give a 404 error),
    so old order books cannot be downloaded: you must save them yourself, live.
    Returns a DataFrame with columns: side ("bid" or "ask"), price, size.
    """
    book = get_json(CLOB_URL + "/book", {"token_id": token_id})

    bids = pd.DataFrame(book["bids"], columns=["price", "size"]).assign(side="bid")
    asks = pd.DataFrame(book["asks"], columns=["price", "size"]).assign(side="ask")
    df = pd.concat([bids, asks], ignore_index=True)

    # Prices and sizes come as text, so convert them to numbers.
    df[["price", "size"]] = df[["price", "size"]].astype(float)
    return df[["side", "price", "size"]]
