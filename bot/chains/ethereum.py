"""Ethereum chain integration: Alchemy RPC + Etherscan + DexScreener."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from bot.config import (
    ALCHEMY_RPC_URL,
    ETHERSCAN_API_KEY,
    ETHERSCAN_BASE_URL,
)
from bot.utils.rate_limiter import RATE_LIMITERS
from bot.utils.retry import retry_async

logger = logging.getLogger("whalegod.chains.ethereum")

# Track last polled block
_last_polled_block: int = 0


def get_last_polled_block() -> int:
    """Return the last polled block number."""
    return _last_polled_block


# ---------------------------------------------------------------------------
# Alchemy JSON-RPC helpers
# ---------------------------------------------------------------------------

async def _rpc_call(
    session: aiohttp.ClientSession, method: str, params: list[Any] | None = None
) -> Any | None:
    """Make an Alchemy JSON-RPC call."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["alchemy"]:
            return await session.post(
                ALCHEMY_RPC_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            )

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return None

    try:
        if resp.status != 200:
            return None
        data = await resp.json()
        if "error" in data:
            logger.warning("Alchemy RPC error: %s", data["error"])
            return None
        return data.get("result")
    except Exception:
        logger.exception("Alchemy RPC parse error")
        return None
    finally:
        resp.release()


async def get_latest_block_number(session: aiohttp.ClientSession) -> int | None:
    """Get the latest Ethereum block number."""
    result = await _rpc_call(session, "eth_blockNumber")
    if result:
        return int(result, 16)
    return None


async def get_block_with_transactions(
    session: aiohttp.ClientSession, block_number: int
) -> dict[str, Any] | None:
    """Fetch a block with full transaction objects."""
    hex_block = hex(block_number)
    return await _rpc_call(session, "eth_getBlockByNumber", [hex_block, True])


# ---------------------------------------------------------------------------
# Ethereum block polling — extract large transfers
# ---------------------------------------------------------------------------

async def poll_recent_blocks(
    session: aiohttp.ClientSession, min_eth: float = 50.0
) -> list[dict[str, Any]]:
    """Poll recent Ethereum blocks for large ETH transfers.

    Returns a list of parsed transfer dicts matching the alert engine format.
    """
    global _last_polled_block

    latest = await get_latest_block_number(session)
    if latest is None:
        logger.warning("Could not get latest ETH block number")
        return []

    # On first run, start from the latest block
    if _last_polled_block == 0:
        _last_polled_block = latest - 1

    # Don't re-process blocks we've seen — process up to 5 new blocks
    start_block = _last_polled_block + 1
    end_block = min(latest, start_block + 4)

    if start_block > latest:
        return []

    results: list[dict[str, Any]] = []

    for block_num in range(start_block, end_block + 1):
        block = await get_block_with_transactions(session, block_num)
        if not block or not block.get("transactions"):
            continue

        timestamp_hex = block.get("timestamp", "0x0")
        block_timestamp = int(timestamp_hex, 16)

        for tx in block["transactions"]:
            if not isinstance(tx, dict):
                continue

            value_hex = tx.get("value", "0x0")
            value_wei = int(value_hex, 16)
            eth_amount = value_wei / 1e18

            if eth_amount < min_eth:
                continue

            from_addr = tx.get("from", "")
            to_addr = tx.get("to", "") or ""  # Contract creation has null to

            results.append({
                "chain": "ethereum",
                "tx_hash": tx.get("hash", ""),
                "from_address": from_addr,
                "to_address": to_addr,
                "amount": eth_amount,
                "token_symbol": "ETH",
                "token_address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                "tx_type": "TRANSFER",
                "block_timestamp": block_timestamp,
            })

    _last_polled_block = end_block
    if results:
        logger.info("ETH poll: found %d large transfers in blocks %d-%d", len(results), start_block, end_block)
    return results


# ---------------------------------------------------------------------------
# Etherscan API helpers
# ---------------------------------------------------------------------------

