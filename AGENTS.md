# Repository Guidelines

## Project Structure & Module Organization
`medforge-spec.md` is the top-level source of truth. Use `docs/` for detailed design and delivery docs (`architecture.md`, `build-gates.md`, `implementation-checklist.md`, etc.). Infrastructure lives in `infra/`:
- `infra/compose/`: control-plane Compose stack and `.env.example`
- `infra/caddy/`: wildcard TLS/routing config
- `infra/packs/default/`: default code-server pack image
- `infra/zfs/` and `infra/firewall/`: host setup scripts

Application stack: Next.js + TypeScript (web) and FastAPI + SQLModel + Pydantic (API/data models).

Primary app code lives in `apps/web` and `apps/api`; infra and spec docs remain in `infra/` and `docs/`.

## Build, Test, and Development Commands
- `cp infra/compose/.env.example infra/compose/.env`: create local environment file.
- `sudo bash infra/host/bootstrap-easy.sh`: one-command host bootstrap (NVIDIA runtime, ZFS datasets, bridge firewall settings, local pack build).
- `bash infra/host/quick-check.sh`: fast local lint/type/test/build pass.
- `bash infra/host/validate-gate56.sh`: run host Gate 5/6 core validation and write evidence markdown.
- `docker compose --env-file infra/compose/.env -f infra/compose/docker-compose.yml up -d --build`: build and start control-plane services.
- `docker compose --env-file infra/compose/.env -f infra/compose/docker-compose.yml logs -f medforge-api medforge-caddy`: stream key service logs.
- `cd apps/api && uv venv .venv && . .venv/bin/activate && uv pip install -e '.[dev]'`: install API dependencies.
- `cd apps/api && pytest -q`: run API tests.
- `cd apps/web && npm install && npm run build`: verify web app type-check/build.
- `POOL_DISKS='/dev/sdX' bash infra/zfs/setup.sh`: one-time ZFS pool/dataset setup (replace disk path).
- `bash infra/firewall/setup.sh`: apply east-west isolation rules for session containers.

## Coding Style & Naming Conventions
Use 2-space indentation in YAML/Markdown, and Bash with `set -euo pipefail`. Keep environment variable names uppercase (`PACK_IMAGE`, `SESSION_SECRET`). Follow existing naming patterns:
- Compose services/networks: `medforge-*`
- Session containers: `mf-session-<slug>`
- Session slug: 8-char lowercase base32 (see `docs/data-model.md`)
- Import ordering: stdlib → third-party → local, with blank lines between groups (Python and TypeScript).
- Shell scripts: prefer named functions over long one-liner pipes. Break complex logic into readable steps.

## Testing Guidelines
Run `cd apps/api && pytest -q` for backend checks and `cd apps/web && npm run build` for frontend validation. Still validate infra/session behavior against `docs/build-gates.md` with evidence (logs, curl output, screenshots). For infra/scripts, run `find infra -name '*.sh' -print0 | xargs -0 -n1 bash -n` and `find infra -name '*.sh' -print0 | xargs -0 -n1 shellcheck` when available.

## Commit & Pull Request Guidelines
Git history is minimal (`Initial commit`), so use clear imperative commits and include issue IDs from `docs/issue-plan.md` when applicable (example: `MF-006 enforce race-safe GPU allocation`). PRs should include:
- scope summary and linked issue (`MF-###`)
- affected gate(s) and acceptance checks executed
- config/security impact (`.env`, networking, auth headers)
- UI/routing screenshots when behavior changes

## Code Hygiene
- **File splitting**: when a file exceeds ~150 lines, split it into smaller focused files. Always add `@filename` references in the relevant places so readers can trace where code moved.
- **TODO tracking**: use `TODO(MF-###)` format so every TODO is tied to a tracked issue. Unlinked TODOs rot.
- **Dead code**: delete it, don't comment it out. Git has history.
- **No wildcard imports**: no `from x import *` or `import *`. Always import explicitly.
- **Type annotations**: require type hints on all Python function signatures. Use TypeScript `strict` mode.
- **API responses**: always return structured error responses with a consistent shape, not raw strings.

## Security & Configuration
- Do not commit secrets; keep real values in `infra/compose/.env`.
- All hosts, ports, and URLs must come from environment variables or config. No `localhost:8080` buried in source.
- Keep `PACK_IMAGE` digest-pinned.
- Preserve Caddy's `request_header -X-Upstream` behavior to prevent upstream spoofing.
- No `latest` Docker tags, no unpinned pip/npm versions. Use exact versions or digests.
- Always use `uv` over `pip` for Python package management.

## Logging
Always include context identifiers (session slug, user ID) in log messages. Multi-tenant debugging is impossible without them.

## Documentation Sync
- Whenever a plan or implementation diverges from the original doc/spec files, update the affected docs in the same change set.
- Do not leave doc updates for later; keep docs aligned in real-time with code and plan decisions.
