# V37.4-R2 — Clock and Feed Reliability Report

**Assessment date:** 2026-11-04  
**Disposition:** Feed freshness is **NOT QUALIFIED**.

## Scope and guardrails

This review created this report only. It inspected the existing R1 reports and saved evidence, and ran read-only Windows time diagnostics. **No Bitstamp WebSocket or market-data connection was opened**: the data-use and network-policy gates remain unapproved. No clock synchronization, timestamp adjustment, policy change, market-data persistence, or application/test/configuration change was performed.

## Windows clock diagnostics

The local clock was `2026-11-04T22:08:59.084+05:30` immediately before the status query. The read-only commands and observed results were:

1. **Command:** `w32tm /query /status`  
   **Result:** exit code 0; `Leap Indicator: 3 (not synchronized)`, `Stratum: 0 (unspecified)`, `Last Successful Sync Time: unspecified`, `Source: Local CMOS Clock`, `Root Delay: 0.0000000s`, `Root Dispersion: 0.0000000s`.  
   This host reports that it is not synchronized to a network time source.

2. **Command:** `w32tm /stripchart /computer:time.windows.com /samples:5 /dataonly`  
   **Start:** `2026-11-04T22:08:59.172+05:30`; target resolved to `40.81.94.65:123`.  
   **Offsets as printed:** `22:08:59, -226.0298906s`; `22:09:01, -225.9912263s`; `22:09:03, -225.9860010s`; `22:09:05, -225.9785529s`; `22:09:07, -225.9935138s`.  
   **Result:** five samples received; exit code 0.

3. **Command:** `w32tm /stripchart /computer:time.cloudflare.com /samples:5 /dataonly`  
   **Start:** `2026-11-04T22:09:07.571+05:30`; target resolved to `[2606:4700:f1::123]:123`.  
   **Offsets as printed:** at `22:09:07`, `error: 0x80072733`; `22:09:09, -225.9951292s`; `22:09:11, -226.0050194s`; `22:09:13, -226.0037751s`; `22:09:15, -225.9880186s`.  
   **Result:** four successful samples and one sample error; command exit code 0. The diagnostic sequence ended at `2026-11-04T22:09:15.951+05:30`.

The two independent time sources returned offsets with a consistent magnitude of about 226 seconds; the signed values above are preserved exactly as `w32tm` printed them. The sources agree closely with each other, but this does not make the local clock synchronized: the status query identifies the Local CMOS Clock and no successful sync time. These brief stripcharts are diagnostics, not a clock correction or a guarantee about clock accuracy at earlier observation times. Microsoft's [`w32tm` documentation](https://learn.microsoft.com/en-us/windows-server/networking/windows-time-service/windows-time-service-tools-and-settings) describes `/query /status` and `/stripchart` as status/offset diagnostics; no configuration or resynchronization command was used.

## Existing feed-timestamp evidence

No timestamp-bearing market messages were collected in this review. The following are claims or values already recorded in prior evidence; they were not re-measured:

