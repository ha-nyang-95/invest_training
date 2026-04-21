# Story 1.2: 환경 & Secrets Infrastructure — WSL2 + OS Keychain + SSH Signing

Status: in-progress

Epic: 1 — Foundation & Market Truth Capture
Story Key: `1-2-환경-secrets-infrastructure-wsl2-os-keychain-ssh-signing`
FR Coverage (direct): —  (infrastructure; no FR slot)
NFR Coverage (direct): NFR-S1 (OS Keychain, `.env` 금지), NFR-S2 (주문/조회 key 분리), NFR-S5 (로컬 네트워크 + SSH key), NFR-A5 (git signed commit 물리 구현)
AR Coverage (direct): AR-SEC1~2 (keyring + SSH signing), AR-CFG1~2·CFG5 (pydantic-settings, `.env` 배제), AR-INF1~2 (WSL2 Trading PC), AR-EXT4 (SSH over local network)

## Story

As **Khuk0 operating the Trading PC (현재 Windows 11 단일 호스트)**,
I want **WSL2 Ubuntu 24.04 LTS + OS Keychain 기반 secret 관리 + git SSH signing 인프라**를 확립하여,
so that **모든 API key·broker 인증·backup 암호화 key 가 첫 commit 부터 OS primitives (wincred / Secret Service) 에만 존재하고, `.env` 또는 환경변수 평문 유출 경로가 런타임에 물리적으로 차단되며, 모든 후속 commit 이 SSH 키로 서명되어 NFR-A5 감사 체인을 시작한다**.

## Acceptance Criteria

