"""Core alert pipeline: receive → enrich → classify → dedup → log → broadcast."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import aiohttp
from telegram import Bot
from telegram.error import BadRequest, Forbidden, ChatMigrated

from bot.config import (
    FLOOD_THRESHOLD,
    FLOOD_WINDOW_SECONDS,
    TX_CATEGORIES,
)
from bot.database import (
    delete_subscription,
    get_all_enabled_subscriptions,
    get_all_tracked_wallets,
    increment_stat,
    insert_whale_log,
)
from bot.chains import ethereum as eth_chain
from bot.chains import solana as sol_chain
from bot.services import label_service
from bot.services import price_service
from bot.utils.formatter import format_flood_digest, format_whale_alert
from bot.utils.rate_limiter import RATE_LIMITERS

logger = logging.getLogger("whalegod.alert_engine")

# ---------------------------------------------------------------------------
# Anti-flood state
# ---------------------------------------------------------------------------
_event_timestamps: deque[float] = deque(maxlen=500)
_flood_mode: bool = False
_flood_buffer: list[dict[str, Any]] = []
_FLOOD_BUFFER_MAX: int = 100
_flood_resume_checks: int = 0

# Track last event per chain for health checks
last_event_time: dict[str, str] = {}

# In-memory dedup: prevents race conditions between concurrent tasks
# (webhook + poller + tracked wallet checker can overlap)
_seen_tx_hashes: dict[str, float] = {}  # tx_hash:chain → timestamp
_SEEN_MAX_SIZE: int = 2000
_SEEN_TTL: float = 600.0  # 10 minutes

# ---------------------------------------------------------------------------
# Subscription cache (avoid DB query on every alert)
# ---------------------------------------------------------------------------
_sub_cache: list[dict[str, Any]] | None = None
_sub_cache_ts: float = 0.0
_SUB_CACHE_TTL: float = 30.0


async def _get_subs_cached() -> list[dict[str, Any]]:
    """Return cached subscriptions, refreshing every 30s."""
    global _sub_cache, _sub_cache_ts
    now = time.monotonic()
    if _sub_cache is not None and (now - _sub_cache_ts) < _SUB_CACHE_TTL:
        return _sub_cache
    _sub_cache = await get_all_enabled_subscriptions()
    _sub_cache_ts = now
    return _sub_cache


def _sub_cache_invalidate() -> None:
    """Invalidate the subscription cache (e.g. after a delete)."""
    global _sub_cache
    _sub_cache = None


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

async def process_helius_event(
    event: dict[str, Any],
    session: aiohttp.ClientSession,
    bot: Bot,
) -> None:
    """Process a single Helius webhook event through the full pipeline."""
    transfers = sol_chain.parse_helius_event(event)
    for transfer in transfers:
        await _pipeline(transfer, session, bot)


async def poll_ethereum(
    session: aiohttp.ClientSession,
    bot: Bot,
) -> None:
    """Poll Ethereum for recent large transfers and process them."""
    try:
        transfers = await eth_chain.poll_recent_blocks(session, min_eth=50.0)
        for transfer in transfers:
            await _pipeline(transfer, session, bot)
    except Exception:
        logger.exception("ETH polling error")


async def check_tracked_wallets(
    session: aiohttp.ClientSession,
    bot: Bot,
) -> None:
    """Check all tracked wallets for new activity."""
    try:
        wallets = await get_all_tracked_wallets()
        for wallet in wallets:
            chain = wallet["chain"]
            address = wallet["wallet_address"]
            chat_id = wallet["chat_id"]

            try:
                if chain == "solana":
                    txs = await sol_chain.get_wallet_transactions(session, address, limit=5)
                    for tx in txs:
                        transfers = sol_chain.parse_helius_event(tx)
                        for transfer in transfers:
                            transfer["_tracked_chat_id"] = chat_id
                            await _pipeline(transfer, session, bot)
                else:
                    txs = await eth_chain.get_wallet_transactions(session, address, limit=5)
                    for tx in txs:
                        eth_value = int(tx.get("value", "0")) / 1e18
                        if eth_value < 1:
                            continue
                        transfer = {
                            "chain": "ethereum",
                            "tx_hash": tx.get("hash", ""),
                            "from_address": tx.get("from", ""),
                            "to_address": tx.get("to", ""),
                            "amount": eth_value,
                            "token_symbol": "ETH",
                            "token_address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                            "tx_type": "TRANSFER",
                            "_tracked_chat_id": chat_id,
                        }
                        await _pipeline(transfer, session, bot)
            except Exception:
                logger.exception("Error checking tracked wallet %s on %s", address, chain)

    except Exception:
        logger.exception("Tracked wallet check error")


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

async def _pipeline(
    transfer: dict[str, Any],
    session: aiohttp.ClientSession,
    bot: Bot,
) -> None:
    """Full pipeline: dedup → enrich → classify → log → broadcast."""
    chain = transfer["chain"]
    tx_hash = transfer.get("tx_hash", "")
    from_addr = transfer.get("from_address", "")
    to_addr = transfer.get("to_address", "")
    amount = transfer.get("amount", 0)
    token_address = transfer.get("token_address", "")

    # Step 0: Fast in-memory dedup (catches race conditions between
    # concurrent webhook events, ETH poller, and tracked wallet checker)
    dedup_key = f"{tx_hash}:{chain}"
    now = time.monotonic()
    if dedup_key in _seen_tx_hashes:
        return  # Already processing or processed
    _seen_tx_hashes[dedup_key] = now

    # Prune old entries periodically
    if len(_seen_tx_hashes) > _SEEN_MAX_SIZE:
        cutoff = now - _SEEN_TTL
        stale = [k for k, ts in _seen_tx_hashes.items() if ts < cutoff]
        for k in stale:
            del _seen_tx_hashes[k]

    # Step 1: Enrich — get USD price
    usd_value = await _enrich_price(session, chain, token_address, amount)
    transfer["usd_value"] = usd_value

    # Step 2: Classify category
    tx_category, signal = _classify(chain, from_addr, to_addr, transfer.get("tx_type", ""))
    transfer["tx_category"] = tx_category
    transfer["signal"] = signal

    # Step 3: Label wallets
    from_label_data = label_service.get_label(chain, from_addr)
    to_label_data = label_service.get_label(chain, to_addr)
    transfer["from_label"] = from_label_data["name"]
    transfer["to_label"] = to_label_data["name"]

    # Step 4: Dedup — insert into whale_logs (unique on tx_hash+chain)
    inserted = await insert_whale_log(
        chain=chain,
        tx_hash=transfer.get("tx_hash", ""),
        from_address=from_addr,
        to_address=to_addr,
        from_label=transfer["from_label"],
        to_label=transfer["to_label"],
        amount=amount,
        token_symbol=transfer.get("token_symbol"),
        token_address=token_address,
        usd_value=usd_value,
        tx_type=transfer.get("tx_type"),
        tx_category=tx_category,
        signal=signal,
    )
    if not inserted:
        return  # Duplicate — skip

    await increment_stat("total_whales_detected")

    # Update health tracking
    last_event_time[chain] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Step 5: Anti-flood check
    now = time.monotonic()
    _event_timestamps.append(now)
    # Prune old timestamps
    while _event_timestamps and _event_timestamps[0] < now - FLOOD_WINDOW_SECONDS:
        _event_timestamps.popleft()

    await _handle_flood(transfer, session, bot)


async def _handle_flood(
    transfer: dict[str, Any],
    session: aiohttp.ClientSession,
    bot: Bot,
) -> None:
    """Handle flood mode: batch or individual broadcast."""
    global _flood_mode, _flood_resume_checks

    if len(_event_timestamps) > FLOOD_THRESHOLD:
        if not _flood_mode:
            _flood_mode = True
            _flood_resume_checks = 0
            logger.warning("Flood mode ACTIVATED — batching alerts")

        if len(_flood_buffer) < _FLOOD_BUFFER_MAX:
            _flood_buffer.append(transfer)

        # Send digest every 60 seconds while in flood mode
        if len(_flood_buffer) >= FLOOD_THRESHOLD:
            sorted_events = sorted(_flood_buffer, key=lambda e: e.get("usd_value", 0), reverse=True)
            msg = format_flood_digest(sorted_events, len(_flood_buffer))
            await _broadcast(msg, bot, transfer={})
            _flood_buffer.clear()
        return

    # Not flooding — check if we should resume normal mode
    if _flood_mode:
        if len(_event_timestamps) < 5:
            _flood_resume_checks += 1
            if _flood_resume_checks >= 2:
                _flood_mode = False
                _flood_resume_checks = 0
                # Flush any remaining buffer
                if _flood_buffer:
                    sorted_events = sorted(_flood_buffer, key=lambda e: e.get("usd_value", 0), reverse=True)
                    msg = format_flood_digest(sorted_events, len(_flood_buffer))
                    await _broadcast(msg, bot, transfer={})
                    _flood_buffer.clear()
                logger.info("Flood mode DEACTIVATED — resuming individual alerts")
        else:
            _flood_resume_checks = 0
            _flood_buffer.append(transfer)
            return

    # Normal individual alert
    msg = format_whale_alert(transfer)
    await _broadcast(msg, bot, transfer=transfer)


# ---------------------------------------------------------------------------
# Price enrichment
# ---------------------------------------------------------------------------

async def _enrich_price(
    session: aiohttp.ClientSession,
    chain: str,
    token_address: str,
    amount: float,
) -> float:
    """Get the USD value of a transfer."""
    try:
        if not token_address or amount <= 0:
            return 0.0
        token_price = await price_service.get_token_price(session, chain, token_address)
        return amount * token_price
    except Exception:
        logger.exception("Price enrichment error")
        return 0.0


# ---------------------------------------------------------------------------
# Transaction classification
# ---------------------------------------------------------------------------

def _classify(
    chain: str,
    from_address: str,
    to_address: str,
    tx_type: str,
) -> tuple[str, str]:
    """Classify a transfer into a category and signal.

    Priority order (most specific first):
    1. Memecoin infrastructure (Pump.fun launches)
    2. MEV bots / sandwich attacks
    3. Trading bots (Banana Gun, Maestro)
    4. CEX deposits / withdrawals
    5. Bridge transfers
    6. DEX swaps
    7. LP add / remove
    8. Smart money moves (VCs, funds, market makers)
    9. Wallet transfer (fallback)
    """

    # 0. Program-specific tx_type from enhanced Solana parser
    if tx_type == "PUMP_FUN":
        return "memecoin_launch", "degen"
    if tx_type in ("JUPITER_DCA", "JUPITER_LIMIT"):
        return "dex_swap", "neutral"
    if tx_type in ("RAYDIUM_CLMM", "RAYDIUM_CPMM", "METEORA_DLMM"):
        return "dex_swap", "neutral"

    # 1. Memecoin infrastructure detection (Pump.fun, etc.)
    if (from_address and label_service.is_memecoin_infra(chain, from_address)) or \
       (to_address and label_service.is_memecoin_infra(chain, to_address)):
        return "memecoin_launch", "degen"

    # 2. MEV bot detection (sandwich bots, Jito tips, Flashbots)
    if (from_address and label_service.is_mev(chain, from_address)) or \
       (to_address and label_service.is_mev(chain, to_address)):
        return "mev_activity", "caution"

    # 3. Trading bot detection (Banana Gun, Maestro)
    if (from_address and label_service.is_trading_bot(chain, from_address)) or \
       (to_address and label_service.is_trading_bot(chain, to_address)):
        return "trading_bot", "neutral"

    # 4. CEX deposit (to_address is CEX)
    if to_address and label_service.is_cex(chain, to_address):
        return "cex_deposit", "bearish"

    # 5. CEX withdrawal (from_address is CEX)
    if from_address and label_service.is_cex(chain, from_address):
        return "cex_withdrawal", "bullish"

    # 6. Bridge transfer
    if (from_address and label_service.is_bridge(chain, from_address)) or \
       (to_address and label_service.is_bridge(chain, to_address)):
        return "bridge", "neutral"

    # 7. DEX swap
    if tx_type in ("SWAP", "swap"):
        return "dex_swap", "neutral"
    if (from_address and label_service.is_dex(chain, from_address)) or \
       (to_address and label_service.is_dex(chain, to_address)):
        return "dex_swap", "neutral"

    # 8. LP detection — Helius tx types
    if tx_type in ("ADD_LIQUIDITY", "addLiquidity"):
        return "lp_add", "bullish"
    if tx_type in ("REMOVE_LIQUIDITY", "removeLiquidity"):
        return "lp_remove", "bearish"

    # 9. Smart money detection (VCs, funds, market makers, foundations)
    if (from_address and label_service.is_smart_money(chain, from_address)) or \
       (to_address and label_service.is_smart_money(chain, to_address)):
        return "smart_money_move", "alpha"

    # Default: wallet-to-wallet transfer
    if from_address and to_address:
        return "wallet_transfer", "neutral"

    return "unknown", "neutral"


# ---------------------------------------------------------------------------
# Broadcast
# ---------------------------------------------------------------------------

_TELEGRAM_MAX_LEN: int = 4096


async def _broadcast(
    message: str,
    bot: Bot,
    transfer: dict[str, Any],
) -> None:
    """Send an alert to all enabled subscriptions that pass threshold/filter checks."""
    # Telegram message limit is 4096 chars — truncate safely
    if len(message) > _TELEGRAM_MAX_LEN:
        message = message[:_TELEGRAM_MAX_LEN - 20] + "\n\n<i>…truncated</i>"

    subs = await _get_subs_cached()
    usd_value = transfer.get("usd_value", 0) if transfer else 0
    tx_category = transfer.get("tx_category", "") if transfer else ""
    chain = transfer.get("chain", "") if transfer else ""

    sent_count = 0

    for sub in subs:
        chat_id = sub["chat_id"]

        # Check thresholds
        if transfer:
            if not _passes_threshold(sub, chain, usd_value, tx_category):
                continue

            # Check category filters
            if not _passes_filter(sub, tx_category):
                continue

        try:
            async with RATE_LIMITERS["telegram"]:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            sent_count += 1
        except Forbidden:
            logger.info("Bot blocked/kicked from chat %d — removing subscription", chat_id)
            await delete_subscription(chat_id)
            _sub_cache_invalidate()
        except BadRequest as e:
            if "chat not found" in str(e).lower():
                logger.info("Chat %d not found — removing subscription", chat_id)
                await delete_subscription(chat_id)
                _sub_cache_invalidate()
            else:
                logger.warning("BadRequest sending to chat %d: %s", chat_id, e)
        except ChatMigrated as e:
            logger.info("Chat %d migrated to %d — removing old subscription", chat_id, e.new_chat_id)
            await delete_subscription(chat_id)
            _sub_cache_invalidate()
        except Exception:
            logger.exception("Error sending alert to chat %d", chat_id)

    if sent_count > 0:
        await increment_stat("total_alerts_sent", sent_count)


def _passes_threshold(
    sub: dict[str, Any],
    chain: str,
    usd_value: float,
    tx_category: str,
) -> bool:
    """Check if a transfer meets the subscription's threshold."""
    if tx_category in ("lp_add", "lp_remove"):
        return usd_value >= sub.get("min_lp_threshold", 25000)

    min_usd = sub.get("min_usd_threshold", 50000)
    return usd_value >= min_usd


def _passes_filter(sub: dict[str, Any], tx_category: str) -> bool:
    """Check if a transfer category is enabled in the subscription."""
    filter_map = {
        "cex_deposit": "show_cex_deposits",
        "cex_withdrawal": "show_cex_withdrawals",
        "dex_swap": "show_dex_swaps",
        "lp_add": "show_lp_events",
        "lp_remove": "show_lp_events",
        "bridge": "show_bridges",
        # New categories — always shown by default (no filter column yet)
        "memecoin_launch": None,
        "smart_money_move": None,
        "mev_activity": None,
        "trading_bot": None,
        "accumulation": None,
        "distribution": None,
    }
    column = filter_map.get(tx_category)
    if column is None:
        return True  # New and unknown categories always pass
    return bool(sub.get(column, 1))
