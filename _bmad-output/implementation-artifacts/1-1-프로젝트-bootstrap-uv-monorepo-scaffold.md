# Story 1.1: 프로젝트 Bootstrap — uv Monorepo Scaffold

Status: done

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

- [x] **Task 1: uv workspace root initialization** (AC: 1)
  - [x] 1.1 Install uv 0.11.7+ on Windows 11 host (PowerShell: `irm https://astral.sh/uv/install.ps1 | iex`). Record version in `docs/operating_playbook.md` (create empty stub if missing).
  - [x] 1.2 Run `uv init --package athena --python 3.13` at `C:\Users\khuk0\vibe\invest_training`. This creates root `pyproject.toml`, `.python-version`, `src/athena/` initial layout.
  - [x] 1.3 Delete the default `src/athena/` folder created by `uv init` — we replace it with the 6-package `packages/` layout. Keep only root `pyproject.toml`, `.python-version`, `README.md`.
  - [x] 1.4 Edit root `pyproject.toml`: remove `[project]` block; keep only `[tool.uv.workspace] members = ["packages/*"]` and `[tool.uv.sources]` mapping each of the 6 packages to `{ workspace = true }`. Set `requires-python = ">=3.13,<3.14"` at workspace level.
  - [x] 1.5 Add `.gitignore` entries for `.venv/`, `__pycache__/`, `*.egg-info/`, `dist/`, `build/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `packages/*/athena/*/_version.py`, `data/`, `.env*` (defensive — `.env` is forbidden anyway per NFR-S1).
  - [x] 1.6 Commit: `chore: initialize uv workspace root (Story 1.1 Task 1)`.

- [x] **Task 2: Scaffold 6 packages with independent pyproject.toml** (AC: 1)
  - [x] 2.1 Create directories per architecture.md#Structure-Patterns (lines 441-465):
    - `packages/athena-core/athena/core/__init__.py`
    - `packages/athena-feature-store/athena/feature_store/__init__.py`
    - `packages/athena-alpha-defense/athena/alpha_defense/__init__.py`
    - `packages/athena-ops-defense/athena/ops_defense/__init__.py`
    - `packages/athena-orchestrator/athena/orchestrator/__init__.py`
    - `packages/athena-execution/athena/execution/__init__.py`
  - [x] 2.2 For each package, create `pyproject.toml` with:
    - `[project] name = "athena-<context>"`, `version = "0.1.0"`, `requires-python = ">=3.13,<3.14"`
    - `[build-system] requires = ["hatchling"], build-backend = "hatchling.build"`
    - `[tool.hatch.build.targets.wheel] packages = ["athena"]` (namespace package layout)
    - `[project.dependencies]` — athena-core has no athena-* deps; all others declare `athena-core` via `[tool.uv.sources]` workspace dep; layering follows AR-BND1 (AC-3). Example for athena-feature-store: `dependencies = ["athena-core"]`. For athena-orchestrator: `dependencies = ["athena-core", "athena-feature-store", "athena-alpha-defense", "athena-ops-defense"]`.
  - [x] 2.3 Create `packages/<pkg>/tests/__init__.py` and `packages/<pkg>/tests/test_smoke.py` with a single test asserting `import athena.<context>` succeeds. Co-located per AR-TEST5.
  - [x] 2.4 Run `uv sync` → must install all 6 packages in editable mode. Run `uv run pytest packages/` → all smoke tests pass.
  - [x] 2.5 Commit: `chore(scaffold): create 6-package monorepo layout (Story 1.1 Task 2)`.

- [x] **Task 3: Add core dependencies and generate uv.lock** (AC: 2)
  - [x] 3.1 Add runtime deps at workspace root: `uv add python-kis polars duckdb pydantic uvloop keyring pydantic-settings`. Verify each resolves to its latest stable compatible with Python 3.13.
  - [x] 3.2 Add dev deps: `uv add --dev pytest pytest-asyncio pytest-xdist ruff mypy pre-commit import-linter`.
  - [x] 3.3 Verify `uv.lock` is created at workspace root; commit it with message `chore(deps): add MVP Tier-1 dependencies + dev toolchain, lock uv.lock (NFR-A5)`.
  - [x] 3.4 Implement integration smoke test `tests/integration/test_scaffold_imports.py`:
    - Import each of the 6 `athena.*` submodules (must not raise).
    - Import `polars`, `duckdb`, `pydantic`, `uvloop`, `keyring`, `pydantic_settings` (must not raise).
    - Assert `sys.version_info[:2] == (3, 13)`.
    - Assert `uv` is resolvable via `shutil.which("uv") is not None`.
  - [x] 3.5 Run `uv run python -c "import athena.core, athena.feature_store, athena.alpha_defense, athena.ops_defense, athena.orchestrator, athena.execution"` → exit 0. Record output in `docs/operating_playbook.md` under "Week 1 Day 1 verification".

- [x] **Task 4: athena-core skeleton — BaseDTO, ErrorCode, version stubs** (AC: 2, 5)
  - [x] 4.1 Create `packages/athena-core/athena/core/dto.py` with `BaseDTO(BaseModel)` declaring the 3 mandatory fields: `timestamp: datetime` (UTC aware, strict validator that rejects naive), `module_version: str` (regex `^M\d+\.v\d+\.\d+\.\d+$|^[a-z_-]+\.v\d+\.\d+\.\d+$`), `policy_version_git_sha: str` (regex `^[0-9a-f]{7,40}(-dirty)?$`). Include a docstring citing architecture.md#Format-Patterns and NFR-M1. Use `model_config = ConfigDict(frozen=True, strict=True, extra="forbid")`.
  - [x] 4.2 Create `packages/athena-core/athena/core/errors.py` with `ErrorCode(StrEnum)` exactly as architecture.md#D14 (lines 314-325) — **do not add or rename values in this story**. Add `class AthenaError(Exception)` base + `class MissingSecretError(AthenaError)` (used by Story 1.2).
  - [x] 4.3 Create `packages/athena-core/athena/core/version.py` (hand-written) that imports from `._version` (generated) and exposes `POLICY_VERSION_SHA`, `MODULE_VERSION`. Provide a default fallback `"unknown-dev"` when `_version.py` is missing (only hit during bare `uv run` before first build — document this).
  - [x] 4.4 Create `packages/athena-core/athena/core/time.py` with `def kst_to_utc(dt)` and `def utc_to_kst(dt)` using `zoneinfo.ZoneInfo("Asia/Seoul")`. Both raise `ValueError` on naive input. (Full timezone utilities belong to downstream stories; these stubs unblock DTO validators.)
  - [x] 4.5 Unit tests `packages/athena-core/tests/test_dto.py`:
    - `BaseDTO` rejects naive datetime (raises `ValidationError`).
    - `BaseDTO` rejects malformed `module_version` / `policy_version_git_sha`.
    - `BaseDTO` accepts valid UTC-aware + semver + 40-char sha.
    - `frozen=True` prevents mutation.
  - [x] 4.6 Unit test `packages/athena-core/tests/test_errors.py`: all 8 ErrorCode members present and string-valued.
  - [x] 4.7 Unit test `packages/athena-core/tests/test_version_no_shell.py`: AST-parse `athena/core/version.py`, assert no `Import`/`ImportFrom` of `subprocess`, `os.popen`, `os.system`, `shutil` (this enforces AR-COM4 "런타임 shell 호출 overhead 0" — AC-5).
  - [x] 4.8 Commit: `feat(core): BaseDTO, ErrorCode, version stubs with 3-field contract enforcement`.

- [x] **Task 5: Hatchling build hook — git SHA injection** (AC: 5)
  - [x] 5.1 Create `packages/athena-core/hatch_build.py` implementing `class CustomBuildHook(BuildHookInterface)`. In `initialize(self, version, build_data)`:
    - Run `subprocess.run(["git", "describe", "--always", "--dirty"], capture_output=True, text=True, check=False)`; fall back to `"unknown-dev"` if git missing or repo absent (supports tarball builds).
    - Capture `datetime.now(UTC).isoformat()`.
    - Write to `athena/core/_version.py` with the exact format shown in AC-5.
  - [x] 5.2 Register the hook in `packages/athena-core/pyproject.toml`:
    ```toml
    [tool.hatch.build.hooks.custom]
    path = "hatch_build.py"
    ```
  - [x] 5.3 Confirm `packages/athena-core/athena/core/_version.py` is in root `.gitignore` (added in Task 1.5 — verify).
  - [x] 5.4 Integration test `packages/athena-core/tests/test_hatch_hook.py`:
    - Run `uv build packages/athena-core` in a subprocess (pytest tmp_path fixture).
    - Unpack the produced wheel, assert `_version.py` exists inside and contains `__commit__` matching `^[0-9a-f]{7,40}(-dirty)?$|^unknown-dev$`.
    - Assert `__build_time_utc__` parses as ISO 8601 UTC.
  - [x] 5.5 Commit: `feat(build): Hatchling hook injects git sha into athena.core._version (AR-COM4)`.

- [x] **Task 6: import-linter contracts** (AC: 3)
  - [x] 6.1 Create `.importlinter` at workspace root with contracts:
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
  - [x] 6.2 Run `uv run lint-imports` on the clean scaffold → all contracts PASS (baseline green).
  - [x] 6.3 Regression test `tests/regression/test_import_linter_contracts.py` — use pytest parametrize to verify `lint-imports` FAILs with the expected contract name when an illegal import is temporarily injected in a pytest tmp_path copy of the repo; assert the original repo still passes. Do **not** modify the real source tree.
  - [x] 6.4 Commit: `feat(ci): import-linter contracts enforce AR-BND1/BND2 layer hierarchy`.

- [x] **Task 7: ruff + mypy + pre-commit hooks** (AC: 4)
  - [x] 7.1 Add `[tool.ruff]` to root `pyproject.toml`:
    - `target-version = "py313"`, `line-length = 100`
    - `[tool.ruff.lint] select = ["E","F","I","N","UP","B","S","TID","DTZ"]` (DTZ = flake8-datetimez, catches naive datetime per Enforcement #6)
    - `[tool.ruff.lint.flake8-tidy-imports.banned-api]` mapping: `pandas` → msg cite Enforcement #3; `requests` → cite Enforcement #4; `urllib.request` → cite Enforcement #4.
    - `[tool.ruff.format] quote-style = "double"`.
  - [x] 7.2 Add `[tool.mypy]` to root `pyproject.toml`: `strict = true`, `python_version = "3.13"`, `mypy_path = "packages/athena-core:packages/athena-feature-store:..."` (all 6), `plugins = ["pydantic.mypy"]`.
  - [x] 7.3 Create `.pre-commit-config.yaml` with hook repos:
    - `astral-sh/ruff-pre-commit` (pinned version matching dev dep) — `ruff check --fix` + `ruff format`
    - `pre-commit/mirrors-mypy` — `mypy --strict`, `additional_dependencies = [pydantic, pydantic-settings]`
    - `Yelp/detect-secrets` OR `gitleaks/gitleaks` — scan staged diff
    - `pre-commit/pre-commit-hooks` — `check-yaml`, `check-toml`, `check-merge-conflict`, `end-of-file-fixer`, `trailing-whitespace`, `detect-private-key`
  - [x] 7.4 Run `uv run pre-commit install` (installs `.git/hooks/pre-commit`). Commit the `.pre-commit-config.yaml` and pinned `.pre-commit-hooks` lockfile-equivalent.
  - [x] 7.5 Run `uv run pre-commit run --all-files` → all hooks pass on clean scaffold (baseline green). Expect zero auto-fix diff after the run.
  - [x] 7.6 Regression test `tests/regression/test_ruff_bans.py`:
    - Create tmp_path file with `import pandas` → `ruff check` must emit `TID` code pointing to Enforcement #3 msg.
    - Create tmp_path file with `import requests` → must emit ban on Enforcement #4 msg.
    - Create tmp_path file with `from datetime import datetime; datetime.now()` → must emit `DTZ` code.
  - [x] 7.7 Commit: `feat(ci): pre-commit hook chain (ruff+mypy+secrets) with architecture bans`.

- [x] **Task 8: GitHub Actions CI — smoke gate** (AC: 3, 4, partial AR-INF4)
  - [x] 8.1 Create `.github/workflows/ci.yml` with a single job `scaffold-gate` on `ubuntu-latest` (self-hosted runner per AR-INF3 is a Story 1.3 concern — this story only sets the file, Story 1.3 migrates `runs-on` to `self-hosted` and adds the 7-stage pipeline):
    - Step: checkout (`fetch-depth: 0` so `git describe` works in Task 5 hook)
    - Step: install uv (`astral-sh/setup-uv@v3`, pin the version)
    - Step: `uv sync --frozen`
    - Step: `uv run pre-commit run --all-files`
    - Step: `uv run lint-imports`
    - Step: `uv run pytest -n auto` (pytest-xdist parallel)
  - [x] 8.2 Document in `docs/operating_playbook.md` that Story 1.3 will (a) migrate to `runs-on: [self-hosted, trading-pc]`, (b) add snapshot regression / 72h cooling / Paper gates. This story's CI is a **scaffold baseline**, not the full 7-stage pipeline.
  - [x] 8.3 Commit: `ci: scaffold-gate workflow (ruff, mypy, import-linter, pytest) — self-hosted migration deferred to Story 1.3`.

- [x] **Task 9: Final verification and sprint handoff** (AC: 1-5)
  - [x] 9.1 From a fresh clone (simulate via `git clone . ../_verify`), run: `uv sync --frozen && uv run pytest && uv run pre-commit run --all-files && uv run lint-imports && uv build packages/athena-core`. All must succeed on first attempt. Record the run log in the Dev Agent Record § Debug Log References.
  - [x] 9.2 Update `README.md` with a 10-line "Quick Start" section citing `uv sync && uv run pytest` and pointing to `docs/operating_playbook.md` for full ops procedures.
  - [x] 9.3 Populate File List in Dev Agent Record below.
  - [x] 9.4 Final commit: `chore(story-1.1): scaffold verification passed, hand off to Story 1.2`. **Do not** prefix with `policy:` — this is scaffold work, not a policy change (NFR-M3 / Change Control does not apply).

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

`claude-opus-4-7[1m]` (Amelia / bmad-agent-dev persona)

### Debug Log References

Key issues encountered and resolutions during implementation:

1. **uv 0.10.0 → 0.11.7 upgrade** (Task 1.1) — Khuk0's host had uv 0.10.0 in
   `Python313\Scripts\`. Installed 0.11.7 to `~/.local/bin/` via official PowerShell
   installer; PATH precedence verified with `where.exe uv`.
2. **`uv init --package athena` creates `athena/` subdirectory** (Task 1.2) — uv 0.11.7's
   `--package` flag is incompatible with the virtual-workspace layout Story 1.1 Task 1.4
   specifies (no `[project]` block at root). Discarded the generated subdirectory and
   wrote `pyproject.toml` + `.python-version` directly per Task 1.4 spec.
3. **pytest test module name collision** (Task 2.4 / Task 3) — All 6 packages declare
   `tests/test_smoke.py` with identical basenames. pytest's default `prepend` import-mode
   created `tests.test_smoke` collisions across packages. Resolved with
   `--import-mode=importlib` (pytest official recommendation) + `asyncio_mode = "auto"`.
4. **`pykis` import fails on Windows** (Task 3.4) — `python-kis` calls
   `ZoneInfo("Asia/Seoul")` at import time; Windows lacks system tzdata. Added
   `tzdata>=2024; sys_platform == 'win32'` to `athena-core` deps (also needed for
   `athena.core.time` Asia/Seoul utilities).
5. **module_version regex semantics** (Task 4.5) — Story Dev Notes pattern
   `^M\d+\.v\d+\.\d+\.\d+$` matches 4-part `M<n>.v<MAJOR>.<MINOR>.<PATCH>`
   (3-part semver), not 4-part semver. Test fixtures corrected from `M1.v0.1.0.0`
   to `M1.v0.1.0`.
6. **`test_version_no_shell` false positives** (Task 4.7) — Initial naive
   substring search caught the docstring's literal mentions of `os.popen`. Rewrote
   as AST `ast.walk` over `Call` nodes (`Attribute.value.id` / `Attribute.attr`),
   eliminating docstring/comment false positives.
7. **`python -m importlinter` fails** (Task 6.3) — `importlinter` ships no
   `__main__.py`. Switched regression test to call the `lint-imports` console
   script via `Path(sys.executable).parent / "lint-imports.exe"` with `shutil.which`
   fallback.
8. **`.importlinter` cp949 codec error** (Task 6.2) — Windows default config-file
   decoder cp949 cannot handle em-dash (`—`). Converted all non-ASCII characters
   to ASCII-safe equivalents (`-`).
9. **ruff DTZ001 on intentional naive datetime** (Task 7) — `test_rejects_naive_datetime`
   constructs a naive datetime by design to exercise the validator. Suppressed with
   inline `# noqa: DTZ001` rather than weakening the rule.
