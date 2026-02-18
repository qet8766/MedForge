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

> **STALE** -- Pre-rework evidence (2026-02-17) predates the phase restructure. Full revalidation required after rework merge.

| Phase | Name | Latest Artifact | Timestamp (UTC) | Status |
| --- | --- | --- | --- | --- |
| 0 | Host Infrastructure | `docs/evidence/2026-02-17/phase0-host-20260217T124352Z.md` | `2026-02-17T12:43:52Z` | STALE |
| 1 | Control Plane Bootstrap | `docs/evidence/2026-02-17/phase1-bootstrap-20260217T124354Z.md` | `2026-02-17T12:43:54Z` | STALE |
| 2 | Auth + API Contract Gate | `docs/evidence/2026-02-17/phase2-auth-api-20260217T124410Z.md` | `2026-02-17T12:44:10Z` | STALE |
| 3 | Session Lifecycle + E2E Runtime | `docs/evidence/2026-02-17/phase3-lifecycle-recovery-20260217T124425Z.md` | `2026-02-17T12:44:25Z` | STALE |
| 4 | Routing + Network Isolation | `docs/evidence/2026-02-17/phase4-routing-e2e-20260217T124444Z.md` | `2026-02-17T12:44:44Z` | STALE |
| 5 | Competition Platform + Browser | `docs/evidence/2026-02-17/phase5-competitions-20260217T124557Z.md` | `2026-02-17T12:45:57Z` | STALE |

## Historical Notes

Historical pre-phase-model artifacts were retired from this repository during terminology cleanup and phase-model consolidation.

Pre-rework (2026-02-17) evidence was generated under the previous phase structure where Phase 4 combined routing, E2E runtime, and browser testing. The rework split these concerns across Phases 3-5.

## Update Rule

- Update `docs/phase-checking-strategy.md` and this file in the same change set for every accepted phase run.
- Keep this file concise; do not append long raw command transcripts here.
- Store long transcripts as separate immutable files under `docs/evidence/<date>/`.
