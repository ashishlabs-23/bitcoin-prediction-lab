# BTCognitive V35.4 Forecast Accuracy Report

**Audit date:** 2026-11-03  
**Primary question:** What is the out-of-sample accuracy of the registered Standard HAR baseline?  
**Answer:** **NOT ESTABLISHED.**

## 1. Forecast identity

The authoritative registry entry [`STANDARD_HAR_BASELINE`](./models/authoritative_model_registry.py#L78) defines:

| Attribute | Registered contract |
|---|---|
| Model | Standard HAR baseline; registry describes an offline Corsi-style OLS volatility baseline |
| Target | Annualized 7-day realized variance, `rv7d_var_ann` |
| Horizon | 168 hours / 7 calendar days |
| Features | `rv_1d`, `rv_7d`, `rv_30d` |
| Authorization | `OFFLINE_RESEARCH_ONLY` |
| Artifact reference | `experiments/results/freeze/standard_har_v1.joblib` |
| Artifact hash | Placeholder string, not a verifiable SHA-256 |

The referenced joblib artifact is absent. Consequently, the exact fitted parameters, preprocessing/transforms, training window, fit provenance, and forecast implementation cannot be verified. The current `/api/tournament/analyse` request does not execute this registered artifact; it performs strategy/regime analysis and emits a separate risk payload.

### Target definition and boundary

For hourly close \(C_t\), define \(r_t=\log(C_t/C_{t-1})\). The repository's target contract is a future realized-variance proxy aggregated over the next 168 closed hourly returns:

\[
rv7d\_var\_ann(t) = \frac{8760}{168}\sum_{j=1}^{168} r_{t+j}^{2}.
\]

The three registered features describe trailing 24-, 168-, and 720-hour realized-variance windows. This expresses the expected target/feature boundary; because the registered model artifact is absent, the precise frozen preprocessing and fitted-model computation are **not verified**. It is not a forecast of price direction. The separate `rv24h_var_ann` target uses the next 24 closed hourly returns and must not be conflated with `rv7d_var_ann`.

## 2. Data and sample

Read-only inspection verified `data/raw/ohlcv.parquet`:

- 42,326 hourly rows.
- First timestamp: `2022-01-01 00:00 UTC`.
- Last timestamp: `2026-10-30 13:00 UTC`.
- No duplicate/out-of-order timestamps, hourly gaps, non-finite OHLCV values, or invalid OHLC geometry were found.
- SHA-256: `ba06fb533c0b53387136b001c142efc90b5e2ccfb37937dc509879a76c2a4057`, matching the protected-file hash asserted in [`test_v33_8_failure_injection.py`](./tests/test_v33_8_failure_injection.py#L24).

This establishes a candidate historical dataset's basic integrity, not the registered Standard HAR's sample, training/holdout split, data-vintage rules, or evaluation origins. The audit did not fit a replacement model, overwrite data, or produce forecasts.

## 3. Measured performance

| Model/comparison | QLIKE | MAE | RMSE | Relative improvement | DM/HLN | Holm-adjusted inference | Confidence interval | Status |
|---|---:|---:|---:|---:|---|---|---|---|
| Naive 7-day volatility persistence | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | No aligned OOS evaluation |
| Registered Standard HAR | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | Baseline | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | Registered artifact absent |
| QLIKE-HAR challenger | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | Not evaluated on identical verified origins |
| HAR-RS-DOW challenger | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | Not evaluated against exact registered artifact |
| Regime-aware benchmark | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | NOT ESTABLISHED | No pre-specified matched evaluation |

The table intentionally contains no substituted values. Price-direction accuracy, directional hit rate, trading profitability, and excursion coverage are not volatility-model accuracy measures and are not reported here.

## 4. Prior reported values: not accepted as registered-model evidence

The V35.2 research material reported 7-day QLIKE values of 0.02571 for Standard Log-HAR, 0.02761 for HAR-RS-DOW, and 0.05185 for persistence. These values are retained as historical claims only; they are not reproducibly bound to the missing registered Standard-HAR artifact, matching data/forecast origins, training window, or a governed OOS evaluation record.

Other saved historical evaluations inspected during the audit used different raw-linear implementations, problematic target alignment or a mismatched persistence horizon, no 168-hour target purge, and very few non-overlapping origins. A separate HAR-RS-DOW freeze audit reported training labels extending into its holdout; that is evidence about that challenger freeze, not proof about the missing Standard-HAR artifact. None of these materials establish current registered-model accuracy.

## 5. Prospective evidence

The append-only ledger was read without modification:

- 21 records total.
- `rv24h_var_ann`: 11 records, resolved.
- `rv7d_var_ann`: 10 records, 5 resolved and 5 pending.
- Nine adjacent issue intervals among the 10 seven-day records overlap. Under a simple chronological non-overlap selection, at most one of those 10 intervals is independent of the adjacent seven-day target windows.

These are not 10 independent blocks and do not meet the approved minimum of 100 non-overlapping clean blocks. Even a count of 100 would not by itself establish validity; precision, dependence, outcome resolution, and effective sample size must be assessed under the frozen protocol. The existing prospective protocol and records were not changed.

## 6. Evaluation protocol required before a future result can be established

1. Recover and verify the exact registered artifact, source revision, SHA-256, feature transform, training cutoff, and registry provenance. If it cannot be recovered, any fit is explicitly labeled a **retrospective reconstruction**, not the registered Standard HAR.
2. Freeze the target definition, data vintage, forecast origin schedule, feature availability, exclusions, split dates, and metric/test protocol before scoring. Enforce feature time \(\le\) issue time and target maturity strictly after issue time.
3. Use identical chronological origins and targets for persistence, Standard HAR, QLIKE-HAR, HAR-RS-DOW, and one pre-specified regime-aware benchmark. Purge overlapping 168-hour outcomes or use a pre-registered dependence-aware inference design; do not tune on the test period.
4. Report QLIKE as the primary variance forecast loss; report MAE/RMSE only on the same correctly aligned variance target and state units/scale. Compute baseline-relative improvement from paired losses.
5. For paired comparisons, use Diebold-Mariano with the Harvey-Leybourne-Newbold finite-sample correction and \(t_{T-1}\) reference, with dependence treatment appropriate to the origin design; apply Holm-Bonferroni across the predeclared family of comparisons.
6. Provide confidence intervals, sample dates/counts, failures/exclusions, and regime-stratified results. Any interval method must reflect serial dependence and the number of effectively independent blocks.
7. Keep all challengers unpromoted unless existing governance criteria are independently satisfied. Do not equate volatility forecast loss with directional return prediction.

## 7. Research references checked

- Corsi, F. (2009), “A Simple Approximate Long-Memory Model of Realized Volatility,” *Journal of Financial Econometrics*, 7(2), 174-196. [DOI: 10.1093/jjfinec/nbp001](https://doi.org/10.1093/jjfinec/nbp001).
- Diebold, F. X. and Mariano, R. S. (1995), “Comparing Predictive Accuracy,” *Journal of Business & Economic Statistics*, 13(3), 253-263. [DOI: 10.1080/07350015.1995.10524599](https://doi.org/10.1080/07350015.1995.10524599).
- Harvey, D., Leybourne, S. and Newbold, P. (1997), “Testing the Equality of Prediction Mean Squared Errors,” *International Journal of Forecasting*, 13(2), 281-291. [DOI: 10.1016/S0169-2070(96)00719-4](https://doi.org/10.1016/S0169-2070(96)00719-4).
- Patton, A. J. (2011), “Volatility Forecast Comparison Using Imperfect Volatility Proxies,” *Journal of Econometrics*, 160(1), 246-256. [DOI: 10.1016/j.jeconom.2010.03.034](https://doi.org/10.1016/j.jeconom.2010.03.034).

These references inform the proposed method; they do not supply BTCognitive-specific forecast results.

## Conclusion

**Registered Standard HAR OOS accuracy: NOT ESTABLISHED.** The available historical dataset is structurally clean, but the model artifact and matched evaluation provenance are absent. Model authorization remains `OFFLINE_RESEARCH_ONLY`; live trading remains `DISABLED`.
