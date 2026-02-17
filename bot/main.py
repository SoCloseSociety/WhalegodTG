"""Entry point: bot init, webhook server, health server, scheduler, signal handling."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
import time
from typing import Any

import aiohttp
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import BotCommand, BotCommandScopeChat, Bot
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from bot import __version__
from bot.config import (
    ADMIN_CHAT_ID,
    HEALTH_PORT,
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_HOST,
    WEBHOOK_PORT,
    validate_env,
)
from bot.database import backup_db, cleanup, close_db, init_db
from bot.handlers.callbacks import handle_settings_callback
from bot.handlers.commands import (
    cmd_chains,
    cmd_donate,
    cmd_gas,
    cmd_help,
    cmd_scan,
    cmd_settings,
    cmd_start,
    cmd_stats,
    cmd_top,
    cmd_track,
    cmd_trending,
    cmd_untrack,
    cmd_watchlist,
    cmd_whale,
)
from bot.services import alert_engine, price_service

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("whalegod")

# Quiet noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_start_time: float = 0.0
_session: aiohttp.ClientSession | None = None
_scheduler: AsyncIOScheduler | None = None
_app: Application | None = None
_health_runner: web.AppRunner | None = None
_webhook_runner: web.AppRunner | None = None


# ---------------------------------------------------------------------------
# Health check server
# ---------------------------------------------------------------------------

async def health_handler(request: web.Request) -> web.Response:
    """GET /health — returns JSON health status."""
    uptime = time.monotonic() - _start_time

    from bot.chains.ethereum import get_last_polled_block

    body = {
        "status": "ok",
        "bot": "WHALEGOD",
        "version": __version__,
        "uptime_seconds": int(uptime),
        "chains": {
            "solana": {
                "status": "ok",
                "last_event": alert_engine.last_event_time.get("solana", "N/A"),
            },
            "ethereum": {
                "status": "ok",
                "last_block": get_last_polled_block(),
                "last_poll": alert_engine.last_event_time.get("ethereum", "N/A"),
            },
        },
    }
    return web.json_response(body)


async def start_health_server() -> None:
    """Start the health check server on port 8080."""
    global _health_runner
    app = web.Application()
    app.router.add_get("/health", health_handler)
    _health_runner = web.AppRunner(app)
    await _health_runner.setup()
    site = web.TCPSite(_health_runner, "0.0.0.0", HEALTH_PORT)
    await site.start()
    logger.info("Health server started on port %d", HEALTH_PORT)


# ---------------------------------------------------------------------------
# Helius webhook server
# ---------------------------------------------------------------------------

async def helius_webhook_handler(request: web.Request) -> web.Response:
    """POST /webhook/helius — receive Helius enhanced transaction events."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        logger.warning("Helius webhook: invalid JSON payload")
        return web.Response(status=400, text="Invalid JSON")

    if not isinstance(body, list):
        # Some events come as single objects
        body = [body]

    bot = _app.bot if _app else None
    session = _session

    if not bot or not session:
        logger.error("Helius webhook: bot or session not ready")
        return web.Response(status=503, text="Not ready")

    for event in body:
        if not isinstance(event, dict) or "signature" not in event:
            logger.warning("Helius webhook: skipping event without signature")
            continue
        # Process each event asynchronously — don't block the response
        asyncio.create_task(_safe_process_event(event, session, bot))

    return web.Response(status=200, text="OK")


async def _safe_process_event(
    event: dict[str, Any],
    session: aiohttp.ClientSession,
    bot: Bot,
) -> None:
    """Safely process a Helius event, catching all exceptions."""
    try:
        await alert_engine.process_helius_event(event, session, bot)
    except Exception:
        logger.exception("Error processing Helius event: %s", event.get("signature", "?"))


