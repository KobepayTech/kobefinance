"""The instrument universe, organised by exchange.

Each entry is ``(symbol, company name, seed price)`` in the exchange's local
currency. Symbols and companies are real listings; seed prices are
representative starting points for the simulator (clearly a simulated feed,
not live quotes). Currency is taken from the exchange definition, so it is
not repeated per row.
"""

from __future__ import annotations

from ..models import Instrument
from .exchanges import EXCHANGE_BY_CODE

# exchange code -> list of (symbol, name, seed_price in local currency)
LISTINGS: dict[str, list[tuple[str, str, float]]] = {
    # ---- Southern Africa ----
    "JSE": [
        ("NPN", "Naspers Ltd", 3650.00),
        ("PRX", "Prosus NV", 720.00),
        ("FSR", "FirstRand Ltd", 72.40),
        ("SBK", "Standard Bank Group", 214.00),
        ("MTN", "MTN Group", 98.50),
        ("SOL", "Sasol Ltd", 128.00),
        ("AGL", "Anglo American", 585.00),
        ("SHP", "Shoprite Holdings", 285.00),
        ("CPI", "Capitec Bank", 2740.00),
        ("VOD", "Vodacom Group", 108.00),
        ("ABG", "Absa Group", 168.00),
        ("BTI", "British American Tobacco", 640.00),
    ],
    "NSX": [
        ("FNB", "FNB Namibia Holdings", 49.50),
        ("NBS", "Namibia Breweries", 42.00),
    ],
    "BSE": [
        ("FNBB", "First National Bank Botswana", 4.05),
        ("LETSHEGO", "Letshego Holdings", 1.18),
        ("SECHABA", "Sechaba Brewery Holdings", 24.50),
    ],
    "LuSE": [
        ("ZANACO", "Zambia National Commercial Bank", 4.20),
        ("ZSUG", "Zambia Sugar", 6.80),
    ],
    "ZSE": [
        ("DLTA", "Delta Corporation", 145.00),
        ("ECO", "Econet Wireless Zimbabwe", 38.00),
        ("INN", "Innscor Africa", 210.00),
    ],
    "VFEX": [
        ("PADENGA", "Padenga Holdings", 0.32),
        ("SEED", "SeedCo International", 0.34),
        ("AXIA", "Axia Corporation", 0.28),
    ],
    "MSE": [
        ("NBM", "National Bank of Malawi", 2800.00),
        ("TNM", "Telekom Networks Malawi", 22.00),
    ],
    "BVMM": [
        ("BIM", "Banco Internacional de Moçambique", 95.00),
    ],

    # ---- West Africa ----
    "NGX": [
        ("DANGCEM", "Dangote Cement", 480.00),
        ("BUACEMENT", "BUA Cement", 102.00),
        ("MTNN", "MTN Nigeria", 205.00),
        ("AIRTELAFRI", "Airtel Africa", 2050.00),
        ("GTCO", "Guaranty Trust Holding", 46.50),
        ("ZENITHBANK", "Zenith Bank", 41.00),
        ("UBA", "United Bank for Africa", 31.00),
        ("ACCESSCORP", "Access Holdings", 22.50),
        ("NESTLE", "Nestlé Nigeria", 945.00),
        ("SEPLAT", "Seplat Energy", 4600.00),
    ],
    "BRVM": [
        ("SNTS", "Sonatel", 18500.00),
        ("ETIT", "Ecobank Transnational", 21.00),
        ("SGBC", "Société Générale Côte d'Ivoire", 13200.00),
        ("ONTBF", "Onatel Burkina Faso", 3550.00),
        ("PALC", "Palm Côte d'Ivoire", 7100.00),
    ],
    "GSE": [
        ("MTNGH", "MTN Ghana", 2.55),
        ("GCB", "GCB Bank", 6.10),
        ("EGH", "Ecobank Ghana", 7.40),
        ("TOTAL", "TotalEnergies Ghana", 14.20),
        ("GGBL", "Guinness Ghana Breweries", 3.10),
    ],
    "BVC": [
        ("BCA", "Banco Comercial do Atlântico", 1100.00),
    ],

    # ---- East Africa ----
    "NSE": [
        ("SCOM", "Safaricom", 18.30),
        ("EQTY", "Equity Group Holdings", 45.10),
        ("KCB", "KCB Group", 40.20),
        ("EABL", "East African Breweries", 152.00),
        ("COOP", "Co-operative Bank of Kenya", 16.40),
        ("ABSA", "Absa Bank Kenya", 17.10),
        ("BAT", "BAT Kenya", 405.00),
    ],
    "DSE": [
        ("CRDB", "CRDB Bank", 520.00),
        ("NMB", "NMB Bank", 4050.00),
        ("TBL", "Tanzania Breweries", 10900.00),
    ],
    "USE": [
        ("MTNU", "MTN Uganda", 182.00),
        ("SBU", "Stanbic Uganda Holdings", 31.50),
        ("UMEME", "Umeme Ltd", 385.00),
    ],
    "RSE": [
        ("BOK", "Bank of Kigali", 292.00),
        ("BRALIRWA", "Bralirwa", 131.00),
        ("MTNR", "MTN Rwanda", 152.00),
    ],
    "ESX": [
        ("WEGAGEN", "Wegagen Bank", 1000.00),
    ],

    # ---- North Africa ----
    "EGX": [
        ("COMI", "Commercial International Bank", 85.50),
        ("HRHO", "EFG Holding", 20.10),
        ("TMGH", "Talaat Moustafa Group", 51.00),
        ("SWDY", "Elsewedy Electric", 82.00),
        ("EAST", "Eastern Company", 31.00),
        ("ABUK", "Abu Qir Fertilizers", 56.00),
    ],
    "CSE": [
        ("IAM", "Maroc Telecom", 101.00),
        ("ATW", "Attijariwafa Bank", 522.00),
        ("BCP", "Banque Centrale Populaire", 282.00),
        ("LHM", "LafargeHolcim Maroc", 1810.00),
        ("CSR", "Cosumar", 205.00),
    ],
    "BVMT": [
        ("BIAT", "Banque Internationale Arabe de Tunisie", 118.00),
        ("SFBT", "Société Frigorifique et Brasserie de Tunis", 16.50),
    ],
    "ASE": [
        ("SAID", "Saidal", 720.00),
        ("BIOP", "Biopharm", 1250.00),
    ],

    # ---- Central Africa ----
    "BVMAC": [
        ("SEMC", "Société Anonyme des Brasseries du Cameroun", 121000.00),
    ],

    # ---- Indian Ocean ----
    "SEM": [
        ("MCBG", "MCB Group", 352.00),
        ("SBMH", "SBM Holdings", 5.30),
        ("IBL", "IBL Ltd", 49.50),
    ],
    "MERJ": [
        ("SACOS", "SACOS Group", 14.00),
    ],

    # ---- Global ----
    "NASDAQ": [
        ("AAPL", "Apple Inc.", 228.50),
        ("MSFT", "Microsoft Corp.", 462.10),
        ("NVDA", "NVIDIA Corp.", 138.75),
        ("GOOGL", "Alphabet Inc.", 191.20),
        ("AMZN", "Amazon.com Inc.", 219.40),
        ("META", "Meta Platforms", 612.80),
        ("TSLA", "Tesla Inc.", 345.60),
    ],
    "NYSE": [
        ("JPM", "JPMorgan Chase", 248.00),
        ("KO", "Coca-Cola Co.", 62.30),
        ("XOM", "Exxon Mobil", 112.40),
    ],
    "LSE": [
        ("SHEL", "Shell plc", 2710.00),
        ("HSBA", "HSBC Holdings", 712.00),
        ("AZN", "AstraZeneca", 11050.00),
        ("ULVR", "Unilever", 4720.00),
    ],
    "CRYPTO": [
        ("BTC-USD", "Bitcoin", 96250.00),
        ("ETH-USD", "Ethereum", 3380.00),
        ("SOL-USD", "Solana", 188.00),
        ("BNB-USD", "BNB", 695.00),
        ("XRP-USD", "XRP", 2.18),
        ("ADA-USD", "Cardano", 0.92),
        ("DOGE-USD", "Dogecoin", 0.38),
    ],

    # ---- Foreign exchange (spot FX): majors + African pairs ----
    "FOREX": [
        # Majors
        ("EURUSD", "Euro / US Dollar", 1.08500),
        ("GBPUSD", "British Pound / US Dollar", 1.27200),
        ("USDJPY", "US Dollar / Japanese Yen", 157.2000),
        ("USDCHF", "US Dollar / Swiss Franc", 0.89500),
        ("AUDUSD", "Australian Dollar / US Dollar", 0.66300),
        ("USDCAD", "US Dollar / Canadian Dollar", 1.36800),
        ("NZDUSD", "New Zealand Dollar / US Dollar", 0.61200),
        # African currency pairs (the terminal's focus)
        ("USDZAR", "US Dollar / South African Rand", 18.0500),
        ("USDNGN", "US Dollar / Nigerian Naira", 1480.0000),
        ("USDKES", "US Dollar / Kenyan Shilling", 129.5000),
        ("USDEGP", "US Dollar / Egyptian Pound", 48.2000),
        ("USDGHS", "US Dollar / Ghanaian Cedi", 14.8000),
        ("USDMAD", "US Dollar / Moroccan Dirham", 9.95000),
        ("USDTZS", "US Dollar / Tanzanian Shilling", 2580.0000),
        ("USDUGX", "US Dollar / Ugandan Shilling", 3720.0000),
        ("EURZAR", "Euro / South African Rand", 19.6000),
        ("GBPZAR", "British Pound / South African Rand", 22.9500),
    ],
}

