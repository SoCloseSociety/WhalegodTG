"""Randomized whale commentary per tier and transaction category."""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# By USD value tier
# ---------------------------------------------------------------------------

TIER_SMOL: list[str] = [  # $50K-$250K
    "smol whale making moves 🐟 not bad anon",
    "a lil splash in the ocean... but we see you ser 👀",
    "fish-tier but still bigger than my portfolio 😭",
    "somebody's got bags moving... respect 🫡",
    "not a minnow, not a whale... a dolphin perhaps? 🐬",
    "decent move ser, the ocean noticed 🌊",
    "a modest whale entry... every chad starts somewhere 💪",
    "bags in motion — somebody woke up and chose alpha 🧠",
    "the ocean ripples... whale activity detected 📡",
    "smol but mighty — this whale's just warming up 🔥",
]

TIER_MEDIUM: list[str] = [  # $250K-$1M
    "now we're talking ser! medium whale alert 🐋💰",
    "somebody's not messing around... half a milly+ moving 🔥",
    "bags are THICC on this one fren 💎",
    "the ocean is getting choppy... whale energy rising 🌊",
    "this is what alpha looks like anon — big moves 📈",
    "wagmi energy from this wallet... serious capital in play 🚀",
    "medium whale but still bigger than most degens' dreams 👑",
    "somebody found the alpha channel... based move ser 🧠",
    "the water's warming up — whale season loading ⚡",
    "not your average degen... this wallet means business 💼",
]

TIER_BIG: list[str] = [  # $1M-$5M
    "🚨 BIG WHALE ALERT 🚨 milly+ on the move ser!!!",
    "gigachad wallet just dropped a MILLY... the ocean trembles 🐋🔥",
    "somebody call CT — we got a BIG one moving 📱🐋",
    "diamond hands with DEEP pockets... absolute unit 💎🦍",
    "this whale just shook the entire ocean... LFG 🚀🌊",
    "milli club energy right here... the chad has spoken 👑",
    "when a milly moves, the whole market pays attention 👀",
    "MASSIVE bags detected... this is institutional-tier degen 🏦💰",
    "the ocean QUAKES — a true leviathan stirs 🌊🐋",
    "somebody's moving generational wealth around... based af 🔥",
]

TIER_MEGA: list[str] = [  # $5M-$25M
    "🚨🚨 MEGA WHALE INCOMING 🚨🚨 5M+ detected ser this is NOT a drill!!!",
    "ABSOLUTE GIGACHAD just moved 5M+ — the entire ocean is SHAKING 🌊🐋💀",
    "hello??? who just moved THAT much??? we need answers anon 📞🐋",
    "this whale could buy your whole neighborhood... mega bags in transit 💰🏠",
    "MEGA WHALE BREACH — this is the kind of move that shifts markets 📈📉",
    "god-tier wallet just casually moving more money than most countries 🌍💰",
    "the deep ocean just released something MASSIVE... brace yourselves 🐋🌊",
    "⚠️ MEGA ALERT ⚠️ this is the whale your whale looks up to 👑🐋",
    "somebody just moved what most degens will never see in a lifetime 😳💰",
    "the earth SHOOK — mega whale detected, all eyes on chain 👀🔥",
]

TIER_LEVIATHAN: list[str] = [  # $25M+
    "🚨🚨🚨 LEVIATHAN DETECTED 🚨🚨🚨 25M+ OH LORD SER WE'RE WITNESSING HISTORY",
    "BIBLICAL WHALE MOVEMENT — the seas are PARTING 🌊🐋👑 this is GENERATIONAL",
    "THE LEVIATHAN HAS SPOKEN — bow before the GOD WHALE 🐋👑🔥 25M+ moved!!!",
    "bruh... did you just see what I saw??? 25M+ in a SINGLE TX — I need to sit down 💀🐋",
    "THIS IS THE ONE — the whale that makes all other whales look like shrimp 🦐🐋👑",
    "🌊🌊🌊 TSUNAMI ALERT 🌊🌊🌊 a leviathan just caused waves across the ENTIRE ocean",
    "the GODS of crypto have moved — 25M+ changing hands — WITNESS THIS 👁️🐋",
    "I've seen a lot of whales anon... but this? THIS is a LEVIATHAN. absolute god-tier 👑💎🐋",
    "the blockchain will remember this day — LEVIATHAN SPOTTED 🐋🔥📜",
    "every trader on CT just felt a disturbance in the force... LEVIATHAN ENERGY 🌊⚡🐋",
]


