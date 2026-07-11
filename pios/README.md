# Data Bot AI — Project Intelligence Operating System (PIOS)

**Single source of truth** for architecture, roadmap, sprint history, standards, validation gates, status, technical debt, and release planning.

Deep handbook remains in [`documentation/`](../documentation/README.md). ADRs remain in [`docs/architecture/`](../docs/architecture/). PIOS is the **control plane** agents must read before any development task.

## Mandatory agent read order

1. This file (`pios/README.md`)
2. [`05_status/PROJECT_STATUS.md`](05_status/PROJECT_STATUS.md)
3. [`04_sprints/CURRENT_SPRINT.md`](04_sprints/CURRENT_SPRINT.md)
4. Relevant slices of [`02_architecture/`](02_architecture/) and [`03_standards/`](03_standards/)
5. Run impact analysis before non-trivial changes:
   ```bash
   python pios/tools/impact_analyze.py --task "describe the change"
   ```
6. Implement only in-scope files
7. Run validation gates ([`03_standards/VALIDATION_GATES.md`](03_standards/VALIDATION_GATES.md))
8. Complete the task:
   ```bash
   python pios/tools/complete_task.py --summary "what changed"
   ```
9. **Stop**

Short protocol: [`06_prompts/TASK_PROTOCOL.md`](06_prompts/TASK_PROTOCOL.md)

## Module map

| Module | Path | Purpose |
|--------|------|---------|
| Vision | `01_vision/` | Product vision, users, goals, canonical roadmap |
| Architecture | `02_architecture/` | Layers, deps, imports, AI/RAG/memory/storage flows |
| Standards | `03_standards/` | Coding, SOLID, testing, validation gates |
| Sprints | `04_sprints/` | Current sprint + archive ledger |
| Status | `05_status/` | Live project status, debt, known issues |
| Prompts | `06_prompts/` | Task + completion protocols |
| Releases | `07_releases/` | v1.0–v2.0 policies and freeze rules |
| Knowledge | `08_knowledge/` | ADRs index, rejected approaches, lessons |
| Docs sync | `09_docs/` | Ownership map PIOS ↔ handbook ↔ guides |
| Tools | `tools/` | Active intelligence CLIs |

## Canonical live files (agents write here)

- `pios/05_status/PROJECT_STATUS.md`
- `pios/04_sprints/CURRENT_SPRINT.md`
- `pios/05_status/TECHNICAL_DEBT.md`
- `pios/01_vision/ROADMAP.md`

Root `ROADMAP.md` and `KNOWN_ISSUES.md` are **mirrors** of PIOS canonical copies.

## Intelligence tools

```bash
python pios/tools/refresh_status.py
python pios/tools/impact_analyze.py --task "..."
python pios/tools/arch_check.py
python pios/tools/complete_task.py --summary "..."
python pios/tools/recommend_sprint.py
```

## Rules

- Never invent features. Label gaps **Not verified**.
- Prefer evidence: tests, routes, services, release tags.
- Do not skip validation gates for release-affecting work.
- Update PIOS at task end; do not leave status stale.
