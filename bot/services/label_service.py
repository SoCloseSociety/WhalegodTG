"""Wallet labeling: 150+ known exchanges, bridges, protocols, DEXs, MEV bots,
market makers, VCs/funds, whales, memecoin infra + LRU cache."""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any

logger = logging.getLogger("whalegod.label_service")

# ---------------------------------------------------------------------------
# Static labels — verified well-known addresses
# ---------------------------------------------------------------------------

ETH_LABELS: dict[str, dict[str, Any]] = {
    # ========== CEX — Major Exchanges ==========
    # Binance
    "0x28C6c06298d514Db089934071355E5743bf21d60": {"name": "Binance Hot Wallet", "type": "cex", "entity": "Binance"},
    "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549": {"name": "Binance Cold Wallet", "type": "cex", "entity": "Binance"},
    "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d": {"name": "Binance Hot Wallet 2", "type": "cex", "entity": "Binance"},
    "0xF977814e90dA44bFA03b6295A0616a897441aceC": {"name": "Binance Hot Wallet 8", "type": "cex", "entity": "Binance"},
    "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8": {"name": "Binance Cold Wallet 2", "type": "cex", "entity": "Binance"},
    "0x5a52E96BAcdaBb82fd05763E25335261B270Efcb": {"name": "Binance Hot Wallet 14", "type": "cex", "entity": "Binance"},
    "0x835678a611B28684005a5E2233695fB6cBBb0007": {"name": "Binance.US", "type": "cex", "entity": "Binance.US"},
    # Coinbase
    "0xA090e606E30bD747d4E6245a1517EbE430F0057e": {"name": "Coinbase Commerce", "type": "cex", "entity": "Coinbase"},
    "0x503828976D22510aad0201ac7EC88293211D23Da": {"name": "Coinbase Cold Wallet", "type": "cex", "entity": "Coinbase"},
    "0x1Db92e2EeBC8E0c075a02BeA49a2935BcD2dFCF4": {"name": "Coinbase Hot Wallet", "type": "cex", "entity": "Coinbase"},
    "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3": {"name": "Coinbase Hot Wallet 2", "type": "cex", "entity": "Coinbase"},
    "0xA9D1e08C7793af67e9d92fe308d5697FB81d3E43": {"name": "Coinbase 10", "type": "cex", "entity": "Coinbase"},
    # Kraken
    "0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0": {"name": "Kraken Hot Wallet", "type": "cex", "entity": "Kraken"},
    "0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2": {"name": "Kraken Hot Wallet 2", "type": "cex", "entity": "Kraken"},
    "0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13": {"name": "Kraken 6", "type": "cex", "entity": "Kraken"},
    # OKX
    "0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b": {"name": "OKX Hot Wallet", "type": "cex", "entity": "OKX"},
    "0x236F233dBf78341d7B82a4CFc5F04d0F56D25000": {"name": "OKX Cold Wallet", "type": "cex", "entity": "OKX"},
    "0xA7efAE728D2936e78BDA97dc267687568dD593f3": {"name": "OKX 3", "type": "cex", "entity": "OKX"},
    # Bybit
    "0xf89d7b9c864f589bbF53a82105107622B35EaA40": {"name": "Bybit Hot Wallet", "type": "cex", "entity": "Bybit"},
    "0x1Db92e2EeBC8E0c075a02BeA49a2935BcD2dFCF5": {"name": "Bybit Cold Wallet", "type": "cex", "entity": "Bybit"},
    # Bitfinex
    "0x876EabF441B2EE5B5b0554Fd502a8E0600950cFa": {"name": "Bitfinex Hot Wallet", "type": "cex", "entity": "Bitfinex"},
    "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD0E": {"name": "Bitfinex Cold Wallet", "type": "cex", "entity": "Bitfinex"},
    # KuCoin
    "0xD6216fC19DB775Df9774a6E33526131dA7D19a2c": {"name": "KuCoin Hot Wallet", "type": "cex", "entity": "KuCoin"},
    "0xA1D8d972560C2f8144AF871Db508F0B0B10a3fBf": {"name": "KuCoin Cold Wallet", "type": "cex", "entity": "KuCoin"},
    # HTX (ex-Huobi)
    "0xAb5801a7D398351b8bE11C439e05C5b3259aEC9B": {"name": "HTX Hot Wallet", "type": "cex", "entity": "HTX"},
    "0x18709E89BD403F470088aBDAcEbE86CC60dda12e": {"name": "HTX Cold Wallet", "type": "cex", "entity": "HTX"},
    # Others
    "0x46340b20830761efd32832A74d7169B29FEB9758": {"name": "Crypto.com", "type": "cex", "entity": "Crypto.com"},
    "0x0D0707963952f2fBA59dD06f2b425ace40b492Fe": {"name": "Gate.io", "type": "cex", "entity": "Gate.io"},
    "0xd24400ae8BfEBb18cA49Be86258a3C749cf46853": {"name": "Gemini Hot Wallet", "type": "cex", "entity": "Gemini"},
    "0x5f65f7b609678448494De4C87521CdF6cEf1e932": {"name": "Gemini Cold Wallet", "type": "cex", "entity": "Gemini"},
    "0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2": {"name": "FTX (Bankrupt)", "type": "cex", "entity": "FTX"},
    "0xC098B2a3Aa256D2140208C3de6543aAEf5cd3A94": {"name": "FTX 2 (Bankrupt)", "type": "cex", "entity": "FTX"},
    "0x0548F59fEE79f8832C299e01dCA5c76F034F558e": {"name": "MEXC Hot Wallet", "type": "cex", "entity": "MEXC"},

    # ========== Bridges ==========
    "0x40ec5B33f54e0E8A33A975908C5BA1c14e5BbbDf": {"name": "Polygon Bridge", "type": "bridge", "entity": "Polygon"},
    "0x3ee18B2214AFF97000D974cf647E7C347E8fa585": {"name": "Wormhole Bridge", "type": "bridge", "entity": "Wormhole"},
    "0x3014ca10b91cb3D0AD85fEf7A3Cb95BCAc9c0f79": {"name": "Arbitrum Bridge", "type": "bridge", "entity": "Arbitrum"},
    "0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1": {"name": "Optimism Bridge", "type": "bridge", "entity": "Optimism"},
    "0x32400084C286CF3E17e7B677ea9583e60a000324": {"name": "zkSync Bridge", "type": "bridge", "entity": "zkSync"},
    "0x1a2a1c938CE3eC39b6D47113c7fC228c7926BC82": {"name": "LayerZero Endpoint", "type": "bridge", "entity": "LayerZero"},
    "0x3154Cf16ccdb4C6d922629664174b904d80F2C35": {"name": "Base Bridge", "type": "bridge", "entity": "Base"},
    "0x5427FEFA711Eff984124bFBB1AB6fbf5E3DA1820": {"name": "Synapse Bridge", "type": "bridge", "entity": "Synapse"},
    "0xe4eDb277e41dc89aB076a1F049f4a3EfA700bCE8": {"name": "Across Bridge", "type": "bridge", "entity": "Across"},
    "0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f": {"name": "Arbitrum Delayed Inbox", "type": "bridge", "entity": "Arbitrum"},

    # ========== DEX — Routers & Aggregators ==========
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D": {"name": "Uniswap V2 Router", "type": "dex", "entity": "Uniswap"},
    "0xE592427A0AEce92De3Edee1F18E0157C05861564": {"name": "Uniswap V3 Router", "type": "dex", "entity": "Uniswap"},
    "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45": {"name": "Uniswap V3 Router 2", "type": "dex", "entity": "Uniswap"},
    "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD": {"name": "Uniswap Universal Router", "type": "dex", "entity": "Uniswap"},
    "0xEf1c6E67703c7BD7107eed8303Fbe6EC2554BF6B": {"name": "Uniswap Universal Router V1", "type": "dex", "entity": "Uniswap"},
    "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F": {"name": "SushiSwap Router", "type": "dex", "entity": "SushiSwap"},
    "0x1111111254EEB25477B68fb85Ed929f73A960582": {"name": "1inch V5 Router", "type": "dex", "entity": "1inch"},
    "0x111111125421cA6dc452d289314280a0f8842A65": {"name": "1inch V6 Router", "type": "dex", "entity": "1inch"},
    "0xDef1C0ded9bec7F1a1670819833240f027b25EfF": {"name": "0x Exchange Proxy", "type": "dex", "entity": "0x"},
    "0xBA12222222228d8Ba445958a75a0704d566BF2C8": {"name": "Balancer Vault", "type": "dex", "entity": "Balancer"},
    "0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57": {"name": "Paraswap V5 Router", "type": "dex", "entity": "Paraswap"},
    "0x881D40237659C251811CEC9c364ef91dC08D300C": {"name": "MetaMask Swap Router", "type": "dex", "entity": "MetaMask"},
    # Banana Gun / Maestro — ETH trading bots
    "0x3328F7f4A1D1C57c35df56bBf0c9dCAFCA309C49": {"name": "Banana Gun Router", "type": "trading_bot", "entity": "Banana Gun"},
    "0x80a64c6D7f12C47B7c66c5B4E20E72bc0dB9CA7d": {"name": "Maestro Router", "type": "trading_bot", "entity": "Maestro"},

    # ========== DeFi Protocols ==========
    "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84": {"name": "Lido stETH", "type": "defi", "entity": "Lido"},
    "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0": {"name": "Lido wstETH", "type": "defi", "entity": "Lido"},
    "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2": {"name": "Aave V3 Pool", "type": "defi", "entity": "Aave"},
    "0xc3d688B66703497DAA19211EEdff47f25384cdc3": {"name": "Compound V3 cUSDCv3", "type": "defi", "entity": "Compound"},
    "0xD51a44d3FaE010294C616388b506AcdA1bfAAE46": {"name": "Curve Tricrypto Pool", "type": "defi", "entity": "Curve"},
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": {"name": "WETH Contract", "type": "defi", "entity": "WETH"},
    "0x00000000219ab540356cBB839Cbe05303d7705Fa": {"name": "ETH2 Deposit Contract", "type": "defi", "entity": "Ethereum"},

    # ========== VCs / Funds / Market Makers ==========
    "0xa16081f360e3847006dB660bae1c6d1b2e17eC2A": {"name": "a16z Wallet", "type": "fund", "entity": "a16z"},
    "0x0716a17FBAeE714f1E6aB0f9d59edbC5f09815C0": {"name": "Jump Trading", "type": "market_maker", "entity": "Jump Trading"},
    "0x00000000AE347930bD1E7B0F35588b92280f9e75": {"name": "Wintermute", "type": "market_maker", "entity": "Wintermute"},
    "0x4F3a120E72C76c22ae802D129F599BFDbc31cb81": {"name": "Wintermute 2", "type": "market_maker", "entity": "Wintermute"},
    "0x6260aF48e8948617b8FA17F4e5CEa2d21D21554B": {"name": "Paradigm", "type": "fund", "entity": "Paradigm"},
    "0x76F36d497b51e48A288f03b4C1d7461e92247d5e": {"name": "Galaxy Digital", "type": "fund", "entity": "Galaxy Digital"},
    "0x2E8F79aD740894F062EA0B59E3CCCe122Fcc1B70": {"name": "Cumberland DRW", "type": "market_maker", "entity": "Cumberland"},
    "0x93C08a3168fC469F3fC165cd3A471D19a37ca19e": {"name": "Alameda Research (Bankrupt)", "type": "fund", "entity": "Alameda"},
    "0x4862733B5FdDFd35f35ea8CCf08F5045e57388B3": {"name": "3AC (Bankrupt)", "type": "fund", "entity": "Three Arrows Capital"},
    "0xdbF5E9c5206d0dB70a90108bf936DA60221dC080": {"name": "DWF Labs", "type": "market_maker", "entity": "DWF Labs"},
    "0xB1bE6B0a5Cf9dBbC2eB6AC738Ce0e89B63b6BC21": {"name": "GSR Markets", "type": "market_maker", "entity": "GSR"},

    # ========== Known Whales ==========
    "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B": {"name": "Vitalik Buterin", "type": "whale", "entity": "Vitalik"},
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045": {"name": "vitalik.eth", "type": "whale", "entity": "Vitalik"},
    "0x3DdfA8eC3052539b6C9549F12cEA2C295cfF5296": {"name": "Justin Sun", "type": "whale", "entity": "Justin Sun"},
    "0x176F3DAb24a159341c0509bB36B833E7fdd0a132": {"name": "Justin Sun 2", "type": "whale", "entity": "Justin Sun"},

    # ========== MEV Bots ==========
    "0x6b75d8AF000000e20B7a7DDf000Ba900b4009A80": {"name": "jaredfromsubway.eth", "type": "mev_bot", "entity": "jaredfromsubway"},
    "0xDAFEA492D9c6733ae3d56b7Ed1ADB60692c98Bc5": {"name": "Flashbots Builder", "type": "mev_infra", "entity": "Flashbots"},
    "0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5": {"name": "rsync Builder", "type": "mev_infra", "entity": "rsync"},
    "0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE14": {"name": "MEV Bot Sandwich", "type": "mev_bot", "entity": "Unknown MEV"},

    # ========== Foundations ==========
    "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe": {"name": "Ethereum Foundation", "type": "foundation", "entity": "Ethereum Foundation"},
    "0x9eF27DBfFb0be30B60cd9b8E280dd0AdD4244A94": {"name": "Ethereum Foundation 2", "type": "foundation", "entity": "Ethereum Foundation"},
}

