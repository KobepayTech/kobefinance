"""Tests for the exchange registry, universe wiring, and currency formatting."""

from __future__ import annotations

from kobefinance.services.exchanges import (
    EXCHANGE_BY_CODE,
    EXCHANGES,
    REGIONS,
    african_exchanges,
    exchanges_in_region,
)
from kobefinance.services.universe import (
    DASHBOARD_WATCHLIST,
    LISTINGS,
    build_universe,
)
from kobefinance.ui.formatting import fmt_instrument_price, fmt_money, fmt_rate


def test_exchange_codes_unique():
    codes = [e.code for e in EXCHANGES]
    assert len(codes) == len(set(codes))


def test_every_region_has_exchanges_except_none():
    # Every declared region should map to at least one exchange.
    for region in REGIONS:
        assert exchanges_in_region(region), f"no exchanges in {region}"


def test_comprehensive_african_coverage():
    african = african_exchanges()
    # Sanity: a broad set across the continent is present.
    must_have = {"JSE", "NGX", "NSE", "EGX", "CSE", "BRVM", "GSE", "SEM", "DSE", "USE"}
    assert must_have.issubset({e.code for e in african})
    assert len(african) >= 25


def test_listings_reference_known_exchanges():
    for code in LISTINGS:
        assert code in EXCHANGE_BY_CODE, f"listing for unknown exchange {code}"


def test_equity_currency_matches_exchange():
    for inst in build_universe():
        if inst.kind == "equity":
            assert inst.currency == EXCHANGE_BY_CODE[inst.exchange].currency


def test_fx_pairs_quote_in_second_currency():
    by_uid = {i.uid: i for i in build_universe()}
    assert by_uid["EURUSD.FOREX"].kind == "fx"
    assert by_uid["EURUSD.FOREX"].currency == "USD"
    assert by_uid["USDZAR.FOREX"].currency == "ZAR"
    assert by_uid["USDNGN.FOREX"].currency == "NGN"


def test_crypto_quotes_in_usd():
    by_uid = {i.uid: i for i in build_universe()}
    btc = by_uid["BTC-USD.CRYPTO"]
    assert btc.kind == "crypto"
    assert btc.currency == "USD"


def test_universe_uids_unique():
    uids = [i.uid for i in build_universe()]
    assert len(uids) == len(set(uids))


def test_dashboard_watchlist_resolves():
    uids = {i.uid for i in build_universe()}
    for uid in DASHBOARD_WATCHLIST:
        assert uid in uids, f"watchlist uid not in universe: {uid}"


def test_fmt_money_known_symbol():
    assert fmt_money(1234.5, "ZAR") == "R1,234.50"
    assert fmt_money(99.0, "NGN") == "₦99.00"


def test_fmt_money_unknown_currency_falls_back_to_code():
    assert fmt_money(1000.0, "ETB") == "1,000.00 ETB"


def test_fmt_rate_precision_scales():
    assert fmt_rate(1.085) == "1.08500"      # EURUSD-style
    assert fmt_rate(18.05) == "18.0500"      # USDZAR-style
    assert fmt_rate(157.2) == "157.20"       # USDJPY-style
    assert fmt_rate(1480.0) == "1,480.00"    # USDNGN-style


def test_fmt_instrument_price_by_kind():
    assert fmt_instrument_price(1.085, "USD", "fx") == "1.08500"
    assert fmt_instrument_price(96250.0, "USD", "crypto") == "$96,250.00"
    assert fmt_instrument_price(228.5, "USD", "equity") == "$228.50"
