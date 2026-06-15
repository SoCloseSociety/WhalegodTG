# CLAUDE.md -- WhalegodTG

## 1. Project Identity

**Name:** WhalegodTG -- On-Chain Whale Transaction Tracker
**Role:** Telegram bot that monitors large transactions (whale movements) on Solana and Ethereum in real-time, classifying them into 14 categories with 50+ labeled wallet addresses.
**Author:** SoClose Society (https://soclose.co)
**License:** MIT

### Stack

- **Language:** Python 3.11+
- **Bot Framework:** python-telegram-bot
- **Blockchain (Solana):** Helius webhooks + RPC
- **Blockchain (Ethereum):** Alchemy RPC
- **Data Sources:** Etherscan API (free tier)
- **Async:** asyncio
- **Deployment:** Docker + Docker Compose

### Architecture Overview

```
bot.py (entry point)
├── handlers/           Telegram command handlers
├── trackers/
│   ├── solana.py       Helius webhook listener + transaction parser
│   └── ethereum.py     Alchemy RPC polling + transaction parser
├── classifiers/        14 transaction category classifiers
├── labels/             50+ known wallet labels (exchanges, bridges, protocols)
├── anti_flood/         Digest mode (>20 events/min), message batching
├── models/             Data models for transactions
├── utils/              Formatting, helpers
└── config.py           Environment configuration
```

### External Services

| Service       | Cost  | Notes                              |
| ------------- | ----- | ---------------------------------- |
| Helius        | Free  | Webhooks + RPC (100k credits/day)  |
| Alchemy       | Free  | Ethereum RPC (free tier)           |
| Etherscan     | Free  | Wallet labels + contract info      |
| Telegram Bot  | Free  | Bot API                            |

### Critical Files -- Do Not Touch Without a Plan

- `trackers/solana.py` -- Helius webhook integration, transaction parsing
- `trackers/ethereum.py` -- Alchemy RPC polling logic
- `classifiers/` -- 14 transaction category definitions
- `labels/` -- 50+ known wallet mappings (exchanges, bridges)
- `anti_flood/` -- Digest mode threshold (>20 events/min)
- `config.py` -- All environment variable mappings

## 2. Workflow Orchestration

- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Transaction classification is chain-specific -- test Solana and Ethereum separately
- Anti-flood thresholds are hardcoded -- any change requires load testing
- After any correction from user: update `tasks/lessons.md`

## 3. Verification Before Done

- Never mark a task complete without proving it works
- Test with known whale wallet addresses on both chains
- Verify anti-flood digest mode activates at threshold
- Check wallet label resolution works for major exchanges
- Confirm Helius webhook receives and parses transactions correctly

## 4. Autonomous Bug Fixing

- When given a bug report: fix it, no hand-holding
- Check Helius webhook endpoint is accessible (requires public URL)
- Verify Alchemy RPC endpoint is responding
- Check Etherscan API rate limits (5 calls/sec on free tier)
- Zero context switching required from the user

## 5. Task Management

1. Plan First: write plan to `tasks/todo.md` with checkable items
2. Verify Plan: check in before starting implementation
3. Track Progress: mark items complete as you go
4. Explain Changes: high-level summary at each step
5. Document Results: add review section to `tasks/todo.md`
6. Capture Lessons: update `tasks/lessons.md` after corrections

## 6. Project-Specific Rules

### Naming Conventions
- Files: snake_case
- Classes: PascalCase
- Functions: snake_case
- Constants: UPPER_SNAKE_CASE

### Dev Commands
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in keys

python bot.py          # Run locally

# Docker
docker-compose up -d
docker-compose logs -f
```

### Environment Variables
- TELEGRAM_BOT_TOKEN -- Bot token from @BotFather
- HELIUS_API_KEY -- Helius API (webhooks + RPC)
- ALCHEMY_API_KEY -- Alchemy Ethereum RPC
- ETHERSCAN_API_KEY -- Etherscan wallet labels

### Known Fragile Areas
- Anti-flood threshold (>20 events/min) is hardcoded -- no config
- Helius webhooks require a public URL (use ngrok for local dev)
- Wallet labels are static -- new exchanges/bridges need manual addition
- Etherscan free tier: 5 calls/sec limit

## 7. Core Principles

- Simplicity First: make every change as simple as possible
- No Laziness: find root causes, no temporary fixes
- Minimal Impact: changes should only touch what's necessary
- Never use em dashes in any output (use -- instead)
- Ollama-first for any local LLM calls (RTX 4070 available)
- Zero-cost priority: all APIs must have free tier alternatives
- Anti-flood integrity: never disable digest mode without load testing

## Neo Connector (auto)
Ce projet expose `NEO_CONNECTOR.md` : le manifeste machine-lisible de TOUS ses
endpoints/auth/env, consommé par NeoBot pour se câbler automatiquement.
- NOTE WhalegodTG : ce repo est un bot Telegram + poller, PAS un fournisseur d'API HTTP.
  Les 2 seuls serveurs entrants sont un health-check et un RÉCEPTEUR de webhook Helius.
  Le manifeste documente ce fait et indique qu'il ne doit PAS être branché comme tool HTTP Neo.
- RÈGLE : à chaque ajout/suppression/modif d'un endpoint, d'une auth ou d'une env var,
  régénère le manifeste via `/neo-connector` (ou le prompt dans .claude/skills/neo-connector).
- Ne jamais éditer NEO_CONNECTOR.md à la main : il est généré.
- Le hook pre-commit (.git/hooks/pre-commit) avertit si des routes ont changé sans MAJ du manifeste.
