#!/usr/bin/env bash
# Install (or dry-run) athena-logger-sync.{service,timer} into systemd.
# Story 1.4 AC-3 Task 3.3. Idempotent. DRY_RUN=1 prints planned actions
# without touching systemd (useful when Logger PC host is not yet
# registered — defer the enable step to Story 1.7).
set -euo pipefail

DRY_RUN=${DRY_RUN:-0}
UNIT_DIR=/etc/systemd/system
# readlink -f resolves symlinked invocations (e.g. /usr/local/bin/install_logger_sync_unit.sh
# → repo script) so SRC always points at the actual repo's infra/systemd.
SRC="$(cd "$(dirname "$(readlink -f "$0")")/../infra/systemd" && pwd)"

install_unit() {
  local f="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] would copy $SRC/$f -> $UNIT_DIR/$f"
    return
  fi
  # `install` performs atomic replace (write-to-tmp + rename) with one
  # command — unlike `cp`, a concurrent `daemon-reload` cannot observe a
  # partially-rewritten unit file. 644 = world-readable, owner-writable.
  sudo install -m 644 "$SRC/$f" "$UNIT_DIR/$f"
}

install_unit athena-logger-sync.service
install_unit athena-logger-sync.timer

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[dry-run] would: systemctl daemon-reload"
  echo "[dry-run] would: systemctl enable --now athena-logger-sync.timer"
  exit 0
fi

# `install -d` is idempotent: creates the directory if missing with the
# given ownership in one call. Separating mkdir + chown (the prior form)
# left a window where mkdir succeeded but chown failed on a pre-existing
# directory owned by another user — with `set -e`, the script then aborted
# AFTER the unit copy but BEFORE daemon-reload, producing a half-installed
# state. /var/cache/athena/rsync-partial holds in-flight rsync tmp files
# outside the parquet tree so DuckDB's rglob cannot read them mid-transfer.
sudo install -d -o khuk0 -g khuk0 -m 755 /var/log/athena
sudo install -d -o khuk0 -g khuk0 -m 755 /var/cache/athena/rsync-partial
sudo systemctl daemon-reload
sudo systemctl enable --now athena-logger-sync.timer
systemctl status athena-logger-sync.timer --no-pager
