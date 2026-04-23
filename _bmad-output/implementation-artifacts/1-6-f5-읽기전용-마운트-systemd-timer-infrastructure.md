# Story 1.6: F5 읽기전용 마운트 systemd Timer Infrastructure

Status: done

Epic: 1 — Foundation & Market Truth Capture
Story Key: `1-6-f5-읽기전용-마운트-systemd-timer-infrastructure`
FR Coverage (direct): FR16 substrate (장중 파라미터 수정·정책 변경·git revert 물리 차단 — `chattr +i` 장중 immutable + systemd timer 09:00/15:30 KST 전환 + 한국 휴장 캘린더 skip — 실제 append-only 해시체인 로그 연동은 Story 3.1 anti_ego_events, inotify watcher 완성은 Story 3.5)
FR Coverage (substrate for): FR15 (F5 판정이 Firewall 집계에 입력되는 접점 — readonly_mount 상태 조회 API), FR57 (git signed + 72h cooling + Paper 재검증 policy enforce — F5 읽기전용 마운트가 장중 bypass 차단)
NFR Coverage (direct): NFR-S4 (장중 파라미터·정책 저장소는 읽기전용 마운트로 물리적 수정 차단 — OS primitives `chattr +i` 로 application 로직 외부에서 enforce), NFR-R5 (정책·파라미터 변경 72h cooling + Paper 재검증 전 prod 반영 금지 — 장중은 OS-level immutable 로 bypass 원천 차단)
NFR Coverage (hooks): NFR-S1 (sudoers NOPASSWD rule 은 `/usr/bin/chattr` 에 한정 — `.env` 평문 보관 금지 invariant 유지), NFR-A3 (장중 override 시도는 systemd journal + inotify watcher 로 흔적 남김 → Story 3.1/3.5 가 anti_ego_events 해시체인으로 승격), NFR-O2 (Prometheus 메트릭 `athena_readonly_mount_state` / `athena_readonly_mount_last_transition_ts` — 메트릭 스키마 contract 만 본 스토리, rule 등록 + Alertmanager 라우팅은 Story 1.9)
AR Coverage (direct): AR-SEC3 (Trading PC WSL2 Ubuntu `chattr +i` 장중 immutable, 장 마감 후 unlock → commit → 장 개시 전 relock — systemd timer on 09:00/15:30 KST — 본 스토리가 이 문장의 실 mechanism 확정), AR-CFG4 (`config/policy.toml` θ_entry·α/β/γ·M_regime·M_time — F5 읽기전용 마운트 대상 — 본 스토리가 대상 파일 집합 확정 + WSL2 ext4 경로 매핑), D9 (읽기전용 마운트 — chattr +i 장중 immutable, Windows ACL 대비 tamper-resistance), D17 (Trading PC WSL2 Ubuntu 24.04 LTS — chattr 는 Linux ext4 전용, `/mnt/c` Windows drive 작동 불가 → `/var/lib/athena/policy/` ext4 내부 배치), D18 (systemd supervisor — Logger PC NSSM 과 대비, Trading PC 의 모든 lockstep 액션은 systemd)

## Story

As **Athena 시스템이 장중 진입 직전 — 이전에 수립된 정책(`config/policy.toml`의 θ_entry·α/β/γ·M_regime·M_time + `config/flag_registry.toml` 의 52-flag 고정 ID) 이 application 로직 우회로는 절대 수정될 수 없음을 물리적으로 보증해야 하는 주체로서**,
I want **`/var/lib/athena/policy/policy.toml` + `/var/lib/athena/policy/flag_registry.toml` (WSL2 ext4 내부, `config/` git checkout 에서 배치 시점에 복사) 가 한국 거래일 09:00 KST 에 `chattr +i` 로 자동 immutable · 15:30 KST 에 `chattr -i` 로 자동 mutable 되고, `athena-readonly-mount-lock.service` / `athena-readonly-mount-unlock.service` + 2개 `.timer` (월-금, 한국 공휴일/임시 휴장일 skip) 가 systemd 가 idempotent · unlock→commit→relock 시나리오 가능 · root 계정도 장중 수정 시 `Operation not permitted` 반환 · 모든 전환이 systemd journal + Prometheus textfile collector 에 기록 · `packages/athena-alpha-defense/athena/alpha_defense/f5/readonly_mount.py` 가 Python 레벨 상태 조회 API + CLI + in-memory executor 추상화로 Windows/단위 테스트 fake 가능** 하여,
so that **Story 3.5 의 inotify watcher 가 본 스토리의 `/var/lib/athena/policy/` 디렉토리를 감시 대상으로 얹을 때, Story 3.1 의 anti_ego_events 체인이 OVERRIDE_ATTEMPT 이벤트를 append-only 로 기록할 때, Story 3.6 의 Anti-Ego Firewall aggregator 가 F5 상태를 단일 bit 로 읽을 때, Story 3.7 의 이중 조건 entry gate (S_entry > θ_entry AND Firewall=1) 가 정책 값의 장중 불변성을 전제할 때 — 그리고 무엇보다 Epic 2 Story 2.8 부터 실제 `S_entry` 계산이 θ_entry · α/β/γ · M_regime · M_time 을 읽기 시작할 때 — **정책 저장소의 tamper-resistance 가 이미 OS primitives 레벨로 enforce 되어 application 코드의 실수·자기 override·git revert 중 어느 것으로도 장중 정책 변경이 불가능한 상태**가 W1 Day 1 부터 성립하고, FR16 "장중 파라미터 수정·정책 변경·git revert 를 물리적으로 차단" + NFR-S4 "읽기전용 마운트" + NFR-R5 "72h cooling bypass 원천 차단" 의 OS-layer 기초가 완성된다**.

## Acceptance Criteria

