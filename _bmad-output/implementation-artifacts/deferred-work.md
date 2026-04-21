# Deferred Work Log

Items intentionally deferred from code reviews and implementation. Each entry cites the source review and the reason for deferral. Revisit during the referenced downstream story or sprint retrospective.

## Deferred from: code review of 1-1-프로젝트-bootstrap-uv-monorepo-scaffold (2026-04-21)

- pytest-xdist filesystem-mutating regression tests — theoretical cross-worker race on injected fixture files in `tests/regression/test_import_linter_contracts.py`. `--dist=loadfile` mitigates within one file; `_` prefix on fixture file prevents `import athena.X` auto-load. Revisit when test corpus grows or when a flaky run reproduces.
- Hatch hook silent `"unknown-dev"` fallback has no warning — `packages/athena-core/hatch_build.py:48-50` catches `(FileNotFoundError, subprocess.SubprocessError, OSError)` and falls back silently. Add `self.app.display_warning` / stderr print in Story 1.3 (CI hardening) or Story 1.9 (observability base).
- `end-of-file-fixer` / `trailing-whitespace` auto-fix in CI — `.pre-commit-config.yaml` hooks auto-modify files and return exit 1, which can fail PRs on benign whitespace churn against `pre-commit run --all-files`. Revisit when Story 1.3 adds the full 7-stage CI gate.
- CI `fetch-depth: 0` + post-sync dirty check — `.github/workflows/ci.yml` has full-history checkout, but if a future `uv sync` ever touches tracked files the hatch hook stamps `-dirty` on clean-CI wheels. Add `git status --porcelain` guard in Story 1.3.
- mypy hook `additional_dependencies` incomplete for future packages — `.pre-commit-config.yaml:34-36` only lists `pydantic`/`pydantic-settings`. Polars/duckdb/python-kis/uvloop imports in Story 1.2+ will fail the hook with `[import-not-found]`. Extend the list as each import materialises.
- `asyncio_mode = "auto"` is loose — `pyproject.toml` silently auto-wraps any `async def test_*`. Switch to `"strict"` until async tests actually appear (Story 1.4+).
- `athena.core.time` crashes at import if `tzdata` missing on Windows — `packages/athena-core/athena/core/time.py:11-12` eagerly constructs `ZoneInfo("Asia/Seoul")` at module import. Current dep `tzdata; sys_platform == 'win32'` guards the supported install path; only unsupported installs fail. Lazy-init `_KST` inside each function if the concern materialises.
- `detect-private-key` has no regression test — `.pre-commit-config.yaml` declares the hook but supply-chain "no secrets" NFR-S1 has zero fire-drill coverage. Add a test that commits a PEM fixture and asserts the hook rejects, during Story 1.3 CI hardening.
- `.importlinter` layers `|` sibling syntax is fragile — `.importlinter:113` requires literal `" | "` with spaces around the pipe; human-editor mistakes silently degrade contract. Add an inline explanatory comment when Story 1.2+ next touches the config.
- `COMMIT_RE` in test_hatch_hook.py under-anchored — `packages/athena-core/tests/test_hatch_hook.py:20` has no trailing `\s*$`, so would capture garbage after the closing quote if the hook's generated file format ever changes. Correct today, fragile for future edits.
- `test_frozen_prevents_mutation` relies on Pydantic patch-version semantics — `packages/athena-core/tests/test_dto.py:579-582` catches only `ValidationError`; historically frozen mutation raised `TypeError`. Widen to `(ValidationError, TypeError)` if Pydantic behaviour shifts.
- `tests/regression/test_ruff_bans.py` matches bare `"TID"` not `"TID253"` — resilient to ruff rule renames but the intent is undocumented. Add an inline comment explaining the choice.
