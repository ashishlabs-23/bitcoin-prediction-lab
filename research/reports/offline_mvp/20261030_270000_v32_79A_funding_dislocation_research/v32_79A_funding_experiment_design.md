# V32.79A — Funding Dislocation Experiment Design (Pre-Registration)
**Milestone:** BTCognitive V32.79 Phase 1A — Funding Dislocation Research  
**Authorization:** Manager — APPROVED, EXPLORATORY ONLY  
**Generated:** 2026-10-30T16:55 UTC  
**Classification:** OFFLINE_RESEARCH_ONLY  

> [!IMPORTANT]
> This document is the pre-registration record for the experiment. It is written before code execution. All design decisions are locked here; post-hoc changes to the experimental protocol are prohibited and must be documented as amendments.

---

## 1. Research Question

Does a BTCUSDT perpetual funding rate that exceeds ±25% annualized — a proxy for extreme market positioning — predict an economically meaningful change in BTCUSD price outcomes over the subsequent 24 hours, after accounting for realistic trading costs?

This is an exploratory investigation only. A positive result cannot establish a validated trading edge and cannot alter the Analysis ABSTAIN gate.

---

## 2. Instrument Distinction

| Item | Source | Role |
|---|---|---|
| **BTCUSDT perpetual funding rate** | `data/raw/binance_funding_2022_2026.parquet` | External market-positioning proxy. NOT the actual funding cost of the BTCUSD instrument. |
| **BTCUSD hourly price** | `data/raw/ohlcv_checkpoint_42233_bars.parquet` | Target outcome instrument. |

The funding dataset captures positioning imbalances in the Binance USDⓈ-M perpetual futures market. It is used as a market-state indicator. It is not directly applicable as a trading cost for spot BTCUSD positions.

---

## 3. Data Scope

| Parameter | Value |
|---|---|
| OHLCV checkpoint | `ohlcv_checkpoint_42233_bars.parquet` — 42,233 hourly bars, 2022-01-01 → 2026-10-26 |
| Funding dataset | `binance_funding_2022_2026.parquet` — 5,113 rows, 2022-01-01 → 2026-09-01 |
| **Genuine overlap** | **2022-01-01 → 2026-09-01** |
| 51-day tail gap | Bars 2026-09-01 → 2026-10-26 excluded — no corresponding funding data |
| No imputation | No forward filling, no interpolation, no fabricated funding records |

---

## 4. Threshold Definition

**Manager-specified threshold:** ±25% annualized funding rate.

**Conversion to per-8h funding rate:**

$$\text{threshold}_{\text{8h}} = \frac{\pm 25\%}{3 \times 365} = \pm \frac{0.25}{1095} \approx \pm 0.0002283$$

In the dataset's native representation (decimal fraction per 8h):
- **Long signal threshold:** `funding_rate ≤ −0.0002283` (shorts crowded; longs benefit → contrarian LONG entry)
- **Short signal threshold:** `funding_rate ≥ +0.0002283` (longs crowded; shorts benefit → contrarian SHORT entry)

**Annualized interpretation:**
- +25% ann means: longs collectively pay 25%/year in funding to shorts → extreme crowding on long side → mean-reversion hypothesis: price may fall.
- −25% ann means: shorts pay 25%/year → extreme short crowding → mean-reversion hypothesis: price may rise.

---

## 5. Causal Availability Rule

Funding is settled at 00:00, 08:00, 16:00 UTC. The confirmed rate becomes available **at settlement time T**.

**Causal rule (conservative):** An extreme funding observation at settlement time $T$ may only inform a trade entry at the **next OHLCV bar open after $T$**. Specifically:
- Funding settled at 00:00 UTC → earliest causal entry at the hourly bar opening at **01:00 UTC** (the bar whose `timestamp == 01:00 UTC`).
- Funding settled at 08:00 UTC → entry at **09:00 UTC** bar.
- Funding settled at 16:00 UTC → entry at **17:00 UTC** bar.

This lag is deliberate and conservative. If exact publication timestamps were available they might allow same-hour entry; without verified publication timestamps, a 1-hour lag is applied.

---

## 6. Episode Grouping

**Problem:** Consecutive 8-hour settlements in the same extreme-funding event would create overlapping 24-hour evaluation windows. Counting each as an independent trade inflates the sample size and violates independence.