async def get_wallet_transactions(
    session: aiohttp.ClientSession, address: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Fetch recent transactions for an Ethereum wallet via Etherscan."""
    url = (
        f"{ETHERSCAN_BASE_URL}?module=account&action=txlist"
        f"&address={address}&sort=desc&page=1&offset={limit}"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["etherscan"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return []

    try:
        if resp.status != 200:
            return []
        data = await resp.json()
        result = data.get("result", [])
        return result if isinstance(result, list) else []
    except Exception:
        logger.exception("Etherscan txlist parse error")
        return []
    finally:
        resp.release()


async def get_token_transfers(
    session: aiohttp.ClientSession, address: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Fetch recent ERC-20 token transfers via Etherscan."""
    url = (
        f"{ETHERSCAN_BASE_URL}?module=account&action=tokentx"
        f"&address={address}&sort=desc&page=1&offset={limit}"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["etherscan"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return []

    try:
        if resp.status != 200:
            return []
        data = await resp.json()
        result = data.get("result", [])
        return result if isinstance(result, list) else []
    except Exception:
        logger.exception("Etherscan tokentx parse error")
        return []
    finally:
        resp.release()


async def get_internal_transactions(
    session: aiohttp.ClientSession, address: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Fetch internal transactions via Etherscan."""
    url = (
        f"{ETHERSCAN_BASE_URL}?module=account&action=txlistinternal"
        f"&address={address}&sort=desc&page=1&offset={limit}"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["etherscan"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return []

    try:
        if resp.status != 200:
            return []
        data = await resp.json()
        result = data.get("result", [])
        return result if isinstance(result, list) else []
    except Exception:
        logger.exception("Etherscan internal tx parse error")
        return []
    finally:
        resp.release()


async def get_gas_oracle(session: aiohttp.ClientSession) -> dict[str, Any] | None:
    """Fetch gas prices from Etherscan gas tracker, with Alchemy RPC fallback."""
    # Source 1: Etherscan gas oracle (detailed slow/standard/fast)
    url = (
        f"{ETHERSCAN_BASE_URL}?module=gastracker&action=gasoracle"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["etherscan"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is not None and isinstance(resp, aiohttp.ClientResponse):
        try:
            if resp.status == 200:
                data = await resp.json()
                result = data.get("result", {})
                if isinstance(result, dict) and result.get("SafeGasPrice"):
                    return {
                        "slow": float(result.get("SafeGasPrice", 0)),
                        "standard": float(result.get("ProposeGasPrice", 0)),
                        "fast": float(result.get("FastGasPrice", 0)),
                        "base_fee": float(result.get("suggestBaseFee", 0)),
                    }
        except Exception:
            logger.exception("Etherscan gas oracle parse error")
        finally:
            resp.release()

    # Source 2: Alchemy RPC fallback (eth_gasPrice — single value, estimate tiers)
    logger.debug("Etherscan gas oracle failed, falling back to Alchemy RPC")
    gas_hex = await _rpc_call(session, "eth_gasPrice")
    if gas_hex:
        try:
            gwei = int(gas_hex, 16) / 1e9
            return {
                "slow": round(gwei * 0.85, 1),
                "standard": round(gwei, 1),
                "fast": round(gwei * 1.15, 1),
                "base_fee": round(gwei, 1),
            }
        except (ValueError, TypeError):
            pass

    return None


async def get_eth_price_etherscan(session: aiohttp.ClientSession) -> float | None:
    """Get ETH/USD price from Etherscan."""
    url = (
        f"{ETHERSCAN_BASE_URL}?module=stats&action=ethprice"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

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
        result = data.get("result", {})
        if isinstance(result, dict) and result.get("ethusd"):
            return float(result["ethusd"])
        return None
    except Exception:
        logger.exception("Etherscan ETH price parse error")
        return None
    finally:
        resp.release()