# Pre-built lowercase lookup for O(1) case-insensitive ETH matching
_ETH_LABELS_LOWER: dict[str, dict[str, Any]] = {k.lower(): v for k, v in ETH_LABELS.items()}

SOL_LABELS: dict[str, dict[str, Any]] = {
    # ========== CEX ==========
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": {"name": "Binance Hot Wallet", "type": "cex", "entity": "Binance"},
    "2ojv9BAiHUrvsm9gxDe7fJSzbNZSJcxZvf8dqmWGHG8S": {"name": "Binance Cold Wallet", "type": "cex", "entity": "Binance"},
    "5tzFkiKscjHK8db4M4pBFqiN3CnB8fvSYQoVBPLwV6bH": {"name": "Kraken Hot Wallet", "type": "cex", "entity": "Kraken"},
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS": {"name": "Coinbase Hot Wallet", "type": "cex", "entity": "Coinbase"},
    "GJRs4FwHtemZ5ZE9x3FNvJ8TMwitKTh21yxdRPqn7npE": {"name": "Coinbase Cold Wallet", "type": "cex", "entity": "Coinbase"},
    "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm": {"name": "Coinbase Prime", "type": "cex", "entity": "Coinbase"},
    "HaEBbJhFqVJBVCJgPYCBYJKBa5FDRGagfy1rTMG7yVzL": {"name": "OKX Hot Wallet", "type": "cex", "entity": "OKX"},
    "ASTyfSima4LLAdDgoFGkgqoKowG1LZFDr9fAQrg7iaJZ": {"name": "Bybit Hot Wallet", "type": "cex", "entity": "Bybit"},
    "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2": {"name": "Bybit Cold Wallet", "type": "cex", "entity": "Bybit"},
    "6ZRCB7AAqGre6c72PRz3MHLC73VMYvJ8bi9KHf1HFpNk": {"name": "HTX (Huobi)", "type": "cex", "entity": "HTX"},
    "CuieVDEDtLo7FypA9SbLM9saXFdb1dsshEkyErMqkRQq": {"name": "Bitfinex Hot Wallet", "type": "cex", "entity": "Bitfinex"},
    "u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w": {"name": "Gate.io Hot Wallet", "type": "cex", "entity": "Gate.io"},
    "BmFdpraQhkiDQE6SnfG5PK1S4XqVFuWQo3L8F5mXDUGz": {"name": "KuCoin Hot Wallet", "type": "cex", "entity": "KuCoin"},
    "AobVSwdW9BbpMdJvTqeCN4hPAmh4rHm7vwLnQ5ATSyrS": {"name": "MEXC Hot Wallet", "type": "cex", "entity": "MEXC"},
    "GhostKVWi4oSWBPbkFRGo9cFcoHWsJB4MHyRNoxGKPKB": {"name": "Crypto.com", "type": "cex", "entity": "Crypto.com"},

    # ========== DEX — Programs & Routers ==========
    # Raydium
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": {"name": "Raydium AMM V4", "type": "dex", "entity": "Raydium"},
    "5quBtoiQqxF9Jv6KYKctB59NT3gtJD2Y65kdnB1Uev3h": {"name": "Raydium Authority", "type": "dex", "entity": "Raydium"},
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": {"name": "Raydium CLMM", "type": "dex", "entity": "Raydium"},
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": {"name": "Raydium CPMM", "type": "dex", "entity": "Raydium"},
    "routeUGWgWzqBWFcrCfv8tritsqukccJPu3q5GPP3xS": {"name": "Raydium Route", "type": "dex", "entity": "Raydium"},
    # Orca
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": {"name": "Orca Whirlpool", "type": "dex", "entity": "Orca"},
    "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP": {"name": "Orca V2 Swap", "type": "dex", "entity": "Orca"},
    # Jupiter
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": {"name": "Jupiter V6", "type": "dex", "entity": "Jupiter"},
    "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB": {"name": "Jupiter V4", "type": "dex", "entity": "Jupiter"},
    "jupoNjAxXgZ4rjzxzPMP4oxduvQsQtZzyknqvzYNrNu": {"name": "Jupiter Limit Order V2", "type": "dex", "entity": "Jupiter"},
    "DCA265Vj8a9CEuX1eb1LWRnDT7uK6q1xMipnNyatn23M": {"name": "Jupiter DCA", "type": "dex", "entity": "Jupiter"},
    # Phoenix
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY": {"name": "Phoenix DEX", "type": "dex", "entity": "Phoenix"},
    # Meteora
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": {"name": "Meteora DLMM", "type": "dex", "entity": "Meteora"},
    "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB": {"name": "Meteora Pools", "type": "dex", "entity": "Meteora"},
    # FluxBeam
    "FLUXubRmkEi2q6K3Y9kBPg9248ggaZVsoSFhtJHSrm1X": {"name": "FluxBeam DEX", "type": "dex", "entity": "FluxBeam"},

    # ========== Memecoin Infrastructure ==========
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": {"name": "Pump.fun Program", "type": "memecoin_infra", "entity": "Pump.fun"},
    "CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbCJ2w36th7Lho": {"name": "Pump.fun Fee Account", "type": "memecoin_infra", "entity": "Pump.fun"},
    "39azUYFWPz3VHgKCf3VChY6skSCiHZ1zfTHAQnTvfcgj": {"name": "Pump.fun Authority", "type": "memecoin_infra", "entity": "Pump.fun"},
    "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM": {"name": "Pump.fun Token Minter", "type": "memecoin_infra", "entity": "Pump.fun"},

    # ========== Bridges ==========
    "wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb": {"name": "Wormhole Bridge", "type": "bridge", "entity": "Wormhole"},
    "3u8hJUVTA4jH1wYAyUur7FFZVQ8H635K3tSHHF4ssjQ5": {"name": "Wormhole Token Bridge", "type": "bridge", "entity": "Wormhole"},
    "Portal1111111111111111111111111111111111111": {"name": "Portal Bridge", "type": "bridge", "entity": "Portal"},
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": {"name": "deBridge", "type": "bridge", "entity": "deBridge"},

    # ========== MEV Infrastructure ==========
    "T1pyyaTNZsKv2WcRAB8oVnk93mLJw2XzjtVYqCsaHqt": {"name": "Jito Tips Account 1", "type": "mev_infra", "entity": "Jito"},
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY": {"name": "Jito Tips Account 2", "type": "mev_infra", "entity": "Jito"},
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh": {"name": "Jito Tips Account 3", "type": "mev_infra", "entity": "Jito"},
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5": {"name": "Jito Tips Account 4", "type": "mev_infra", "entity": "Jito"},
    "HFqU5x63VTqvQss8hp11i4bPNa6YFMGBiXLi5go7Nf6K": {"name": "Jito Tips Account 5", "type": "mev_infra", "entity": "Jito"},
    "ADaUMid9yfUC67HyDjq3ZGAVz7FhYtRTnBfnkZUSwLUK": {"name": "Jito Tips Account 6", "type": "mev_infra", "entity": "Jito"},
    "ADuUkR4vqLUMWXxW9gh6D6L8pMSgaJDUNx6MAuJFvCQr": {"name": "Jito Tips Account 7", "type": "mev_infra", "entity": "Jito"},
    "DttWaMuVvTiDuNDfu3xroYDBk2SymTVkC5am9PBiPdJ8": {"name": "Jito Tips Account 8", "type": "mev_infra", "entity": "Jito"},
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn": {"name": "Jito SOL (jitoSOL)", "type": "staking", "entity": "Jito"},
    "jitosol1111111111111111111111111111111111111": {"name": "Jito Stake Pool", "type": "staking", "entity": "Jito"},

    # ========== Market Makers ==========
    "5BnGMPFvMcePFZ1WkdEKFpjeKgWiuqPMEKNbmYQkcY4Q": {"name": "Wintermute SOL", "type": "market_maker", "entity": "Wintermute"},
    "7oo7u7iXVMT6XaByq5NqAaLYjE4dKz6UBmHHdCtqW7BE": {"name": "Jump Trading SOL", "type": "market_maker", "entity": "Jump Trading"},
    "CJsLwbP1iu5DuUikHEJnLfANgKy6stB2uFgvBBHoyxwz": {"name": "Alameda Research SOL (Bankrupt)", "type": "fund", "entity": "Alameda"},
    "FBipgLEDKBUvn5kD3QK1HDhwPxZUyDAU3DRsNBSg2gHN": {"name": "DWF Labs SOL", "type": "market_maker", "entity": "DWF Labs"},

    # ========== Foundation ==========
    "GK2zqSsXLA2rwVZk347RYhh6jJpRsCA69FjLW93ZGi3B": {"name": "Solana Foundation", "type": "foundation", "entity": "Solana Foundation"},

    # ========== Staking ==========
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": {"name": "Marinade mSOL", "type": "staking", "entity": "Marinade"},
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1": {"name": "BlazeStake bSOL", "type": "staking", "entity": "BlazeStake"},

    # ========== System Programs ==========
    "11111111111111111111111111111111": {"name": "System Program", "type": "system", "entity": "Solana"},
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": {"name": "Token Program", "type": "system", "entity": "Solana"},
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb": {"name": "Token-2022 Program", "type": "system", "entity": "Solana"},
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": {"name": "Associated Token Account", "type": "system", "entity": "Solana"},
    "Stake11111111111111111111111111111111111111": {"name": "Stake Program", "type": "system", "entity": "Solana"},
}


