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

(populated at end of Story 1.1 Task 3.5 / Task 9.1)

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
