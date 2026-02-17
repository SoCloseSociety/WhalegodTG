"""All /command handlers for the WHALEGOD Telegram bot."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import (
    ADMIN_CHAT_ID,
    DONATE_BTC,
    DONATE_ETH,
    DONATE_SOL,
    DONATE_USDT_TRC20,
    MAX_WALLETS_PER_USER,
    SOLANA_LINKS,
    ETH_LINKS,
)
from bot.database import (
    add_tracked_wallet,
    count_active_chats,
    count_total_tracked_wallets,
    count_user_wallets,
    ensure_subscription,
    get_bot_stats,
    get_recent_whale_logs,
    get_top_whale_logs,
    get_user_wallets,
    get_whale_volume,
    remove_tracked_wallet,
)
from bot.chains import ethereum as eth_chain
from bot.chains import solana as sol_chain
from bot.services import alert_engine, label_service, price_service
from bot.utils.formatter import format_scan_result, format_whale_list_entry
from bot.utils.helpers import (
    chain_emoji,
    detect_chain,
    format_usd,
    relative_time,
    shorten_address,
)

logger = logging.getLogger("whalegod.commands")

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _is_bot_admin(update: Update) -> bool:
    """Check if user is the bot administrator (ADMIN_CHAT_ID)."""
    if not ADMIN_CHAT_ID or not update.effective_user:
        return False
    return update.effective_user.id == ADMIN_CHAT_ID


async def _is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is admin/creator in a group. Always True for DMs."""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return False
    if chat.type == "private":
        return True
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("creator", "administrator")
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Helpers — safe reply for groups, channels, edited msgs
# ---------------------------------------------------------------------------

WHALE_ART = r"""<pre>
        ____
    ___/ o  \___
   /    ____    \
  |   /    \    |
   \  \____/   /
    \__________/
  ~~~~~~~~~~~~~~~
   W H A L E G O D
</pre>"""


async def _reply(update: Update, text: str, **kwargs: Any) -> None:
    """Safe reply that works in DMs, groups, channels, and with edited msgs."""
    target = update.effective_message
    if target is None:
        return
    kwargs.setdefault("parse_mode", "HTML")
    kwargs.setdefault("disable_web_page_preview", True)
    try:
        await target.reply_text(text, **kwargs)
    except Exception:
        logger.exception("Failed to reply in chat %s", update.effective_chat.id if update.effective_chat else "?")


async def _reply_edit(update: Update, text: str, **kwargs: Any) -> Any:
    """Send a reply that can be edited later. Returns the sent message."""
    target = update.effective_message
    if target is None:
        return None
    kwargs.setdefault("parse_mode", "HTML")
    kwargs.setdefault("disable_web_page_preview", True)
    try:
        return await target.reply_text(text, **kwargs)
    except Exception:
        logger.exception("Failed to reply in chat %s", update.effective_chat.id if update.effective_chat else "?")
        return None


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message + auto-subscribe."""
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    await ensure_subscription(chat_id)

    chat_type = update.effective_chat.type
    if chat_type in ("group", "supergroup"):
        group_note = (
            "\n\n👥 <b>Group Mode Active</b>\n"
            "all commands work here fren! everyone in the group "
            "can use /whale, /scan, /trending etc.\n"
            "admins can use /settings to configure alerts for this group 🔧"
        )
    else:
        group_note = ""

    msg = (
        f"{WHALE_ART}\n"
        f"gm ser, welcome to <b>WHALEGOD</b> 🐋\n"
        f"\n"
        f"<i>wen whale moves, we move first ser.</i>\n"
        f"\n"
        f"the most based on-chain whale tracker for Solana ◎ and Ethereum ⟠.\n"
        f"real-time alerts, zero BS, pure alpha. 100% free forever. 🧠🔥\n"
        f"\n"
        f"🐋 we are the WHALEGOD community — degens united, watching the ocean together.\n"
        f"every anon here is fam. wagmi 🤝💎\n"
        f"\n"
        f"<b>Quick Start:</b>\n"
        f"🐋 /whale — recent whale movements\n"
        f"🏆 /top — biggest moves today\n"
        f"🎯 /track — stalk a wallet\n"
        f"🔍 /scan — scan any token\n"
        f"🔥 /trending — what's hot rn\n"
        f"⛽ /gas — gas prices\n"
        f"📖 /help — full command list\n"
        f"\n"
        f"alerts are ON by default. customize with /settings\n"
        f"{group_note}\n"
        f"<i>you're part of the pod now ser. the ocean awaits 🌊🐋</i>"
    )

    await _reply(update, msg)


# ---------------------------------------------------------------------------
# /whale
# ---------------------------------------------------------------------------

async def cmd_whale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /whale [sol|eth] — recent whale movements."""
    args = context.args or []
    chain_filter = None
    if args:
        arg = args[0].lower()
        if arg in ("sol", "solana"):
            chain_filter = "solana"
        elif arg in ("eth", "ethereum"):
            chain_filter = "ethereum"

    logs = await get_recent_whale_logs(chain=chain_filter, limit=5)

    if not logs:
        ocean_msg = (
            "🐋 <b>Whale Watch</b>\n\n"
            "the ocean is calm right now ser... no whale movements detected 🌊😴\n\n"
            "the whales are sleeping but WHALEGOD never does 👁️\n"
            "check back soon fren — wen they move, you'll know first 🔔\n\n"
            "💡 use /top for biggest moves today\n"
            "💡 use /trending to see what's poppin rn 🔥"
        )
        await _reply(update, ocean_msg)
        return

    header = "🐋 <b>Recent Whale Movements</b>"
    if chain_filter:
        c = chain_emoji(chain_filter)
        header += f" — {c} {chain_filter.upper()}"
    header += "\n\n"

    entries = []
    for i, log in enumerate(logs, 1):
        entries.append(format_whale_list_entry(i, log))

    msg = header + "\n\n".join(entries)
    msg += "\n\n💡 use /top for biggest moves | /trending for hot tokens 🔥"

    await _reply(update, msg)


