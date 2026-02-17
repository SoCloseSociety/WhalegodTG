"""Address validation/shortening, USD/amount formatting, time helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone


def is_solana_address(address: str) -> bool:
    """Check if the string looks like a valid Solana base58 address."""
    return bool(re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", address))


def is_ethereum_address(address: str) -> bool:
    """Check if the string looks like a valid Ethereum hex address."""
    return bool(re.match(r"^0x[0-9a-fA-F]{40}$", address))


def detect_chain(address: str) -> str | None:
    """Return 'solana', 'ethereum', or None based on address format."""
    if is_ethereum_address(address):
        return "ethereum"
    if is_solana_address(address):
        return "solana"
    return None


def shorten_address(address: str, head: int = 4, tail: int = 4) -> str:
    """Shorten an address to ``head...tail`` format."""
    if len(address) <= head + tail + 3:
        return address
    return f"{address[:head]}...{address[-tail:]}"


def format_usd(value: float | None) -> str:
    """Smart-format a USD value.

    Examples::

        format_usd(1_250_000)   -> "$1.25M"
        format_usd(500_000)     -> "$500K"
        format_usd(50_000)      -> "$50,000"
        format_usd(1_234.56)    -> "$1,234.56"
    """
    if value is None:
        return "$?"
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000:
        return f"{sign}${abs_val / 1_000_000:.2f}M"
    if abs_val >= 100_000:
        return f"{sign}${abs_val / 1_000:.0f}K"
    if abs_val >= 1_000:
        return f"{sign}${abs_val:,.0f}"
    return f"{sign}${abs_val:,.2f}"


def format_amount(value: float, symbol: str = "") -> str:
    """Format a token amount with commas and optional symbol."""
    if value >= 1_000_000:
        formatted = f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        formatted = f"{value:,.2f}"
    elif value >= 1:
        formatted = f"{value:,.2f}"
    else:
        formatted = f"{value:.4f}"
    if symbol:
        return f"{formatted} {symbol}"
    return formatted


def relative_time(iso_or_dt: str | datetime) -> str:
    """Return a human-readable relative time string like '2m ago'."""
    if isinstance(iso_or_dt, str):
        try:
            dt = datetime.fromisoformat(iso_or_dt.replace("Z", "+00:00"))
        except ValueError:
            return "just now"
    else:
        dt = iso_or_dt

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = datetime.now(timezone.utc) - dt
    seconds = int(diff.total_seconds())
    if seconds < 0:
        seconds = 0

    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def chain_emoji(chain: str) -> str:
    """Return the appropriate chain symbol emoji."""
    return "◎" if chain == "solana" else "⟠"


def signal_emoji(signal: str) -> str:
    """Return emoji for a signal type."""
    return {
        "bullish": "📈",
        "bearish": "📉",
        "neutral": "➡️",
        "degen": "🐸",
        "alpha": "🧠",
        "caution": "⚠️",
    }.get(signal, "➡️")
