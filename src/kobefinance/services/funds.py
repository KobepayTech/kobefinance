"""Fund statement parsing and chain-graph building (the "Fund Chain" feature).

Reads a fund interim/annual statement PDF (rule-based, tuned for UTT AMIS /
Umoja Fund-style reports) into a :class:`FundReport` — NAV, net/total assets,
manager, custodian, asset breakdown, and income drivers — and builds a
node/link graph for the Funds screen. pdfplumber is imported lazily so the
package loads without it; a bundled sample report keeps the screen usable
offline.

Adapted from the user's fund_chain_bot pipeline.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

TZS_MULTIPLIER = 1000  # statement tables are labelled TZS '000'


# -- number / money helpers ---------------------------------------------------


def _to_number(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("−", "-")
    if text in {"", "-", "—"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^0-9.\-]", "", text.strip("()"))
    if text in {"", ".", "-"}:
        return None
    try:
        n = float(text)
        return -n if negative else n
    except ValueError:
        return None


def money_from_statement_thousand(value: str | None) -> float | None:
    n = _to_number(value)
    return None if n is None else n * TZS_MULTIPLIER


def fmt_tzs(value: float | None) -> str:
    if value is None:
        return "—"
    abs_v = abs(value)
    sign = "-" if value < 0 else ""
    if abs_v >= 1e12:
        return f"{sign}TZS {abs_v / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{sign}TZS {abs_v / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{sign}TZS {abs_v / 1e6:.2f}M"
    return f"{sign}TZS {abs_v:,.0f}"


# -- data model ---------------------------------------------------------------


@dataclass
class FundReport:
    fund_name: str
    report_date: str | None = None
    manager: str | None = None
    custodian: str | None = None
    nav_per_unit: float | None = None
    net_assets_tzs: float | None = None
    total_assets_tzs: float | None = None
    net_income_tzs: float | None = None
    assets: dict[str, float | None] = field(default_factory=dict)
    income: dict[str, float | None] = field(default_factory=dict)
    rules: dict[str, str] = field(default_factory=dict)
    source_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# -- PDF parsing --------------------------------------------------------------


def download_pdf(url: str, dest_dir: str | Path) -> Path:
    """Download a PDF to *dest_dir* using a proxy/CA-aware session."""
    from .fundamentals import _get_session  # reuse CA-bundle session

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(url.split("?")[0]).name) or "report.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    dest = dest_dir / name

    session = _get_session()
    if session is None:
        import urllib.request

        urllib.request.urlretrieve(url, dest)
        return dest
    with session.get(url, timeout=60, stream=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=131072):
                if chunk:
                    fh.write(chunk)
    return dest


def extract_text(pdf_path: str | Path) -> str:
    import pdfplumber

    chunks: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
    return "\n".join(chunks)


def _first_group(pattern: str, text: str, flags: int = re.I | re.S) -> str | None:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _line_money(label: str, text: str) -> float | None:
    # Row like: "Treasury bonds 134,785,306 181,672,862 162,687,311".
    # Anchored to line start so "Equity Investments" doesn't match
    # "Valuation gain/(loss) on equity investments".
    pat = rf"^\s*{re.escape(label)}\s+([\(\)\d,.-]+)\s+[\(\)\d,.-]+\s+[\(\)\d,.-]+"
    m = re.search(pat, text, re.I | re.M)
    return money_from_statement_thousand(m.group(1)) if m else None


ASSET_LABELS = [
    "Cash and cash equivalents",
    "Term deposits with banks",
    "Treasury bonds",
    "Corporate bonds",
    "Equity Investments",
    "Interest receivable",
    "Other receivables",
]
INCOME_LABELS = [
    "Interest income",
    "Gross dividend income",
    "Valuation gain/(loss) on equity investments",
    "Other income/(loss)",
    "Total income",
    "Operating expenses",
    "Taxation",
    "Change in net assets attributable to unit holders",
]


def parse_fund_report(pdf_path: str | Path) -> FundReport:
    """Parse a fund statement PDF into a :class:`FundReport`."""
    text = extract_text(pdf_path)
    compact = re.sub(r"\s+", " ", text)

    fund_name = (
        "Umoja Fund"
        if re.search(r"Umoja Fund", compact, re.I)
        else (_first_group(r"(\b[A-Z][A-Za-z ]+ Fund\b)", compact) or "Unknown Fund")
    )
    report_date = _first_group(
        r"period ended\s+([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+20\d{2})", compact
    ) or _first_group(r"AS AT\s+([0-9]{1,2}(?:st|nd|rd|th)?\s*[A-Za-z]+\s*20\d{2})", compact)

    manager = (
        "UTT AMIS"
        if re.search(r"UTT AMIS", compact, re.I)
        else _first_group(r"thereafter by\s+([^,]+?),\s+a Registered Fund Manager", compact)
    )
    custodian = _first_group(
        r"The Custodian of the Fund is\s+([^,\.]+(?:Plc|PLC|Limited|Ltd)?)", compact
    )

    assets = {label: _line_money(label, text) for label in ASSET_LABELS}
    income = {label: _line_money(label, text) for label in INCOME_LABELS}

    nav_per_unit = None
    sec = re.search(r"Net Asset Value per unit(?P<s>.*?)(?:Prof\.|Board Chairman|$)", text, re.I | re.S)
    if sec:
        nums = re.findall(r"\d[\d,]*\.\d{2}", sec.group("s"))
        if len(nums) >= 3:
            nav_per_unit = _to_number(nums[-3])

    rules: dict[str, str] = {}
    sale = _first_group(r"sale price is based on\s+(.*?same working day)", compact)
    repurchase = _first_group(r"re-purchase price is based on\s+(.*?service charge)", compact)
    if sale:
        rules["sale_price"] = sale
    if repurchase:
        rules["repurchase_price"] = repurchase

    return FundReport(
        fund_name=fund_name,
        report_date=report_date,
        manager=manager,
        custodian=custodian,
        nav_per_unit=nav_per_unit,
        net_assets_tzs=_line_money("Net-assets attributable to unit holders", text),
        total_assets_tzs=_line_money("Total assets", text),
        net_income_tzs=income.get("Change in net assets attributable to unit holders"),
        assets=assets,
        income=income,
        rules=rules,
        source_file=str(pdf_path),
    )


# -- graph building -----------------------------------------------------------


@dataclass(frozen=True)
class FundNode:
    id: str
    label: str
    type: str           # fund|manager|custodian|investor|regulator|asset|income
    side: str           # center|left|right|bottom
    value: float | None = None
    subtitle: str = ""


@dataclass(frozen=True)
class FundLink:
    source: str
    target: str
    label: str


def _pct(value: float | None, total: float | None) -> str:
    if value is None or not total:
        return "—"
    return f"{value / total * 100:.1f}%"


def build_fund_graph(report: FundReport) -> tuple[list[FundNode], list[FundLink]]:
    """Build categorized nodes + links from a :class:`FundReport`."""
    nodes: list[FundNode] = []
    links: list[FundLink] = []

    nav = f"  ·  NAV {report.nav_per_unit:,.2f}" if report.nav_per_unit else ""
    nodes.append(
        FundNode("fund", f"{report.fund_name}{nav}", "fund", "center",
                 report.net_assets_tzs, f"Net assets {fmt_tzs(report.net_assets_tzs)}")
    )

    left = []
    if report.manager:
        left.append(FundNode("manager", report.manager, "manager", "left", subtitle="Fund Manager"))
        links.append(FundLink("manager", "fund", "manages"))
    if report.custodian:
        left.append(FundNode("custodian", report.custodian, "custodian", "left", subtitle="Custodian"))
        links.append(FundLink("custodian", "fund", "custody"))
    left.append(FundNode("unit_holders", "Unit Holders", "investor", "left",
                         report.net_assets_tzs, fmt_tzs(report.net_assets_tzs)))
    links.append(FundLink("unit_holders", "fund", "capital"))
    left.append(FundNode("regulator", "CMSA / CIS Rules", "regulator", "left", subtitle="Regulated scheme"))
    links.append(FundLink("regulator", "fund", "regulates"))
    nodes.extend(left)

    total = report.total_assets_tzs
    asset_order = [
        "Equity Investments", "Treasury bonds", "Term deposits with banks",
        "Interest receivable", "Corporate bonds", "Cash and cash equivalents",
        "Other receivables",
    ]
    for name in asset_order:
        value = report.assets.get(name)
        if value is None:
            continue
        nid = "asset_" + re.sub(r"[^a-z0-9]+", "_", name.lower())
        nodes.append(FundNode(nid, name, "asset", "right", value,
                              f"{fmt_tzs(value)} · {_pct(value, total)}"))
        links.append(FundLink("fund", nid, "holds"))

    income_order = [
        "Interest income", "Valuation gain/(loss) on equity investments",
        "Gross dividend income", "Other income/(loss)",
    ]
    for name in income_order:
        value = report.income.get(name)
        if value is None:
            continue
        nid = "income_" + re.sub(r"[^a-z0-9]+", "_", name.lower())
        nodes.append(FundNode(nid, name, "income", "bottom", value, fmt_tzs(value)))
        links.append(FundLink(nid, "fund", "income"))

    return nodes, links


# -- history (sqlite) ---------------------------------------------------------


def save_report(db_path: str | Path, report: FundReport) -> None:
    import json

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute(
        """CREATE TABLE IF NOT EXISTS fund_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fund_name TEXT, report_date TEXT,
            nav_per_unit REAL, net_assets_tzs REAL, total_assets_tzs REAL,
            manager TEXT, custodian TEXT, source_file TEXT, payload_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
    )
    con.execute(
        """INSERT INTO fund_reports (fund_name, report_date, nav_per_unit,
            net_assets_tzs, total_assets_tzs, manager, custodian, source_file, payload_json)
            VALUES (?,?,?,?,?,?,?,?,?)""",
        (report.fund_name, report.report_date, report.nav_per_unit, report.net_assets_tzs,
         report.total_assets_tzs, report.manager, report.custodian, report.source_file,
         json.dumps(report.to_dict(), ensure_ascii=False)),
    )
    con.commit()
    con.close()


# -- bundled sample (offline demo / tests) ------------------------------------

SAMPLE_UMOJA = FundReport(
    fund_name="Umoja Fund",
    report_date="31ST DECEMBER 2025",
    manager="UTT AMIS",
    custodian="CRDB Bank Plc",
    nav_per_unit=1281.38,
    net_assets_tzs=427_863_311_000.0,
    total_assets_tzs=445_894_596_000.0,
    net_income_tzs=29_747_649_000.0,
    assets={
        "Equity Investments": 176_463_217_000.0,
        "Treasury bonds": 134_785_306_000.0,
        "Term deposits with banks": 106_705_000_000.0,
        "Interest receivable": 26_997_783_000.0,
        "Corporate bonds": 300_000_000.0,
        "Cash and cash equivalents": 283_077_000.0,
        "Other receivables": 360_213_000.0,
    },
    income={
        "Interest income": 15_875_539_000.0,
        "Valuation gain/(loss) on equity investments": 15_433_659_000.0,
        "Gross dividend income": 3_276_908_000.0,
        "Other income/(loss)": 1_010_925_000.0,
    },
    source_file="(bundled sample)",
)
