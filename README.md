
# PriceRadar

**A monitoring station for price discrepancies between crypto exchanges.**

Collects bid/ask from three exchanges (Binance, Bybit, OKX) via WebSocket, calculates spreads with taker fees, stores history, detects peaks, and reveals patterns: at what hours and on which pairs exchanges diverge the most. This is **not an arbitrage bot** — it's a tool for observation and analysis. The goal is to see not a moment, but a pattern.

**English** | [Русский](README.ru.md)

---

## What it shows

### 1. Current spreads

A table of all 54 rows (9 pairs × 3 exchange pairs × 2 directions), refreshed every 5 seconds. Displays `spread_net`, `spread_gross`, total fees, highlight level based on thresholds, and data freshness status for each exchange.

![Current spreads](docs/screenshots/01-current.png)

### 2. Spread history

Interactive chart (Chart.js) with three lines — Last, Max, Min — for the selected period and interval. Horizontal threshold lines (`0.3 / 0.5 / 1.0 / 1.5 / 2.0%`). **net / gross** metric switcher. Export to CSV / JSON.

![History](docs/screenshots/02-history.png)

### 3. Peaks list

Table of `|spread_net|` deviations above peak thresholds (`0.3 / 0.5 / 1.0 / 2.0%`). Filters by pair, exchanges, direction, threshold, and period. Pagination. Open peaks in red, closed in green.

![Peaks](docs/screenshots/03-peaks.png)

### 4. Heatmap

24 cells by hour of day in UTC. Metric — `% of time ≥ 0.3%` (primary) or `average |net|` (secondary). Color ranges from yellow to dark red. Tooltip on each cell: statistics by thresholds, avg, max, minutes of data.

![Heatmap](docs/screenshots/04-heatmap.png)

### 5. Telegram notifications

Notifications on peak opening with threshold ≥ configured value. Cooldown — no more than once every N minutes per row.

![Telegram](docs/screenshots/05-telegram.png)

### 6. Fees management

UI for updating exchange taker fees with versioning: the old version is closed (`effective_to`), the new one is opened (`effective_from`). Past aggregates and peaks keep their `fee_version`.

![Fees](docs/screenshots/06-fees.png)

---

## Features

- **Collection from 3 exchanges** via WebSocket: Binance, Bybit, OKX.
- **9 trading pairs:** BTC, ETH, SOL, BNB, XRP, DOGE, ADA, AVAX, LINK (to USDT).
- **54 rows:** 9 pairs × 3 exchange pairs × 2 directions (A→B and B→A are independent rows).
- **Taker fees accounted:** `spread_net = spread_gross − fee_A − fee_B`.
- **Per-second ring buffer** in memory: 54 buffers × 3600 points (1 hour).
- **Minute aggregation** in PostgreSQL: min / max / avg_abs / avg_signed / last + `seconds_above_*` counters.
- **Peak detector** with 3-second hysteresis and pause during data gaps.
- **Heatmap** by hour of day in UTC.
- **Telegram notifications** when threshold is exceeded.
- **Export** to CSV / JSON.
- **Fees management** via UI with versioning.
- **Versioning of thresholds and fees** (`threshold_version`, `fee_version`) — old data is not mixed with new.

---

