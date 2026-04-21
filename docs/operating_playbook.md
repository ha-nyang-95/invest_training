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

### Story 1.1 Task 9.1 — Final 5-Gate Verification (2026-04-21)

```
$ uv sync --frozen --group dev
Checked 64 packages in 3ms

$ uv run pytest -n auto
16 workers [41 items]
40 passed, 1 skipped in 1.93s

$ uv run pre-commit run --all-files
ruff (legacy alias) ........ Passed
ruff format ................ Passed
mypy ....................... Passed
detect private key ......... Passed
check yaml ................. Passed
check toml ................. Passed
check for merge conflicts .. Passed
fix end of files ........... Passed
trim trailing whitespace ... Passed

$ uv run lint-imports
Athena layer order (one-way only) KEPT
athena.core is a leaf (no athena.* deps) KEPT
execution MUST NOT import orchestrator (DTO interface only - AR-BND2) KEPT
alpha_defense MUST NOT import execution KEPT
ops_defense MUST NOT import execution KEPT
Contracts: 5 kept, 0 broken.

$ uv build --package athena-core --wheel --out-dir <tmp>
Successfully built athena_core-0.1.0-py3-none-any.whl
```

All 5 gates passed. Story 1.1 ready for review handoff.

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

**Story 1.1 baseline (current state):** `.github/workflows/ci.yml` runs on
`ubuntu-latest` and gates merges with: pre-commit (ruff + mypy + hygiene +
detect-private-key) → `lint-imports` → `pytest -n auto`. Triggered on every
push to `master`/`main` and on PR open.

**Story 1.3 migration (planned):**

1. Change `runs-on: ubuntu-latest` → `runs-on: [self-hosted, trading-pc]`
   (AR-INF3, D19 — physical implementation of the 72h cooling gate).
2. Add the full 7-stage pipeline:
   1. Lint + format (ruff)
   2. Type check (mypy strict)
   3. Layer enforcement (import-linter)
   4. Unit + regression tests (pytest)
   5. Snapshot regression (past 2 failures replay)
   6. 72h cooling gate marker
   7. Paper-run verification gate
3. Add `--cov-fail-under=80` to pytest (coverage gate).

Until Story 1.3 lands, the `scaffold-gate` job is the ONLY CI check — sufficient
for Story 1.1 verification, intentionally insufficient as a release gate.

---

## Commit Identity

Story 1.1 commits use inline `git -c user.name=... -c user.email=...` because per-repo and
global `git config` are intentionally unset. SSH commit signing infrastructure is owned by
**Story 1.2** (`1-2-환경-secrets-infrastructure-wsl2-os-keychain-ssh-signing`). Until then,
commits are unsigned but author-attributed to `장철환 <wkdcjfghks1@gmail.com>` (matching the
initial commit `17b61cf`).

**Story 1.2 update (2026-04-21):** global `git config --global user.name/email` set to
`chulhwan` / `wkdcjfghks1@gmail.com` before Task 2 commit. Unsigned commits `2f95bb6`,
`35ac260`, `a755d48`, `0558d3e`, `05a26da` carry this author. SSH signing is activated by
Task 5 (WSL2 side) — first **signed** commit will be the Task 5.4 empty verification commit,
and the Task 7.4 handoff commit is the second signed commit.

---

## Story 1.2 — Environment & Secrets Infrastructure

Source story: `_bmad-output/implementation-artifacts/1-2-환경-secrets-infrastructure-wsl2-os-keychain-ssh-signing.md`.

### Secret Bootstrap — one-time keyring enrollment

The 14 `SecretName` IDs are fixed in `packages/athena-core/athena/core/keyring_client.py`
(`SecretName(StrEnum)` — 5 KIS order/query keys + DART + 2 LLM + 2 notification +
3 S3 + LUKS). Enrolling them is a one-time per-host step.

**Recommended (production) — OS-native UI, value never touches shell history:**

*Windows (wincred backend):*
Open "자격 증명 관리자" (Credential Manager) → Windows 자격 증명 → 일반 자격 증명 추가. Set:
- 인터넷/네트워크 주소: `athena`
- 사용자 이름: `<SECRET_NAME>` (e.g. `KIS_ORDER_APP_KEY`)
- 암호: `<actual secret value>`

Or via CLI (value still shows in process list momentarily):
```powershell
cmdkey /generic:athena /user:KIS_ORDER_APP_KEY /pass:<value>
```

