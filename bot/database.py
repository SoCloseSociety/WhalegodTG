"""SQLite database: schema, migrations, all queries, WAL mode, indexing, backups."""

from __future__ import annotations

import glob
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

from bot.config import (
    DB_PATH,
    DEFAULT_ETH_THRESHOLD,
    DEFAULT_LP_THRESHOLD,
    DEFAULT_SOL_THRESHOLD,
    DEFAULT_USD_THRESHOLD,
    LOG_RETENTION_DAYS,
)

logger = logging.getLogger("whalegod.database")

_db: aiosqlite.Connection | None = None

# Whitelist for increment_stat to prevent SQL injection
_VALID_STAT_COLUMNS = frozenset({"total_alerts_sent", "total_whales_detected"})

# Whitelist for update_subscription
_VALID_SUB_COLUMNS = frozenset({
    "min_sol_threshold", "min_eth_threshold", "min_usd_threshold",
    "min_lp_threshold", "show_cex_deposits", "show_cex_withdrawals",
    "show_dex_swaps", "show_lp_events", "show_bridges", "enabled",
})

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tracked_wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    wallet_address TEXT NOT NULL,
    chain TEXT NOT NULL CHECK(chain IN ('solana', 'ethereum')),
    label TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE(user_id, wallet_address)
);

CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL UNIQUE,
    min_sol_threshold REAL DEFAULT {sol_t},
    min_eth_threshold REAL DEFAULT {eth_t},
    min_usd_threshold REAL DEFAULT {usd_t},
    min_lp_threshold REAL DEFAULT {lp_t},
    show_cex_deposits INTEGER DEFAULT 1,
    show_cex_withdrawals INTEGER DEFAULT 1,
    show_dex_swaps INTEGER DEFAULT 1,
    show_lp_events INTEGER DEFAULT 1,
    show_bridges INTEGER DEFAULT 1,
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS whale_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chain TEXT NOT NULL,
    tx_hash TEXT NOT NULL,
    from_address TEXT,
    to_address TEXT,
    from_label TEXT,
    to_label TEXT,
    amount REAL,
    token_symbol TEXT,
    token_address TEXT,
    usd_value REAL,
    tx_type TEXT,
    tx_category TEXT,
    signal TEXT,
    timestamp TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE(tx_hash, chain)
);

