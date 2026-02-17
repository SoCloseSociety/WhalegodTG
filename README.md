# WHALEGOD 🐋

**wen whale moves, we move first ser.**

![Chains](https://img.shields.io/badge/chains-Solana%20%7C%20Ethereum-blue)
![Cost](https://img.shields.io/badge/API%20cost-%240-brightgreen)
![Vibe](https://img.shields.io/badge/vibe-based-purple)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

The most based on-chain whale movement tracker for Solana and Ethereum. Real-time alerts, zero BS, pure alpha. All data fetched live from free APIs — zero hardcoded data, zero stubs.

---

## Features

- **Real-time Whale Alerts** — Solana via Helius webhooks, Ethereum via block polling
- **Multi-chain** — Solana (SOL) + Ethereum (ETH) tracked simultaneously
- **Smart Classification** — CEX deposits/withdrawals, DEX swaps, LP events, bridges, wallet transfers
- **Bullish/Bearish Signals** — Each whale movement classified with market signal
- **Known Wallet Labels** — 50+ exchanges, bridges, DEXs, and protocols identified
- **Customizable Thresholds** — Per-chat settings for SOL/ETH/USD/LP minimums
- **Category Filters** — Toggle CEX, DEX, LP, bridge alerts independently
- **Wallet Tracking** — Stalk up to 10 wallets per user with notifications
- **Token Scanner** — Scan any token for price, volume, liquidity, and links
- **Trending Tokens** — DexScreener boosted/trending tokens feed
- **Gas Tracker** — ETH gas prices + SOL priority fees
- **Anti-Flood Protection** — Automatic digest mode during whale storms
- **Smart Links** — Every alert includes explorer, chart, analysis, and swap links
- **Degen Commentary** — 100+ randomized whale quotes in full memecoin culture
- **Docker Deployable** — Single command deploy with health checks
- **$0 API Costs** — All free-tier APIs, no credit card required

---

## Supported Chains

| Chain | Data Sources | Method | Cost |
|-------|-------------|--------|------|
| **Solana** | Helius, DexScreener, Jupiter | Webhooks + polling | $0 |
| **Ethereum** | Alchemy, Etherscan, DexScreener | Block polling (60s) | $0 |

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message + auto-subscribe |
| `/whale [sol\|eth]` | Recent whale movements |
| `/top [24h\|1h\|7d]` | Biggest moves by volume |
| `/track <address> [label]` | Track a wallet |
| `/untrack <address>` | Stop tracking a wallet |
| `/watchlist` | Your tracked wallets |
| `/scan <token>` | Scan a token (price, volume, liquidity) |
| `/trending` | Trending/boosted tokens |
| `/chains` | Chain status + live prices |
| `/gas` | ETH gas + SOL priority fees |
| `/settings` | Alert preferences (inline keyboard) |
| `/stats` | Bot statistics |
| `/donate` | Support WHALEGOD |
| `/help` | Full command reference |

---

## Architecture

```
                    ┌─────────────────┐
                    │   Telegram Bot   │
                    │   (Commands)     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──────┐  ┌───▼────┐  ┌──────▼───────┐
    │ Helius Webhook  │  │ Alchemy │  │  Etherscan   │
    │ (Solana events) │  │  (RPC)  │  │  (ETH data)  │
    └─────────┬──────┘  └───┬────┘  └──────┬───────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │  Alert Engine    │
                    │  (Core Pipeline) │
                    │                  │
                    │ Parse → Enrich → │
                    │ Classify → Label │
                    │ → Dedup → Log → │
                    │ Format → Send    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
    │ Price Service   │ │  Label   │ │   SQLite    │
    │ Jupiter/DexScr  │ │ Service  │ │  Database   │
    │ /CoinGecko     │ │          │ │  (WAL mode) │
    └────────────────┘ └──────────┘ └─────────────┘
```

---

## Quick Deploy

### 1. Clone

```bash
git clone https://github.com/your-repo/whalegod-bot.git
cd whalegod-bot
```

### 2. Configure

```bash
cp .env.example .env
nano .env  # Add your API keys
```

### 3. Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

That's it ser. WHALEGOD is live. LFG 🚀

---

## Manual Docker Commands

```bash
# Build
docker compose build

# Start
docker compose up -d

# Logs
docker compose logs -f whalegod

# Restart
docker compose restart whalegod

# Stop
docker compose down

# Health check
curl http://localhost:8080/health
```

---

## API Keys Setup

All APIs are **free tier** — no credit card required.

| Service | Get Key At | Free Tier |
|---------|-----------|-----------|
| **Telegram Bot** | [@BotFather](https://t.me/BotFather) | Unlimited |
| **Helius** | [helius.dev](https://helius.dev) | 1M credits/month |
| **Alchemy** | [alchemy.com](https://www.alchemy.com) | 300M compute units/month |
| **Etherscan** | [etherscan.io/apis](https://etherscan.io/apis) | 5 req/sec |
| **CoinGecko** (optional) | [coingecko.com/en/api](https://www.coingecko.com/en/api) | 30 req/min |

### Steps:
1. **Telegram**: Message @BotFather, create bot, get token
2. **Helius**: Sign up, create project, copy API key
3. **Alchemy**: Sign up, create Ethereum Mainnet app, copy API key
4. **Etherscan**: Sign up, go to API Keys, create new key
5. **CoinGecko** (optional): Sign up for demo API, get key

---

## Alert Links Reference

### Solana Alerts Include:
| Link | Destination |
|------|------------|
| Transaction | solscan.io/tx/... |
| Wallet | solscan.io/account/... |
| Chart | dexscreener.com/solana/... |
| Analysis | birdeye.so/token/... |
| Rugcheck | rugcheck.xyz/tokens/... |
| Swap | jup.ag/swap/... |

### Ethereum Alerts Include:
| Link | Destination |
|------|------------|
| Transaction | etherscan.io/tx/... |
| Wallet | etherscan.io/address/... |
| Chart | dexscreener.com/ethereum/... |
| Analysis | dextools.io/... |
| Swap | app.uniswap.org/swap/... |

---

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Telegram bot token |
| `HELIUS_API_KEY` | Yes | — | Helius API key (Solana) |
| `ALCHEMY_API_KEY` | Yes | — | Alchemy API key (Ethereum) |
| `ETHERSCAN_API_KEY` | Yes | — | Etherscan API key |
| `COINGECKO_API_KEY` | No | — | CoinGecko demo API key |
| `WEBHOOK_HOST` | No | — | VPS IP/domain for Helius webhooks |
| `WEBHOOK_PORT` | No | 9876 | Webhook listener port |
| `DEFAULT_SOL_THRESHOLD` | No | 500 | Min SOL for alerts |
| `DEFAULT_ETH_THRESHOLD` | No | 50 | Min ETH for alerts |
| `DEFAULT_USD_THRESHOLD` | No | 50000 | Min USD for alerts |
| `DEFAULT_LP_THRESHOLD` | No | 25000 | Min USD for LP alerts |
| `DB_PATH` | No | /app/data/whalegod.db | SQLite database path |
| `LOG_RETENTION_DAYS` | No | 7 | Days to keep whale logs |
| `MAX_WALLETS_PER_USER` | No | 10 | Max tracked wallets per user |
| `FLOOD_THRESHOLD` | No | 20 | Events/min to trigger digest mode |
| `FLOOD_WINDOW_SECONDS` | No | 60 | Flood detection window |
| `ADMIN_CHAT_ID` | No | — | Admin chat for startup notifications |
| `DONATE_SOL` | No | — | SOL donation address |
| `DONATE_ETH` | No | — | ETH donation address |
| `DONATE_BTC` | No | — | BTC donation address |
| `DONATE_USDT_TRC20` | No | — | USDT TRC-20 donation address |

---

## Donation

If WHALEGOD helps you catch alpha, consider supporting the project:

Set your donation addresses in `.env` and users can see them via `/donate`.

the WHALEGOD remembers those who donate 👑🐋

---

## License

MIT License. ser, it's free. like our API costs. wagmi 🐋

---

*built by degens, for degens. wen whale moves, we move first ser.* 🐋🔥
