# Documentation Sync Map

| Concern | Canonical (write) | Deep reference (read) | Generated / export |
|---------|-------------------|----------------------|--------------------|
| Live status | `pios/05_status/*` | — | `refresh_status.py` |
| Roadmap | `pios/01_vision/ROADMAP.md` | root mirror `ROADMAP.md` | — |
| Known issues | `pios/05_status/KNOWN_ISSUES.md` | root mirror `KNOWN_ISSUES.md` | — |
| Architecture narrative | `pios/02_architecture/*` | `documentation/02_architecture`, ADRs | — |
| Handbook | `documentation/*` | — | `scripts/export_handbook.py` |
| Release guides | `docs/release/*` | `documentation/18_release` | — |
| Release checklists | `release/v1.0/*` | `pios/07_releases` | — |
| Agent protocol | `pios/06_prompts/*` | `.cursor/rules/pios-protocol.mdc` | — |

## Rules

1. Agents update PIOS live files every task
2. Handbook updates only with repo evidence
3. Do not duplicate long handbook chapters into PIOS — link instead
4. When root mirrors diverge, **PIOS wins**; refresh mirrors
