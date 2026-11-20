# BTCognitive V31.2 — Data Blocker Resolution

**Decision:** `NO QUALIFIED CANDIDATE`

## 1. Three-agent findings

| Agent | Finding | Evidence | Recommendation |
|---|---|---|---|
| Bitstamp Forensics | The local Bitstamp CSV is a real 1-minute file with consistent 60-second timestamps and a valid SHA-256, but the dataset’s timestamp/PIT semantics are not proven. The file identity is credible; the contract is not. | `data/raw/btcusd_1-min_data.csv`; `research/entry_tp_sl/data_intake_manifest.json`; `research/entry_tp_sl/provenance.template.json` | `REJECT AS ACTIVE CANDIDATE` |
| Alternative Source Qualification | Coinbase 15m has a coherent venue/instrument/time contract for a limited 15-minute context study, but it is not an equivalent substitute for the 1-minute entry path. Binance hourly is not a valid single-source replacement because the repository mixes venue identities without a single manifest. | `engine/coinbase_15m_adapter.py`; `data/raw/coinbase_15m_manifest.json`; `data/ingest_real_historical.py`; `research/v12_strategy_tournament_engine.py` | `COINBASE 15M ONLY FOR FUTURE SEPARATE STUDY` |
| Contract and Integration Audit | The repo contains conflicting source assumptions across Bitstamp, Coinbase, and Binance. The intake manifest, provenance template, and V12 consumer disagree on dataset identity and availability semantics. | `data/ingest_real_historical.py`; `research/v12_strategy_tournament_engine.py`; `research/entry_tp_sl/data_intake_manifest.json`; `research/entry_tp_sl/provenance.template.json` | `NO SINGLE-SOURCE CONTRACT` |

## 2. Maximum three blockers

1. **Unresolved timestamp / availability contract**
   - The Bitstamp manifest claims a verified PIT contract, but the provenance template explicitly leaves `timestamp_role` and `available_time_rule` as `UNVERIFIED`.
   - Needed evidence: the exact published Bitstamp semantics for bar-open vs bar-close and the source’s decision-time availability rule; human approval by the research owner if the dataset is to be accepted.

2. **Conflicting dataset identity across the repo**
   - The project contains Bitstamp 1-minute CSV, Coinbase 15-minute data, and Binance hourly data, yet the active consumer code and manifests do not converge on one canonical source.
   - Needed evidence: one manifest declaring the exact source, symbol, venue, product type, and version for the active research path; human sign-off that no other source is being used as a hidden substitute.

3. **No valid single-source manifest for the next stage**
   - The repository still lacks one defensible, frozen source contract covering identity, rights, and time semantics across the chosen feed.
   - Needed evidence: a single accepted manifest with valid artifact hash, metadata, time semantics, rights record, and a reviewed `available_time` rule; human approval before replay or tuning begins.

## 3. Exact next action

Do not proceed to replay, strategy tuning, tournament runs, or collector work. The safest next action is:

- choose one source path only after a human-approved manifest is created;
- accept Bitstamp only if the timestamp and available-time semantics are explicitly resolved from primary evidence;
- keep Coinbase 15m scoped only to a separate exploratory study; and
- quarantine Binance and all other datasets from the active research path.

## 4. Files created or changed

- Created: `research/v31_2_blocker_resolution.md`
- Updated: `CHANGES.md` (short audit entry appended)

## 5. Confirmation

No strategy logic, replay logic, live behavior, collectors, or protected ledgers were modified. This is a research-only evidence decision, not a launch of any strategy or execution path.
