# NEO_CONNECTOR -- WhalegodTG
- service: whalegod
- base_url_prod: UNKNOWN (self-hosted; no public domain in repo. Servers bind `0.0.0.0` -- health on `:8080`, Helius webhook receiver on `:${WEBHOOK_PORT}` default `:9876`. The user-set `WEBHOOK_HOST` is only the address handed TO Helius for its callbacks, not a Neo base URL.)
- auth: none (neither inbound HTTP server requires auth; the product surface is a Telegram bot, not an HTTP API)
- env_required: [TELEGRAM_BOT_TOKEN, HELIUS_API_KEY, ALCHEMY_API_KEY, ETHERSCAN_API_KEY, COINGECKO_API_KEY (optional), WEBHOOK_HOST (optional), WEBHOOK_PORT (optional, default 9876), ADMIN_CHAT_ID (optional), DB_PATH (optional)]
- generated_at:

> Machine-readable connection manifest for NeoBot. Everything below is proven from
> code -- do NOT edit by hand; regenerate via the Neo Connector audit (`/neo-connector`).
>
> **VERDICT: this repo should NOT be wired as Neo HTTP tools.** WhalegodTG is a
> Telegram bot + background poller. It is a CONSUMER of external HTTP APIs (Helius,
> Alchemy, Etherscan, DexScreener, Jupiter, CoinGecko), not a provider of one. The
> only two inbound HTTP endpoints it serves are an unauthenticated container health
> check and a Helius-specific webhook RECEIVER -- neither is a general-purpose API for
> Neo to call. All user-facing functionality is exposed exclusively through Telegram
> bot commands (long-polling via `Application.updater.start_polling`, see
> `bot/main.py`), which carry no programmatic HTTP surface. There is no REST/JSON API,
> no auth layer, no `generate -> poll -> result` job flow. If Neo needs whale data it
> should call the same upstreams directly (Helius/Alchemy), or interact with the bot
> over Telegram -- not over HTTP.

## Auth
- **none** on both inbound servers. `bot/main.py` builds two bare `aiohttp.web.Application`
  instances with no middleware, no token check, no signature verification.
  - `GET /health` (port 8080) -- open.
  - `POST /webhook/helius` (port `WEBHOOK_PORT`) -- open; it trusts any caller posting
    Helius-shaped JSON. There is no shared-secret / signature check on the webhook
    (Helius enhanced webhooks registered here send none -- see `register_webhook` payload
    in `bot/chains/solana.py`, which sets no `authHeader`).
- The Telegram side authenticates via `TELEGRAM_BOT_TOKEN` to Telegram's servers
  (outbound); `ADMIN_CHAT_ID` gates the admin-only `/stats` command menu and startup
  notifications. None of this is reachable as an HTTP endpoint.

## Endpoints
Inbound HTTP servers, both defined in `bot/main.py`.

### GET /health  (port 8080, `HEALTH_PORT`, hardcoded in `bot/config.py`)
- auth: none
- async: false
- input: none
- output: JSON
  `{status:"ok", bot:"WHALEGOD", version:str, uptime_seconds:int, chains:{solana:{status:"ok", last_event:str}, ethereum:{status:"ok", last_block:int|None, last_poll:str}}}`
  (`last_event`/`last_poll` are `"N/A"` until first event; `last_block` from `bot.chains.ethereum.get_last_polled_block`)
- errors: none (always 200 unless server down)
- example_curl: `curl http://localhost:8080/health`
- notes: used by Docker/compose healthcheck (`curl -f http://localhost:8080/health`)
  and `deploy.sh` status. Port is NOT configurable (constant `HEALTH_PORT=8080`). Exposed
  in docker-compose as `"8080:8080"`.

### POST /webhook/helius  (port `WEBHOOK_PORT`, default 9876, from env)
- auth: none (no signature/secret verification)
- async: false at the HTTP layer (returns 200 immediately), but it SPAWNS background
  processing -- `asyncio.create_task(_safe_process_event(...))` per event -> alerts are
  delivered to Telegram out-of-band, not in the HTTP response.
- input: Helius enhanced-transaction webhook payload. Body is a JSON array of event
  objects (a single object is also accepted and wrapped in a list). Each event must
  contain a `signature` field or it is skipped. Fields consumed by the parser
  (`parse_helius_event` in `bot/chains/solana.py`): `signature`, `type`, `feePayer`,
  `nativeTransfers[]`, `tokenTransfers[]`, `accountData[]`, `instructions[]`.
- output: `text/plain` -- `"OK"` (200). `400 "Invalid JSON"` on unparseable body;
  `503 "Not ready"` if bot/session not initialised yet.
- errors: 400 (invalid JSON), 503 (not ready). Per-event parse failures are caught and
  logged, never surfaced in the response.