CREATE TABLE IF NOT EXISTS bot_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_alerts_sent INTEGER DEFAULT 0,
    total_whales_detected INTEGER DEFAULT 0,
    uptime_start TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS price_cache (
    token_address TEXT PRIMARY KEY,
    chain TEXT NOT NULL,
    symbol TEXT,
    price_usd REAL,
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_whale_timestamp ON whale_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_whale_chain ON whale_logs(chain);
CREATE INDEX IF NOT EXISTS idx_whale_usd ON whale_logs(usd_value);
CREATE INDEX IF NOT EXISTS idx_whale_category ON whale_logs(tx_category);
CREATE INDEX IF NOT EXISTS idx_whale_token ON whale_logs(token_address);
CREATE INDEX IF NOT EXISTS idx_tracked_address ON tracked_wallets(wallet_address);
CREATE INDEX IF NOT EXISTS idx_tracked_user ON tracked_wallets(user_id);
CREATE INDEX IF NOT EXISTS idx_sub_enabled ON alert_subscriptions(enabled);
""".format(
    sol_t=DEFAULT_SOL_THRESHOLD,
    eth_t=DEFAULT_ETH_THRESHOLD,
    usd_t=DEFAULT_USD_THRESHOLD,
    lp_t=DEFAULT_LP_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Open the database and apply schema."""
    global _db

    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row

    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA synchronous=NORMAL")
    await _db.execute("PRAGMA cache_size=-8000")       # 8MB (was 64MB)
    await _db.execute("PRAGMA busy_timeout=5000")
    await _db.execute("PRAGMA temp_store=MEMORY")       # temp tables in RAM
    await _db.execute("PRAGMA mmap_size=33554432")      # 32MB memory-mapped I/O

    await _db.executescript(SCHEMA_SQL)
    await _db.commit()

    async with _db.execute("SELECT COUNT(*) FROM bot_stats") as cur:
        row = await cur.fetchone()
        if row[0] == 0:
            await _db.execute("INSERT INTO bot_stats DEFAULT VALUES")
            await _db.commit()

    logger.info("Database initialized at %s", DB_PATH)


async def close_db() -> None:
    """Close the database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("Database closed")


def get_db() -> aiosqlite.Connection:
    """Return the current database connection."""
    if _db is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _db


# ---------------------------------------------------------------------------
# Alert subscriptions
# ---------------------------------------------------------------------------

async def ensure_subscription(chat_id: int) -> dict[str, Any]:
    """Create subscription if it doesn't exist, return current settings."""
    db = get_db()
    async with db.execute(
        "SELECT * FROM alert_subscriptions WHERE chat_id = ?", (chat_id,)
    ) as cur:
        row = await cur.fetchone()
    if row:
        return dict(row)

    await db.execute(
        "INSERT OR IGNORE INTO alert_subscriptions (chat_id) VALUES (?)",
        (chat_id,),
    )
    await db.commit()
    async with db.execute(
        "SELECT * FROM alert_subscriptions WHERE chat_id = ?", (chat_id,)
    ) as cur:
        row = await cur.fetchone()
    return dict(row)


async def get_all_enabled_subscriptions() -> list[dict[str, Any]]:
    """Return all subscriptions with enabled=1."""
    db = get_db()
    async with db.execute(
        "SELECT * FROM alert_subscriptions WHERE enabled = 1"
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def update_subscription(chat_id: int, **kwargs: Any) -> None:
    """Update one or more columns on a subscription (whitelist-safe)."""
    filtered = {k: v for k, v in kwargs.items() if k in _VALID_SUB_COLUMNS}
    if not filtered:
        return
    db = get_db()
    sets = ", ".join(f"{k} = ?" for k in filtered)
    vals = list(filtered.values()) + [chat_id]
    await db.execute(
        f"UPDATE alert_subscriptions SET {sets} WHERE chat_id = ?", vals
    )
    await db.commit()


async def delete_subscription(chat_id: int) -> None:
    """Remove a subscription."""
    db = get_db()
    await db.execute("DELETE FROM alert_subscriptions WHERE chat_id = ?", (chat_id,))
    await db.commit()


async def count_active_chats() -> int:
    """Count active (enabled) subscriptions."""
    db = get_db()
    async with db.execute(
        "SELECT COUNT(*) FROM alert_subscriptions WHERE enabled = 1"
    ) as cur:
        row = await cur.fetchone()
    return row[0]


# ---------------------------------------------------------------------------
# Tracked wallets
# ---------------------------------------------------------------------------

async def add_tracked_wallet(
    user_id: int, chat_id: int, address: str, chain: str, label: str | None = None
) -> bool:
    """Add a wallet. Returns True on success, False on duplicate."""
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO tracked_wallets (user_id, chat_id, wallet_address, chain, label) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, chat_id, address, chain, label),
        )
        await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def remove_tracked_wallet(user_id: int, address: str) -> bool:
    """Remove a tracked wallet. Returns True if a row was deleted."""
    db = get_db()
    cur = await db.execute(
        "DELETE FROM tracked_wallets WHERE user_id = ? AND wallet_address = ?",
        (user_id, address),
    )
    await db.commit()
    return cur.rowcount > 0