*Linux/WSL2 (Secret Service / libsecret backend):*
```bash
echo -n '<value>' | secret-tool store \
    --label='Athena KIS_ORDER_APP_KEY' \
    service athena \
    username KIS_ORDER_APP_KEY
```

**Dev-bootstrap (NOT for production) — Python one-liner:**

```bash
uv run python -c "from athena.core.keyring_client import set_secret, SecretName; \
    set_secret(SecretName.KIS_ORDER_APP_KEY, '<value>')"
```

⚠ **Warning:** the value appears in PowerShell/bash history. Use only for throwaway test
values. For real API keys, use the OS-native UI path above.

**Verifying enrollment:**

```python
from athena.core.keyring_client import get_secret, SecretName
print(get_secret(SecretName.KIS_ORDER_APP_KEY))   # raises MissingSecretError if absent
```

### Story 1.2 Task 1 — WSL2 setup (captured 2026-04-21)

Ubuntu installed via Microsoft Store (Ubuntu 24.04.1 LTS app), default user `khuk0`.
`/etc/wsl.conf` written with `[boot] systemd=true` + `[interop] appendWindowsPath=false`.
`wsl --shutdown` performed once after config change; systemd confirmed as PID 1.

```
$ wsl -l -v
  NAME      STATE           VERSION
* Ubuntu    Stopped         2
# (Stopped = idle; starts systemd on first command inside distro, verified below)

$ cat /etc/os-release | head -6
PRETTY_NAME="Ubuntu 24.04.1 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.1 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu

$ ps -p 1 -o comm=
systemd

$ systemctl is-system-running
running

$ systemctl --user is-active default.target
active
```

Base packages installed (`apt install -y build-essential git curl openssh-client
ca-certificates` + `pre-commit` for Task 5 support). Placeholder directories created:
`/var/lib/athena/{policy,ledger,data}` + `/data/parquet` + `/mnt/external`, owned by `khuk0:khuk0`.

### Story 1.2 Task 5 — SSH signing setup (captured 2026-04-21)

Signing key generated in WSL2: `~/.ssh/id_ed25519_athena_sign` (ed25519, no passphrase
— YubiKey hardware-backing deferred to V1.1+ per architecture D11). Global git config
applied WSL2-side: `gpg.format=ssh`, `user.signingkey`, `gpg.ssh.allowedSignersFile`,
`commit.gpgsign=true`, `tag.gpgsign=true`. `~/.ssh/allowed_signers` scopes verification
to `wkdcjfghks1@gmail.com` only.

```
$ ssh-keygen -lf ~/.ssh/id_ed25519_athena_sign.pub
256 SHA256:wx1+0pvHVT9Q46uW3xPPhSoO/cLKAZNUV33P3fBMAzU khuk0@athena-signing (ED25519)

$ git log --show-signature -1 197ce26
commit 197ce26d9cd4c034d82f425f99ece043564d80d7
Good "git" signature for wkdcjfghks1@gmail.com with ED25519 key \
    SHA256:wx1+0pvHVT9Q46uW3xPPhSoO/cLKAZNUV33P3fBMAzU
Author: chulhwan <wkdcjfghks1@gmail.com>
Date:   Tue Apr 21 21:29:22 2026 +0900

    chore(story-1.2): enable git SSH signing (AC-4)

$ git verify-commit 197ce26; echo $?
0
```

Commit `197ce26` is the **first signed commit in repository history**. It is
`--allow-empty` (zero file changes — verification only) and used `--no-verify`
because pre-commit hooks require python3.13 which is not in Ubuntu 24.04 main
apt; full WSL2 dev environment setup is Story 1.3 scope. The handoff commit
(Task 7.4) is made from Windows (where pre-commit works natively) with the same
author identity but is unsigned because signing keys live in WSL2.

### Story 1.2 Task 6 — Logger PC ↔ Trading PC SSH trust (captured 2026-04-21)

Sshd service running on Windows (StartType=Automatic). Four firewall rules in force,
three on Windows Defender Firewall and one on the WSL Hyper-V firewall layer.

**Windows Defender Firewall:**

