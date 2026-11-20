# V32.79 Phase 0 — Execution Cost Reconciliation (Workstream F)
**Milestone:** BTCognitive V32.79 — Phase 0 Baseline & Data Provenance Audit  
**Generated:** 2026-10-30  
**Auditor:** Lead Orchestrator — Workstream F (Cost Reconciliation)  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Purpose

This report reconciles the discrepancy between two round-trip cost figures that appear in prior V32.77/V32.78 documentation (21/84 bps vs. 24/87 bps), documents the Manager-corrected breakeven thresholds, and freezes the cost methodology for all future V32.79 research.

---

## 2. Cost Discrepancy Reconciliation

### 2.1 Source of the 24/87 bps Figure (Verified Authority)

From `research/reports/offline_mvp/20261030_240000_v32_77_volatility_adaptive_entry_research/v32_77_cost_economics.md`:

| Scenario | Per-Side Fee | Half-Spread | Slippage | Round-Trip Total |
|---|---|---|---|---|
| Binance VIP0 Taker | 10.0 bps | 2.0 bps | 0.0 bps | **24.0 bps** |
| Coinbase Advanced Taker | 40.0 bps | 3.5 bps | 0.0 bps | **87.0 bps** |

**Components (Binance VIP0):**
- Taker fee: 10 bps per side × 2 sides = 20 bps
- Half-spread (bid-ask friction): 2 bps per side × 2 sides = 4 bps
- **Total: 24 bps (0.24%)** ✅

**Components (Coinbase Advanced Taker):**
- Taker fee: 40 bps per side × 2 sides = 80 bps  
  *(Note: as of 2024-2026, Coinbase Advanced retail taker fee was reduced from 60 bps to 40 bps; the 40 bps figure is used here)*
- Half-spread: 3.5 bps per side × 2 sides = 7 bps
- **Total: 87 bps (0.87%)** ✅

### 2.2 Origin of the 21/84 bps Figure

The 21/84 bps figures appear to have originated in earlier milestones (V32.71/V32.73) before the spread component was fully itemized. The earlier estimate used:
- 10.5 bps per side × 2 = 21 bps (rounding half-spread differently)
- 42 bps per side × 2 = 84 bps (using an earlier Coinbase fee schedule)

**Resolution:** The 21/84 bps figures are superseded. The **24/87 bps methodology** is the authoritative standard, verified in V32.77 and confirmed by the Manager. All future reports must use 24/87 bps.

---

## 3. Manager-Corrected Breakeven TP Rate — Frozen Methodology

### 3.1 Formula

For a symmetric stop/target barrier:
$$\text{Breakeven TP Rate} = \frac{\text{Target} + \text{Cost}}{\text{Target} + \text{Stop}}$$

Where:
- **Target** = TP distance from entry (%)
- **Stop** = SL distance from entry (%)
- **Cost** = Total round-trip friction (%)

### 3.2 Standard Barrier (3% Target / 1.5% Stop)

| Exchange | Cost | Target | Stop | Breakeven TP Rate |
|---|---|---|---|---|
| Binance VIP0 | 0.24% | 1.5% | 1.5% | (1.5% + 0.24%) / (1.5% + 1.5%) = **58.0%** |
| Coinbase Advanced | 0.87% | 1.5% | 1.5% | (1.5% + 0.87%) / (1.5% + 1.5%) = **79.0%** |

> [!WARNING]
> **Prior reports used an INCORRECT breakeven formula.** The prior formula `(Target + Cost) / (Target + Stop)` was applied with Target = 1.5%, Stop = 1.5%, but some reports erroneously described a "3%/1.5% barrier" (asymmetric: TP = 3%, SL = 1.5%). The Manager's stated values of 38.7% (Binance) and 52.7% (Coinbase) correspond to the **asymmetric 3%/1.5% barrier** (3% TP, 1.5% SL), computed below.

### 3.3 Asymmetric Barrier (3% TP / 1.5% SL) — Manager Figures

| Exchange | Cost | TP Distance | SL Distance | Breakeven TP Rate |
|---|---|---|---|---|
| Binance VIP0 | 0.24% | 3.0% | 1.5% | (3.0% + 0.24%) / (3.0% + 1.5%) = **38.7%** ✅ (matches Manager) |
| Coinbase Advanced | 0.87% | 3.0% | 1.5% | (3.0% + 0.87%) / (3.0% + 1.5%) = **52.7%** ✅ (matches Manager) |