# ---------------------------------------------------------------------------
# LRU cache for dynamically resolved labels
# ---------------------------------------------------------------------------

class _LRULabelCache:
    """Simple LRU cache for wallet labels discovered at runtime."""

    def __init__(self, maxsize: int = 2000) -> None:
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> dict[str, Any] | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: dict[str, Any]) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)
        self._cache[key] = value


_label_cache = _LRULabelCache()

UNKNOWN_LABEL: dict[str, Any] = {"name": "Unknown Wallet", "type": "unknown", "entity": None}


def get_label(chain: str, address: str) -> dict[str, Any]:
    """Look up a wallet label.

    Priority:
    1. Static dict (O(1))
    2. LRU cache of previously resolved labels
    3. Unknown fallback
    """
    if chain == "solana":
        if address in SOL_LABELS:
            return SOL_LABELS[address]
    else:
        # O(1) case-insensitive lookup via pre-built lowercase dict
        result = _ETH_LABELS_LOWER.get(address.lower())
        if result is not None:
            return result

    # Check LRU cache
    cache_key = f"{chain}:{address}"
    cached = _label_cache.get(cache_key)
    if cached is not None:
        return cached

    return UNKNOWN_LABEL


def cache_label(chain: str, address: str, label: dict[str, Any]) -> None:
    """Store a discovered label in the LRU cache."""
    cache_key = f"{chain}:{address}"
    _label_cache.put(cache_key, label)