```
$ Get-Service sshd
Name      : sshd
Status    : Running
StartType : Automatic

$ Get-NetFirewallRule -Name sshd-local-subnet
DisplayName : OpenSSH Server (local subnet only)
Enabled     : True
Profile     : Private
Action      : Allow
# Scope: Private profile + LocalSubnet (covers Tailscale network for home LAN access)

$ Get-NetFirewallRule -Name sshd-wsl-vnet
DisplayName : OpenSSH from WSL2 vNet (Story 1.2 AC-5)
Enabled     : True
Profile     : Any
Action      : Allow
# RemoteAddress: 172.16.0.0/12 — WSL2 standard RFC1918 range. Required because
# WSL vEthernet has no NetworkCategory and the Private-profile rule above doesn't match.

$ Get-NetFirewallRule -Name OpenSSH-Server-In-TCP
DisplayName : OpenSSH SSH Server (sshd)
Enabled     : False
# The wide-open default rule auto-created with the OpenSSH capability — explicitly disabled.
```

**WSL Hyper-V firewall:**

```
$ Get-NetFirewallHyperVRule -Name WSL-Athena-SSH-to-Host
DisplayName : WSL2 -> Host SSH (Story 1.2 AC-5)
Action      : Allow
# Direction=Inbound in the Hyper-V rule means inbound to the VM's vNIC. For WSL2 -> Host
# traffic (which is outbound from the VM), this rule is strictly redundant because the
# WSL VM's DefaultOutboundAction is already Allow. Kept as defensive documentation.
```

**WSL2-side verification:**

```
$ ssh logger-pc "echo ok"
Warning: Permanently added '172.20.16.1' (ED25519) to the list of known hosts.
ok

$ ssh-keygen -lf ~/.ssh/known_hosts | head -1
256 SHA256:oXXxA5TolUKJcaxWHDg+ptS4HIjuH3Yyq0XgpP8E+Po [logger-pc-ed25519]
```

**Windows OpenSSH administrators-group override:**

`khuk0` is in the local Administrators group, so sshd consults
`C:\ProgramData\ssh\administrators_authorized_keys` instead of the per-user
`%USERPROFILE%\.ssh\authorized_keys`. The WSL2 logger-sync pubkey was enrolled into
`administrators_authorized_keys` with ACL restricted to SYSTEM + BUILTIN\Administrators
(Full control) per Windows OpenSSH strict-mode requirement.

**IP note:** `HostName` in `~/.ssh/config → Host logger-pc` is the default gateway from
WSL2's perspective (`ip route show | awk '/^default/ {print $3}'`). On WSL2 reboot this
value can change — re-check with the same command and update `~/.ssh/config` if needed.
Current value: `172.20.16.1`. Alternative (not adopted): `[experimental]
networkingMode=mirrored` in `/etc/wsl.conf` would make the IP stable at the cost of
NAT-mode isolation.

### Story 1.2 Task 7.2 — 5-gate pre-handoff verification (captured 2026-04-21)

Captured by dev agent before Task 1/5/6 manual work — confirms the code-only portion
of Story 1.2 (Tasks 2, 3, 4) is release-ready. Re-run with identical commands immediately
before the Task 7.4 handoff commit once Tasks 1/5/6 are complete.

```
$ uv sync --frozen --group dev
Audited 64 packages in 4ms

$ uv run pytest -n auto
======================= 111 passed, 2 skipped in 2.00s =======================

$ uv run pre-commit run --all-files
ruff (legacy alias) ........ Passed
ruff format ................ Passed
mypy ....................... Passed
Detect hardcoded secrets ... Passed
detect private key ......... Passed
check yaml ................. Passed
check toml ................. Passed
check for merge conflicts .. Passed
fix end of files ........... Passed
trim trailing whitespace ... Passed

$ uv run lint-imports
Analyzed 13 files, 3 dependencies.
Athena layer order (one-way only) KEPT
athena.core is a leaf (no athena.* deps) KEPT
execution MUST NOT import orchestrator (DTO interface only - AR-BND2) KEPT
alpha_defense MUST NOT import execution KEPT
ops_defense MUST NOT import execution KEPT
Contracts: 5 kept, 0 broken.

$ uv build --package athena-core --wheel --out-dir /tmp/athena-1-2-check
Successfully built athena_core-0.1.0-py3-none-any.whl
```

**Test suite delta from Story 1.1 close (72 passing / 2 skipped):** +39 new tests
across `test_keyring_client.py` (10), `test_keyring_client_no_shell.py` (5),
`test_settings.py` (22), `test_no_dotenv_files.py` (2). `.env` guard has 5 parametrize
cases that are counted individually in the +39. The story's original Task 7.3 estimate
was "+19 min / +25 max" — actual count exceeded the max because of the parametrize
expansion and additional accessor-coverage / literal-rejection / missing-error tests.
