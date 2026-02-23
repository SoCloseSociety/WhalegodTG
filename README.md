<p align="center">
  <img src="assets/banner.svg" alt="WHALEGOD" width="900">
</p>

<p align="center">
  <strong>On-chain whale tracker for Solana & Ethereum — wen whale moves, we move first ser.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-575ECF?style=flat-square" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11%2B-575ECF?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+"></a>
  <img src="https://img.shields.io/badge/Chains-Solana%20%7C%20Ethereum-575ECF?style=flat-square" alt="Chains">
  <img src="https://img.shields.io/badge/API%20Cost-$0-575ECF?style=flat-square" alt="$0 API Cost">
  <a href="https://github.com/SoCloseSociety/WhalegodTG/stargazers"><img src="https://img.shields.io/github/stars/SoCloseSociety/WhalegodTG?style=flat-square&color=575ECF" alt="Stars"></a>
  <a href="https://github.com/SoCloseSociety/WhalegodTG/issues"><img src="https://img.shields.io/github/issues/SoCloseSociety/WhalegodTG?style=flat-square&color=575ECF" alt="Issues"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#key-features">Features</a> &bull;
  <a href="#bot-commands">Commands</a> &bull;
  <a href="#faq">FAQ</a> &bull;
  <a href="#contributing">Contributing</a>
</p>

---

## What is WHALEGOD?

**WHALEGOD** is a free, open-source Telegram bot that tracks whale movements on Solana and Ethereum in real-time. It classifies transactions into 14 categories (CEX flows, DEX swaps, LP events, bridge transfers, memecoin launches, smart money moves, MEV...), enriches them with price data, and delivers formatted alerts to your Telegram group.

Zero API cost — runs entirely on free tiers (Helius, Alchemy, Etherscan, DexScreener).

### Who is this for?

- **Crypto Traders** who want to front-run whale moves
- **DeFi Degens** tracking smart money and LP activity
- **Trading Groups** looking for a whale alert bot
- **Memecoin Traders** catching early Pump.fun launches
- **Developers** learning async Python + blockchain APIs

### Key Features

- **Multi-Chain** — Solana (Helius webhooks) + Ethereum (Alchemy RPC)
- **Real-Time** — Solana via push webhooks, ETH via 60s block polling
- **14 Transaction Categories** — CEX, DEX, LP, Bridge, Memecoin, Smart Money, MEV...
- **Smart Classification** — Bullish/bearish/neutral/degen/alpha signals
- **50+ Wallet Labels** — Known exchanges, bridges, protocols auto-identified
- **Customizable Thresholds** — Per-chat SOL/ETH/USD/LP minimums
- **Wallet Tracking** — Track up to 10 custom wallets per user
- **Anti-Flood** — Automatic digest mode during whale storms (>20 events/min)
- **Deduplication** — 2000-tx cache prevents duplicate alerts
- **Rate Limiting** — Per-API semaphores for safe usage
- **Price Caching** — Multi-source with fallback (Jupiter → DexScreener → CoinGecko)
- **Docker Ready** — One-command deployment with health checks
- **$0 API Cost** — Runs on free tiers only
- **Free & Open Source** — MIT license

---

## Quick Start

### With Docker (recommended)

```bash
git clone https://github.com/SoCloseSociety/WhalegodTG.git
cd WhalegodTG
cp .env.example .env
# Edit .env with your API keys
docker compose up -d
```

### Manual

```bash
git clone https://github.com/SoCloseSociety/WhalegodTG.git
cd WhalegodTG
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python -m bot
```

### Free API Keys

