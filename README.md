# polymarkert_strategy
Studying Polymarket's "Bitcoin Up or Down" 5-minute markets.

Install (Python 3.10+): `pip install -r requirements.txt` (and `pip install jupyter` if you don't have it).

Run: open `notebooks/example.ipynb` in Jupyter or VS Code and run all cells.

- `src/data.py`: downloads public Polymarket data (no API key needed).
- `src/plotting.py`: common plot style; `save_fig` saves figures to `figures/` as PNG.

## What data we can and cannot get (checked October 2026)

- **Markets:** each 5-minute window is its own market, with slug `btc-updown-5m-<start time in Unix seconds>`.
  Old (resolved) markets can still be fetched.
- **Price history:** about one price per minute, also for resolved markets (we found data more than 200 days old).
  So one 5-minute window has only about 5 points, and before the window the price usually sits near 0.50.
- **Trades:** every single trade, to the second (`data.get_trades`). Often 1000+ trades per 5-minute market.
- **Order book:** only while the market is open (`get_order_book` in `src/data.py`). Closed markets give a 404 error,
  so order book data must be collected live.
- **Not available:** old order books.
