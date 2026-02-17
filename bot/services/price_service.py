"""Multi-source price service: Jupiter → DexScreener → CoinGecko → Etherscan fallback."""

from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from bot.config import (
    COINGECKO_API_KEY,
    ETHERSCAN_API_KEY,
    ETHERSCAN_BASE_URL,
    PRICE_TTL_ACTIVE,
    PRICE_TTL_BASE,
    PRICE_TTL_STABLECOIN,
    SOL_MINT,
    STABLECOINS,
)
from bot.utils.rate_limiter import RATE_LIMITERS
from bot.utils.retry import retry_async

logger = logging.getLogger("whalegod.price_service")

# ---------------------------------------------------------------------------
# In-memory price cache: {token_address: (price_usd, timestamp_mono)}
# ---------------------------------------------------------------------------
_price_cache: dict[str, tuple[float, float]] = {}

# Base asset keys
_BASE_SOL_KEY = "__SOL__"
_BASE_ETH_KEY = "__ETH__"

# Track last successful call per source for health checks
last_success: dict[str, float] = {}


def _cache_get(key: str, ttl: int | None = None) -> float | None:
    """Return cached price if still valid, else None."""
    entry = _price_cache.get(key)
    if entry is None:
        return None
    price, ts = entry
    if ttl is None:
        ttl = PRICE_TTL_STABLECOIN if key in STABLECOINS else PRICE_TTL_ACTIVE
    if time.monotonic() - ts > ttl:
        return None
    return price


def _cache_set(key: str, price: float) -> None:
    """Store a price in the cache."""
    _price_cache[key] = (price, time.monotonic())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_sol_price(session: aiohttp.ClientSession) -> float:
    """Get current SOL/USD price."""
    cached = _cache_get(_BASE_SOL_KEY, PRICE_TTL_BASE)
    if cached is not None:
        return cached

    price = await _jupiter_price(session, SOL_MINT)
    if price:
        _cache_set(_BASE_SOL_KEY, price)
        return price

    price = await _dexscreener_price(session, "solana", SOL_MINT)
    if price:
        _cache_set(_BASE_SOL_KEY, price)
        return price

    price = await _coingecko_price(session, "solana")
    if price:
        _cache_set(_BASE_SOL_KEY, price)
        return price

    # Last resort — return last known
    entry = _price_cache.get(_BASE_SOL_KEY)
    return entry[0] if entry else 0.0