# ---------------------------------------------------------------------------
# By transaction category (override tier-based)
# ---------------------------------------------------------------------------

CATEGORY_CEX_DEPOSIT: list[str] = [
    "bags heading to the exchange... somebody's about to dump? 🤔📉",
    "CEX deposit detected — is this whale about to sell? 👀📉",
    "moving to the exchange... paper hands or profit taking? 🧻",
    "whale sending to CEX — the bears might be cooking 🐻",
    "exchange deposit incoming... potential sell pressure loading 📉",
    "uh oh... bags going to the exchange. somebody knows something? 🤔",
    "CEX inflow detected — watch for sell walls ser ⚠️📉",
    "the whale feeds the exchange... dump incoming or just parking? 🏦",
    "exchange deposit = potential sell. stay sharp degens ⚡📉",
    "to the exchange they go... somebody's taking profits or getting rekt 💸",
]

CATEGORY_CEX_WITHDRAWAL: list[str] = [
    "pulling off the exchange — diamond hands loading up 💎🙌",
    "CEX withdrawal detected — this whale is ACCUMULATING ser 📈💪",
    "off the exchange, into cold storage... bullish energy 🐂🔥",
    "smart money pulling coins off exchange — they're not selling 💎",
    "withdrawal from CEX = bullish signal — somebody's holding tight 🙌",
    "the whale takes custody... no more exchange risk. based af 👑",
    "CEX outflow detected — less supply on exchanges = bullish 📈🐂",
    "pulling bags to safety... this whale is in it for the long game 💎🎯",
    "exchange withdrawal = conviction play. diamond hands confirmed 💎✅",
    "off the exchange and into the vault — this chad is NOT selling 🏆",
]

CATEGORY_DEX_SWAP: list[str] = [
    "whale just aped on DEX — no CEX middleman energy 🦍",
    "DEX swap detected — this whale trades like a true degen 🔄🦍",
    "swapping on DEX... the whale prefers sovereignty 👑🔄",
    "on-chain swap! this whale doesn't need a CEX 💪🔄",
    "DEX activity from a whale — what are they buying? 👀",
    "the whale swaps on DEX — decentralization is the way 🛡️",
    "swap detected — the degen whale trades where the real action is 🔥",
    "DEX swap = on-chain conviction. this whale means business 💼",
    "swapping bags on-chain — what does the whale know? 🧠👀",
    "a true degen — whale-sized swap on DEX. respect ser 🫡",
]

CATEGORY_LP_ADD: list[str] = [
    "fresh liquidity pouring in! the pool is getting thicc 🏊💧",
    "LP deposit — this whale is committing to the pool 💧💪",
    "new liquidity added — the pool just got DEEPER 🌊",
    "whale providing liquidity... farming season is ON 🌾💧",
    "LP add detected — somebody believes in this pool fr fr 💯",
    "thicc liquidity incoming... the pool appreciates your service 🫡💧",
    "whale just deepened the pool — less slippage for everyone 📈💧",
    "liquidity provider whale detected — the real MVPs 🏆💧",
    "adding to the pool... this whale plays the long game 🎯💧",
    "fresh LP deposit — the pool is eating GOOD tonight 🍽️💧",
]

CATEGORY_LP_REMOVE: list[str] = [
    "⚠️ liquidity drying up... watch your positions fren",
    "LP removal detected — somebody's pulling out 💧📉",
    "liquidity leaving the pool... exit liquidity for who? 🤔",
    "⚠️ whale removing LP — stay alert degens",
    "the pool gets thinner... whale pulling liquidity 📉💧",
    "LP removal = potential trouble. DYOR and watch closely 👀⚠️",
    "somebody's done farming... LP exit detected 🚪💧",
    "liquidity withdrawal from a whale — proceed with caution ⚠️🐋",
    "the pool just lost a whale... monitor slippage fren 📊",
    "LP remove detected — is this the beginning of the end? 🤔⚠️",
]

