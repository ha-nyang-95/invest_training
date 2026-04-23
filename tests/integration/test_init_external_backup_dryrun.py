"""Story 1.5 Task 4.4 — init_external_backup.sh dry-run + mount unit INI parsing.

Stage-3 (`@pytest.mark.integration`).

Covers AC-4 Then 1-4:
1. `DRY_RUN=1 bash scripts/init_external_backup.sh` → exit 0, stdout shows
   `[dry-run]` prefix for every destructive command.
2. `DRY_RUN=0` with DEVICE unset → exit 1 + friendly DEVICE-required message
   (the OS Keychain probe is skipped because DEVICE resolution happens first).
3. The systemd `.mount` unit parses as INI with the expected `[Mount]`
   section keys.

Note — the `DRY_RUN=0` + Keychain-missing scenario is intentionally deferred:
reaching it requires DEVICE set, which we cannot provide on a CI host without
risking running cryptsetup / mount. The Keychain-missing branch is covered
by code review against `scripts/init_external_backup.sh` + the playbook
procedure, plus Story 1.2 's wider Keychain tests.
"""

from __future__ import annotations

import configparser
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "init_external_backup.sh"
_MOUNT_UNIT = _REPO_ROOT / "infra" / "systemd" / "mnt-external.mount"


def _bash_binary() -> str | None:
    """Prefer WSL's `bash` on Windows; POSIX `bash` elsewhere. WSL adapts
    paths via `wslpath` but we avoid the complexity by running the script
    from its tree-relative path under a cwd set to the repo root."""
    return shutil.which("bash")


@pytest.mark.skipif(
    _bash_binary() is None,
    reason="bash not on PATH — init_external_backup.sh is Linux/WSL2 only",
)
def test_dry_run_prefixes_every_destructive_command() -> None:
    bash = _bash_binary()
    assert bash is not None
    result = subprocess.run(  # noqa: S603
        [bash, str(_SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={"DRY_RUN": "1", "PATH": "/usr/bin:/bin", "USER": "khuk0"},
        check=False,
        cwd=str(_REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"dry-run exited {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("[dry-run] ")]
    # At minimum: cryptsetup luksFormat + luksOpen + mkfs.ext4 + mount +
    # mkdir for mount point + mkdir for ledger + chown x2 = 8. Require ≥5 to
    # guard against accidental early exit without locking down exact count
    # (future additions of e.g. `parted` are allowed).
    assert len(lines) >= 5, f"expected ≥5 dry-run lines, got {len(lines)}:\n{result.stdout}"
    # Spot-check a few tokens we expect to see prefixed.
    combined = "\n".join(lines)
    for token in ("luksFormat", "mkfs.ext4", "mount "):
        assert token in combined, f"dry-run missing {token!r}\n{combined}"


@pytest.mark.skipif(
    _bash_binary() is None,
    reason="bash not on PATH — init_external_backup.sh is Linux/WSL2 only",
)
def test_missing_device_non_dryrun_exits_one() -> None:
    bash = _bash_binary()
    assert bash is not None
    result = subprocess.run(  # noqa: S603
        [bash, str(_SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={"DRY_RUN": "0", "PATH": "/usr/bin:/bin"},
        check=False,
        cwd=str(_REPO_ROOT),
    )
    assert result.returncode == 1
    assert "DEVICE" in result.stderr


def test_mount_unit_has_expected_ini_structure() -> None:
    """configparser tolerates `[Unit]` / `[Mount]` / `[Install]` — the
    `.mount` unit MUST parse cleanly so Story 1.10 's installer can
    drop it into /etc/systemd/system without post-processing."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(_MOUNT_UNIT, encoding="utf-8")
    assert set(parser.sections()) == {"Unit", "Mount", "Install"}
    assert parser["Mount"]["Where"] == "/mnt/external"
    assert parser["Mount"]["Type"] == "ext4"
    # systemd escape form: /mnt/external ↔ mnt-external.mount
    assert _MOUNT_UNIT.name == "mnt-external.mount"


def test_script_is_executable() -> None:
    """Git-tracked scripts must retain the executable bit on Linux. On
    Windows git's filemode can be inconsistent — skip the bit-check when
    Python reports no executable permission (common under msys/git-for-windows
    where the stored mode is 0100755 but the working-copy mode is 0100644)."""
    if sys.platform.startswith("win"):
        # Still verify git stored it as executable via ls-files.
        result = subprocess.run(  # noqa: S603
            ["git", "ls-files", "--stage", str(_SCRIPT.relative_to(_REPO_ROOT).as_posix())],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(_REPO_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            mode = result.stdout.strip().split()[0]
            assert mode == "100755", (
                f"scripts/init_external_backup.sh git mode is {mode}, expected 100755"
            )
        return
    assert _SCRIPT.stat().st_mode & 0o111, "scripts/init_external_backup.sh not executable"
