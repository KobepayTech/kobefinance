"""Tests for fund statement parsing and chain-graph building."""

from __future__ import annotations

import kobefinance.services.funds as funds
from kobefinance.services.funds import (
    SAMPLE_UMOJA,
    _line_money,
    _to_number,
    build_fund_graph,
    fmt_tzs,
    money_from_statement_thousand,
    parse_fund_report,
)

_STATEMENT = """
Umoja Fund Interim Report and Accounts for the period ended 31st December 2025
The Fund is managed by UTT AMIS, a Registered Fund Manager.
The Custodian of the Fund is CRDB Bank Plc, appointed under the trust deed.
Cash and cash equivalents 283,077 250,000 240,000
Term deposits with banks 106,705,000 100,000,000 95,000,000
Treasury bonds 134,785,306 181,672,862 162,687,311
Equity Investments 176,463,217 150,000,000 140,000,000
Interest receivable 26,997,783 20,000,000 18,000,000
Total assets 445,894,596 430,000,000 410,000,000
Net-assets attributable to unit holders 427,863,311 410,000,000 395,000,000
Interest income 15,875,539 12,000,000 11,000,000
Gross dividend income 3,276,908 2,500,000 2,400,000
Net Asset Value per unit 1,281.38 1,200.00 1,250.00
"""


def test_number_and_money_helpers():
    assert _to_number("1,234") == 1234.0
    assert _to_number("(500)") == -500.0
    assert _to_number("—") is None
    assert money_from_statement_thousand("134,785,306") == 134_785_306_000.0


def test_fmt_tzs_scales():
    assert fmt_tzs(427_863_311_000.0) == "TZS 427.86B"
    assert fmt_tzs(300_000_000.0) == "TZS 300.00M"
    assert fmt_tzs(-5_000_000_000.0) == "-TZS 5.00B"
    assert fmt_tzs(None) == "—"


def test_line_money_anchors_to_line_start():
    assert _line_money("Treasury bonds", _STATEMENT) == 134_785_306_000.0
    # "Equity Investments" must not match the valuation-gain income line.
    assert _line_money("Equity Investments", _STATEMENT) == 176_463_217_000.0


def test_parse_fund_report_on_text(monkeypatch):
    monkeypatch.setattr(funds, "extract_text", lambda _p: _STATEMENT)
    report = parse_fund_report("dummy.pdf")
    assert report.fund_name == "Umoja Fund"
    assert report.manager == "UTT AMIS"
    assert report.custodian.startswith("CRDB Bank")
    assert report.report_date == "31st December 2025"
    assert report.nav_per_unit == 1281.38
    assert report.total_assets_tzs == 445_894_596_000.0
    assert report.assets["Treasury bonds"] == 134_785_306_000.0
    assert report.income["Interest income"] == 15_875_539_000.0


def test_build_fund_graph_structure():
    nodes, links = build_fund_graph(SAMPLE_UMOJA)
    ids = {n.id for n in nodes}
    assert "fund" in ids and "manager" in ids and "custodian" in ids
    assert "unit_holders" in ids and "regulator" in ids
    assert "asset_equity_investments" in ids
    assert any(n.type == "income" for n in nodes)
    # Center fund node.
    fund = next(n for n in nodes if n.id == "fund")
    assert fund.side == "center"
    # Every link references existing nodes.
    for link in links:
        assert link.source in ids and link.target in ids


def test_sample_allocation_sums_close_to_total():
    total = sum(v for v in SAMPLE_UMOJA.assets.values() if v)
    assert abs(total - 445_894_596_000.0) / 445_894_596_000.0 < 0.01