async def get_eth_price(session: aiohttp.ClientSession) -> float:
    """Get current ETH/USD price."""
    cached = _cache_get(_BASE_ETH_KEY, PRICE_TTL_BASE)
    if cached is not None:
        return cached

    price = await _etherscan_eth_price(session)
    if price:
        _cache_set(_BASE_ETH_KEY, price)
        return price

    price = await _coingecko_price(session, "ethereum")
    if price:
        _cache_set(_BASE_ETH_KEY, price)
        return price

    price = await _dexscreener_price(session, "ethereum", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
    if price:
        _cache_set(_BASE_ETH_KEY, price)
        return price

    entry = _price_cache.get(_BASE_ETH_KEY)
    return entry[0] if entry else 0.0


async def get_token_price(
    session: aiohttp.ClientSession, chain: str, token_address: str
) -> float:
    """Get a token price in USD using multi-source fallback."""
    # Native asset shortcuts
    if chain == "solana" and token_address == SOL_MINT:
        return await get_sol_price(session)
    if chain == "ethereum" and token_address.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
        return await get_eth_price(session)

    cached = _cache_get(token_address)
    if cached is not None:
        return cached

    # Source 1: Jupiter (Solana only)
    if chain == "solana":
        price = await _jupiter_price(session, token_address)
        if price:
            _cache_set(token_address, price)
            return price

    # Source 2: DexScreener
    price = await _dexscreener_price(session, chain, token_address)
    if price:
        _cache_set(token_address, price)
        return price

    # Source 3: CoinGecko (if key available)
    # CoinGecko needs coin IDs not addresses — limited usefulness here
    # Skip for arbitrary tokens, only useful for base assets

    return 0.0


async def refresh_base_prices(session: aiohttp.ClientSession) -> None:
    """Proactively refresh SOL and ETH prices (called by scheduler)."""
    await get_sol_price(session)
    await get_eth_price(session)
    logger.debug(
        "Base prices refreshed — SOL: $%.2f, ETH: $%.2f",
        _price_cache.get(_BASE_SOL_KEY, (0,))[0],
        _price_cache.get(_BASE_ETH_KEY, (0,))[0],
    )


async def get_token_info_dexscreener(
    session: aiohttp.ClientSession, chain: str, token_address: str
) -> dict[str, Any] | None:
    """Fetch full token info from DexScreener (for /scan command)."""
    chain_id = "solana" if chain == "solana" else "ethereum"
    url = f"https://api.dexscreener.com/tokens/v1/{chain_id}/{token_address}"

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["dexscreener_pairs"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return None

    try:
        if resp.status != 200:
            return None
        data = await resp.json()
        last_success["dexscreener"] = time.monotonic()
        # Returns array of pairs — pick the one with highest liquidity
        if isinstance(data, list) and data:
            pairs = sorted(data, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
            return pairs[0]
        return None
    except Exception:
        logger.exception("DexScreener token info parse error")
        return None
    finally:
        resp.release()


async def get_trending_tokens(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """Fetch trending/boosted tokens from DexScreener."""
    url = "https://api.dexscreener.com/token-boosts/latest/v1"

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["dexscreener_profiles"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return []

    try:
        if resp.status != 200:
            return []
        data = await resp.json()
        last_success["dexscreener"] = time.monotonic()
        if isinstance(data, list):
            return data[:20]  # Get top 20 for filtering
        return []
    except Exception:
        logger.exception("DexScreener trending parse error")
        return []
    finally:
        resp.release()


# ---------------------------------------------------------------------------
# Private: individual source fetchers
# ---------------------------------------------------------------------------

async def _jupiter_price(session: aiohttp.ClientSession, mint: str) -> float | None:
    """Fetch price from Jupiter Price API v2."""
    url = f"https://api.jup.ag/price/v2?ids={mint}"

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["jupiter"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return None

    try:
        if resp.status != 200:
            return None
        data = await resp.json()
        last_success["jupiter"] = time.monotonic()
        token_data = data.get("data", {}).get(mint)
        if token_data and token_data.get("price"):
            return float(token_data["price"])
        return None
    except Exception:
        logger.exception("Jupiter price parse error")
        return None
    finally:
        resp.release()


async def _dexscreener_price(
    session: aiohttp.ClientSession, chain: str, token_address: str
) -> float | None:
    """Fetch price from DexScreener."""
    chain_id = "solana" if chain == "solana" else "ethereum"
    url = f"https://api.dexscreener.com/tokens/v1/{chain_id}/{token_address}"

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["dexscreener_pairs"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return None

    try:
        if resp.status != 200:
            return None
        data = await resp.json()
        last_success["dexscreener"] = time.monotonic()
        if isinstance(data, list) and data:
            price_str = data[0].get("priceUsd")
            if price_str:
                return float(price_str)
        return None
    except Exception:
        logger.exception("DexScreener price parse error")
        return None
    finally:
        resp.release()


async def _coingecko_price(session: aiohttp.ClientSession, coin_id: str) -> float | None:
    """Fetch price from CoinGecko demo API."""
    if not COINGECKO_API_KEY:
        return None

    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    headers = {"x-cg-demo-api-key": COINGECKO_API_KEY}

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["coingecko"]:
            return await session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return None

    try:
        if resp.status != 200:
            return None
        data = await resp.json()
        last_success["coingecko"] = time.monotonic()
        price = data.get(coin_id, {}).get("usd")
        if price:
            return float(price)
        return None
    except Exception:
        logger.exception("CoinGecko price parse error")
        return None
    finally:
        resp.release()


async def _etherscan_eth_price(session: aiohttp.ClientSession) -> float | None:
    """Fetch ETH price from Etherscan."""
    if not ETHERSCAN_API_KEY:
        return None

    url = f"{ETHERSCAN_BASE_URL}?module=stats&action=ethprice&apikey={ETHERSCAN_API_KEY}"

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["etherscan"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return None

    try:
        if resp.status != 200:
            return None
        data = await resp.json()
        last_success["etherscan"] = time.monotonic()
        result = data.get("result", {})
        if isinstance(result, dict) and result.get("ethusd"):
            return float(result["ethusd"])
        return None
    except Exception:
        logger.exception("Etherscan ETH price parse error")
        return None
    finally:
        resp.release()