# Curated cross-region set shown on the dashboard (a uid is "SYMBOL.EXCHANGE").
DASHBOARD_WATCHLIST: list[str] = [
    "AAPL.NASDAQ", "MSFT.NASDAQ", "NVDA.NASDAQ",
    "NPN.JSE", "MTN.JSE",
    "DANGCEM.NGX", "MTNN.NGX",
    "SCOM.NSE", "COMI.EGX", "SNTS.BRVM",
    "EURUSD.FOREX", "GBPUSD.FOREX", "USDJPY.FOREX",
    "USDZAR.FOREX", "USDNGN.FOREX",
    "BTC-USD.CRYPTO", "ETH-USD.CRYPTO", "SOL-USD.CRYPTO",
]

# Asset class per exchange, for exchanges that aren't plain equities.
_KIND_BY_EXCHANGE: dict[str, str] = {"FOREX": "fx", "CRYPTO": "crypto"}


def _kind_and_currency(code: str, symbol: str, exchange_currency: str) -> tuple[str, str]:
    """Derive (kind, quote currency) for a listing on exchange *code*."""
    kind = _KIND_BY_EXCHANGE.get(code, "equity")
    if kind == "fx":
        # A 6-letter pair BASEQUOTE quotes in the second currency.
        currency = symbol[3:6] if len(symbol) >= 6 else "USD"
    elif kind == "crypto":
        currency = "USD"
    else:
        currency = exchange_currency
    return kind, currency


def build_universe() -> list[Instrument]:
    """Flatten :data:`LISTINGS` into :class:`Instrument` objects."""
    out: list[Instrument] = []
    for code, rows in LISTINGS.items():
        exchange = EXCHANGE_BY_CODE.get(code)
        if exchange is None:
            continue
        for symbol, name, seed in rows:
            kind, currency = _kind_and_currency(code, symbol, exchange.currency)
            out.append(
                Instrument(
                    symbol=symbol,
                    name=name,
                    exchange=code,
                    currency=currency,
                    seed_price=seed,
                    kind=kind,
                )
            )
    return out
