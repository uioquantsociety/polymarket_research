"""
Build the dataset: one row per 5-minute window, with the true answer y.

y comes from Polymarket itself, so it is exactly how each market was resolved.

Example:
    df = build_dataset("2026-10-01", "2026-10-08")
    df["y"]  # -> 1, 0, 0, 1, ...
"""

import pandas as pd

from polymarket_data import get_btc_5m_winners


def build_dataset(start, end):
    """
    One row per resolved 5-minute window between start and end (UTC text, e.g. "2026-10-01").

    Returns a DataFrame with columns:
      window_start = when the 5-minute window starts
      y            = 1 if "Up" won, 0 if "Down" won
    """
    winners = get_btc_5m_winners(start, end)

    df = pd.DataFrame()
    df["window_start"] = winners["window_start"]
    df["y"] = (winners["winner"] == "Up").astype(int)
    return df
