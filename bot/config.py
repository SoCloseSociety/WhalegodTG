"""All environment variables, constants, and rate limit configurations."""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("whalegod")

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
try:
    _admin_raw = os.getenv("ADMIN_CHAT_ID", "")
    ADMIN_CHAT_ID: int | None = int(_admin_raw) if _admin_raw.strip() else None
except ValueError:
    ADMIN_CHAT_ID = None

# ---------------------------------------------------------------------------
# Solana APIs
# ---------------------------------------------------------------------------
HELIUS_API_KEY: str = os.getenv("HELIUS_API_KEY", "")
HELIUS_BASE_URL: str = "https://api.helius.xyz/v0"

# ---------------------------------------------------------------------------
# Ethereum APIs
# ---------------------------------------------------------------------------
ALCHEMY_API_KEY: str = os.getenv("ALCHEMY_API_KEY", "")
ALCHEMY_RPC_URL: str = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
ETHERSCAN_API_KEY: str = os.getenv("ETHERSCAN_API_KEY", "")
ETHERSCAN_BASE_URL: str = "https://api.etherscan.io/api"

# ---------------------------------------------------------------------------
# Price fallback
# ---------------------------------------------------------------------------
COINGECKO_API_KEY: str = os.getenv("COINGECKO_API_KEY", "")

# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------
WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "9876"))
HEALTH_PORT: int = 8080

# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------
DEFAULT_SOL_THRESHOLD: float = float(os.getenv("DEFAULT_SOL_THRESHOLD", "500"))
DEFAULT_ETH_THRESHOLD: float = float(os.getenv("DEFAULT_ETH_THRESHOLD", "50"))
DEFAULT_USD_THRESHOLD: float = float(os.getenv("DEFAULT_USD_THRESHOLD", "50000"))
DEFAULT_LP_THRESHOLD: float = float(os.getenv("DEFAULT_LP_THRESHOLD", "25000"))

# ---------------------------------------------------------------------------
# Donation wallets
# ---------------------------------------------------------------------------
DONATE_SOL: str = os.getenv("DONATE_SOL", "")
DONATE_ETH: str = os.getenv("DONATE_ETH", "")
DONATE_BTC: str = os.getenv("DONATE_BTC", "")
DONATE_USDT_TRC20: str = os.getenv("DONATE_USDT_TRC20", "")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH: str = os.getenv("DB_PATH", "data/whalegod.db")

# ---------------------------------------------------------------------------
# Operational
# ---------------------------------------------------------------------------
LOG_RETENTION_DAYS: int = int(os.getenv("LOG_RETENTION_DAYS", "7"))
MAX_WALLETS_PER_USER: int = int(os.getenv("MAX_WALLETS_PER_USER", "10"))
FLOOD_THRESHOLD: int = int(os.getenv("FLOOD_THRESHOLD", "20"))
FLOOD_WINDOW_SECONDS: int = int(os.getenv("FLOOD_WINDOW_SECONDS", "60"))

# ---------------------------------------------------------------------------
# Well-known token mints / addresses
# ---------------------------------------------------------------------------
SOL_MINT: str = "So11111111111111111111111111111111111111112"
WETH_ADDRESS: str = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

# ---------------------------------------------------------------------------
# Price cache TTLs (seconds)
# ---------------------------------------------------------------------------
PRICE_TTL_ACTIVE: int = 30
PRICE_TTL_STABLECOIN: int = 300
PRICE_TTL_BASE: int = 15  # SOL / ETH

# ---------------------------------------------------------------------------
# Well-known stablecoin addresses
# ---------------------------------------------------------------------------
STABLECOINS: set[str] = {
    # Solana
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    # Ethereum
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
    "0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI
}

