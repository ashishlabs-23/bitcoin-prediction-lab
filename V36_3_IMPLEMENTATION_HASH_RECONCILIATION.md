# BTCognitive V36.3 — Implementation Hash Reconciliation

## Result

All five entries in `6B_implementation_manifest.json::source_file_hashes` resolve to the declared source content. The two apparent current-file mismatches are caused by Windows CRLF checkout bytes versus the manifest/Git LF bytes, not a later source-code change. Their original bytes are reproducible from local Git objects.

Separate metadata issues remain: the manifest’s recorded `git_commit` does not contain this workstream, and the manifest self-digest has no documented verification convention.

## Source-file digest comparison

| File / manifest entry | Declared SHA-256 | Current raw file SHA-256 | LF-normalized SHA-256 | Result / Git evidence |
|---|---|---|---|---|
| `research/entry_tp_sl/barrier_contract.py` | `290311994de7f14c7216c1b92053cbd085f0fd1d4a7749a24520c91d4d4e7fcc` | Same as declared | Same | Match; identical content at `fedfd1697bd78302e45da4a0e4980aba72c52e46`, `6b5f225e4f3670c8ba63063137b64ed7ce0270c1`, and current `HEAD`. |
| `research/entry_tp_sl/feasibility_audit.md` | `69720d224a762f9e0b3d7e2e69152711066261eb152d667fb3b5b9f50b551eb5` | Same as declared | Same | Match; same three local Git snapshots. |
| `research/entry_tp_sl/reference_resolver.py` | `2cc311a82a72d46c6206c57b4e7e5aa3ebe4634123341162934f87df0423b690` | `a98818e3723648b7e2b7d75df30dab6e36e98e0134359915bf72607d4324ca6d` | Same as declared | **Explained:** working file has 278 CRLF line endings; `core.autocrlf=true`. Exact declared LF bytes are recoverable from `fedfd...`, `6b5f...`, and `HEAD`. No Git worktree diff for this file. |
| `research/entry_tp_sl/resolver_reachability_after_6B.md` | `fac95343397fe21bdb8abbe1afb974865c695264c328c43f23e92db8c255fcfc` | Same as declared | Same | Match; same three local Git snapshots. |
| `research/entry_tp_sl/triple_barrier.py` | `758b07f935a317cc435dc96f5dc0d53c992612f014b7579e2d2b05fc105e84de` | `300dbd0a969ab5027a5fb70db854a74acb90e83d0f154774b07747f6a6293e03` | Same as declared | **Explained:** working file has 390 CRLF line endings; `core.autocrlf=true`. Exact declared LF bytes are recoverable from `fedfd...`, `6b5f...`, and `HEAD`. No Git worktree diff for this file. |

**Conclusion for the requested per-file classification:** 2 apparent raw-hash mismatches are `EXPLAINED` line-ending normalization; 0 source-hash mismatches are unexplained or unrecoverable. The exact historical source content is recoverable without restoring or modifying any file. There is no evidence of a later semantic resolver change in these two files between the declared source bytes and current Git `HEAD`.

## Provenance fields adjacent to source hashes

| Manifest field | Reconciliation |
|---|---|
| `dataset_sha256` | `1bf91f2789846af29d60a9c15e780b565b63a85c286e83080ac28bf4bf7d1287`; matches the current CSV and `data_intake_manifest.json`. This verifies local byte identity only. |
| `contract_manifest_sha256` | `b6b94d69e576be0357ce9249f24ca05fb44430e6e9050a940054833204e0013f`; equals `contract_freeze_manifest.json::manifest_sha256`. All eight entries in `contract_file_hashes` match their current files. The field is an asserted logical digest; no canonicalization recipe was found, and it is not the raw SHA of the manifest JSON. |
| `git_commit` | `cd1017aa90637bb81b1edf263f620e89346d84ca` is a valid local commit (2026-09-07) but its tree contains no `research/entry_tp_sl/` paths. The actual workstream source was committed in `fedfd1697bd78302e45da4a0e4980aba72c52e46` (2026-10-07); those source-file hashes match the manifest. `6b5f225e4f3670c8ba63063137b64ed7ce0270c1` and current `HEAD` contain the same declared content. **Commit attribution: `UNEXPLAINED/INCORRECT`; code content remains recoverable.** |
| `timestamp_utc` | Manifest says `2026-10-07T16:50:00Z`; the `fedfd...` commit is dated `2026-10-07 22:52:09 +0530` (17:22:09Z), later than the manifest timestamp. Identical source hashes support byte identity but do not establish test execution timing. |
| `environment_fingerprint` | The value is recorded in the implementation manifest and frozen contract manifest. It represents the environment-fingerprint payload, not a source file SHA. It was not recomputed in this read-only audit; `environment_fingerprint.py` requires runtime/package inspection. |
| `implementation_manifest_sha256` | Declared `a1abc15d247dc05d015e22a58e75d90ac077d767bb516bfa1bc9f12562ebc3b8`. Current raw manifest SHA is `0b4a718fa9f001a624c827a2c47edc14bfe88d17f81331364e85aa5ad9147236`; canonical JSON with that field removed is `9bf646490a0d362adfc0b7c9b34001a94324602c50c1438cae96cf036f1c23f7`. No in-repository algorithm or artifact identifies how the declared value is derived. **Unverifiable metadata field; not evidence that the five source hashes differ.** |

## Test-claim boundary

`6B_implementation_manifest.json::test_summary` records PASS strings for cost accounting, differential parity, property, PIT, and timeout tests. It does not record command lines, individual test node IDs, result artifacts, or a source commit containing the declared `git_commit` paths. The source bytes are now reconciled, but **the historical test executions are not independently verified by this hash audit**. No tests were run for V36.3.

## Classification summary

| Question | Answer |
|---|---|
| Are the two prior “resolver hash mismatches” actual content changes? | No; CRLF checkout bytes normalize exactly to the declared LF SHA-256 values. |
| Can the declared implementation be reconstructed from current local Git objects? | Yes; exact declared source bytes are in the `fedfd...` commit and unchanged through `HEAD`. |
| Is the manifest’s recorded commit correct for this workstream? | No; that commit tree has no workstream paths. |
| Are historical 6B tests proven to have run on those exact bytes? | Not by the available manifests; the claim remains unverified without logs/commands. |