| Service | Sign Up | Free Tier |
|---------|---------|-----------|
| **Telegram** | [@BotFather](https://t.me/BotFather) | Unlimited |
| **Helius** | [helius.dev](https://helius.dev) | 1M credits/month |
| **Alchemy** | [alchemy.com](https://alchemy.com) | 300M compute units/month |
| **Etherscan** | [etherscan.io](https://etherscan.io/apis) | 5 req/sec |

---

## How It Works

```
Solana (Helius Webhook)     Ethereum (Alchemy RPC)
         │                           │
         └───────────┬───────────────┘
                     ▼
         ┌───────────────────────┐
         │    Alert Engine       │
         │                      │
         │  Parse → Enrich →    │
         │  Classify → Dedup →  │
         │  Log → Format → Send │
         └───────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Telegram Groups     │
         │   (formatted alerts)  │
         └───────────────────────┘
```

### Transaction Categories

| Category | Signal | Example |
|----------|--------|---------|
| CEX Deposit | Bearish | Whale sends 500 SOL to Binance |
| CEX Withdrawal | Bullish | 1000 ETH withdrawn from Coinbase |
| DEX Swap | Varies | Large swap on Jupiter/Uniswap |
| LP Add | Bullish | New liquidity added to pool |
| LP Remove | Bearish | Liquidity pulled from pool |
| Bridge Transfer | Neutral | Cross-chain move |
| Memecoin Launch | Degen | New Pump.fun token |
| Smart Money | Alpha | VC/fund wallet moves |
| MEV Activity | Caution | Sandwich attack detected |
| Accumulation | Bullish | Repeated buys over time |
| Distribution | Bearish | Systematic selling |

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Subscribe to whale alerts |
| `/whale [sol\|eth]` | Recent whale movements |
| `/top [24h\|1h\|7d]` | Top moves by volume |
| `/track <address> [label]` | Track a wallet |
| `/untrack <address>` | Stop tracking |
| `/watchlist` | View tracked wallets |
| `/scan <token>` | Token analysis |
| `/trending` | Trending tokens |
| `/chains` | Chain status & prices |
| `/gas` | ETH gas + SOL fees |
| `/settings` | Configure thresholds |
| `/stats` | Bot statistics |
| `/help` | Full command reference |

---

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | Yes |
| `HELIUS_API_KEY` | Solana RPC + webhooks | Yes |
| `ALCHEMY_API_KEY` | Ethereum RPC | Yes |
| `ETHERSCAN_API_KEY` | Block data & gas | Yes |
| `COINGECKO_API_KEY` | Price fallback | Optional |
| `WEBHOOK_HOST` | Public URL for Helius webhooks | Optional |
| `DEFAULT_SOL_THRESHOLD` | Min SOL for alerts (default: 500) | No |
| `DEFAULT_ETH_THRESHOLD` | Min ETH for alerts (default: 50) | No |
| `DEFAULT_USD_THRESHOLD` | Min USD for alerts (default: 50000) | No |

---

## Project Structure

```
WhalegodTG/
├── bot/
│   ├── main.py              # Entry point & event loop
│   ├── config.py            # Environment & constants
│   ├── database.py          # SQLite schema & queries
│   ├── chains/
│   │   ├── solana.py        # Helius integration
│   │   └── ethereum.py      # Alchemy/Etherscan integration
│   ├── handlers/
│   │   ├── commands.py      # Bot commands
│   │   └── callbacks.py     # Inline button callbacks
│   ├── services/
│   │   ├── alert_engine.py  # Core pipeline
│   │   ├── price_service.py # Token prices & caching
│   │   └── label_service.py # Wallet identification
│   └── utils/
│       ├── formatter.py     # Message formatting
│       ├── rate_limiter.py  # API rate limiting
│       ├── retry.py         # Retry logic
│       └── whale_quotes.py  # 100+ meme quotes
├── Dockerfile
├── docker-compose.yml
├── deploy.sh
└── requirements.txt
```

---

## Troubleshooting

### Bot doesn't start

1. Check `.env` — all required keys must be set
2. Verify Python 3.11+ with `python --version`
3. For Docker: check `docker compose logs whalegod`

### No Solana alerts

1. Verify `HELIUS_API_KEY` is valid at helius.dev dashboard
2. Check that `WEBHOOK_HOST` is publicly accessible (for webhooks)
3. Bot logs webhook registration status on startup

### No Ethereum alerts

1. Verify `ALCHEMY_API_KEY` and `ETHERSCAN_API_KEY`
2. ETH polling runs every 60s — wait at least 2 minutes
3. Check thresholds — default is 50 ETH minimum

---

## FAQ

**Q: Is this free?**
A: Yes. Bot is free, all APIs have free tiers. Total cost: $0.

**Q: Do I need a VPS?**
A: For Solana webhooks, you need a public URL. Docker on a $4/month VPS works perfectly.

**Q: Can I track other chains?**
A: Currently Solana + Ethereum. Adding new chains requires implementing a new chain module in `bot/chains/`.

**Q: How fast are the alerts?**
A: Solana: instant (webhooks). Ethereum: ~60 seconds (polling).

---

## Alternatives Comparison

| Feature | WHALEGOD | Whale Alert | Nansen | Arkham |
|---------|----------|-------------|--------|--------|
| Price | **Free** | Freemium | $150/mo | $50/mo |
| Solana | Yes | No | Yes | Yes |
| Ethereum | Yes | Yes | Yes | Yes |
| Telegram bot | Yes | Yes | No | No |
| Self-hosted | Yes | No | No | No |
| Open source | Yes | No | No | No |
| Customizable | Fully | No | Limited | Limited |

---

## Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) before submitting a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Disclaimer

This tool is provided for **educational and informational purposes only**. It does not constitute financial advice. On-chain data may be delayed or incomplete. The authors are not responsible for trading decisions made based on the bot's alerts.

---

<p align="center">
  <strong>If this project helps you, please give it a star!</strong><br>
  <a href="https://github.com/SoCloseSociety/WhalegodTG">
    <img src="https://img.shields.io/github/stars/SoCloseSociety/WhalegodTG?style=for-the-badge&logo=github&color=575ECF" alt="Star this repo">
  </a>
</p>

<br>

<p align="center">
  <sub>Built with purpose by <a href="https://soclose.co"><strong>SoClose</strong></a> &mdash; Digital Innovation Through Automation & AI</sub><br>
  <sub>
    <a href="https://soclose.co">Website</a> &bull;
    <a href="https://linkedin.com/company/soclose-agency">LinkedIn</a> &bull;
    <a href="https://twitter.com/SoCloseAgency">Twitter</a> &bull;
    <a href="mailto:contact@soclose.co">Contact</a>
  </sub>
</p>
