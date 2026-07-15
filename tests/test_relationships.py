"""Tests for relationship graphs, node resolution, and the stress signal."""

from __future__ import annotations

from kobefinance.models import Instrument
from kobefinance.services.market_data import SimulatedProvider
from kobefinance.services.relationships import (
    GRAPHS,
    RelatedEntity,
    RelationshipGraph,
    build_peer_graph,
    resolve_node,
    stress_signal,
)
from kobefinance.services.universe import build_universe


def _from_returns(rets, start=100.0):
    out = [start]
    for r in rets:
        out.append(out[-1] * (1 + r))
    return out


def test_build_peer_graph_splits_by_correlation_sign():
    base = [-0.02, 0.01, 0.02, -0.01, 0.02, -0.02, 0.01, 0.01, -0.02, 0.02] * 3
    closes = {
        "C.X": _from_returns(base),
        "W.X": _from_returns([r * 0.9 for r in base]),   # moves with -> right
        "A.X": _from_returns([-r for r in base]),         # moves against -> left
    }
    inst = {
        "W.X": Instrument("W", "With Co", "NASDAQ", "USD", 100.0),
        "A.X": Instrument("A", "Against Co", "NASDAQ", "USD", 100.0),
    }
    graph = build_peer_graph("C.X", "Center", closes, inst, top=5)
    names_right = {e.name for e in graph.customers()}
    names_left = {e.name for e in graph.suppliers()}
    assert "With Co" in names_right
    assert "Against Co" in names_left
    assert all(0 <= e.confidence <= 100 for e in graph.related)


def test_build_peer_graph_empty_when_no_history():
    graph = build_peer_graph("C.X", "Center", {}, {}, top=5)
    assert graph.center_uid == "C.X"
    assert graph.related == []


def test_apple_graph_present_and_split():
    graph = GRAPHS["AAPL.NASDAQ"]
    assert graph.center_name == "Apple"
    assert len(graph.suppliers()) >= 5
    assert len(graph.customers()) >= 2


def test_supplier_uids_exist_in_universe():
    uids = {i.uid for i in build_universe()}
    graph = GRAPHS["AAPL.NASDAQ"]
    for e in graph.related:
        if e.uid is not None:
            assert e.uid in uids, f"missing supplier uid {e.uid}"
    assert graph.center_uid in uids


def _provider_with(prices: dict[str, float]) -> SimulatedProvider:
    insts = [Instrument(uid.split(".")[0], uid, uid.split(".")[1], "USD", p) for uid, p in prices.items()]
    return SimulatedProvider(insts, seed=1)


def test_resolve_node_public_vs_private():
    provider = _provider_with({"AVGO.NASDAQ": 200.0})
    public_entity = RelatedEntity("Broadcom", "supplier", 88, "high", "AVGO.NASDAQ")
    private_entity = RelatedEntity("Consumers", "customer", 99, "high", None)
    pub = resolve_node(provider, public_entity)
    priv = resolve_node(provider, private_entity)
    assert pub.public and pub.price is not None
    assert not priv.public and priv.price is None


def test_stress_signal_fires_on_broad_weakness():
    # Build a graph whose suppliers are all currently well below seed (down day).
    provider = _provider_with({"A.NASDAQ": 100.0, "B.NASDAQ": 100.0, "C.NASDAQ": 100.0})
    # Force prices down ~5% from seed so change_pct is negative.
    for uid in ("A.NASDAQ", "B.NASDAQ", "C.NASDAQ"):
        provider._price[uid] = 95.0
    graph = RelationshipGraph(
        "X", "X.NASDAQ",
        [
            RelatedEntity("A", "supplier", 90, "high", "A.NASDAQ"),
            RelatedEntity("B", "supplier", 90, "high", "B.NASDAQ"),
            RelatedEntity("C", "supplier", 90, "high", "C.NASDAQ"),
        ],
    )
    count, movers = stress_signal(provider, graph)
    assert count == 3
    assert all(p < 0 for _, p in movers)


def test_stress_signal_quiet_when_few_down():
    provider = _provider_with({"A.NASDAQ": 100.0, "B.NASDAQ": 100.0})
    provider._price["A.NASDAQ"] = 94.0  # only one down
    graph = RelationshipGraph(
        "X", "X.NASDAQ",
        [
            RelatedEntity("A", "supplier", 90, "high", "A.NASDAQ"),
            RelatedEntity("B", "supplier", 90, "high", "B.NASDAQ"),
        ],
    )
    count, _ = stress_signal(provider, graph)
    assert count == 0