**AC-1: WSL2 Ubuntu 24.04 LTS + systemd Activation** [Source: epics.md#Story-1.2 (lines 465-468), architecture.md#D17 (lines 338-341), architecture.md#AR-INF1-2]

**Given** Windows 11 Trading PC (현재 호스트 `C:\Users\khuk0\`)
**When** `wsl --install -d Ubuntu-24.04` 실행 + 최초 부팅 + `/etc/wsl.conf` `[boot] systemd=true` 설정 + `wsl --shutdown` 후 재진입
**Then** `wsl -l -v` 가 `Ubuntu-24.04` / `Running` / `2` 세 필드 모두 표시
**And** WSL2 shell 에서 `systemctl --user status` 가 에러 없이 반환 (systemd user session 살아있음)
**And** `cat /etc/os-release` 가 `VERSION_CODENAME=noble` + `UBUNTU_CODENAME=noble` 포함 (24.04 LTS 확인)
**And** `/var/lib/athena/` · `/data/parquet/` · `/mnt/external/` 3개 디렉토리를 `sudo mkdir -p` 로 선-생성 (후속 스토리 placeholder; 내용물은 각 스토리 소관)
**And** 검증 로그가 `docs/operating_playbook.md` § "Story 1.2 Task 1" 아래에 원시 출력 그대로 저장됨

**AC-2: OS Keychain 경유 Secret Fetch — `athena.core.keyring_client`** [Source: epics.md#Story-1.2 (lines 470-473), architecture.md#D7 (line 295), architecture.md#NFR-S1 (line 1009), PRD.md#NFR-S1 (line 1020), PRD.md#NFR-S2 (line 1021)]

**Given** Python `keyring` 25.x (Story 1.1 이미 설치됨; `packages/athena-core/pyproject.toml`)
**And** 14개 `SecretName(StrEnum)` 레지스트리 — KIS 주문 key / KIS 조회 key / KIS 계좌번호 (NFR-S2 분리) · DART · HyperCLOVA · Solar Pro · Telegram · 카카오워크 · S3 access/secret/SSE-C · LUKS passphrase — ID 고정, Change Control 경유 없이 변경 금지
**When** `athena.core.keyring_client.get_secret(SecretName.KIS_ORDER_APP_KEY)` 를 호출
**Then** 내부적으로 `keyring.get_password(service="athena", username="KIS_ORDER_APP_KEY")` 가 Windows Credential Manager (wincred backend) 또는 Linux Secret Service (libsecret backend) 에서 auto-backend 경유 fetch
**And** 등록된 값이 있으면 `str` 으로 반환 (값 내용은 로그·print·stderr 로 유출 금지 — 오직 caller 로만 return)
**And** 등록된 값이 없으면 즉시 `MissingSecretError("KIS_ORDER_APP_KEY not in OS Keychain")` raise — 메시지 포맷 `f"{name} not in OS Keychain"` 고정 (Story 1.1 `athena.core.errors.MissingSecretError` 재사용)
**And** 편의 함수 `set_secret(name, value)` 는 `keyring.set_password("athena", name, value)` 1줄 wrapper — dev bootstrap 전용임을 docstring 명시 (prod 경로에서는 호출 금지)
**And** 모듈은 `subprocess`·`os.popen`·`os.system`·`shutil` 를 **import 하지 않고 호출도 하지 않음** — `tests/test_keyring_client_no_shell.py` 가 AST 로 검증 (Story 1.1 `test_version_no_shell.py` 패턴 재사용)

**AC-3: `pydantic-settings` Settings + `.env` 런타임 차단** [Source: epics.md#Story-1.2 (lines 475-478), architecture.md#D21 (line 361), architecture.md#AR-CFG5, PRD.md#NFR-S1 (line 1020)]

**Given** Story 1.1 이미 설치한 `pydantic-settings>=2,<3`
**When** `athena.core.settings` 모듈이 import 되거나 `get_settings()` 가 최초 호출
**Then** `_ensure_no_dotenv_files(repo_root)` 가 실행되어 워크스페이스 루트 + 1단계 하위 디렉토리에서 `.env`, `.env.*` glob 매칭 파일이 하나라도 있으면 즉시 `SystemExit(".env usage forbidden by NFR-S1: found <경로>")` — 프로세스 종료
**And** 제외 디렉토리 명시: `.venv/`, `.git/`, `_bmad/`, `_bmad-output/`, `node_modules/`, `build/`, `dist/`, `__pycache__/` 내부의 `.env*` 는 무시 (false-positive 방지)
**And** `Settings(BaseSettings)` 클래스는 `SettingsConfigDict(env_file=None, env_prefix="ATHENA_", frozen=True, extra="forbid")` 로 선언 — `.env` 파싱 기능 자체를 비활성, 환경변수는 `ATHENA_*` prefix 의 **non-secret** 런타임 플래그만 허용
**And** `Settings` 가 가진 필드는 **secret 값이 아닌 런타임 플래그뿐**: `environment: Literal["prod", "paper"] = "paper"` (기본 paper — 실자본 사고 예방), `app_log_level: Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"] = "INFO"`
**And** secret 접근은 `Settings` 메서드로만 노출 — 예: `settings.kis_order_app_key() -> str` 은 내부적으로 `keyring_client.get_secret(SecretName.KIS_ORDER_APP_KEY)` 를 매 호출 lazy 위임 (값 캐싱 금지 — 메모리 수명 단축)
**And** `get_settings() -> Settings` 는 `@lru_cache(maxsize=1)` singleton — **Settings 객체만 cache, secret 값은 cache 되지 않음**
**And** 레포 루트에 새 regression test `tests/regression/test_no_dotenv_files.py` — 제외 디렉토리 빼고 워크스페이스 트리를 walk, `.env*` 매칭 파일이 발견되면 FAIL (상시 CI 게이트)

**AC-4: Git SSH Signing (ed25519)** [Source: epics.md#Story-1.2 (lines 480-483), architecture.md#D8 (line 297), PRD.md#NFR-A5]

**Given** git 2.34+ 가 Trading PC WSL2 와 Windows 11 양쪽에 설치됨 (WSL2 Ubuntu 24.04 기본 git 2.43+, Windows Git 2.53.0 이미 존재 — operating_playbook.md 에 기록됨)
**When** `ssh-keygen -t ed25519 -C "khuk0@athena-signing" -f ~/.ssh/id_ed25519_athena_sign -N ""` 을 WSL2 에서 실행 + `git config --global gpg.format ssh` + `git config --global user.signingkey <pubkey_path>` + `git config --global commit.gpgsign true` + `git config --global tag.gpgsign true` + `~/.ssh/allowed_signers` 에 `<email> ssh-ed25519 AAAA...` 1줄 등록 + `git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers`
**Then** `git commit -S --allow-empty -m "test: ssh signing verify"` 가 SSH key 서명을 붙여 새 commit 생성 (exit 0)
**And** `git log --show-signature -1` 출력에 `Good "<key comment>" signature` 포함 (로컬 allowed_signers 검증)
**And** `git verify-commit HEAD` 가 exit 0 (서명 체인 기계 검증)
**And** Story 1.1 의 unsigned commit 과는 분리 — Story 1.2 Task 4 의 첫 signed commit 은 `policy:` prefix 금지 (scaffold work), 메시지 `chore(story-1.2): enable git SSH signing (AC-4)` 권장
**And** SSH 개인키 파일은 **절대 git add 금지** — `.gitignore` 는 `~/.ssh/` 외부 영역이므로 git 은 자연스럽게 추적 안 하지만, Story 1.1 의 `detect-private-key` + gitleaks 가 실수 방어 (이 AC 에 regression 추가 없음 — 후속 스토리에서 fire-drill 도입 예정)

**AC-5: Logger PC ↔ Trading PC SSH 트러스트 + 방화벽 scope 제한** [Source: epics.md#Story-1.2 (lines 485-488), architecture.md#D12 (line 308), architecture.md#D17 (lines 338-341), PRD.md#NFR-S5 (line 1024)]

**Given** Windows 11 호스트 = Logger PC 역할 (`athena-l2-logger` NSSM 타깃, Story 1.7 구현), WSL2 Ubuntu 24.04 = Trading PC 역할 (`athena-orchestrator` systemd 타깃). 단일 물리 박스에서 두 OS 가 공존 — WSL2 게스트는 Windows 호스트를 `$(powershell.exe -c '(Get-NetIPAddress ...)')` 로 얻은 `<windows_host_ip>` 로 접근 가능
**When** Windows 11 에서 "Optional Features → OpenSSH Server" 설치 + `Set-Service sshd -StartupType Automatic` + `Start-Service sshd` + `New-NetFirewallRule -Name sshd-local -DisplayName "OpenSSH Server (local subnet only)" -Protocol TCP -LocalPort 22 -Action Allow -Direction Inbound -Profile Private -RemoteAddress LocalSubnet`
**And** WSL2 에서 `ssh-keygen -t ed25519 -C "trading-pc→logger-pc" -f ~/.ssh/id_ed25519_athena_logger_sync -N ""` + 공개키를 Windows 쪽 `C:\Users\khuk0\.ssh\authorized_keys` (ACL: SYSTEM + 현재 사용자만 Read, `icacls` 명시 적용) 에 append
**And** WSL2 `~/.ssh/config` 에 다음 호스트 alias 등록:
```ssh-config
Host logger-pc
    HostName <windows_host_ip_from_wsl_side>
    User khuk0
    IdentityFile ~/.ssh/id_ed25519_athena_logger_sync
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
```
**Then** WSL2 Trading PC 에서 `ssh logger-pc "echo ok"` 가 exit 0 + stdout `ok` — password prompt 없음 (key 인증만)
**And** `~/.ssh/known_hosts` 에 Logger PC host key 가 최초 1회 등록 (이후 변경 시 MITM 경보)
**And** 다른 VLAN · 외부 네트워크 (public internet 모사용 `curl ifconfig.me` 로 얻은 공인 IP 로 반대 방향 접속) 에서는 TCP 22 차단 확인 (`Test-NetConnection -ComputerName <공인_ip> -Port 22` 가 `TcpTestSucceeded: False`)
**And** 방화벽 규칙과 authorized_keys 등록 내역을 `docs/operating_playbook.md` § "Story 1.2 Task 6" 에 기록 — 단 실제 공개키 fingerprint 만, 전체 키 내용 복사 금지 (키가 짧지만 관행 유지)

## Tasks / Subtasks

Execute **in order**. Mark `[x]` only when both implementation AND tests pass. Run the full test suite (`uv run pytest -n auto`) after each code-bearing task — never proceed with failing tests. Host-setup tasks (Task 1, 4, 5, 6) require manual Khuk0 action but MUST leave verifiable artifacts (`wsl -l -v` output, `git log --show-signature`, `ssh logger-pc echo ok`) pasted verbatim into `docs/operating_playbook.md`.

- [ ] **Task 1: WSL2 Ubuntu 24.04 LTS 설치 + systemd 활성화** (AC: 1)
  - [ ] 1.1 Windows PowerShell (관리자) 에서 `wsl --install -d Ubuntu-24.04` 실행. 최초 부팅 시 username `khuk0` / password 설정. `wsl --update` 로 커널 최신화.
  - [ ] 1.2 WSL2 shell 에서 `sudo tee /etc/wsl.conf > /dev/null <<'EOF'` 로 다음 블록 기록:
    ```ini
    [boot]
    systemd=true

    [interop]
    appendWindowsPath=false
    ```
    `appendWindowsPath=false` 는 `$PATH` 에 Windows `cmd.exe`·`powershell.exe`·Chocolatey 가 섞여 들어와 Ruff/mypy/uv 가 엉뚱한 실행파일을 잡는 사고 방지 (Story 1.1 Task 1.1 의 `where.exe uv` 정황 참고).
  - [ ] 1.3 Windows PowerShell 에서 `wsl --shutdown` → 재 접속. 확인: `systemctl --user status` 가 에러 없이 반환 + `ps -p 1 -o comm=` 가 `systemd` 출력.
  - [ ] 1.4 필수 패키지 설치: `sudo apt update && sudo apt install -y build-essential git curl openssh-client ca-certificates` (+ `rsync` 는 Story 1.4 에서 설치).
  - [ ] 1.5 placeholder 디렉토리 생성: `sudo mkdir -p /var/lib/athena/{policy,ledger,data} /data/parquet /mnt/external` + `sudo chown -R khuk0:khuk0 /var/lib/athena /data/parquet` (권한은 후속 스토리가 세부 조정).
  - [ ] 1.6 검증: `wsl -l -v` · `cat /etc/os-release` · `systemctl --user status` 출력을 그대로 `docs/operating_playbook.md` § "Story 1.2 Task 1 — WSL2 setup" 블록에 append.
  - [ ] 1.7 **커밋 없음** — 이 Task 는 호스트 설정만. 다음 Task 에서 한 번에 묶어 커밋.

- [x] **Task 2: `athena.core.keyring_client` 모듈 + 단위 테스트** (AC: 2)
  - [x] 2.1 `packages/athena-core/athena/core/keyring_client.py` 작성:
    - `KEYRING_SERVICE: Final[str] = "athena"` — 서비스 이름 고정. 변경 = Change Control (NFR-M3).
    - `class SecretName(StrEnum)` — 14개 secret ID 고정 (docstring 에 PRD NFR-S1/S2 + architecture Integration Points 인용):
      - `KIS_ORDER_APP_KEY`, `KIS_ORDER_APP_SECRET`, `KIS_ORDER_ACCOUNT_NUMBER` (주문용, NFR-S2)
      - `KIS_QUERY_APP_KEY`, `KIS_QUERY_APP_SECRET` (조회 전용, NFR-S2 key 분리)
      - `DART_API_KEY`
      - `HYPERCLOVA_API_KEY`, `SOLAR_PRO_API_KEY`
      - `TELEGRAM_BOT_TOKEN`, `KAKAOWORK_WEBHOOK_URL`
      - `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_SSE_C_KEY`
      - `LUKS_PASSPHRASE`
    - `def get_secret(name: SecretName | str) -> str` — `keyring.get_password(KEYRING_SERVICE, str(name))` 호출, None 이면 `raise MissingSecretError(f"{name} not in OS Keychain")` — 메시지 포맷은 AC-2 에 고정됨.
    - `def set_secret(name: SecretName | str, value: str) -> None` — `keyring.set_password(KEYRING_SERVICE, str(name), value)` wrapper. docstring 에 "dev bootstrap only; production secrets MUST be set via OS-native GUI (wincred / seahorse)" 명시.
    - `__all__ = ["KEYRING_SERVICE", "SecretName", "get_secret", "set_secret"]`.
  - [x] 2.2 단위 테스트 `packages/athena-core/tests/test_keyring_client.py`:
    - `test_get_secret_returns_value`: `monkeypatch.setattr("keyring.get_password", lambda s, u: "val")` → `get_secret(SecretName.KIS_ORDER_APP_KEY) == "val"` + monkeypatch 호출 시 `s == "athena"` 검증.
    - `test_get_secret_raises_missing_error`: monkeypatch → `None`; `with pytest.raises(MissingSecretError, match=r"^KIS_ORDER_APP_KEY not in OS Keychain$"):`.
    - `test_get_secret_accepts_raw_str`: `get_secret("CUSTOM_NAME")` 도 동작 (문자열 경로), monkeypatch 에서 `u == "CUSTOM_NAME"` 검증.
    - `test_set_secret_calls_keyring_set_password`: monkeypatch 한 `keyring.set_password` 가 `("athena", "DART_API_KEY", "secret")` 인자로 호출되는지 검증.
    - `test_secret_name_registry_size_and_format`: `len(SecretName) == 14`, 모든 value `re.fullmatch(r"[A-Z][A-Z0-9_]*", v.value)`, 5개 KIS 키 + 9개 기타.
    - `test_keyring_service_frozen`: `KEYRING_SERVICE == "athena"` (값 변경 감지).
  - [x] 2.3 AST 검증 테스트 `packages/athena-core/tests/test_keyring_client_no_shell.py` — Story 1.1 `test_version_no_shell.py` 패턴 복제·적응:
    - `keyring_client.py` AST walk, `Import`·`ImportFrom` 노드에서 `subprocess`·`os.popen`·`os.system`·`shutil` 금지.
    - `Call` 노드에서 `os.system(...)` / `os.popen(...)` / bare `system(...)`·`popen(...)` (from-import 형태) 전부 검출 — Story 1.1 리뷰에서 추가된 bare-name 검출 로직 재사용.
  - [x] 2.4 `uv run pytest packages/athena-core/tests/test_keyring_client*.py -v` → 전부 pass. 전체 스위트 `uv run pytest -n auto` 도 pass 유지.
  - [x] 2.5 pre-commit 통과 확인 (`uv run pre-commit run --all-files`) — ruff·mypy·gitleaks.
  - [x] 2.6 커밋: `feat(core): add keyring_client with 14-secret registry (Story 1.2 AC-2)` → commit `35ac260`. **Deviation:** Task 4.2 (mypy hook `additional_dependencies += keyring>=25`) bundled into this commit because single-file mypy on `keyring_client.py` fails without the dep (blocks pre-commit). Also bundled: `pyproject.toml` `explicit_package_bases = true` — fixes pre-existing Story 1.1 single-file mypy bug (`Source file found twice` on PEP-420 namespace dir) that only surfaces when committing a new file. Also added ruff per-file-ignore `S105` for `keyring_client.py` (SecretName values are enum IDs, not real passwords). Test count: +15 (10 unit + 5 AST).

- [x] **Task 3: `athena.core.settings` Settings class + `.env` 런타임 차단** (AC: 3)
  - [x] 3.1 `packages/athena-core/athena/core/settings.py` 작성:
    - import 최상단에 `_REPO_ROOT` 탐지: `Path(__file__).resolve().parents[4]` 가 기본값 (packages/athena-core/athena/core/settings.py → 4단계 상위가 워크스페이스 루트). env override `ATHENA_REPO_ROOT` 로 테스트에서 주입 가능.
    - `_EXCLUDE_DIRS: Final[frozenset[str]] = frozenset({".venv", ".git", "_bmad", "_bmad-output", "node_modules", "build", "dist", "__pycache__"})`.
    - `def _ensure_no_dotenv_files(root: Path) -> None`:
      - 워크스페이스 루트를 walk. `os.walk` 사용 시 `dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]` 로 pruning.
      - `.env` 정확 일치 또는 `.env.*` glob 매칭 파일 1건 이상 발견 → 첫 매칭 경로를 담아 `raise SystemExit(f".env usage forbidden by NFR-S1: found {path}")`.
      - 매칭 0건이면 조용히 return.
      - 재귀 깊이 1단계 (`root` + 직속 하위만) 로 제한 — 성능 + false-positive 축소. `os.walk` 의 `dirnames[:] = []` 로 자식 순회 중단.

      실제 구현: `for item in root.iterdir(): if item.name == ".env" or fnmatch(item.name, ".env.*"): raise ...`; 그리고 `for subdir in root.iterdir(): if subdir.is_dir() and subdir.name not in _EXCLUDE_DIRS: for item in subdir.iterdir(): ...`.
    - 모듈 import 시점 side-effect 로 `_ensure_no_dotenv_files(_REPO_ROOT)` 호출 — 프로세스 시작 즉시 fail-fast. 테스트에서는 `_EXCLUDE_DIRS` 에 tmp_path 가 포함되도록 monkeypatch.
    - `class Settings(BaseSettings)`:
      - `model_config = SettingsConfigDict(env_file=None, env_prefix="ATHENA_", frozen=True, extra="forbid", case_sensitive=False)`.
      - 필드: `environment: Literal["prod", "paper"] = "paper"`, `app_log_level: Literal["DEBUG","INFO","WARNING","ERROR","CRITICAL"] = "INFO"`.
      - secret 접근 메서드 1개당 `SecretName` 1개 — `def kis_order_app_key(self) -> str: return get_secret(SecretName.KIS_ORDER_APP_KEY)` 패턴 × 14회. ⚠ **값 캐싱 금지** — 메서드가 매 호출 keyring 재조회 (메모리 수명 최소화).
    - `@lru_cache(maxsize=1) def get_settings() -> Settings: return Settings()` — Settings 객체 자체는 불변이므로 singleton 안전. **값은 cache 되지 않음** (메서드가 keyring 재호출).
    - `__all__ = ["Settings", "get_settings"]`.
  - [x] 3.2 단위 테스트 `packages/athena-core/tests/test_settings.py`:
    - `test_settings_defaults`: `Settings(); settings.environment == "paper"`, `settings.app_log_level == "INFO"`.
    - `test_settings_is_frozen`: `with pytest.raises(ValidationError): settings.environment = "prod"`.
    - `test_settings_forbids_extra_env(monkeypatch)`: `monkeypatch.setenv("ATHENA_UNKNOWN_FIELD", "x")`; `with pytest.raises(ValidationError, match=r"extra"): Settings()`.
    - `test_settings_accepts_env_override(monkeypatch)`: `monkeypatch.setenv("ATHENA_ENVIRONMENT", "prod")`; `Settings().environment == "prod"` (non-secret flag 는 env 허용).
    - `test_dotenv_guard_raises_on_root_env(tmp_path)`: `(tmp_path / ".env").write_text("SECRET=x")`; `with pytest.raises(SystemExit, match=r"\.env usage forbidden by NFR-S1"): _ensure_no_dotenv_files(tmp_path)`. 각 파일명 parametrize: `.env`, `.env.local`, `.env.production`, `.env.test`, `.env.development`.
    - `test_dotenv_guard_excludes_venv_and_bmad(tmp_path)`: `(tmp_path / ".venv").mkdir(); (tmp_path / ".venv" / ".env").write_text("..."); (tmp_path / "_bmad-output").mkdir(); (tmp_path / "_bmad-output" / ".env").write_text("...")` → `_ensure_no_dotenv_files(tmp_path)` return 정상.
    - `test_dotenv_guard_does_not_recurse_deeper_than_1(tmp_path)`: `tmp_path/a/b/.env` (깊이 2 이상) 은 탐지 안 함 확인 — scope 문서화.
    - `test_get_settings_is_singleton`: `get_settings() is get_settings()`.
    - `test_secret_accessor_delegates_to_keyring(monkeypatch)`: `captured = {}`; `def fake(name): captured["name"] = name; return "VAL"`; `monkeypatch.setattr("athena.core.keyring_client.get_secret", fake)`; `Settings().kis_order_app_key() == "VAL"`; `captured["name"] == SecretName.KIS_ORDER_APP_KEY`.
    - `test_secret_accessor_does_not_cache(monkeypatch)`: keyring_client.get_secret 이 2회 호출로 2회 counter 증가 — 캐싱 없음 증명.
  - [x] 3.3 `uv run pytest packages/athena-core/tests/test_settings.py -v` → 22/22 pass. 전체 스위트 109 passing / 2 skip.
  - [x] 3.4 커밋: `feat(core): add Settings class with .env runtime guard (Story 1.2 AC-3)` → commit `a755d48`. **Deviation A:** Test `test_settings_forbids_extra_env` adjusted — pydantic-settings silently ignores unknown `ATHENA_*` env vars (only declared fields are read); `extra="forbid"` governs direct kwargs. Renamed to `test_settings_forbids_extra_kwargs` and exercises `Settings(unknown_field="x")`. **Deviation B:** `test_all_14_secret_accessors_exist` uses `dir(Settings)` (class) not `dir(instance)` to avoid Pydantic v2.11 deprecation warnings on `model_fields` / `model_computed_fields` instance access. Test count: +22 (story estimated ~10, actual higher due to parametrize expansion for 5 dotenv filename cases).

- [x] **Task 4: 레포 차원 `.env` Regression + mypy hook 의존성 확장** (AC: 3 enforcement)
  - [x] 4.1 `tests/regression/test_no_dotenv_files.py` 작성:
    - `REPO_ROOT = Path(__file__).resolve().parents[2]`.
    - `EXCLUDE_DIRS` = Story 3.1 의 `_EXCLUDE_DIRS` 와 동일 (import 로 공유 금지 — regression 테스트는 독립된 제외 리스트로 이중검증). 주석에 reason 명시.
    - 트리 전체 walk. `.env` 또는 `.env.*` 매칭 0건 assert. 실패 시 발견 경로 전체 출력 (어디에 숨어 있는지 보여주기).
    - 추가: `test_exclude_lists_stay_in_sync` — runtime guard 의 `_EXCLUDE_DIRS` 가 regression 의 `EXCLUDE_DIRS` 에 완전 포함되는지 assert (drift 감지, import coupling 없이).
  - [x] 4.2 ~~`.pre-commit-config.yaml` 의 `mypy` hook `additional_dependencies` 에 다음 추가: `keyring>=25`~~. **Bundled into Task 2 commit `35ac260`** because the dep is required to make Task 2 pre-commit hook pass — split would have required `--no-verify` bypass (banned). Story 1.1 deferred-work.md item 5 is fully resolved.
  - [x] 4.3 `uv run pytest tests/regression/test_no_dotenv_files.py -v` → 2/2 pass. 전체 스위트 111 passing / 2 skip.
  - [x] 4.4 커밋: `test(regression): forbid .env files repo-wide (Story 1.2 AC-3)` → commit `0558d3e`. (mypy hook deps 는 Task 2 에서 이미 landing 되어 이 commit 제목에서 제외.)

- [ ] **Task 5: Git SSH Signing 구성** (AC: 4) — Khuk0 수동 실행, WSL2 shell 안에서
  - [ ] 5.1 WSL2 에서 `ssh-keygen -t ed25519 -C "khuk0@athena-signing" -f ~/.ssh/id_ed25519_athena_sign -N ""` — passphrase 없음 (자동 서명용; V1.1+ YubiKey 도입 시 passphrase 추가, architecture D11).
  - [ ] 5.2 `~/.ssh/allowed_signers` 파일 생성: `wkdcjfghks1@gmail.com ssh-ed25519 <pubkey_body>` 1줄 (이메일은 Khuk0 user profile 기준, pubkey 는 `cat ~/.ssh/id_ed25519_athena_sign.pub` 의 두번째 필드만).
  - [ ] 5.3 git 전역 설정 (WSL2 Trading PC side 만):
    ```bash
    git config --global gpg.format ssh
    git config --global user.signingkey ~/.ssh/id_ed25519_athena_sign.pub
    git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
    git config --global commit.gpgsign true
    git config --global tag.gpgsign true
    git config --global user.name "장철환"
    git config --global user.email "wkdcjfghks1@gmail.com"
    ```
  - [ ] 5.4 검증용 signed commit 생성: `cd ~/vibe/invest_training && git commit -S --allow-empty -m "chore(story-1.2): enable git SSH signing (AC-4)"`.
  - [ ] 5.5 `git log --show-signature -1` 출력에 `Good "khuk0@athena-signing" signature` 또는 동등 문자열 확인. `git verify-commit HEAD` 가 exit 0.
  - [ ] 5.6 두 출력 블록 전체를 `docs/operating_playbook.md` § "Story 1.2 Task 5 — SSH signing setup" 아래에 붙여넣기 (pubkey fingerprint 만, 전체 privkey 금지).
  - [ ] 5.7 **Windows 11 host 쪽 git signing 은 이 스토리에서 수행하지 않음** — Story 1.7 (L2 로거 운영 시) 에 Logger PC git config 를 별도 설정. 현재 스토리의 scope 는 Trading PC (WSL2) 에서의 정책·코드 커밋.

- [ ] **Task 6: Logger PC ↔ Trading PC SSH 트러스트 + 방화벽 scope 제한** (AC: 5) — Khuk0 수동, Windows + WSL2 양쪽
  - [ ] 6.1 Windows 11 PowerShell (관리자):
    ```powershell
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
    Set-Service -Name sshd -StartupType Automatic
    Start-Service sshd
    New-NetFirewallRule -Name "sshd-local-subnet" `
        -DisplayName "OpenSSH Server (local subnet only)" `
        -Protocol TCP -LocalPort 22 -Direction Inbound `
        -Action Allow -Profile Private -RemoteAddress LocalSubnet
    # 기본 OpenSSH 규칙이 전체 scope 로 열려 있으면 비활성:
    Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue | Disable-NetFirewallRule
    ```
    검증: `Get-NetFirewallRule -Name sshd-local-subnet | Format-List DisplayName,Enabled,Profile,Action` + `Get-NetFirewallRule -Name sshd-local-subnet | Get-NetFirewallAddressFilter | Format-List RemoteAddress`.
  - [ ] 6.2 WSL2 에서 key 생성: `ssh-keygen -t ed25519 -C "trading-pc→logger-pc" -f ~/.ssh/id_ed25519_athena_logger_sync -N ""`.
  - [ ] 6.3 공개키 Windows 쪽 copy: WSL2 에서 `cat ~/.ssh/id_ed25519_athena_logger_sync.pub` → Windows PowerShell 에서:
    ```powershell
    $authkeys = "$env:USERPROFILE\.ssh\authorized_keys"
    New-Item -ItemType Directory -Path (Split-Path $authkeys) -Force | Out-Null
    Add-Content -Path $authkeys -Value "<WSL2 공개키 한 줄>" -Encoding ASCII
    # ACL 제한: SYSTEM + 현재 유저만 Read/Write
    icacls $authkeys /inheritance:r
    icacls $authkeys /grant "SYSTEM:(R)" "$env:USERNAME:(R)"
    ```
    (OpenSSH 서버 `administrators_authorized_keys` 대신 per-user authorized_keys 사용 — Khuk0 계정 기준 1인 개발.)
  - [ ] 6.4 Windows host IP 얻기 (WSL2 게스트 기준): `ip route show | awk '/^default/ {print $3}'` — 이 주소가 WSL2 에서 보이는 Windows host 의 게이트웨이 IP. 가변적이므로 Task 7 의 operating_playbook 에 "WSL2 재부팅 시 재확인 필요" 노트.
  - [ ] 6.5 WSL2 `~/.ssh/config` 에 append:
    ```ssh-config
    Host logger-pc
        HostName <위에서 얻은 IP>
        User khuk0
        IdentityFile ~/.ssh/id_ed25519_athena_logger_sync
        IdentitiesOnly yes
        StrictHostKeyChecking accept-new
    ```
    (`<IP>` 대신 WSL2 가 제공하는 `/etc/hosts` 자동 생성 항목을 쓸 수도 있으나, 재부팅 시 리셋되는 이슈가 있어 명시 IP 권장.)
  - [ ] 6.6 검증 A — 성공 경로: `ssh logger-pc "echo ok"` → stdout `ok` + exit 0 + password prompt 없음. 출력을 playbook 에 붙여넣기.
  - [ ] 6.7 검증 B — 거부 경로: Windows PowerShell 에서 `Test-NetConnection -ComputerName <공인_ip> -Port 22` 가 `TcpTestSucceeded: False` (옵션: 휴대폰 tethering 으로 외부 네트워크에서 접속 시도해 차단 확인).
  - [ ] 6.8 host key fingerprint (`ssh-keygen -lf ~/.ssh/known_hosts` 출력) 를 playbook 에 기록 — MITM 감지용 reference.

- [ ] **Task 7: `docs/operating_playbook.md` 업데이트 + 최종 검증 + 핸드오프** (AC: 1-5)
  - [ ] 7.1 `docs/operating_playbook.md` 에 다음 섹션 추가:
    - `## Story 1.2 — Environment & Secrets Infrastructure`
      - `### WSL2 Ubuntu 24.04 Setup` (Task 1 출력 블록)
      - `### Secret Bootstrap — one-time keyring enrollment`:
        ```
        # 14개 SecretName ID 별로 한 번씩 실행 (value 는 실제 발급받은 키)
        uv run python -c "from athena.core.keyring_client import set_secret, SecretName; set_secret(SecretName.KIS_ORDER_APP_KEY, '<value>')"
        # prod 경로에서는 이 스크립트 대신 Windows Credential Manager GUI (cmdkey) 또는 Seahorse 로 수동 등록 권장
        ```
        ⚠ **경고:** `set_secret` 의 shell 1-liner 는 PS1 history 에 value 가 남을 수 있다. Windows 는 `cmdkey /add:athena /user:<SECRET_NAME> /pass:<value>` 또는 "자격 증명 관리자" GUI, Linux 는 `secret-tool store --label=... service athena username <SECRET_NAME>` 사용 권장.
      - `### Git SSH Signing` (Task 5 verification 블록 + pubkey fingerprint)
      - `### Logger PC ↔ Trading PC SSH` (Task 6 firewall rule · authorized_keys ACL · `ssh logger-pc echo ok` 출력 · known_hosts fingerprint)
  - [ ] 7.2 5-gate 재실행: `uv sync --frozen --group dev` / `uv run pytest -n auto` / `uv run pre-commit run --all-files` / `uv run lint-imports` / `uv build --package athena-core --wheel --out-dir /tmp/athena-1-2-check`. 모두 pass.
  - [ ] 7.3 테스트 수 기준: Story 1.1 은 40 passing / 1 skipped 로 마감. Story 1.2 는 최소 +19 tests 예상 — keyring_client unit 6 + no-shell AST 2 + settings unit 10 + no-dotenv regression 1 (parametrize 확장 시 개별 case 까지 세면 +25 이상). mypy hook 의존성 확장 (Task 4.2) 은 기존 mypy 재활용이므로 별도 test count 증가 없음. → **60+ passing 예상**. 실제 수치를 Dev Agent Record § Completion Notes List 에 기록.
  - [ ] 7.4 최종 커밋: `chore(story-1.2): WSL2 + OS Keychain + SSH signing infra verified, hand off to Story 1.3`. 이 커밋은 Task 5 에서 활성화된 SSH signing 이 자동 적용되어 signed — `git log --show-signature -1` 로 더블체크. **`policy:` prefix 금지** (인프라 세팅이지 정책 변경 아님 — NFR-R5 72h cooling 비적용).
  - [ ] 7.5 `_bmad-output/implementation-artifacts/sprint-status.yaml` 에서 `1-2-*` 상태를 `ready-for-dev` → `in-progress` → `review` 순으로 이 Task 완료 시점에 수동 업데이트. (dev-story 스킬이 자동 처리 가능하지만 명시.)

## Dev Notes

### Source-of-Truth Invariants (Story 1.2 가 Down-stream 전역에 고정하는 불변식)

1. **OS Keychain 단일 경로** [architecture.md#D7 line 295, NFR-S1]
   모든 비대칭·대칭 key, API token, 계좌 번호, 백업 passphrase 는 **`athena.core.keyring_client.get_secret`** 단일 진입점을 경유. 직접 `keyring.get_password(...)` 호출 금지 — Story 1.3 ruff custom rule 로 차단 예정. 본 스토리에서는 code review 가 차단선.

2. **14개 SecretName ID 고정** [본 스토리 Task 2.1]
   `SecretName(StrEnum)` 14개 ID 는 첫 릴리스부터 Change Control 없이 변경 금지. 후속 스토리에서 secret 필요 시:
   - 같은 도메인 (KIS·DART·LLM·Telegram·카카오워크·S3·LUKS) 이면 기존 ID 재사용
   - 새 도메인 (예: 증권사 교체 Secondary Adapter, Story 4.1) 이면 추가는 Change Control 경유
   52-flag Registry (Story 2.1) 와 유사한 freeze 원칙.

3. **`.env` 파일 존재 자체가 장애 조건** [epics.md#Story-1.2 line 477, NFR-S1]
   `.env` / `.env.*` 파일이 워크스페이스 루트 또는 1단계 하위 디렉토리에 나타나는 순간 프로세스가 `SystemExit` 로 즉사. 로컬 dev 에서도 예외 없음 — 유일한 회피는 해당 파일 제거. `.env.example`·`.env.sample` 포함 (AC-3 은 glob `.env.*` 로 명시적으로 차단). Story 1.1 이 이미 `.gitignore` 에 `.env*` 선언하여 git commit 을 막고 있으나, 본 스토리는 "파일 시스템에 존재하기만 해도" 차단하는 런타임 enforce 레이어를 추가.

4. **Settings singleton, secret 값 non-cached** [본 스토리 Task 3.1]
   `get_settings()` 는 lru_cache 로 Settings 인스턴스만 캐시. `settings.kis_order_app_key()` 는 매 호출 `keyring.get_password` 를 실행 — 메모리 내 secret 수명 최소화. Story 1.7+ 의 L2 로거가 분당 60회 이상 key 를 조회해도 keyring 호출 overhead 는 무시 가능 (wincred / libsecret 모두 µs 단위).

5. **SSH signing key 는 `~/.ssh/id_ed25519_athena_sign`, 네트워크 trust key 는 `~/.ssh/id_ed25519_athena_logger_sync`** [본 스토리 Task 5.1, 6.2]
   두 key 는 **물리적으로 분리**. signing key 는 git 서명 전용, trust key 는 rsync over SSH 전용 (Story 1.4 가 활용). 한쪽이 유출되어도 다른 쪽은 영향 없음. 이 명명 규약은 Story 1.3·1.4·1.6 에서 그대로 재참조.

6. **Git signing 이 2026-04-21 Task 5.4 시점부터 무조건 활성화** [Task 5.3]
   `commit.gpgsign=true` 전역 설정 이후 모든 로컬 커밋이 서명됨. Story 1.1 의 8개 scaffold 커밋은 서명 없음 (Task 5 가 소급 적용 안 함 — rewrite 금지, history 불변). Story 1.2 Task 7.4 의 handoff 커밋이 **첫 번째 signed commit**. 향후 `git log --show-signature master` 는 Task 5 이후 커밋만 "Good signature" 표시.

### Scope Boundaries — 명시적으로 OUT of Story 1.2

| Out-of-scope 항목 | 귀속 스토리 | 이유 |
|---|---|---|
| GitHub self-hosted runner 등록 + 7단계 CI pipeline | Story 1.3 | CI hardening 은 별도 스토리 |
| 72h cooling gate + Paper 재검증 marker | Story 1.3 | 정책 변경 워크플로우 |
| WSL2 `chattr +i` + `athena-readonly-mount.service` systemd unit | Story 1.6 | F5 하드락 OS-레벨 enforcement |
| L2 WebSocket 로거 (`scripts/l2_logger.py`) | Story 1.7 | Logger PC 쪽 daemon 구현 |
| DART / 뉴스 crawler | Story 1.8 | 외부 data ingest |
| rsync systemd timer (`athena-logger-sync.service`) | Story 1.4 | 본 스토리의 SSH trust 를 **전제로** 구현 |
| LUKS 외장 SSD 암호화 · 마운트 스크립트 | Story 1.10 (backup automation) | secret (LUKS_PASSPHRASE) 은 Task 2.1 에 레지스트리만 등록 |
| YubiKey 2FA / hardware-backed signing key | V1.1+ (자본 확장 시) | architecture.md#D11 에서 deferred |
| ruff custom rule: "keyring.get_password 직접 호출 금지" | Story 1.3 | AST-plugin 필요, MVP 는 code review |
| Windows 11 host (Logger PC) git signing 설정 | Story 1.7 | Logger PC 는 `athena-l2-logger` 이외 git 활동 없음 (pull 만) |
| Secondary Adapter 용 secret (증권사 교체 시) | Story 4.1 (adapter abstraction) | 현재 SecretName 레지스트리에 placeholder 없음 — Change Control 경유 추가 |
| Settings 에 rate-limit · p99 예산 등 non-secret 상수 하드코딩 | Story 1.3 + Story 2.1 | `config/settings.toml` + `config/flag_registry.toml` 로 이관, Settings 는 런타임 flag 만 |

유혹이 들면 **멈추고 핸드오프**. Day-1/2 에 scope creep 이 발생하면 W1 일정 전체가 밀린다.

### Architecture Patterns & Constraints (이 스토리의 payload)

- **pydantic-settings 2.x 단일 경로** [architecture.md#D21 line 361, #AR-CFG5]: `BaseSettings` subclass + `SettingsConfigDict(env_file=None)`. `.env` 파싱 기능 자체를 라이브러리 레벨에서 비활성. 환경변수는 `ATHENA_*` prefix 의 **non-secret runtime flag** 에 한정.
- **Secret naming 은 SCREAMING_SNAKE_CASE + 도메인 prefix** [architecture.md#Naming-Patterns line 410]: `KIS_*`, `DART_*`, `S3_*`, `LUKS_*`, `TELEGRAM_*`. 14개 ID 고정 리스트는 Task 2.1.
- **keyring 백엔드 자동 선택** [D7]: Windows `wincred`, Linux `libsecret` (Ubuntu 24.04 기본 설치됨 via `gnome-keyring` 또는 `libsecret-1-0`). headless WSL2 환경에서 libsecret 이 DBUS 를 필요로 함 — Task 1.4 의 기본 패키지 설치 시 `gnome-keyring`·`libsecret-tools` 자동 설치 여부 확인. 불필요 시 수동 `sudo apt install -y gnome-keyring libsecret-tools`.
- **SSH key 알고리즘은 ed25519 고정** [D8, industry norm]: ECDSA / RSA 금지. Git 2.34+ 와 OpenSSH 8.0+ 가 양쪽 모두 지원.
- **Git SSH signing 은 `gpg.format=ssh`** [D8 line 297]: GPG keyring infra 없이 SSH key 재활용. `~/.ssh/allowed_signers` 파일로 로컬 검증 가능 — GitHub 는 자체 allowed-signers 를 관리하지만 로컬 `git log --show-signature` 가 동작하는 것이 본 AC-4 의 1차 요건.
- **Graceful degradation 적용 여부**: secret fetch 실패는 **graceful degradation 대상 아님** — `MissingSecretError` 는 프로세스 종료급 장애로 처리. Story 1.1 의 `architecture.md#Process-Patterns line 557` "Kill Switch · M22 hard-lock · Ledger write 실패만 CRITICAL" 리스트에 secret 부재도 암묵적 포함 (trading 불가 상태).

### Testing Standards

- **Framework**: pytest + pytest-asyncio (Story 1.1 에서 설정 완료) — async 경로 없음, `asyncio_mode=auto` 무영향.
- **Determinism**: 모든 테스트 `-p no:randomly` 로 pass (Story 1.1 과 동일, 본 스토리에서는 랜덤 요소 없음).
- **Monkeypatch 경로** [PT-I2 — 테스트 전략]: keyring·OS 호출은 **전부 monkeypatch** — 실제 OS Keychain 쓰기 금지. 실수로 `keyring.set_password` 를 실제 실행하면 dev PC 에 찌꺼기 secret 이 남는다.
- **tmp_path 패턴** [Story 1.1 Task 5.4, 6.3 재사용]: `.env` guard 테스트는 `tmp_path` fixture 로 격리. 실 워크스페이스 루트를 건드리지 않음.
- **AST 검증 재사용** [Story 1.1 Task 4.7 패턴]: `test_keyring_client_no_shell.py` 는 `test_version_no_shell.py` 의 AST walk 로직을 복사·적응. bare-name `Call(Name("system"))` 검출 로직 포함 (Story 1.1 리뷰에서 추가됨).
- **레이아웃** [AR-TEST5]: 단위 테스트 co-located (`packages/athena-core/tests/`), regression 은 `tests/regression/`.
- **커버리지**: Story 1.3 가 `--cov-fail-under=80` 도입. 본 스토리에서는 coverage gate 없음.

### Project Structure Notes

Story 1.2 는 Story 1.1 의 디렉토리 트리를 **확장만 하고 변경은 없음**. 추가되는 경로:

```
packages/athena-core/athena/core/
  ├── keyring_client.py            # NEW (Task 2)
  └── settings.py                  # NEW (Task 3)

packages/athena-core/tests/
  ├── test_keyring_client.py       # NEW (Task 2.2)
  ├── test_keyring_client_no_shell.py  # NEW (Task 2.3)
  └── test_settings.py             # NEW (Task 3.2)

tests/regression/
  └── test_no_dotenv_files.py      # NEW (Task 4.1)

docs/
  └── operating_playbook.md        # MODIFIED (Task 1.6, 5.6, 6.1-6.8, 7.1)
```

**명시적으로 생성 금지:**
- `.env`·`.env.example`·`.env.sample` 등 어떤 형태의 env 파일 — NFR-S1 위반
- `scripts/` — Story 1.2 는 호스트 설정과 athena-core 모듈 확장만 담당. 검증은 playbook 의 bash/PS1 블록으로 충분
- `config/secrets.toml` 등 secret-like 파일 — OS Keychain 외 저장 경로 영구 금지
- `infra/systemd/*.service` — Story 1.4 (rsync) · Story 1.6 (readonly mount) · Story 1.7 (L2 logger) 소관

**허용되는 architecture.md 이탈 (Dev Agent Record 에 기록):**
- operating_playbook.md 에 호스트별 IP 같은 **가변 값** 을 하드코딩 — 단일 개발자 환경 전제. 다중 개발자 확장 시 `infra/` 로 이관.

### Previous Story Intelligence (Story 1.1 이관 사항)

Story 1.1 이 2026-04-21 에 `done` 으로 마감되면서 본 스토리가 이어받는 기술·테스트·리뷰 learning:

1. **`MissingSecretError` 이미 정의됨** [1-1-*.md Task 4.2, `packages/athena-core/athena/core/errors.py:29-30`]
   `class MissingSecretError(AthenaError)` 가 이미 `athena.core.errors` 에 존재 — 재선언 금지. import 만 하면 됨: `from athena.core.errors import MissingSecretError`.

2. **`keyring>=25` + `pydantic-settings>=2,<3` 의존성 이미 lock** [`packages/athena-core/pyproject.toml:9`, `uv.lock`]
   새로 `uv add` 할 필요 없음. Story 1.1 의 code review 에서 "D-4 keyring 이 core leaf 에 있는 것은 Story-1.2 intent 로 수용" 으로 결론.

3. **cp949 codec trap on Korean Windows** [1-1 Debug Log #8, #13]
   파일 / subprocess IO 는 **항상 `encoding="utf-8"` 명시** — Korean Windows 의 기본 locale 이 cp949 이므로 non-ASCII 가 있으면 `UnicodeDecodeError`. `keyring_client.py` 자체는 텍스트 IO 없지만, `docs/operating_playbook.md` 에 append 하는 Python 스크립트가 있다면 `open(..., encoding="utf-8")` 필수.

4. **pytest-xdist 파일 시스템 레이스 회피** [1-1 Debug Log #12]
   `pyproject.toml` 에 `--dist=loadfile` 이미 설정됨 — 같은 파일 내 테스트는 1개 worker 에서 실행. 본 스토리의 `test_dotenv_guard_*` 도 tmp_path 를 쓰므로 worker 간 충돌 없음.

5. **pytest `--import-mode=importlib`** [1-1 Debug Log #3]
   여러 package `tests/` 가 동일 `test_settings.py` 네임을 쓸 때 충돌 방지. 본 스토리의 새 테스트 파일명 `test_keyring_client*.py`·`test_settings.py` 는 athena-core 전용이므로 충돌 없음.

6. **ruff `DTZ001` inline suppress** [1-1 Debug Log #9]
   naive datetime 사용이 테스트 의도일 때 `# noqa: DTZ001` + 이유 주석. 본 스토리는 naive datetime 사용 없음 (settings 필드는 전부 str/Literal), 대비로만 언급.

7. **ruff per-file-ignores 에 `tests/` 예외 이미 설정** [pyproject.toml:53-56]
   `S101` (assert) · `S404`·`S603`·`S607` (subprocess) 가 `**/tests/**` 에서 허용 — 본 스토리의 AST 검증 테스트에서 subprocess 불필요하지만, 향후 regression test 가 subprocess 를 쓸 수 있는 여지 확보됨.

8. **mypy `additional_dependencies` 확장 필요** [1-1 Deferred-Work 5번]
   `.pre-commit-config.yaml:34-36` 의 mypy hook 이 현재 `pydantic`·`pydantic-settings` 만 포함. 본 스토리 Task 4.2 가 `keyring>=25` 를 추가. Story 1.4 이후 `polars`·`duckdb`·`python-kis` 도 순차 추가 필요 (각 스토리 본문에서 처리).

9. **gitleaks + detect-private-key 이미 활성** [.pre-commit-config.yaml:40-49]
   SSH 개인키 실수 commit 방어선 존재. 본 스토리 Task 5.1 에서 생성하는 `~/.ssh/id_ed25519_athena_sign` 은 홈 디렉토리 바깥 (git 추적 범위 밖) 에 있어 자연스럽게 격리되지만, 만에 하나 repo 안에 복사되면 pre-commit 이 차단. Khuk0 review 에서 "Story 1.3 에 PEM fixture 로 fire-drill 테스트" 로 deferred — 본 스토리에서는 수동 확인.

10. **`.importlinter` ASCII-only 제약** [1-1 Debug Log #8 → 리뷰 픽스]
    `.importlinter` 는 Windows cp949 codec 으로 읽힘 — em-dash·한글 주석 금지. 본 스토리는 `.importlinter` 수정 없음 (keyring_client / settings 는 athena.core 레이어에 속하므로 기존 `core-leaf` forbidden 규칙이 이미 커버). 변경 발생 시 ASCII-safe 확인.

11. **`--import-mode=importlib` + `--dist=loadfile`** [pyproject.toml:34, 39]
    본 스토리의 새 테스트 파일이 기존 addopts 와 자동 호환. 추가 설정 불필요.

12. **MODULE_VERSION 은 `core.v0.1.0`** [1-1 DN-3 리뷰 deviation, `packages/athena-core/athena/core/version.py:55`]
    BaseDTO 의 `module_version` 에 주입되는 값. 본 스토리의 새 모듈 (`keyring_client`, `settings`) 은 DTO 를 반환하지 않으므로 MODULE_VERSION 과 무관. 단, 향후 Settings 를 DTO 로 직렬화할 일이 생기면 이 constant 재사용.

### Git Intelligence Summary

**Recent commits on `master` (상위 5건, 2026-04-21 기준):**
```
362c89d chore(story-1.1): scaffold verification passed, hand off to Story 1.2
37235ce ci: scaffold-gate workflow (ruff, mypy, import-linter, pytest)
b7501d8 feat(ci): pre-commit hook chain (ruff+mypy+secrets) with architecture bans
841783d feat(ci): import-linter contracts enforce AR-BND1/BND2 layer hierarchy
7ddb963 feat(build): Hatchling hook injects git sha into athena.core._version (AR-COM4)
```

**현재 untracked / modified 주의사항**: 2026-04-21 시점 워크스페이스에 Story 1.1 의 **review patch 적용 commit 이 아직 unstaged 상태** 로 남아 있음 (`git status` 출력의 16개 modified + 4개 untracked). 이 review patch 들은 Story 1.1 `done` 마감 조건이지만 커밋이 하나로 합쳐져 있지 않음.

**Dev agent 가 Story 1.2 Task 1 에 들어가기 전 확인할 것:**
1. `git status` 로 workspace clean 확인 — dirty 상태에서 Task 2 이하의 `feat(core): ...` 커밋을 생성하면 Story 1.1 의 미커밋 수정이 함께 섞인다.
2. 만약 dirty 라면: (a) Story 1.1 의 review patch 들을 하나의 추가 커밋 (`docs/fix(story-1.1): apply review patches` 또는 유사) 으로 먼저 landing — commit message 에 patch 항목 counts (`17/17 patches, all pass`) 기록. 또는 (b) 리뷰 리포트에 상세가 있다면 그 문맥을 존중.
3. Story 1.1 의 Change Log entry (2026-04-21 세 번째 entry) 가 "status review → done" 을 기록했으므로 review patch 는 이미 **의도적으로 적용된 상태**. 단지 commit 경계가 `done` 커밋과 합쳐지지 않았을 뿐. Story 1.2 dev agent 는 먼저 이 상태를 정리.

**본 스토리의 커밋 전략** (총 5건 예상):
- T2 → `feat(core): add keyring_client with 14-secret registry (Story 1.2 AC-2)` (unsigned, Task 5 이전)
- T3 → `feat(core): add Settings class with .env runtime guard (Story 1.2 AC-3)` (unsigned)
- T4 → `test(regression): forbid .env files repo-wide + extend mypy hook deps (Story 1.2 AC-3)` (unsigned)
- T5.4 → `chore(story-1.2): enable git SSH signing (AC-4)` (**첫 signed commit**)
- T7.4 → `chore(story-1.2): WSL2 + OS Keychain + SSH signing infra verified, hand off to Story 1.3` (signed)

Task 1·6 은 호스트 설정이므로 자체 커밋 없음 (playbook 수정은 Task 7.1 의 signed 커밋에 포함).

### Latest Tech Information

버전은 Story 1.1 에서 이미 frozen. **본 스토리에서 "최신 버전 research" 후 bump 금지** — 모델 라이프사이클은 Epic 8 소관.

| Library / Tool | Frozen Version (from `uv.lock`) | 본 스토리에서 검증할 동작 |
|---|---|---|
| keyring (jaraco) | 25.7.0 | wincred + Secret Service auto-backend |
| pydantic-settings | 2.14.0 | `SettingsConfigDict(env_file=None)` 가 `.env` 파싱 완전 비활성 |
| pydantic | 2.13.3 | `BaseSettings` + `frozen=True` + `extra="forbid"` |
| Ubuntu LTS | 24.04 (Noble Numbat) | 2029년 지원 종료 — LTS 라이프사이클 이내 |
| OpenSSH (WSL2 Ubuntu) | 9.6p1 기본 | ed25519 + ssh-signing 양쪽 지원 |
| OpenSSH Server (Windows 11) | Optional Feature 1.0 기반 | 서비스명 `sshd`, 설정 `C:\ProgramData\ssh\sshd_config` |
| git | 2.43+ (WSL2 Ubuntu 24.04 기본) / 2.53 (Windows host, already installed per playbook) | `gpg.format=ssh` · `gpg.ssh.allowedSignersFile` |
| systemd | 255 (Ubuntu 24.04) | user session + unit control |

**Platform-specific caveat (WSL2):**
- `wsl.conf` 의 `systemd=true` 는 WSL 0.67.6+ 에서 정식 지원. `wsl --version` 으로 확인.
- WSL2 Mirror Mode 네트워킹은 기본 NAT 와 다름 — Khuk0 환경에서 `wsl.conf` 에 `[experimental] networkingMode=mirrored` 를 설정하면 `logger-pc` IP 가 Windows host 와 동일해질 수 있으나, 본 스토리는 **기본 NAT 모드** 전제로 Task 6 진행 (게이트웨이 IP 로 접근). mirrored mode 로의 마이그레이션은 Story 1.4 rsync 안정성 이슈 발생 시 재평가.

### References

- **Epic · Story source**: `_bmad-output/planning-artifacts/epics.md#Epic-1` (line 338), `#Story-1.2` (lines 457-488)
- **Architecture 보안 결정**: `_bmad-output/planning-artifacts/architecture.md#D7` (line 295 — keyring), `#D8` (line 297 — SSH signing), `#D10` (line 301 — LUKS), `#D21` (line 361 — pydantic-settings), `#AR-SEC1-2`, `#NFR-S1 매핑` (line 1009 — `keyring_client.py` 지정)
- **Architecture 인프라 결정**: `architecture.md#D17` (lines 338-341 — OS 분할), `#D12` (line 308 — rsync over SSH), `#D19` (line 348 — self-hosted runner, Story 1.3 소관), `#Integration-Points` (lines 1017-1028 — KIS · DART · S3 · LLM · Telegram · 카카오워크)
- **Architecture 파일 구조**: `architecture.md#Complete-Project-Directory-Structure` (line 696 — `keyring_client.py`, line 690 — `settings.py`)
- **PRD 보안 NFR**: `prd.md#NFR-S1` (line 1020 — `.env` 영구 금지), `#NFR-S2` (line 1021 — 주문/조회 key 분리), `#NFR-S5` (line 1024 — 로컬 네트워크 + SSH key), `#NFR-A5` (line 1051 — git signed commit), `#PT-6` (line 767 — Secret Management internal only)
- **Story 1.1 참조 (선행)**: `_bmad-output/implementation-artifacts/1-1-프로젝트-bootstrap-uv-monorepo-scaffold.md` 전체, 특히 § "Dev Notes Source-of-Truth Invariants" (lines 241-257), § "Debug Log References" (lines 353-398), § "Review Findings" (lines 519-558)
- **Deferred work log**: `_bmad-output/implementation-artifacts/deferred-work.md` — 본 스토리 Task 4.2 가 항목 5 번 (mypy hook deps) 을 first-step 해소
- **Implementation Readiness Report**: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-21.md` — READY verdict, Critical 0 / Major 0 / Minor 2 (본 스토리와 무관)

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context) — implementing as Amelia (bmad-agent-dev persona) under auto-mode.

### Debug Log References

| # | Phase | Issue | Root Cause | Resolution |
|---|---|---|---|---|
| 1 | Prereq | `git commit` failed with "Author identity unknown" | global `user.name`/`user.email` unset on Windows host | Set global `user.name="chulhwan"`, `user.email="wkdcjfghks1@gmail.com"` per Khuk0 instruction (replaces the `장철환` name used by Story 1.1 inline `-c` flags). |
| 2 | Task 2 | pre-commit mypy on single file `keyring_client.py`: `Cannot find implementation or library stub for module named "keyring"` | `.pre-commit-config.yaml` mypy hook `additional_dependencies` missing `keyring>=25` | Added `keyring>=25` to hook deps — brought forward from Task 4.2 into Task 2 commit. |
| 3 | Task 2 | pre-commit mypy on single file: `Source file found twice under different module names: "core" and "athena.core"` (Story 1.1 deferred bug that only surfaces on per-file runs) | `packages/<pkg>/athena/` is a PEP-420 namespace dir (no `__init__.py`). Without `explicit_package_bases`, mypy double-resolves single files passed via `--files`. All-files runs happened to avoid the bug because mypy picked the `athena.core` resolution first. | Added `explicit_package_bases = true` to `[tool.mypy]` in `pyproject.toml`. |
| 4 | Task 2 | ruff S105 fired on `KIS_ORDER_APP_SECRET`, `KIS_QUERY_APP_SECRET`, `TELEGRAM_BOT_TOKEN`, `S3_SECRET_ACCESS_KEY`, `LUKS_PASSPHRASE` (heuristic flagged enum values whose identifier ends in *_SECRET/*_TOKEN/*_PASSPHRASE) | S105 (hardcoded-password) treats `"LUKS_PASSPHRASE"` as a password string. In a secret-NAME registry, the value is a lookup ID, not a credential. | `[tool.ruff.lint.per-file-ignores]` entry for `packages/athena-core/athena/core/keyring_client.py` disables S105 with reasoning comment. |
| 5 | Task 3 | `test_settings_forbids_extra_env` (env-var variant) did not raise — pydantic-settings silently ignored unknown `ATHENA_*` env vars | `extra="forbid"` governs model constructor kwargs, not the env-var surface. Env vars that don't match a declared field are simply not read. | Renamed test to `test_settings_forbids_extra_kwargs` and exercises `Settings(unknown_field="x")`. This is the correct semantics for `extra="forbid"`. Kept AC-3 intent (reject unknown config) satisfied, just via the correct entry point. |
| 6 | Task 3 | Pydantic v2.11 deprecation warning on `dir(Settings())` — `model_fields` / `model_computed_fields` instance access | Walking `dir(instance)` triggers Pydantic v2.11's deprecation shim for these attributes (scheduled removal in v3.0). | `test_all_14_secret_accessors_exist` now walks `dir(Settings)` (the class). Same coverage, no deprecation warning. |
| 7 | Task 4 | ruff N811 on `from athena.core.settings import _EXCLUDE_DIRS as settings_exclude` — "Constant imported as non-constant" | Alias `settings_exclude` is lowercase; ruff N811 enforces constants keep UPPER_CASE on import. | Renamed alias to `SETTINGS_EXCLUDE_DIRS`. |

### Completion Notes List

**Completed (code tasks) — 2026-04-21:**

- **Prerequisite cleanup** (commit `2f95bb6`) — Story 1.1 review patches (16 modified + 4 untracked) landed as one commit before Story 1.2 work began (per Dev Notes § Git Intelligence Summary). Workspace now clean before new commits.
- **Task 2** (commit `35ac260`) — `athena.core.keyring_client` with 14-secret `SecretName(StrEnum)` registry + `get_secret` / `set_secret` + AST no-shell defense. Bundled Task 4.2 mypy hook deps fix + Story 1.1 deferred `explicit_package_bases` fix + ruff S105 per-file-ignore. +15 tests.
- **Task 3** (commit `a755d48`) — `athena.core.settings` with `_ensure_no_dotenv_files` import-time guard + `Settings(BaseSettings)` (frozen, extra=forbid, 14 non-caching secret accessors) + `get_settings()` lru_cache singleton. +22 tests.
- **Task 4** (commit `0558d3e`) — `tests/regression/test_no_dotenv_files.py` full-tree `.env` ban with independent `EXCLUDE_DIRS` duplicate + drift detector. +2 tests.

**Test suite delta:** Story 1.1 closed at 72 passing / 2 skipped (includes Story 1.1 review patches). Story 1.2 after Tasks 2-4: **111 passing / 2 skipped** (+39 new tests — estimate in story Task 7.3 was "+19 min, +25 max"; actual is higher because `_ensure_no_dotenv_files` parametrize expansion adds 5 cases per filename, and full accessor coverage/missing-error/literal-rejection paths added).

**Manual tasks pending Khuk0 action:**

- Task 1: WSL2 Ubuntu 24.04 + systemd (PowerShell admin)
- Task 5: Git SSH signing setup (WSL2 shell)
- Task 6: Windows OpenSSH Server + Logger↔Trading SSH trust (Windows admin + WSL2)
- Task 7: final playbook append + handoff commit (requires Task 5 signing active)

See § "Khuk0 Handoff — Manual Steps" at the end of this file for the exact command blocks.

### File List

**New files:**
- `packages/athena-core/athena/core/keyring_client.py` (Task 2.1)
- `packages/athena-core/athena/core/settings.py` (Task 3.1)
- `packages/athena-core/tests/test_keyring_client.py` (Task 2.2)
- `packages/athena-core/tests/test_keyring_client_no_shell.py` (Task 2.3)
- `packages/athena-core/tests/test_settings.py` (Task 3.2)
- `tests/regression/test_no_dotenv_files.py` (Task 4.1)

**Modified files:**
- `pyproject.toml` (Task 2: `explicit_package_bases=true` under `[tool.mypy]` + `S105` per-file-ignore for `keyring_client.py`)
- `.pre-commit-config.yaml` (Task 2 = Task 4.2: mypy hook `additional_dependencies += keyring>=25`)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (Task 4: Story 1.2 status `ready-for-dev` → `in-progress`)
- `_bmad-output/implementation-artifacts/1-2-환경-secrets-infrastructure-wsl2-os-keychain-ssh-signing.md` (self — Dev Agent Record + task checkboxes)

**To be modified during Task 7 (after Khuk0 manual steps):**
- `docs/operating_playbook.md` — append § "Story 1.2 — Environment & Secrets Infrastructure" with Task 1/5/6 verification blocks
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Story 1.2 status `in-progress` → `review`

## Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-04-21 | 0.1.0 | Story 1.2 file created from epics.md (ready-for-dev) | John (PM) via create-story |
| 2026-04-21 | 0.2.0 | Story 1.1 review patches landed (commit `2f95bb6`) as prerequisite cleanup | Amelia (dev) |
| 2026-04-21 | 0.3.0 | Tasks 2-4 complete: keyring_client (`35ac260`), settings (`a755d48`), .env regression (`0558d3e`). +39 tests. Code-bearing portion of Story 1.2 done; awaiting Khuk0 host setup for Tasks 1/5/6/7. | Amelia (dev) |

## Khuk0 Handoff — Manual Steps

This block details the WSL2 / Windows / SSH commands that Claude Code cannot execute on Khuk0's behalf (either require admin elevation, WSL install, or physical-host interaction). After each numbered block, paste the raw command outputs into the target section of `docs/operating_playbook.md` as indicated.

### [Manual] Task 1: WSL2 Ubuntu 24.04 + systemd

**1a. Windows PowerShell (run as Administrator):**

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
```

On first boot: username `khuk0`, your password.

**1b. WSL2 shell:**

```bash
sudo tee /etc/wsl.conf > /dev/null <<'EOF'
[boot]
systemd=true

[interop]
appendWindowsPath=false
EOF
```

**1c. Windows PowerShell:** `wsl --shutdown` → re-enter WSL2.

**1d. WSL2 shell — install base packages + placeholder dirs:**

```bash
sudo apt update && sudo apt install -y build-essential git curl openssh-client ca-certificates
sudo mkdir -p /var/lib/athena/{policy,ledger,data} /data/parquet /mnt/external
sudo chown -R khuk0:khuk0 /var/lib/athena /data/parquet
```

**1e. Capture for playbook (paste into § "Story 1.2 Task 1 — WSL2 setup"):**

```bash
wsl -l -v                  # run from Windows PowerShell
cat /etc/os-release        # from WSL2
systemctl --user status    # from WSL2
ps -p 1 -o comm=           # from WSL2, must show "systemd"
```

### [Manual] Task 5: Git SSH Signing

**5a. WSL2 shell — generate signing key:**

```bash
ssh-keygen -t ed25519 -C "khuk0@athena-signing" -f ~/.ssh/id_ed25519_athena_sign -N ""
```

**5b. Build `~/.ssh/allowed_signers`:**

```bash
echo "wkdcjfghks1@gmail.com $(awk '{print $1" "$2}' ~/.ssh/id_ed25519_athena_sign.pub)" > ~/.ssh/allowed_signers
chmod 600 ~/.ssh/allowed_signers
```

**5c. Global git config (WSL2 side):**

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_athena_sign.pub
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
git config --global commit.gpgsign true
git config --global tag.gpgsign true
# name/email already set globally to chulhwan / wkdcjfghks1@gmail.com on Windows side;
# WSL2 has its own ~/.gitconfig — re-run these two on WSL2 to mirror:
git config --global user.name "chulhwan"
git config --global user.email "wkdcjfghks1@gmail.com"
```

**5d. Verification signed commit:**

```bash
cd ~/vibe/invest_training  # adjust if WSL2 mount path differs
git commit -S --allow-empty -m "chore(story-1.2): enable git SSH signing (AC-4)"
git log --show-signature -1
git verify-commit HEAD
```

Copy `git log --show-signature -1` + `ssh-keygen -lf ~/.ssh/id_ed25519_athena_sign.pub` (fingerprint only) to playbook § "Story 1.2 Task 5 — SSH signing setup".

### [Manual] Task 6: Logger PC ↔ Trading PC SSH + Firewall

**6a. Windows PowerShell (Administrator):**

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
New-NetFirewallRule -Name "sshd-local-subnet" `
    -DisplayName "OpenSSH Server (local subnet only)" `
    -Protocol TCP -LocalPort 22 -Direction Inbound `
    -Action Allow -Profile Private -RemoteAddress LocalSubnet
Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue | Disable-NetFirewallRule
```

**6b. WSL2 — generate trust key:**

```bash
ssh-keygen -t ed25519 -C "trading-pc->logger-pc" -f ~/.ssh/id_ed25519_athena_logger_sync -N ""
cat ~/.ssh/id_ed25519_athena_logger_sync.pub  # copy this single line
```

**6c. Windows PowerShell — install public key with restricted ACL:**

```powershell
$authkeys = "$env:USERPROFILE\.ssh\authorized_keys"
New-Item -ItemType Directory -Path (Split-Path $authkeys) -Force | Out-Null
Add-Content -Path $authkeys -Value "<paste WSL2 public key line>" -Encoding ASCII
icacls $authkeys /inheritance:r
icacls $authkeys /grant "SYSTEM:(R)" "$env:USERNAME:(R)"
```

**6d. WSL2 — find Windows host IP + write SSH config:**

```bash
HOST_IP=$(ip route show | awk '/^default/ {print $3}')
echo "Windows host IP seen from WSL2: $HOST_IP"
cat >> ~/.ssh/config <<EOF

Host logger-pc
    HostName $HOST_IP
    User khuk0
    IdentityFile ~/.ssh/id_ed25519_athena_logger_sync
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF
chmod 600 ~/.ssh/config
```

**6e. Verify — success path:**

```bash
ssh logger-pc "echo ok"
```

Expected: stdout `ok`, exit 0, no password prompt.

**6f. Verify — deny path (Windows PowerShell):**

Use the PUBLIC IP (e.g. from `curl ifconfig.me`) with `Test-NetConnection -ComputerName <public_ip> -Port 22` — must return `TcpTestSucceeded: False`. (Alternative: phone-tether to an external network and try to SSH in.)

**6g. Capture for playbook (§ "Story 1.2 Task 6"):**

```bash
# WSL2
ssh logger-pc "echo ok"
ssh-keygen -lf ~/.ssh/known_hosts
```

```powershell
# Windows
Get-NetFirewallRule -Name sshd-local-subnet | Format-List DisplayName,Enabled,Profile,Action
Get-NetFirewallRule -Name sshd-local-subnet | Get-NetFirewallAddressFilter | Format-List RemoteAddress
```

### [Manual] Task 7: After Tasks 1, 5, 6 complete

Once Khuk0 finishes the above, the dev agent (Amelia in a fresh session, or continuing this one) will:

1. Append the captured verification blocks to `docs/operating_playbook.md` under §§ "Story 1.2 Task 1", "Task 5", "Task 6" (Task 7.1).
2. Re-run the 5-gate: `uv sync --frozen --group dev` → `uv run pytest -n auto` → `uv run pre-commit run --all-files` → `uv run lint-imports` → `uv build --package athena-core --wheel --out-dir /tmp/athena-1-2-check`. All must pass (Task 7.2).
3. Record the final test count in Dev Agent Record § Completion Notes List (Task 7.3).
4. Create the handoff signed commit `chore(story-1.2): WSL2 + OS Keychain + SSH signing infra verified, hand off to Story 1.3` (Task 7.4) — this will be **signed** because Task 5 activated `commit.gpgsign=true`. Verify with `git log --show-signature -1`.
5. Update `sprint-status.yaml`: Story 1.2 `in-progress` → `review` (Task 7.5).
6. Set story file `Status: review` at the top of this document.
