# V32.80B — Independent Red-Team Audit (Workstream 7)

**Milestone:** BTCognitive V32.80B — Funding Data Provenance Closure  
**Generated:** 2026-10-30T18:20:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Adversarial Scope

The Red-Team mandate for V32.80B is to independently challenge the data provenance findings of the funding investigation, specifically evaluating:
1. Whether the $+0.000100$ ceiling in 2022, 2025, and 2026 can be explained away as natural market dynamics.
2. The severity of the conflict between `funding.parquet` and `binance_funding_2022_2026.parquet`.
3. The validity of any research derived from this dataset given the upstream conflict.

---

## 2. Red-Team Challenge 1: The "Natural Market Regime" Defense is Disproven

**The Proposition:** Proponents of the strategy claimed that the lack of rate spikes in 2022 and 2025–2026 was simply a quiet market regime where perpetual basis stayed clamped.

### Red-Team Counter-Analysis:
1. In 2025 and 2026, Bitcoin price surged from $\$75,000$ to $\$125,000$ (as verified by mark prices in the file itself, reaching $\$124,946.20$ on Binance).
2. It is economically implausible that during an explosive $66\%$ bull run in 2025 where mark prices touched $\$125\text{k}$, perpetual funding rates on Binance never once exceeded the baseline $10\text{ bps}$ clamp ($0.01\%$) across $1,095$ consecutive 8-hour settlements.
3. In contrast, during the 2024 bull run, the exact same contract unclamped $213$ times up to $+0.000881$ ($88\text{ bps}$).
4. Crucially, `data/raw/funding.parquet` proves that during early 2026, live funding rates did in fact trade up to $+0.000821$ ($113$ times $\ge 0.000228$).
5. **Red-Team Verdict:** The claim that 2025–2026 was a natural clamp regime is economically unconvincing and contradicted by local empirical evidence in `funding.parquet`.

---

## 3. Red-Team Challenge 2: The Two-File Conflict Disqualifies Uncritical Reliance

| Property | `data/raw/binance_funding_2022_2026.parquet` | `data/raw/funding.parquet` |
|---|---|---|
| **2026 Overlapping Period** | Jan 1, 2026 – May 5, 2026 | Jan 1, 2026 – May 5, 2026 |
| **Max Rate in Period** | $+0.000100$ ($10\text{ bps}$) | **$+0.000821$ ($82\text{ bps}$)** |
| **Rows $\ge +0.000228$** | **0** | **113** |
| **Correlation ($r$)** | \multicolumn{2}{c|}{**$r = 0.0159$ (Zero Correlation)**} |

Two parquet files stored in the same `data/raw/` directory purporting to describe the exact same asset (Binance BTCUSDT perpetual funding) have **zero correlation** during the exact same months.
- One shows a completely suppressed rate bounded by $0.000100$.
- The other shows heavy contango and frequent spikes.

**Red-Team Verdict:** This internal contradiction cannot be resolved without external API network access. Under `OFFLINE_RESEARCH_ONLY`, neither file can be crowned authoritative. All research utilizing `binance_funding_2022_2026.parquet` must be quarantined under `SOURCE_LINEAGE_UNRESOLVED`.

---

## 4. Final Red-Team Assessment

1. The Lead Orchestrator has correctly avoided declaring the dataset authentic or claiming a natural market regime.
2. The classification `SOURCE_LINEAGE_UNRESOLVED` is the only intellectually honest and governed choice.
3. The negative strategy conclusion (`INSUFFICIENT_EVIDENCE`) is doubly reinforced: the strategy not only fails statistical robustness across bandwidths, but its underlying dataset contains unresolved source conflicts.

