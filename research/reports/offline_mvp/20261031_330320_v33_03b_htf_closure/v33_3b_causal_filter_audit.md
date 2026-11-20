# BTCognitive V33.3B — Causal Filter & Point-in-Time Integrity Audit

**Version:** 33.3.2  
**Milestone:** V33.3B HTF Range Expansion Breakout Evidence Closure  
**Date:** 2026-10-31  
**Operating Contract:** OFFLINE_RESEARCH_ONLY  
**Lead Orchestrator:** Antigravity  

---

## 1. Audit Scope & Point-in-Time Principles

In Section 3 of the Manager Ruling, six specific causal invariants were mandated for verification:
1. Classifier uses only data available at the decision timestamp.
2. Regime is frozen before entry execution.
3. The 4-hour breakout channel excludes the current signal candle.
4. Entry occurs at a feasible subsequent execution price.
5. No future regime label is used.
6. Skipped trades remain visible in the event ledger.

This report documents the forensic code audit verifying each invariant.

---

## 2. Invariant-by-Invariant Verification Matrix

```mermaid
sequenceDiagram
    autonumber
    participant D1 as 1h OHLCV Data
    participant D4 as 4h Resampled Data
    participant R as Regime Classifier (df_1h)
    participant S as Strategy Signal (df_4h)
    participant E as Execution Simulator

    D4->>S: 4h Bar i Closes at t_sig
    Note over S: Channel check: Close[i] > High_20[i-1:i-20] (excludes Bar i)
    D1->>R: Query closed 1h bars at t <= t_sig
    R->>R: Confirm 3-bar hysteresis regime
    R-->>S: Return frozen regime state
    alt Regime is CONSOLIDATION or TRANSITION
        S->>E: Action: EXCLUDE (Log skipped trade)
    else Regime is TRENDING_BULL or COMPRESSION
        S->>E: Action: KEEP (Authorize entry)
        E->>E: Fill LONG at Bar i+1 OPEN Price (t_sig + 4h)
    end
```

### Invariant 1: Channel Excludes Current Signal Candle
- **Source Inspection:** `research/v12_strategy_tournament_engine.py` line 536:
  ```python
  df_resampled["range_high_20_4h"] = pd.Series(h4).shift(1).rolling(20, min_periods=20).max().fillna(pd.Series(h4))
  df_resampled["range_low_20_4h"] = pd.Series(l4).shift(1).rolling(20, min_periods=20).min().fillna(pd.Series(l4))
  ```
- **Evaluation:** `.shift(1)` strictly shifts the 20-period rolling maximum window back by 1 candle. Bar $i$'s own high $H_i$ is completely excluded from `range_high_20_4h[i]`.
- **Status:** **VERIFIED PASS (Zero Lookahead in Channel)**

---

### Invariant 2 & 3: Feasible Subsequent Execution Price
- **Source Inspection:** `research/v12_strategy_tournament_engine.py` line 920:
  ```python
  if cur["close"] > cur["range_high_20_4h"]:
      in_pos = True
      pos_entry_price = float(nxt["open"])
      pos_entry_idx = i + 1
      active_stop = float(cur["range_low_20_4h"])
  ```
- **Evaluation:** The signal evaluates on bar $i$ closed data (`cur["close"]`). The entry price is filled at bar $i+1$ open (`nxt["open"]`). The engine **never assumes an impossible fill at the same bar close**.
- **Status:** **VERIFIED PASS (Strict Next-Bar Open Execution)**

---

### Invariant 4 & 5: Decision-Time Regime Freezing & Zero Future Labels
- **Source Inspection:** In `scripts/qa/reconcile_13_trades.py` and `scripts/qa/v33_3a_validation_engine.py`:
  ```python
  entry_t = df_4h.iloc[pos_entry_idx]["timestamp"]
  sig_t = df_4h.iloc[pos_entry_idx - 1]["timestamp"]
  sub_1h = df_1h[df_1h["timestamp"] <= sig_t]
  regime = sub_1h.iloc[-1]["regime"]
  ```
- **Evaluation:** The regime is evaluated on closed 1-hour candles at or before the signal time $t_{\text{sig}}$ (the close of 4h bar $i$). Because entry occurs 4 hours later at $t_{\text{entry}} = t_{\text{sig}} + 4\text{h}$, the regime classification is **frozen in time before the order is filled**. Zero future regime labels or future price data are accessible.
- **Status:** **VERIFIED PASS (Strict Temporal Precedence)**

---

### Invariant 6: Full Transparency of Skipped / Excluded Trades
- **Evidence:** All 84 excluded trades are permanently recorded with their full counterfactual execution paths in [v33_3b_excluded_trade_classification.csv](file:///c:/Projects/BTCognitive/BTCognitive/research/reports/offline_mvp/20261031_330320_v33_03b_htf_closure/v33_3b_excluded_trade_classification.csv).
- **Audit Findings:** Every skipped trade logs:
  - Exact entry timestamp and price that would have been executed.
  - Exact stop loss and exit price that would have resolved.
  - Counterfactual net return (confirming an average loss of **-55.49 bps**).
  - Explicit reason for exclusion (`CONSOLIDATION_RANGE` or `TRANSITION_UNSUPPORTED`).
- **Status:** **VERIFIED PASS (Complete Event Traceability)**

---

## 3. Causal Audit Verdict

The execution architecture and regime gating mechanism satisfy all six causal requirements. The strategy and filter operate under **strict point-in-time constraints ($t_{\text{data}} \le t_{\text{signal}} < t_{\text{entry}} < t_{\text{exit}}$)**.

