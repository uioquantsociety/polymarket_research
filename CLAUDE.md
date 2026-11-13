# CLAUDE.md

Context for Claude Code in this repo. Add to it as the project grows.

## Project
UiO Quant Society research project: can we beat Polymarket's "Bitcoin Up or Down" 5-minute markets?
About 8 members each work alone in their own fork of this repo and pitch their findings.
The best work is merged into `main` of the shared repo later.
Research and backtests on public data only. Never place trades or help anyone trade on Polymarket.

## Rules for Claude
- Never commit or push. The repo owner does all git commits.
- Propose changes and wait for a yes before editing files or running long jobs.

## Layout
- `src/polymarket_data.py`: markets, winners, minute prices, trades, order books (Polymarket APIs)
- `src/binance_data.py`: BTC/USDT candles (OHLCV, buy volume, trade count) from Binance
- `data/`: local downloads, git-ignored
- Everything else (notebooks, figures, pitch) is built by each member in their own fork.

## Conventions
- All times in UTC (pandas Timestamps with tz). Convert to Europe/Oslo only for display.
- Code and comments in English; README and talk with members in Norwegian.
- Keep code simple for students: one small function per task, a docstring that lists the returned columns, short comments. Every data function returns a pandas DataFrame.
- Notebooks import from src with `sys.path.append("../src")`.

## Facts about the data (checked 2026)
- Each window is its own market. Slug: `btc-updown-5m-<window start in Unix seconds>`.
- Resolution: Chainlink BTC/USD 60s TWAP in the last minute of the window >= TWAP in the minute before the window -> "Up". Binance approximates this in ~95% of windows, so use Polymarket's `winner` as the true answer.
- Gamma `/markets` accepts up to 100 `slug` params per call (needs `closed=true`).
- CLOB `prices-history` has at most one point per minute, often 30-60 s stale. Do not use it as an executable price.
- Trades: Data API v2 (`/v2/trades?condition=...`, cursor pagination). v1 `/trades` is retired (410).
- Order books exist only while a market is open.

## Lessons learned
- Minute prices made a "TWAP gap" strategy look like +7.5 cents per trade; with real trade prices around the window start the edge was gone, because the market prices the gap within seconds. Always check an edge against trade prices at the moment of buying.
- Split train/test by time, never randomly.