- example_curl:
  `curl -X POST http://localhost:9876/webhook/helius -H 'Content-Type: application/json' -d '[{"signature":"<sig>","type":"TRANSFER","nativeTransfers":[{"fromUserAccount":"A","toUserAccount":"B","amount":600000000000}]}]'`
- notes: this is a callback SINK for Helius, not an API Neo should call. The bot
  auto-registers this URL with Helius on startup (`register_webhook`) only if
  `WEBHOOK_HOST` is set, building `http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook/helius`
  (plain HTTP, port must be publicly reachable). Exposed in docker-compose as
  `"${WEBHOOK_PORT:-9876}:${WEBHOOK_PORT:-9876}"`.

## Telegram command surface (NOT HTTP -- for reference only)
Registered in `bot/main.py` via `CommandHandler`; handlers in `bot/handlers/commands.py`.
These are reachable ONLY through Telegram (long-polling), never over HTTP:
`/start`, `/whale [sol|eth]`, `/top [24h|1h|7d]`, `/track <address> [label]`,
`/untrack <address>`, `/watchlist`, `/scan <token>`, `/trending`, `/settings`,
`/chains`, `/gas`, `/stats` (admin), `/donate`, `/help`. Inline settings buttons via a
`CallbackQueryHandler` on pattern `^settings:` (`bot/handlers/callbacks.py`).

## Outbound integrations (this bot CALLS these -- Neo could call them directly instead)
Proven from `bot/config.py` + `bot/chains/*`:
- **Helius** -- `https://api.helius.xyz/v0` (webhooks mgmt, `/addresses/{addr}/transactions`,
  `/transactions`) and `https://mainnet.helius-rpc.com` (RPC: `getPriorityFeeEstimate`,
  `getRecentPrioritizationFees`). Auth: `?api-key=HELIUS_API_KEY`.
- **Alchemy** -- `https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}` (ETH RPC polling).
- **Etherscan** -- `https://api.etherscan.io/api` (gas/blocks), `?apikey=ETHERSCAN_API_KEY`.
- **DexScreener / Jupiter / CoinGecko** -- price enrichment/fallback (see `bot/services/price_service.py`).
- **Telegram Bot API** -- via `python-telegram-bot`, token `TELEGRAM_BOT_TOKEN`.

## Background / scheduled work (APScheduler, `bot/main.py setup_scheduler`)
Internal cron-like jobs (no HTTP trigger):
- `poll_ethereum` -- interval 60s (Alchemy ETH block scan)
- `check_tracked_wallets` -- interval 5min (Helius wallet history)
- `price_service.refresh_base_prices` -- interval 60s
- `cleanup` -- daily 03:00 UTC (DB)
- `backup_db` -- daily 04:00 UTC
- `_log_health` -- interval 5min (log only)

## Flows
- **Solana real-time alert (push):** Helius -> `POST /webhook/helius` -> 200 OK (sync) +
  `asyncio.create_task` -> `alert_engine.process_helius_event` (parse -> enrich price ->
  classify -> dedup -> format) -> Telegram message to subscribed chats. No polling, no
  job id; alert is fire-and-forget to Telegram.
- **Ethereum alert (pull):** APScheduler every 60s -> `alert_engine.poll_ethereum` ->
  Alchemy RPC -> same enrich/classify/format -> Telegram.
- **Tracked wallets:** APScheduler every 5min -> `alert_engine.check_tracked_wallets`.
- There is NO `POST /generate -> GET /status/{id} -> GET /result/{id}` async HTTP flow.

## Gaps
- **base_url_prod: UNKNOWN** -- no public domain anywhere in repo (README, deploy.sh,
  docker-compose, CLAUDE.md). Self-hosted on an arbitrary VPS; reachability of
  `/webhook/helius` depends entirely on operator-set `WEBHOOK_HOST` + open firewall port.
- **Webhook authenticity: UNVERIFIED by design** -- `POST /webhook/helius` has no
  signature/secret. Anyone who reaches the port can inject fake events. Confirm in
  `bot/services/alert_engine.py` whether any downstream guard exists (not in audit scope
  here) -- file: `bot/services/alert_engine.py`.
- **/health port not configurable** -- hardcoded `HEALTH_PORT = 8080` in `bot/config.py`.
- Detailed alert-pipeline behaviour (dedup cache size, classifier logic, formatting) lives
  in `bot/services/alert_engine.py`, `bot/services/label_service.py`,
  `bot/utils/formatter.py` -- not part of any HTTP contract, not audited line-by-line here.

## Recap
- Inbound HTTP endpoints found: **2** (`GET /health`, `POST /webhook/helius`).
- Usable as Neo HTTP tools: **0**. One is an internal health probe; the other is a Helius
  callback sink. Neither is a programmable API for Neo.
- New vs already-covered: n/a -- this service should NOT be wired into NeoBot's HTTP tool
  surface. Whale data, if needed, comes from calling Helius/Alchemy directly or via the
  Telegram bot.