| Existing evidence | Recorded result | What it establishes—and does not |
|---|---|---|
| `V37_4_R1_MANAGER_ACCEPTANCE_REPORT.md` and the follow-up in `V37_4_R1_QA_REPORT.md` | One previously captured trade was reported with event time `2026-11-04T16:11:57.653000Z`, local receipt time `2026-11-04T16:15:43.729603Z`, and a computed difference of `226.076603s`. It produced one in-memory candle; the API returned `STALE`, and analysis was withheld. | A previously measured **event-timestamp versus local-receipt-timestamp difference**. Because the host clock is presently unsynchronized and differs from both NTP references by about the same magnitude, this difference cannot be treated as a qualified measure of exchange or network delay. |
| Session checkpoint `checkpoints\014-implementing-bitstamp-feed-pat.md` | Records a prior raw-message inspection with `timestamp=1793806603` and `microtimestamp=1793806603316000`, corresponding to `2026-11-04T15:36:43.000Z` and `2026-11-04T15:36:43.316Z`; it records receipt-time differences of `226.501574s` and `226.185574s`. | The checkpoint's parser-unit comparison supports that those two timestamp fields were not confused by seconds-versus-microseconds conversion for that inspected message. The raw message itself is not present among the persisted evidence inspected here, so this is not an independent raw-message reparse. |
| `files\v37_4_bitstamp_soak_summary.json` in the session evidence directory | Summary records a requested 1,800-second run, actual duration `1800.1986s`, `3693` trade events, last event `2026-11-04T15:50:58.957+00:00`, last receipt `2026-11-04T15:54:45.036723+00:00`, and `max_receive_lag_seconds=227.028209`. The last event/receipt pair differs by `226.079723s`. | An aggregate summary, not a saved sequence of consecutive raw messages. The R1 manager report says a 30-minute soak was not completed, which conflicts with this JSON summary's duration and finished time. This report does not resolve that provenance conflict. |
| `files\v37_3_data_qualification\bitstamp_ohlc_raw_response.json` and `files\v37_3_data_qualification\bitstamp_ohlc_structured_qa.json` | Saved HTTP OHLC response contains ten candles; the structured QA records a last candle close lag of `240.0s` and marks the latest expected candle missing. | This is candle-response evidence, not a sequence of trade messages or event-to-receipt measurements. Its reported lag is also dependent on the local retrieval-time clock. |

The session `files\` and `checkpoints\` paths above refer to `C:\Users\Ashish\.copilot\session-state\51eedde1-236e-4970-84a5-a1b2daff43ad\`. The two R1 reports are at the repository root.

**Latency distribution:** `median`, `p95`, and `max` are all **NOT ESTABLISHED** from raw consecutive messages. The soak JSON contains a scalar named `max_receive_lag_seconds`, but the underlying consecutive messages and their individual receipt timestamps are not persisted in the inspected evidence. That scalar is therefore reported as an existing summary value, not independently verified as the maximum of a raw latency series. No distribution or substitute estimate is inferred.

## Separate causes and limits of inference

- **NTP / local clock offset:** The current host is explicitly unsynchronized. Two time-server diagnostics returned offsets around 226 seconds in magnitude. This is a material confounder for any prior comparison of exchange event timestamps to locally generated receipt timestamps.
- **Event-versus-receive lag:** Prior R1 reports record differences around 226 seconds. They are timestamp differences as recorded, not a clock-corrected feed-latency measurement.
- **Possible exchange-side delay:** Cannot be separated or established. The evidence does not show when the exchange created, queued, or published each message relative to its event timestamp.
- **Path / network delay:** Cannot be isolated. No synchronized receiver clock, packet capture, or separate exchange-side timing is available in the inspected evidence; the recorded interval can include exchange processing, publication/buffering, network transit, and local receipt-clock error.
- **Parser error:** The prior R1 report's seconds/microseconds agreement argues against a unit-conversion error for that reported message. It does not establish parser correctness for an unavailable raw sequence or account for an unsynchronized receipt clock.
- **What cannot be inferred:** The available evidence cannot determine how much of the apparent lag is due to the local clock, exchange-side processing, message publication, network path, or other buffering; it cannot establish a latency distribution, qualify current feed freshness, or establish that a previous `STALE` label represented true exchange-to-receiver staleness.

## Decision

**Feed freshness: NOT QUALIFIED.** Windows reports an unsynchronized clock, and its measured offset magnitude is comparable to the prior reported event-to-receipt differences. The existing message/summary evidence is insufficient to correct or decompose those differences, and raw consecutive messages needed for latency statistics are unavailable. The previously recorded `STALE` statuses remain historical API outcomes, not a validated freshness conclusion. No provider connection was made; data-use and network-policy gates remain unapproved.

1. **Research Experiment:** `INCONCLUSIVE`
2. **Prospective Evidence:** `NOT_STARTED`
3. **Model Authorization:** `OFFLINE_RESEARCH_ONLY`
4. **Live Trading:** `DISABLED`
