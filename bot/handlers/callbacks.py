"""Inline keyboard callback handlers for settings management."""

from __future__ import annotations

import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.database import ensure_subscription, update_subscription
from bot.utils.helpers import format_usd

logger = logging.getLogger("whalegod.callbacks")

# ---------------------------------------------------------------------------
# Settings message builder
# ---------------------------------------------------------------------------

def build_settings_message(
    sub: dict[str, Any],
) -> tuple[str, InlineKeyboardMarkup]:
    """Build the settings message and inline keyboard."""
    enabled = bool(sub.get("enabled", 1))
    enabled_str = "🟢 ON" if enabled else "🔴 OFF"

    sol_t = sub.get("min_sol_threshold", 500)
    eth_t = sub.get("min_eth_threshold", 50)
    usd_t = sub.get("min_usd_threshold", 50000)
    lp_t = sub.get("min_lp_threshold", 25000)

    show_cex_dep = "✅" if sub.get("show_cex_deposits", 1) else "❌"
    show_cex_wd = "✅" if sub.get("show_cex_withdrawals", 1) else "❌"
    show_dex = "✅" if sub.get("show_dex_swaps", 1) else "❌"
    show_lp = "✅" if sub.get("show_lp_events", 1) else "❌"
    show_bridge = "✅" if sub.get("show_bridges", 1) else "❌"

    msg = (
        f"⚙️ <b>Alert Settings</b>\n\n"
        f"<b>Status:</b> {enabled_str}\n\n"
        f"<b>Thresholds:</b>\n"
        f"◎ SOL: {sol_t:,.0f} SOL\n"
        f"⟠ ETH: {eth_t:,.0f} ETH\n"
        f"💰 USD: {format_usd(usd_t)}\n"
        f"💧 LP: {format_usd(lp_t)}\n\n"
        f"<b>Filters:</b>\n"
        f"{show_cex_dep} CEX Deposits\n"
        f"{show_cex_wd} CEX Withdrawals\n"
        f"{show_dex} DEX Swaps\n"
        f"{show_lp} LP Events\n"
        f"{show_bridge} Bridges\n\n"
        f"<i>tap buttons below to adjust ser 👇</i>"
    )

    keyboard = InlineKeyboardMarkup([
        # Row 1: Master toggle
        [InlineKeyboardButton(
            f"{'🔴 Turn OFF' if enabled else '🟢 Turn ON'} Alerts",
            callback_data="settings:toggle_enabled",
        )],
        # Row 2: Category filters
        [
            InlineKeyboardButton(f"{show_cex_dep} CEX Dep", callback_data="settings:toggle_cex_deposits"),
            InlineKeyboardButton(f"{show_cex_wd} CEX Wd", callback_data="settings:toggle_cex_withdrawals"),
        ],
        [
            InlineKeyboardButton(f"{show_dex} DEX", callback_data="settings:toggle_dex_swaps"),
            InlineKeyboardButton(f"{show_lp} LP", callback_data="settings:toggle_lp_events"),
            InlineKeyboardButton(f"{show_bridge} Bridge", callback_data="settings:toggle_bridges"),
        ],
        # Row 3: SOL thresholds
        [InlineKeyboardButton("◎ SOL Threshold:", callback_data="settings:noop")],
        [
            InlineKeyboardButton("100", callback_data="settings:sol_t:100"),
            InlineKeyboardButton("250", callback_data="settings:sol_t:250"),
            InlineKeyboardButton("500", callback_data="settings:sol_t:500"),
            InlineKeyboardButton("1000", callback_data="settings:sol_t:1000"),
        ],
        # Row 4: ETH thresholds
        [InlineKeyboardButton("⟠ ETH Threshold:", callback_data="settings:noop")],
        [
            InlineKeyboardButton("10", callback_data="settings:eth_t:10"),
            InlineKeyboardButton("25", callback_data="settings:eth_t:25"),
            InlineKeyboardButton("50", callback_data="settings:eth_t:50"),
            InlineKeyboardButton("100", callback_data="settings:eth_t:100"),
        ],
        # Row 5: USD thresholds
        [InlineKeyboardButton("💰 USD Threshold:", callback_data="settings:noop")],
        [
            InlineKeyboardButton("$10K", callback_data="settings:usd_t:10000"),
            InlineKeyboardButton("$25K", callback_data="settings:usd_t:25000"),
            InlineKeyboardButton("$50K", callback_data="settings:usd_t:50000"),
            InlineKeyboardButton("$100K", callback_data="settings:usd_t:100000"),
        ],
        # Row 6: LP thresholds
        [InlineKeyboardButton("💧 LP Threshold:", callback_data="settings:noop")],
        [
            InlineKeyboardButton("$10K", callback_data="settings:lp_t:10000"),
            InlineKeyboardButton("$25K", callback_data="settings:lp_t:25000"),
            InlineKeyboardButton("$50K", callback_data="settings:lp_t:50000"),
            InlineKeyboardButton("$100K", callback_data="settings:lp_t:100000"),
        ],
    ])

    return msg, keyboard


# ---------------------------------------------------------------------------
# Callback dispatcher
# ---------------------------------------------------------------------------

async def handle_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle all settings inline keyboard callbacks."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    data = query.data
    if not data.startswith("settings:"):
        return

    parts = data.split(":")
    if len(parts) < 2:
        return

    action = parts[1]
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id

    # Ensure subscription exists
    sub = await ensure_subscription(chat_id)

    if action == "noop":
        return

    # Toggle actions
    toggle_map: dict[str, str] = {
        "toggle_enabled": "enabled",
        "toggle_cex_deposits": "show_cex_deposits",
        "toggle_cex_withdrawals": "show_cex_withdrawals",
        "toggle_dex_swaps": "show_dex_swaps",
        "toggle_lp_events": "show_lp_events",
        "toggle_bridges": "show_bridges",
    }

    if action in toggle_map:
        column = toggle_map[action]
        current = sub.get(column, 1)
        new_val = 0 if current else 1
        await update_subscription(chat_id, **{column: new_val})
        sub[column] = new_val

    # Threshold actions
    elif action == "sol_t" and len(parts) == 3:
        val = float(parts[2])
        await update_subscription(chat_id, min_sol_threshold=val)
        sub["min_sol_threshold"] = val

    elif action == "eth_t" and len(parts) == 3:
        val = float(parts[2])
        await update_subscription(chat_id, min_eth_threshold=val)
        sub["min_eth_threshold"] = val

    elif action == "usd_t" and len(parts) == 3:
        val = float(parts[2])
        await update_subscription(chat_id, min_usd_threshold=val)
        sub["min_usd_threshold"] = val

    elif action == "lp_t" and len(parts) == 3:
        val = float(parts[2])
        await update_subscription(chat_id, min_lp_threshold=val)
        sub["min_lp_threshold"] = val

    # Rebuild settings message
    msg, keyboard = build_settings_message(sub)

    try:
        await query.edit_message_text(
            msg, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True
        )
    except Exception:
        logger.exception("Failed to edit settings message")
