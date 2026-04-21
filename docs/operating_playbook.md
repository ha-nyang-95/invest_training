# Athena Operating Playbook

> Stub created in Story 1.1 Task 1.1 — populated incrementally across stories.
> Source of truth for Khuk0's day-to-day operational procedures, environment versions,
> and verification logs.

---

## Toolchain Versions (frozen at scaffold time)

Recorded by Story 1.1 Task 1.1 on **2026-04-21** (Windows 11 host):

| Tool | Version | Source / Install Command |
|---|---|---|
| `uv` | `0.11.7` | `irm https://astral.sh/uv/install.ps1 \| iex` (installed to `C:\Users\khuk0\.local\bin\`) |
| Python (workspace) | `3.13` (uv-managed) | pinned via `.python-version`, downloaded by `uv` if absent |
| Python (system, baseline) | `3.14.4` | pre-existing on host (NOT used by Athena workspace) |
| `git` | `2.53.0.windows.2` | pre-existing on host |

**Note on PATH precedence:** `C:\Users\khuk0\.local\bin\uv.exe` (0.11.7) takes precedence over the older
`C:\Users\khuk0\AppData\Local\Programs\Python\Python313\Scripts\uv.exe` (0.10.0). Verify with
`where.exe uv` — first entry must be `.local\bin`.

---

## Week 1 Day 1 Verification

Story 1.1 Task 3.5 — recorded **2026-04-21**.

```
$ uv sync --group dev
Resolved 67 packages in 99ms
Installed 61 packages, +tzdata==2026.1 (Windows IANA db)

$ uv run python -c "import athena.core, athena.feature_store, athena.alpha_defense, athena.ops_defense, athena.orchestrator, athena.execution; print('ALL 6 OK')"
ALL 6 OK

$ uv run pytest tests/ packages/ -q
11 passed, 1 skipped in 0.49s
```

**Skipped:** `test_uvloop_importable_on_non_windows` — `uvloop` is Linux/macOS only;
the orchestrator process runs on WSL2 Ubuntu (D17), so Windows dev hosts skip this check.

**Tier-1 dependency snapshot (frozen by uv.lock):**

| Package | Resolved version |
|---|---|
| pydantic | 2.13.3 |
| pydantic-settings | 2.14.0 |
| keyring | 25.7.0 |
| polars | 1.40.0 |
| duckdb | 1.5.2 |
| python-kis | 2.1.6 |
| tzdata (Windows) | 2026.1 |
| pytest / asyncio / xdist | 9.0.3 / 1.3.0 / 3.8.0 |
| ruff / mypy / pre-commit / import-linter | 0.15.11 / 1.20.1 / 4.5.1 / 2.11 |

---

## CI / Self-Hosted Runner Migration

(deferred to Story 1.3 — see `_bmad-output/planning-artifacts/epics.md#Story-1.3`)

---

## Commit Identity

Story 1.1 commits use inline `git -c user.name=... -c user.email=...` because per-repo and
global `git config` are intentionally unset. SSH commit signing infrastructure is owned by
**Story 1.2** (`1-2-환경-secrets-infrastructure-wsl2-os-keychain-ssh-signing`). Until then,
commits are unsigned but author-attributed to `장철환 <wkdcjfghks1@gmail.com>` (matching the
initial commit `17b61cf`).
