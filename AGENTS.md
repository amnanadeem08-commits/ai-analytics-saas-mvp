# AGENTS.md — Data Bot AI

**Start here:** [`pios/README.md`](pios/README.md)

This repository uses a **Project Intelligence Operating System (PIOS)**. Do not begin feature work from a large pasted prompt.

## Minimum protocol

```text
Read PIOS.
Read current project status.
Read current sprint.
Run impact_analyze.
Implement next task.
Run validation.
Update PIOS (complete_task).
Stop.
```

## Key paths

| Need | Path |
|------|------|
| Entrypoint | `pios/README.md` |
| Live status | `pios/05_status/PROJECT_STATUS.md` |
| Current sprint | `pios/04_sprints/CURRENT_SPRINT.md` |
| Architecture | `pios/02_architecture/` |
| Standards / gates | `pios/03_standards/` |
| Deep handbook | `documentation/README.md` |
| ADRs | `docs/architecture/` |

## Tools

```bash
python pios/tools/refresh_status.py
python pios/tools/impact_analyze.py --task "..."
python pios/tools/arch_check.py
python pios/tools/complete_task.py --summary "..."
python pios/tools/recommend_sprint.py
```