# ---------------------------------------------------------------------------
# /top
# ---------------------------------------------------------------------------

async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /top [24h|1h|7d] — top whale movements by volume."""
    args = context.args or []
    time_arg = args[0].lower() if args else "24h"

    hours_map = {"1h": 1, "24h": 24, "7d": 168, "1d": 24}
    hours = hours_map.get(time_arg, 24)
    time_label = time_arg if time_arg in hours_map else "24h"

    logs = await get_top_whale_logs(hours=hours, limit=10)
    volume = await get_whale_volume(hours=hours)

    if not logs:
        msg = (
            f"🏆 <b>Top Whale Moves ({time_label})</b>\n\n"
            f"no whale activity in this period ser 🌊\n"
            f"the ocean is sleeping... for now 😴\n"
            f"but wen it wakes up, we'll be ready 💪\n\n"
            f"💡 try /whale for recent activity\n"
            f"💡 try /trending for what's hot rn 🔥"
        )
        await _reply(update, msg)
        return

    medals = ["🥇", "🥈", "🥉"]
    header = f"🏆 <b>Top Whale Moves ({time_label})</b>\n\n"

    entries = []
    for i, log in enumerate(logs, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        entries.append(format_whale_list_entry(i, log, medal=medal))

    msg = header + "\n\n".join(entries)
    msg += f"\n\n📊 Total whale volume ({time_label}): <b>{format_usd(volume)}</b>"
    msg += "\n\n<i>the WHALEGOD pod sees everything ser 👁️🐋</i>"

    await _reply(update, msg)


# ---------------------------------------------------------------------------
# /track
# ---------------------------------------------------------------------------

async def cmd_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /track <address> [label] — add a wallet to tracking."""
    if not update.effective_user or not update.effective_chat:
        return
    args = context.args or []
    if not args:
        msg = (
            "🎯 <b>Track a Wallet</b>\n\n"
            "usage: <code>/track &lt;wallet_address&gt; [label]</code>\n\n"
            "examples:\n"
            "<code>/track 0x28C6c06298d514Db089934071355E5743bf21d60</code>\n"
            '<code>/track 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM "My Alpha Wallet"</code>\n\n'
            "we auto-detect the chain (SOL/ETH) from the address 🧠\n"
            f"max {MAX_WALLETS_PER_USER} wallets per user — choose wisely fren 💎"
        )
        await _reply(update, msg)
        return

    address = args[0]
    label = " ".join(args[1:]).strip('"\'') if len(args) > 1 else None

    chain = detect_chain(address)
    if not chain:
        await _reply(
            update,
            "❌ ser that doesn't look like a valid wallet address 🤔\n\n"
            "needs to be:\n"
            "• <b>Solana</b> — base58 address (32-44 chars)\n"
            "• <b>Ethereum</b> — 0x + 40 hex chars\n\n"
            "double-check and try again fren 🔍",
        )
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    count = await count_user_wallets(user_id)
    if count >= MAX_WALLETS_PER_USER:
        await _reply(
            update,
            f"⚠️ you're already tracking {count}/{MAX_WALLETS_PER_USER} wallets ser\n"
            f"remove one with /untrack to make room 🧹\n"
            f"use /watchlist to see your current wallets 📋",
        )
        return

    known = label_service.get_label(chain, address)
    if known["type"] != "unknown" and not label:
        label = known["name"]

    success = await add_tracked_wallet(user_id, chat_id, address, chain, label)

    if success:
        c = chain_emoji(chain)
        label_msg = f'\n🏷️ identified as: <b>{known["name"]}</b>' if known["type"] != "unknown" else ""
        if label and known["type"] == "unknown":
            label_msg = f"\n🏷️ labeled as: <b>{label}</b>"

        await _reply(
            update,
            f"🎯 Wallet locked in ser. We're stalking now. 🕵️\n\n"
            f"{c} <code>{address}</code>{label_msg}\n\n"
            f"you'll get alerts wen this wallet makes moves 💎\n"
            f"tracking {count + 1}/{MAX_WALLETS_PER_USER} wallets\n\n"
            f"<i>the WHALEGOD pod has eyes on this one 👁️🐋</i>",
        )
    else:
        await _reply(
            update,
            "you're already on this one fren 💎\n"
            "diamond hands don't need to track twice 🙌\n"
            "use /watchlist to see all your tracked wallets",
        )