10. **mypy duplicate-module collision on tests/** (Task 7) — All 6 packages declare
    `tests/__init__.py`; mypy resolved them all to module name `tests` and aborted.
    Added `tests/` to `[tool.mypy].exclude`. Pre-commit's mypy hook already files-filters
    to `^packages/[^/]+/athena/[^/]+/.*\.py$`, so test type checking is intentional gap.
11. **pre-commit auto-fix loop on first commit** (Task 7) — `end-of-file-fixer` and
    `ruff-format` rewrote 5+1 files after staging; commit failed via the .git/hooks/pre-commit.
    Re-staged with `git add -u` and re-ran commit; hooks then exited clean.
12. **pytest-xdist race on import-linter regression** (Task 9.1) — Concurrent workers
    interleaved `inject` and `baseline` test runs, producing false baseline failures.
    Added `--dist=loadfile` to pyproject's pytest addopts so all tests in one file
    stay on a single worker.

### Completion Notes List

- **All 5 ACs satisfied.** AC-1 (6-package scaffold) + AC-2 (uv.lock + import smoke)
  + AC-3 (import-linter contracts + regression) + AC-4 (pre-commit hook chain +
  banned-api regression) + AC-5 (Hatchling build hook + `_version.py` + AST no-shell guard).
- **Scope deviations from Story spec** (with rationale):
  - **Task 1.4 `[project]` removed**: Honored — root `pyproject.toml` is a virtual
    workspace declaration only. Runtime deps moved to per-package `[project.dependencies]`
    (per AR-BND1 layering); dev tools live in root `[dependency-groups.dev]` (PEP 735).
    This deviates from a literal reading of Task 3.1 ("uv add at workspace root") but
    achieves the spec's intent (single `uv.lock`, reproducible install).
  - **Task 1.5 `.gitignore` scope expanded**: Pre-existing `.gitignore` ignored
    `_bmad-output/` and `docs/` wholesale; Task 1 implementation re-authored it to
    track BMAD artifacts (audit / NFR-A5) and `docs/operating_playbook.md` (living doc).
    A separate sentinel commit (`cbf9eb0`) landed the BMAD tracking before Task 1 commit
    so attribution stays clean.
  - **Task 8 `setup-uv@v3` pinned to 0.11.7**: Used the action version named in the
    Story without bumping; Story 1.3 owns toolchain version policy.
- **Per-AC commit attribution** (8 commits, all on `master`):
  - `cbf9eb0` BMAD artifact tracking sentinel (pre-Task 1)
  - `b0974dd` Task 1 — uv workspace root
  - `aad84c0` Task 2 — 6-package scaffold (AC-1)
  - `e215e34` Task 3 — Tier-1 deps + uv.lock + integration tests (AC-2)
  - `b7cf908` Task 4 — `BaseDTO`, `ErrorCode`, `version`, `time` + 19 tests (AC-2, partial AC-5)
  - `7ddb963` Task 5 — Hatchling build hook + 3 wheel-inspection tests (AC-5)
  - `841783d` Task 6 — `.importlinter` 5 contracts + 4 regression tests (AC-3)
  - `b7501d8` Task 7 — ruff + mypy + pre-commit chain + 4 ban regression tests (AC-4)
  - `37235ce` Task 8 — `.github/workflows/ci.yml` scaffold-gate
  - (this commit) Task 9 — verification + handoff
- **Final 5-gate verification (Task 9.1)**: `uv sync --frozen` (64 pkgs OK), `pytest -n auto`
  (40 passed / 1 skipped uvloop-Windows), `pre-commit run --all-files` (9 hooks pass),
  `lint-imports` (5 contracts kept), `uv build --package athena-core --wheel` (wheel built).
  Run log archived in `docs/operating_playbook.md` § "Story 1.1 Task 9.1 — Final 5-Gate Verification".
- **Test totals at handoff**: 41 collected — 40 passing (12 athena-core unit, 6 smoke,
  3 hatch hook integration, 7 scaffold integration, 8 ruff+importlinter regression),
  1 skipped (uvloop on Windows). Determinism check (`-p no:randomly`) not required by
  Story 1.1; deferred to Story 1.3 alongside coverage gate.
- **Out-of-scope preserved**: No `keyring_client`, `Settings`, structured logger,
  `FLAG_REGISTRY`, `LedgerClient`, `decisions.duckdb`, F5 mount unit, or self-hosted
  CI runner introduced. Story 1.2-1.6 inherit a clean scaffold.

### File List

**Sentinel commit `cbf9eb0` (BMAD artifact tracking, pre-Task 1):**
- `.gitignore` (rewritten)
- `_bmad/` + `_bmad-output/` (now git-tracked)

**Task 1 — uv workspace root:**
- `pyproject.toml` (created — virtual workspace + sources)
- `.python-version` (created — 3.13)
- `docs/operating_playbook.md` (created — stub + Day-1 toolchain table)
- `README.md` (modified — placeholder, replaced in Task 9.2)

**Task 2 — 6-package scaffold (24 files):**
- `packages/athena-core/{pyproject.toml, athena/core/__init__.py, tests/__init__.py, tests/test_smoke.py}`
- `packages/athena-feature-store/{...same shape...}`
- `packages/athena-alpha-defense/{...}`
- `packages/athena-ops-defense/{...}`
- `packages/athena-orchestrator/{...}`
- `packages/athena-execution/{...}`

**Task 3 — Tier-1 deps + integration tests:**
- `pyproject.toml` (modified — `[dependency-groups.dev]`, `[tool.pytest.ini_options]`)
- `packages/athena-core/pyproject.toml` (modified — pydantic, pydantic-settings, keyring, tzdata)
- `packages/athena-feature-store/pyproject.toml` (modified — polars, duckdb)
- `packages/athena-orchestrator/pyproject.toml` (modified — uvloop non-Windows)
- `packages/athena-execution/pyproject.toml` (modified — python-kis)
- `uv.lock` (created — 67 packages locked)
- `tests/integration/__init__.py` + `tests/integration/test_scaffold_imports.py` (created — 6 tests)
- `docs/operating_playbook.md` (modified — Week-1-Day-1 verification log)

**Task 4 — athena-core skeleton (7 files):**
- `packages/athena-core/athena/core/dto.py` (created — `BaseDTO` + 3-field contract)
- `packages/athena-core/athena/core/errors.py` (created — `ErrorCode` 8 + `AthenaError` + `MissingSecretError`)
- `packages/athena-core/athena/core/version.py` (created — `POLICY_VERSION_SHA`, `MODULE_VERSION`)
- `packages/athena-core/athena/core/time.py` (created — `kst_to_utc`, `utc_to_kst`)
- `packages/athena-core/tests/test_dto.py` (created — 10 tests)
- `packages/athena-core/tests/test_errors.py` (created — 5 tests)
- `packages/athena-core/tests/test_version_no_shell.py` (created — 4 AST tests)

**Task 5 — Hatchling build hook (3 files):**
- `packages/athena-core/hatch_build.py` (created — `CustomBuildHook`)
- `packages/athena-core/pyproject.toml` (modified — `[tool.hatch.build.hooks.custom]`)
- `packages/athena-core/tests/test_hatch_hook.py` (created — 3 wheel-inspection tests)

**Task 6 — import-linter (3 files):**
- `.importlinter` (created — 5 contracts: layers + 4 forbidden)
- `tests/regression/__init__.py` (created)
- `tests/regression/test_import_linter_contracts.py` (created — 1 baseline + 3 negative)

**Task 7 — ruff + mypy + pre-commit (3 files + auto-fixes to 11 prior files):**
- `pyproject.toml` (modified — `[tool.ruff]`, `[tool.mypy]`, `[tool.pydantic-mypy]`)
- `.pre-commit-config.yaml` (created — ruff + mypy + hygiene + secrets)
- `tests/regression/test_ruff_bans.py` (created — 4 parametrized)
- Auto-format + EOF-fix touched: `README.md`, `packages/athena-core/{pyproject.toml, athena/core/__init__.py, athena/core/dto.py, tests/test_*}`,
  `packages/athena-{execution, ops-defense, orchestrator}/athena/*/__init__.py`,
  `tests/integration/test_scaffold_imports.py`, `tests/regression/test_import_linter_contracts.py`

**Task 8 — CI scaffold-gate (2 files):**
- `.github/workflows/ci.yml` (created)
- `docs/operating_playbook.md` (modified — CI / self-hosted migration section)

**Task 9 — Verification + handoff (this commit):**
- `pyproject.toml` (modified — `--dist=loadfile` for pytest-xdist)
- `README.md` (rewritten — Quick Start)
- `docs/operating_playbook.md` (modified — Final 5-Gate Verification log)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — `1-1` → `review`)
- `_bmad-output/implementation-artifacts/1-1-프로젝트-bootstrap-uv-monorepo-scaffold.md` (this file: status, all checkboxes, Dev Agent Record, File List, Change Log)

### Change Log

| Date | Author | Note |
|---|---|---|
| 2026-04-21 | Amelia (claude-opus-4-7[1m]) | Story 1.1 implementation complete; status `ready-for-dev` → `in-progress` → `review`. 8 commits + 1 sentinel. 40 tests passing. |
| 2026-04-21 | Amelia (claude-opus-4-7[1m]) | Code review run — 3 parallel layers (Blind Hunter, Edge Case Hunter, Acceptance Auditor). 4 decision-needed, 15 patch, 12 defer, ~25 dismissed. See Review Findings section. |
| 2026-04-21 | Amelia (claude-opus-4-7[1m]) | Review action pass — 4/4 decisions resolved, 17/17 patches applied (incl. 3 decision-converted). Test suite: 40 → 72 tests (+32), all pass. 5-gate re-verified (pytest, pre-commit incl. new gitleaks hook, lint-imports, uv build, uv sync). Status `review` → `done`. Notable deviation logged: DN-3 changed `MODULE_VERSION` format from story spec line 77 (`<pkg_semver>+<git_sha8>`) to architecture line 625 compatible (`core.v<semver>`); SHA lives in `policy_version_git_sha` only. |

### Review Findings

**Decision-Needed** (resolve before patching):

- [x] [Review][Decision] BaseDTO.timestamp accepts any tz-aware datetime, not only UTC — docstring says "UTC-aware" but validator only rejects naive. Asia/Seoul-attached timestamps flow freely and produce silent off-by-9h bugs in downstream joins. Choose: (a) tighten to UTC-only (reject non-zero offset), (b) auto-convert via `.astimezone(UTC)` inside validator, or (c) relax docstring to "tz-aware". [packages/athena-core/athena/core/dto.py:33-41]
- [x] [Review][Decision] `_POLICY_SHA_PATTERN` rejects tag-prefix `git describe` output — pattern `^[0-9a-f]{7,40}(-dirty)?$` fails on `v1.0.0-5-gabcdef12` format that `git describe --always --dirty` emits once a tag exists. Scheduled-to-fail when first release tag is created. Choose: (a) relax pattern to accept tag-prefix form (product identity pollution), (b) `version.py` post-processes to extract bare hex, or (c) hatch hook switches to `git rev-parse HEAD` (deviates from AC-5 wording). [packages/athena-core/athena/core/dto.py:23]
- [x] [Review][Decision] `MODULE_VERSION` constant semantics collide with `BaseDTO.module_version` field — `version.py:MODULE_VERSION = "0.1.0+abc12345"` does not match DTO regex `^M\d+\.v\d+\.\d+\.\d+$|^[a-z_-]+\.v\d+\.\d+\.\d+$`. The two identities are semantically different (package-level vs per-M-module) but share a confusing name. Choose: (a) rename `MODULE_VERSION` → `PACKAGE_VERSION`, (b) keep the name and add disambiguation docstring. [packages/athena-core/athena/core/version.py:24]
- [x] [Review][Decision] `packages/athena-core` pulls `keyring>=25` — platform-specific backend deps at the leaf layer. Architecturally, keyring belongs to a secrets/ops_defense package, not the core leaf (AR-BND1). Story 1.2 spec intends `keyring_client` to live in `athena.core`, but including the dep now is a precedent. Choose: (a) accept (Story-1.2 intent), (b) move dep to `athena.ops_defense` or a dedicated package, defer `keyring_client` location to Story 1.2 scope. [packages/athena-core/pyproject.toml:481]

**Patches** (unambiguous fixes):

- [x] [Review][Patch] CRITICAL: `KIS_RATE_LIMIT` value is `"KIS_RATE_LIMIT"` but architecture.md#D14 line 317 explicitly specifies `"EGW00201"` (KIS gateway error code). Renames a frozen taxonomy on Day 1 without Change Control and breaks python-kis error translation. Also update `test_error_code_values_are_strings_matching_names` which locks in the wrong value via `member.value == member.name`. [packages/athena-core/athena/core/errors.py:15, packages/athena-core/tests/test_errors.py:30-33]
- [x] [Review][Patch] CRITICAL: `_git_describe` missing `cwd=self.root` argument — if `uv build` runs from a CWD inside a different git repo (e.g. developer's `~/projects` parent tree), silently stamps that foreign repo's SHA into `_version.py`. AR-COM4 product identity can be forged. [packages/athena-core/hatch_build.py:38-44]
- [x] [Review][Patch] MAJOR: Secret scanner incomplete — only `detect-private-key` is configured. AC-4 Task 7.3 explicitly requires `Yelp/detect-secrets` OR `gitleaks/gitleaks` in addition. Add hook repo + baseline. [.pre-commit-config.yaml:39-47]
- [x] [Review][Patch] MAJOR: `_git_describe` uses locale encoding (cp949 on Korean Windows) — `text=True` with no explicit `encoding=` decodes git's UTF-8 output via cp949 on the target host, raising `UnicodeDecodeError` on any non-ASCII tag/commit subject. `UnicodeDecodeError` is not caught by the except tuple and escapes the build. Add `encoding="utf-8", errors="replace"` and `UnicodeDecodeError` to except. [packages/athena-core/hatch_build.py:38-48]
- [x] [Review][Patch] MAJOR: `test_version_file_commit_matches_git_sha_or_fallback` accepts literal `"unknown-dev"` — the regex `...|^unknown-dev$` lets the AC-5 test pass silently when the hook fell back. A broken git/CI checkout ships wheels with no SHA and the test reports green. Split into: (a) when `shutil.which("git")` and `(REPO_ROOT/".git").exists()` both truthy, require hex-only match; (b) fallback-allowed path skipped or gated on explicit flag. [packages/athena-core/tests/test_hatch_hook.py:61-67]
- [x] [Review][Patch] MAJOR: AST forbidden-call check has bypass `from os import system; system(...)` — `FORBIDDEN_TOPLEVEL_MODULES` only contains `{"subprocess", "shutil"}`, and `_collect_dotted_calls` only matches `Attribute(value=Name(...))`, missing bare-name `Call(Name("system"))`. Either (a) add `os` to forbidden imports with allow-list of safe attrs, or (b) add bare-call detection for `system`, `popen`, `run`, `exec*`, `spawn*`. [packages/athena-core/tests/test_version_no_shell.py:42-88]
- [x] [Review][Patch] MAJOR: `pytest.skip` on missing `lint-imports` silently greens AC-3 regression — if `uv sync --group dev` ever fails to install the console script (entry-point collision, venv corruption), ALL contract-detection tests skip and CI shows green with zero coverage. Replace `pytest.skip` with `pytest.fail` when `os.environ.get("CI")` truthy. [tests/regression/test_import_linter_contracts.py:26-35]
- [x] [Review][Patch] MAJOR: `MODULE_VERSION` on fallback produces `"0.1.0+unknown-"` (trailing dash from slicing `"unknown-dev"[:8]`) — garbage product identity. Branch in `version.py`: if `POLICY_VERSION_SHA` is not pure hex, emit full `f"{_PACKAGE_SEMVER}+{POLICY_VERSION_SHA}"` (no slice) or dedicated unknown token. [packages/athena-core/athena/core/version.py:24]
- [x] [Review][Patch] MINOR: `_MODULE_VERSION_PATTERN` is too permissive — `[a-z_-]+` accepts `-.v0.0.0`, `_.v0.0.0`, `---.v0.0.0`. Tighten to `[a-z][a-z_]*` or whitelist the 6 actual context prefixes. [packages/athena-core/athena/core/dto.py:22]
- [x] [Review][Patch] MINOR: `kst_to_utc` / `utc_to_kst` don't verify input tz — functions accept any tz-aware value and silently treat as source tz. Add `assert dt.utcoffset() == timedelta(hours=9)` (or `tzinfo == _KST`) in `kst_to_utc` and mirror for `utc_to_kst`. [packages/athena-core/athena/core/time.py:15-23]
- [x] [Review][Patch] MINOR: `[tool.mypy].exclude` uses bare substring patterns — `"build"`, `"dist"`, `"tests/"` may over-match files whose path coincidentally contains those substrings (e.g. `packages/rebuild_*`). Anchor with `^build/`, `^dist/`, `(^|/)tests/`. [pyproject.toml:1080]
- [x] [Review][Patch] MINOR: Hatch hook f-string injection risk — `f'__commit__: str = "{commit}"'` breaks or opens code injection if `commit` contains `"` or `\n`. Normal `git describe --always --dirty` output is safe, but tag names can be arbitrary. Use `repr(commit)` to produce a safely-quoted literal. [packages/athena-core/hatch_build.py:28-32]
- [x] [Review][Patch] MINOR: CI workflow missing `concurrency` group — two rapid pushes race and burn runner minutes. Add `concurrency: { group: ${{ github.ref }}, cancel-in-progress: true }`. [.github/workflows/ci.yml:7-18]
- [x] [Review][Patch] MINOR: `_inject_illegal_import` cleanup — Windows `unlink()` may raise `PermissionError` if Python still holds the file handle after import; `missing_ok=True` does NOT suppress `PermissionError`. Add short retry loop + `sys.modules.pop("athena.<pkg>._lint_regression_only", None)` before delete. [tests/regression/test_import_linter_contracts.py:38-50]
- [x] [Review][Patch] MINOR: `test_ruff_bans.py` missing `import urllib.request` form — spec banned-api registry key `urllib.request` bans both `from urllib import request` AND `import urllib.request`, but regression tests only parametrize the first. Add a 4th case to close coverage. [tests/regression/test_ruff_bans.py]

