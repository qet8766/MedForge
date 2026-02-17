# MedForge Validation Evidence (Concise Index)

This file is the concise canonical index for phase validation evidence.

### Scope

### In Scope

- current canonical accepted artifact pointer per phase
- concise timestamp/status index for latest accepted progression
- update rule coupling with `docs/phase-checking-strategy.md`

### Out of Scope

- long-form command transcripts and raw payload dumps (`docs/evidence/<date>/`)
- phase acceptance criteria and execution semantics (`docs/phase-checking-strategy.md`)
- runtime behavior contracts (`docs/architecture.md` and domain contract docs)

### Canonical Sources

- `docs/phase-checking-strategy.md`
- `docs/evidence/`

## Current Canonical Artifacts

Latest canonical full progression pass: `2026-02-17` (remote-public-only policy).

| Phase | Name | Latest Artifact | Timestamp (UTC) | Status |
| --- | --- | --- | --- | --- |
| 0 | Host Foundation | `docs/evidence/2026-02-17/phase0-host-20260217T064618Z.md` | `2026-02-17T06:46:18Z` | PASS |
| 1 | Control Plane Bootstrap | `docs/evidence/2026-02-17/phase1-bootstrap-20260217T064621Z.md` | `2026-02-17T06:46:21Z` | PASS |
| 2 | Auth + Session API Contracts | `docs/evidence/2026-02-17/phase2-auth-api-20260217T064639Z.md` | `2026-02-17T06:46:39Z` | PASS |
| 3 | Session Lifecycle + Recovery | `docs/evidence/2026-02-17/phase3-lifecycle-recovery-20260217T064705Z.md` | `2026-02-17T06:47:05Z` | PASS |
| 4 | Routing, Isolation, End-to-End | `docs/evidence/2026-02-17/phase4-routing-e2e-20260217T064739Z.md` | `2026-02-17T06:47:39Z` | PASS |
| 5 | Competition Platform (Alpha) | `docs/evidence/2026-02-17/phase5-competitions-20260217T064856Z.md` | `2026-02-17T06:48:56Z` | PASS |

## Historical Notes

Historical pre-phase-model artifacts were retired from this repository during terminology cleanup and phase-model consolidation.

## Update Rule

- Update `docs/phase-checking-strategy.md` and this file in the same change set for every accepted phase run.
- Keep this file concise; do not append long raw command transcripts here.
- Store long transcripts as separate immutable files under `docs/evidence/<date>/`.
