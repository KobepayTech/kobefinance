"""Registry of stock exchanges.

The terminal is global, but African exchanges are covered comprehensively
here. Each exchange carries the metadata screens need: display name, country,
city, ISO-4217 trading currency, MIC, IANA timezone, and (where one exists)
the Yahoo Finance ticker suffix used to fetch live data later.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Exchange:
    code: str          # short internal code, e.g. "JSE"
    name: str
    country: str
    city: str
    currency: str      # ISO 4217
    region: str
    mic: str = ""      # ISO 10383 Market Identifier Code
    timezone: str = ""
    yahoo_suffix: str = ""  # e.g. ".JO" for the JSE; "" if unsupported


# Region ordering for grouped display.
REGIONS: tuple[str, ...] = (
    "Southern Africa",
    "West Africa",
    "East Africa",
    "North Africa",
    "Central Africa",
    "Indian Ocean",
    "Global",
)

EXCHANGES: list[Exchange] = [
    # ---- Southern Africa ----
    Exchange("JSE", "Johannesburg Stock Exchange", "South Africa", "Johannesburg", "ZAR", "Southern Africa", "XJSE", "Africa/Johannesburg", ".JO"),
    Exchange("A2X", "A2X Markets", "South Africa", "Johannesburg", "ZAR", "Southern Africa", "A2XX", "Africa/Johannesburg"),
    Exchange("NSX", "Namibian Stock Exchange", "Namibia", "Windhoek", "NAD", "Southern Africa", "XNAM", "Africa/Windhoek"),
    Exchange("BSE", "Botswana Stock Exchange", "Botswana", "Gaborone", "BWP", "Southern Africa", "XBOT", "Africa/Gaborone"),
    Exchange("LuSE", "Lusaka Securities Exchange", "Zambia", "Lusaka", "ZMW", "Southern Africa", "XLUS", "Africa/Lusaka"),
    Exchange("ZSE", "Zimbabwe Stock Exchange", "Zimbabwe", "Harare", "ZWG", "Southern Africa", "XZIM", "Africa/Harare"),
    Exchange("VFEX", "Victoria Falls Stock Exchange", "Zimbabwe", "Victoria Falls", "USD", "Southern Africa", "", "Africa/Harare"),
    Exchange("MSE", "Malawi Stock Exchange", "Malawi", "Blantyre", "MWK", "Southern Africa", "XMSW", "Africa/Blantyre"),
    Exchange("ESE", "Eswatini Stock Exchange", "Eswatini", "Mbabane", "SZL", "Southern Africa", "XSWA", "Africa/Mbabane"),
    Exchange("MSM", "Maseru Securities Market", "Lesotho", "Maseru", "LSL", "Southern Africa", "", "Africa/Maseru"),
    Exchange("BVMM", "Bolsa de Valores de Moçambique", "Mozambique", "Maputo", "MZN", "Southern Africa", "XBVM", "Africa/Maputo"),
    Exchange("BODIVA", "Bolsa de Dívida e Valores de Angola", "Angola", "Luanda", "AOA", "Southern Africa", "XBDV", "Africa/Luanda"),

    # ---- West Africa ----
    Exchange("NGX", "Nigerian Exchange", "Nigeria", "Lagos", "NGN", "West Africa", "XNSA", "Africa/Lagos"),
    Exchange("BRVM", "Bourse Régionale des Valeurs Mobilières", "WAEMU (regional)", "Abidjan", "XOF", "West Africa", "XBRV", "Africa/Abidjan"),
    Exchange("GSE", "Ghana Stock Exchange", "Ghana", "Accra", "GHS", "West Africa", "XGHA", "Africa/Accra"),
    Exchange("SLSE", "Sierra Leone Stock Exchange", "Sierra Leone", "Freetown", "SLE", "West Africa", "", "Africa/Freetown"),
    Exchange("BVC", "Bolsa de Valores de Cabo Verde", "Cape Verde", "Praia", "CVE", "West Africa", "XBVC", "Atlantic/Cape_Verde"),

    # ---- East Africa ----
    Exchange("NSE", "Nairobi Securities Exchange", "Kenya", "Nairobi", "KES", "East Africa", "XNAI", "Africa/Nairobi"),
    Exchange("DSE", "Dar es Salaam Stock Exchange", "Tanzania", "Dar es Salaam", "TZS", "East Africa", "XDAR", "Africa/Dar_es_Salaam"),
    Exchange("USE", "Uganda Securities Exchange", "Uganda", "Kampala", "UGX", "East Africa", "XUGA", "Africa/Kampala"),
    Exchange("RSE", "Rwanda Stock Exchange", "Rwanda", "Kigali", "RWF", "East Africa", "RSEX", "Africa/Kigali"),
    Exchange("ESX", "Ethiopian Securities Exchange", "Ethiopia", "Addis Ababa", "ETB", "East Africa", "", "Africa/Addis_Ababa"),

    # ---- North Africa ----
    Exchange("EGX", "Egyptian Exchange", "Egypt", "Cairo", "EGP", "North Africa", "XCAI", "Africa/Cairo"),
    Exchange("CSE", "Casablanca Stock Exchange", "Morocco", "Casablanca", "MAD", "North Africa", "XCAS", "Africa/Casablanca"),
    Exchange("BVMT", "Bourse de Tunis", "Tunisia", "Tunis", "TND", "North Africa", "XTUN", "Africa/Tunis"),
    Exchange("ASE", "Algiers Stock Exchange", "Algeria", "Algiers", "DZD", "North Africa", "XALG", "Africa/Algiers"),
    Exchange("LSM", "Libyan Stock Market", "Libya", "Tripoli", "LYD", "North Africa", "", "Africa/Tripoli"),
    Exchange("KSE", "Khartoum Stock Exchange", "Sudan", "Khartoum", "SDG", "North Africa", "", "Africa/Khartoum"),

    # ---- Central Africa ----
    Exchange("BVMAC", "Bourse des Valeurs Mobilières de l'Afrique Centrale", "CEMAC (regional)", "Douala", "XAF", "Central Africa", "", "Africa/Douala"),

    # ---- Indian Ocean ----
    Exchange("SEM", "Stock Exchange of Mauritius", "Mauritius", "Port Louis", "MUR", "Indian Ocean", "XMAU", "Indian/Mauritius"),
    Exchange("MERJ", "MERJ Exchange", "Seychelles", "Victoria", "SCR", "Indian Ocean", "TRPX", "Indian/Mahe"),

    # ---- Global (terminal is worldwide) ----
    Exchange("NASDAQ", "Nasdaq Stock Market", "United States", "New York", "USD", "Global", "XNAS", "America/New_York"),
    Exchange("NYSE", "New York Stock Exchange", "United States", "New York", "USD", "Global", "XNYS", "America/New_York"),
    Exchange("LSE", "London Stock Exchange", "United Kingdom", "London", "GBP", "Global", "XLON", "Europe/London", ".L"),
    Exchange("CRYPTO", "Crypto (global)", "Global", "—", "USD", "Global", "", "UTC"),
]

# Fast lookup by code.
EXCHANGE_BY_CODE: dict[str, Exchange] = {e.code: e for e in EXCHANGES}


def exchanges_in_region(region: str) -> list[Exchange]:
    """All exchanges in *region*, in registry order."""
    return [e for e in EXCHANGES if e.region == region]


def african_exchanges() -> list[Exchange]:
    """Every exchange except the Global region."""
    return [e for e in EXCHANGES if e.region != "Global"]