# ---------------------------------------------------------------------------
# /untrack
# ---------------------------------------------------------------------------

async def cmd_untrack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /untrack <address> — remove a tracked wallet."""
    if not update.effective_user:
        return
    args = context.args or []
    if not args:
        await _reply(
            update,
            "🗑️ <b>Untrack a Wallet</b>\n\n"
            "usage: <code>/untrack &lt;wallet_address&gt;</code>\n\n"
            "use /watchlist to see which wallets you're tracking 📋",
        )
        return

    address = args[0]
    user_id = update.effective_user.id

    removed = await remove_tracked_wallet(user_id, address)
    if removed:
        await _reply(
            update,
            f"🗑️ wallet untracked ser\n"
            f"<code>{shorten_address(address)}</code> is free from our gaze 👁️\n\n"
            f"use /watchlist to see remaining wallets\n"
            f"use /track to add a new one 🎯",
        )
    else:
        await _reply(
            update,
            "hmm, that wallet isn't in your tracking list fren 🤔\n"
            "check /watchlist to see what you're tracking\n"
            "maybe you already untracked it? 🧐",
        )


# ---------------------------------------------------------------------------
# /watchlist
# ---------------------------------------------------------------------------

async def cmd_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /watchlist — list all tracked wallets."""
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    wallets = await get_user_wallets(user_id)

    if not wallets:
        await _reply(
            update,
            "📋 <b>Your Watchlist</b>\n\n"
            "you're not tracking any wallets yet ser 🤷\n\n"
            "use /track &lt;address&gt; to start stalking a wallet 🕵️\n"
            "the WHALEGOD pod is waiting for your targets 🎯",
        )
        return

    header = "📋 <b>Your Watchlist</b>\n\n"
    lines = []

    for w in wallets:
        chain = w["chain"]
        addr = w["wallet_address"]
        label = w["label"] or "Unlabeled"
        created = w.get("created_at", "")
        c = chain_emoji(chain)

        links = SOLANA_LINKS if chain == "solana" else ETH_LINKS
        explorer_url = links["wallet"].format(address=addr)

        since = relative_time(created) if created else "unknown"
        lines.append(
            f"{c} <a href=\"{explorer_url}\">{shorten_address(addr)}</a>\n"
            f"   🏷️ {label} • tracking since {since}"
        )

    msg = header + "\n\n".join(lines)
    msg += f"\n\n🎯 tracking {len(wallets)}/{MAX_WALLETS_PER_USER} wallets"
    msg += "\n\n<i>the pod sees all 👁️🐋</i>"

    await _reply(update, msg)