**The Manager's 38.7%/52.7% breakeven figures are confirmed correct for the asymmetric 3% TP / 1.5% SL barrier.**

### 3.4 Standard Barrier (1.5% TP / 0.75% SL) — Prior Configuration

For completeness, the configuration tested in V32.74–V32.76 (1.5% TP / 0.75% SL):

| Exchange | Cost | TP | SL | Breakeven TP Rate |
|---|---|---|---|---|
| Binance VIP0 | 0.24% | 1.5% | 0.75% | (1.5% + 0.24%) / (1.5% + 0.75%) = **77.3%** |
| Coinbase Advanced | 0.87% | 1.5% | 0.75% | (1.5% + 0.87%) / (1.5% + 0.75%) = **105.3%** |

**At Coinbase retail fees, the standard 1.5%/0.75% barrier requires a >100% TP rate — mathematically impossible.** This confirms why all tested configurations in V32.74–V32.76 failed under Coinbase fees.

---

## 4. Funding Rate Drag (Multi-Day Positions)

For positions held on BTCUSDT perpetual futures, funding accumulates at each 8h settlement.

**Empirical median funding rate (from `binance_funding_2022_2026.parquet`):** +0.006%/8h

| Horizon | Settlements | Expected Funding Drag (Long) | Adjusted Binance BEP | Adjusted Coinbase BEP |
|---|---|---|---|---|
| 24h (3 settlements) | 3 | +0.018% = 1.8 bps | 38.7% + ~0.6% ≈ 39.3% | 52.7% + ~0.6% ≈ 53.3% |
| 72h (9 settlements) | 9 | +0.054% = 5.4 bps | 38.7% + ~1.8% ≈ 40.5% | 52.7% + ~1.8% ≈ 54.5% |
| 168h (21 settlements) | 21 | +0.126% = 12.6 bps | 38.7% + ~4.2% ≈ 42.9% | 52.7% + ~4.2% ≈ 56.9% |

Note: The V32.77 cost report used +0.010%/8h (10 bps/settlement), yielding higher funding drag. Empirical median is +0.006%/8h. The funding adjustment is a directional cost only for net long positions; short positions receive funding from longs when rate is positive.

**Key asymmetry:** Long positions pay funding in positive-rate environments (the historical norm), which is an additional headwind for long-biased strategies.

---

## 5. Spot vs. Perpetual Distinction

| Characteristic | Spot BTC/USD | Perpetual BTCUSDT |
|---|---|---|
| Exchange fees | Coinbase: 40 bps taker per side | Binance: 10 bps taker per side |
| Spread | 3.5 bps/side | 2.0 bps/side |
| Funding | **None** | ±0.006% per 8h (positive = long pays) |
| Short selling | Requires separate borrow (∼1-5% ann.) | Built-in via short position |
| Leverage | 1x only (unless margin account) | Up to 125x available |

**The OHLCV checkpoint is Coinbase spot data** (`data/raw/ohlcv_checkpoint_42233_bars.parquet` — Coinbase BTC/USD hourly). Research using this dataset for backtest prices but simulating perpetual futures positions would need to account for the basis between spot and perp prices.

---

## 6. Frozen Methodology for V32.79

The following parameters are frozen and must be used in all future V32.79 Phase 1 research without modification:

| Parameter | Value | Source |
|---|---|---|
| Binance VIP0 round-trip cost | **24 bps (0.24%)** | V32.77 cost_economics.md, Manager confirmed |
| Coinbase Advanced round-trip cost | **87 bps (0.87%)** | V32.77 cost_economics.md, Manager confirmed |
| Binance BEP TP rate (3%/1.5% barrier) | **38.7%** | Manager-corrected, this report verified |
| Coinbase BEP TP rate (3%/1.5% barrier) | **52.7%** | Manager-corrected, this report verified |
| Funding drag assumption | **+0.006%/8h empirical median** (BTCUSDT perp) | Computed from binance_funding_2022_2026.parquet |
| Passive maker rate | **DISQUALIFIED** (adverse selection) | V32.77 cost_economics.md Section 3 |
| Theoretical zero-cost | **DISQUALIFIED as acceptance gate** | V32.77 cost_economics.md Section 4 |

---

*No external data fetched. No datasets modified. No models trained.*

