# Polymarket BTC Up/Down: klarer vi å slå markedet?

Fellesprosjekt i UiO Quant Society. Alle jobber med **samme hypotese og samme datakilder**, men velger sin egen vinkling. På neste møte pitcher alle sine funn, og vi velger den beste.


---

## Hypotesen

> **Klarer vi å slå markedet på Polymarkets «Bitcoin Up or Down» 5-minuttersmarkeder?**

«Slå markedet» betyr at du finner en regel eller modell som enten
- **forutsier utfallet bedre enn markedsprisen**, eller
- **ville tjent penger** hvis du hadde kjøpt til prisen som faktisk gjaldt der og da,

og at det holder på data du **ikke** brukte til å finne regelen.

Hypotesen er bevisst åpen. Velg selv *hva* du ser på (start av vinduet, siste minutt, store BTC-hopp, tid på døgnet …) og *hvordan* (se metodestikkordene nederst).


---

## Slik fungerer markedene

- Hvert marked dekker 5 minutter, for eksempel 08:55–09:00 UTC. Det finnes 288 per døgn.
- **Up** vinner hvis BTC ender vinduet høyere enn eller likt der den startet, ellers vinner **Down**.
- En Up-andel betaler 1 dollar hvis Up vinner. Prisen (0–1) kan derfor leses som markedets sannsynlighet for Up.
- **Nøyaktig regel:** Polymarket sammenligner Chainlinks *gjennomsnittspris (TWAP) det siste minuttet* av vinduet med gjennomsnittsprisen *minuttet før* vinduet starter.

---

## Kom i gang

Alle jobber i **sitt eget repo**. Etter pitchen flettes det beste inn i `main` her.

1. Trykk **Fork** øverst på GitHub-siden til dette repoet. Da får du en kopi under din egen bruker, og den henger sammen med dette repoet, så det beste enkelt kan flettes inn senere med en pull request.
2. Klon *ditt eget* repo og installer pakkene (Python 3.10+):
   ```bash
   git clone https://github.com/<ditt-brukernavn>/polymarket_research.git
   cd polymarket_research
   pip install -r requirements.txt
   ```
3. Jobb fritt i ditt eget repo, og commit og push så ofte du vil.

Lag gjerne en mappe for notebookene dine (for eksempel `analysis/`). Fra en notebook i den mappen:

```python
import sys
sys.path.append("../src")  # so Python finds polymarket_data.py and binance_data.py

import polymarket_data as pm
import binance_data as bn
```

---

## Dataene

All kode for å hente data ligger i to filer i `src/`. Ingen nøkler eller innlogging trengs, og alle tider er i UTC.

### `polymarket_data.py`

| funksjon | gir deg |
|---|---|
| `get_btc_5m_markets(start, end)` | alle avgjorte markeder i en periode: `window_start`, `winner`, `condition_id`, `up_token_id`, `down_token_id`. Én måned tar noen sekunder. |
| `get_trades(condition_id)` | **hver handel** i ett marked, per sekund: `timestamp`, `outcome`, `side`, `price`, `size`, `up_price` |
| `get_price_history(token_id, start, end)` | pris per minutt for Up eller Down |
| `get_btc_5m_prices(window_start)` | Up- og Down-pris per minutt for ett marked |
| `get_market(slug)` / `btc_5m_slug(window_start)` | detaljer om ett marked / navnet på markedet |
| `get_order_book(token_id)` | ordreboken akkurat nå (bare mens markedet er åpent) |

```python
markets = pm.get_btc_5m_markets("2026-10-01", "2026-10-08")   # one week, ~2000 markets
markets["y"] = (markets["winner"] == "Up").astype(int)          # the true answer: 1 = Up won

trades = pm.get_trades(markets["condition_id"][0])              # every trade in the first market
```

### `binance_data.py`

| funksjon | gir deg |
|---|---|
| `get_btc_prices(start, end, timeframe)` | BTC/USDT-candles: `timestamp, open, high, low, close, volume, buy_volume, trades` |

`timeframe` kan være `"1s"`, `"1m"`, `"5m"`, `"1h"` eller `"1d"`. `timestamp` er når candlen **starter**.

```python
btc = bn.get_btc_prices("2026-10-01", "2026-10-08", timeframe="1m")
```

Lagre store nedlastinger i `data/` (for eksempel `markets.to_csv("../data/markets.csv")`). Mappen er i `.gitignore`, så den havner ikke i git.

---

## Metodestikkord: velg din vinkling

**Statistiske modeller:** logistisk regresjon · Lasso/Ridge · interaksjonsledd · probit / Brownsk bevegelse («rettferdig» sannsynlighet fra volatilitet)

**Maskinlæring:** beslutningstre / Random Forest · gradient boosting (XGBoost/LightGBM) · feature importance / SHAP · k-nærmeste naboer

**Tidsserier:** autokorrelasjon · momentum mot tilbakegang · GARCH / volatilitetsklynger · Markov-kjede

**Markedseffektivitet:** kalibrering (vinner Up 60 % når prisen er 0,60?) · favoritt–longshot-skjevhet · over- eller underreaksjon · hendelsesstudie (KPI, rentemøter, børsåpning i USA 13:30 UTC) · sesongmønstre

**Hypotesetesting:** binomisk test · bootstrap · permutasjonstest · korreksjon for mange tester (Bonferroni)

**Evaluering og handel:** log-loss / Brier-score · ROC og AUC · walk-forward-validering · Kelly-kriteriet · Sharpe ratio og drawdown · gebyrer og spread

**Andre datakilder:** ordreflyt (`buy_volume` fra Binance) · funding rate og open interest · ETH/SOL som ledende signal · sentiment (Fear & Greed, Google Trends)

**Eksempler på vinklinger**
- *Henger markedet etter BTC?* Handelspriser per sekund mot Binance `1s`
- *Er markedet kalibrert?* Kalibreringsplott + favoritt–longshot
- *Overreagerer markedet på store hopp?* Hendelsesstudie + bootstrap
- *Når er markedet dårligst?* Tid på døgnet, helg, volatilitetsregimer
- *Er siste minutt «låst»?* TWAP-regelen + handelspriser i siste minutt

---

## Pitch på neste møte

- **5 minutter** per person, i fritt format: HTML-presentasjon, PowerPoint eller et prosjekt i Overleaf.
- Forslag til struktur: **hypotese → data → metode → resultat → slo du markedet? → hvorfor/hvorfor ikke**.
- Vis resultatet på data du ikke brukte til å finne regelen.
- Et ærlig «nei, og her er hvorfor» er også en god pitch.
- Vi velger den beste vinklingen og jobber videre med den sammen.

---

## Repostruktur

```
README.md          ← du er her
CLAUDE.md          ← kontekst for Claude Code (bygges opp underveis)
requirements.txt
src/
  polymarket_data.py
  binance_data.py
data/              ← dine nedlastinger (ikke i git)
```

Resten bygger du selv i ditt eget repo: notebooks, figurer og pitch.

**Hente oppdateringer:** hvis datafilene her blir forbedret, trykker du **Sync fork** på GitHub-siden til ditt repo og kjører `git pull`.
