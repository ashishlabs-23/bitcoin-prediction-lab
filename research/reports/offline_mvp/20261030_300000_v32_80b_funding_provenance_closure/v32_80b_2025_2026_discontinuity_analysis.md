# V32.80B — 2025–2026 Discontinuity & Provenance Analysis (Workstream 5)

**Milestone:** BTCognitive V32.80B — Funding Data Provenance Closure  
**Generated:** 2026-10-30T18:10:00Z  
**Classification:** OFFLINE_RESEARCH_ONLY  

---

## 1. Executive Summary

This report analyzes the structural discontinuity observed between the 2023–2024 period (frequent funding spikes $> +0.000100$) and the 2025–2026 period (all positive rates bounded by $+0.000100$).

In accordance with the Manager's ruling, we evaluate seven formal hypotheses to explain this behavior:
1. Genuine observed market conditions
2. Missing observations
3. A change in the source / contract
4. Field substitution
5. Local data clipping / rounding
6. A transformation error
7. Insufficient provenance

---

## 2. Hypothesis-by-Hypothesis Forensic Audit

### Hypothesis 1: Field Substitution (REJECTED)
- *Proposition:* The pipeline captured the interest-rate component $I$ instead of the total funding rate $F$.
- *Evidence:* In 2025–2026, there are $874$ unique values in 2025 and $670$ in 2026. Values fluctuate continuously with 8 decimal places of floating-point precision, including negative rates (e.g. $-0.000152$). If field substitution had occurred, all observations would equal $0.000100$.
- *Ruling:* **REJECTED**.

### Hypothesis 2: Local Data Clipping or Rounding (REJECTED)
- *Proposition:* Local code in `download_binance_funding_history.py` clipped rates to $0.000100$.
- *Evidence:* Inspection of `download_binance_funding_history.py` lines 80–90 proves zero clipping or clamping logic. Rates are raw `float(row["fundingRate"])`. In 2024, the exact same script and lines processed values up to $+0.000881$.
- *Ruling:* **REJECTED**.

### Hypothesis 3: Missing Observations (REJECTED)
- *Proposition:* Spikes occurred but were dropped by missing settlements.
- *Evidence:* As proven in `v32_80b_settlement_interval_audit.md`, exactly $5,113$ of $5,115$ expected 8-hour settlements are present ($99.96\%$ complete). There are no missing days or dropped windows.
- *Ruling:* **REJECTED**.

### Hypothesis 4: Local Transformation Error (REJECTED)
- *Proposition:* An index alignment or math transform distorted the rates.
- *Evidence:* The parquet stores the direct parsed float.
- *Ruling:* **REJECTED**.

### Hypothesis 5: Genuine Observed Market Conditions (POSSIBLE BUT DISPUTED)
- *Proposition:* The 2025–2026 market structure was characterized by low perpetual basis, clamping rates to $0.000100$.
- *Counter-Evidence:* Contemporaneous local file `data/raw/funding.parquet` (covering Jan–May 2026) recorded $113$ settlements $\ge +0.000228$, with rates up to $+0.000821$. The correlation between the two files is $r = 0.0159$.
- *Ruling:* **UNVERIFIABLE OFFLINE**.

### Hypothesis 6: Discrepant Upstream Source / Contract Lineage (CONFIRMED CONFLICT)
- *Proposition:* `funding.parquet` and `binance_funding_2022_2026.parquet` sampled either different endpoints, different symbols, or different API response formats.
- *Evidence:* The two files cannot both be faithful, unmodified representations of the exact same exchange contract at the exact same seconds without an upstream discrepancy.
- *Ruling:* **SOURCE DISCREPANCY CONFIRMED**.

### Hypothesis 7: Insufficient Provenance (UPHELD)
- Because external network calls are strictly prohibited under `OFFLINE_RESEARCH_ONLY`, we cannot query live Binance endpoints or verify third-party archives to establish whether `binance_funding_2022_2026.parquet` or `funding.parquet` reflects authentic exchange settlement.
- *Ruling:* **UPHELD — SOURCE_LINEAGE_UNRESOLVED**.

---

## 3. Final Analytical Determination

The Manager's skepticism is completely vindicated:
1. The 2025–2026 dormancy was **not** a simple "natural market regime."
2. The presence of $113$ rate spikes in `funding.parquet` during the exact same 2026 months where `binance_funding_2022_2026.parquet` has zero spikes proves an unresolved data source conflict.
3. Therefore, the 2022–2026 funding dataset cannot be classified as `FUNDING_PROVENANCE_VERIFIED`.

**Formal Classification for V32.80B:**  
`SOURCE_LINEAGE_UNRESOLVED` (retaining `INSUFFICIENT_EVIDENCE` for all strategy claims).

