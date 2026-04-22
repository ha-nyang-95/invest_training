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

**Story 1.1 baseline (superseded):** `.github/workflows/ci.yml` ran the
single-job `scaffold-gate` on `ubuntu-latest` with pre-commit + lint-imports
+ pytest.

**Story 1.3 migration (landed, Khuk0 host-setup pending):** Workflow renamed
`scaffold-gate` → `ci-7-stage`, runs on `[self-hosted, trading-pc]` (AR-INF3).
7 jobs in strict serial `needs:` chain — parallelism is banned because each
stage is a gate in the Athena governance sequence:

  1. `stage-1-pre-commit` — ruff + mypy + hygiene + detect-private-key +
     gitleaks + import-linter
  2. `stage-2-pytest-unit` — `pytest -n auto -m "not integration and not
     snapshot and not walk_forward" -p no:randomly` (PYTHONHASHSEED=0)
  3. `stage-3-pytest-integration` — `pytest -n auto -m integration` (mock KIS)
  4. `stage-4-snapshot-regression` — `pytest -m snapshot` (skipped until
     Epic 2 Story 2.1 fixture)
  5. `stage-5-walk-forward-smoke` — `pytest -m walk_forward` (skipped until
     Epic 8 Story 8.3 runner)
  6. `stage-6-cooling-gate` — `scripts/check_cooling.py` (72h since previous
     `policy:` merge; FR57)
  7. `stage-7-paper-replay-marker` — `scripts/check_paper_replay_marker.py`
     (`paper-replay-ok/<short_sha>` tag check; NFR-R5)

`concurrency.group = ci-${{ github.ref }}` with `cancel-in-progress: true`.
Coverage gate (`--cov-fail-under=80`) is explicitly out of scope and deferred
to Story 1.9 / Epic 2.

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

---

## Story 1.3 — Self-Hosted CI/CD Pipeline — 7단계 Gate

Story 1.3 automates Tasks 2, 3, 4, 6 and the Task 5 branch-protection script.
Tasks 1 (self-hosted runner registration) and the apply/verify side of Task 5
(gh auth, gh-api PUT, protected-push dry-run) remain Khuk0 admin work. The
following sub-sections are populated as each step is completed.

### Commit Discipline (Story 1.3 onward)

Branch protection activates `required_signatures: true` on `master` as soon as
Khuk0 runs `scripts/setup_branch_protection.sh`. Until Windows host SSH signing
lands (Story 1.7, still deferred but no longer a blocker), **the entire dev
loop — edit, pre-commit, pytest, signed commit — runs inside WSL2 Ubuntu 24.04**:

```bash
wsl -d Ubuntu
cd /mnt/c/Users/khuk0/vibe/invest_training

# pre-commit hook chain runs on its own during `git commit`, so the explicit
# `--all-files` run is only needed when you want to verify untouched files.
uv run pytest -n auto
git commit -S -m "..."
```

WSL2 toolchain state (installed 2026-04-22 in Story 1.3 session):

- `uv 0.11.7` at `~/.local/bin/uv` (sourced by `~/.bashrc` via
  `$HOME/.local/bin/env`).
- `CPython 3.13.13` under uv-managed Python (`uv python install 3.13`).
- `gh 2.45.0` from `apt` (Ubuntu `noble-updates/universe`).
- `.venv/` reproduced via `uv sync --frozen --group dev` (64 packages).
- Git hooks installed via `uv run pre-commit install` and
  `uv run pre-commit install --hook-type commit-msg`.

Because hooks now run natively in WSL2 alongside `git commit`, `--no-verify`
is no longer used. The hybrid "pre-commit on Windows Git Bash + commit on
WSL2 proxy" pattern (used for Story 1.3 commits `c7b88a8`, `4cb1b12`,
`9a763ca`, `23051cb`, `ec5c45e`, `bb633df` because WSL2 lacked the toolchain
at that point) is retired.

Windows host git remains **banned as a commit origin** until Story 1.7
configures SSH signing there, because `required_signatures: true` rejects
unsigned commits at push time.

### Self-Hosted Runner Bootstrap (Task 1 — Khuk0 manual)

Run the following inside the WSL2 Ubuntu 24.04 shell. Replace `<TOKEN>` with
the one-time registration token displayed at `GitHub → Settings → Actions →
Runners → New self-hosted runner → Linux / x64`. **Never** paste the token
into git history, chat logs, or this file — it is a 15-minute credential and
remains out of repo storage (NFR-S1, Story 1.2 AC-3).

