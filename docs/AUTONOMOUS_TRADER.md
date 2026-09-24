# KobeFinance Autonomous Trader

Integration target: Automaton-style continuous planning/memory/tools plus Jev-style fast bounded decisions.

Automaton is MIT licensed: copied/ported components must retain its license and attribution. Jev itself is proprietary/hosted, so KobeFinance uses an API adapter rather than copying or reverse-engineering Jev. A local bounded-decision adapter is included as an alternative.

## Boundary
AI proposes judgments. Deterministic code computes state, sizes risk and can veto. Broker code alone executes. Research mode never trades; paper mode must use PaperBroker; live mode must be explicitly enabled with trade-only credentials and withdrawals disabled.

## Loop
market data -> state -> memory -> planner -> bounded decision -> risk veto -> broker -> outcome -> memory/calibration

## Local model
KobeFinance already supports Ollama/llama.cpp. Use a capable local reasoning model for planner/research/critic tasks. For the fast Jev-like layer, benchmark a small classifier/ranker rather than a large chat model. A Qwen-family 4B-class model or an open Jev-like bounded classifier is the intended starting point.

## Next
Port Automaton memory/state/heartbeat/tool-policy concepts into Python; add SQLite episodic/semantic/procedural trade memory, calibration logs, Strategy Arena, paper execution adapter, tests, and Autonomous Desk UI before enabling live autonomy.
