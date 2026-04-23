# Athena systemd units

Linux/WSL2 supervisor units for Trading PC. Logger PC uses NSSM
(architecture.md D18) and is not covered here.

## Units by story

| Story | Unit | Action | Schedule | Install state |
|---|---|---|---|---|
| 1.4 | `athena-logger-sync.service` + `.timer` | rsync Logger PC → Trading PC | every 60 s | enabled by `scripts/install_logger_sync_unit.sh` |
| 1.4 | `mnt-external.mount` | mount external SSD for ledger backup | on demand (Story 1.5) | enabled by Story 1.5 install path |
| 1.6 | `athena-readonly-mount-lock.service` + `.timer` | `chattr +i` policy files at KRX open | Mon–Fri 09:00 KST | enabled by `infra/systemd/athena-readonly-mount.install.sh` |
| 1.6 | `athena-readonly-mount-unlock.service` + `.timer` | `chattr -i` policy files at KRX close | Mon–Fri 15:30 KST | enabled by same install.sh |
| 1.6 | `athena-inotify-watcher.service` | OVERRIDE_ATTEMPT inotify watcher | on demand | **scaffold only** — Story 3.5 wires `ExecStart=` + `[Install]` |

## Story 1.6 install order

```bash
# Trading PC, WSL2 Ubuntu 24.04, khuk0 user, ext4 home
cd ~/invest_training
DRY_RUN=1 sudo bash infra/systemd/athena-readonly-mount.install.sh   # preview
sudo bash infra/systemd/athena-readonly-mount.install.sh             # apply
systemctl list-timers --all | grep readonly-mount
```

The install script:

1. Warns (does not fix) if the system timezone is not `Asia/Seoul`. Story 1.10
   covers the `timedatectl set-timezone Asia/Seoul` automation.
2. Creates `/var/lib/athena/policy/` on ext4 and seeds it from `config/`.
   Subsequent runs **do not overwrite** existing copies — operator edits made
   during the unlock window are preserved.
3. Validates `infra/systemd/sudoers.d/athena-readonly-mount` with `visudo -cf`
   before installing it as `/etc/sudoers.d/athena-readonly-mount` (mode 0440,
   root:root). A bad sudoers file would lock the operator out of `sudo`, so
   the validation is non-negotiable.
4. Installs the 4 active units + the inotify scaffold, runs
   `systemctl daemon-reload`, and `enable --now` on the lock + unlock timers.

## Story 1.6 manual ops

```bash
# Force lock outside the timer window (e.g. before policy-edit window ends)
sudo systemctl start athena-readonly-mount-lock.service
# Force unlock for emergency policy fix (operating_playbook.md ## Story 1.6)
sudo systemctl start athena-readonly-mount-unlock.service
# Inspect last transition
journalctl -u athena-readonly-mount-lock.service -n 1 --no-pager
journalctl -u athena-readonly-mount-unlock.service -n 1 --no-pager
# Read current state without changing it
uv run python -m athena.alpha_defense.f5 status
```

## Test surface

`tests/integration/test_readonly_mount_units.py` shells out to
`systemd-analyze verify` + `visudo -cf` + `install.sh DRY_RUN=1` to check
unit syntax and idempotency. WSL2 only (`@pytest.mark.integration`).