**Episode definition:**
- A new qualifying funding observation starts a fresh **episode**.
- Any subsequent qualifying observation within **24 hours** of the episode start belongs to the same episode and is NOT counted as a new independent trade.
- The episode start bar determines the entry price for the entire episode.
- After the 24-hour evaluation window closes (or TP/SL is hit), the next qualifying observation may start a new episode.

This guarantees non-overlapping evaluation windows and prevents a prolonged funding dislocation event from inflating the event count.

---

## 7. Barrier Definition

| Parameter | Value |
|---|---|
| TP distance | +3.0% from entry (LONG) / −3.0% (SHORT) |
| SL distance | −1.5% from entry (LONG) / +1.5% (SHORT) |
| Horizon | 24 hours = 24 hourly bars |
| Resolution rule | First-passage: evaluate each bar sequentially |
| Same-bar ambiguity | If bar touches both TP and SL: conservatively record SL_FIRST |

**Outcome categories:**
- `TP_FIRST` — TP level reached before SL within 24 bars
- `SL_FIRST` — SL level reached before TP (or same bar: SL_FIRST by conservative rule)
- `EXPIRED` — neither level reached within 24 bars; outcome = close-minus-entry after 24 bars

---

## 8. Primary Endpoint

**Net Expected Value (net EV) per trade**, defined as:

$$\text{net EV} = P(\text{TP\_FIRST}) \times (\text{TP pct} - \text{cost}) + P(\text{SL\_FIRST}) \times (-\text{SL pct} - \text{cost}) + P(\text{EXPIRED}) \times (\text{mean expiry PnL} - \text{cost})$$

Where cost = round-trip trading cost (24 bps Binance, 87 bps Coinbase).

**Secondary endpoints:**
- Gross EV (before costs)
- TP rate, SL rate, EXPIRED rate
- MFE distribution (maximum favorable excursion within 24h)
- MAE distribution (maximum adverse excursion within 24h)
- Chronological stability (first/second half comparison)

**Unconditional baseline:** Same metrics computed on all bars in the overlap period (same 24h horizon, same barrier), regardless of funding level. This is the comparison benchmark.

---

## 9. Evaluation Structure

| Arm | Description |
|---|---|
| LONG arm | Entry when funding ≤ −25% ann (shorts crowded → contrarian long) |
| SHORT arm | Entry when funding ≥ +25% ann (longs crowded → contrarian short) |
| Unconditional baseline LONG | All bars, long side |
| Unconditional baseline SHORT | All bars, short side |

Long and short are evaluated separately throughout. Combined statistics are reported for reference only.

---

## 10. Statistical Requirements

| Requirement | Specification |
|---|---|
| Minimum qualifying events | ≥ 100 distinct episodes per arm (if fewer, report INSUFFICIENT_EVIDENCE) |
| Effective sample size | Reported separately from raw event count |
| Multiple-testing | K = 2 pre-specified arms (long, short); Bonferroni threshold = 0.025 |
| Standard errors | Block bootstrap (block length = 24h) or Newey-West HAC (bandwidth = 31 lags) |
| DM-HLN correction | Applied when comparing conditioned vs. unconditional baseline |
| Confidence intervals | 95% bootstrap CI on net EV |
| Chronological stability | Split sample at midpoint; test first vs. second half separately |

---

## 11. Stop Conditions

| Condition | Action |
|---|---|
| Fewer than 100 qualifying episodes per arm | Report INSUFFICIENT_EVIDENCE for that arm |
| Causal availability cannot be established | Stop and report BLOCKED_BY_PROVENANCE |
| Protected dataset hash mismatch | Stop and report data integrity failure |
| External network access required | Stop — OFFLINE_RESEARCH_ONLY |

---

## 12. Governance Invariants (Unchanged)

- `OFFLINE_RESEARCH_ONLY` — zero external API calls
- Analysis `ABSTAIN` gate — untouched
- `NO_GO_NO_VALIDATED_EDGE` — unchanged
- Prospective evidence — 7/100 blocks, runner NOT restarted
- Protected OHLCV hashes — verified before analysis begins
- Git: `main` branch only, no commits/pushes/branches
- No model training, no strategy promotion, no live trading

---

*Pre-registration locked. Execution follows.*

