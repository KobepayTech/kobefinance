# Feature parity vs FinceptTerminal

Reference inventory of [FinceptTerminal](https://github.com/Fincept-Corporation/FinceptTerminal)
capabilities and AI models, mapped to KobeFinance's status. FinceptTerminal is
AGPL/commercial — every item below is built **clean-room** for KobeFinance, not
copied.

Legend: ✅ done · ⚠️ partial · ⬜ missing

## AI models / LLM providers

| Provider | Fincept | KobeFinance |
| --- | --- | --- |
| Anthropic (Claude) | ✅ | ✅ `claude-opus-4-8` |
| Ollama (local) | ✅ | ✅ |
| llama.cpp (local) | — | ✅ |
| Template (offline) | — | ✅ |
| OpenAI (GPT) | ✅ | ⬜ |
| Google Gemini | ✅ | ⬜ |
| Groq | ✅ | ⬜ |
| DeepSeek | ✅ | ⬜ |
| MiniMax | ✅ | ⬜ |
| OpenRouter | ✅ | ⬜ |

- Fincept ships **37 persona agents** (Buffett, Graham, Lynch, Munger, Klarman,
  Marks + economic/geopolitics), targeting 50+. KobeFinance: AI chat + bot
  designer, no persona framework yet → ⬜.

## Features

| Capability | Fincept | KobeFinance |
| --- | --- | --- |
| Equity research | ✅ | ⚠️ fundamentals/analysts, no DCF |
| Portfolio + risk (VaR, Sharpe, drawdown) | ✅ | ✅ |
| Backtesting / algo bots | ✅ | ✅ Strategy Lab + auto-traders |
| Alpha factors / factor discovery | ✅ | ✅ factor library |
| Relationship mapping | ✅ | ✅ any-stock (curated + correlation peers) |
| Paper trading | ✅ | ✅ |
| Forex (MetaTrader) | ✅ | ✅ gated MT5 |
| News | ✅ | ✅ basic (Yahoo) |
| Crypto/equity quotes | ✅ | ✅ |
| Derivatives pricing | ✅ | ⬜ |
| Fixed income analysis | ✅ | ⬜ |
| Broker integrations (16: Zerodha, IBKR, Alpaca, Tradier, Saxo…) | ✅ | ⬜ (MT5 only) |
| Real-time crypto trading (Kraken/HyperLiquid WS) | ✅ | ⬜ (quotes only) |
| 100+ data connectors (Polygon, FRED, IMF, World Bank, DBnomics, AkShare) | ✅ | ⬜ |
| Sentiment / alt-data (Reddit, X, Polymarket, NLP) | ✅ | ⬜ |
| Quant modules (18: stochastic, vol surfaces, pricing) | ✅ | ⚠️ backtest + factors |
| Node editor / visual workflow builder | ✅ | ⬜ |
| MCP tool integration | ✅ | ⬜ |
| RL trading / HFT | ✅ | ⬜ |
| Maritime / satellite / geopolitics | ✅ | ⬜ |
| ML model training UI | ✅ | ⬜ |

## Suggested build order (highest value first)

1. **Multi-provider LLM layer** — add OpenAI, Gemini, Groq, DeepSeek, OpenRouter
   backends alongside the existing Claude/Ollama/llama.cpp/template (small,
   high-leverage; unlocks the persona agents).
2. **AI persona/analyst agents** — Buffett/Graham/Lynch/Munger style agents over
   our fundamentals + factors, each returning a structured thesis.
3. **More data connectors** — FRED, World Bank, IMF, Polygon (free tiers) behind
   the existing provider protocol.
4. **DCF + derivatives + fixed-income** calculators (extends Equity Research /
   quant modules).
5. **Sentiment / alt-data** (news NLP first, then social).
6. **Node editor / visual workflow builder** (larger UI effort).
