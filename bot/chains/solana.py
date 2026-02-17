"""Solana chain integration: Helius webhooks + enriched tx + DexScreener + Jupiter."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from bot.config import HELIUS_API_KEY, HELIUS_BASE_URL, SOL_MINT, WEBHOOK_HOST, WEBHOOK_PORT
from bot.utils.rate_limiter import RATE_LIMITERS
from bot.utils.retry import retry_async

logger = logging.getLogger("whalegod.chains.solana")


# ---------------------------------------------------------------------------
# Helius webhook management
# ---------------------------------------------------------------------------

async def register_webhook(session: aiohttp.ClientSession) -> str | None:
    """Register a Helius enhanced webhook for whale transfers.

    Checks for existing webhooks first to avoid duplicates on restart.
    Returns the webhook ID on success, or None.
    """
    if not WEBHOOK_HOST:
        logger.warning("WEBHOOK_HOST not set — skipping Helius webhook registration")
        return None

    webhook_url = f"http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook/helius"

    # Check for existing webhook with same URL to avoid duplicates
    existing = await get_existing_webhooks(session)
    for wh in existing:
        if wh.get("webhookURL") == webhook_url:
            wh_id = wh.get("webhookID", "unknown")
            logger.info("Helius webhook already exists: %s — skipping registration", wh_id)
            return wh_id

    url = f"{HELIUS_BASE_URL}/webhooks?api-key={HELIUS_API_KEY}"

    payload = {
        "webhookURL": webhook_url,
        "transactionTypes": [
            "TRANSFER",
            "SWAP",
            "ADD_LIQUIDITY",
            "REMOVE_LIQUIDITY",
            "TOKEN_MINT",
        ],
        "accountAddresses": [],  # Empty = all large transfers
        "webhookType": "enhanced",
        "encoding": "jsonParsed",
    }

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["helius"]:
            return await session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=15)
            )

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        logger.error("Failed to register Helius webhook")
        return None

    try:
        if resp.status in (200, 201):
            data = await resp.json()
            webhook_id = data.get("webhookID")
            logger.info("Helius webhook registered: %s", webhook_id)
            return webhook_id
        body = await resp.text()
        logger.error("Helius webhook registration failed: %d — %s", resp.status, body)
        return None
    finally:
        resp.release()


async def get_existing_webhooks(session: aiohttp.ClientSession) -> list[dict[str, Any]]:
    """List all existing Helius webhooks."""
    url = f"{HELIUS_BASE_URL}/webhooks?api-key={HELIUS_API_KEY}"

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["helius"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return []

    try:
        if resp.status == 200:
            return await resp.json()
        return []
    finally:
        resp.release()


# ---------------------------------------------------------------------------
# Transaction parsing from Helius webhook payload
# ---------------------------------------------------------------------------

# Well-known Solana program IDs for enhanced detection
_PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
_PUMP_FUN_FEE = "CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbCJ2w36th7Lho"
_RAYDIUM_AMM_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
_RAYDIUM_CLMM = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
_RAYDIUM_CPMM = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
_JUPITER_V6 = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
_JUPITER_DCA = "DCA265Vj8a9CEuX1eb1LWRnDT7uK6q1xMipnNyatn23M"
_JUPITER_LIMIT = "jupoNjAxXgZ4rjzxzPMP4oxduvQsQtZzyknqvzYNrNu"
_METEORA_DLMM = "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"
_ORCA_WHIRLPOOL = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
_JITO_TIP_ACCOUNTS = {
    "T1pyyaTNZsKv2WcRAB8oVnk93mLJw2XzjtVYqCsaHqt",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "HFqU5x63VTqvQss8hp11i4bPNa6YFMGBiXLi5go7Nf6K",
    "ADaUMid9yfUC67HyDjq3ZGAVz7FhYtRTnBfnkZUSwLUK",
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSgaJDUNx6MAuJFvCQr",
    "DttWaMuVvTiDuNDfu3xroYDBk2SymTVkC5am9PBiPdJ8",
}


def _detect_program_type(event: dict[str, Any]) -> str | None:
    """Detect special program interactions from Helius event data.

    Returns a refined tx_type override or None if no special program detected.
    """
    # Check accountData / instructions for program involvement
    account_data = event.get("accountData", [])
    instructions = event.get("instructions", [])

    # Collect all program IDs involved
    program_ids: set[str] = set()
    for instr in instructions:
        pid = instr.get("programId", "")
        if pid:
            program_ids.add(pid)
        # Check inner instructions too
        for inner in instr.get("innerInstructions", []):
            inner_pid = inner.get("programId", "")
            if inner_pid:
                program_ids.add(inner_pid)

    # Also check account addresses for program involvement
    for acc in account_data:
        acc_addr = acc.get("account", "")
        if acc_addr:
            program_ids.add(acc_addr)

    # Pump.fun detection
    if _PUMP_FUN_PROGRAM in program_ids or _PUMP_FUN_FEE in program_ids:
        return "PUMP_FUN"

    # Jupiter DCA detection
    if _JUPITER_DCA in program_ids:
        return "JUPITER_DCA"

    # Jupiter Limit Order detection
    if _JUPITER_LIMIT in program_ids:
        return "JUPITER_LIMIT"

    # Meteora DLMM detection
    if _METEORA_DLMM in program_ids:
        return "METEORA_DLMM"

    # Raydium CLMM/CPMM detection
    if _RAYDIUM_CLMM in program_ids:
        return "RAYDIUM_CLMM"
    if _RAYDIUM_CPMM in program_ids:
        return "RAYDIUM_CPMM"

    return None


def parse_helius_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a Helius enhanced transaction event into whale movement dicts.

    Returns a list of parsed transfers (one tx can have multiple transfers).
    Enhanced with Pump.fun, Raydium, Jupiter DCA, Meteora detection.
    """
    results: list[dict[str, Any]] = []
    sig = event.get("signature", "")
    tx_type = event.get("type", "UNKNOWN")
    fee_payer = event.get("feePayer", "")

    # Detect special program involvement for refined classification
    program_type = _detect_program_type(event)
    effective_tx_type = program_type or tx_type

    # Process native SOL transfers
    native_transfers = event.get("nativeTransfers", [])
    for nt in native_transfers:
        from_addr = nt.get("fromUserAccount", "")
        to_addr = nt.get("toUserAccount", "")
        lamports = nt.get("amount", 0)
        sol_amount = lamports / 1e9

        if sol_amount < 1:  # Skip dust
            continue

        # Skip all Jito tip payments (MEV tips are noise for whale tracking)
        if to_addr in _JITO_TIP_ACCOUNTS:
            continue

        results.append({
            "chain": "solana",
            "tx_hash": sig,
            "from_address": from_addr,
            "to_address": to_addr,
            "amount": sol_amount,
            "token_symbol": "SOL",
            "token_address": SOL_MINT,
            "tx_type": effective_tx_type,
        })

    # Process SPL token transfers
    token_transfers = event.get("tokenTransfers", [])
    for tt in token_transfers:
        from_addr = tt.get("fromUserAccount", "") or fee_payer
        to_addr = tt.get("toUserAccount", "")
        raw_amount = tt.get("tokenAmount", 0)
        mint = tt.get("mint", "")

        if not raw_amount or raw_amount == 0:
            continue

        results.append({
            "chain": "solana",
            "tx_hash": sig,
            "from_address": from_addr,
            "to_address": to_addr,
            "amount": float(raw_amount),
            "token_symbol": tt.get("symbol", ""),
            "token_address": mint,
            "tx_type": effective_tx_type,
        })

    return results