CATEGORY_BRIDGE: list[str] = [
    "cross-chain movement detected... where's this whale headed? 🌉",
    "bridging to another chain — multi-chain whale energy 🌐🐋",
    "the whale goes cross-chain... following the alpha? 🧠🌉",
    "bridge activity — this whale knows no chain boundaries 🌍",
    "cross-chain transfer detected — the whale explores new waters 🌊🌉",
    "bridging bags to another chain... something brewing over there? 🤔🌉",
    "multi-chain whale on the move — following the yields? 💰🌉",
    "bridge detected — the whale migrates to greener pastures 🐋🌿",
    "cross-chain transfer — this whale's portfolio spans the multiverse 🌌",
    "bridging detected... chain-hopping whale alert 🐋⛓️",
]

# ---------------------------------------------------------------------------
# NEW: Memecoin / Smart Money / MEV categories
# ---------------------------------------------------------------------------

CATEGORY_MEMECOIN_LAUNCH: list[str] = [
    "🚀 NEW MEMECOIN JUST DROPPED — Pump.fun launch detected! ape or nah? 🐸",
    "fresh token minted on Pump.fun... the degen casino never sleeps 🎰🐸",
    "a wild memecoin appeared! whale is early on this one ser 🦍🐸",
    "Pump.fun activity from a whale — could be the next 1000x or a rug 🤷‍♂️🐸",
    "the whale is launching/buying a fresh memecoin... degen szn confirmed 🔥🐸",
    "new token launch detected — the pump begins. are you early anon? 🏃‍♂️💨",
    "Pump.fun event — somebody just birthed a new memecoin into existence 🐣🐸",
    "whale interaction with Pump.fun... they're either creating or aping early 🧠🐸",
    "fresh launch on the bonding curve — the degen gods smile upon us 🐸💰",
    "memecoin launch detected — could moon, could rug. that's the game 🎲🐸",
]

CATEGORY_SMART_MONEY: list[str] = [
    "🧠 SMART MONEY ALERT — VC/fund/market maker just moved. follow the alpha 👀",
    "institutional wallet active — when the smart money moves, pay attention 🏦🧠",
    "VC wallet detected — these guys have the alpha before everyone else 💼👀",
    "market maker just made a move — they know something we don't 🤫🧠",
    "smart money flowing... the big brains are positioning 🧠💰",
    "fund wallet active — this is what institutional conviction looks like 💎🏦",
    "the smart money has spoken — when VCs move, the market listens 📢🧠",
    "institutional-tier movement — this wallet has insider alpha vibes 🧠🔥",
    "market maker positioning detected — front-run the front-runners 🏃💨",
    "smart money on the move — these wallets don't miss. watch closely 👁️🧠",
]

CATEGORY_MEV: list[str] = [
    "🤖 MEV BOT DETECTED — the sandwich machines are running 🥪",
    "MEV activity spotted — bots extracting value from the mempool 🤖💰",
    "sandwich attack likely — MEV bot is feasting on degens 🥪😤",
    "Jito/MEV infrastructure activity — someone's paying for priority 💸🤖",
    "MEV extraction in progress — the bots never sleep ser 🤖⚡",
    "bot vs degen warfare — MEV detected in this TX 🤖⚔️",
    "the MEV machines are EATING today — sandwich bots active 🥪🤖",
    "Flashbots/Jito tip detected — somebody needs this TX FIRST ⚡🤖",
    "MEV bot just extracted value — welcome to the dark forest 🌲🤖",
    "robotic precision — MEV bot calculated this one to perfection 🎯🤖",
]