async def get_user_wallets(user_id: int) -> list[dict[str, Any]]:
    """Get all tracked wallets for a user."""
    db = get_db()
    async with db.execute(
        "SELECT * FROM tracked_wallets WHERE user_id = ? ORDER BY created_at",
        (user_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def count_user_wallets(user_id: int) -> int:
    """Count tracked wallets for a user."""
    db = get_db()
    async with db.execute(
        "SELECT COUNT(*) FROM tracked_wallets WHERE user_id = ?", (user_id,)
    ) as cur:
        row = await cur.fetchone()
    return row[0]


async def count_total_tracked_wallets() -> int:
    """Count all tracked wallets globally."""
    db = get_db()
    async with db.execute("SELECT COUNT(*) FROM tracked_wallets") as cur:
        row = await cur.fetchone()
    return row[0]


async def get_all_tracked_wallets() -> list[dict[str, Any]]:
    """Get all tracked wallets (for the background checker)."""
    db = get_db()
    async with db.execute("SELECT * FROM tracked_wallets") as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Whale logs
# ---------------------------------------------------------------------------

async def insert_whale_log(
    chain: str,
    tx_hash: str,
    from_address: str | None,
    to_address: str | None,
    from_label: str | None,
    to_label: str | None,
    amount: float | None,
    token_symbol: str | None,
    token_address: str | None,
    usd_value: float | None,
    tx_type: str | None,
    tx_category: str | None,
    signal: str | None,
) -> bool:
    """Insert a whale log entry. Returns False on duplicate (dedup)."""
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO whale_logs "
            "(chain, tx_hash, from_address, to_address, from_label, to_label, "
            "amount, token_symbol, token_address, usd_value, tx_type, tx_category, signal) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (chain, tx_hash, from_address, to_address, from_label, to_label,
             amount, token_symbol, token_address, usd_value, tx_type, tx_category, signal),
        )
        await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def get_recent_whale_logs(
    chain: str | None = None, limit: int = 5
) -> list[dict[str, Any]]:
    """Get the most recent whale log entries."""
    db = get_db()
    if chain:
        sql = "SELECT * FROM whale_logs WHERE chain = ? ORDER BY timestamp DESC LIMIT ?"
        params: tuple[Any, ...] = (chain, limit)
    else:
        sql = "SELECT * FROM whale_logs ORDER BY timestamp DESC LIMIT ?"
        params = (limit,)
    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_top_whale_logs(
    hours: int = 24, limit: int = 10
) -> list[dict[str, Any]]:
    """Get top whale logs by USD value within a timeframe."""
    db = get_db()
    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    async with db.execute(
        "SELECT * FROM whale_logs WHERE timestamp >= ? ORDER BY usd_value DESC LIMIT ?",
        (cutoff_str, limit),
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_whale_volume(hours: int = 24) -> float:
    """Get total whale USD volume in the timeframe."""
    db = get_db()
    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    async with db.execute(
        "SELECT COALESCE(SUM(usd_value), 0) FROM whale_logs WHERE timestamp >= ?",
        (cutoff_str,),
    ) as cur:
        row = await cur.fetchone()
    return float(row[0])


# ---------------------------------------------------------------------------
# Bot stats
# ---------------------------------------------------------------------------

async def increment_stat(column: str, amount: int = 1) -> None:
    """Increment a counter in bot_stats (whitelist-safe)."""
    if column not in _VALID_STAT_COLUMNS:
        logger.error("Attempted to increment invalid stat column: %s", column)
        return
    db = get_db()
    await db.execute(
        f"UPDATE bot_stats SET {column} = {column} + ? WHERE id = 1", (amount,)
    )
    await db.commit()


async def get_bot_stats() -> dict[str, Any]:
    """Return the bot_stats row."""
    db = get_db()
    async with db.execute("SELECT * FROM bot_stats WHERE id = 1") as cur:
        row = await cur.fetchone()
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# Price cache (DB-level)
# ---------------------------------------------------------------------------

async def upsert_price_cache(
    token_address: str, chain: str, symbol: str | None, price_usd: float
) -> None:
    """Insert or update a cached price."""
    db = get_db()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    await db.execute(
        "INSERT INTO price_cache (token_address, chain, symbol, price_usd, updated_at) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(token_address) DO UPDATE SET "
        "price_usd = excluded.price_usd, symbol = excluded.symbol, updated_at = excluded.updated_at",
        (token_address, chain, symbol, price_usd, now),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

async def cleanup() -> None:
    """Delete old whale_logs and stale price_cache entries, then reclaim space."""
    db = get_db()

    log_cutoff = (
        datetime.now(timezone.utc) - timedelta(days=LOG_RETENTION_DAYS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    price_cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    cur = await db.execute(
        "DELETE FROM whale_logs WHERE timestamp < ?", (log_cutoff,)
    )
    logs_deleted = cur.rowcount
    cur = await db.execute(
        "DELETE FROM price_cache WHERE updated_at < ?", (price_cutoff,)
    )
    prices_deleted = cur.rowcount
    await db.commit()

    # Reclaim disk space if significant rows were deleted
    if logs_deleted > 50 or prices_deleted > 50:
        try:
            await db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            # VACUUM rebuilds the DB file — only run when deletions are significant
            if logs_deleted > 200:
                await db.execute("VACUUM")
                logger.info("VACUUM completed — reclaimed disk space")
        except Exception:
            logger.warning("VACUUM skipped — DB may be locked")

    logger.info(
        "Cleanup complete — deleted %d old whale logs, %d stale prices",
        logs_deleted, prices_deleted,
    )


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

_BACKUP_MAX_KEEP: int = 3


async def backup_db() -> str | None:
    """Create a timestamped backup of the database. Keeps last 3 backups.

    Returns the backup path on success, or None.
    """
    if _db is None:
        logger.warning("Cannot backup — database not initialized")
        return None

    backup_dir = os.path.join(os.path.dirname(DB_PATH) or ".", "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"whalegod_{timestamp}.db")

    try:
        # Checkpoint WAL to ensure consistency before copy
        await _db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        await _db.commit()

        # Copy database file
        shutil.copy2(DB_PATH, backup_path)

        # Rotate old backups — keep only the most recent ones
        existing = sorted(glob.glob(os.path.join(backup_dir, "whalegod_*.db")))
        while len(existing) > _BACKUP_MAX_KEEP:
            old = existing.pop(0)
            try:
                os.remove(old)
                logger.debug("Removed old backup: %s", old)
            except OSError:
                pass

        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        logger.info("Database backup created: %s (%.1f MB)", backup_path, size_mb)
        return backup_path
    except Exception:
        logger.exception("Database backup failed")
        return None