```bash
mkdir -p ~/actions-runner && cd ~/actions-runner
# Pin to the latest 2.322+ GA release listed on
# https://github.com/actions/runner/releases
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.322.0/actions-runner-linux-x64-2.322.0.tar.gz
tar xzf actions-runner-linux-x64.tar.gz
./config.sh \
  --url https://github.com/<OWNER>/invest_training \
  --token <TOKEN> \
  --labels self-hosted,trading-pc,wsl2-ubuntu-24.04 \
  --name athena-trading-pc \
  --work _work \
  --unattended \
  --replace

# System-level systemd unit (Task 1.3 Change Log — chosen over user-level for
# boot-from-cold independence of login session). `svc.sh install` with `sudo`
# writes the unit under `/etc/systemd/system/` and starts it as root-launched
# service running as Khuk0. The `loginctl enable-linger` below is kept as a
# belt-and-braces no-op for any future revert to user-scope.
sudo loginctl enable-linger khuk0
sudo ./svc.sh install khuk0
sudo ./svc.sh start
sudo systemctl status 'actions.runner.*.service'

chmod 600 ~/actions-runner/.runner \
          ~/actions-runner/.credentials \
          ~/actions-runner/.credentials_rsaparams
ls -la ~/actions-runner/.credentials   # expect -rw-------
```

Verification artefacts (to be pasted here once Khuk0 completes the bootstrap):

- `gh api repos/<OWNER>/invest_training/actions/runners` JSON (name, labels,
  status=`online`).
- `sudo systemctl status actions.runner.<OWNER>-invest_training.athena-trading-pc.service`
  showing `active (running)` after a `wsl --shutdown` reboot.
- Confirmation that the token value has been discarded (not stored anywhere).

### 7-Stage Workflow Architecture (Task 2 — landed)

`.github/workflows/ci.yml` (workflow name `ci-7-stage`) defines the 7-stage
pipeline described above. Real-PR verification on the self-hosted runner is
deferred until the runner is registered (Task 2.6). When Khuk0 opens the first
PR against `master`, capture the `gh run view <RUN_ID>` output or the Actions
URL and paste it here as evidence that stage-1 through stage-7 went green on
the self-hosted runner.

### Policy Cooling + Paper Replay Marker Gates (Task 4 — landed)

Both scripts live under `scripts/` and exit 0 on non-policy HEAD commits. On a
`policy:`-prefixed HEAD:

- `scripts/check_cooling.py` rejects the commit when fewer than 72h have
  elapsed since the previous `policy:` merge (`POLICY_NOT_COOLED` JSON on
  stderr).
- `scripts/check_paper_replay_marker.py` rejects the commit when the
  lightweight tag `paper-replay-ok/<short_sha>` is missing
  (`PAPER_REPLAY_MISSING` JSON on stderr).

#### Story 1.3 Task 4.6 — Paper Replay Marker (temporary manual workflow)

Until Epic 8 Story 8.5 publishes the marker automatically, developers create
the tag locally after a successful paper replay:

```bash
git tag paper-replay-ok/$(git rev-parse --short HEAD) HEAD
git push origin "paper-replay-ok/$(git rev-parse --short HEAD)"
```

Tag shape is lightweight (not annotated) so it does not collide with
`tag.gpgsign=true`. During Story 1.3 validation keep the tag local only and
delete it after the smoke run so the remote repo is not polluted with test
markers.

### Branch Protection Baseline (Task 5 — Khuk0 manual apply pending)

1. `gh auth status` — confirm `gh` is authenticated with a PAT that carries
   the `repo` scope. PAT storage: OS Keychain only (NFR-S1). `.env` storage
   is banned.
2. Execute `OWNER=<github-owner> bash scripts/setup_branch_protection.sh`.
   The script runs an idempotent `gh api -X PUT` on
   `/repos/<owner>/invest_training/branches/master/protection` and writes
   the resulting config JSON to `infra/github/branch_protection.json`.
3. `git add infra/github/branch_protection.json && git commit -S -m "feat(ci): branch protection + required signatures on master (Story 1.3 AC-5)"`
   — this is the first commit after `required_signatures=true` is active;
   it must be signed from WSL2.
4. Protected-push dry-run:

   ```bash
   git push origin master
   # expected: remote: error: GH006: Protected branch update failed ...
   ```

5. Signed-commit enforcement capture — attempt to push an unsigned commit
   from Windows Git Bash (deferred to Story 1.7 fully). Paste the
   "Commits must have verified signatures" rejection here once observed.

### Policy Commit End-to-End (Task 6 — partial, manual verification pending)

`config/policy.toml` is the scaffolded placeholder. The `policy-prefix-guard`
commit-msg hook is registered in `.pre-commit-config.yaml`. To activate it
locally, run:

```bash
uv run pre-commit install --hook-type commit-msg
```

End-to-end smoke (Khuk0 captures the terminal transcript here when running):

1. Edit `config/policy.toml`, `git add`, then `git commit -m "feat: adjust"`
   — expect the hook to reject.
