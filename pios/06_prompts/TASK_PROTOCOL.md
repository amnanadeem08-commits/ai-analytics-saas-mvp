# Task Protocol (replace 500-line prompts)

```text
Read PIOS (pios/README.md).
Read current project status (pios/05_status/PROJECT_STATUS.md).
Read current sprint (pios/04_sprints/CURRENT_SPRINT.md).
Run: python pios/tools/impact_analyze.py --task "<task>"
Implement next task (in-scope files only).
Run validation gates (pios/03_standards/VALIDATION_GATES.md).
Run: python pios/tools/complete_task.py --summary "<summary>"
Stop.
```

## Rules

- Do not invent architecture or features
- Run `arch_check.py` before claiming done on cross-layer work
- Update roadmap/debt only when the change truly affects them
- Produce a completion report; then stop