# ---------------------------------------------------------------------------
# Transaction categories
# ---------------------------------------------------------------------------
TX_CATEGORIES: dict[str, dict[str, str]] = {
    "cex_deposit":      {"emoji": "🏦⬆️", "label": "CEX Deposit",        "signal": "bearish",  "desc": "whale moving to exchange — possible sell incoming"},
    "cex_withdrawal":   {"emoji": "🏦⬇️", "label": "CEX Withdrawal",     "signal": "bullish",  "desc": "whale pulling off exchange — accumulation vibes"},
    "wallet_transfer":  {"emoji": "💸",    "label": "Wallet Transfer",    "signal": "neutral",  "desc": "whale-to-whale — big bags moving"},
    "dex_swap":         {"emoji": "🔄",    "label": "DEX Swap",           "signal": "neutral",  "desc": "whale swapping on DEX"},
    "lp_add":           {"emoji": "💧➕",  "label": "LP Add",             "signal": "bullish",  "desc": "fresh liquidity — somebody's committing"},
    "lp_remove":        {"emoji": "💧➖",  "label": "LP Remove",          "signal": "bearish",  "desc": "liquidity leaving — stay alert"},
    "bridge":           {"emoji": "🌉",    "label": "Bridge Transfer",    "signal": "neutral",  "desc": "cross-chain movement detected"},
    "memecoin_launch":  {"emoji": "🐸🚀", "label": "Memecoin Launch",    "signal": "degen",    "desc": "Pump.fun / memecoin launch or early buy"},
    "smart_money_move": {"emoji": "🧠💰", "label": "Smart Money Move",   "signal": "alpha",    "desc": "VC/fund/market maker moving — follow the alpha"},
    "mev_activity":     {"emoji": "🤖🥪", "label": "MEV Activity",       "signal": "caution",  "desc": "MEV bot or sandwich attack detected"},
    "trading_bot":      {"emoji": "🤖🎯", "label": "Trading Bot",        "signal": "neutral",  "desc": "automated trading bot activity (Banana Gun, Maestro)"},
    "accumulation":     {"emoji": "🟢📈", "label": "Accumulation",       "signal": "bullish",  "desc": "whale accumulation pattern detected"},
    "distribution":     {"emoji": "🔴📉", "label": "Distribution",       "signal": "bearish",  "desc": "whale distribution pattern detected"},
    "unknown":          {"emoji": "📦",    "label": "Unknown",            "signal": "neutral",  "desc": "unclassified whale movement"},
}

# ---------------------------------------------------------------------------
# Smart links
# ---------------------------------------------------------------------------
SOLANA_LINKS: dict[str, str] = {
    # Explorers
    "tx":         "https://solscan.io/tx/{tx_hash}",
    "wallet":     "https://solscan.io/account/{address}",
    "solana_fm":  "https://solana.fm/address/{address}",
    # Charts & analysis
    "chart":      "https://dexscreener.com/solana/{token_address}",
    "birdeye":    "https://birdeye.so/token/{token_address}?chain=solana",
    "photon":     "https://photon-sol.tinyastro.io/en/lp/{token_address}",
    "axiom":      "https://axiom.trade/t/{token_address}",
    # Safety
    "rugcheck":   "https://rugcheck.xyz/tokens/{token_address}",
    "bubblemaps": "https://app.bubblemaps.io/sol/token/{token_address}",
    # Swap
    "jupiter":    "https://jup.ag/swap/SOL-{token_address}",
    # Wallet dashboards
    "gmgn":       "https://gmgn.ai/sol/address/{address}",
    "gmgn_token": "https://gmgn.ai/sol/token/{token_address}",
    "cielo":      "https://app.cielo.finance/profile/{address}/tokens/solana",
    "step":       "https://app.step.finance/en/dashboard?watching={address}",
    "sonarwatch": "https://sonar.watch/portfolio/{address}",
    # Telegram trading bots
    "trojan":     "https://t.me/TrojanOnSolana_bot?start={token_address}",
    "bonkbot":    "https://t.me/bonkbot_bot?start={token_address}",
    "maestro":    "https://t.me/MaestroSniperBot?start={token_address}",
    "banana":     "https://t.me/BananaGunSniper_bot?start=snp_{token_address}",
}

ETH_LINKS: dict[str, str] = {
    # Explorers
    "tx":         "https://etherscan.io/tx/{tx_hash}",
    "wallet":     "https://etherscan.io/address/{address}",
    # Charts & analysis
    "chart":      "https://dexscreener.com/ethereum/{token_address}",
    "dextools":   "https://www.dextools.io/app/ether/pair-explorer/{token_address}",
    "bubblemaps": "https://app.bubblemaps.io/eth/token/{token_address}",
    # Swap
    "uniswap":    "https://app.uniswap.org/swap?outputCurrency={token_address}",
    # Wallet dashboards
    "debank":     "https://debank.com/profile/{address}",
    "arkham":     "https://platform.arkhamintelligence.com/explorer/address/{address}",
    "zerion":     "https://app.zerion.io/{address}/overview",
    # Gas
    "gas":        "https://etherscan.io/gastracker",
    # Telegram trading bots
    "maestro":    "https://t.me/MaestroSniperBot?start={token_address}",
    "banana":     "https://t.me/BananaGunSniper_bot?start=snp_{token_address}",
}

# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------
REQUIRED_VARS: list[str] = [
    "TELEGRAM_BOT_TOKEN",
    "HELIUS_API_KEY",
    "ALCHEMY_API_KEY",
    "ETHERSCAN_API_KEY",
]


def validate_env() -> None:
    """Fail fast if required env vars are missing."""
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        logger.critical("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)