# ---------------------------------------------------------------------------
# /scan
# ---------------------------------------------------------------------------

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scan <token_address> — scan a token's data."""
    args = context.args or []
    if not args:
        await _reply(
            update,
            "🔍 <b>Token Scanner</b>\n\n"
            "usage: <code>/scan &lt;token_address&gt;</code>\n\n"
            "paste any Solana or Ethereum token address\n"
            "and we'll fetch the alpha for you ser 🧠\n\n"
            "works for any token on DEX — rug or gem, we show the data 📊",
        )
        return

    token_address = args[0]
    chain = detect_chain(token_address)
    if not chain:
        await _reply(
            update,
            "❌ ser, that doesn't look like a valid token address 🤔\n"
            "paste the contract address from Solscan, Etherscan, or DexScreener",
        )
        return

    loading_msg = await _reply_edit(update, "🔍 scanning... hold on ser, fetching alpha 🧐⏳")
    if not loading_msg:
        return

    session = context.bot_data.get("session")
    if not session:
        await loading_msg.edit_text("❌ bot is still warming up ser — try again in a sec 🔄")
        return

    token_info = await price_service.get_token_info_dexscreener(session, chain, token_address)
    if not token_info:
        await loading_msg.edit_text(
            "ser, this token might be so degen even we can't find it 🥷\n\n"
            "possible reasons:\n"
            "• token hasn't been listed on any DEX yet\n"
            "• wrong contract address\n"
            "• rug deployed 2 seconds ago lol\n\n"
            "double-check the address and try again 🔍",
            parse_mode="HTML",
        )
        return

    msg = format_scan_result(chain, token_info)
    await loading_msg.edit_text(msg, parse_mode="HTML", disable_web_page_preview=True)


# ---------------------------------------------------------------------------
# /trending
# ---------------------------------------------------------------------------

async def cmd_trending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /trending — show trending/boosted tokens."""
    session = context.bot_data.get("session")
    if not session:
        await _reply(update, "❌ bot is still warming up ser — try again in a sec 🔄")
        return

    tokens = await price_service.get_trending_tokens(session)
    if not tokens:
        await _reply(
            update,
            "🔥 <b>Trending Tokens</b>\n\n"
            "couldn't fetch trending data right now ser 😔\n"
            "the DexScreener API might be napping\n"
            "try again in a bit fren! 🔄",
        )
        return

    msg = "🔥 <b>Trending Tokens</b> — what's hot rn\n\n"

    seen: set[str] = set()
    count = 0
    for token in tokens:
        if count >= 10:
            break

        chain_id = token.get("chainId", "")
        token_addr = token.get("tokenAddress", "")
        name = token.get("name", "Unknown")
        symbol = token.get("symbol", "???")

        key = f"{chain_id}:{token_addr}"
        if key in seen:
            continue
        seen.add(key)

        if chain_id not in ("solana", "ethereum"):
            continue

        c = chain_emoji(chain_id)
        chart_link = f"https://dexscreener.com/{chain_id}/{token_addr}"

        msg += (
            f"{count + 1}. {c} <b>{name}</b> (${symbol})\n"
            f'   🔗 <a href="{chart_link}">Chart</a> • 🚀 Boosted\n\n'
        )
        count += 1

    if count == 0:
        msg += "no SOL/ETH trending tokens found right now 🤷\n"

    msg += (
        "<i>dyor ser, boosted ≠ safe — always check rugcheck/contract.\n"
        "nfa, the WHALEGOD pod shares data not financial advice 🧠🐋</i>"
    )

    await _reply(update, msg)


# ---------------------------------------------------------------------------
# /chains
# ---------------------------------------------------------------------------

async def cmd_chains(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chains — show chain status and prices."""
    session = context.bot_data.get("session")
    if not session:
        await _reply(update, "❌ bot is still warming up ser — try again in a sec 🔄")
        return

    sol_price = await price_service.get_sol_price(session)
    eth_price = await price_service.get_eth_price(session)
    last_eth_block = eth_chain.get_last_polled_block()

    sol_status = "🟢" if sol_price > 0 else "🔴"
    eth_status = "🟢" if eth_price > 0 else "🔴"

    sol_last = alert_engine.last_event_time.get("solana", "N/A")
    eth_last = alert_engine.last_event_time.get("ethereum", "N/A")

    msg = (
        f"⛓️ <b>Chain Status</b>\n\n"
        f"◎ <b>Solana</b>\n"
        f"   Status: {sol_status} Active\n"
        f"   Price: <b>${sol_price:,.2f}</b>\n"
        f"   Data: Helius webhooks + DexScreener\n"
        f"   Last event: {relative_time(sol_last) if sol_last != 'N/A' else 'N/A'}\n"
        f'   🔗 <a href="https://solscan.io">Solscan</a> | '
        f'<a href="https://dexscreener.com/solana">DexScreener</a>\n\n'
        f"⟠ <b>Ethereum</b>\n"
        f"   Status: {eth_status} Active\n"
        f"   Price: <b>${eth_price:,.2f}</b>\n"
        f"   Data: Alchemy RPC + Etherscan polling\n"
        f"   Last block: {last_eth_block:,}\n"
        f"   Last event: {relative_time(eth_last) if eth_last != 'N/A' else 'N/A'}\n"
        f'   🔗 <a href="https://etherscan.io">Etherscan</a> | '
        f'<a href="https://dexscreener.com/ethereum">DexScreener</a>\n\n'
        f"<i>both chains running ser — the WHALEGOD pod misses nothing 🧠🐋</i>"
    )

    await _reply(update, msg)