# ---------------------------------------------------------------------------
# Helius parsed transaction history (for /scan, tracked wallets)
# ---------------------------------------------------------------------------

async def get_wallet_transactions(
    session: aiohttp.ClientSession, address: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Fetch parsed transaction history for a Solana wallet via Helius."""
    url = (
        f"{HELIUS_BASE_URL}/addresses/{address}/transactions"
        f"?api-key={HELIUS_API_KEY}&limit={limit}"
    )

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["helius"]:
            return await session.get(url, timeout=aiohttp.ClientTimeout(total=15))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return []

    try:
        if resp.status == 200:
            return await resp.json()
        logger.warning("Helius wallet txs failed: %d", resp.status)
        return []
    finally:
        resp.release()


async def enrich_transactions(
    session: aiohttp.ClientSession, signatures: list[str]
) -> list[dict[str, Any]]:
    """Enrich transaction signatures using Helius parsed transactions API."""
    if not signatures:
        return []

    url = f"{HELIUS_BASE_URL}/transactions?api-key={HELIUS_API_KEY}"

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["helius"]:
            return await session.post(
                url,
                json={"transactions": signatures[:20]},  # Max 20 per request
                timeout=aiohttp.ClientTimeout(total=15),
            )

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return []

    try:
        if resp.status == 200:
            return await resp.json()
        logger.warning("Helius enrich failed: %d", resp.status)
        return []
    finally:
        resp.release()


# ---------------------------------------------------------------------------
# Helius priority fee estimate
# ---------------------------------------------------------------------------

async def get_priority_fee(session: aiohttp.ClientSession) -> dict[str, Any] | None:
    """Get priority fee estimates from Helius RPC."""
    url = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getRecentPrioritizationFees",
        "params": [],
    }

    async def _fetch() -> aiohttp.ClientResponse:
        async with RATE_LIMITERS["helius"]:
            return await session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10))

    resp = await retry_async(_fetch)
    if resp is None or not isinstance(resp, aiohttp.ClientResponse):
        return None

    try:
        if resp.status == 200:
            data = await resp.json()
            result = data.get("result", [])
            if result:
                fees = [r.get("prioritizationFee", 0) for r in result if r.get("prioritizationFee")]
                if fees:
                    return {
                        "min": min(fees),
                        "max": max(fees),
                        "avg": sum(fees) / len(fees),
                        "median": sorted(fees)[len(fees) // 2],
                    }
        return None
    except Exception:
        logger.exception("Helius priority fee parse error")
        return None
    finally:
        resp.release()
