# Athena V1.0

본인 전용 한국 주식 단기 트레이딩 시스템. 2층 방어 (Veto Gate + Anti-Ego
Firewall) + 4층 Circuit Breaker + Hard-Locked Exit. PRD §17/§18 scope locked
(상용화 기각).

## Quick Start

Requires git + 16 GB+ RAM. Python 3.13 is uv-managed (no pre-install needed).

```sh
# 1. Install uv 0.11.7+
irm https://astral.sh/uv/install.ps1 | iex                # Windows PowerShell
curl -LsSf https://astral.sh/uv/install.sh | sh           # Linux / macOS

# 2. Sync workspace
uv sync --frozen --group dev

# 3. Verify (5 gates — must all pass before merging)
uv run pytest -n auto
uv run lint-imports
uv run pre-commit run --all-files
uv build --package athena-core --wheel
```

See `docs/operating_playbook.md` for full ops procedures, toolchain versions,
and the Story 1.3 self-hosted CI migration plan.

## Architecture

- 8 Epics / 65 Stories — `_bmad-output/planning-artifacts/`
- Layer hierarchy enforced by import-linter — `.importlinter`
- 6-package monorepo: `athena.{core, feature_store, alpha_defense, ops_defense, orchestrator, execution}`
- DTO 3-field contract (timestamp UTC, module_version semver, policy_version_git_sha) — `athena.core.dto.BaseDTO`
- Build-time git SHA injection — `packages/athena-core/hatch_build.py`

## Sprint Status

`_bmad-output/implementation-artifacts/sprint-status.yaml`