## Architecture

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Binance  │  │  Bybit   │  │   OKX    │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │ WS          │ WS          │ WS
     └─────────────┼─────────────┘
                   ▼
         ┌──────────────────┐
         │     FastAPI      │
         │  ─ collectors    │  WebSocket → in-memory PriceStore
         │  ─ spread_engine │  gross / net calculation
         │  ─ ring buffer   │  3600 points × 54 rows
         │  ─ aggregator    │  every minute → DB
         │  ─ peak_detector │  open / close peaks
         │  ─ notifier      │  Telegram on threshold
         └────────┬─────────┘
                  │
          ┌───────┴───────┐
          ▼               ▼
      ┌────────┐     ┌────────┐
      │   PG   │     │ Redis  │
      └────┬───┘     └────────┘
           │ REST API /api/v1/*
           ▼
      ┌──────────┐
      │ Laravel  │
      │ +Chart.js│
      └──────────┘
```

---

## Tech stack

**Backend**
- Python 3.12, FastAPI, uvicorn
- SQLAlchemy 2.0 (async), PostgreSQL 16
- Redis 7
- loguru (logging), httpx (Telegram), websockets

**Frontend**
- Laravel 13, PHP 8.4
- Blade, vanilla JS
- Chart.js 4

**Infrastructure**
- Docker Compose (5 services)
- nginx + php-fpm

---

## Getting started

### Requirements

- **Docker Desktop** — [download](https://www.docker.com/products/docker-desktop/)
- **Git** — [download](https://git-scm.com/downloads)
- Free ports: `8010` (backend), `8020` (frontend), `5432` (PostgreSQL), `6379` (Redis)

**Version check:**

```bash
docker --version
docker compose version
git --version
```

Should output versions. If `command not found` — install and **start Docker Desktop** (tray icon should be active).

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/ditlate0-spec/priceradar.git
cd priceradar

# 2. Copy configs
cp .env.example .env
cp frontend/.env.example frontend/.env

# 3. Start the stack (first run — 5–10 min to build images)
docker compose up -d

# 4. Generate APP_KEY for Laravel
docker compose exec frontend php artisan key:generate

# 5. Open in browser
# UI:           http://localhost:8020
# API Swagger:  http://localhost:8010/docs
# Health:       http://localhost:8010/api/v1/health
```

**For Windows PowerShell** — same commands, but `cp` is replaced with `copy`:

```powershell
copy .env.example .env
copy frontend\.env.example frontend\.env
```

**First data** appears in the UI in ~5 minutes (needs to fill ring buffer with 300 points).

**Full heatmap** — after 24 hours (a day of history is needed).

### Verification after start

```bash
# Containers should be Up
docker compose ps

# Expected: 5 services — db, redis, backend, frontend, frontend-nginx

# Backend responds
curl http://localhost:8010/api/v1/health
```

### Stopping

```bash
docker compose down       # stop
docker compose down -v    # stop and delete PostgreSQL data
```

### Viewing logs

```bash
docker compose logs backend --tail=50 --follow      # backend
docker compose logs frontend --tail=50 --follow     # Laravel/php-fpm
docker compose logs frontend-nginx --tail=50        # nginx
```

### Restart after changes

| What changed | Command |
|---|---|
| Backend Python code | `docker compose restart backend` |
| Blade template / JS frontend | just refresh the page (**Ctrl+F5**) |
| `.env` | `docker compose up -d --force-recreate backend` |
| `docker-compose.yml` | `docker compose up -d --force-recreate` |
| `Dockerfile` | `docker compose build <service> && docker compose up -d <service>` |

**Important:** `docker compose restart` **does not re-read** `.env`. To apply config changes — only `up -d --force-recreate`.

---

## How it works

### Spread calculation

For exchange pair (A, B) and direction A→B:

```
spread_gross(A→B) = (bid_A − ask_B) / ask_B × 100%
spread_net(A→B)   = spread_gross(A→B) − fee_A − fee_B
```

- `bid_A` — best buy price on exchange A.
- `ask_B` — best sell price on exchange B.
- `fee_A`, `fee_B` — taker fees (in %).

**Primary metric** — `spread_net`. All thresholds, highlights, peaks, and statistics are based on it.

**Example.** BTC/USDT, bybit→binance:
- `bid_bybit = 63000`, `ask_binance = 63030`
- `spread_gross = (63000 − 63030) / 63030 × 100% = −0.0476%`
- Fees: `0.1% + 0.1% = 0.2%`
- `spread_net = −0.0476 − 0.2 = −0.2476%`

### Thresholds

| Purpose | Values | Where applied |
|---|---|---|
| Highlight | `0.3 / 0.8 / 1.5 / 2.0 %` | cell color in UI |
| Peaks and counters | `0.3 / 0.5 / 1.0 / 2.0 %` | peak open/close, `seconds_above_*` |

**Two independent sets.** Highlight "shouts" less often, peaks capture finer events. This is a deliberate decision: `0.8%` is already orange in UI, but `0.5%` is already a peak.

Highlight levels:

| Level | Condition | Color |
|---|---|---|
| Normal | `|net| < 0.3%` | no highlight |
| Noticeable | `0.3 ≤ |net| < 0.8` | yellow |
| Significant | `0.8 ≤ |net| < 1.5` | orange |
| Strong | `1.5 ≤ |net| < 2.0` | red |
| Extreme | `|net| ≥ 2.0` | dark red |

### Stale statuses

| Condition | Status | Behavior |
|---|---|---|
| Data < 5 sec | `ok` | normal operation |
| 5–30 sec | `stale` | spread calculated but marked |
| > 30 sec | `unavailable` | spread not calculated, aggregate not written |

### Peak detector

- **Opening:** `|spread_net| ≥ threshold` for the first time.
- **Closing:** `|spread_net| < threshold` for **3 consecutive seconds** (hysteresis).
- **Pause:** on data gap the peak is marked `is_paused = true`, hysteresis is not counted until data resumes.
- **Thresholds are independent:** peak at `1.0%` and peak at `2.0%` are different records. Peak at `0.3%` may close while peak at `1.0%` remains open.

**`duration_data_seconds`** — seconds when spread was **above threshold** (excluding hysteresis seconds).
**`duration_seconds`** — calendar duration including hysteresis seconds.

### Versioning

- **`threshold_version`** — when thresholds change (`thresholds_v1` → `thresholds_v2`), old aggregates don't mix with new ones.
- **`fee_version`** — same for fees. Format: `fees_<YYYY_MM>_<YYYY_MM>`.

### Per-second buffer

- 54 buffers (one per row).
- Each holds 3600 points (1 hour).
- Stores `spread_net` and `spread_gross` with timestamp.
- **In-memory**, not written to DB.
- **Lost on restart** — restored from minute aggregates with loss of per-second detail.
- First **5 minutes** (300 points) — "warm-up": per-second highlight and peak detector disabled, `/health` returns `buffer_ready: false`.

### Minute aggregation

Every minute per row:

- `spread_min`, `spread_max` — by sign.
- `spread_avg_abs` — average by modulus.
- `spread_avg_signed` — average by sign.
- `spread_last` — last value.
- `seconds_above_03 / 05 / 10 / 20` — seconds when `|spread_net|` was above threshold.
- `sample_count` — how many per-second points fell within the minute (norm 60).
- `partial` — `true` if `sample_count < 60`.
- `stale_level` — `ok` / `stale` / `unavailable`.

Write — **batched once per minute**. This reduces DB load by 60× compared to raw ticks.

---

## API

All endpoints are prefixed with `/api/v1/`. Full documentation — `http://localhost:8010/docs`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service status, buffers, versions |
| GET | `/spreads/current` | Current prices and spreads (54 rows) |
| GET | `/spreads/history` | Minute aggregate history |
| GET | `/peaks` | Peaks list with filters |
| GET | `/heatmap` | Heatmap by hour UTC |
| GET | `/fees` | Active exchange fees |
| POST | `/fees` | Update fee (new version) |
| GET | `/export` | Export aggregates to CSV / JSON |

### Main endpoint parameters

**`GET /spreads/history`**
- `pair` — required, e.g. `BTC/USDT`
- `exchange_pair` — required, `binance-bybit` / `binance-okx` / `bybit-okx`
- `direction` — required, `binance-bybit` (with dash)
- `from`, `to` — ISO 8601 UTC, default — 24 hours
- `interval` — `1m` (default) / `5m` / `15m` / `1h` / `1d`
- `metric` — `net` / `gross`

**`GET /peaks`**
- `pair`, `exchange_pair`, `direction` — optional
- `threshold` — `0.3` / `0.5` / `1.0` / `2.0`
- `from`, `to` — ISO 8601 UTC
- `limit`, `offset` — pagination

**`GET /heatmap`**
- `pair`, `exchange_pair`, `direction` — required
- `days` — days back (default 7, max 90)
- `tz` — `utc` (default) / `local`
- `metric` — `pct_above_03` / `avg_spread`

**`GET /export`**
- `pair`, `exchange_pair`, `direction` — required
- `from`, `to` — ISO 8601 UTC
- `format` — `csv` / `json`
- `metric` — `net` / `gross` / `both`

### Examples

```bash
# Current spreads
curl "http://localhost:8010/api/v1/spreads/current"

# BTC/USDT history, binance→okx, 24 hours, 5-minute interval
curl "http://localhost:8010/api/v1/spreads/history?pair=BTC/USDT&exchange_pair=binance-okx&direction=binance-okx&interval=5m"

# Peaks above 0.5% for 7 days
curl "http://localhost:8010/api/v1/peaks?threshold=0.5&from=2026-09-15T00:00:00Z"

# BTC/USDT heatmap binance→okx for 7 days
curl "http://localhost:8010/api/v1/heatmap?pair=BTC/USDT&exchange_pair=binance-okx&direction=binance-okx&days=7"

# Export to CSV
curl -O "http://localhost:8010/api/v1/export?pair=BTC/USDT&exchange_pair=binance-okx&direction=binance-okx&format=csv"
```

---

## Telegram notifications

Notifications come when the peak detector opens a peak with threshold `≥ TELEGRAM_MIN_THRESHOLD`.

**Setup:**

1. **Create a bot** via `@BotFather` in Telegram → get the token.
2. **Find your `chat_id`** via `@userinfobot`.
3. **Send `/start` to the bot** — otherwise Telegram won't allow it to message you.
4. **Add to `.env`:**

   ```
   TELEGRAM_BOT_TOKEN=<token>
   TELEGRAM_CHAT_ID=<chat_id>
   TELEGRAM_ENABLED=true
   TELEGRAM_MIN_THRESHOLD=0.5
   TELEGRAM_COOLDOWN_MINUTES=5
   ```

5. **Recreate the container:**

   ```bash
   docker compose up -d --force-recreate backend
   ```

6. **Verify:**

   ```bash
   docker compose exec backend python -c "import asyncio; from app.core.notifier import send_test; asyncio.run(send_test())"
   ```

**Cooldown:** after a notification for a row is sent — the next one not earlier than `TELEGRAM_COOLDOWN_MINUTES` minutes. Protection against spam during frequent peaks on the same row.

**Message format:**

```
⚠️ Peak on ADA/USDT
Direction: binance→okx
Threshold: 0.50%
Net: 0.5204%
Time (UTC): 2026-09-22 17:50:23
```

**What is NOT sent:** peak closing, spread change, fee change. Only opening — per spec, "simple notifications without events and escalation".

---

## Limitations

**What is NOT done and why:**

- **Automatic fee pulling from exchanges.** Binance, Bybit, OKX **have no public fee endpoints** — all require signed requests with a user's API key. Implemented **manual update via UI** with versioning through `effective_from`.

- **WebSocket from backend to frontend.** Currently polling every 5 seconds. Sufficient for observation; WS — planned for the next iteration.

- **Rate limiting.** Not implemented. For local run — not critical. In production — mandatory (REST 60 req/min per IP, WS 4 connections per IP).

**Deliberate decisions:**

- **Thresholds are fixed, not adaptive.** Calibration — future plan.
- **`fee_version` — monthly granularity.** Changes once a month. Sufficient for comparability.
- **Per-second buffer is lost on restart.** Restored from minute aggregates with loss of per-second detail.
- **All timestamps — UTC.** Heatmap — UTC. Local timezone toggle — future plan.

---

## Project structure

```
priceradar/
├── backend/                        # FastAPI
│   ├── app/
│   │   ├── api/                    # REST endpoints
│   │   │   ├── spreads.py          # /spreads/current
│   │   │   ├── history.py          # /spreads/history
│   │   │   ├── peaks.py            # /peaks
│   │   │   ├── heatmap.py          # /heatmap
│   │   │   ├── fees.py             # /fees
│   │   │   └── export.py           # /export
│   │   ├── collectors/             # WebSocket to exchanges
│   │   │   ├── base.py
│   │   │   ├── binance.py
│   │   │   ├── bybit.py
│   │   │   ├── okx.py
│   │   │   └── manager.py
│   │   ├── core/                   # core
│   │   │   ├── config.py           # settings from .env
│   │   │   ├── database.py         # SQLAlchemy
│   │   │   ├── ring_buffer.py      # per-second buffer
│   │   │   ├── buffer_manager.py   # 54 buffers
│   │   │   ├── spread_engine.py    # spread calculation
│   │   │   ├── tick_processor.py   # per-second recalculation
│   │   │   ├── aggregator.py       # minute aggregation
│   │   │   ├── peak_detector.py    # peak detector
│   │   │   ├── notifier.py         # Telegram
│   │   │   └── fees.py             # fee_version
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── exchange_fees.py
│   │   │   ├── spread_aggregates.py
│   │   │   ├── skipped_minutes.py
│   │   │   └── peaks.py
│   │   └── main.py                 # FastAPI + lifespan
│   ├── scripts/                    # diagnostic scripts
│   │   ├── check_aggregates.py
│   │   ├── check_peaks.py
│   │   └── check_gross.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                       # Laravel + Chart.js
│   ├── app/Http/Controllers/
│   │   ├── SpreadsController.php
│   │   ├── PeaksController.php
│   │   ├── HeatmapController.php
│   │   └── FeesController.php
│   ├── resources/views/
│   │   ├── layouts/app.blade.php
│   │   ├── spreads/index.blade.php
│   │   ├── spreads/history.blade.php
│   │   ├── peaks/index.blade.php
│   │   ├── heatmap/index.blade.php
│   │   └── fees/index.blade.php
│   ├── public/
│   │   ├── css/spreads.css
│   │   └── js/
│   │       ├── spreads.js
│   │       ├── history.js
│   │       ├── peaks.js
│   │       ├── heatmap.js
│   │       └── fees.js
│   ├── routes/web.php
│   ├── docker/nginx/default.conf
│   ├── Dockerfile
│   └── .env.example
│
├── docs/screenshots/               # screenshots for README
│   ├── 01-current.png
│   ├── 02-history.png
│   ├── 03-peaks.png
│   ├── 04-heatmap.png
│   ├── 05-telegram.png
│   └── 06-fees.png
│
├── docker-compose.yml              # 5 services
├── .env.example                    # backend config example
├── .gitignore
├── LICENSE
├── README.md                       # English (this file)
└── README.ru.md                    # Russian
```

---

## Author

- GitHub: [@ditlate0-spec](https://github.com/ditlate0-spec)
- Instagram: [@prod_23b](https://www.instagram.com/prod_23b/)

---

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** license.

**You are free to:**
- Share — copy and redistribute the material in any medium or format.
- Adapt — remix, transform, and build upon the material.

**Under the following terms:**
- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
- **NonCommercial** — You may **not use the material for commercial purposes**.
- **No additional restrictions** — You may not apply legal terms or technological measures that legally restrict others from doing anything the license permits.

**Full legal code:** https://creativecommons.org/licenses/by-nc/4.0/legalcode

**Human-readable summary:** https://creativecommons.org/licenses/by-nc/4.0/