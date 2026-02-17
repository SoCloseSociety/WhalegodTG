"""Message templates and smart link builder for Telegram HTML messages."""

from __future__ import annotations

from typing import Any

from bot.config import (
    ETH_LINKS,
    SOLANA_LINKS,
    SOL_MINT,
    TX_CATEGORIES,
)
from bot.utils.helpers import (
    chain_emoji,
    format_amount,
    format_usd,
    relative_time,
    shorten_address,
    signal_emoji,
)
from bot.utils.whale_quotes import get_commentary


def build_smart_links(
    chain: str,
    tx_hash: str,
    from_address: str | None = None,
    to_address: str | None = None,
    token_address: str | None = None,
) -> str:
    """Build an HTML smart links section for an alert message."""
    links_map = SOLANA_LINKS if chain == "solana" else ETH_LINKS
    lines: list[str] = []

    # Transaction link
    if tx_hash:
        tx_url = links_map["tx"].format(tx_hash=tx_hash)
        lines.append(f'• <a href="{tx_url}">View Transaction</a>')

    # Sender / receiver links
    sender_parts: list[str] = []
    if from_address:
        wallet_url = links_map["wallet"].format(address=from_address)
        sender_parts.append(f'<a href="{wallet_url}">Sender</a>')
    if to_address:
        wallet_url = links_map["wallet"].format(address=to_address)
        sender_parts.append(f'<a href="{wallet_url}">Receiver</a>')
    if sender_parts:
        lines.append(f"• {' | '.join(sender_parts)}")

    # Chart / analysis links (only for non-native tokens)
    is_native = (
        token_address is None
        or token_address == SOL_MINT
        or (token_address and token_address.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    )

    if token_address and not is_native:
        chart_url = links_map["chart"].format(token_address=token_address)
        lines.append(f'• <a href="{chart_url}">Chart</a>')

        if chain == "solana":
            birdeye_url = links_map["birdeye"].format(token_address=token_address)
            lines.append(f'• <a href="{birdeye_url}">Birdeye</a>')
            rugcheck_url = links_map["rugcheck"].format(token_address=token_address)
            lines.append(f'• <a href="{rugcheck_url}">Rugcheck</a>')
        else:
            dextools_url = links_map["dextools"].format(token_address=token_address)
            lines.append(f'• <a href="{dextools_url}">DexTools</a>')

    return "\n".join(lines)


def format_whale_alert(event: dict[str, Any]) -> str:
    """Format a whale event into a full Telegram HTML alert message."""
    chain = event.get("chain", "solana")
    tx_hash = event.get("tx_hash", "")
    from_addr = event.get("from_address", "")
    to_addr = event.get("to_address", "")
    from_label = event.get("from_label", "Unknown Wallet")
    to_label = event.get("to_label", "Unknown Wallet")
    amount = event.get("amount", 0)
    symbol = event.get("token_symbol", "")
    token_address = event.get("token_address")
    usd_value = event.get("usd_value", 0)
    tx_category = event.get("tx_category", "unknown")
    sig = event.get("signal", "neutral")
    timestamp = event.get("timestamp", "")

    cat_info = TX_CATEGORIES.get(tx_category, TX_CATEGORIES["unknown"])
    cat_emoji = cat_info["emoji"]
    cat_label = cat_info["label"]
    sig_icon = signal_emoji(sig)
    c_emoji = chain_emoji(chain)
    chain_name = chain.upper()

    commentary = get_commentary(usd_value or 0, tx_category)
    links = build_smart_links(chain, tx_hash, from_addr, to_addr, token_address)

    time_str = relative_time(timestamp) if timestamp else "just now"

    msg = (
        f"🐋 <b>WHALE ALERT — {c_emoji} {chain_name}</b> 🐋\n"
        f"\n"
        f"{cat_emoji} <b>{cat_label}</b> • Signal: {sig_icon} {sig.capitalize()}\n"
        f"\n"
        f"💰 {format_amount(amount, symbol)} ({format_usd(usd_value)})\n"
        f"📤 From: <b>{from_label}</b> ({shorten_address(from_addr)})\n"
        f"📥 To: <b>{to_label}</b> ({shorten_address(to_addr)})\n"
        f"⏰ {time_str}\n"
        f"\n"
        f"🔗 <b>Links:</b>\n"
        f"{links}\n"
        f"\n"
        f"<i>{commentary}</i>"
    )
    return msg


def format_whale_list_entry(
    idx: int, log: dict[str, Any], medal: str = ""
) -> str:
    """Format a single whale log entry for /whale or /top commands."""
    chain = log.get("chain", "solana")
    tx_category = log.get("tx_category", "unknown")
    amount = log.get("amount", 0)
    symbol = log.get("token_symbol", "")
    usd_value = log.get("usd_value", 0)
    from_label = log.get("from_label", "Unknown")
    to_label = log.get("to_label", "Unknown")
    timestamp = log.get("timestamp", "")
    tx_hash = log.get("tx_hash", "")

    cat_info = TX_CATEGORIES.get(tx_category, TX_CATEGORIES["unknown"])
    c_emoji = chain_emoji(chain)
    links_map = SOLANA_LINKS if chain == "solana" else ETH_LINKS
    tx_url = links_map["tx"].format(tx_hash=tx_hash) if tx_hash else ""

    prefix = medal if medal else f"{idx}."
    time_str = relative_time(timestamp) if timestamp else ""

    line = (
        f"{prefix} {c_emoji} {cat_info['emoji']} "
        f"{format_amount(amount, symbol)} ({format_usd(usd_value)})\n"
        f"    {from_label} → {to_label}"
    )
    if time_str:
        line += f" • {time_str}"
    if tx_url:
        line += f'\n    <a href="{tx_url}">tx</a>'

    return line


def format_flood_digest(events: list[dict[str, Any]], total_count: int) -> str:
    """Format a flood-mode digest message for many whale events."""
    msg = (
        f"🐋🌊 <b>WHALE STORM DETECTED</b> 🌊🐋\n"
        f"\n"
        f"⚡ <b>{total_count} whale movements</b> in the last minute!\n"
        f"\n"
        f"<b>Top 5 by volume:</b>\n"
    )

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, evt in enumerate(events[:5]):
        chain = evt.get("chain", "solana")
        c_emoji = chain_emoji(chain)
        amount = evt.get("amount", 0)
        symbol = evt.get("token_symbol", "")
        usd_value = evt.get("usd_value", 0)

        msg += f"{medals[i]} {c_emoji} {format_amount(amount, symbol)} ({format_usd(usd_value)})\n"

    msg += (
        f"\n"
        f"💡 Use /whale to see the latest movements\n"
        f"\n"
        f"<i>the ocean is going CRAZY right now ser 🌊🐋🔥</i>"
    )
    return msg


def format_scan_result(
    chain: str,
    token_info: dict[str, Any],
    recent_txs: list[dict[str, Any]] | None = None,
) -> str:
    """Format a /scan result message with deep DexScreener analysis."""
    base_token = token_info.get("baseToken", {})
    quote_token = token_info.get("quoteToken", {})
    name = base_token.get("name", "Unknown")
    symbol = base_token.get("symbol", "???")
    quote_symbol = quote_token.get("symbol", "")
    price_usd = token_info.get("priceUsd", "0")
    price_change = token_info.get("priceChange", {})
    change_5m = price_change.get("m5", 0)
    change_1h = price_change.get("h1", 0)
    change_6h = price_change.get("h6", 0)
    change_24h = price_change.get("h24", 0)
    volume = token_info.get("volume", {})
    volume_5m = volume.get("m5", 0)
    volume_1h = volume.get("h1", 0)
    volume_6h = volume.get("h6", 0)
    volume_24h = volume.get("h24", 0)
    liquidity = token_info.get("liquidity", {}).get("usd", 0)
    fdv = token_info.get("fdv", 0)
    market_cap = token_info.get("marketCap", 0)
    token_address = base_token.get("address", "")
    dex_id = token_info.get("dexId", "unknown")
    pair_created = token_info.get("pairCreatedAt", 0)

    # Buy/sell transaction counts
    txns = token_info.get("txns", {})
    buys_5m = txns.get("m5", {}).get("buys", 0)
    sells_5m = txns.get("m5", {}).get("sells", 0)
    buys_1h = txns.get("h1", {}).get("buys", 0)
    sells_1h = txns.get("h1", {}).get("sells", 0)
    buys_24h = txns.get("h24", {}).get("buys", 0)
    sells_24h = txns.get("h24", {}).get("sells", 0)

    c_emoji = chain_emoji(chain)
    chain_name = chain.upper()

    change_24h_f = float(change_24h) if change_24h else 0
    change_emoji = "📈" if change_24h_f >= 0 else "📉"
    change_str = f"{change_24h_f:+.2f}%" if change_24h else "N/A"

    links_map = SOLANA_LINKS if chain == "solana" else ETH_LINKS
    chart_url = links_map["chart"].format(token_address=token_address)

    # Pair age calculation
    pair_age_str = ""
    if pair_created:
        from datetime import datetime, timezone
        try:
            created_dt = datetime.fromtimestamp(pair_created / 1000, tz=timezone.utc)
            age = datetime.now(timezone.utc) - created_dt
            if age.days > 365:
                pair_age_str = f"{age.days // 365}y {age.days % 365}d"
            elif age.days > 0:
                pair_age_str = f"{age.days}d {age.seconds // 3600}h"
            elif age.seconds > 3600:
                pair_age_str = f"{age.seconds // 3600}h {(age.seconds % 3600) // 60}m"
            else:
                pair_age_str = f"{age.seconds // 60}m"
        except (ValueError, OSError):
            pair_age_str = ""

    # Rug risk assessment
    rug_risk, risk_emoji = _assess_rug_risk(
        liquidity=float(liquidity or 0),
        volume_24h=float(volume_24h or 0),
        fdv=float(fdv or 0),
        buys_24h=buys_24h,
        sells_24h=sells_24h,
        pair_age_str=pair_age_str,
    )

    # Build message
    msg = (
        f"🔍 <b>Token Scan — {c_emoji} {chain_name}</b>\n"
        f"\n"
        f"<b>{name}</b> (${symbol})"
    )
    if quote_symbol:
        msg += f" / {quote_symbol}"
    msg += f"\n🏷️ DEX: {dex_id.capitalize()}"
    if pair_age_str:
        msg += f" • Age: {pair_age_str}"

    msg += (
        f"\n\n💰 <b>Price:</b> ${price_usd}\n"
        f"{change_emoji} 5m: {_fmt_change(change_5m)} • "
        f"1h: {_fmt_change(change_1h)} • "
        f"6h: {_fmt_change(change_6h)} • "
        f"24h: {change_str}\n"
    )

    msg += (
        f"\n📊 <b>Volume:</b>\n"
        f"  5m: {format_usd(float(volume_5m or 0))} • "
        f"1h: {format_usd(float(volume_1h or 0))} • "
        f"24h: {format_usd(float(volume_24h or 0))}\n"
    )

    # Buy/Sell ratio
    msg += f"\n🔄 <b>Buys / Sells:</b>\n"
    msg += f"  5m: {buys_5m}B / {sells_5m}S"
    if buys_5m + sells_5m > 0:
        ratio_5m = buys_5m / (buys_5m + sells_5m) * 100
        msg += f" ({ratio_5m:.0f}% buy)"
    msg += f"\n  1h: {buys_1h}B / {sells_1h}S"
    if buys_1h + sells_1h > 0:
        ratio_1h = buys_1h / (buys_1h + sells_1h) * 100
        msg += f" ({ratio_1h:.0f}% buy)"
    msg += f"\n  24h: {buys_24h}B / {sells_24h}S"
    if buys_24h + sells_24h > 0:
        ratio_24h = buys_24h / (buys_24h + sells_24h) * 100
        msg += f" ({ratio_24h:.0f}% buy)"
    msg += "\n"

    # Market metrics
    msg += f"\n💧 Liquidity: {format_usd(float(liquidity or 0))}\n"
    if market_cap:
        msg += f"📈 Market Cap: {format_usd(float(market_cap))}\n"
    msg += f"📈 FDV: {format_usd(float(fdv or 0))}\n"

    # Rug risk assessment
    msg += f"\n{risk_emoji} <b>Risk Level:</b> {rug_risk}\n"

    # Links
    msg += (
        f"\n🔗 <b>Links:</b>\n"
        f'• <a href="{chart_url}">Chart</a>'
    )

    if chain == "solana":
        birdeye_url = links_map["birdeye"].format(token_address=token_address)
        rugcheck_url = links_map["rugcheck"].format(token_address=token_address)
        jupiter_url = links_map["jupiter"].format(token_address=token_address)
        msg += f'\n• <a href="{birdeye_url}">Birdeye</a>'
        msg += f'\n• <a href="{rugcheck_url}">Rugcheck</a>'
        msg += f'\n• <a href="{jupiter_url}">Swap on Jupiter</a>'
    else:
        dextools_url = links_map["dextools"].format(token_address=token_address)
        uniswap_url = links_map["uniswap"].format(token_address=token_address)
        msg += f'\n• <a href="{dextools_url}">DexTools</a>'
        msg += f'\n• <a href="{uniswap_url}">Swap on Uniswap</a>'

    if recent_txs:
        msg += "\n\n<b>Recent whale TXs:</b>\n"
        for i, tx in enumerate(recent_txs[:5], 1):
            amount = tx.get("amount", 0)
            symbol_tx = tx.get("token_symbol", "")
            usd_val = tx.get("usd_value", 0)
            msg += f"{i}. {format_amount(amount, symbol_tx)} ({format_usd(usd_val)})\n"

    msg += "\n<i>dyor ser, nfa 🧠</i>"
    return msg


def _fmt_change(val: Any) -> str:
    """Format a price change percentage."""
    if val is None or val == 0:
        return "N/A"
    f = float(val)
    return f"{f:+.2f}%"


def _assess_rug_risk(
    liquidity: float,
    volume_24h: float,
    fdv: float,
    buys_24h: int,
    sells_24h: int,
    pair_age_str: str,
) -> tuple[str, str]:
    """Assess rug pull risk based on on-chain metrics.

    Returns (risk_label, risk_emoji).
    """
    risk_score = 0
    flags: list[str] = []

    # Low liquidity check
    if liquidity < 5_000:
        risk_score += 3
        flags.append("very low liq")
    elif liquidity < 25_000:
        risk_score += 2
        flags.append("low liq")
    elif liquidity < 100_000:
        risk_score += 1

    # FDV vs liquidity ratio (extremely high = danger)
    if liquidity > 0 and fdv > 0:
        fdv_liq_ratio = fdv / liquidity
        if fdv_liq_ratio > 100:
            risk_score += 3
            flags.append("FDV/liq >100x")
        elif fdv_liq_ratio > 50:
            risk_score += 2
            flags.append("FDV/liq >50x")
        elif fdv_liq_ratio > 20:
            risk_score += 1

    # Volume vs liquidity (wash trading indicator)
    if liquidity > 0 and volume_24h > 0:
        vol_liq_ratio = volume_24h / liquidity
        if vol_liq_ratio > 50:
            risk_score += 2
            flags.append("suspicious vol/liq")

    # Buy/sell imbalance (heavy sells = dump)
    total_txs = buys_24h + sells_24h
    if total_txs > 10:
        sell_ratio = sells_24h / total_txs
        if sell_ratio > 0.75:
            risk_score += 2
            flags.append("heavy selling")
        elif sell_ratio > 0.6:
            risk_score += 1

    # Very new token
    if pair_age_str and ("m" in pair_age_str and "d" not in pair_age_str and "y" not in pair_age_str and "h" not in pair_age_str):
        risk_score += 2
        flags.append("very new")
    elif pair_age_str and "h" in pair_age_str and "d" not in pair_age_str and "y" not in pair_age_str:
        risk_score += 1
        flags.append("new pair")

    # Build result
    if risk_score >= 6:
        risk_label = "EXTREME"
        flag_str = " (" + ", ".join(flags[:3]) + ")" if flags else ""
        return f"{risk_label}{flag_str}", "🔴"
    if risk_score >= 4:
        risk_label = "HIGH"
        flag_str = " (" + ", ".join(flags[:3]) + ")" if flags else ""
        return f"{risk_label}{flag_str}", "🟠"
    if risk_score >= 2:
        risk_label = "MODERATE"
        flag_str = " (" + ", ".join(flags[:2]) + ")" if flags else ""
        return f"{risk_label}{flag_str}", "🟡"
    return "LOW", "🟢"
