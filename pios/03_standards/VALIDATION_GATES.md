# Validation Gates

Derived from [`release/v1.0/RELEASE_GATES.md`](../../release/v1.0/RELEASE_GATES.md).

## Per-task gates (minimum)

| # | Gate | Command / evidence |
|---|------|--------------------|
| 1 | Architecture rules | `python pios/tools/arch_check.py` |
| 2 | Targeted tests | `pytest` paths suggested by impact analyze |
| 3 | No invented features | Diff reviewed against PIOS + handbook |
| 4 | PIOS updated | status / sprint / debt as needed |

## Release gates (v1.0+)

| # | Gate | Evidence |
|---|------|----------|
| 1 | Production checklists | `release/v1.0/*_CHECKLIST.md` |
| 2 | Full automated suite | `pytest` |
| 3 | E2E with real datasets | `tests/release/test_e2e_production.py` |
| 4 | Known issues documented | `pios/05_status/KNOWN_ISSUES.md` |
| 5 | Dependencies pinned | `requirements*.txt` |
| 6 | Release docs verified | `docs/release/*`, changelog, roadmap |
| 7 | API docs confirmed | `docs/release/API_GUIDE.md` |
| 8 | Deployment docs | `docs/release/DEPLOYMENT_GUIDE.md` |
| 9 | Backup / recovery | DR guide + backup checklist |
| 10 | Security validation | `tests/security/`, security audit endpoint |

Do **not** skip release gates for release-affecting work.
