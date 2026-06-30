"""Company relationship graphs (supply chain / customers) with live stock data.

A graph centers on one company and links to related entities — suppliers,
customers, partners. Public entities resolve to a provider uid so the UI can
overlay live price/percent-change; private ones (consumers, carriers) carry no
market data. Includes a supplier-stress detector that flags broad weakness.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RelatedEntity:
    name: str
    relation: str            # "supplier" | "customer" | "partner"
    confidence: int          # 0-100
    importance: str          # "high" | "medium" | "low"
    uid: str | None = None   # provider uid if publicly traded, else None
    products: str = ""
    side: str = "left"       # "left" (suppliers) | "right" (customers)
    market_cap_b: float = 0.0  # approx market cap in USD billions (node sizing)


@dataclass(frozen=True)
class RelationshipGraph:
    center_name: str
    center_uid: str
    related: list[RelatedEntity] = field(default_factory=list)
    center_market_cap_b: float = 0.0

    def suppliers(self) -> list[RelatedEntity]:
        return [e for e in self.related if e.side == "left"]

    def customers(self) -> list[RelatedEntity]:
        return [e for e in self.related if e.side == "right"]


IMPORTANCE_WEIGHT = {"high": 4.2, "medium": 2.6, "low": 1.5}


# Hand-curated graphs. Keyed by center uid.
GRAPHS: dict[str, RelationshipGraph] = {
    "AAPL.NASDAQ": RelationshipGraph(
        center_name="Apple",
        center_uid="AAPL.NASDAQ",
        center_market_cap_b=3500.0,
        related=[
            RelatedEntity("TSMC", "supplier", 95, "high", "TSM.NYSE", "SoC fabrication", "left", 1000.0),
            RelatedEntity("Hon Hai (Foxconn)", "supplier", 90, "high", "2317.TWSE", "Final assembly", "left", 90.0),
            RelatedEntity("Broadcom", "supplier", 88, "high", "AVGO.NASDAQ", "Wireless & connectivity chips", "left", 1700.0),
            RelatedEntity("Qualcomm", "supplier", 82, "high", "QCOM.NASDAQ", "5G modems", "left", 190.0),
            RelatedEntity("Samsung Electronics", "supplier", 78, "high", "005930.KRX", "Displays & memory", "left", 370.0),
            RelatedEntity("Sony", "supplier", 70, "medium", "SONY.NYSE", "Camera image sensors", "left", 120.0),
            RelatedEntity("Consumers", "customer", 99, "high", None, "Device & services sales", "right"),
            RelatedEntity("Telecom carriers", "customer", 84, "high", None, "iPhone distribution", "right"),
            RelatedEntity("Retailers", "customer", 72, "medium", None, "Apple Store & resellers", "right"),
            RelatedEntity("Enterprise", "customer", 60, "medium", None, "Mac/iPad fleets", "right"),
        ],
    ),
    "NVDA.NASDAQ": RelationshipGraph(
        center_name="NVIDIA",
        center_uid="NVDA.NASDAQ",
        center_market_cap_b=3400.0,
        related=[
            RelatedEntity("TSMC", "supplier", 96, "high", "TSM.NYSE", "GPU fabrication", "left", 1000.0),
            RelatedEntity("SK hynix", "supplier", 88, "high", "000660.KRX", "HBM memory", "left", 120.0),
            RelatedEntity("Samsung Electronics", "supplier", 80, "high", "005930.KRX", "HBM / memory", "left", 370.0),
            RelatedEntity("Hon Hai (Foxconn)", "supplier", 75, "medium", "2317.TWSE", "Server systems", "left", 90.0),
            RelatedEntity("Microsoft", "customer", 92, "high", "MSFT.NASDAQ", "Azure AI compute", "right", 3300.0),
            RelatedEntity("Amazon", "customer", 88, "high", "AMZN.NASDAQ", "AWS GPU instances", "right", 2300.0),
            RelatedEntity("Meta", "customer", 86, "high", "META.NASDAQ", "AI training clusters", "right", 1500.0),
            RelatedEntity("Alphabet", "customer", 82, "high", "GOOGL.NASDAQ", "Cloud / AI", "right", 2100.0),
            RelatedEntity("Tesla", "customer", 68, "medium", "TSLA.NASDAQ", "Autonomy training", "right", 1100.0),
        ],
    ),
    "TSM.NYSE": RelationshipGraph(
        center_name="TSMC",
        center_uid="TSM.NYSE",
        center_market_cap_b=1000.0,
        related=[
            RelatedEntity("ASML", "supplier", 94, "high", None, "EUV lithography", "left"),
            RelatedEntity("Applied Materials", "supplier", 80, "medium", None, "Deposition / etch", "left"),
            RelatedEntity("Tokyo Electron", "supplier", 78, "medium", None, "Wafer processing", "left"),
            RelatedEntity("Apple", "customer", 95, "high", "AAPL.NASDAQ", "A/M-series SoCs", "right", 3500.0),
            RelatedEntity("NVIDIA", "customer", 95, "high", "NVDA.NASDAQ", "Data-center GPUs", "right", 3400.0),
            RelatedEntity("Qualcomm", "customer", 85, "high", "QCOM.NASDAQ", "Snapdragon SoCs", "right", 190.0),
            RelatedEntity("Broadcom", "customer", 84, "high", "AVGO.NASDAQ", "Networking / custom silicon", "right", 1700.0),
        ],
    ),
}


@dataclass(frozen=True)
class NodeView:
    """Resolved, display-ready view of a related entity."""

    entity: RelatedEntity
    public: bool
    price: float | None = None
    change_1d: float | None = None
    currency: str = ""
    kind: str = "equity"


def resolve_node(provider, entity: RelatedEntity) -> NodeView:
    """Attach live quote data to an entity (if it has a public uid)."""
    if entity.uid is None:
        return NodeView(entity=entity, public=False)
    quote = provider.quote(entity.uid)
    if quote is None:
        return NodeView(entity=entity, public=True)
    return NodeView(
        entity=entity,
        public=True,
        price=quote.price,
        change_1d=quote.change_pct,
        currency=quote.currency,
        kind=quote.kind,
    )


def stress_signal(
    provider, graph: RelationshipGraph, *, threshold: float = -3.0, min_count: int = 3
) -> tuple[int, list[tuple[str, float]]]:
    """Detect broad supplier weakness.

    Returns ``(count, movers)`` where *movers* are ``(ticker, pct)`` for
    suppliers down at least ``threshold`` today. A signal fires when *count*
    reaches *min_count* — the caller decides how to surface it.
    """
    movers: list[tuple[str, float]] = []
    for entity in graph.suppliers():
        node = resolve_node(provider, entity)
        if node.public and node.change_1d is not None and node.change_1d <= threshold:
            ticker = (entity.uid or entity.name).split(".")[0]
            movers.append((ticker, node.change_1d))
    movers.sort(key=lambda m: m[1])
    return (len(movers) if len(movers) >= min_count else 0, movers)