# ---------------------------------------------------------------------------
# /gas
# ---------------------------------------------------------------------------

async def cmd_gas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /gas — show gas prices for ETH and SOL."""
    session = context.bot_data.get("session")
    if not session:
        await _reply(update, "❌ bot is still warming up ser — try again in a sec 🔄")
        return

    gas_oracle = await eth_chain.get_gas_oracle(session)
    sol_fees = await sol_chain.get_priority_fee(session)

    msg = "⛽ <b>Gas Tracker</b>\n\n"

    if gas_oracle:
        slow = gas_oracle["slow"]
        standard = gas_oracle["standard"]
        fast = gas_oracle["fast"]

        if fast < 20:
            gas_comment = "gas is cheap ser, time to ape 🦍 LFG"
        elif fast < 50:
            gas_comment = "gas is reasonable fren... go ahead and send it 👍"
        elif fast < 100:
            gas_comment = "gas is getting spicy... choose wisely anon 🌶️"
        else:
            gas_comment = "gas is insane rn, patience ser or get rekt on fees 🧘💸"

        msg += (
            f"⟠ <b>Ethereum Gas</b>\n"
            f"   🐢 Slow: <b>{slow:.0f}</b> gwei\n"
            f"   🚶 Standard: <b>{standard:.0f}</b> gwei\n"
            f"   🚀 Fast: <b>{fast:.0f}</b> gwei\n"
            f"   <i>{gas_comment}</i>\n"
            f'   🔗 <a href="https://etherscan.io/gastracker">Live Gas Tracker</a>\n\n'
        )
    else:
        msg += "⟠ <b>Ethereum Gas</b>: unavailable rn 😔\n\n"

    if sol_fees:
        msg += (
            f"◎ <b>Solana Priority Fees</b>\n"
            f"   Min: {sol_fees['min']:,.0f} micro-lamports\n"
            f"   Avg: {sol_fees['avg']:,.0f} micro-lamports\n"
            f"   Max: {sol_fees['max']:,.0f} micro-lamports\n"
            f"   <i>solana fees still basically free, based chain 😎</i>\n"
        )
    else:
        msg += "◎ <b>Solana Fees</b>: still basically free ser 😎 based chain energy\n"

    await _reply(update, msg)


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats — bot statistics (admin only)."""
    if not _is_bot_admin(update):
        await _reply(update, "🔒 this command is for bot admins only ser")
        return

    stats = await get_bot_stats()
    active_chats = await count_active_chats()
    tracked_count = await count_total_tracked_wallets()

    uptime_start = stats.get("uptime_start", "")
    if uptime_start:
        try:
            start_dt = datetime.fromisoformat(uptime_start.replace("Z", "+00:00"))
            uptime = datetime.now(timezone.utc) - start_dt
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            uptime_str = f"{days}d {hours}h {minutes}m"
        except Exception:
            uptime_str = "unknown"
    else:
        uptime_str = "unknown"

    whales = stats.get("total_whales_detected", 0)
    alerts = stats.get("total_alerts_sent", 0)

    health_lines = []
    for source, ts in price_service.last_success.items():
        age = time.monotonic() - ts
        status = "🟢" if age < 300 else "🟡" if age < 600 else "🔴"
        health_lines.append(f"   {status} {source}: {int(age)}s ago")

    msg = (
        f"📊 <b>WHALEGOD Stats</b>\n\n"
        f"🐋 Whales detected: <b>{whales:,}</b>\n"
        f"📨 Alerts sent: <b>{alerts:,}</b>\n"
        f"👥 Active groups/chats: <b>{active_chats}</b>\n"
        f"🎯 Wallets tracked: <b>{tracked_count}</b>\n"
        f"⏱️ Uptime: <b>{uptime_str}</b>\n"
        f"💰 Cost: <b>$0</b> (100% free APIs)\n\n"
    )

    if health_lines:
        msg += "<b>API Health:</b>\n" + "\n".join(health_lines) + "\n\n"

    msg += (
        "<i>WHALEGOD never sleeps ser 👁️🐋\n"
        "100% free, 100% based, powered by the community 💎</i>"
    )

    await _reply(update, msg)


