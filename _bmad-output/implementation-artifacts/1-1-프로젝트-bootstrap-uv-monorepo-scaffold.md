# Story 1.1: 프로젝트 Bootstrap — uv Monorepo Scaffold

Status: in-progress

Epic: 1 — Foundation & Market Truth Capture
Story Key: `1-1-프로젝트-bootstrap-uv-monorepo-scaffold`
FR Coverage (direct): NFR-A5, NFR-M1, NFR-M2, NFR-M3 의 물리 구현
AR Coverage (direct): AR-ST1~4, AR-BND1~2, AR-COM4, AR-CFG5, AR-SEC1 (placeholder), AR-TEST1~2·TEST5, AR-CQ1~5

## Story

As a Developer (Khuk0, Week 1 Day 1),
I want to initialize the Athena monorepo with `uv` workspace + 6 package skeletons + toolchain enforcement (import-linter, pre-commit, mypy strict, Hatchling build-time git SHA injection),
so that every subsequent story is built on a reproducible, audit-compliant, layer-enforced foundation where `policy_version_git_sha` injection, Pydantic DTO 3-field contract, and forbidden-API lint rules are physically enforced from the first line of code.

## Acceptance Criteria

**AC-1: 6-Package Scaffold** [Source: epics.md#Story-1.1 (lines 432-435), architecture.md#AR-ST1-2 (lines 171-172), architecture.md#Structure-Patterns (lines 441-465)]

**Given** an empty git repository on the Windows 11 host
**When** `uv init --package athena --python 3.13` is executed at repo root **and** the 6-package scaffold is created manually
**Then** `packages/athena-core/`, `packages/athena-feature-store/`, `packages/athena-alpha-defense/`, `packages/athena-ops-defense/`, `packages/athena-orchestrator/`, `packages/athena-execution/` each exist with their own `pyproject.toml` at `version = "0.1.0"` (semver, NFR-M2)
**And** each package directory contains `athena/<context>/__init__.py` and a co-located `tests/` subdirectory with at least one passing smoke test (`tests/test_smoke.py::test_import`) [AR-TEST5]
**And** the workspace root `pyproject.toml` declares all 6 packages under `[tool.uv.workspace] members = ["packages/*"]`
**And** `.python-version` pins to `3.13`

**AC-2: Dependency Lock & Import Smoke** [Source: epics.md#Story-1.1 (lines 437-440), architecture.md#AR-ST3-4 (lines 173-174)]

**Given** the 6-package scaffold is complete
**When** the following are executed at the workspace root:
  - `uv add python-kis polars duckdb pydantic uvloop keyring pydantic-settings`
  - `uv add --dev pytest pytest-asyncio pytest-xdist ruff mypy pre-commit import-linter`
**Then** `uv.lock` is generated at workspace root and is committed to git (NFR-A5 감사 요건의 물리 구현)
**And** `uv run python -c "import athena.core, athena.feature_store, athena.alpha_defense, athena.ops_defense, athena.orchestrator, athena.execution"` succeeds with exit code 0
**And** `uv sync` from a fresh clone reproduces the lockfile state identically (checksum match)

**AC-3: Import-Linter Layer Enforcement** [Source: epics.md#Story-1.1 (lines 442-445), architecture.md#AR-BND1-2 (lines 213-214), architecture.md#Architectural-Boundaries (lines 895-914)]

**Given** `.importlinter` config at workspace root declaring the layered architecture
**When** `uv run lint-imports` executes (and runs as a CI step)
**Then** the following import hierarchy is enforced — violations FAIL the command:
  - Layer order (one-way only): `athena.core` ← `athena.feature_store` ← {`athena.alpha_defense` ∥ `athena.ops_defense`} ← `athena.orchestrator` ← `athena.execution`
**And** each of the following reverse imports is explicitly forbidden by a dedicated `forbidden` contract with a specific violation message:
  - `athena.execution` → `athena.orchestrator`
  - `athena.alpha_defense` → `athena.execution`
  - `athena.ops_defense` → `athena.execution`
  - `athena.core` → any other `athena.*` package
**And** two negative regression tests (`tests/regression/test_import_linter_contracts.py`) assert that deliberately added illegal imports (a) get detected by `lint-imports`, (b) the tests then remove them — verifying the enforcement actually fires rather than silently passing

**AC-4: Pre-Commit Hook Chain (4 hooks minimum)** [Source: epics.md#Story-1.1 (lines 447-450), architecture.md#Pattern-Enforcement (lines 596-606), architecture.md#AR-CQ1-5 (lines 261-265)]

**Given** `.pre-commit-config.yaml` installed at workspace root
**When** `git commit` is invoked on any change
**Then** the following hooks run in order and block the commit on any failure:
  1. **ruff** — `ruff check` (rule sets: `E,F,I,N,UP,B,S,TID`) + `ruff format --check`
  2. **mypy** — `mypy --strict` on all `packages/*/athena/**/*.py`
  3. **secret scanner** — `detect-private-key` + `detect-secrets` (or `gitleaks-lite` equivalent) on staged diff
  4. **standard hygiene** — `check-yaml`, `check-toml`, `check-merge-conflict`, `end-of-file-fixer`, `trailing-whitespace`
**And** ruff config explicitly forbids these imports via `[tool.ruff.lint.flake8-tidy-imports.banned-api]`:
  - `pandas` → "Polars only per architecture.md#Enforcement-Guidelines #3"
  - `requests` / `urllib.request` → "httpx.AsyncClient only per architecture.md#Enforcement-Guidelines #4"
**And** ruff config forbids `datetime.datetime.now` without `tz=` via a custom check or `flake8-datetimez`-equivalent rule → "naive datetime forbidden per architecture.md#Enforcement-Guidelines #6"
**And** `pre-commit run --all-files` succeeds on a freshly scaffolded repo (baseline green)

**AC-5: Hatchling Build Hook — git SHA Injection** [Source: epics.md#Story-1.1 (lines 452-455), architecture.md#AR-COM4/D15 (lines 208, 328), architecture.md#Build-Process (line 1112)]

**Given** a Hatchling custom build hook implemented at `packages/athena-core/hatch_build.py`
**When** `uv build packages/athena-core` (or `hatch build`) is executed for any package
**Then** the build hook executes `git describe --always --dirty` at build time (not runtime) and writes the result into `packages/athena-core/athena/core/_version.py` with the structure:

```python
# AUTO-GENERATED by hatch_build.py — DO NOT EDIT
__commit__: str = "<git-describe-output>"       # e.g., "a3f2d1c" or "a3f2d1c-dirty"
__build_time_utc__: str = "<iso8601>"
```

**And** `athena.core.version` (hand-written, not auto-generated) exposes `POLICY_VERSION_SHA: str = _version.__commit__` and `MODULE_VERSION: str = "<package_semver>+<git_sha8>"`
**And** `athena.core.version` **never** calls `subprocess`, `os.popen`, or shell at runtime — enforced by a unit test asserting the module has no `subprocess`/`os.popen`/`os.system` references (AR-COM4 "런타임 shell 호출 overhead 0")
**And** `_version.py` is listed in `.gitignore` (generated artifact, not source)

## Tasks / Subtasks

Execute **in order**. Mark each `[x]` only when both implementation and tests pass. Run the full test suite (`uv run pytest`) after each task — never proceed with failing tests.

- [ ] **Task 1: uv workspace root initialization** (AC: 1)
  - [ ] 1.1 Install uv 0.11.7+ on Windows 11 host (PowerShell: `irm https://astral.sh/uv/install.ps1 | iex`). Record version in `docs/operating_playbook.md` (create empty stub if missing).
  - [ ] 1.2 Run `uv init --package athena --python 3.13` at `C:\Users\khuk0\vibe\invest_training`. This creates root `pyproject.toml`, `.python-version`, `src/athena/` initial layout.
  - [ ] 1.3 Delete the default `src/athena/` folder created by `uv init` — we replace it with the 6-package `packages/` layout. Keep only root `pyproject.toml`, `.python-version`, `README.md`.
  - [ ] 1.4 Edit root `pyproject.toml`: remove `[project]` block; keep only `[tool.uv.workspace] members = ["packages/*"]` and `[tool.uv.sources]` mapping each of the 6 packages to `{ workspace = true }`. Set `requires-python = ">=3.13,<3.14"` at workspace level.
  - [ ] 1.5 Add `.gitignore` entries for `.venv/`, `__pycache__/`, `*.egg-info/`, `dist/`, `build/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `packages/*/athena/*/_version.py`, `data/`, `.env*` (defensive — `.env` is forbidden anyway per NFR-S1).
  - [ ] 1.6 Commit: `chore: initialize uv workspace root (Story 1.1 Task 1)`.

- [ ] **Task 2: Scaffold 6 packages with independent pyproject.toml** (AC: 1)
  - [ ] 2.1 Create directories per architecture.md#Structure-Patterns (lines 441-465):
    - `packages/athena-core/athena/core/__init__.py`
    - `packages/athena-feature-store/athena/feature_store/__init__.py`
    - `packages/athena-alpha-defense/athena/alpha_defense/__init__.py`
    - `packages/athena-ops-defense/athena/ops_defense/__init__.py`
    - `packages/athena-orchestrator/athena/orchestrator/__init__.py`
    - `packages/athena-execution/athena/execution/__init__.py`
  - [ ] 2.2 For each package, create `pyproject.toml` with:
    - `[project] name = "athena-<context>"`, `version = "0.1.0"`, `requires-python = ">=3.13,<3.14"`
    - `[build-system] requires = ["hatchling"], build-backend = "hatchling.build"`
    - `[tool.hatch.build.targets.wheel] packages = ["athena"]` (namespace package layout)
    - `[project.dependencies]` — athena-core has no athena-* deps; all others declare `athena-core` via `[tool.uv.sources]` workspace dep; layering follows AR-BND1 (AC-3). Example for athena-feature-store: `dependencies = ["athena-core"]`. For athena-orchestrator: `dependencies = ["athena-core", "athena-feature-store", "athena-alpha-defense", "athena-ops-defense"]`.
  - [ ] 2.3 Create `packages/<pkg>/tests/__init__.py` and `packages/<pkg>/tests/test_smoke.py` with a single test asserting `import athena.<context>` succeeds. Co-located per AR-TEST5.
  - [ ] 2.4 Run `uv sync` → must install all 6 packages in editable mode. Run `uv run pytest packages/` → all smoke tests pass.
  - [ ] 2.5 Commit: `chore(scaffold): create 6-package monorepo layout (Story 1.1 Task 2)`.

- [ ] **Task 3: Add core dependencies and generate uv.lock** (AC: 2)
  - [ ] 3.1 Add runtime deps at workspace root: `uv add python-kis polars duckdb pydantic uvloop keyring pydantic-settings`. Verify each resolves to its latest stable compatible with Python 3.13.
  - [ ] 3.2 Add dev deps: `uv add --dev pytest pytest-asyncio pytest-xdist ruff mypy pre-commit import-linter`.
  - [ ] 3.3 Verify `uv.lock` is created at workspace root; commit it with message `chore(deps): add MVP Tier-1 dependencies + dev toolchain, lock uv.lock (NFR-A5)`.
  - [ ] 3.4 Implement integration smoke test `tests/integration/test_scaffold_imports.py`:
    - Import each of the 6 `athena.*` submodules (must not raise).
    - Import `polars`, `duckdb`, `pydantic`, `uvloop`, `keyring`, `pydantic_settings` (must not raise).
    - Assert `sys.version_info[:2] == (3, 13)`.
    - Assert `uv` is resolvable via `shutil.which("uv") is not None`.
  - [ ] 3.5 Run `uv run python -c "import athena.core, athena.feature_store, athena.alpha_defense, athena.ops_defense, athena.orchestrator, athena.execution"` → exit 0. Record output in `docs/operating_playbook.md` under "Week 1 Day 1 verification".

- [ ] **Task 4: athena-core skeleton — BaseDTO, ErrorCode, version stubs** (AC: 2, 5)
  - [ ] 4.1 Create `packages/athena-core/athena/core/dto.py` with `BaseDTO(BaseModel)` declaring the 3 mandatory fields: `timestamp: datetime` (UTC aware, strict validator that rejects naive), `module_version: str` (regex `^M\d+\.v\d+\.\d+\.\d+$|^[a-z_-]+\.v\d+\.\d+\.\d+$`), `policy_version_git_sha: str` (regex `^[0-9a-f]{7,40}(-dirty)?$`). Include a docstring citing architecture.md#Format-Patterns and NFR-M1. Use `model_config = ConfigDict(frozen=True, strict=True, extra="forbid")`.
  - [ ] 4.2 Create `packages/athena-core/athena/core/errors.py` with `ErrorCode(StrEnum)` exactly as architecture.md#D14 (lines 314-325) — **do not add or rename values in this story**. Add `class AthenaError(Exception)` base + `class MissingSecretError(AthenaError)` (used by Story 1.2).
  - [ ] 4.3 Create `packages/athena-core/athena/core/version.py` (hand-written) that imports from `._version` (generated) and exposes `POLICY_VERSION_SHA`, `MODULE_VERSION`. Provide a default fallback `"unknown-dev"` when `_version.py` is missing (only hit during bare `uv run` before first build — document this).
  - [ ] 4.4 Create `packages/athena-core/athena/core/time.py` with `def kst_to_utc(dt)` and `def utc_to_kst(dt)` using `zoneinfo.ZoneInfo("Asia/Seoul")`. Both raise `ValueError` on naive input. (Full timezone utilities belong to downstream stories; these stubs unblock DTO validators.)
  - [ ] 4.5 Unit tests `packages/athena-core/tests/test_dto.py`:
    - `BaseDTO` rejects naive datetime (raises `ValidationError`).
    - `BaseDTO` rejects malformed `module_version` / `policy_version_git_sha`.
    - `BaseDTO` accepts valid UTC-aware + semver + 40-char sha.
    - `frozen=True` prevents mutation.
  - [ ] 4.6 Unit test `packages/athena-core/tests/test_errors.py`: all 8 ErrorCode members present and string-valued.
  - [ ] 4.7 Unit test `packages/athena-core/tests/test_version_no_shell.py`: AST-parse `athena/core/version.py`, assert no `Import`/`ImportFrom` of `subprocess`, `os.popen`, `os.system`, `shutil` (this enforces AR-COM4 "런타임 shell 호출 overhead 0" — AC-5).
  - [ ] 4.8 Commit: `feat(core): BaseDTO, ErrorCode, version stubs with 3-field contract enforcement`.

- [ ] **Task 5: Hatchling build hook — git SHA injection** (AC: 5)
  - [ ] 5.1 Create `packages/athena-core/hatch_build.py` implementing `class CustomBuildHook(BuildHookInterface)`. In `initialize(self, version, build_data)`:
    - Run `subprocess.run(["git", "describe", "--always", "--dirty"], capture_output=True, text=True, check=False)`; fall back to `"unknown-dev"` if git missing or repo absent (supports tarball builds).
    - Capture `datetime.now(UTC).isoformat()`.
    - Write to `athena/core/_version.py` with the exact format shown in AC-5.
  - [ ] 5.2 Register the hook in `packages/athena-core/pyproject.toml`:
    ```toml
    [tool.hatch.build.hooks.custom]
    path = "hatch_build.py"
    ```
  - [ ] 5.3 Confirm `packages/athena-core/athena/core/_version.py` is in root `.gitignore` (added in Task 1.5 — verify).
  - [ ] 5.4 Integration test `packages/athena-core/tests/test_hatch_hook.py`:
    - Run `uv build packages/athena-core` in a subprocess (pytest tmp_path fixture).
    - Unpack the produced wheel, assert `_version.py` exists inside and contains `__commit__` matching `^[0-9a-f]{7,40}(-dirty)?$|^unknown-dev$`.
    - Assert `__build_time_utc__` parses as ISO 8601 UTC.
  - [ ] 5.5 Commit: `feat(build): Hatchling hook injects git sha into athena.core._version (AR-COM4)`.

- [ ] **Task 6: import-linter contracts** (AC: 3)
  - [ ] 6.1 Create `.importlinter` at workspace root with contracts:
    ```ini
    [importlinter]
    root_packages =
        athena.core
        athena.feature_store
        athena.alpha_defense
        athena.ops_defense
        athena.orchestrator
        athena.execution

    [importlinter:contract:layers]
    name = Athena layer order
    type = layers
    layers =
        athena.execution
        athena.orchestrator
        athena.alpha_defense | athena.ops_defense
        athena.feature_store
        athena.core

    [importlinter:contract:core-leaf]
    name = athena.core is a leaf (no athena.* deps)
    type = forbidden
    source_modules = athena.core
    forbidden_modules = athena.feature_store, athena.alpha_defense, athena.ops_defense, athena.orchestrator, athena.execution

    [importlinter:contract:execution-no-orchestrator]
    name = execution MUST NOT import orchestrator
    type = forbidden
    source_modules = athena.execution
    forbidden_modules = athena.orchestrator

    [importlinter:contract:alpha-no-execution]
    name = alpha_defense MUST NOT import execution
    type = forbidden
    source_modules = athena.alpha_defense
    forbidden_modules = athena.execution

    [importlinter:contract:ops-no-execution]
    name = ops_defense MUST NOT import execution
    type = forbidden
    source_modules = athena.ops_defense
    forbidden_modules = athena.execution
    ```
  - [ ] 6.2 Run `uv run lint-imports` on the clean scaffold → all contracts PASS (baseline green).
  - [ ] 6.3 Regression test `tests/regression/test_import_linter_contracts.py` — use pytest parametrize to verify `lint-imports` FAILs with the expected contract name when an illegal import is temporarily injected in a pytest tmp_path copy of the repo; assert the original repo still passes. Do **not** modify the real source tree.
  - [ ] 6.4 Commit: `feat(ci): import-linter contracts enforce AR-BND1/BND2 layer hierarchy`.

- [ ] **Task 7: ruff + mypy + pre-commit hooks** (AC: 4)
  - [ ] 7.1 Add `[tool.ruff]` to root `pyproject.toml`:
    - `target-version = "py313"`, `line-length = 100`
    - `[tool.ruff.lint] select = ["E","F","I","N","UP","B","S","TID","DTZ"]` (DTZ = flake8-datetimez, catches naive datetime per Enforcement #6)
    - `[tool.ruff.lint.flake8-tidy-imports.banned-api]` mapping: `pandas` → msg cite Enforcement #3; `requests` → cite Enforcement #4; `urllib.request` → cite Enforcement #4.
    - `[tool.ruff.format] quote-style = "double"`.
  - [ ] 7.2 Add `[tool.mypy]` to root `pyproject.toml`: `strict = true`, `python_version = "3.13"`, `mypy_path = "packages/athena-core:packages/athena-feature-store:..."` (all 6), `plugins = ["pydantic.mypy"]`.
  - [ ] 7.3 Create `.pre-commit-config.yaml` with hook repos:
    - `astral-sh/ruff-pre-commit` (pinned version matching dev dep) — `ruff check --fix` + `ruff format`
    - `pre-commit/mirrors-mypy` — `mypy --strict`, `additional_dependencies = [pydantic, pydantic-settings]`
    - `Yelp/detect-secrets` OR `gitleaks/gitleaks` — scan staged diff
    - `pre-commit/pre-commit-hooks` — `check-yaml`, `check-toml`, `check-merge-conflict`, `end-of-file-fixer`, `trailing-whitespace`, `detect-private-key`
  - [ ] 7.4 Run `uv run pre-commit install` (installs `.git/hooks/pre-commit`). Commit the `.pre-commit-config.yaml` and pinned `.pre-commit-hooks` lockfile-equivalent.
  - [ ] 7.5 Run `uv run pre-commit run --all-files` → all hooks pass on clean scaffold (baseline green). Expect zero auto-fix diff after the run.
  - [ ] 7.6 Regression test `tests/regression/test_ruff_bans.py`:
    - Create tmp_path file with `import pandas` → `ruff check` must emit `TID` code pointing to Enforcement #3 msg.
    - Create tmp_path file with `import requests` → must emit ban on Enforcement #4 msg.
    - Create tmp_path file with `from datetime import datetime; datetime.now()` → must emit `DTZ` code.
  - [ ] 7.7 Commit: `feat(ci): pre-commit hook chain (ruff+mypy+secrets) with architecture bans`.

- [ ] **Task 8: GitHub Actions CI — smoke gate** (AC: 3, 4, partial AR-INF4)
  - [ ] 8.1 Create `.github/workflows/ci.yml` with a single job `scaffold-gate` on `ubuntu-latest` (self-hosted runner per AR-INF3 is a Story 1.3 concern — this story only sets the file, Story 1.3 migrates `runs-on` to `self-hosted` and adds the 7-stage pipeline):
    - Step: checkout (`fetch-depth: 0` so `git describe` works in Task 5 hook)
    - Step: install uv (`astral-sh/setup-uv@v3`, pin the version)
    - Step: `uv sync --frozen`
    - Step: `uv run pre-commit run --all-files`
    - Step: `uv run lint-imports`
    - Step: `uv run pytest -n auto` (pytest-xdist parallel)
  - [ ] 8.2 Document in `docs/operating_playbook.md` that Story 1.3 will (a) migrate to `runs-on: [self-hosted, trading-pc]`, (b) add snapshot regression / 72h cooling / Paper gates. This story's CI is a **scaffold baseline**, not the full 7-stage pipeline.
  - [ ] 8.3 Commit: `ci: scaffold-gate workflow (ruff, mypy, import-linter, pytest) — self-hosted migration deferred to Story 1.3`.

- [ ] **Task 9: Final verification and sprint handoff** (AC: 1-5)
  - [ ] 9.1 From a fresh clone (simulate via `git clone . ../_verify`), run: `uv sync --frozen && uv run pytest && uv run pre-commit run --all-files && uv run lint-imports && uv build packages/athena-core`. All must succeed on first attempt. Record the run log in the Dev Agent Record § Debug Log References.
  - [ ] 9.2 Update `README.md` with a 10-line "Quick Start" section citing `uv sync && uv run pytest` and pointing to `docs/operating_playbook.md` for full ops procedures.
  - [ ] 9.3 Populate File List in Dev Agent Record below.
  - [ ] 9.4 Final commit: `chore(story-1.1): scaffold verification passed, hand off to Story 1.2`. **Do not** prefix with `policy:` — this is scaffold work, not a policy change (NFR-M3 / Change Control does not apply).

## Dev Notes

### Source-of-Truth Invariants (freeze these on Day 1 — downstream stories depend on them)

1. **DTO 3-field contract** [architecture.md#Format-Patterns lines 476-491, NFR-M1]
   Every Pydantic DTO created in any future story **MUST** inherit from `athena.core.dto.BaseDTO` which provides `timestamp` (UTC-aware), `module_version` (semver), `policy_version_git_sha` (40-char hex). Enforcement via ruff custom rule is a Story-1.3 concern; in this story we only land the base class and reject naive datetime at validator level.

2. **Error taxonomy locked** [architecture.md#D14 lines 314-325]
   The 8 `ErrorCode` values `KIS_RATE_LIMIT`, `FEATURE_MISSING`, `LLM_TIMEOUT`, `CONFIDENCE_BELOW_THRESHOLD`, `DATA_STALE`, `HEARTBEAT_LOST`, `SLIPPAGE_EXCEEDED`, `POLICY_NOT_COOLED` are frozen. Adding values = Change Control (NFR-M3, max 1 in 12 weeks). Do not anticipate future codes in this story.

3. **Layer hierarchy is one-way** [architecture.md#AR-BND1-2 lines 213-214]
   `core ← feature_store ← {alpha_defense, ops_defense} ← orchestrator ← execution`. The layers contract in `.importlinter` is the single source of truth; the `forbidden` contracts are redundant belt-and-suspenders that produce clearer error messages when violated. Keep both.

4. **`policy_version_git_sha` = product identity** [architecture.md#D15/AR-COM4 lines 208, 328; PRD.md lines 720, 763, 1047]
   Every decision·order·log downstream MUST embed the current git SHA. The Hatchling hook in AC-5 is the ONLY sanctioned source — runtime `subprocess` calls to `git describe` are banned (AR-COM4 "런타임 shell 호출 overhead 0"). The unit test in Task 4.7 enforces this with AST inspection.

5. **`.env` is forbidden forever** [PRD.md NFR-S1 line 1020]
   `.env*` is in `.gitignore` defensively but **the Settings class in Story 1.2 will SystemExit on detecting any `.env` at startup**. Do not create a `.env.example`, `.env.sample`, or equivalent in this story. Secrets go to OS Keychain via `keyring` (Story 1.2).

### Scope Boundaries — Explicitly OUT of Story 1.1

| Out-of-scope item | Belongs to | Reason |
|---|---|---|
| `athena.core.keyring_client`, `athena.core.settings.Settings` | Story 1.2 | WSL2 + OS Keychain + SSH signing infrastructure is the separate story |
| `athena.core.logging` structured JSON logger | Story 1.9 (observability base) | Needs Prometheus + Grafana context |
| `athena.core.flags.FLAG_REGISTRY` (52 flag IDs) | Story 2.1 | Registry content belongs to Epic 2, not scaffold |
| `LedgerClient`, `decisions.duckdb` schema | Stories 1.4 / 1.5 / 6.1 | Separate multi-story thread |
| self-hosted runner migration, 7-stage pipeline | Story 1.3 | CI in this story is scaffold-grade only |
| F5 readonly mount systemd unit | Story 1.6 | OS-layer hardening is a separate story |
| ruff custom rule for "DTO must inherit BaseDTO" | Story 1.3 (alongside full CI) | Requires AST plugin; MVP catches via code review + import-linter |

If tempted to implement anything above during this story: **stop and hand off**. Scope creep on Day 1 cascades.

### Architecture Patterns & Constraints (this story's payload)

- **uv workspace** [architecture.md#Starter-Evaluation lines 137-228, AR-ST1-4]: single `uv.lock`, 6 packages as workspace members, path dep via `[tool.uv.sources]`. **Do not** use PEP 621 multi-project with separate lockfiles — that breaks reproducibility and NFR-A5.
- **Namespace package layout** [architecture.md#Structure-Patterns lines 441-465]: each package uses `packages/athena-<ctx>/athena/<ctx>/` — the top-level `athena/` is a PEP 420 implicit namespace so all 6 packages share it. No `__init__.py` at `packages/athena-<ctx>/athena/` level. The `__init__.py` starts at `athena/<ctx>/`.
- **Python 3.13 only** [architecture.md lines 182-186]: `requires-python = ">=3.13,<3.14"` (not `>=3.11`). uvloop 0.22.1 confirmed 3.13 compatible. python-kis Soju06 confirmed 3.13 compatible. No 3.12 fallback.
- **uvloop is NOT imported in this story** — uvloop installation belongs here (AC-2), but `asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())` wiring belongs to `scripts/orchestrator_daemon.py` (Story 1.7+). Do not add a global import that auto-activates it.
- **Hatchling namespace-package pitfall**: `[tool.hatch.build.targets.wheel] packages = ["athena"]` with `only-include = ["athena/<ctx>"]` is required per package — otherwise Hatchling will try to include the entire namespace `athena/` and collide across packages. Verify the generated wheel for `athena-core` contains only `athena/core/`, not other contexts.

### Testing Standards

- **Framework**: pytest + pytest-asyncio + pytest-xdist [AR-TEST1]
- **Determinism**: all tests must pass with `uv run pytest -p no:randomly` (no hidden test order dependence). Fixed seeds where random is used [AR-TEST2].
- **Layout** [AR-TEST5]:
  - Unit tests: co-located `packages/athena-<ctx>/tests/test_*.py`
  - Integration tests: `tests/integration/` (cross-package)
  - Regression tests: `tests/regression/` (this story seeds `test_import_linter_contracts.py` and `test_ruff_bans.py`)
- **Coverage target**: not enforced in this story. Story 1.3 adds `--cov-fail-under=80` as CI gate.
- **Test naming**: `test_<module>_<behavior>.py::test_<scenario>`, assertive style (no `unittest.TestCase`).
- **No network in unit tests**: any network call (e.g., `git describe` subprocess) runs in `tests/integration/` or `tests/regression/` with a tmp_path git repo fixture.

### Project Structure Notes

The directory tree created by this story is the foundation for stories 1.2 through 8.6. It **must match** architecture.md#Complete-Project-Directory-Structure (lines 667-891) in naming and nesting. Any deviation (e.g., flattening `athena/<ctx>/m1/` into `athena/m1/`) will cascade into dozens of downstream rewrites.

**Deviations from architecture.md NOT permitted in this story:**
- Adding modules under `athena/<ctx>/` beyond `__init__.py` (empty) — those are downstream story payloads
- Creating `config/`, `infra/`, `migrations/`, `data/`, `scripts/`, `dashboards/` directories — each has a dedicated story
- Writing any DuckDB or Parquet code — Stories 1.4, 1.5, 1.7

**Deviations from architecture.md permitted (note in Dev Agent Record):**
- `docs/operating_playbook.md` may be created as a stub in Task 1.1 if not already present — the full playbook is populated across multiple stories.
- `README.md` Quick Start section in Task 9.2 is scaffold-level only; full README polish is Story 1.9 or 7.x.

### Previous Story Intelligence

**None — this is the first story of Epic 1 and of the entire project.** There is no previous story to learn from. The `initial commit` on branch `master` (commit `17b61cf`) is the BMAD planning bootstrap (adds `.gitignore` + `_bmad/`); it is **not** a scaffold precedent. Start Task 1 from a clean working tree.

### Git Intelligence Summary

Only one commit exists on `master`: `17b61cf Initial commit`. Working tree currently has untracked `.gitignore` and `_bmad/`. Recommendation: before Task 1.2 runs `uv init` (which generates files), stash or commit the planning artifacts explicitly so that any `uv init` diff is attributable. No policy-change commits, no past scaffold attempts — clean slate.

### Latest Tech Information

All versions are already fixed by the architecture. Do **not** "research latest" and bump versions in this story — that is a future Story 8.x model-lifecycle concern. Versions to use as of 2026-04-21:

| Package | Target version | Source of truth |
|---|---|---|
| Python | 3.13 (any patch) | architecture.md line 183 |
| uv | 0.11.7+ | architecture.md line 192 |
| uvloop | 0.22.1 | architecture.md line 188 |
| Pydantic | 2.x (latest 2.x) | architecture.md line 187 |
| pydantic-settings | 2.x | architecture.md line 222 |
| python-kis (Soju06) | latest 3.13-compatible | architecture.md line 185 |
| polars, duckdb | latest stable | no version pin beyond major |
| pytest, pytest-asyncio, pytest-xdist | latest stable | AR-TEST1 |
| ruff | latest (use py313 target) | AR-CQ1 |
| mypy | latest | AR-CQ3 |
| pre-commit | latest | AR-CQ4 |
| import-linter | latest | AR-BND1 |
| Hatchling | latest (uv default) | architecture.md line 199 |

`uv.lock` (committed in Task 3.3) is the binding source of truth after this story. Any version bump requires a dedicated story.

### References

- **Epic + Story source**: `_bmad-output/planning-artifacts/epics.md#Epic-1 (line 420)`, `#Story-1.1 (lines 424-456)`
- **Architecture Step 1 — Starter Evaluation**: `_bmad-output/planning-artifacts/architecture.md#Starter-Template-Evaluation (lines 121-228)`
- **Architecture Step 2 — Decisions**: `architecture.md#AR-ST1-4 (lines 171-174)`, `#AR-BND1-2 (lines 213-214)`, `#AR-COM4 (line 208)`, `#AR-CFG5 (line 222)`, `#AR-TEST1-5 (lines 253-257)`, `#AR-CQ1-5 (lines 261-265)`
- **Architecture Step 3 — Patterns**: `architecture.md#Implementation-Patterns (lines 399-663)` — specifically naming (405-437), structure (439-472), format (474-533), communication (535-551), process (553-581), enforcement (583-606), examples (608-663)
- **Architecture Step 4 — Structure**: `architecture.md#Complete-Project-Directory-Structure (lines 667-891)`, `#Architectural-Boundaries (lines 893-914)`
- **PRD sources**: `prd.md#NFR-S1 (line 1020)` `.env` 금지, `#NFR-A5 (line 1051)` git signed commit audit, `#NFR-M1-3 (lines 1055-1057)` DTO + semver + Change Control, `#PT-I1 (line 794)` monorepo 구조, `#PT-I2 (line 799)` 테스트 전략
- **Implementation Readiness Report**: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-21.md` — READY verdict, no Critical/Major gaps

## Dev Agent Record

### Agent Model Used

`<to be filled by dev agent — e.g., claude-opus-4-7[1m]>`

### Debug Log References

### Completion Notes List

### File List

<!-- Populate with ALL files created or modified during implementation, grouped by Task. Example:
Task 1:
- C:\Users\khuk0\vibe\invest_training\pyproject.toml (created)
- C:\Users\khuk0\vibe\invest_training\.python-version (created)
- C:\Users\khuk0\vibe\invest_training\.gitignore (modified)
Task 2:
- packages/athena-core/pyproject.toml (created)
- packages/athena-core/athena/core/__init__.py (created)
- packages/athena-core/tests/test_smoke.py (created)
- ... (5 more packages identically) ...
-->
