# Release Policy

## Version lines

| Line | Status | Policy |
|------|--------|--------|
| v1.0 | Released / maintenance | Freeze: bugfix, security, docs only on `release/v1.0` |
| v1.1 | Planned | Compatible features on `main` (minor) |
| v1.2 | Planned | Further compatible features |
| v2.0 | Future | Breaking API / major architecture allowed with migration notes |

## Freeze policy (v1.0)

**Allowed:** bug fixes, security patches, documentation  
**Forbidden:** architectural changes, breaking APIs, new product features

## Promotion

1. Pass validation gates in `pios/03_standards/VALIDATION_GATES.md`
2. Update release notes under `pios/07_releases/<version>/`
3. Tag SemVer; update PIOS status + roadmap

Checklists: [`release/v1.0/`](../../release/v1.0/)