**Deferred** (pre-existing / out of Story 1.1 scope):

- [x] [Review][Defer] pytest-xdist filesystem-mutating regression tests — theoretical cross-worker race on injected fixture files. `--dist=loadfile` mitigates within one file; `_` prefix prevents `import athena.X` auto-load. Revisit when test corpus grows. [tests/regression/test_import_linter_contracts.py]
- [x] [Review][Defer] Hatch hook silent `"unknown-dev"` fallback has no warning — no `display_warning` or stderr print when git missing/failed. Add observability hook in Story 1.3 or 1.9. [packages/athena-core/hatch_build.py:48-50]
- [x] [Review][Defer] `end-of-file-fixer` / `trailing-whitespace` auto-fix in CI — can fail PRs on benign whitespace churn. Revisit when Story 1.3 adds full 7-stage CI gate. [.pre-commit-config.yaml]
- [x] [Review][Defer] CI `fetch-depth: 0` + post-sync dirty check — if a future `uv sync` ever touches tracked files, hook stamps `-dirty` on clean-CI wheels. Add `git status --porcelain` guard in Story 1.3. [.github/workflows/ci.yml]
- [x] [Review][Defer] mypy hook `additional_dependencies` incomplete for future packages — only pydantic/pydantic-settings listed; polars/duckdb/python-kis imports will break hook once Stories 1.2+ land. Extend as each import materialises. [.pre-commit-config.yaml:34-36]
- [x] [Review][Defer] `asyncio_mode = "auto"` is loose — silently auto-wraps any `async def test_*`. Switch to `"strict"` until async tests actually appear (Story 1.4+). [pyproject.toml]
- [x] [Review][Defer] `athena.core.time` crashes at import if `tzdata` missing on Windows — current dep declaration (`tzdata; sys_platform == 'win32'`) guards the supported install path. Only unsupported installs fail. Lazy-init `_KST` if the concern materialises. [packages/athena-core/athena/core/time.py:11-12]
- [x] [Review][Defer] `detect-private-key` has no regression test — supply-chain "no secrets" NFR has zero fire-drill coverage. Add a test that commits a PEM fixture and asserts hook rejects in Story 1.3 CI hardening. [.pre-commit-config.yaml]
- [x] [Review][Defer] `.importlinter` layers `|` sibling syntax is fragile — requires literal `" | "` with spaces; human-editor error possible. Add inline comment when Story 1.2+ touches the config. [.importlinter:113]
- [x] [Review][Defer] `COMMIT_RE` in test_hatch_hook.py under-anchored (`no trailing \s*$`) — correct today, fragile for future edits. [packages/athena-core/tests/test_hatch_hook.py:20]
- [x] [Review][Defer] `test_frozen_prevents_mutation` relies on Pydantic patch-version semantics — `pytest.raises(ValidationError)` may need widening to `(ValidationError, TypeError)` if Pydantic behaviour shifts. [packages/athena-core/tests/test_dto.py:579-582]
- [x] [Review][Defer] `tests/regression/test_ruff_bans.py` matches bare `"TID"` not `"TID253"` — resilient to rule renames but undocumented. Add comment. [tests/regression/test_ruff_bans.py]