async def start_webhook_server() -> None:
    """Start the Helius webhook receiver on WEBHOOK_PORT."""
    global _webhook_runner
    app = web.Application()
    app.router.add_post("/webhook/helius", helius_webhook_handler)
    _webhook_runner = web.AppRunner(app)
    await _webhook_runner.setup()
    site = web.TCPSite(_webhook_runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()
    logger.info("Webhook server started on port %d", WEBHOOK_PORT)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

def setup_scheduler(session: aiohttp.ClientSession, bot: Bot) -> AsyncIOScheduler:
    """Configure and return the APScheduler instance."""
    scheduler = AsyncIOScheduler()

    # ETH polling — every 60s
    scheduler.add_job(
        alert_engine.poll_ethereum,
        "interval",
        seconds=60,
        args=[session, bot],
        id="eth_poll",
        max_instances=1,
        misfire_grace_time=30,
    )

    # Tracked wallet check — every 5 min
    scheduler.add_job(
        alert_engine.check_tracked_wallets,
        "interval",
        minutes=5,
        args=[session, bot],
        id="tracked_wallets",
        max_instances=1,
        misfire_grace_time=30,
    )

    # Price refresh — every 60s
    scheduler.add_job(
        price_service.refresh_base_prices,
        "interval",
        seconds=60,
        args=[session],
        id="price_refresh",
        max_instances=1,
        misfire_grace_time=30,
    )

    # DB cleanup — daily at 03:00 UTC
    scheduler.add_job(
        cleanup,
        "cron",
        hour=3,
        minute=0,
        id="db_cleanup",
        max_instances=1,
        misfire_grace_time=30,
    )

    # DB backup — daily at 04:00 UTC (after cleanup)
    scheduler.add_job(
        backup_db,
        "cron",
        hour=4,
        minute=0,
        id="db_backup",
        max_instances=1,
        misfire_grace_time=30,
    )

    # Health log — every 5 min
    scheduler.add_job(
        _log_health,
        "interval",
        minutes=5,
        id="health_log",
        max_instances=1,
        misfire_grace_time=30,
    )

    return scheduler


async def _log_health() -> None:
    """Log API health metrics."""
    now = time.monotonic()
    last_success = price_service.last_success
    parts = []
    for source, ts in last_success.items():
        age = int(now - ts)
        status = "OK" if age < 300 else "WARN" if age < 600 else "STALE"
        parts.append(f"{source}={status}({age}s)")

    if parts:
        logger.info("API health: %s", ", ".join(parts))
    else:
        logger.info("API health: no calls recorded yet")


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler — log and suppress."""
    logger.error("Telegram handler error: %s", context.error, exc_info=context.error)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    """Main async entry point."""
    global _start_time, _session, _scheduler, _app

    _start_time = time.monotonic()

    logger.info("=" * 50)
    logger.info("WHALEGOD v%s starting up...", __version__)
    logger.info("=" * 50)

    # Validate environment
    validate_env()

    # Initialize database
    await init_db()

    # Create shared aiohttp session
    timeout = aiohttp.ClientTimeout(total=30)
    _session = aiohttp.ClientSession(timeout=timeout)

    # Build Telegram application
    _app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Register command handlers
    _app.add_handler(CommandHandler("start", cmd_start))
    _app.add_handler(CommandHandler("whale", cmd_whale))
    _app.add_handler(CommandHandler("top", cmd_top))
    _app.add_handler(CommandHandler("track", cmd_track))
    _app.add_handler(CommandHandler("untrack", cmd_untrack))
    _app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    _app.add_handler(CommandHandler("scan", cmd_scan))
    _app.add_handler(CommandHandler("trending", cmd_trending))
    _app.add_handler(CommandHandler("settings", cmd_settings))
    _app.add_handler(CommandHandler("chains", cmd_chains))
    _app.add_handler(CommandHandler("gas", cmd_gas))
    _app.add_handler(CommandHandler("stats", cmd_stats))
    _app.add_handler(CommandHandler("donate", cmd_donate))
    _app.add_handler(CommandHandler("help", cmd_help))

    # Register callback query handler
    _app.add_handler(CallbackQueryHandler(handle_settings_callback, pattern=r"^settings:"))

    # Register error handler
    _app.add_error_handler(error_handler)

    # Initialize the application
    await _app.initialize()
    await _app.start()

    # Store session in bot_data directly (reliable, no callback dependency)
    _app.bot_data["session"] = _session
    logger.info("HTTP session stored in bot_data")

    # Register public command menu (visible to all users)
    public_commands = [
        BotCommand("start", "Start WHALEGOD and join the pod"),
        BotCommand("whale", "Recent whale movements"),
        BotCommand("top", "Top whale txs by volume (24h)"),
        BotCommand("track", "Track a wallet address"),
        BotCommand("untrack", "Stop tracking a wallet"),
        BotCommand("watchlist", "View your tracked wallets"),
        BotCommand("scan", "Deep scan a token contract"),
        BotCommand("trending", "Trending tokens right now"),
        BotCommand("settings", "Configure alert thresholds"),
        BotCommand("chains", "Chain status and prices"),
        BotCommand("gas", "Current gas prices"),
        BotCommand("donate", "Support WHALEGOD"),
        BotCommand("help", "Show all commands"),
    ]
    await _app.bot.set_my_commands(public_commands)

    # Register admin-only menu (includes /stats, visible only to admin)
    if ADMIN_CHAT_ID:
        admin_commands = public_commands + [
            BotCommand("stats", "Bot statistics & health (admin)"),
        ]
        try:
            await _app.bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=ADMIN_CHAT_ID),
            )
        except Exception:
            logger.warning("Could not set admin command menu")
    logger.info("Bot commands registered for menu")

    # Start health server
    await start_health_server()

    # Start webhook server for Helius
    await start_webhook_server()

    # Register Helius webhook (attempt — may fail if WEBHOOK_HOST not set)
    from bot.chains.solana import register_webhook
    await register_webhook(_session)

    # Setup and start scheduler
    _scheduler = setup_scheduler(_session, _app.bot)
    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))

    # Initial price warm-up — BEFORE polling starts so /gas /chains work immediately
    await price_service.refresh_base_prices(_session)

    # Start polling LAST — all services must be ready before accepting user commands
    await _app.updater.start_polling(drop_pending_updates=True)

    logger.info("WHALEGOD is LIVE ser 🐋🔥 wagmi")

    # Notify admin
    if ADMIN_CHAT_ID:
        try:
            await _app.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    f"🐋 <b>WHALEGOD v{__version__} is LIVE</b> 🐋\n\n"
                    f"gm ser, the whale tracker is up and running 🔥\n"
                    f"all systems operational. wagmi 🚀"
                ),
                parse_mode="HTML",
            )
        except Exception:
            logger.warning("Could not notify admin chat")

    # Wait for shutdown signal
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    await stop_event.wait()
    await shutdown()


async def shutdown() -> None:
    """Graceful shutdown: stop scheduler, close sessions, close DB."""
    global _scheduler, _session, _health_runner, _webhook_runner, _app

    logger.info("Shutting down WHALEGOD...")

    # Stop scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    # Stop Telegram updater and application
    if _app:
        try:
            await _app.updater.stop()
            await _app.stop()
            await _app.shutdown()
        except Exception:
            logger.exception("Error stopping Telegram app")

    # Stop health server
    if _health_runner:
        await _health_runner.cleanup()
        logger.info("Health server stopped")

    # Stop webhook server
    if _webhook_runner:
        await _webhook_runner.cleanup()
        logger.info("Webhook server stopped")

    # Close aiohttp session
    if _session:
        await _session.close()
        logger.info("HTTP session closed")

    # Close database
    await close_db()

    logger.info("WHALEGOD shutdown complete. gn ser 🌙")


def run() -> None:
    """Synchronous entry point."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    run()