CATEGORY_TRADING_BOT: list[str] = [
    "🤖 TRADING BOT ALERT — Banana Gun/Maestro router active 🍌",
    "bot-assisted trade detected — whale using sniper tools 🎯🤖",
    "Banana Gun activity — this whale trades with precision tools 🍌🔫",
    "Maestro router engaged — professional degen tools deployed 🤖💼",
    "trading bot transaction — automated alpha extraction 🤖⚡",
    "sniper bot active — this wallet isn't clicking buttons manually ser 🎯",
    "bot trade detected — the whale has automated their degen strats 🤖🧠",
    "trading bot deployed — speed is the name of the game here ⚡🤖",
    "automated snipe — when you need to be first, you use the bots 🏃🤖",
    "bot router activity — this whale means SERIOUS business 💼🤖",
]

CATEGORY_ACCUMULATION: list[str] = [
    "🟢 ACCUMULATION PATTERN — this wallet is LOADING UP fr fr 📈💎",
    "consistent buying detected — the whale is stacking heavy 📦💰",
    "accumulation mode ACTIVATED — bags getting bigger every day 📈🐋",
    "this wallet has been buying non-stop... they know something 🧠📈",
    "accumulation vibes — when whales stack, smart money pays attention 💎👀",
    "LOADING UP — this wallet is on an accumulation mission 🎯📈",
    "the whale accumulates in silence... then the market notices 🤫📈",
    "buy buy buy — this wallet is in full accumulation mode 🛒💰",
    "consistent inflows detected — this is what conviction looks like 💎📈",
    "whale stacking bags — accumulation pattern confirmed 📊📈",
]

CATEGORY_DISTRIBUTION: list[str] = [
    "🔴 DISTRIBUTION PATTERN — this wallet is OFFLOADING ser 📉⚠️",
    "consistent selling detected — the whale is distributing bags 📦📉",
    "distribution mode — when smart money sells, pay attention ⚠️📉",
    "this wallet has been selling consistently... exit strategy? 🚪📉",
    "distribution pattern detected — potential top signal ⚠️📉",
    "the whale distributes... are they done with this position? 🤔📉",
    "sell sell sell — this wallet is in full distribution mode 📉💸",
    "outflows detected — the smart money might be rotating out ⚠️📉",
    "whale dumping bags — distribution pattern confirmed 📊📉",
    "exit liquidity loading... this whale is distributing to degens ⚠️📉",
]


def get_quote_by_usd(usd_value: float) -> str:
    """Get a random commentary based on USD value tier."""
    if usd_value >= 25_000_000:
        return random.choice(TIER_LEVIATHAN)
    if usd_value >= 5_000_000:
        return random.choice(TIER_MEGA)
    if usd_value >= 1_000_000:
        return random.choice(TIER_BIG)
    if usd_value >= 250_000:
        return random.choice(TIER_MEDIUM)
    return random.choice(TIER_SMOL)


def get_quote_by_category(category: str) -> str | None:
    """Get a random commentary for a specific transaction category.

    Returns None for categories without specific commentary.
    """
    mapping: dict[str, list[str]] = {
        "cex_deposit": CATEGORY_CEX_DEPOSIT,
        "cex_withdrawal": CATEGORY_CEX_WITHDRAWAL,
        "dex_swap": CATEGORY_DEX_SWAP,
        "lp_add": CATEGORY_LP_ADD,
        "lp_remove": CATEGORY_LP_REMOVE,
        "bridge": CATEGORY_BRIDGE,
        "memecoin_launch": CATEGORY_MEMECOIN_LAUNCH,
        "smart_money_move": CATEGORY_SMART_MONEY,
        "mev_activity": CATEGORY_MEV,
        "trading_bot": CATEGORY_TRADING_BOT,
        "accumulation": CATEGORY_ACCUMULATION,
        "distribution": CATEGORY_DISTRIBUTION,
    }
    quotes = mapping.get(category)
    if quotes:
        return random.choice(quotes)
    return None


def get_commentary(usd_value: float, category: str) -> str:
    """Get the best commentary for a whale event.

    Category-specific commentary takes priority over USD-tier commentary.
    """
    cat_quote = get_quote_by_category(category)
    if cat_quote:
        return cat_quote
    return get_quote_by_usd(usd_value)
