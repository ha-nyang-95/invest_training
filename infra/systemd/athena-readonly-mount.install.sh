#!/usr/bin/env bash
# Install (or dry-run) the F5 readonly-mount stack — Story 1.6 AC-2 Task 2.5.
#
# Steps (idempotent):
#   1. Verify host is WSL2 + ext4 + Asia/Seoul timezone (warn but continue).
#   2. Create /var/lib/athena/policy/ on ext4 + seed from repo's config/.
#   3. Install 4 systemd units (lock/unlock × service/timer) into /etc/systemd/system/.
#   4. Install athena-inotify-watcher.service scaffold (Story 3.5 will replace
#      the ExecStart). Not enabled.
#   5. visudo -cf the sudoers drop-in, then install with mode 0440 root:root.
#   6. systemctl daemon-reload + enable --now both lock + unlock timers.
#
# DRY_RUN=1 prints planned actions without invoking sudo / chattr / systemctl.
set -euo pipefail

DRY_RUN=${DRY_RUN:-0}
UNIT_DIR=/etc/systemd/system
SUDOERS_DIR=/etc/sudoers.d
POLICY_DIR=/var/lib/athena/policy
LOG_DIR=/var/log/athena
TEXTFILE_DIR=/var/lib/node_exporter/textfile_collector

REPO_ROOT="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
SRC_SYSTEMD="$REPO_ROOT/infra/systemd"
SRC_SUDOERS="$REPO_ROOT/infra/systemd/sudoers.d"
SRC_CONFIG="$REPO_ROOT/config"

LOCK_TIMER=athena-readonly-mount-lock.timer
UNLOCK_TIMER=athena-readonly-mount-unlock.timer
SUDOERS_FILE=athena-readonly-mount

dry() { echo "[dry-run] $*"; }
run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    dry "$*"
  else
    eval "$@"
  fi
}

# 1) Host preflight ----------------------------------------------------------
preflight() {
  local tz
  tz="$(timedatectl show --property=Timezone --value 2>/dev/null || echo unknown)"
  if [[ "$tz" != "Asia/Seoul" ]]; then
    echo "WARN: system timezone is '$tz'; OnCalendar=Mon..Fri 09:00 will not match KST." >&2
    echo "      Run: sudo timedatectl set-timezone Asia/Seoul (deferred per Story 1.10)." >&2
  fi
  # ext4 check is best-effort — WSL2 native filesystem reports as ext4.
  local fstype
  fstype="$(df -T "$(dirname "$POLICY_DIR")" 2>/dev/null | awk 'NR==2 {print $2}' || echo unknown)"
  if [[ "$fstype" != "ext4" && "$DRY_RUN" != "1" ]]; then
    echo "WARN: $POLICY_DIR parent fstype is '$fstype', not ext4. chattr +i will fail." >&2
  fi
}

# 2) Materialise policy directory + seed from config/ ------------------------
seed_policy_dir() {
  if [[ "$DRY_RUN" == "1" ]]; then
    dry "mkdir -p $POLICY_DIR + chown khuk0:khuk0"
    dry "cp $SRC_CONFIG/policy.toml $POLICY_DIR/policy.toml (if missing)"
    dry "cp $SRC_CONFIG/flag_registry.toml $POLICY_DIR/flag_registry.toml (if missing or empty stub)"
    return
  fi
  sudo install -d -o khuk0 -g khuk0 -m 755 "$POLICY_DIR"
  sudo install -d -o khuk0 -g khuk0 -m 755 "$LOG_DIR"
  sudo install -d -o root -g root -m 755 "$TEXTFILE_DIR" || true
  # Idempotent seed: only copy if the destination is missing. Once we are in
  # production the operator edits POLICY_DIR copies during the unlock window
  # — overwriting from `config/` would clobber that work. Story 1.10 will
  # automate the safe re-sync.
  if [[ ! -f "$POLICY_DIR/policy.toml" ]]; then
    sudo install -m 644 -o khuk0 -g khuk0 "$SRC_CONFIG/policy.toml" "$POLICY_DIR/policy.toml"
  fi
  if [[ ! -f "$POLICY_DIR/flag_registry.toml" ]]; then
    if [[ -f "$SRC_CONFIG/flag_registry.toml" ]]; then
      sudo install -m 644 -o khuk0 -g khuk0 "$SRC_CONFIG/flag_registry.toml" "$POLICY_DIR/flag_registry.toml"
    else
      # Story 2.1 will populate the real 52-flag registry. For Story 1.6 we
      # only need the file to exist so chattr +i has a target.
      printf "# Empty stub — Story 2.1 will populate the 52-flag registry.\n" |
        sudo tee "$POLICY_DIR/flag_registry.toml" >/dev/null
      sudo chown khuk0:khuk0 "$POLICY_DIR/flag_registry.toml"
      sudo chmod 644 "$POLICY_DIR/flag_registry.toml"
    fi
  fi
}

