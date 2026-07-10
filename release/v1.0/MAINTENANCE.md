# Maintenance Branch Rules — `release/v1.0`

This branch tracks Data Bot AI **v1.0.x** production maintenance.

## Allowed

- Bug fixes
- Security patches
- Documentation updates

## Not Allowed

- Architectural changes
- Breaking API changes
- New product features

## Process

1. Land hotfixes on `release/v1.0`
2. Tag patch releases as `v1.0.x` when needed
3. Cherry-pick or merge fixes back to `main` when appropriate

All new feature development continues on `main`.
