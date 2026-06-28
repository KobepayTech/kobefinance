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
from kobefinance.ui.formatting import fmt_money


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


def test_universe_currency_matches_exchange():
    universe = build_universe()
    for inst in universe:
        assert inst.currency == EXCHANGE_BY_CODE[inst.exchange].currency


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
