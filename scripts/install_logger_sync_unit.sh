#!/usr/bin/env bash
# Install (or dry-run) athena-logger-sync.{service,timer} into systemd.
# Story 1.4 AC-3 Task 3.3. Idempotent. DRY_RUN=1 prints planned actions
# without touching systemd (useful when Logger PC host is not yet
# registered — defer the enable step to Story 1.7).
set -euo pipefail

DRY_RUN=${DRY_RUN:-0}
UNIT_DIR=/etc/systemd/system
SRC="$(cd "$(dirname "$0")/../infra/systemd" && pwd)"

install_unit() {
  local f="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] would copy $SRC/$f -> $UNIT_DIR/$f"
    return
  fi
  sudo cp "$SRC/$f" "$UNIT_DIR/$f"
  sudo chmod 644 "$UNIT_DIR/$f"
}

install_unit athena-logger-sync.service
install_unit athena-logger-sync.timer

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[dry-run] would: systemctl daemon-reload"
  echo "[dry-run] would: systemctl enable --now athena-logger-sync.timer"
  exit 0
fi

sudo mkdir -p /var/log/athena
sudo chown khuk0:khuk0 /var/log/athena
sudo systemctl daemon-reload
sudo systemctl enable --now athena-logger-sync.timer
systemctl status athena-logger-sync.timer --no-pager
