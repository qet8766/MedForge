## 9. Issue Plan (Phase 1/2 + Estimates)

Assumptions for estimates:

- One full-time engineer working across API, infra, and docs.
- Estimates are engineering time only (not external waiting on DNS/domain approvals).
- Effort is in engineering days (`d`), including implementation + basic validation.

### Phase 1 (MVP to Gate 7)

| Issue | Scope | Gate Mapping | Depends On | Estimate | Status |
| --- | --- | --- | --- | --- | --- |
| `MF-001` | Host foundation: Docker, NVIDIA toolkit, ZFS setup script, wildcard DNS/TLS baseline | Gate 0 | None | `2.0d` | Done |
| `MF-002` | Compose bootstrap + networks + service wiring (`web`, `api`, `db`, `caddy`) | Gate 1 | `MF-001` | `1.5d` | Done |
| `MF-003` | DB schema, enums, generated `gpu_active`, constraints, seed rows | Gate 1 | `MF-002` | `1.0d` | Done |
| `MF-004` | Auth basics: signup/login, cookie sessions, `/api/me`, Origin checks | Gate 2 | `MF-003` | `1.5d` | Done |
| `MF-005` | `GET /api/auth/session-proxy` contract + Caddy forward_auth wiring | Gate 2, 5 | `MF-004` | `1.0d` | Done |
| `MF-006` | Session create transaction with race-safe GPU allocation and per-user limits | Gate 3 | `MF-003`, `MF-004` | `2.0d` | Done |
| `MF-007` | Per-session ZFS dataset provisioning (`workspace_zfs`, ownership, optional quota) | Gate 3 | `MF-006` | `1.0d` | Done |
| `MF-008` | Container launch path (`mf-session-<slug>`, runtime hardening, single-GPU binding) | Gate 3 | `MF-006`, `MF-007` | `1.5d` | Done |
| `MF-009` | Stop flow with idempotency, snapshot on stop, terminal-state guarantees | Gate 3 | `MF-008` | `1.5d` | Done |
| `MF-010` | Poller for `starting/running` sessions and container-death transition logic | Gate 4 | `MF-008` | `1.0d` | Done |
| `MF-011` | Boot-time reconciliation across `starting/running/stopping` | Gate 4 | `MF-009`, `MF-010` | `1.0d` | Done |
| `MF-012` | East-west isolation rules in `DOCKER-USER` + validation test | Gate 5 | `MF-002`, `MF-005`, `MF-008` | `1.0d` | Done |
| `MF-013` | Structured JSON event logging (`session.start`, `session.stop`) | Gate 3, 4 | `MF-004`, `MF-006`, `MF-009`, `MF-010` | `0.5d` | Done |
| `MF-014` | End-to-end UI flow wiring and smoke validation for login -> start -> IDE -> stop | Gate 6 | `MF-005`, `MF-009`, `MF-011`, `MF-012` | `2.0d` | Done |
| `MF-015` | Competition schema + API (`competitions`, `datasets`, `submissions`) with `competition_tier` and permanent competitions | Gate 7 | `MF-003`, `MF-004` | `1.5d` | Done |
| `MF-016` | Submission scoring pipeline + worker (append-only `submission_scores`, `score_status`, metric/split versioning) | Gate 7 | `MF-015` | `1.5d` | Done |
| `MF-017` | Kaggle-style web pages for competitions, dataset catalog, leaderboard, and submission UI | Gate 7 | `MF-015`, `MF-016` | `2.0d` | Done |
| `MF-018` | Seed permanent PUBLIC competitions (`titanic-survival`, `rsna-pneumonia-detection`, `cifar-100-classification`) + mirrored data manifests | Gate 7 | `MF-015` | `1.0d` | Done |
| `MF-019` | Competition validation suite (schema checks, daily caps, deterministic ranking) | Gate 7 | `MF-016`, `MF-017` | `0.5d` | Done |
| `MF-020` | Competition API error-contract migration (`application/problem+json`) + web client parser alignment (extracts `detail`/`title`, not full RFC 7807 `type`/`errors`) | Gate 7 (hardening) | `MF-015`, `MF-016`, `MF-017` | `0.5d` | Done |

Phase 1 total estimated effort: `25.5d`.

### Phase 2 (Hardening After MVP)

| Issue | Scope | Depends On | Estimate | Status |
| --- | --- | --- | --- | --- |
| `MF-101` | Automated gate test suite (concurrency, kill/reconcile, auth spoof, isolation) | Phase 1 complete | `2.0d` | Done |
| `MF-102` | Operational scripts/runbook: reconciliation trigger, snapshot inspection, emergency cleanup | Phase 1 complete | `1.0d` | Done |
| `MF-103` | Logging hardening: correlation IDs, normalized error codes, log schema checks | `MF-013` | `1.0d` | Done |
| `MF-104` | Security hardening pass: auth rate limits, cookie/session abuse protections, header policy tests | `MF-004`, `MF-005` | `1.5d` | Done |
| `MF-105` | Soak/load pass: repeated create/stop cycles and failure-injection checks | Phase 1 complete | `1.5d` | Done |

Phase 2 total estimated effort: `7.0d`.

### Suggested Execution Order

1. `MF-001` -> `MF-005` to establish stable control plane and auth/routing base.
2. `MF-006` -> `MF-009` to complete reliable lifecycle (`create`, launch, stop, snapshot).
3. `MF-010` -> `MF-012` to guarantee failure recovery and network isolation.
4. `MF-013` -> `MF-014` to finish observability and full flow validation.
5. `MF-015` -> `MF-019` to deliver permanent competition APIs, scoring, and portal UX.

### Exit Criteria

Phase 1 exit criteria met as of 2026-02-16 (see `docs/host-validation-2026-02-16.md`):

- [x] All Phase 1 issues (`MF-001` through `MF-020`) completed.
- [x] Gates 0-7 acceptance checks pass as written in `docs/build-gates.md`.
- [x] No open defect that can strand sessions in `starting`/`stopping` or break GPU exclusivity.

Phase 2 hardening complete as of 2026-02-16:

- [x] All Phase 2 issues (`MF-101` through `MF-105`) completed.
- [x] 112 total tests (108 fast CI + 2 docker + 2 load).
- [x] Operational scripts and runbook in `infra/host/ops-*.sh` and `docs/runbook.md`.
- [x] Structured logging with correlation IDs and error code registry.