# ---------------------------------------------------------------------------
# Type checkers — used by alert_engine for classification
# ---------------------------------------------------------------------------

def is_cex(chain: str, address: str) -> bool:
    """Check if an address belongs to a known CEX."""
    label = get_label(chain, address)
    return label["type"] == "cex"


def is_bridge(chain: str, address: str) -> bool:
    """Check if an address is a known bridge."""
    label = get_label(chain, address)
    return label["type"] == "bridge"


def is_dex(chain: str, address: str) -> bool:
    """Check if an address is a known DEX."""
    label = get_label(chain, address)
    return label["type"] in ("dex", "trading_bot")


def is_mev(chain: str, address: str) -> bool:
    """Check if an address is a known MEV bot or MEV infrastructure."""
    label = get_label(chain, address)
    return label["type"] in ("mev_bot", "mev_infra")


def is_market_maker(chain: str, address: str) -> bool:
    """Check if an address is a known market maker."""
    label = get_label(chain, address)
    return label["type"] == "market_maker"


def is_smart_money(chain: str, address: str) -> bool:
    """Check if an address is smart money (VC, fund, market maker, foundation)."""
    label = get_label(chain, address)
    return label["type"] in ("fund", "market_maker", "foundation", "whale")


def is_memecoin_infra(chain: str, address: str) -> bool:
    """Check if an address is memecoin infrastructure (Pump.fun, etc.)."""
    label = get_label(chain, address)
    return label["type"] == "memecoin_infra"


def is_trading_bot(chain: str, address: str) -> bool:
    """Check if an address is a known trading bot (Banana Gun, Maestro, etc.)."""
    label = get_label(chain, address)
    return label["type"] == "trading_bot"


def get_entity(chain: str, address: str) -> str | None:
    """Return the entity name for a known address, or None."""
    label = get_label(chain, address)
    return label.get("entity")
