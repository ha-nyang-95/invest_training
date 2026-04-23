#!/usr/bin/env bash
# scripts/init_external_backup.sh — Story 1.5 AC-4.
#
# 외장 SSD 를 LUKS2 로 포맷 + ext4 로 덧씌우고 /mnt/external 에 마운트한다.
# LUKS passphrase 는 OS Keychain 에서 조회 (SecretName=LUKS_PASSPHRASE).
# 실 LUKS 초기화 + systemd enable 은 Story 1.10 의 backup automation 에서
# 반복 (본 스크립트는 bootstrap 1회 + 이후 verify용).
#
# DRY_RUN=1 로 실행하면 cryptsetup / mkfs / mount 등 파괴적 명령을 stdout 에
# `[dry-run]` prefix 로 출력만 하고 실제로 수행하지 않는다 — 외장 SSD 가
# 아직 없거나 Logger PC 의 WSL2 세션이 아닌 환경에서도 sanity-check 가능.
set -euo pipefail

DEVICE="${DEVICE:-}"
MOUNT_POINT="${MOUNT_POINT:-/mnt/external}"
LUKS_NAME="${LUKS_NAME:-athena_external}"
KEY_KEYCHAIN_ID="${KEY_KEYCHAIN_ID:-LUKS_PASSPHRASE}"
DRY_RUN="${DRY_RUN:-0}"

if [[ -z "$DEVICE" && "$DRY_RUN" == "0" ]]; then
  echo "ERROR: DEVICE (예: /dev/sdb1) 필수 — 또는 DRY_RUN=1 로 호출" >&2
  exit 1
fi
if [[ "$DRY_RUN" == "1" && -z "$DEVICE" ]]; then
  DEVICE="/dev/sdX1-DRY"
fi

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] $*"
    return 0
  fi
  eval "$@"
}

# 1. LUKS 키 사전 확인 — OS Keychain 에 없으면 fail fast.
if [[ "$DRY_RUN" == "0" ]]; then
  if ! python3 -c "
import sys
from athena.core.keyring_client import get_secret, SecretName
try:
    get_secret(SecretName.LUKS_PASSPHRASE)
except Exception:
    sys.exit(1)
"; then
    echo "ERROR: OS Keychain 에 '${KEY_KEYCHAIN_ID}' 없음. 다음 명령으로 설정:" >&2
    echo "  python3 -c \"from athena.core.keyring_client import set_secret, SecretName; import secrets; set_secret(SecretName.LUKS_PASSPHRASE, secrets.token_urlsafe(32))\"" >&2
    exit 2
  fi
fi

# 2. LUKS 포맷 (파괴적 — 기존 데이터 모두 wipe).
run "python3 -c \"from athena.core.keyring_client import get_secret, SecretName; import sys; sys.stdout.write(get_secret(SecretName.LUKS_PASSPHRASE))\" | sudo cryptsetup luksFormat --type luks2 --batch-mode $DEVICE -"

# 3. LUKS open.
run "python3 -c \"from athena.core.keyring_client import get_secret, SecretName; import sys; sys.stdout.write(get_secret(SecretName.LUKS_PASSPHRASE))\" | sudo cryptsetup luksOpen $DEVICE $LUKS_NAME -"

# 4. ext4 포맷.
run "sudo mkfs.ext4 -L athena_external /dev/mapper/$LUKS_NAME"

# 5. 마운트 포인트 준비 + 마운트.
run "sudo mkdir -p $MOUNT_POINT"
run "sudo mount /dev/mapper/$LUKS_NAME $MOUNT_POINT"
run "sudo chown ${USER:-khuk0}:${USER:-khuk0} $MOUNT_POINT"
run "sudo mkdir -p $MOUNT_POINT/ledger"
run "sudo chown -R ${USER:-khuk0}:${USER:-khuk0} $MOUNT_POINT/ledger"

# 6. systemd mount unit 는 `infra/systemd/mnt-external.mount` 에 별도 tracked.
echo "NOTE: systemd mount unit (/etc/systemd/system/mnt-external.mount) 설치 + 'sudo systemctl enable --now mnt-external.mount' 은 Story 1.10 backup automation 단계."

echo "[ok] LUKS device $DEVICE mounted at $MOUNT_POINT"
