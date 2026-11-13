"""
Download public BTC price and volume data from Binance (no login or API key needed).

API used (docs: https://developers.binance.com/docs/binance-spot-api-docs):
  - https://data-api.binance.vision: Binance's address for public market data only.

All times are in UTC.

Example:
    btc = get_btc_prices("2026-10-20 08:00", "2026-10-20 09:00", timeframe="1m")
"""

import pandas as pd
import requests

BINANCE_URL = "https://data-api.binance.vision"


def get_btc_prices(start, end, timeframe="1m"):
    """
    Get BTC/USDT candles from Binance between start and end (end not included).

    start, end: UTC text, e.g. "2026-10-20 08:00".
    timeframe: length of each candle: "1s", "1m", "5m", "1h", "1d".

    Returns a DataFrame with one row per candle and columns:
      timestamp  = when the candle starts
      open       = BTC price at the start of the candle
      high       = highest BTC price during the candle
      low        = lowest BTC price during the candle
      close      = BTC price at the end of the candle
      volume     = how much BTC was traded during the candle
      buy_volume = the part of volume where the buyer started the trade (buying pressure)
      trades     = number of trades during the candle
    """
    start_ms = int(pd.to_datetime(start, utc=True).timestamp() * 1000)
    end_ms = int(pd.to_datetime(end, utc=True).timestamp() * 1000)

    # Binance gives at most 1000 candles per call, so we ask page by page.
    candles = []
    while start_ms < end_ms:
        params = {"symbol": "BTCUSDT", "interval": timeframe,
                  "startTime": start_ms, "endTime": end_ms - 1, "limit": 1000}
        response = requests.get(BINANCE_URL + "/api/v3/klines", params=params, timeout=30)
        response.raise_for_status()
        page = response.json()
        if not page:
            break
        candles += page
        start_ms = page[-1][0] + 1  # continue after the last candle we got

    # Each candle is a list: [start time in ms, open, high, low, close, volume,
    #                          end time, quote volume, trades, buy volume, ...]
    columns = ["timestamp", "open", "high", "low", "close", "volume", "buy_volume", "trades"]
    df = pd.DataFrame([c[:6] + [c[9], c[8]] for c in candles], columns=columns)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df[columns[1:7]] = df[columns[1:7]].astype(float)  # prices and volumes come as text
    df = df.drop_duplicates("timestamp").sort_values("timestamp", ignore_index=True)

    # Warn if candles are missing (for example if Binance was down).
    gaps = df["timestamp"].diff() > pd.Timedelta(timeframe)
    if gaps.any():
        print("Warning:", gaps.sum(), "gaps in the Binance data")
    return df
