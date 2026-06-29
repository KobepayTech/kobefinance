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


@dataclass(frozen=True)
class RelationshipGraph:
    center_name: str
    center_uid: str
    related: list[RelatedEntity] = field(default_factory=list)

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
        related=[
            RelatedEntity("TSMC", "supplier", 95, "high", "TSM.NYSE", "SoC fabrication", "left"),
            RelatedEntity("Hon Hai (Foxconn)", "supplier", 90, "high", "2317.TWSE", "Final assembly", "left"),
            RelatedEntity("Broadcom", "supplier", 88, "high", "AVGO.NASDAQ", "Wireless & connectivity chips", "left"),
            RelatedEntity("Qualcomm", "supplier", 82, "high", "QCOM.NASDAQ", "5G modems", "left"),
            RelatedEntity("Samsung Electronics", "supplier", 78, "high", "005930.KRX", "Displays & memory", "left"),
            RelatedEntity("Sony", "supplier", 70, "medium", "SONY.NYSE", "Camera image sensors", "left"),
            RelatedEntity("Consumers", "customer", 99, "high", None, "Device & services sales", "right"),
            RelatedEntity("Telecom carriers", "customer", 84, "high", None, "iPhone distribution", "right"),
            RelatedEntity("Retailers", "customer", 72, "medium", None, "Apple Store & resellers", "right"),
            RelatedEntity("Enterprise", "customer", 60, "medium", None, "Mac/iPad fleets", "right"),
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