# ---------------------------------------------------------------------------
# /donate
# ---------------------------------------------------------------------------

async def cmd_donate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /donate — show donation wallets."""
    msg = (
        "👑 <b>Support WHALEGOD</b>\n\n"
        "WHALEGOD is 100% free and always will be ser 💎\n"
        "but if the alpha we provide has saved your bags,\n"
        "the WHALEGOD remembers those who give back 👑🐋\n\n"
    )

    if DONATE_SOL:
        msg += f"◎ <b>SOL:</b>\n<code>{DONATE_SOL}</code>\n\n"
    if DONATE_ETH:
        msg += f"⟠ <b>ETH / ERC-20:</b>\n<code>{DONATE_ETH}</code>\n\n"
    if DONATE_BTC:
        msg += f"₿ <b>BTC:</b>\n<code>{DONATE_BTC}</code>\n\n"
    if DONATE_USDT_TRC20:
        msg += f"💵 <b>USDT (TRC-20):</b>\n<code>{DONATE_USDT_TRC20}</code>\n\n"

    if not any([DONATE_SOL, DONATE_ETH, DONATE_BTC, DONATE_USDT_TRC20]):
        msg += "<i>donation wallets not configured yet 😢</i>\n\n"

    msg += (
        "<i>every satoshi helps keep the whale watching alive 🐋💎\n"
        "donors get a special place in the WHALEGOD hall of fame 👑</i>"
    )

    await _reply(update, msg)


# ---------------------------------------------------------------------------
# /settings
# ---------------------------------------------------------------------------

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings — show current config with inline keyboard.

    In groups, only admins/creators can change settings.
    """
    if not update.effective_chat:
        return

    if not await _is_group_admin(update, context):
        await _reply(update, "🔒 only group admins can change settings ser")
        return

    from bot.handlers.callbacks import build_settings_message

    chat_id = update.effective_chat.id
    sub = await ensure_subscription(chat_id)

    msg, keyboard = build_settings_message(sub)
    await _reply(update, msg, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — full command reference."""
    chat_type_note = ""
    if update.effective_chat and update.effective_chat.type in ("group", "supergroup"):
        chat_type_note = (
            "\n\n👥 <b>Group Mode</b>\n"
            "all commands work in groups! everyone can use them.\n"
            "admins can customize alerts with /settings\n"
            "add WHALEGOD to any group for free whale intel 🐋"
        )

    msg = (
        "📖 <b>WHALEGOD Command Reference</b>\n\n"

        "🔍 <b>Whale Tracking</b>\n"
        "/whale [sol|eth] — recent whale movements\n"
        "/top [24h|1h|7d] — biggest whale moves\n"
        "/trending — trending tokens rn 🔥\n\n"

        "🎯 <b>Wallet Stalking</b>\n"
        "/track &lt;address&gt; [label] — track a wallet\n"
        "/untrack &lt;address&gt; — stop tracking\n"
        "/watchlist — your tracked wallets\n\n"

        "📊 <b>Market Intel</b>\n"
        "/scan &lt;token&gt; — scan any token\n"
        "/chains — chain status + live prices\n"
        "/gas — gas prices (ETH + SOL)\n\n"

        "⚙️ <b>Settings</b>\n"
        "/settings — alert preferences\n"
        "/stats — bot statistics\n\n"

        "💰 <b>Support</b>\n"
        "/donate — support WHALEGOD (optional)\n"
        f"{chat_type_note}\n\n"

        "<i>wen whale moves, we move first ser 🐋🔥\n"
        "100% free • 100% based • powered by degens for degens 💎\n"
        "you're part of the WHALEGOD pod now. wagmi 🤝🌊</i>"
    )

    await _reply(update, msg)