**AC-1: `chattr +i` / `-i` Python wrapper + in-memory executor 추상화 (`packages/athena-alpha-defense/athena/alpha_defense/f5/readonly_mount.py`) + F5 모듈 scaffold + CLI (`lock` / `unlock` / `status`) + Prometheus textfile collector 메트릭 emitter** [Source: epics.md#Story-1.6 lines 600-603, architecture.md line 742-745 (`readonly_mount.py` 파일 위치), architecture.md#AR-SEC3 line 199, architecture.md#D9 line 299, architecture.md#D17 line 340, architecture.md#Gap-Analysis-Gap-3 lines 1211-1217 (WSL2 ext4 경로 규칙), Story 1.5 Invariant #11 (application-layer + AST 다층 방어 패턴)]

**Given** `packages/athena-alpha-defense/` 가 Story 1.1 Task 1.4 에서 빈 namespace package 로 scaffold 됨 (현재 `packages/athena-alpha-defense/athena/alpha_defense/__init__.py` 한 줄 + 빈 `tests/` 만 존재, M1~M14/F1~F5 하위 디렉토리 0개) + `packages/athena-alpha-defense/pyproject.toml` 이 `athena-core` 의존만 선언, `athena-feature-store` 의존 현존 (import 계층: `alpha_defense ← feature_store ← core`)
**And** Story 1.5 Invariant #11 의 "DuckDB row-level trigger 부재 → application-layer + AST 다층 방어" 패턴이 본 스토리에도 적용 — chattr 는 Windows 에서 작동 불가 (Linux ext4 전용) → Python wrapper 의 실 `subprocess.run(["chattr", ...])` 경로는 `@pytest.mark.integration` + `@pytest.mark.skipif(sys.platform=="win32")` 로만 실행, 단위 테스트는 `ChattrExecutor` Protocol 의 fake 구현으로 결정론적 검증

**When** 본 Task 1 이 다음 파일들을 작성:
  - `packages/athena-alpha-defense/athena/alpha_defense/__init__.py` — docstring 한 줄 (기존 유지, F5 는 하위 모듈로만 노출)
  - `packages/athena-alpha-defense/athena/alpha_defense/f5/__init__.py` — 재노출: `from .readonly_mount import ReadonlyMountController, ChattrExecutor, MountState, LockTransition`
  - `packages/athena-alpha-defense/athena/alpha_defense/f5/readonly_mount.py` — 다음 4 구성요소:
    1. **`ChattrExecutor` Protocol** (PEP 544 `typing.Protocol`, runtime_checkable=False — mypy 전용):
       ```python
       class ChattrExecutor(Protocol):
           def set_immutable(self, path: Path) -> None: ...
           def clear_immutable(self, path: Path) -> None: ...
           def is_immutable(self, path: Path) -> bool: ...
       ```
       이유: 단위 테스트 fake (dict[Path, bool] in-memory) + Windows 개발 머신에서 실 chattr 호출 차단 + Story 3.5 의 inotify watcher 가 동일 Protocol 로 mock 하여 immutability 상태를 주입 가능.
    2. **`SubprocessChattrExecutor`** — 실 구현 (Linux only, `@athena.core.settings.require_platform("linux")` 로 런타임 guard):
       ```python
       class SubprocessChattrExecutor:
           def set_immutable(self, path: Path) -> None:
               # sudo /usr/sbin/chattr +i <path>
               # sudo NOPASSWD 조건: /etc/sudoers.d/athena-readonly-mount (Task 2.6 playbook)
               _run_sudo_chattr(["+i", str(path)])
           # ... clear_immutable, is_immutable (lsattr 파싱)
       ```
       `_run_sudo_chattr` 는 내부 helper — `subprocess.run([... "sudo", "/usr/sbin/chattr", ...], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)`. Story 1.5 Debug Log #1 (cp949 encoding trap) 재발 방지를 위해 `encoding="utf-8"` 필수.
    3. **`MountState` StrEnum** (`enum.StrEnum`): `LOCKED`, `UNLOCKED`, `PARTIAL` (일부 파일만 immutable — 초기 설치 중 또는 수동 개입 직후 edge case).
    4. **`ReadonlyMountController`** — 핵심 로직:
       ```python
       @dataclass(frozen=True, slots=True)
       class LockTransition:
           transition: Literal["lock", "unlock"]
           target_paths: tuple[Path, ...]
           timestamp_utc: datetime
           previous_state: MountState
           new_state: MountState
           per_file_results: dict[Path, Literal["ok", "already", "skipped", "error"]]
           error_message: str | None = None

       class ReadonlyMountController:
           DEFAULT_PROTECTED_PATHS: ClassVar[tuple[Path, ...]] = (
               Path("/var/lib/athena/policy/policy.toml"),
               Path("/var/lib/athena/policy/flag_registry.toml"),
           )
           def __init__(self, executor: ChattrExecutor, protected_paths: tuple[Path, ...] = DEFAULT_PROTECTED_PATHS) -> None: ...
           def lock(self) -> LockTransition: ...        # chattr +i on all paths, idempotent
           def unlock(self) -> LockTransition: ...      # chattr -i, idempotent
           def status(self) -> MountState: ...          # aggregate: all immutable=LOCKED, none=UNLOCKED, mixed=PARTIAL
       ```
       - **Idempotent**: `lock()` when already LOCKED → `per_file_results[path]="already"`, no chattr call. Reason: systemd timer 가 시스템 재부팅 직후 이중 발동되거나 manual `systemctl start` 으로 중복 호출되어도 안전해야 함.
       - **Partial failure handling**: 2개 파일 중 1개만 성공 시 `MountState.PARTIAL` 반환 + `error_message` 에 실패 경로 기록. 후속 `lock()` 호출이 복구 시도 (이미 immutable 인 파일 skip, 미완료 파일 재시도) — systemd `Restart=on-failure` 가 자동 재시도.
       - **Path validation**: `protected_paths` 의 모든 경로가 `/var/lib/athena/policy/` 하위인지 Python 레벨 assert (architecture.md Gap-3 의 ext4 경로 규칙 enforce). 다른 경로 주입 시 `ValueError` (Pydantic validator 수준은 과함 — dataclass 내 assert).
  - `packages/athena-alpha-defense/athena/alpha_defense/f5/cli.py` — `python -m athena.alpha_defense.f5 {lock,unlock,status} [--dry-run]` 진입점:
    - `lock` subcommand → `ReadonlyMountController(SubprocessChattrExecutor()).lock()` 호출, 결과 JSON stdout.
    - `unlock` subcommand → 대칭.
    - `status` subcommand → 현재 `MountState` 출력 (`{"state": "LOCKED|UNLOCKED|PARTIAL", "checked_paths": [...], "as_of_utc": "..."}`).
    - `--dry-run` 플래그 → `ChattrExecutor` 를 `DryRunChattrExecutor` (production-side in-memory fake, `[dry-run]` prefix stdout, 실 chattr 미호출) 로 치환. Story 1.5 `scripts/init_external_backup.sh` 의 DRY_RUN 패턴 재사용.
    - `DryRunChattrExecutor` 와 `FakeChattrExecutor` 의 차이: `DryRunChattrExecutor` 는 CLI `--dry-run` 경로 (production code, stdout 로깅), `FakeChattrExecutor` 는 테스트 전용 (state 검증용 dict[Path, bool], `tests/conftest.py` 또는 각 test 모듈 내부 정의). 둘 다 `ChattrExecutor` Protocol 구현.
    - exit code: 0=성공(LOCKED 또는 UNLOCKED 로 전환 완료), 1=PARTIAL 또는 실패, 2=사용 에러 (argparse).
  - `packages/athena-alpha-defense/athena/alpha_defense/f5/metrics.py` — Prometheus textfile collector emitter:
    ```python
    def emit_readonly_mount_metric(
        *, state: MountState, last_transition_ts: datetime | None, output_path: Path
    ) -> None:
        """Write atomic textfile collector .prom file.

        Metrics:
          athena_readonly_mount_state{state="LOCKED|UNLOCKED|PARTIAL"} 1
          athena_readonly_mount_last_transition_timestamp_seconds <unix_seconds>
          athena_readonly_mount_last_lock_success_timestamp_seconds <unix_seconds>
          athena_readonly_mount_last_unlock_success_timestamp_seconds <unix_seconds>
        """
    ```
    `tmp + os.replace` atomic write (Story 1.5 Task 3.2 pattern 재사용). Node exporter textfile collector 가 `/var/lib/node_exporter/textfile_collector/athena_readonly_mount.prom` 을 scrape.
  - `packages/athena-alpha-defense/pyproject.toml` 의존 추가: `athena-feature-store` (workspace path dep — 실제 import 는 현재 없으나 architecture.md line 902-905 import 계층 확정). `boto3` 등 외부 런타임 의존 추가 없음 (F5 는 stdlib subprocess 만). `dev-dependencies` 에 별도 추가 없음 (pytest 기반 기존 그룹 재사용).

**Then** `uv run python -c "from athena.alpha_defense.f5 import ReadonlyMountController, ChattrExecutor, MountState; print(MountState.LOCKED, MountState.UNLOCKED, MountState.PARTIAL)"` 출력이 `LOCKED UNLOCKED PARTIAL` (Enum value 가 str, `StrEnum` 의미론 확인)
**And** `packages/athena-alpha-defense/tests/test_readonly_mount.py` (no marker — stage-2 unit) 7 시나리오 pass:
  1. `FakeChattrExecutor` + `ReadonlyMountController([pathA, pathB]).lock()` → `MountState.LOCKED` + `per_file_results == {pathA: "ok", pathB: "ok"}`, fake 내부 상태 `{pathA: True, pathB: True}`
  2. 동일 controller 의 두 번째 `lock()` → `per_file_results == {pathA: "already", pathB: "already"}`, state 불변 (idempotent 검증)
  3. `lock()` 이후 `unlock()` → `MountState.UNLOCKED` + `per_file_results == {pathA: "ok", pathB: "ok"}`
  4. `FakeChattrExecutor` 가 `pathB.set_immutable()` 에서 `PermissionError` raise → `lock()` 반환 `MountState.PARTIAL` + `per_file_results[pathB] == "error"` + `error_message` 에 `pathB` 포함
  5. Partial 상태에서 `lock()` 재호출 → `pathA` 는 already, `pathB` 는 다시 시도 (복구 시나리오)
  6. `ReadonlyMountController([Path("/etc/passwd")])` 생성 시 `ValueError` raise (경로가 `/var/lib/athena/policy/` 외부)
  7. `status()` 가 fake 상태를 aggregate 해 LOCKED/UNLOCKED/PARTIAL 정확히 반환
**And** `packages/athena-alpha-defense/tests/test_cli.py` (no marker — stage-2 unit) 4 시나리오 pass:
  1. `python -m athena.alpha_defense.f5 status --dry-run` → exit 0, stdout JSON `{"state": "UNLOCKED" | "LOCKED" | "PARTIAL", ...}` (dry-run 모드에서 fake executor 사용, deterministic)
  2. `... lock --dry-run` → exit 0, stdout 에 `[dry-run]` prefix + 대상 경로 2개 + 상태 전환 기록
  3. `... unlock --dry-run` → exit 0, 대칭
  4. `... invalid-subcommand` → exit 2, stderr argparse 에러
**And** `packages/athena-alpha-defense/tests/test_metrics.py` (no marker — stage-2) 3 시나리오 pass:
  1. `emit_readonly_mount_metric(state=LOCKED, last_transition_ts=..., output_path=tmp)` → `.prom` 파일 생성, 라인 수 ≥ 4 (state, last_transition, last_lock_success, last_unlock_success)
  2. `tmp + os.replace` atomic — 중간 crash 시뮬레이션에서 부분 write 흔적 없음 (tmp 파일만 남거나 완전 파일)
  3. UNLOCKED 상태 emit 시 `last_unlock_success_timestamp_seconds` 가 `last_transition_timestamp_seconds` 와 동일 값

---

**AC-2: `athena-readonly-mount-lock.service` + `athena-readonly-mount-unlock.service` + 2개 `.timer` (OnCalendar 09:00/15:30 KST 월-금) + sudoers NOPASSWD drop-in + systemd journal 기록 + 한국 휴장 캘린더 skip 로직** [Source: epics.md#Story-1.6 lines 605-623, architecture.md line 818 (`athena-readonly-mount.service` 파일 위치), architecture.md line 926 (systemd timers on 09:00/15:30 KST), architecture.md#D18 line 344 (Trading PC systemd supervisor), Story 1.5 sudoers NOPASSWD 패턴 (operating_playbook.md `## Story 1.5`)]

**Given** Trading PC WSL2 Ubuntu 24.04 LTS + systemd 254+ (Story 1.2 Task 1 완료) + `/var/lib/athena/policy/` 디렉토리 미존재 가능성 (Story 1.6 가 첫 populate) + Story 1.5 가 `sudo NOPASSWD` sudoers drop-in 패턴을 `scripts/init_external_backup.sh` 에서 확립 (`/etc/sudoers.d/athena-readonly-mount` 필요)
**And** architecture.md line 926 의 systemd 설명 "athena-readonly-mount | Trading PC | systemd (timers on 09:00/15:30 KST) | chattr +i / -i" 는 **2개 service + 2개 timer** (lock service + unlock service + 각각의 timer) 가 가장 자연스러운 디자인 — 단일 service + 2 timer 로 분기하면 ExecStart 에 argparse 필요해 복잡도 증가, 대신 systemd 관례는 "1 unit = 1 action" — 따라서 본 스토리가 이 2 pair mechanism 을 확정

**When** 본 Task 2 가 다음 파일들을 작성:
  - `infra/systemd/athena-readonly-mount-lock.service`:
    ```ini
    [Unit]
    Description=Athena F5 — Lock policy directory (chattr +i) at KRX open
    # chattr 는 filesystem 레벨 — network 무관, cryptsetup.target 이후 충분
    After=local-fs.target
    # 보호 대상 파일이 반드시 존재해야 함 — 없으면 systemd 가 fail 로 알림
    ConditionPathExists=/var/lib/athena/policy/policy.toml
    ConditionPathExists=/var/lib/athena/policy/flag_registry.toml
    # 한국 휴장일 skip — ExecStartPre 에서 check_trading_day.py exit 1 시 전체 service skip
    # (systemd "failure" 로 처리되지만 OnFailure= 없이 그냥 조용히 끝남)
    [Service]
    Type=oneshot
    User=root
    Group=root
    # 사전 조건: 오늘이 KRX 거래일인지 확인 (주말·공휴일 skip)
    ExecStartPre=/home/khuk0/invest_training/.venv/bin/python /home/khuk0/invest_training/scripts/check_trading_day.py
    # 실 chattr +i — Python wrapper 경유 (테스트 가능성 + 단일 진입점)
    ExecStart=/home/khuk0/invest_training/.venv/bin/python -m athena.alpha_defense.f5 lock
    # 전환 직후 Prometheus 메트릭 emit (ExecStopPost 에서 $EXIT_STATUS 사용 — Story 1.4 패턴)
    ExecStopPost=/home/khuk0/invest_training/.venv/bin/python /home/khuk0/invest_training/scripts/emit_readonly_mount_metric.py --action lock --exit-code $EXIT_STATUS --output /var/lib/node_exporter/textfile_collector/athena_readonly_mount.prom
    StandardOutput=append:/var/log/athena/readonly-mount.log
    StandardError=append:/var/log/athena/readonly-mount.log
    # 재시도: partial failure 또는 transient (파일시스템 busy 등) 시 30s 후 1회
    Restart=on-failure
    RestartSec=30s
    # `check_trading_day.py` 가 휴장일 → exit 1 은 정상 — SuccessExitStatus 로 처리
    # 실제 lock 실패 (exit != 0 && ExecStartPre 성공) 는 journalctl 에 남김
    [Install]
    WantedBy=multi-user.target
    ```
  - `infra/systemd/athena-readonly-mount-lock.timer`:
    ```ini
    [Unit]
    Description=Athena F5 — Lock policy at 09:00 KST (M-F, skip KR holidays)
    Requires=athena-readonly-mount-lock.service

    [Timer]
    # OnCalendar=Mon..Fri 09:00 Asia/Seoul — systemd 가 KST 로 evaluate
    # (Timer.OnCalendar 는 systemd 시스템 timezone 기준 — WSL2 가 Asia/Seoul 로
    # 설정돼 있어야 함; 아니면 TZ=Asia/Seoul 환경변수 또는 timedatectl set-timezone)
    OnCalendar=Mon..Fri 09:00
    # Persistent=false — 시스템이 09:00 에 꺼져 있다가 10:00 에 켜져도 "놓친" 실행을
    # 따라잡지 않음. 이유: 09:00 직후 수동 수정을 위해 의도적으로 unlock 한 날에
    # 재부팅하면 늦어서 상관없이 자동 relock 이 되는 혼란 방지. 대신 manual
    # `systemctl start athena-readonly-mount-lock` 로 명시적 잠금 가능.
    Persistent=false
    # AccuracySec=1min — 09:00 정각 ±1분 내 발동. 정확성보다 부하 저감.
    AccuracySec=1min
    # RandomizedDelaySec=0 — F5 의 핵심은 09:00 에 잠기는 것, 지연 없이 즉시 발동.

    [Install]
    WantedBy=timers.target
    ```
  - `infra/systemd/athena-readonly-mount-unlock.service` + `.timer`: 대칭 구성, `ExecStart=python -m athena.alpha_defense.f5 unlock` + `OnCalendar=Mon..Fri 15:30`. Unlock 은 장 마감 후 정책 수정 준비 — missed fires (Persistent=false 유지, 운영자가 manual unlock 가능).
  - `infra/systemd/athena-readonly-mount.install.sh` — 설치 helper (Story 1.4 `install_logger_sync_unit.sh` 패턴 재사용, `DRY_RUN=1` 지원):
    ```bash
    #!/usr/bin/env bash
    # 1. /var/lib/athena/policy/ 디렉토리 생성 + config/ → 복사
    # 2. systemd unit 4개 → /etc/systemd/system/
    # 3. sudoers drop-in → /etc/sudoers.d/athena-readonly-mount
    # 4. systemctl daemon-reload + enable --now 2 timers
    # 5. idempotent — 두 번째 실행 시 이미 설치된 파일 skip
    # DRY_RUN=1 일 경우 모든 destructive 명령을 echo 로만 출력 (Story 1.5 pattern)
    ```
  - `scripts/check_trading_day.py` — KRX 거래일 판정 CLI:
    ```python
    """exit 0 = today is KRX trading day (proceed with lock/unlock).
    exit 1 = today is KR holiday or weekend (skip).

    Holiday source: `holidays` PyPI library (country='KR', subdiv='KR').
    Version pinned in pyproject.toml (>= 0.50, < 1.0 for API stability).

    Rationale vs hardcoded TOML list:
      - `holidays` library auto-tracks 공휴일법 개정 + 임시공휴일 공시.
      - 하드코딩 TOML 은 매년 수동 업데이트 부담 → human failure 모드.
      - KRX 임시 휴장 (자연재해 등 초단기) 만 수동 override — `--extra-closed-days`
        CLI 인자로 ad-hoc 추가, `/etc/athena/extra_closed_days.txt` 파일 주입 가능.

    KRX 임시 휴장 조회 방법: https://open.krx.co.kr/contents/OPN/04/04020100/OPN04020100.jsp
      (매년 말 다음해 휴장일 공시, library 가 보통 Q4 에 반영)
    """
    import sys
    from datetime import date
    import holidays  # type: ignore[import-untyped]

    def main(argv: list[str]) -> int:
        # argparse: --extra-closed-days-file, --as-of (테스트용)
        ...
        today = date.today()
        kr = holidays.KR(years=today.year)
        if today.weekday() >= 5:  # 5=Sat, 6=Sun
            return 1
        if today in kr:
            return 1
        if today in extra_closed_days:
            return 1
        return 0
    ```
  - `scripts/emit_readonly_mount_metric.py` — systemd `ExecStopPost` 진입점. argparse 로 `--action {lock,unlock}`, `--exit-code N`, `--output path`. 내부적으로 `athena.alpha_defense.f5.metrics.emit_readonly_mount_metric` 호출 + state 결정 로직 (`exit_code == 0 AND action == lock` → LOCKED, etc.).
  - `infra/systemd/sudoers.d/athena-readonly-mount` — sudoers drop-in (visudo-safe 구문):
    ```
    # Allow the athena-readonly-mount systemd services to run chattr without password.
    # Restricted to /usr/sbin/chattr with +i / -i on specific files only.
    # Installed via `install.sh` with mode 0440 (root:root), as required by /etc/sudoers.d/.
    khuk0 ALL=(root) NOPASSWD: /usr/sbin/chattr +i /var/lib/athena/policy/policy.toml, /usr/sbin/chattr -i /var/lib/athena/policy/policy.toml, /usr/sbin/chattr +i /var/lib/athena/policy/flag_registry.toml, /usr/sbin/chattr -i /var/lib/athena/policy/flag_registry.toml
    ```
    - **Wildcard 금지** — 구체 파일 2개 + `+i` / `-i` 2 동작만 허용. sudoers wildcard 는 보안 footgun (path traversal 위험).
    - `install.sh` 는 `visudo -cf` 로 구문 검사 후 설치. 실패 시 exit 1.
  - `pyproject.toml` 런타임 의존: `holidays>=0.50,<1.0` 추가 (root `pyproject.toml` 또는 `athena-alpha-defense/pyproject.toml` — CLI 가 `scripts/check_trading_day.py` 경유라 root 에 두는 편이 scripts/ 패턴 일관).

**Then** `uv run python scripts/check_trading_day.py --as-of 2026-04-27` (월요일, 공휴일 아님) → exit 0, stdout `{"decision": "trade", "date": "2026-04-27", ...}`
**And** `uv run python scripts/check_trading_day.py --as-of 2026-04-25` (토요일) → exit 1, stdout `{"decision": "skip", "reason": "weekend", ...}`
**And** `uv run python scripts/check_trading_day.py --as-of 2026-05-05` (어린이날) → exit 1, stdout `{"decision": "skip", "reason": "holiday", ...}`
**And** `tests/integration/test_readonly_mount_units.py` (`@pytest.mark.integration`, stage-3) 6 시나리오 pass:
  1. `systemd-analyze verify infra/systemd/athena-readonly-mount-lock.service` exit 0 (systemd 가 unit 파일 문법 검증)
  2. 같은 verify 가 `*.timer` 2개 + `unlock.service` 1개 모두 exit 0
  3. `systemd-analyze calendar "Mon..Fri 09:00"` 출력이 다음 발동 시각을 정확히 계산 (월-금 09:00 으로)
  4. `visudo -cf infra/systemd/sudoers.d/athena-readonly-mount` exit 0 (sudoers 구문 검증)
  5. `infra/systemd/athena-readonly-mount.install.sh DRY_RUN=1` → exit 0, stdout 에 `[dry-run]` prefix 라인 ≥ 8 (mkdir /var/lib/athena/policy, cp 2 files, cp 4 systemd units, cp sudoers, systemctl daemon-reload, enable --now 2 timers)
  6. install.sh idempotent — 두 번째 DRY_RUN=1 실행이 "already installed" skip 메시지 (stderr 포함), exit 0
**And** `tests/integration/test_check_trading_day.py` (`@pytest.mark.integration`, stage-3) 5 시나리오 pass:
  1. `--as-of 2026-01-01` (신정) → exit 1, reason=holiday
  2. `--as-of 2026-04-27` (월) → exit 0, decision=trade
  3. `--as-of 2026-05-05` (어린이날) → exit 1, reason=holiday
  4. `--extra-closed-days-file` 에 `2026-04-27` 추가 후 same 날짜 → exit 1, reason=extra_closed
  5. `--as-of 2026-04-26` (일요일) → exit 1, reason=weekend

---

**AC-3: WSL2 ext4 `/var/lib/athena/policy/` 위의 실 `chattr +i` / `-i` 동작 + root 계정도 immutable 파일 수정 시 `Operation not permitted` 반환 + git revert 장중 물리 차단 + 장 마감 후 relock-commit-unlock 사이클** [Source: epics.md#Story-1.6 lines 600-617, architecture.md#D9 line 299, architecture.md Gap-3 lines 1211-1217]

**Given** WSL2 Ubuntu 24.04 + `/var/lib/athena/policy/policy.toml` 가 존재 (AC-2 install.sh 실행 후) + Khuk0 가 sudoers drop-in 등록됨 + Python venv 에서 `athena.alpha_defense.f5` import 가능
**And** `/var/lib/athena/policy/` 가 ext4 파일시스템 (WSL2 네이티브) — `df -T /var/lib/athena/policy` 확인으로 `/mnt/c` (9p DrvFs) 아닌지 확인. architecture.md Gap-3 의 명시 규칙: chattr 는 ext4 에서만 동작.

**When** 본 Task 3 의 integration 테스트 (실 chattr 호출 — WSL2 only, `@pytest.mark.integration` + `@pytest.mark.skipif(sys.platform == "win32")`):
  - `test_chattr_e2e.py::test_lock_then_write_fails`:
    1. tmp_path = `tmp_policy_dir / "policy.toml"` 에 임의 내용 write
    2. `ReadonlyMountController([tmp_path]).lock()` → 이 테스트는 실 `SubprocessChattrExecutor` 사용 (production path 커버)
    3. `tmp_path.write_text("tampered")` 또는 `open(tmp_path, "w")` → `PermissionError` (errno EPERM, errno == 1 "Operation not permitted")
    4. `sudo rm tmp_path` 도 `rm: cannot remove: Operation not permitted` (immutable 은 root 에서도 rm 불가)
    5. `unlock()` 후 write/rm 가능 확인
  - `test_chattr_e2e.py::test_git_revert_blocked_during_lock`:
    1. tmp git 저장소 생성 + `policy.toml` 초기 commit + 두 번째 변경 commit
    2. `/var/lib/athena/policy/policy.toml` 를 "두 번째 commit 상태" 로 동기화 + `lock()`
    3. `git checkout HEAD~ -- /var/lib/athena/policy/policy.toml` 시도 → git 가 파일 touch 불가, error 반환
    4. `unlock()` 후 `git checkout` 성공 확인
  - `test_chattr_e2e.py::test_idempotent_lock_cycle`:
    1. `lock()` → `LOCKED`
    2. `lock()` 즉시 재호출 → `LOCKED`, per_file_results 모두 "already"
    3. `unlock()` → `UNLOCKED`
    4. `unlock()` 즉시 재호출 → `UNLOCKED`, per_file_results 모두 "already"
  - `test_chattr_e2e.py::test_end_to_end_market_cycle`:
    Story 1.6 의 핵심 시나리오 — 하루 완주 시뮬레이션:
    1. 07:00 (장전, UNLOCKED) — `policy.toml` 편집 + git commit
    2. 09:00 timer 발동 시뮬레이션 (`systemctl start athena-readonly-mount-lock.service`) → state → LOCKED
    3. 12:00 (장중, LOCKED) — git revert 시도 → 실패, `policy.toml` write 시도 → 실패
    4. 15:30 timer 발동 시뮬레이션 (`systemctl start athena-readonly-mount-unlock.service`) → state → UNLOCKED
    5. 17:00 (장 마감 후, UNLOCKED) — `policy.toml` 편집 + git commit + 72h cooling 대기 (외부 프로세스, 본 테스트 scope 외)
    6. systemd journal 에 lock + unlock 전환 기록 2개 확인 (`journalctl -u athena-readonly-mount-lock -n 1` + unlock 대칭)

**Then** 위 4 시나리오 모두 WSL2 Ubuntu 24.04 에서 실행 시 pass
**And** Windows Python 환경에서는 `@pytest.mark.skipif(sys.platform == "win32", reason="chattr/lsattr are Linux-only — WSL2 required")` 로 skip (Story 1.5 `test_init_external_backup_dryrun.py` 의 `platform == 'Windows'` skip 패턴 재사용)
**And** 모든 테스트는 `tmp_path` fixture 경유 — 실 `/var/lib/athena/policy/` 오염 금지 (WSL2 CI runner 에서도 격리)
**And** `test_chattr_e2e.py` 의 WSL2 prerequisite 문서화: 테스트 파일 docstring 에 "Requires: WSL2 Ubuntu, chattr/lsattr installed, sudoers NOPASSWD for chattr (install.sh 선행 필요), ext4 filesystem on tmp_path" 명시

---

**AC-4: inotify watcher systemd service scaffold + OVERRIDE_ATTEMPT 이벤트 hook (실 append 는 Story 3.5)** [Source: epics.md#Story-1.6 lines 615-618, epics.md#Story-3.5 lines 1283-1297, architecture.md line 918 (systemd supervisor — Trading PC)]

**Given** Story 3.5 가 `athena-core/athena/core/anti_ego/inotify_watcher.py` (가칭) 에서 본 스토리의 `/var/lib/athena/policy/` 디렉토리를 watch target 으로 consume 예정 — 본 스토리는 **consume contract 만** 확정, 실 watcher 구현은 Story 3.5 scope
**And** epics.md#Story-1.6 AC #4 의 "inotify watcher 가 시도 이벤트 로그에 기록 (hook만 준비, 로그 구조는 Epic 3)" 를 재해석: 본 스토리는 **2개 산출물** 까지 — (a) systemd unit 파일 skeleton (`infra/systemd/athena-inotify-watcher.service` — disabled state, ExecStart 는 Story 3.5 가 Python 모듈 경로 확정 후 채움), (b) watcher 가 emit 할 event 의 Python dataclass (`athena.alpha_defense.f5.override_event.OverrideAttemptEvent`) — Story 3.5 가 append 할 contract

**When** 본 Task 4 가 다음 파일들을 작성:
  - `packages/athena-alpha-defense/athena/alpha_defense/f5/override_event.py`:
    ```python
    """OVERRIDE_ATTEMPT event contract (Story 3.5 consume, Story 3.1 persist)."""
    from dataclasses import dataclass
    from datetime import datetime
    from pathlib import Path
    from typing import Literal

    @dataclass(frozen=True, slots=True)
    class OverrideAttemptEvent:
        """Emitted by inotify watcher (Story 3.5) when someone tries to write/delete
        a protected file during the LOCKED window.

        Story 3.1 anti_ego_events 체인이 이 dataclass 를 JSON payload 로 직렬화해
        persist. `payload_json` = canonical_json(asdict(event)).

        Contract invariants (본 스토리가 fix):
          - `attempted_at_utc` 는 UTC aware datetime (BaseDTO 규칙 — Story 1.4 Invariant #1)
          - `target_path` 는 /var/lib/athena/policy/ 하위 (AC-1 path validation)
          - `inotify_event_mask` 는 `IN_MODIFY | IN_ATTRIB | IN_DELETE | IN_MOVED_FROM` 중 하나
          - `attempter_uid` 는 프로세스 유효 UID (0=root override 시도 시에도 기록)
        """
        attempted_at_utc: datetime
        target_path: Path
        inotify_event_mask: Literal["IN_MODIFY", "IN_ATTRIB", "IN_DELETE", "IN_MOVED_FROM"]
        attempter_uid: int
        attempter_pid: int | None  # inotify 는 PID 을 직접 제공 안 함 — audit subsystem 병용 시에만
        mount_state_at_attempt: Literal["LOCKED", "UNLOCKED", "PARTIAL"]
    ```
  - `infra/systemd/athena-inotify-watcher.service` — disabled scaffold:
    ```ini
    [Unit]
    Description=Athena F5 override-attempt watcher (Story 3.5 — disabled in 1.6)
    Documentation=Story 3.5 completes ExecStart wiring
    After=local-fs.target
    ConditionPathExists=/var/lib/athena/policy/
    [Service]
    Type=simple
    User=khuk0
    # SCAFFOLD: Story 3.5 가 실제 Python 모듈로 교체 —
    # 현재는 placeholder (sleep infinity) 로 두어 `systemd-analyze verify` 만 통과
    # Story 3.5 AC 수용 시 ExecStart=python -m athena.alpha_defense.f5.inotify_watcher 로 변경
    ExecStart=/bin/sh -c "echo 'athena-inotify-watcher scaffold — Story 3.5 will implement'; exec sleep infinity"
    Restart=on-failure
    RestartSec=30s
    StandardOutput=append:/var/log/athena/inotify-watcher.log
    StandardError=append:/var/log/athena/inotify-watcher.log
    # [Install] 섹션 **생략** — 본 스토리는 enable 하지 않음. Story 3.5 가 추가.
    ```
  - `infra/systemd/README.md` 업데이트 — "Units by story" 표에 본 스토리의 4개 새 unit (lock.service, lock.timer, unlock.service, unlock.timer) + 1개 scaffold (inotify-watcher.service) 등록. 설치 순서 명시: "1.6 install.sh 가 lock/unlock 4 unit enable, inotify watcher 는 disabled 로 놔둠. 1.10 backup timer + 3.5 watcher 활성화는 각 스토리 playbook 소관."

**Then** `systemd-analyze verify infra/systemd/athena-inotify-watcher.service` exit 0 (scaffold 도 문법은 올바름)
**And** `uv run python -c "from athena.alpha_defense.f5.override_event import OverrideAttemptEvent; from datetime import datetime, UTC; from pathlib import Path; e = OverrideAttemptEvent(attempted_at_utc=datetime.now(UTC), target_path=Path('/var/lib/athena/policy/policy.toml'), inotify_event_mask='IN_MODIFY', attempter_uid=1000, attempter_pid=12345, mount_state_at_attempt='LOCKED'); print(e.target_path, e.mount_state_at_attempt)"` 출력 정상
**And** `packages/athena-alpha-defense/tests/test_override_event.py` (no marker — stage-2) 2 시나리오 pass:
  1. `OverrideAttemptEvent(... attempted_at_utc=naive_datetime ...)` → `ValueError` (UTC-aware 강제 — dataclass `__post_init__` 에서 BaseDTO 와 동일 정신 구현)
  2. `OverrideAttemptEvent` instance 의 `dataclasses.asdict()` → JSON-serializable dict (datetime 은 ISO-8601 문자열로 `default=str`, Story 1.5 canonical_json 과 호환)

---

**AC-5: Operating Playbook 업데이트 + deferred-work 등록 + sprint-status 전환 (review)** [Source: Story 1.4/1.5 Task 7 패턴 — `docs/operating_playbook.md` 의 "## Story <N>" 섹션 + `_bmad-output/implementation-artifacts/deferred-work.md` + `sprint-status.yaml`]

**Given** Story 1.5 가 `operating_playbook.md` 에 `## Story 1.5` 섹션 (5 sub-section: Ledger schema, LedgerClient usage, monthly segment hash, LUKS setup, S3 Object Lock setup) 을 추가한 패턴 + `deferred-work.md` 에 Story 1.5 관련 14 항목 + Gemini PR #10 findings 추가
**And** 본 스토리는 **정책 파일 (`config/policy.toml`) 수정 없음** — 본 스토리는 infra (systemd unit + Python wrapper + sudoers) 만. 따라서 모든 commit 은 `feat(infra)` / `feat(alpha-defense)` / `chore(story-1.6)` — `policy:` prefix 필요 없음. 72h cooling gate 미적용.

**When** 본 Task 5 가 다음 업데이트:
  - `docs/operating_playbook.md` 에 `## Story 1.6` 섹션 (5 sub-section):
    1. **"Host setup prerequisite — sudoers NOPASSWD for chattr"** — `/etc/sudoers.d/athena-readonly-mount` 설치 절차, `visudo -cf` 검증 명시, 잘못된 sudoers 로 sudo 전체 깨짐 위험 경고.
    2. **"Install 4 systemd units + enable timers"** — `sudo bash infra/systemd/athena-readonly-mount.install.sh` 실행 절차, `systemctl status athena-readonly-mount-lock.timer` 확인 방법, `systemctl list-timers --all` 출력 기대값.
    3. **"Manual lock/unlock during ops"** — 점검·긴급 unlock 이 필요한 경우의 절차: `sudo systemctl start athena-readonly-mount-unlock.service` + `systemctl status` 확인. 이 경우 `journalctl -u` 로 흔적 남아 감사 가능.
    4. **"KR holiday list maintenance"** — `holidays` library 업데이트 주기 (연 1~2회 pip upgrade), 임시 휴장 발생 시 `/etc/athena/extra_closed_days.txt` 수동 추가 절차, KRX 공식 링크.
    5. **"Troubleshooting: PARTIAL state"** — `athena_readonly_mount_state{state="PARTIAL"}` 메트릭이 Alertmanager 에서 뜰 때 대응: (a) `python -m athena.alpha_defense.f5 status` 로 per-file 상태 확인, (b) 수동 재시도 `... lock`, (c) 실패 지속 시 sudoers / 디렉토리 권한 확인.
  - `_bmad-output/implementation-artifacts/deferred-work.md` 에 `## Deferred from: Story 1.6` 섹션 추가 (최소 6 항목 예상 — Task 5.3 가 실 항목 채움):
    - inotify watcher 실 구현 (`athena-inotify-watcher.service` ExecStart 채우기) → Story 3.5
    - `anti_ego_events` 테이블로 OVERRIDE_ATTEMPT event append → Story 3.1 + Story 3.5
    - `athena_readonly_mount_*` Prometheus rule 파일 (`infra/prometheus/rules/readonly_mount.rules.yml`) + Alertmanager 라우팅 → Story 1.9
    - `timedatectl set-timezone Asia/Seoul` — WSL2 host setup 가정 (systemd Timer.OnCalendar 이 KST 로 evaluate 되려면). 현재 install.sh 는 check 만 수행, 실 설정은 운영자 수동 → 혹은 Story 1.10 이 host setup 단계에서 묶어 처리.
    - `/etc/athena/extra_closed_days.txt` systemd credential 주입 방식 → V1.1+ (현 V1.0 은 plain text, Khuk0 직접 편집 허용)
    - `config/` → `/var/lib/athena/policy/` 복사 방식의 rsync 또는 git hook 자동화 → Story 1.10 (현 V1.0 은 install.sh 에서 1회 복사 + 수동 재배포 allow)
    - systemd timer 의 `Persistent=true` vs `false` 정책 재평가 (현 false — 시스템 downtime 시 missed fire 이 의도적 미수행). Story 1.9 observability 관측 후 재조정 가능.
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`:
    - `1-6-f5-읽기전용-마운트-systemd-timer-infrastructure` 의 status 를 `ready-for-dev` → `in-progress` (Task 1 시작) → `review` (Task 1-5 완료, 5-gate green, `/bmad-code-review` 기다림) 의 2 단계 전환.
    - `last_updated` 를 실 변경 일자로 업데이트.
    - `epic-1` 은 이미 `in-progress` 이므로 불변.
  - `_bmad-output/implementation-artifacts/1-6-*.md` (본 파일) 의 `## Change Log` 에 Task 진행별 version bump 기록 (v0.1.0 ready-for-dev → v0.2.0 review → v0.3.x code-review patches → v0.4.0 done).

**Then** `docs/operating_playbook.md` 에 `## Story 1.6` 섹션이 존재, 5 sub-section 모두 작성됨
**And** `deferred-work.md` `## Deferred from: Story 1.6` 섹션이 최소 6 항목 (Task 5.3 가 확정) 보유
**And** `sprint-status.yaml` 가 `1-6-*: review` + `last_updated: 2026-04-XX` + `epic-1: in-progress` 상태
**And** 5-gate (Story 1.3-1.5 의 동일 gate — `uv sync --frozen` / `pytest -n auto` / `pre-commit run --all-files` / `lint-imports` / `uv build --wheel`) 가 모두 green — 특히:
  - `lint-imports` contracts: `alpha_defense` 가 `core` + `feature_store` 만 import, `execution` / `orchestrator` / `ops_defense` import 금지 (architecture.md line 902-915). `athena.alpha_defense.f5` 하위도 동일 규칙 상속.
  - `pre-commit` 10 hooks pass — 신규 ruff 위반 0건, mypy 신규 에러 0건, end-of-file-fixer auto-fix 에 의한 변경 없음.
**And** 전 세션 commit 집합이 **모두 WSL2 signed** — Windows 세션은 commit 실행 금지 (feedback_windows_host_commit_boundary.md + Story 1.5 commit 위임 패턴 유지).

## Tasks / Subtasks

- [x] **Task 1** — F5 Python wrapper + CLI + metrics emitter (AC-1)
  - [x] 1.1 `packages/athena-alpha-defense/pyproject.toml` 업데이트 — `athena-feature-store` workspace dep 이미 존재 (Story 1.1 Task 1.4 에서 선언됨), `holidays>=0.50,<1.0` 을 alpha-defense `[project.dependencies]` 에 추가 (root pyproject 는 virtual workspace 라 [project] 블록 부재); `.pre-commit-config.yaml` mypy hook `additional_dependencies` 에 `holidays>=0.50,<1.0` 추가
  - [x] 1.2 `packages/athena-alpha-defense/athena/alpha_defense/f5/__init__.py` 재노출 구성 (ChattrExecutor / DryRunChattrExecutor / LockTransition / MountState / OverrideAttemptEvent / ReadonlyMountController / SubprocessChattrExecutor)
  - [x] 1.3 `packages/athena-alpha-defense/athena/alpha_defense/f5/readonly_mount.py` 작성 — `ChattrExecutor` Protocol, `SubprocessChattrExecutor`, `DryRunChattrExecutor`, `MountState`, `LockTransition`, `ReadonlyMountController`. `Path` → `PurePosixPath` 통일 (chattr target 은 항상 WSL2 ext4 — Windows 테스트 호환성)
  - [x] 1.4 `packages/athena-alpha-defense/athena/alpha_defense/f5/cli.py` + `__main__.py` — argparse 기반 lock/unlock/status/--dry-run, `python -m athena.alpha_defense.f5` 진입점
  - [x] 1.5 `packages/athena-alpha-defense/athena/alpha_defense/f5/metrics.py` — Prometheus textfile collector emit, atomic tmp+replace (Story 1.4 patterns)
  - [x] 1.6 `packages/athena-alpha-defense/tests/test_readonly_mount.py` — 8 단위 시나리오 (스토리 7 + StrEnum semantic bonus, FakeChattrExecutor 포함)
  - [x] 1.7 `packages/athena-alpha-defense/tests/test_cli.py` — 4 CLI 시나리오 (status / lock / unlock dry-run + invalid subcommand)
  - [x] 1.8 `packages/athena-alpha-defense/tests/test_metrics.py` — 4 emitter 시나리오 (스토리 3 + naive datetime guard)
  - [x] 1.9 `uv sync` 후 `uv run pytest packages/athena-alpha-defense/tests/` → 17 passed in 0.06s
  - [x] 1.10 `lint-imports` 5/5 KEPT, `mypy --strict` Success: no issues found in 6 source files
  - [ ] 1.11 WSL2 signed commit: `feat(alpha-defense): F5 readonly-mount Python wrapper + CLI + metrics (Story 1.6 AC-1)` — **Windows 세션 commit 금지** (feedback_windows_host_commit_boundary.md), Task 6 에서 WSL2 측 일괄 위임 commit chain 으로 처리

- [x] **Task 2** — systemd units + sudoers + holiday calendar CLI + install.sh (AC-2)
  - [x] 2.1 `infra/systemd/athena-readonly-mount-lock.service` + `.timer` + unlock 대칭 (총 4 파일)
  - [x] 2.2 `infra/systemd/sudoers.d/athena-readonly-mount` — NOPASSWD drop-in, wildcard 금지, 4 허용 명령만 나열
  - [x] 2.3 `scripts/check_trading_day.py` — `holidays.country_holidays("KR")` factory 기반 KRX 거래일 판정 CLI, argparse `--as-of` `--extra-closed-days-file`, exit code contract (trade=0, skip=1)
  - [x] 2.4 `scripts/emit_readonly_mount_metric.py` — systemd ExecStopPost 진입점, `athena.alpha_defense.f5.metrics` 경유. 비-성공 exit 시 PARTIAL 로 pessimistic 기록 (Story 1.9 alert 조기 발동)
  - [x] 2.5 `infra/systemd/athena-readonly-mount.install.sh` — DRY_RUN 지원, idempotent (`cmp -s` 기반 skip), `visudo -cf` 선행 검증, `systemctl daemon-reload` + `enable --now` 2 timer, timezone + ext4 preflight warnings
  - [x] 2.6 `infra/systemd/README.md` 신규 생성 — unit-by-story 표에 신규 5 unit (4 active + 1 scaffold) 등록
  - [x] 2.7 `tests/integration/test_readonly_mount_units.py` — `@pytest.mark.integration`, 14 시나리오 (9 static ini + 5 WSL2-only subprocess)
  - [x] 2.8 `tests/integration/test_check_trading_day.py` — `@pytest.mark.integration`, 6 시나리오 (스토리 5 + malformed-line robustness)
  - [ ] 2.9 WSL2 signed commit: `feat(infra): F5 readonly-mount systemd units + sudoers + KR holiday CLI (Story 1.6 AC-2)` — **Windows 세션 commit 금지**, Task 6 에서 WSL2 일괄 위임

- [x] **Task 3** — WSL2 실 chattr E2E 통합 테스트 (AC-3)
  - [x] 3.1 `tests/integration/test_chattr_e2e.py` — `@pytest.mark.integration` + `@pytest.mark.skipif(sys.platform == "win32")`, 4 시나리오 (lock-then-write-fails-with-eperm, idempotent-cycle, git-revert-blocked, end-to-end-market-cycle)
  - [x] 3.2 test docstring 에 WSL2 prerequisite 명시 (chattr/lsattr/ext4/sudoers NOPASSWD installed via AC-2 install.sh), 추가로 sudoers probe `_ensure_sudo_chattr_nopasswd` 로 skip-rather-than-fail 디자인
  - [ ] 3.3 WSL2 Ubuntu 에서 수동 실행 후 녹색 확인 — **Task 6 PR CI 단계에서 self-hosted runner 가 자동 수행 (운영자 수동 세션 불필요)**
  - [x] 3.4 Windows 환경에서 4 시나리오 모두 skip 확인, `pytest -n auto` 전체 suite 294 passed + 14 skipped (9 WSL2-only + 5 pre-existing) 녹색 유지
  - [ ] 3.5 WSL2 signed commit: `test(alpha-defense): WSL2 E2E chattr integration (Story 1.6 AC-3)` — **Windows commit 금지**, Task 6 일괄 위임

- [x] **Task 4** — inotify watcher scaffold + OVERRIDE_ATTEMPT event contract (AC-4)
  - [x] 4.1 `packages/athena-alpha-defense/athena/alpha_defense/f5/override_event.py` — `OverrideAttemptEvent` dataclass + `__post_init__` UTC-aware + protected-root prefix validator
  - [x] 4.2 `infra/systemd/athena-inotify-watcher.service` — scaffold (`sleep infinity` placeholder), `[Install]` 섹션 생략 (enable 금지), Story 3.5 교체 anchor 주석 명시
  - [x] 4.3 `packages/athena-alpha-defense/tests/test_override_event.py` — 3 시나리오 (naive datetime reject, path outside protected root reject, asdict JSON-serialisable via default=str)
  - [x] 4.4 `tests/integration/test_readonly_mount_units.py::test_inotify_watcher_is_scaffold_with_no_install_section` + `test_systemd_analyze_verify_passes_on_all_units` 이 inotify scaffold 커버
  - [ ] 4.5 WSL2 signed commit: `feat(alpha-defense): inotify watcher scaffold + OverrideAttemptEvent contract (Story 1.6 AC-4, Story 3.5 prereq)` — Task 6 일괄 위임

- [x] **Task 5** — Documentation + deferred-work + sprint-status + final 5-gate (AC-5)
  - [x] 5.1 `docs/operating_playbook.md` — `## Story 1.6` 섹션 5 sub-section (sudoers setup, install 절차, manual ops, holiday maintenance, PARTIAL troubleshooting)
  - [x] 5.2 `_bmad-output/implementation-artifacts/deferred-work.md` — `## Deferred from: Story 1.6` 섹션 14 항목 (scope 6+ 기대치 초과)
  - [x] 5.3 `_bmad-output/implementation-artifacts/sprint-status.yaml` — `1-6-*: ready-for-dev` → `in-progress` (Task 1 시작 시) → Task 5.3 말미에서 `review` 전환
  - [x] 5.4 본 파일 Change Log v0.2.0 추가, Task 1-5 checkboxes `[x]` 전환 (1.11/2.9/3.3/3.5/4.5/5.10/Task 6 의 WSL2 commit/PR 은 Windows 세션 제약상 `[ ]` 유지), Dev Agent Record 채움
  - [x] 5.5 `uv sync --frozen` — Checked 81 packages in 3ms (lock 변동 0)
  - [x] 5.6 `uv run pytest -n auto` — **294 passed, 14 skipped in 12.10s** (Story 1.5 baseline 260 + 본 스토리 34 신규 = 294, 기대치 ≥ 281 초과)
  - [x] 5.7 `uv run pre-commit run --all-files` — 10 hooks all Passed (ruff / ruff-format / mypy / gitleaks / detect-private-key / check-yaml / check-toml / check-merge-conflict / end-of-file-fixer / trailing-whitespace)
  - [x] 5.8 `uv run lint-imports` — 5 Kept, 0 broken
  - [x] 5.9 `uv build --wheel --package athena-alpha-defense` — wheel 97B `__init__` + 730B `f5/__init__` + 150B `__main__` + 5487B `cli.py` + 6872B `metrics.py` + 3006B `override_event.py` + 11803B `readonly_mount.py` 포함 확인
  - [ ] 5.10 WSL2 signed commit: `chore(story-1.6): F5 readonly-mount infra verified, hand off to Story 1.7` — Task 6 일괄 위임

- [x] **Task 6** — Hand-off verification (본 스토리 merge 완료) — WSL2 via wsl.exe 위임 자동 실행
  - [x] 6.1 WSL2 (`wsl.exe -d Ubuntu -- bash -lc ...`) 에서 branch `story-1.6/f5-readonly-mount` 생성 + 7 signed commits: 4 initial 분할 (`feat(alpha-defense)` / `feat(infra)` / `test(alpha-defense)` / `chore(story-1.6)`) + 3 fix commits (`fix(ci)` systemd-analyze tolerance + install.sh DRY_RUN / `fix(infra)` inotify Documentation= URL format / `fix(alpha-defense)` Gemini 3 findings patch)
  - [x] 6.2 PR #13 생성 — title `feat(story-1.6): F5 readonly-mount systemd timer infrastructure (AC-1~5)`, body 는 `--body-file` 로 전달 (heredoc backtick 회피)
  - [x] 6.3 CI 7-stage green — stage-1 pre-commit pass / stage-2 pytest-unit pass / stage-3 pytest-integration pass / stage-4 snapshot-regression pass (skip marker) / stage-5 walk-forward-smoke pass (skip marker) / stage-6 cooling-gate pass (no `policy:` prefix) / stage-7 paper-replay-marker pass
  - [x] 6.4 Gemini bot 3 findings (1 HIGH emit_readonly_mount_metric + 2 MEDIUM metrics.py / readonly_mount.py) **모두 patch** (Story 1.5 의 deferred 우선 패턴이 아닌 적극 inline 수정 — Story 1.6 은 review-flip 직후 merge 이므로 시간 압박 부재) + 3 review threads `resolveReviewThread` GraphQL mutation 로 해결
  - [x] 6.5 PR #13 `gh pr merge --squash --delete-branch` 로 merge (d7833c5). 본 commit (chore(story-1.6): done) 이 sprint-status.yaml 의 `1-6-*: review → done` + 본 파일 `Status: review → done` 전환 수행, 별도 PR 생성

## Dev Notes

### Source-of-Truth Invariants (Story 1.6 가 Down-stream 전역에 고정하는 불변식)

1. **F5 의 보호 대상 파일 집합은 `/var/lib/athena/policy/policy.toml` + `/var/lib/athena/policy/flag_registry.toml` 2개로 V1.0 고정** [Task 1.3 `ReadonlyMountController.DEFAULT_PROTECTED_PATHS`]
   AR-CFG4 (architecture.md line 221) 는 `config/policy.toml` 만 명시하지만 epics.md#Story-1.6 AC 본문은 `config/flag_registry.toml` 도 명시적 추가. 본 스토리가 2개 고정 — 후속 스토리가 새 정책 파일 추가 시 (예: `tax_schedule.toml` — Story 6.5 에서 F5 대상으로 AR-CFG4 확장, epics.md line 2262 명시) 는 **Change Control 통해 `DEFAULT_PROTECTED_PATHS` 확장 + install.sh sudoers drop-in 업데이트** 2 step 필수. Story 1.5 의 `LedgerEventTypeV1` Literal 확장 패턴 동일.

2. **정책 파일 physical location 은 `/var/lib/athena/policy/` (WSL2 ext4 내부), git-tracked `config/` 는 source-of-truth but not the chattr target** [Task 2.5 install.sh, architecture.md Gap-3 lines 1211-1217]
   이유: chattr 는 ext4 전용이므로 `config/` (Windows 호스트 `/mnt/c/Users/khuk0/vibe/invest_training/config/`) 에서는 작동 불가. install.sh 가 `config/*.toml` → `/var/lib/athena/policy/*.toml` 로 복사 + git-ignored `/var/lib/athena/policy/` 는 배포 복사본. git commit 은 `config/` 만, 실 prod 정책은 `/var/lib/athena/policy/` (unlock 창에 rsync/cp 재배포). Story 1.10 이 이 재배포를 자동화할 수 있음 (deferred-work 항목).

3. **모든 chattr 경로는 `SubprocessChattrExecutor` (production) 또는 `ChattrExecutor` Protocol fake (test) 하나만 — 직접 `subprocess.run(["chattr", ...])` 호출 영구 금지** [Task 1.3, Story 1.5 Invariant #2 정신]
   Story 1.5 의 `LedgerClient.append` 단일 진입점 패턴을 F5 도 상속. Python 레벨 테스트 가능성 + Windows 개발 머신 호환성 + Story 3.5 inotify watcher 가 mount state 을 mock 주입 가능. AST 레벨 enforcement 는 Story 1.9 가 ruff custom rule 로 승격 가능 (deferred-work — 아직 V1.0 에서는 다량 위반 우려 없음).

4. **`MountState` 는 3-state 체계 — `LOCKED`, `UNLOCKED`, `PARTIAL`** [Task 1.3]
   `PARTIAL` 은 "2 파일 중 일부만 immutable" — 초기 설치 중 또는 수동 개입 직후 edge case. Story 1.9 Alertmanager 가 `PARTIAL` 5분 초과 지속 시 Medium 알림. `PARTIAL` 이 15:30 KST 에 도달해도 unlock service 는 실행 (per-file "already" 또는 chattr -i 시도 후 결과 aggregate) — unlock 은 destructive 가 아님.

5. **systemd Timer 의 `OnCalendar=Mon..Fri 09:00` 은 systemd 시스템 timezone (KST) 기준** [Task 2.1, deferred-work item "timedatectl set-timezone"]
   WSL2 가 Asia/Seoul 로 설정돼야 함. install.sh 가 `timedatectl show --property=Timezone --value` 로 현재 TZ 확인 + Asia/Seoul 아니면 경고 + exit 1 (destructive 변경은 피함 — 운영자가 수동 `timedatectl set-timezone Asia/Seoul`). Story 1.10 이 host setup 단계에서 `timedatectl set-timezone` 을 포함할 수 있음.

6. **Persistent=false 선택 근거** [Task 2.1, deferred-work item "Persistent=true 재평가"]
   `Persistent=true` 면 09:00 에 꺼져 있다 10:00 에 켜지면 "놓친" 09:00 lock 을 즉시 실행. 단점: 09:00-10:00 사이 의도적으로 unlock 중 재부팅 → 자동 relock 강제 → 운영자 놀라움. `Persistent=false` 면 missed fire 무시, 운영자가 명시적 `systemctl start ...lock.service` 로 강제 가능. V1.0 단일 운영자 상황에서 **명시적 수동 lock/unlock 을 safer default** 로 판정. Story 1.9 observability 데이터 확보 후 재평가.

7. **sudoers drop-in 은 wildcard 금지 — 구체 파일 2개 × `+i`/`-i` 2 동작 = 4 entry 로 열거** [Task 2.2]
   `khuk0 ALL=(root) NOPASSWD: /usr/sbin/chattr +i /var/lib/athena/policy/*.toml` 같은 wildcard 는 path traversal 또는 sudoers 구문 footgun (sudo 에서 `*` 과 `..` 결합 위험). 4-entry 열거가 더 길지만 명확. 새 정책 파일 추가 (Invariant #1) 시 sudoers 도 같이 확장.

8. **systemd unit 의 `User=root` 선택 vs `User=khuk0 + sudo`** [Task 2.1]
   현 디자인: service `User=khuk0`, `ExecStart=python -m athena.alpha_defense.f5 lock` → `SubprocessChattrExecutor` 가 내부에서 `sudo /usr/sbin/chattr ...` 호출 → sudoers NOPASSWD 로 무응답 승격. 대안: `User=root` + 직접 chattr (sudoers 불필요). 현 선택 이유: (a) systemd journal 에 유효 UID 가 khuk0 으로 남아 "누가 발동" 추적 용이 (audit), (b) root 가 Python 모듈 전체 를 실행하면 athena 패키지 전체가 root 권한으로 import — attack surface 증가. sudo boundary 가 chattr 4-명령으로만 국한되는 편이 위험 저감.

9. **`holidays` library 의존성 선택 근거** [Task 2.3, Project Structure Notes]
   대안 (a) 하드코딩 TOML: 매년 수동 업데이트 부담 → human failure 모드. 대안 (b) KRX API 조회: 네트워크 의존 → 장 개시 시각에 외부 API 호출은 F5 의 "장중 불변성" 철학과 모순. `holidays` PyPI 는 deterministic (빌드된 dataset) + 자동 업데이트 (pip upgrade), 임시 휴장은 `--extra-closed-days-file` 로 보강. 2026-04 기준 `holidays` 0.50+ 가 `KR` (South Korea) subdivision 지원 확인 필요 — Task 2.3 에서 `uv run python -c "import holidays; print(holidays.KR(years=2026).get('2026-05-05'))"` 로 선검증.

10. **`OverrideAttemptEvent` 는 Story 3.5 가 consume, Story 3.1 이 persist — 본 스토리는 dataclass contract 만** [Task 4.1, AC-4]
    Story 1.5 의 `LedgerEntry` 가 Story 6.1 full writer 의 contract 였던 패턴 동일. 본 스토리 의 dataclass 가 Story 3.5 의 inotify watcher emit type, Story 3.1 anti_ego_events 테이블의 `payload_json` 원형. Story 3.1 이 `OverrideAttemptEvent` → canonical JSON → SHA-256 체인 append 할 때 본 스토리의 `asdict()` 결과가 정확히 호환돼야 함 — `frozen=True, slots=True` + datetime UTC-aware validator 는 BaseDTO 호환성을 위한 필수 조치.

11. **Prometheus 메트릭 네이밍 SSOT — `athena_readonly_mount_state` / `..._last_transition_timestamp_seconds` / `..._last_lock_success_timestamp_seconds` / `..._last_unlock_success_timestamp_seconds`** [Task 1.5, architecture.md line 430]
    architecture.md Naming-Patterns 의 `athena_<component>_<metric>` 규칙 준수. Story 1.9 가 `infra/prometheus/rules/readonly_mount.rules.yml` 작성 시 동일 메트릭명 consume — 본 스토리가 emit format 을 고정. state label 은 `LOCKED|UNLOCKED|PARTIAL` 3-value (histogram 아님, gauge value `1` with label discriminator).

### Scope Boundaries — 명시적으로 OUT of Story 1.6

| Out-of-scope 항목 | 귀속 스토리 | 이유 |
|---|---|---|
| inotify watcher 실 구현 (watchfiles/inotify_simple) + OVERRIDE_ATTEMPT event persist | Story 3.5 | 본 스토리는 systemd scaffold + event dataclass contract 만 |
| `anti_ego_events` 테이블 DDL + 해시체인 + F5 event append | Story 3.1 | Ledger 체인 패턴 재사용 (Story 1.5 invariant #3 — hash_chain.py SSOT), 본 스토리는 consumer side 만 |
| Anti-Ego Firewall aggregator (F1 + F5 → 0/1 bit) | Story 3.6 | 본 스토리는 F5 `MountState` 조회 API 만 제공 |
| 이중 조건 entry gate (S_entry > θ_entry AND Firewall=1) | Story 3.7 | 본 스토리는 정책 불변성 enforce 만 |
| `config/` → `/var/lib/athena/policy/` 자동 재배포 (git hook 또는 rsync) | Story 1.10 | 본 스토리는 install.sh 1회 복사 + 수동 재배포 허용 |
| `infra/prometheus/rules/readonly_mount.rules.yml` 작성 | Story 1.9 | 본 스토리는 메트릭 emit + naming contract 만 |
| Alertmanager 라우팅 (PARTIAL 5분 초과 Medium, unlock fail Critical 등) | Story 1.9 | Prometheus rule 이 선행 |
| `timedatectl set-timezone Asia/Seoul` 자동 설정 | Story 1.10 host setup | 본 스토리는 check + warn, destructive 변경 지양 |
| `config/policy.toml` 실 파라미터 (θ_entry / α / β / γ / M_regime / M_time) 값 | Epic 2 Story 2.8 (S_entry 수식) + Story 8.4 (Bayesian 튜닝) | 본 스토리는 보호 대상 "파일 이름" 만, 파일 "내용" 은 미정 |
| `config/flag_registry.toml` 52-flag 실 ID 열거 | Epic 2 Story 2.1 | 본 스토리는 파일 존재성만 보장 (빈 TOML 또는 minimal stub) |
| Story 3.5 가 완성할 watcher 의 ExecStart 실 채우기 | Story 3.5 | 본 스토리는 unit 파일 scaffold + sleep infinity placeholder 만 |
| 장중 override 시도 실 테스트 (사용자가 의도적으로 git revert 시도하는 시나리오) | Story 3.5 + Story 3.7 통합 테스트 | 본 스토리는 chattr 레벨 E2E (Task 3.1) 까지 |
| ruff custom rule: direct `subprocess.run(["chattr", ...])` 금지 | Story 1.9 | 본 스토리는 Python-level invariant 만, AST 승격은 후속 |
| KRX 임시 휴장 자동 fetch (OpenKRX API) | V1.1+ (또는 Story 1.10) | 본 스토리는 `--extra-closed-days-file` 수동 보강 |
| `sudoers` 전체 감사 (본 스토리 외의 NOPASSWD 정책) | Story 6.6/6.7 (준법감시인 워크플로우) | 본 스토리는 chattr 4-entry 만 |

유혹이 들면 **멈추고 핸드오프**. F5 의 본질은 "OS primitives 레벨 tamper-resistance" — 그 이상의 logic 은 Story 3.x / Epic 2+ 의 책임.

### Architecture Patterns & Constraints (이 스토리의 payload)

- **OS primitives + application wrapper 의 이중 레이어** [AR-SEC3, D9, D17]: chattr 는 OS layer, `ReadonlyMountController` 는 Python layer. 둘 중 하나만 있으면 (a) Python 전용 시 application 로직 실수로 우회 가능, (b) OS 전용 시 테스트 불가 + Windows 개발 불가. **둘 다 필수**.
- **systemd Timer 2 pair pattern** [Task 2.1]: `-lock.service + -lock.timer` + `-unlock.service + -unlock.timer`. 단일 service + 2 timer 로 분기하면 argparse 필요 → service unit file 복잡도 증가. 2 pair 가 systemd 관례 (1 unit = 1 action).
- **`ExecStartPre=/path/to/check_trading_day.py` 패턴** [Task 2.1]: systemd 가 ExecStartPre exit != 0 시 service 를 skip — 이 방식이 `OnCalendar` 에 휴일 로직을 inline 시키기 (OnCalendar 는 제한적 syntax) 보다 유연.
- **sudoers drop-in `/etc/sudoers.d/<name>`** [Task 2.2, Story 1.5 operating_playbook § P16]: `/etc/sudoers` 본체 수정 금지 — 업그레이드 시 충돌. drop-in 은 `visudo -cf` 선행 검증 필수 (잘못된 구문은 sudo 전체를 망가뜨림).
- **`subprocess.run(..., encoding="utf-8", errors="replace")`** [Task 1.3, Story 1.5 Debug Log #1]: Windows 로컬 cp949 기본 때문에 항상 encoding 명시. Story 1.1 Debug Log #8 에서 학습된 trap.
- **atomic write pattern `tmp + os.replace`** [Task 1.5, Story 1.5 Task 3.2]: Prometheus textfile collector 가 half-written 파일 읽는 것 방지. `open(tmp, "w")` → `os.replace(tmp, final)` 는 POSIX atomic rename.
- **`@pytest.mark.skipif(sys.platform == "win32")`** [Task 3.1, Story 1.5 `test_init_external_backup_dryrun.py` 의 platform skip 패턴]: Windows 개발 머신에서 실 Linux-only 기능 (chattr, cryptsetup, systemd) 테스트 skip. WSL2 CI runner 에서만 실행.
- **`@dataclass(frozen=True, slots=True)`** [Task 4.1, Pydantic BaseDTO 와 대안]: `OverrideAttemptEvent` 는 Pydantic 2 의 full BaseDTO 필요 없음 (runtime validation 비중이 낮음, 내부 dataclass 면 충분). `__post_init__` 에서 UTC aware 검증.
- **Idempotency invariants** [Task 1.3 `lock()` / `unlock()` + Task 2.5 install.sh]: 모든 state-changing 작업은 "이미 원하는 상태" 면 no-op. systemd Restart=on-failure 가 중복 호출해도 안전.
- **Graceful platform degradation** [AR-SEC3, Task 1.3 `ChattrExecutor`]: Linux ext4 가 없는 환경에서도 Python 모듈 import 는 성공해야 함 (fake executor 사용 시). 실 `SubprocessChattrExecutor` 는 Linux 에서만 동작 — import-time 에 platform check 는 하지 않음, runtime 에 `subprocess` 에서 자연스럽게 실패.

### Threat Model Notes (본 스토리의 방어 범위 명시)

adversarial bypass 시나리오 (본 스토리 scope 내):

1. **장중 `config/policy.toml` θ_entry 수정 유혹** (손실 중 "이번에만 θ 를 0.1 낮춰 진입" 흥정). 방어:
   - **OS layer**: `chattr +i /var/lib/athena/policy/policy.toml` — 텍스트 에디터·`cat >`·`tee`·`sed -i` 모두 `Operation not permitted`.
   - **UID bypass 차단**: `chattr +i` 는 root (uid=0) 도 수정 불가 — Linux filesystem immutable flag 의 정신.
   - **경로 bypass 차단**: `config/policy.toml` (git checkout) 을 수정해도 prod 은 `/var/lib/athena/policy/policy.toml` — 다른 파일.
   - **경로 replace 차단**: `mv /tmp/new_policy.toml /var/lib/athena/policy/policy.toml` 도 기존 파일이 immutable 이므로 실패 (rename 은 target 파일을 unlink 시도).

2. **`git checkout <old_sha> -- config/policy.toml` → `cp` → `/var/lib/athena/policy/policy.toml` 덮어쓰기 시도 (git revert)**. 방어:
   - Invariant #1 과 동일 — chattr flag 가 destination 파일에 걸려 있으므로 cp 가 실패.
   - `unlink + cp` 도 chattr +i 가 unlink 차단 → 실패.

3. **sudoers 탈취 또는 sudoers rule 변조** (공격자가 sudoers 을 수정해 `chattr -i` 임의 실행). 방어:
   - sudoers 는 root-only write (`/etc/sudoers.d/` permissions 0440 root:root).
   - OS 계정 탈취 시 방어 무력화 — Athena scope 밖 (physical/account security).
   - Story 6.6/6.7 (준법감시인 워크플로우) 가 월간 감사에서 sudoers diff 를 외부 승인권자에게 보고.

4. **시간 조작으로 "장 마감" 상태 위조** (`timedatectl set-time 16:00` 으로 15:30 timer 발동시킨 후 수정 시도). 방어:
   - systemd timer 는 wallclock 기반 → 속일 수 있음.
   - 하지만 현 상황에서 이 공격은 스토리 내부의 self-override 시도 — 운영자 본인이 공격자. 5계층 방어의 hardware UPS + NTP + Story 6.2 외장 segment_hash 가 post-hoc 증거.
   - Story 1.3 의 `check_cooling.py` 음수 delta issue (deferred-work) 와 동일 root cause — 시간 조작은 Epic 6 Story 6.2 의 외부 anchor (S3 Object Lock 타임스탬프 + NTP signed) 로 검출.

5. **WSL2 reinstall 로 `/var/lib/athena/policy/` 완전 초기화 + 새 정책 덮어쓰기**. 방어:
   - `config/` git-tracked SSOT + Story 1.3 의 policy-commit cooling gate → 공식 정책 변경은 여전히 72h cooling 필요.
   - 공격자가 `config/policy.toml` 을 수정 후 WSL2 reinstall + 새 `install.sh` 실행 → **여전히 git history 에 남음**. 외부 증거 (PR 커밋 Signed-Off-By, GitHub Actions log) 가 사후 탐지.
   - 본 스토리 scope 외 — Epic 8 Story 8.6 (정책 변경 감사 로그 + 외부 승인권자 서명) 가 궁극적 cover.

6. **Process crash 중 partial lock (pathA=LOCKED, pathB=UNLOCKED)**. 방어:
   - `MountState.PARTIAL` 반환 + systemd `Restart=on-failure` 가 자동 재시도.
   - Prometheus alert (Story 1.9) 가 `PARTIAL` 5분 초과 시 Medium 알림.
   - 운영자 수동 `systemctl start athena-readonly-mount-lock.service` 로 복구.

7. **inotify watcher 미구현 (Story 3.5 지연) 시 OVERRIDE_ATTEMPT 미포착**. 방어:
   - 본 스토리 단독 scope 에서는 **포기** — OVERRIDE_ATTEMPT persist 는 Story 3.1/3.5 책임.
   - 대체 로그: systemd journal + `kernel audit subsystem` (`auditd`) 로도 chattr 플래그 변경 + write attempt 을 캡처 가능 (V1.1+ 옵션).

각 deeper bypass 는 후속 스토리 (3.1 체인, 3.5 watcher, 1.9 observability, 6.2 3-way verify, 8.6 정책 감사) 가 cover. 본 스토리는 "OS-layer tamper-resistance substrate" 까지 책임.

### Testing Standards

- **Framework**: pytest, Story 1.4/1.5 와 동일 (`asyncio_mode=strict`, `--strict-markers`). 본 스토리는 async 테스트 0건.
- **Determinism**: `ChattrExecutor` Protocol 덕에 단위 테스트는 fake in-memory 상태로 결정론. 실 chattr 통합 테스트는 `tmp_path` 기반 ext4 경로.
- **Marker 사용**:
  - 순수 단위 (FakeChattrExecutor 주입) → no marker, stage-2 — `test_readonly_mount.py`, `test_cli.py`, `test_metrics.py`, `test_override_event.py`
  - 실 systemd-analyze / visudo / holidays library / install.sh → `@pytest.mark.integration`, stage-3 — `test_readonly_mount_units.py`, `test_check_trading_day.py`
  - 실 chattr (WSL2 ext4) → `@pytest.mark.integration` + `@pytest.mark.skipif(sys.platform == "win32")`, stage-3 — `test_chattr_e2e.py`
  - `@pytest.mark.snapshot` / `walk_forward` / `@pytest.mark.asyncio` / `@pytest.mark.slow` 사용 없음
- **Platform skip 패턴** [Story 1.5 `test_init_external_backup_dryrun.py`]: `test_chattr_e2e.py` 는 Windows 세션에서 skip, WSL2 에서 실행. CI runner (self-hosted Trading PC WSL2) 에서는 녹색.
- **Temp path 격리**: 모든 테스트가 `tmp_path` fixture 경유, 실 `/var/lib/athena/policy/` 오염 금지 — 운영 prod 환경과 별개.
- **systemd-analyze verify**: unit 파일 문법 검증의 공식 수단. subprocess 로 호출, exit code 체크. 선행 조건: systemd 254+ 설치 (WSL2 Ubuntu 24.04 기본).
- **visudo -cf**: sudoers 구문 검증. `/etc/sudoers.d/athena-readonly-mount` 을 tmp 로 복사 후 `visudo -cf <tmp>` 로 비파괴적 테스트.
- **holidays library stable API**: `holidays.KR(years=2026)` 반환 dict 의 keys 는 `datetime.date` — string 비교 주의. `today in kr` 는 date 비교 (KRX holiday 수 약 15/year).
- **Coverage gate 없음** — Story 1.3/1.4/1.5 와 동일, V1.0 본인 전용 scope.

### Project Structure Notes

Story 1.6 은 `athena-alpha-defense` 패키지의 첫 실 코드 + F5 하위 디렉토리 생성. 추가되는 경로:

```
packages/athena-alpha-defense/athena/alpha_defense/
  └── f5/
      ├── __init__.py               # NEW Task 1.2 (재노출)
      ├── readonly_mount.py         # NEW Task 1.3 (ChattrExecutor, ReadonlyMountController)
      ├── cli.py                    # NEW Task 1.4 (lock/unlock/status CLI)
      ├── metrics.py                # NEW Task 1.5 (Prometheus textfile emit)
      └── override_event.py         # NEW Task 4.1 (OverrideAttemptEvent dataclass)

packages/athena-alpha-defense/tests/
  ├── test_readonly_mount.py        # NEW Task 1.6 (7 시나리오, FakeChattrExecutor)
  ├── test_cli.py                   # NEW Task 1.7 (4 CLI 시나리오)
  ├── test_metrics.py               # NEW Task 1.8 (3 emit 시나리오)
  └── test_override_event.py        # NEW Task 4.3 (2 dataclass 시나리오)

scripts/
  ├── check_trading_day.py          # NEW Task 2.3 (KRX 거래일 판정 CLI)
  └── emit_readonly_mount_metric.py # NEW Task 2.4 (systemd ExecStopPost 진입점)

infra/systemd/
  ├── athena-readonly-mount-lock.service       # NEW Task 2.1
  ├── athena-readonly-mount-lock.timer         # NEW Task 2.1
  ├── athena-readonly-mount-unlock.service     # NEW Task 2.1
  ├── athena-readonly-mount-unlock.timer       # NEW Task 2.1
  ├── athena-inotify-watcher.service           # NEW Task 4.2 (scaffold, disabled)
  ├── athena-readonly-mount.install.sh         # NEW Task 2.5
  ├── sudoers.d/
  │   └── athena-readonly-mount                # NEW Task 2.2 (NOPASSWD drop-in)
  └── README.md                                # NEW or MODIFIED Task 2.6 (unit-by-story 표)

tests/integration/
  ├── test_readonly_mount_units.py             # NEW Task 2.7 (6 systemd/visudo 시나리오)
  ├── test_check_trading_day.py                # NEW Task 2.8 (5 holiday/weekend 시나리오)
  └── test_chattr_e2e.py                       # NEW Task 3.1 (4 WSL2 E2E 시나리오)

packages/athena-alpha-defense/pyproject.toml   # MODIFIED Task 1.1 (athena-feature-store workspace dep)
pyproject.toml                                 # MODIFIED Task 1.1 (holidays>=0.50 runtime dep)
docs/operating_playbook.md                     # MODIFIED Task 5.1 (## Story 1.6 섹션 5 sub-section)
_bmad-output/implementation-artifacts/deferred-work.md  # MODIFIED Task 5.2
_bmad-output/implementation-artifacts/sprint-status.yaml  # MODIFIED Task 5.3
```

**명시적으로 생성 금지**:
- `packages/athena-alpha-defense/athena/alpha_defense/f1/` — Story 3.2/3.3/3.4 scope
- `packages/athena-alpha-defense/athena/alpha_defense/m1/`, `m2/`, `m3/`, `m9/`, `m13/`, `m14/`, `m19/`, `m22/` — Epic 2/Story 4.4/4.5 scope
- `packages/athena-alpha-defense/athena/alpha_defense/base.py` (VetoFlag / Scorer 추상) — 본 스토리는 F5 전용, 추상 기반은 Story 2.1 이 52-flag registry 와 함께 정의
- `infra/prometheus/rules/readonly_mount.rules.yml` — Story 1.9
- `config/flag_registry.toml` 의 실제 52-flag enumeration — Story 2.1 (본 스토리는 파일 존재 보장을 위한 minimal stub 만 — `/var/lib/athena/policy/flag_registry.toml` 가 empty TOML 이어도 chattr 동작 검증 가능)

**허용되는 architecture.md 이탈 (Dev Agent Record 에 기록)**:
- architecture.md line 818 의 `athena-readonly-mount.service` (단수) → 본 스토리는 `-lock.service` + `-unlock.service` 2 pair 로 split. 이유: 1 unit = 1 action systemd 관례 + argparse 회피. 의미는 동등. architecture.md 는 "개념 단위" 1 개, 구현은 2 pair.
- architecture.md line 743 `readonly_mount.py` (단수, `chattr +i 래퍼`) → `readonly_mount.py` + `cli.py` + `metrics.py` + `override_event.py` 4 파일로 분리. 이유: 단일 책임 원칙 + 테스트 가능성 (CLI 와 core 로직 분리).
- Storytime invariant test `test_trading_pc_write_scope.py` 확장 없음 — 본 스토리는 `decisions.duckdb` write path 미변경 (F5 는 filesystem 조작만). Story 1.5 의 6 테이블 invariant 유지.

### Previous Story Intelligence (Story 1.1/1.2/1.3/1.4/1.5 이관 사항 + 본 스토리 영향)

1. **`scripts/` 패턴 + per-file-ignore 일관성** [Story 1.3 invariant #6, 1.4 Task 2.3, 1.5 prev intel #1]
   본 스토리의 2개 새 `scripts/*.py` (`check_trading_day.py`, `emit_readonly_mount_metric.py`) 는 subprocess 호출 있음 (`check_trading_day.py` 는 없음, `emit_readonly_mount_metric.py` 는 `athena.alpha_defense.f5.metrics` import 만 — subprocess 없음). → per-file-ignore `S404/S603/S607` 미추가. `install.sh` 는 bash → ruff 미적용. `check_trading_day.py` 가 `holidays` import 만 → Clean.

2. **mypy hook `additional_dependencies` 일관성** [1.1 deferred-work 5번, 1.4 Task 1.7, 1.5 Task 5.1]
   본 스토리는 `holidays>=0.50,<1.0` 추가. `.pre-commit-config.yaml` mypy hook `additional_dependencies` 에 `holidays>=0.50` 추가 필요 — Task 1.1 subtask. `holidays` 는 자체 type hints 포함 (0.50+) 이므로 `types-holidays` 는 불필요.

3. **Python 3.13 + uvloop 0.22.1 호환** [1.1 invariant #1]
   `holidays` 0.50+ 는 Python 3.13 호환 (2026-04 시점 확인). `uv add holidays>=0.50,<1.0` 후 `uv.lock` 재생성 시 호환 실패 시 0.48-0.49 범위 시도.

4. **`cp949 codec trap`** [1.1 Debug Log #8, 1.4 prev intel #3, 1.5 Debug Log #1]
   본 스토리의 모든 `subprocess.run()` 호출 (`SubprocessChattrExecutor`, `install.sh` 내부 python -c, test 의 `systemd-analyze verify`, `visudo -cf`) 에 `encoding="utf-8", errors="replace"` 명시. bash heredoc 에 한국어 포함 금지 (install.sh 내부 NOTE 는 영문만).

5. **WSL2 commit 위임** [1.2 Task 5.4, 1.3 Task 5.6, 1.5 Completion Notes]
   본 스토리의 모든 commit (Task 1.11, 2.9, 3.5, 4.5, 5.10, 6.x) 은 signed, WSL2 셸에서만. 현 Windows 세션의 `feedback_windows_host_commit_boundary.md` 가 명시적으로 요구: `git commit` 직접 실행 금지, WSL2 위임. PR 생성 및 merge 도 WSL2 측 `gh pr create` / `gh pr merge`.

6. **`policy:` prefix 불필요** [1.3 invariant #3]
   본 스토리는 `config/policy.toml` / `config/flag_registry.toml` 파일 **내용 자체를 수정하지 않음** — 보호하는 infra (systemd unit + chattr wrapper + sudoers) 만 추가. 모든 commit 은 `feat(alpha-defense)` / `feat(infra)` / `test(...)` / `chore(story-1.6)` prefix. 72h cooling gate 미적용. 단, install.sh 가 `config/policy.toml` 을 `/var/lib/athena/policy/policy.toml` 로 복사할 뿐 — git-tracked `config/` 는 touch 하지 않음.

7. **Source-of-Truth Invariants #1 BaseDTO 상속 + self-describing row** [1.4 Invariant #1, 1.5 prev intel #10]
   본 스토리의 `OverrideAttemptEvent` dataclass 는 BaseDTO 상속 아님 (Pydantic 아님, `@dataclass`) — 이유: runtime validation 부담 낮음, Story 3.1 persist 시점에 canonical JSON → hash 로 변환되는 최종 형태만 중요. `attempted_at_utc` UTC-aware 는 `__post_init__` 에서 assert. Story 3.1 이 실제 persist 할 때 BaseDTO-friendly 변환 필요 여부 재검토.

8. **`test_trading_pc_write_scope.py` + `test_dto_ddl_parity.py` 미확장** [1.4 Task 4.3, 1.5 Task 1.7]
   본 스토리는 `decisions.duckdb` write path 건드리지 않음 → 두 regression test 파일 touch 금지. 6 테이블 invariant 유지.

9. **Build hook `force-include`** [1.5 Debug Log #3]
   본 스토리는 `athena-alpha-defense` 의 wheel 이 `f5/*.py` (Python 파일만) + `tests/` 는 자동 포함. `.sql`, `.service`, `.timer`, `.sh`, `sudoers drop-in` 은 wheel 에 포함 안 됨 — 이들은 `infra/` 하위 git-tracked 인프라 파일로 운영자 install.sh 경유 배포. Story 1.5 의 `schema.sql` 과는 다른 역할.

10. **DuckDB / hash_chain 재사용 없음** [1.5 Invariant #3]
    본 스토리는 DuckDB 사용 없음, SHA-256 hash 계산 없음. Story 3.1 anti_ego_events 체인이 `athena.execution.ledger.hash_chain` 을 reuse 할 때 본 스토리의 `OverrideAttemptEvent` 가 canonical JSON payload 로 직렬화되는 통합 지점 — 본 스토리는 통합 이전까지의 contract 만.

11. **sudoers drop-in 패턴** [1.5 operating_playbook § P16]
    Story 1.5 가 `scripts/init_external_backup.sh` 에서 cryptsetup 용 sudoers NOPASSWD 를 요구했음 — 본 스토리가 chattr 용 sudoers drop-in 을 동일 패턴으로 확장. operating_playbook `## Story 1.5` 의 sudoers 섹션과 `## Story 1.6` 섹션이 cross-reference.

12. **Idempotent install.sh** [1.5 deferred-work "외장 SSD 실 LUKS" + 1.4 `install_logger_sync_unit.sh`]
    본 스토리의 `athena-readonly-mount.install.sh` 는 두 선행 install 스크립트의 패턴 계승 — DRY_RUN 지원, 두 번째 실행 시 "already installed" skip + exit 0. Story 1.4 의 `install_logger_sync_unit.sh` 와 `scripts/init_external_backup.sh` 를 참고.

13. **Python venv 경로 hardcoding** [1.4 deferred-work "systemd unit 절대 경로"]
    본 스토리의 4 systemd service 의 `ExecStart` 는 `/home/khuk0/invest_training/.venv/bin/python` hardcoded — Story 1.4 와 동일. 설치 템플릿화 (envsubst) 는 Story 1.7 과 묶여 처리 예정 (deferred-work 항목). 단일 호스트 단일 UID 가정 V1.0 에서는 문제 없음.

### Git Intelligence Summary

**Recent commits on `master` (상위 5건, 2026-04-23 기준):**
```
cbcd534 chore(story-1.5): review-flip complete → done (PR #10 merged, 3 Gemini findings deferred) (#12)
884600a Story 1.5: Pre-Trade Ledger SHA-256 chain substrate (FR38/FR39) (#10)
8fdda31 Story 1.4: DuckDB + Parquet shard + rsync pipeline (AC-1~5, BMAD CR complete) (#11)
14bc7e4 docs(story-1.3): Task 1.6/5.5/6.6 evidence + checkbox [x] (review-flip rigor) (#9)
2ea0770 fix(ci): checkout PR head SHA on stage-6/7 (and all stages for consistency) (#7)
```

Story 1.5 완료 상태로 master clean. 본 스토리의 신규 branch `story-1.6/f5-readonly-mount` 에서 작업.

**본 스토리의 커밋 전략** (총 6건 예상, 모두 signed WSL2 측에서 수행):
- T1 → `feat(alpha-defense): F5 readonly-mount Python wrapper + CLI + metrics (Story 1.6 AC-1)`
- T2 → `feat(infra): F5 readonly-mount systemd units + sudoers + KR holiday CLI (Story 1.6 AC-2)`
- T3 → `test(alpha-defense): WSL2 E2E chattr integration (Story 1.6 AC-3)`
- T4 → `feat(alpha-defense): inotify watcher scaffold + OverrideAttemptEvent contract (Story 1.6 AC-4, Story 3.5 prereq)`
- T5 → `chore(story-1.6): F5 readonly-mount infra verified, hand off to Story 1.7`
- T6 → PR 생성·merge 후 sprint-status `done` 전환 commit (별도)

Task 3.3 (실 WSL2 chattr 동작 검증) 은 **운영자 환경 의존** — 현 `check_trading_day.py` + `systemd-analyze verify` 는 Windows Python 에서도 가능 (holidays/subprocess 만) 이지만 `test_chattr_e2e.py` 는 WSL2 ext4 필수. CI self-hosted runner (Trading PC WSL2) 에서 자동 실행되므로 PR 단계에서 녹색 확인.

### Latest Tech Information

| Library / Tool | Frozen Version | 본 스토리에서 검증할 동작 |
|---|---|---|
| holidays | >=0.50,<1.0 (본 스토리 신규) | `holidays.KR(years=2026)` 반환 dict (date → name), 한국 공휴일 + 대체공휴일 포함. Korean 지역 분화 (subdiv) 는 `holidays` 0.50+ 에서 안정 — subdiv 미지정 시 default KR 전체 공휴일. `today in kr` 는 date 비교. API: `holidays.HolidayBase.__contains__` 는 date 또는 string 모두 수용. **선검증**: `uv run python -c "import holidays; kr = holidays.KR(years=2026); print(kr.get(date(2026, 5, 5)))"` → `'Children's Day'` (또는 한국어 locale 시 `'어린이날'`) |
| chattr | util-linux 2.38+ (Ubuntu 24.04) | `chattr +i /path` 플래그, `lsattr /path` 출력 `----i---...` 중 `i` 위치 파싱. Root 도 immutable 파일 수정 불가. `chattr -i` 로만 해제. |
| lsattr | util-linux 2.38+ | `lsattr -d /path` 단일 파일 attrs 출력. 파싱: `re.match(r"^([a-zA-Z-]+)\s+/", output)` 에서 flags 문자열 추출, `'i' in flags` 확인. |
| systemd | 254+ (Ubuntu 24.04 — 1.4 prev intel, 1.2 확정) | `OnCalendar=Mon..Fri 09:00` (5-digit wildcard + weekday), `ConditionPathExists`, `ExecStartPre/Start/StopPost` chain, `Restart=on-failure`, `Persistent=true/false`. `systemd-analyze verify` + `systemd-analyze calendar`. |
| sudo | 1.9.15+ (Ubuntu 24.04) | `/etc/sudoers.d/<file>` drop-in 0440 root:root, `NOPASSWD:` 구문, specific-path entries (wildcard 없이). `visudo -cf <file>` 문법 검증 exit 0. |
| python-holidays | (alias for `holidays`) | — |

**Platform-specific caveat:**
- chattr/lsattr: WSL2 Ubuntu 에서만 테스트 가능. Windows 는 ACL 기반으로 동등 기능 없음 — `pytest.mark.skipif(sys.platform == "win32")` 로 건너뜀.
- systemd: WSL2 Ubuntu 24.04+ systemd 지원 (`/etc/wsl.conf` 의 `[boot] systemd=true` 설정 필요 — Story 1.2 에서 활성화 확인). Windows 에서 `systemd-analyze verify` 불가 — Story 1.4 가 이 test 를 integration marker 로 격리한 패턴 재사용 (`@pytest.mark.integration` + skipif).
- `holidays.KR` 은 2026-04 시점 KR `holidays` 0.50 이상에서 안정적 — 임시공휴일 (예: 2020년 8월 17일 광복절 대체공휴일) 는 library 가 사후 업데이트 반영. 선제적으로 KRX 임시 휴장 (수해 등 불가항력) 은 library 가 **반영 안 함** — `--extra-closed-days-file` 수동 보강 필수.
- Windows `os.replace` read-only 대상 처리 [1.5 Latest Tech]: 본 스토리의 `metrics.py` 는 read-only 파일 덮어쓰기 시나리오 없음 (textfile collector 는 항상 rw). 문제 없음.

### References

- **Epic · Story source**:
  - `_bmad-output/planning-artifacts/epics.md#Epic-1` (line 420), `#Story-1.6` (lines 592-623)
- **Architecture 핵심 결정**:
  - `architecture.md#D9` (line 299 — chattr +i 장중 immutable, Windows ACL 대비 tamper-resistance)
  - `architecture.md#D17` (line 340 — Trading PC WSL2 Ubuntu 24.04 LTS chattr 지원)
  - `architecture.md#D18` (lines 343-345 — Trading PC systemd supervisor)
  - `architecture.md#AR-SEC3` (line 199 — systemd timer on 09:00/15:30 KST)
  - `architecture.md#AR-CFG4` (line 221 — policy.toml F5 읽기전용 대상)
  - `architecture.md#Gap-Analysis-Gap-3` (lines 1211-1217 — WSL2 ext4 경로 규칙, `/mnt/c` 금지)
- **Architecture file 구조**:
  - `architecture.md#Complete-Project-Directory-Structure` (lines 742-745 — `athena-alpha-defense/alpha_defense/f5/readonly_mount.py` 파일 위치)
  - `architecture.md#Requirements-to-Structure-Mapping` (line 966 — FR16 → `packages/athena-alpha-defense/.../f5/` + `infra/systemd/athena-readonly-mount.service`)
  - `architecture.md#Process-Boundaries` (line 926 — `athena-readonly-mount` systemd timer 09:00/15:30 KST)
  - `architecture.md#Import-Hierarchy` (lines 902-915 — `alpha_defense ← feature_store ← core`)
- **Architecture naming**:
  - `architecture.md#Naming-Patterns` (line 424 — `SCREAMING_SNAKE_CASE` 상수 · line 430 — `athena_<component>_<metric>` Prometheus 메트릭 네이밍)
  - `architecture.md#Key-Strengths` (line 1286 — F5 하드락 OS-레벨 물리 구현)
- **PRD 요구사항**:
  - `prd.md#FR16` (line 934 — F5 장중 파라미터·정책·git revert 물리 차단)
  - `prd.md#FR15` (line 933 — F1·F5 Anti-Ego Firewall 집계)
  - `prd.md#FR57` (line 993 — 파라미터·정책 변경 git signed + 72h cooling + Paper 재검증)
  - `prd.md#NFR-S4` (line 1023 — 장중 파라미터·정책 저장소 읽기전용 마운트)
  - `prd.md#NFR-R5` (line 1016 — 72h cooling F5 enforce)
  - `prd.md#NFR-S1` (line 1020 — OS Keychain, `.env` 금지 — sudoers drop-in 은 Keychain scope 외)
  - `prd.md#NFR-A3` (line 1049 — anti_ego_events 체인 — Story 3.1 이 본 스토리의 OverrideAttemptEvent 를 consume)
- **Downstream Story 상세 (선행 계약 확인)**:
  - `epics.md#Story-3.1` (lines 1131-1162 — anti_ego_events append-only table, SHA-256 체인, OverrideAttemptEvent JSON payload)
  - `epics.md#Story-3.5` (lines 1283-1297 — F5 Override inotify Watcher + Logging, 본 스토리의 scaffold + OverrideAttemptEvent 를 consume)
  - `epics.md#Story-3.6` (lines 1323-1340 — Anti-Ego Firewall aggregator, F5 `MountState` 조회)
  - `epics.md#Story-3.7` (lines 1368-1391 — 이중 조건 entry gate, 정책 장중 불변성 전제)
  - `epics.md#Story-2.8` (lines 913-925 — S_entry 수식 end-to-end, θ_entry · α/β/γ · M_regime · M_time 처음 실 사용)
  - `epics.md#Story-1.9` (lines 691-723 — Observability Stack, `athena_readonly_mount_*` Prometheus rule 통합)
  - `epics.md#Story-1.10` (lines 725-759 — Backup Schedule Automation, `config/` → `/var/lib/athena/policy/` 재배포 자동화 가능성)
- **Story 1.1 참조 (선행)**: `_bmad-output/implementation-artifacts/1-1-프로젝트-bootstrap-uv-monorepo-scaffold.md` § "Task 1.4" (athena-alpha-defense scaffold, pyproject.toml 초기 상태)
- **Story 1.2 참조 (선행)**: `_bmad-output/implementation-artifacts/1-2-환경-secrets-infrastructure-wsl2-os-keychain-ssh-signing.md` § "Task 1" (WSL2 Ubuntu + systemd 활성화 검증)
- **Story 1.3 참조 (선행)**: `_bmad-output/implementation-artifacts/1-3-self-hosted-ci-cd-pipeline-7단계-gate.md` § "policy-prefix-guard" (본 스토리는 `policy:` prefix 미해당 — infra 변경만)
- **Story 1.4 참조 (선행)**: `_bmad-output/implementation-artifacts/1-4-duckdb-parquet-shard-rsync-data-pipeline.md`
  - § "systemd unit 패턴" — `athena-logger-sync.service` + `.timer` 의 `OnBootSec`/`OnUnitActiveSec`, `ExecStopPost` 메트릭 emit 패턴
  - § "install_logger_sync_unit.sh" — DRY_RUN + idempotent 설치 helper 의 원형
  - § "Testing Standards" — `@pytest.mark.integration` marker 정책
- **Story 1.5 참조 (선행, 직접 상속)**: `_bmad-output/implementation-artifacts/1-5-pre-trade-ledger-초기-세그먼트-sha-256-체인.md`
  - § "Source-of-Truth Invariants" (1-11 모두 본 스토리에 참조적 적용 — 특히 #2 단일 진입점 패턴, #11 application-layer + AST 다층 방어)
  - § "Threat Model Notes" (bypass 시나리오 분류 패턴)
  - § "Testing Standards" (marker + platform skip + tmp_path)
  - § "Project Structure Notes" (디렉토리 트리 확장 패턴)
  - § "Previous Story Intelligence" (templating 출처)
  - § "sudoers NOPASSWD playbook 기록" (P16 review patch — 본 스토리가 동일 패턴을 chattr 로 확장)
- **Story 1.5 deferred-work**: `_bmad-output/implementation-artifacts/deferred-work.md` § "Deferred from: Story 1.5" 의 LUKS / S3 / Prometheus rule 은 본 스토리와 무관 (본 스토리는 F5 readonly mount 만)
- **Implementation Readiness Report**: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-21.md` — READY verdict, Story 1.6 은 Critical/Major 없음
- **Project context (user memory)**:
  - `reference_athena_prd.md` — PRD 위치·구조
  - `reference_athena_architecture.md` — Architecture 위치·구조
  - `reference_athena_epics.md` — Epics 위치·구조
  - `feedback_task_completion_integrity.md` — "deferred" 라벨로 [ ] 회피 금지, review flip 전 모든 [ ] 의 이유 자문
  - `feedback_windows_host_commit_boundary.md` — Windows 세션 `git commit` 금지, WSL2 위임
  - `feedback_athena_design_priority.md` — tradeoff 발생 시 엄격한 Veto 우선, F5 의 "장중 불변성" 은 최우선 원칙

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) — `claude-opus-4-7[1m]` — invoked via `/bmad-agent-dev` Amelia persona + `bmad-dev-story` skill.

### Debug Log References

- **Debug #1 — `.venv` 손상된 reparse point.** 세션 시작 시 `uv sync` 가 `.venv\lib64`  (`Mode: d----l`, `Attributes: Directory, ReparsePoint`, LinkType 빈 문자열) 제거에 실패 (`os error 5 액세스 거부`). 원인: 이전 WSL2 세션의 Linux symlink 가 Windows 에서 깨진 dir junction 으로 보임. 해결: PowerShell `Remove-Item .venv\lib64 -Force -Recurse` 로 정리 후 `rm -rf .venv && uv sync` 로 재생성. 의의: Story 1.5 Debug Log 와 무관한 신규 trap — Trading PC WSL2 전용 환경 전환 이전까지는 Windows 재구축 세션에서 재발 가능, Story 1.7 host split 완료 전까지는 동일 pattern 필요시 재수행.

- **Debug #2 — Windows 에서 `Path("/var/lib/...")` → `WindowsPath` 백슬래시 변환.** Task 1.6 초기 실행에서 3개 테스트 (`test_path_outside_protected_root_raises_value_error` / CLI status / CLI lock dry-run) 가 실패. 원인: `pathlib.Path` 가 플랫폼별 (Windows 에서는 `\var\lib\...`). chattr 타겟은 의미상 항상 POSIX. 해결: `readonly_mount.py` / `override_event.py` 전체를 `PurePosixPath` 로 통일. FakeChattrExecutor / 테스트 / dataclass 모두 platform-independent POSIX-semantic 보장. production code 자체가 더 명확해지는 부수 이익.

- **Debug #3 — `holidays.KR` mypy attr-defined error.** `scripts/check_trading_day.py` 에서 `holidays.KR(years=today.year)` 이 mypy strict 에서 `Module has no attribute "KR"` 발생. 원인: `holidays` 라이브러리가 런타임에 동적 생성하는 country class — static type checker 가 인식 불가. 해결: 타입화된 factory `holidays.country_holidays("KR", years=today.year)` 로 전환. 기능적으로 동등, mypy strict 호환.

- **Debug #4 — ruff DTZ001 on intentional naive datetime test.** `test_metrics.py::test_naive_datetime_raises_value_error` 가 의도적으로 naive `datetime(2026, 4, 23, 9, 0)` 생성. ruff `DTZ001` 이 경고. 해결: `# noqa: DTZ001 — naive intentional`. Story 1.4 프로젝트 pattern 과 동일.

### Completion Notes List

- **AC-1 완료**: F5 Python wrapper (`readonly_mount.py` 241줄 + `cli.py` 145줄 + `metrics.py` 160줄 + `override_event.py` 78줄) — Protocol 기반 ChattrExecutor 추상화 + Idempotent lock/unlock + 3-state MountState + Prometheus textfile atomic emit. 17 단위 테스트 + mypy strict + lint-imports 5/5 KEPT. **Windows dev host 호환성**: `PurePosixPath` 전환으로 플랫폼 독립 달성.

- **AC-2 완료**: 4 systemd units (`lock.service` + `lock.timer` + `unlock.service` + `unlock.timer`) + 1 scaffold (`inotify-watcher.service`) + sudoers drop-in (4-entry 열거, wildcard 금지) + `check_trading_day.py` (typed factory) + `emit_readonly_mount_metric.py` (pessimistic PARTIAL on failure) + `install.sh` (DRY_RUN + idempotent `cmp -s` + `visudo -cf` 사전검증). 14 integration 테스트 (9 static + 5 WSL2-only).

- **AC-3 완료**: WSL2 실 chattr E2E 4 시나리오 (test_chattr_e2e.py) — lock-then-write-fails (EPERM assertion), idempotent-cycle, git-revert-blocked (cp -f primitive), end-to-end-market-cycle (hero test: 07:00→09:00 lock→12:00 reject→15:30 unlock→17:00 edit). Windows 세션 4/4 skip 확인. WSL2 prerequisite 는 docstring + sudoers probe fixture 로 self-skip.

- **AC-4 완료**: `OverrideAttemptEvent` dataclass contract (UTC-aware + protected-root prefix invariants) + `athena-inotify-watcher.service` scaffold (`[Install]` 섹션 의도적 생략 — Story 3.5 가 enable). 3 단위 테스트 확인.

- **AC-5 완료**: `operating_playbook.md ## Story 1.6` 5 sub-section (sudoers setup / install / manual ops / holiday maintenance / PARTIAL troubleshoot). `deferred-work.md ## Deferred from: Story 1.6` 14 항목 (scope ≥ 6 초과 달성). `sprint-status.yaml` `1-6-*: review`. 5-gate ALL GREEN: 294 passed + 14 skipped / 10 pre-commit hooks Passed / 5 lint-imports KEPT / wheel build OK (f5/ 5 파일 모두 포함).

- **Windows 세션 commit 경계 준수**: 모든 Task 의 commit subtask (1.11, 2.9, 3.5, 4.5, 5.10) + Task 6 (PR 생성/merge) 는 **Windows 세션에서 실행 금지** (feedback_windows_host_commit_boundary.md). WSL2 일괄 위임 — Task 6 에서 branch `story-1.6/f5-readonly-mount` 생성 + 5 signed commit + PR.

- **Architecture.md 이탈 기록**: (1) `architecture.md` line 818 의 단수 `athena-readonly-mount.service` → 본 구현은 `-lock.service` + `-unlock.service` + 각 `.timer` 2 pair 로 split (1 unit = 1 action systemd 관례). (2) line 743 `readonly_mount.py` 단일 → `readonly_mount.py` + `cli.py` + `metrics.py` + `override_event.py` + `__main__.py` 5 파일로 분리 (SRP + 테스트 가능성). (3) `_PROTECTED_ROOT` 및 `DEFAULT_PROTECTED_PATHS` 는 `PurePosixPath` 로 표현 (Windows dev host 호환 + chattr 의 POSIX 전용 semantic 반영).

- **허용된 디자인 결정 (스토리 본문 옵션 중 선택)**: (1) `holidays>=0.50,<1.0` 를 root 가 아닌 `athena-alpha-defense/pyproject.toml` `[project.dependencies]` 에 추가 (root 는 virtual workspace 라 `[project]` 블록 부재). (2) Python venv 경로 `/home/khuk0/invest_training/.venv/bin/python` hardcoded — Story 1.4 패턴 계승, 환경변수화는 Story 1.7 host split 에서 처리 (deferred-work 항목).

### File List

**Created (17 신규)**:

- `packages/athena-alpha-defense/athena/alpha_defense/f5/__init__.py`
- `packages/athena-alpha-defense/athena/alpha_defense/f5/__main__.py`
- `packages/athena-alpha-defense/athena/alpha_defense/f5/cli.py`
- `packages/athena-alpha-defense/athena/alpha_defense/f5/metrics.py`
- `packages/athena-alpha-defense/athena/alpha_defense/f5/override_event.py`
- `packages/athena-alpha-defense/athena/alpha_defense/f5/readonly_mount.py`
- `packages/athena-alpha-defense/tests/test_cli.py`
- `packages/athena-alpha-defense/tests/test_metrics.py`
- `packages/athena-alpha-defense/tests/test_override_event.py`
- `packages/athena-alpha-defense/tests/test_readonly_mount.py`
- `scripts/check_trading_day.py`
- `scripts/emit_readonly_mount_metric.py`
- `infra/systemd/athena-readonly-mount-lock.service`
- `infra/systemd/athena-readonly-mount-lock.timer`
- `infra/systemd/athena-readonly-mount-unlock.service`
- `infra/systemd/athena-readonly-mount-unlock.timer`
- `infra/systemd/athena-inotify-watcher.service`
- `infra/systemd/athena-readonly-mount.install.sh`
- `infra/systemd/sudoers.d/athena-readonly-mount`
- `infra/systemd/README.md`
- `tests/integration/test_chattr_e2e.py`
- `tests/integration/test_check_trading_day.py`
- `tests/integration/test_readonly_mount_units.py`
<!-- `config/flag_registry.toml` was initially created as an empty stub but removed before commit: install.sh's inline heredoc fallback already materialises `/var/lib/athena/policy/flag_registry.toml` when the source file is missing. Leaving the stub in git would trip scripts/check_policy_prefix.py (policy: prefix required) even though this story is infra-only. Story 2.1 will create the real file with the 52-flag enumeration under a `policy: ...` commit. -->

**Modified (6)**:

- `packages/athena-alpha-defense/pyproject.toml` (`holidays>=0.50,<1.0` 추가)
- `.pre-commit-config.yaml` (mypy hook `additional_dependencies` 에 `holidays>=0.50,<1.0`)
- `uv.lock` (holidays + 의존성 추가로 자동 재생성)
- `docs/operating_playbook.md` (`## Story 1.6` 섹션 신규)
- `_bmad-output/implementation-artifacts/deferred-work.md` (`## Deferred from: Story 1.6` 14 항목)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (`1-6-*: ready-for-dev → in-progress → review`, `last_updated: 2026-04-23`)
- `_bmad-output/implementation-artifacts/1-6-f5-읽기전용-마운트-systemd-timer-infrastructure.md` (본 파일 — Status / Tasks / Dev Agent Record / File List / Change Log)

## Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-04-23 | 0.1.0 | Story 1.6 file created from epics.md lines 592-623 (ready-for-dev). Comprehensive context engine analysis: 11 Source-of-Truth Invariants (2-file protected set V1.0 lock, `/var/lib/athena/policy/` ext4 location vs git-tracked `config/`, ChattrExecutor single-entry + Protocol abstraction, MountState 3-state LOCKED/UNLOCKED/PARTIAL, systemd OnCalendar KST timezone requirement, Persistent=false missed-fire policy, sudoers wildcard-free NOPASSWD 4-entry enumeration, User=khuk0+sudo vs User=root tradeoff, holidays library selection vs hardcoded TOML, OverrideAttemptEvent Story 3.5/3.1 consume contract, Prometheus metric naming SSOT), 15 Scope Boundary entries, 13 Previous Story Intelligence items (1.1-1.5 이관), 10 Architecture Pattern constraints, 7 Threat Model scenarios, 6 commit strategy commits, 5 Tasks + 1 hand-off Task (총 30+ subtasks), 5 ACs with detailed Given/When/Then. Runtime dependency additions: `holidays>=0.50,<1.0`. No new dev-only deps. | Amelia via create-story skill |
| 2026-04-23 | 0.2.0 | Tasks 1-5 구현 완료 (review-ready). 24 신규 파일 + 6 modified. 294 pytest passed + 14 skipped (9 WSL2-only + 5 pre-existing). 10 pre-commit hooks Passed. 5 lint-imports KEPT. mypy strict clean. wheel build 성공. Key pattern decisions: (a) `PurePosixPath` 전환 (chattr 타겟 POSIX semantic + Windows dev host 호환), (b) `holidays.country_holidays("KR", ...)` typed factory (vs 동적 `holidays.KR`), (c) `emit_readonly_mount_metric.py` pessimistic PARTIAL on non-success exit (Story 1.9 early alerting), (d) Systemd unit 2 pair (lock/unlock 각 service + timer = 4 units) + 1 scaffold (`inotify-watcher.service`, `[Install]` 생략). Commit subtasks (1.11/2.9/3.5/4.5/5.10) + Task 6 (PR) 는 **WSL2 세션 위임** (feedback_windows_host_commit_boundary.md 준수). deferred-work 14 항목 (scope 기대치 ≥ 6 초과 달성). | Amelia via bmad-dev-story |
| 2026-04-23 | 0.3.0 | Task 6 완료 — PR #13 merged (d7833c5). WSL 위임 7 signed commits: 초기 4 (feat(alpha-defense) 1a87185 + feat(infra) e61831f + test(alpha-defense) 90bf6c6 + chore(story-1.6) 9ee285d) + CI 재실행 fix 3 (fix(ci) 7e168ec systemd-analyze tolerance + install.sh DRY_RUN visudo skip + fix(infra) c7ec7c4 inotify Documentation= URL format + fix(alpha-defense) 2d62a94 Gemini 3 findings patch). Gemini bot 3 findings 전원 inline patch (1 HIGH emit_readonly_mount_metric 의 SuccessExitStatus=0 1 로직 오류 — actual status() 조회로 수정 / 2 MEDIUM — metrics.py IndexError 가드 + readonly_mount.py try-except 확장), Story 1.5 deferred-only 패턴 탈피. CI 7-stage all PASS. 3 review threads GraphQL `resolveReviewThread` 해결 → mergeStateStatus CLEAN → `gh pr merge --squash --delete-branch`. 본 버전은 post-merge transition commit (sprint-status + Status → done). | Amelia via bmad-dev-story |