2. Retry with `git commit -m "policy: smoke-test adjustment"` — hook passes,
   signature applied.
3. Push, open PR, observe CI: stages 1-5 green, stage-6 passes via the
   genesis path (no prior `policy:` merge), stage-7 rejects with
   `PAPER_REPLAY_MISSING`.
4. Run the manual tag command from Task 4.6 above, re-run the workflow,
   stage-7 turns green.
5. Merge, confirm `git log --show-signature HEAD` on `master` shows the
   SSH signature.

Delete the temporary `paper-replay-ok/*` tag after the smoke run completes.

## Story 1.4 — DuckDB + Parquet Shard + rsync Data Pipeline

### Logger PC `features_logger.duckdb` Initialisation (one-time)

Run once on Logger PC after Story 1.7 brings the host online:

```bash
uv run python -c "\
from pathlib import Path; \
from athena.feature_store.duckdb_client import open_logger_duckdb; \
from athena.feature_store.schemas import (\
create_ticks_table, create_quotes_table, create_news_table); \
conn = open_logger_duckdb(Path('data/duckdb/features_logger.duckdb')); \
create_ticks_table(conn); create_quotes_table(conn); create_news_table(conn); \
print('initialized')"
```

### Hourly Parquet Shard Export Schedule (Logger PC)

Logger PC runs Windows 11; use NSSM-wrapped scheduled task or Task
Scheduler. Recommended cron expression (UTC): `0 1 * * * *` (every hour at
minute 01, gives the logger 60s slack to flush the prior hour before
export). Command:

```
uv run python scripts/export_parquet_shard.py \
  --duckdb data/duckdb/features_logger.duckdb \
  --out-root data/parquet \
  --hour now-1
```

Exit 0 is success (per-table file count emitted on stdout as JSON). Exit 1
with stderr `error_code=SHARD_ALREADY_EXISTS` means the export was retried
against an already-written hour (architecture invariant — don't force; use
`--check-only` to verify data identity instead).

### Trading PC `athena-logger-sync.timer` Installation

Normal install (Logger PC reachable):

```bash
bash scripts/install_logger_sync_unit.sh
```

Dry run (Logger PC absent — W1 Day 1 through end of Story 1.7):

```bash
DRY_RUN=1 bash scripts/install_logger_sync_unit.sh
```

Before running the normal install, add to `~/.ssh/config`:

```
Host logger-pc
  HostName 192.168.1.<LOGGER_IP>
  User khuk0
  IdentityFile ~/.ssh/id_ed25519_athena_sync
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
  Compression yes
```

Generate a **separate** sync key (not the signing key — NFR-S2 mandates
separation):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_athena_sync -N "" \
  -C "athena-sync@trading-pc"
ssh-copy-id -i ~/.ssh/id_ed25519_athena_sync.pub logger-pc
ssh logger-pc 'echo ok'  # must pass without password prompt
```

### rsync Lag Alert Diagnostic Procedure

When Alertmanager pages `LoggerSyncLagHigh` (lag > 120s), the on-call runs
these five checks in order — each is cheap and narrows the cause fast:

1. **Logger PC reachability** — `ping -c 3 logger-pc` from Trading PC.
2. **SSH path** — `ssh logger-pc 'echo ok'` — checks key + authorized_keys
   + sshd on Logger PC.
3. **systemd journal** —
   `journalctl -u athena-logger-sync.service --since '5 min ago'` —
   look for `Permission denied`, `Host key verification failed`,
   `Connection timed out`, or non-zero rsync exit codes.
4. **Manual dry-run rsync** —
   `rsync -avn --timeout=10 logger-pc:/data/parquet/ /data/parquet/` —
   confirms the pipeline works interactively even if systemd's unit
   environment is stale.
5. **Disk free space** — `df -h /data` — a full destination filesystem
   produces exit 12 even when SSH is fine.

### Trading PC Write-Scope Invariant

Trading PC writes ONLY to these five `decisions.duckdb` tables:

- `modules_output` — Story 1.5 (Pre-Trade Ledger)
- `decisions` — Story 1.5
- `orders` — Story 4.3
- `anti_ego_events` — Story 3.1
- `labels_f1` — Story 3.3

`ticks` / `quotes` / `news` are Logger PC's exclusive writer zone; Trading
PC reads them via Parquet external scan (`parquet_reader.attach_parquet_views`).
Defenders:

- `tests/regression/test_trading_pc_write_scope.py` — introspects
  `FeatureStore` for exactly five `insert_*` methods and greps
  `feature_query.py` for any forbidden INSERT against Logger tables.

Any reviewer considering adding a sixth `insert_*` must update both the
invariant test's expected set AND Source-of-Truth Invariant #3 in the
story file.