# 3+4) systemd units ---------------------------------------------------------
install_unit() {
  local f="$1"
  if [[ -f "$UNIT_DIR/$f" ]] && cmp -s "$SRC_SYSTEMD/$f" "$UNIT_DIR/$f"; then
    echo "skip $f (already installed and identical)"
    return
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    dry "install -m 644 $SRC_SYSTEMD/$f -> $UNIT_DIR/$f"
    return
  fi
  sudo install -m 644 "$SRC_SYSTEMD/$f" "$UNIT_DIR/$f"
}

install_units() {
  install_unit athena-readonly-mount-lock.service
  install_unit athena-readonly-mount-lock.timer
  install_unit athena-readonly-mount-unlock.service
  install_unit athena-readonly-mount-unlock.timer
  install_unit athena-inotify-watcher.service  # scaffold, not enabled
}

# 5) sudoers drop-in ---------------------------------------------------------
install_sudoers() {
  local src="$SRC_SUDOERS/$SUDOERS_FILE"
  if [[ ! -f "$src" ]]; then
    echo "ERROR: sudoers source not found at $src" >&2
    exit 1
  fi
  # visudo -cf is non-destructive — bad syntax leaves /etc/sudoers untouched.
  # Some distros let visudo -cf run without sudo (it only reads the given
  # file); others require root. We try the unprivileged path first, then
  # fall back to sudo. In DRY_RUN we skip the real check entirely: CI
  # runners often have no interactive sudo, and the real install path
  # still validates before touching /etc/sudoers.d/.
  if [[ "$DRY_RUN" == "1" ]]; then
    dry "visudo -cf $src (validate sudoers syntax)"
    dry "install -m 0440 -o root -g root $src -> $SUDOERS_DIR/$SUDOERS_FILE"
    return
  fi
  if ! visudo -cf "$src" >/dev/null 2>&1; then
    if ! sudo visudo -cf "$src" >/dev/null; then
      echo "ERROR: visudo -cf failed on $src — refusing to install." >&2
      exit 1
    fi
  fi
  if [[ -f "$SUDOERS_DIR/$SUDOERS_FILE" ]] && cmp -s "$src" "$SUDOERS_DIR/$SUDOERS_FILE"; then
    echo "skip sudoers/$SUDOERS_FILE (already installed and identical)"
    return
  fi
  sudo install -m 0440 -o root -g root "$src" "$SUDOERS_DIR/$SUDOERS_FILE"
}

# 6) systemd activate --------------------------------------------------------
activate_timers() {
  if [[ "$DRY_RUN" == "1" ]]; then
    dry "systemctl daemon-reload"
    dry "systemctl enable --now $LOCK_TIMER"
    dry "systemctl enable --now $UNLOCK_TIMER"
    return
  fi
  sudo systemctl daemon-reload
  sudo systemctl enable --now "$LOCK_TIMER"
  sudo systemctl enable --now "$UNLOCK_TIMER"
  systemctl status "$LOCK_TIMER" --no-pager || true
  systemctl status "$UNLOCK_TIMER" --no-pager || true
}

main() {
  preflight
  seed_policy_dir
  install_units
  install_sudoers
  activate_timers
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] all install steps planned — no system state changed"
  else
    echo "F5 readonly-mount install complete. Verify: systemctl list-timers --all | grep readonly-mount"
  fi
}

main "$@"
