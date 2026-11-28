# SKILL_UTILIZATION_REGISTER

Auditable record of which skills each agent actually discovered, read and invoked.
Maintained by AGENT 00 (Main Orchestrator). Updated per sprint; entries are appended, never rewritten.

**Sprint:** 2026-11-28 (evening) — orchestration spec v2
**Baseline commit at sprint start:** see `git log -1` (CI green from run 46167547882)

---

## Skill catalog discovered in this environment

| Location | What it contains | Used? |
|---|---|---|
| `.agents/skills/btcognitive-research-orchestrator/SKILL.md` | Project seven-phase lifecycle, econometric standards, governance | Yes — read in full by AGENT 00, and by every specialist before work |
| `AGENTS.md` (repo root) | Permanent operating contract, epistemic boundaries, Phase 0–7 | Yes — read in full |
| `README.md` | Architecture, endpoints, current status block | Yes |
| `/home/ubuntu/skills/` (platform skills) | deep-research, data-analysis, finance-pro-playbooks, financial-analysis, workflow-composer, webdev, imagegen, slides, office-documents, git-attribution, etc. | Per-agent (see table) |

Skills that were **not** available and were therefore not claimed: any external/third-party skill registry; no skill was installed during this sprint.

---

## Per-agent register

| Agent | Assignment | Skills discovered | Skills read | Skills invoked | Procedures applied | Skills unavailable | Alternative used |
|---|---|---|---|---|---|---|---|
| 00 Orchestrator | Integration, verification, delivery | All above | `AGENTS.md`, project SKILL.md, README, git-attribution | project SKILL.md, git-attribution, workflow delegation | Phase 0–7 lifecycle; commit attribution rules | — | Manual git/CI verification with `gh` |
| 01 Architecture | Dependency map, debt register | project SKILL.md | project SKILL.md | — | Phase 1 state recovery | — | Static reading + `git` history |
| 02/05/06/07 Research + Forecasting + Calibration | Loss functions, model diagnosis, literature | deep-research, finance-pro-playbooks, financial-analysis | project SKILL.md | deep-research | Phase 2 research-before-design | — | Primary sources via web search |
| 03/10 Data + Backend | Ingestion, invariants, API cost | project SKILL.md, data-analysis | project SKILL.md | — | Phase 1/4 causal boundaries | — | Code reading + live endpoint probes |
| 11 Frontend | IA, above-the-fold, responsive, a11y | imagegen (for review only), project SKILL.md | project SKILL.md | browser inspection | Phase 1 state recovery | — | Playwright/axe where available |
| 13 QA/Security | Failure triage, security audit | project SKILL.md | project SKILL.md | — | Phase 6 red-team verification | — | Isolated pytest invocations |

---

## Notes on governance compliance

- Every agent was instructed to obey `AGENTS.md` §2 epistemic boundaries and the project skill's Phase 5 guardrails.
- No agent was authorised to modify code during this sprint; implementation follows explicit user approval (Stage C).
