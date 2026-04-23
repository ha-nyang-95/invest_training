# Story 1.5: Pre-Trade Ledger 초기 세그먼트 & SHA-256 체인

Status: done

Epic: 1 — Foundation & Market Truth Capture
Story Key: `1-5-pre-trade-ledger-초기-세그먼트-sha-256-체인`
FR Coverage (direct): FR38 substrate (Pre-Trade Ledger append-only 구조·DDL·genesis·체인 writer minimal path — 실 writer 완성은 Story 6.1), FR39 substrate (월말 SHA-256 segment hash 계산 + 외장 SSD LUKS + S3 Object Lock 2-target 백업 경로 — 실 systemd timer 스케줄은 Story 1.10)
FR Coverage (substrate for): FR22 (청산 이벤트 Ledger 기록 — Story 4.7), FR45 (준법감시인 회신 Ledger append — Story 6.7), FR17 (anti_ego_events SHA-256 체인은 본 구조 재사용 — Story 3.1)
NFR Coverage (direct): NFR-S3 (append-only tamper-evident 구조 — SHA-256 월간 체인 해시 + UPDATE/DELETE 물리 차단), NFR-A1 (모든 주문 의도·체결·거부 이벤트 월간 체인 해시 + 외장 write-only 백업 substrate), NFR-A2 (영구 보존 substrate — segment hash 파일은 삭제 금지 정책)
NFR Coverage (hooks): NFR-O3 (Ledger 체인 해시 불일치 → Critical 알림 + Global CB hook — 본 스토리는 검증 script 에 hook 만 준비, Story 1.9 Prometheus rule + Story 5.6 Global CB 연동 완성), NFR-S1 (LUKS 키 + S3 credential 은 OS Keychain, `.env`/평문 금지), NFR-M4 (`user_id` 컬럼 commercialization seam — pre_trade_ledger 도 동일 prefix 준수)
AR Coverage (direct): AR-DATA4 (스키마 마이그레이션 = 새 DuckDB 파일 + Ledger 체인 새 세그먼트 시작 — 본 스토리가 "새 세그먼트 시작" 의 mechanism 확정), AR-DATA6 (Ledger 백업 2-target: 외장 SSD LUKS 실시간 mirror + S3 Object Lock Compliance 월간), AR-SEC4 (백업 암호화 — LUKS + S3 SSE-C, 키 OS Keychain), D6 (2-target backup), Enforcement #5 (Ledger 직접 SQL 금지 — `LedgerClient` 단일 진입점)

## Story

As **Khuk0's Athena system needing legally-compliant (§178-2) tamper-evident audit trail from Week 1 — before any decision/order is ever written**,
I want **`decisions.duckdb` 의 6번째 테이블로 `pre_trade_ledger` 를 append-only SHA-256 체인 구조 + `LedgerClient.append()` 유일 진입점 + UPDATE/DELETE 물리 차단 (DuckDB view + AFTER-trigger 패턴) + genesis entry + 월말 segment_hash 계산 placeholder + 외장 SSD LUKS + S3 Object Lock Compliance 2-target 백업 경로 + verify_ledger.py 정기 검증 CI substrate 로 초기화**하여,
so that **Story 6.1 의 full LedgerWriter 가 상주할 때, Story 3.1 의 anti_ego_events 체인이 동일 패턴을 재사용할 때, Story 4.7 의 청산 이벤트가 Ledger 에 1:1 기록될 때 — 그리고 무엇보다 Week 2 부터 Paper/Prod decision 이 발생하기 전에 — **모든 write path 의 mandatory sink** 가 이미 append-only + 체인 무결성 + 2-target 백업 + 검증 script 형태로 준비된 상태이고, NFR-S3 "자기 override 로 수정 불가능한 tamper-evident" 가 OS+DuckDB 레벨로 enforce 되며 AR-DATA4 "새 스키마는 Ledger 체인 새 세그먼트 시작" 의 mechanism 이 이미 녹아 있다**.

## Acceptance Criteria

**AC-1: `pre_trade_ledger` 테이블 DDL (decisions.duckdb 의 6번째 테이블) + BaseDTO 상속 `LedgerEntry` Pydantic DTO + UPDATE/DELETE 물리 차단 (DuckDB view + trigger 패턴)** [Source: epics.md#Story-1.5 lines 562-565, architecture.md#D4 line 285 ("새 스키마 → 새 DuckDB + Ledger 체인 새 세그먼트"), architecture.md line 788 (`schema.sql` 파일 위치), architecture.md lines 407-411 (naming), prd.md FR38 line 968, Story 1.4 Source-of-Truth Invariant #7 (4-필드 prefix)]

**Given** `packages/athena-execution/` 가 Story 1.1 Task 1.4 에서 빈 namespace package 로 scaffold 됨 (현재 `packages/athena-execution/athena/execution/__init__.py` docstring 한 줄 만 존재) + `packages/athena-execution/pyproject.toml` 에 `duckdb>=1` 미선언 — 본 Task 가 의존 추가 + `athena-core` / `athena-feature-store` intra-workspace 의존 관계 선언 (import 계층: `execution ← feature_store ← core`)
**And** Story 1.4 Task 1 에서 확정된 4-필드 prefix invariant (`timestamp TIMESTAMPTZ NOT NULL`, `module_version VARCHAR(64) NOT NULL`, `policy_version_git_sha VARCHAR(48) NOT NULL`, `user_id INTEGER NOT NULL DEFAULT 1`) 가 `pre_trade_ledger` 에도 그대로 상속

**When** 본 Task 1 이 다음 파일들을 작성:
  - `packages/athena-execution/athena/execution/ledger/schema.sql` — DuckDB 1.x DDL 원문 (SQL 스크립트 파일로 분리. 이유: architecture.md line 788 가 명시적으로 `schema.sql` 파일 요구 + 장래 Story 6.1 의 full writer 가 DDL 텍스트 자체를 read-verify 에 사용). 다음 3개 statement 포함:
    1. `CREATE TABLE pre_trade_ledger_raw (...)` — 실 append-only 물리 테이블
    2. `CREATE VIEW pre_trade_ledger AS SELECT * FROM pre_trade_ledger_raw` — read 진입점 (application 코드는 view 만 read, raw 테이블은 LedgerClient 만 write)
    3. `CREATE OR REPLACE MACRO block_ledger_update() AS ...` 는 DuckDB 가 row-level trigger 미지원 — **대안: DuckDB 1.x 는 trigger 가 없으므로 UPDATE/DELETE 는 (a) Python 레벨 `LedgerClient` 의 유일 진입점 + (b) `test_trading_pc_write_scope.py` 확장 (`UPDATE pre_trade_ledger` / `DELETE FROM pre_trade_ledger` 문자열 금지 AST 검사) 두 층으로 차단**. (epics.md AC 본문의 "view + trigger pattern" 을 DuckDB 제약에 맞춰 재해석 — 물리 trigger 불가, 따라서 application invariant + ruff-adjacent 회귀 테스트로 enforce. Dev Agent Record 에 결정 근거 기록 필수.)
  - **Ledger schema — 정확한 컬럼 리스트** (epics.md lines 563-565 명시 컬럼 + Story 1.4 4-필드 prefix + BaseDTO 동기화):
    - `id BIGINT PRIMARY KEY` — DuckDB sequence 기반 auto-increment (`CREATE SEQUENCE seq_pre_trade_ledger_id START 1`)
    - `timestamp TIMESTAMPTZ NOT NULL` (BaseDTO 상속 — entry 생성 시각 UTC)
    - `module_version VARCHAR(64) NOT NULL` (BaseDTO)
    - `policy_version_git_sha VARCHAR(48) NOT NULL` (BaseDTO + epics.md line 564 에 별도 명시)
    - `user_id INTEGER NOT NULL DEFAULT 1` (NFR-M4 seam)
    - `event_type VARCHAR(64) NOT NULL` — Pydantic Literal 로 V1.0 허용 값 고정 (Story 6.1 이 확장 시 Change Control). V1.0 초기 값: `{'genesis', 'schema_segment_transition'}` (본 스토리만 사용). Story 3.1/3.7/4.7/6.1 이 각자 허용 event_type 확장 (예: `'entry_authorized'`, `'entry_rejected_*'`, `'order_placed'`, `'order_filled'`, `'compliance_email_sent'` 등 — epics.md lines 2114-2119 full list 는 Story 6.1 소관).
    - `payload_json VARCHAR NOT NULL` — 이벤트 payload 의 canonical JSON (deterministic serialization: `json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)`). 해시 재현성을 위해 canonical form 필수.
    - `prev_hash VARCHAR(64)` — 이전 entry `this_hash` (64-char hex). genesis 만 NULL 허용 — `CHECK (id = 1 AND prev_hash IS NULL) OR (id > 1 AND prev_hash IS NOT NULL)`
    - `this_hash VARCHAR(64) NOT NULL` — 현재 entry 해시 (아래 규칙으로 LedgerClient 가 계산)
    - `param_hash VARCHAR(64) NOT NULL` — 이벤트 시점 policy 파라미터의 SHA-256 (본 스토리는 빈 dict `{}` 의 canonical SHA-256 = `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` 를 placeholder; 실 파라미터 직렬화는 Story 6.1)
    - `created_at_utc TIMESTAMPTZ NOT NULL DEFAULT now()` — DB 레벨 삽입 시각 (epics.md line 564 명시). 즉, 본 테이블은 2개 시각 컬럼 공존: `timestamp` (BaseDTO, 이벤트 발생 시각 = application-asserted) vs `created_at_utc` (DB 삽입 시각 = DB-asserted). 의의: application clock skew 검출용 — Story 6.2 의 verify job 이 `created_at_utc < timestamp - tolerance` or `created_at_utc > timestamp + 1h` 를 anomaly 로 reporting.
  - Primary index: `CREATE INDEX idx_pre_trade_ledger_created_at ON pre_trade_ledger_raw(created_at_utc)` — Story 1.4 Naming 규약 (`idx_<table>_<columns>`) 준수. 추가 인덱스 (event_type 기반 조회 등) 는 Story 6.1 이 필요 시 추가.
  - **Pydantic DTO** `LedgerEntry(BaseDTO)` — `packages/athena-execution/athena/execution/ledger/dto.py`:
    ```python
    from __future__ import annotations
    from typing import Literal
    from pydantic import Field
    from athena.core.dto import BaseDTO

    # V1.0 허용 event_type — Story 6.1 이 full 집합으로 확장.
    # 본 스토리가 실제 append 하는 것은 'genesis' 와 (스키마 진화 시) 'schema_segment_transition' 두 가지뿐.
    LedgerEventTypeV1 = Literal["genesis", "schema_segment_transition"]

    class LedgerEntry(BaseDTO):
        # BaseDTO inherit: timestamp (UTC), module_version, policy_version_git_sha
        user_id: int = Field(default=1, ge=0)
        event_type: LedgerEventTypeV1
        payload_json: str  # canonical JSON (sort_keys=True, separators=(',', ':'))
        prev_hash: str | None = Field(default=None, min_length=64, max_length=64)
        this_hash: str = Field(min_length=64, max_length=64)
        param_hash: str = Field(min_length=64, max_length=64)
        # created_at_utc 는 DB server-side default — DTO 에는 optional read-back 필드로만
        created_at_utc: datetime | None = None
    ```
    `LedgerEntry` 는 immutable (BaseDTO 의 `frozen=True, strict=True, extra=forbid` 상속).
  - `packages/athena-execution/athena/execution/ledger/__init__.py` — `from .client import LedgerClient` + `from .dto import LedgerEntry, LedgerEventTypeV1` 재노출
  - `packages/athena-execution/athena/execution/ledger/schema.py` — Python 바인딩:
    ```python
    from pathlib import Path
    import duckdb

    SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")

    def create_pre_trade_ledger(conn: duckdb.DuckDBPyConnection) -> None:
        """Idempotent — safe to run on every LedgerClient init.
        CREATE TABLE/VIEW/SEQUENCE statements all use IF NOT EXISTS semantics."""
        conn.execute(SCHEMA_SQL)
    ```
    idempotent: `CREATE SEQUENCE IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, `CREATE OR REPLACE VIEW`.
  - `packages/athena-execution/pyproject.toml` 의존 추가: `athena-core` (workspace path dep), `athena-feature-store` (workspace), `duckdb>=1`, `pyarrow>=17`. Python 3.13 requires 유지.

**Then** `uv run python -c "import duckdb; from athena.execution.ledger.schema import create_pre_trade_ledger; conn = duckdb.connect(':memory:'); create_pre_trade_ledger(conn); print(sorted(r[0] for r in conn.execute(\"SELECT table_name FROM duckdb_tables() WHERE table_name LIKE 'pre_trade%' OR table_name = 'pre_trade_ledger'\").fetchall()), sorted(r[0] for r in conn.execute(\"SELECT view_name FROM duckdb_views() WHERE view_name LIKE 'pre_trade%'\").fetchall()))"` 출력이 정확히 `['pre_trade_ledger_raw'], ['pre_trade_ledger']` (raw 는 table, view 는 view)
**And** `PRAGMA table_info('pre_trade_ledger_raw')` 가 정확히 11개 컬럼 (`id`, `timestamp`, `module_version`, `policy_version_git_sha`, `user_id`, `event_type`, `payload_json`, `prev_hash`, `this_hash`, `param_hash`, `created_at_utc`) + `user_id notnull=1, dflt_value='1'` + `created_at_utc` 의 `dflt_value` 가 `now()` 포함 (DuckDB 의 default 표현 포맷은 1.x 마이너 버전 간 차이가 있어 substring 매칭: `.lower().startswith("now") or "current_timestamp" in .lower()`)
**And** `DROP TABLE IF EXISTS pre_trade_ledger` 는 view 에 대한 DROP TABLE 이므로 DuckDB 가 `Catalog Error: pre_trade_ledger is a view` 또는 `DROP VIEW` 요구 에러 raise (즉 view 를 table 인 척 조작할 수 없음 — catalog 레벨 separation 검증)
**And** `test_trading_pc_write_scope.py` 가 **Story 1.4 의 5 테이블에서 6 테이블로 갱신** (1.4 Invariant #7 에 이미 명시됨) — `insert_*` 메서드 정확히 6개 (추가: `insert_ledger_entry`) + `FeatureStore` 가 `pre_trade_ledger` 를 직접 read/write 하지 않음 (LedgerClient 가 전담) 을 AST 검사로 enforce
**And** `test_dto_ddl_parity.py` 가 **4번째 테이블 (pre_trade_ledger) 의 DTO ↔ DDL column set 일치** 를 추가 검증 — `LedgerEntry.model_fields.keys()` 와 `PRAGMA table_info('pre_trade_ledger_raw')` column set 의 exact equality (server-side default 컬럼 `id`, `created_at_utc` 는 DTO 에서 Optional 로 매핑되므로 parity 테스트의 expected set 에 포함)
**And** `packages/athena-execution/tests/test_ledger_schema.py` (no marker — stage-2 unit) 5 시나리오 pass:
  1. `create_pre_trade_ledger(:memory:)` → view + table + sequence 모두 생성, 두 번째 호출 idempotent (error 없이 pass)
  2. `INSERT INTO pre_trade_ledger_raw (...) VALUES (nextval('seq_pre_trade_ledger_id'), ...)` 직접 SQL 이 성공 (trigger 없음 — application-layer enforce 를 증명하기 위해 DB 레벨은 open 임을 명시)
  3. `UPDATE pre_trade_ledger_raw SET payload_json='tampered' WHERE id=1` 은 DuckDB 가 수락 (DB 레벨 차단 불가 — **Dev Note 명시**: 따라서 write-scope invariant test + LedgerClient 유일 진입점 + Ledger 직접 SQL 금지 ruff hook (Story 1.9) 3층으로 방어)
  4. `CHECK` constraint 검증: `INSERT ... (id=1, prev_hash='aa...')` → DuckDB `Constraint Error` (genesis 는 prev_hash NULL 만 허용)
  5. `CHECK` constraint: `INSERT ... (id=2, prev_hash=NULL)` → `Constraint Error` (non-genesis 는 prev_hash 필수)
**And** `packages/athena-execution/` 가 `lint-imports` 5 contracts 에서 allowed: `execution ← core`, `execution ← feature_store` 만. `execution → orchestrator` 등 역방향 import 시 fail (1.1 의 import-linter 설정 재활용)

---

**AC-2: `LedgerClient.append(entry: LedgerEntry)` 단일 진입점 + Genesis entry 자동 seed + SHA-256 해시 체인 무결성 (prev_hash 체인 + this_hash 계산 규칙)** [Source: epics.md#Story-1.5 lines 567-570, architecture.md#Process-Patterns lines 571-575 (`LedgerClient.append` 단일 진입점 규칙), prd.md NFR-S3 line 1022, Story 1.4 Source-of-Truth Invariant #3 (Trading PC write-scope)]

**Given** AC-1 의 `pre_trade_ledger` DDL 이 적용된 빈 `decisions.duckdb` + 호출 시점 `policy_version_git_sha` 가 `athena.core.version.POLICY_VERSION_SHA` 에서 조회 가능 (Story 1.1 Hatchling build hook 결과)

**When** 본 Task 2 가 `packages/athena-execution/athena/execution/ledger/hash_chain.py` + `client.py` 작성:
  - `hash_chain.py`:
    ```python
    from __future__ import annotations
    import hashlib
    import json
    from typing import Any

    HASH_PLACEHOLDER = "0" * 64  # 아직 계산되지 않은 this_hash 의 sentinel

    def canonical_json(payload: dict[str, Any]) -> str:
        """Deterministic JSON — sort_keys + 최소 separators + default=str.
        해시 재현성을 위해 모든 payload 직렬화는 본 함수 경유 필수."""
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def compute_entry_hash(
        *,
        prev_hash: str | None,
        payload_json: str,
        policy_version_git_sha: str,
        event_type: str,
        user_id: int,
    ) -> str:
        """Entry hash 계산 — input 순서와 separator 가 spec 의 일부.

        Genesis (prev_hash=None): SHA256("" || payload_json || policy_version_git_sha || event_type || user_id)
        Non-genesis: SHA256(prev_hash || payload_json || policy_version_git_sha || event_type || user_id)

        Separator: null byte (0x00) — UTF-8 문자열에 나타나지 않으므로 구분 모호성 없음.
        """
        sep = b"\x00"
        prev = (prev_hash or "").encode("ascii")
        body = sep.join([
            prev,
            payload_json.encode("utf-8"),
            policy_version_git_sha.encode("ascii"),
            event_type.encode("utf-8"),
            str(user_id).encode("ascii"),
        ])
        return hashlib.sha256(body).hexdigest()
    ```
    별개 이유: epics.md line 569 의 "`this_hash=SHA256(payload_json || policy_version_git_sha)`" 는 spec narrative 이고 minimal form 이지만, event_type + user_id 를 해시 input 에 포함하면 **동일 payload 가 다른 event_type 으로 재삽입되는 collision 방어** + V1.1+ multi-user 전환 시 user_id 오염 방어. spec extension 은 Dev Agent Record + Change Log 에 명시적 기록.
  - `client.py`:
    ```python
    from __future__ import annotations
    from typing import Any
    import duckdb
    from athena.core.version import POLICY_VERSION_SHA
    from athena.core.dto import BaseDTO
    from athena.execution.ledger.dto import LedgerEntry, LedgerEventTypeV1
    from athena.execution.ledger.hash_chain import canonical_json, compute_entry_hash
    from athena.execution.ledger.schema import create_pre_trade_ledger

    EMPTY_PARAM_HASH = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    # = sha256(b"{}").hexdigest() — V1.0 placeholder, Story 6.1 이 실 policy 파라미터 직렬화 대체

    class LedgerClient:
        """Pre-Trade Ledger 의 유일한 Python 진입점.

        ``conn.execute("INSERT INTO pre_trade_ledger_raw ...")`` 직접 호출은 영구 금지 —
        ruff custom rule (Story 1.9) + test_trading_pc_write_scope.py 가 AST 레벨로 차단.
        """

        def __init__(
            self,
            conn: duckdb.DuckDBPyConnection,
            *,
            user_id: int = 1,
            module_version: str = "LedgerClient.v1.0.0",
        ) -> None:
            self._conn = conn
            self._user_id = user_id
            self._module_version = module_version
            create_pre_trade_ledger(conn)  # idempotent
            self._ensure_genesis()

        def _ensure_genesis(self) -> None:
            """첫 append 이전에 genesis entry 가 자동으로 존재하도록 보장.
            두 번째 이후 호출은 no-op (id=1 존재 확인)."""
            existing = self._conn.execute(
                "SELECT id FROM pre_trade_ledger_raw WHERE id = 1"
            ).fetchone()
            if existing is not None:
                return
            from datetime import datetime, UTC
            genesis_payload = {
                "note": "ledger genesis — chain segment start",
                "policy_version_git_sha": POLICY_VERSION_SHA,
            }
            payload_json = canonical_json(genesis_payload)
            this_hash = compute_entry_hash(
                prev_hash=None,
                payload_json=payload_json,
                policy_version_git_sha=POLICY_VERSION_SHA,
                event_type="genesis",
                user_id=self._user_id,
            )
            self._conn.execute(
                "INSERT INTO pre_trade_ledger_raw "
                "(id, timestamp, module_version, policy_version_git_sha, user_id, "
                "event_type, payload_json, prev_hash, this_hash, param_hash) "
                "VALUES (nextval('seq_pre_trade_ledger_id'), ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
                [
                    datetime.now(UTC),
                    self._module_version,
                    POLICY_VERSION_SHA,
                    self._user_id,
                    "genesis",
                    payload_json,
                    this_hash,
                    EMPTY_PARAM_HASH,
                ],
            )

        def append(
            self,
            *,
            event_type: LedgerEventTypeV1,
            payload: dict[str, Any],
            param_hash: str = EMPTY_PARAM_HASH,
        ) -> int:
            """Append 1 entry, return assigned id.

            V1.0 event_type 집합은 genesis 와 schema_segment_transition 2개뿐.
            Story 6.1 이 allowed Literal 을 확장하면 본 메서드 signature 는
            그대로 유지되고 Literal 타입만 넓어짐 (mypy 는 호출부에서 검증).
            """
            prev = self._conn.execute(
                "SELECT this_hash FROM pre_trade_ledger_raw ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if prev is None:
                raise RuntimeError(
                    "pre_trade_ledger_raw has no genesis — LedgerClient __init__ failed?"
                )
            prev_hash = prev[0]
            payload_json = canonical_json(payload)
            this_hash = compute_entry_hash(
                prev_hash=prev_hash,
                payload_json=payload_json,
                policy_version_git_sha=POLICY_VERSION_SHA,
                event_type=event_type,
                user_id=self._user_id,
            )
            from datetime import datetime, UTC
            self._conn.execute(
                "INSERT INTO pre_trade_ledger_raw "
                "(id, timestamp, module_version, policy_version_git_sha, user_id, "
                "event_type, payload_json, prev_hash, this_hash, param_hash) "
                "VALUES (nextval('seq_pre_trade_ledger_id'), ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    datetime.now(UTC),
                    self._module_version,
                    POLICY_VERSION_SHA,
                    self._user_id,
                    event_type,
                    payload_json,
                    prev_hash,
                    this_hash,
                    param_hash,
                ],
            )
            new_id = self._conn.execute(
                "SELECT currval('seq_pre_trade_ledger_id')"
            ).fetchone()[0]
            return int(new_id)
    ```
  - **동기 write** — architecture.md line 575 "append 는 동기 (해시체인 consistency 보장), 비동기 wrapper 금지" 준수. `async def append` 시그니처 금지.
  - **Concurrency 모델**: V1.0 은 단일 asyncio 프로세스 + 단일 DuckDB connection (architecture.md D13). 다중 asyncio task 가 append 를 동시 호출하는 경우 DuckDB connection 의 내부 mutex 가 직렬화. 단, **chain integrity 는 "이전 this_hash 읽기 + 현재 INSERT" 가 단일 SQL transaction 이 아니어야 확실**한가? → DuckDB connection 자체가 단일 스레드에서 쓰이므로 (asyncio 같은 루프 내 순차 실행) race 없음. 명시적 `BEGIN/COMMIT` 은 불필요하지만 **Dev Note 에 assumption 기록**. 멀티 커넥션 case 는 V1.1+ scope.

**Then** `packages/athena-execution/tests/test_ledger_client.py` (no marker — stage-2 unit, DuckDB :memory:):
  1. **Genesis auto-seed**: 빈 `:memory:` connection 으로 `LedgerClient(conn)` 생성 → `SELECT COUNT(*) FROM pre_trade_ledger` = 1, `SELECT event_type, prev_hash FROM pre_trade_ledger WHERE id=1` = `('genesis', NULL)`
  2. **Genesis idempotent**: 같은 connection 으로 `LedgerClient(conn)` 재생성 → COUNT 여전히 1 (genesis 중복 삽입 없음)
  3. **Single append**: `client.append(event_type='schema_segment_transition', payload={'reason': 'story-1.5 smoke'})` → `id=2` 반환, `SELECT prev_hash, this_hash FROM pre_trade_ledger WHERE id=2` 의 `prev_hash` 가 id=1 의 `this_hash` 와 일치, `this_hash` 는 64-char hex
  4. **Chain of N**: 5번 연속 append → id 순서대로 `prev_hash(n) == this_hash(n-1)` 모든 쌍 검증
  5. **Canonical JSON determinism**: 동일 payload dict 를 2번 append 하면 두 번의 `payload_json` 문자열이 bytewise 일치 (sort_keys 검증). 키 순서가 다른 dict `{'a':1,'b':2}` vs `{'b':2,'a':1}` 도 동일 `payload_json` 생성
  6. **Hash 검증**: Task 3 의 `verify_chain` 함수 (또는 inline assertion) 가 N+1 entry 전체 체인을 recompute → DB 값과 일치
  7. **V1.0 event_type Literal 제약**: `client.append(event_type='entry_authorized', ...)` 는 mypy 레벨에서 reject (Literal 위반) — 이 assertion 은 `tests/regression/test_ledger_event_type_literal.py` 에서 mypy 호출로 검증 (Task 2.5 참조)
  8. **Hash placeholder 진입 불가**: `HASH_PLACEHOLDER = "0"*64` 가 실제 append 경로에서 DB 에 저장되지 않음 (placeholder 는 추후 unused code 로 제거 가능 — 존재 여부는 regression grep 로 체크)

**And** `tests/integration/test_ledger_concurrency_smoke.py` (`@pytest.mark.integration`):
  - `asyncio` 단일 loop + 5개 task 동시 `client.append(...)` → 5 + 1(genesis) = 6 entry, 체인 연속성 검증 (asyncio 는 cooperative, 실 병렬 아님 → duckdb mutex 로 충분)
  - 멀티 커넥션 (2개 `open_decisions_duckdb` 인스턴스) 같은 파일 동시 `append` → **V1.0 scope 밖, skip with marker + deferred-work 기록**

**And** import 검증: `python -c "from athena.execution.ledger import LedgerClient, LedgerEntry"` 성공 + `__init__.py` 가 재노출 정확

---

**AC-3: 월말 SHA-256 segment_hash 계산 script `scripts/monthly_ledger_chain.py` placeholder (매월 1일 03:00 KST 실행 의도 — 실 systemd timer 스케줄은 Story 1.10) + 산출물 JSON 포맷 확정 + 외장 SSD LUKS + S3 Object Lock 2-target 저장 경로 확정** [Source: epics.md#Story-1.5 lines 572-575, architecture.md#D23 line 372 (월간 체인 해시 S3 Object Lock Compliance), architecture.md line 786 (`hash_chain.py` 월간 SHA-256), epics.md#Story-6.2 lines 2137-2167 (full backup script 는 Story 6.2)]

**Given** AC-2 의 `LedgerClient` 가 동작하고, `decisions.duckdb` 에 genesis + N 개 entry 가 존재 + 외장 SSD (또는 dev 환경의 LUKS 미설치 플레이스홀더 경로) + S3 bucket (또는 MinIO mock) 경로가 `athena.core.settings.Settings` 에 주입됨

**When** 본 Task 3 이 다음을 작성:
  - `packages/athena-execution/athena/execution/ledger/segment_hash.py`:
    ```python
    from __future__ import annotations
    import hashlib
    from dataclasses import dataclass
    import duckdb

    @dataclass(frozen=True)
    class SegmentHashResult:
        month: str  # "YYYY-MM"
        segment_hash: str  # 64-char hex
        prev_segment_hash: str | None  # None for the very first segment
        entry_count: int
        first_id: int | None
        last_id: int | None
        computed_at_utc: str  # ISO 8601

    def compute_segment_hash(
        conn: duckdb.DuckDBPyConnection,
        *,
        year: int,
        month: int,
        prev_segment_hash: str | None,
        policy_version_git_sha: str,
    ) -> SegmentHashResult:
        """전 월 entry 를 id 오름차순으로 읽어 segment_hash 계산.

        segment_hash = SHA256(prev_segment_hash || sorted_ids_hash || policy_version_git_sha)
        sorted_ids_hash = SHA256( "\n".join(str(id) for id in sorted(ids)) )

        entry 0 개 월은 `entry_count=0, first_id=None, last_id=None, segment_hash =
        SHA256(prev_segment_hash || "" || policy_version_git_sha)` — 공허한 달도 chain 을 이어감.
        """
        rows = conn.execute(
            "SELECT id FROM pre_trade_ledger "
            "WHERE created_at_utc >= make_timestamp(?, ?, 1, 0, 0, 0.0) "
            "AND created_at_utc < make_timestamp(?, ?, 1, 0, 0, 0.0) "
            "ORDER BY id",
            [year, month,
             year + (1 if month == 12 else 0),
             1 if month == 12 else month + 1],
        ).fetchall()
        ids = [r[0] for r in rows]
        sorted_ids_hash = hashlib.sha256(
            "\n".join(str(i) for i in ids).encode("ascii")
        ).hexdigest() if ids else hashlib.sha256(b"").hexdigest()
        body = "\x00".join([
            prev_segment_hash or "",
            sorted_ids_hash,
            policy_version_git_sha,
        ]).encode("utf-8")
        segment_hash = hashlib.sha256(body).hexdigest()
        from datetime import datetime, UTC
        return SegmentHashResult(
            month=f"{year:04d}-{month:02d}",
            segment_hash=segment_hash,
            prev_segment_hash=prev_segment_hash,
            entry_count=len(ids),
            first_id=ids[0] if ids else None,
            last_id=ids[-1] if ids else None,
            computed_at_utc=datetime.now(UTC).isoformat(),
        )
    ```
    separator `\x00` + `\n` 은 chain hash 의 **재현 가능한 canonical form**. Story 6.2 의 verify job 이 동일 함수 재호출.
  - `scripts/monthly_ledger_chain.py` (CLI, placeholder — systemd timer 실장착 Story 1.10 / 본격 writer Story 6.2):
    ```python
    from __future__ import annotations
    import argparse
    import json
    import sys
    from pathlib import Path
    from athena.core.version import POLICY_VERSION_SHA
    from athena.execution.ledger.segment_hash import compute_segment_hash
    from athena.feature_store.duckdb_client import open_decisions_duckdb

    def main() -> int:
        ap = argparse.ArgumentParser()
        ap.add_argument("--db", type=Path, required=True)
        ap.add_argument("--year", type=int, required=True)
        ap.add_argument("--month", type=int, required=True, choices=range(1, 13))
        ap.add_argument("--prev-segment-hash", type=str, default=None)
        ap.add_argument("--out-local", type=Path, required=True,
                        help="외장 SSD LUKS mount 경로 — 예: /mnt/external/ledger/year=2026/month=04/segment_hash.json")
        ap.add_argument("--s3-placeholder", type=Path, default=None,
                        help="S3 업로드 placeholder — Story 6.2 가 실 boto3 연동. 지정 시 파일을 이 경로에도 복사 (MinIO mock 등)")
        args = ap.parse_args()

        try:
            with open_decisions_duckdb(args.db) as conn:
                result = compute_segment_hash(
                    conn,
                    year=args.year,
                    month=args.month,
                    prev_segment_hash=args.prev_segment_hash,
                    policy_version_git_sha=POLICY_VERSION_SHA,
                )
        except Exception as e:
            print(json.dumps({"error_code": "LEDGER_SEGMENT_COMPUTE_FAILED",
                              "error": str(e)}), file=sys.stderr)
            return 1

        body = json.dumps({
            "month": result.month,
            "segment_hash": result.segment_hash,
            "prev_segment_hash": result.prev_segment_hash,
            "entry_count": result.entry_count,
            "first_id": result.first_id,
            "last_id": result.last_id,
            "computed_at_utc": result.computed_at_utc,
            "policy_version_git_sha": POLICY_VERSION_SHA,
        }, sort_keys=True, indent=2)

        # Atomic write to external (LUKS mount assumed pre-mounted — Task 4 섹션)
        args.out_local.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.out_local.with_suffix(args.out_local.suffix + ".tmp")
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(args.out_local)
        # chmod 444 (read-only) per epics.md Story 6.2 AC (본 스토리는 AC-3 에도 동일 적용)
        args.out_local.chmod(0o444)

        if args.s3_placeholder is not None:
            args.s3_placeholder.parent.mkdir(parents=True, exist_ok=True)
            args.s3_placeholder.write_text(body, encoding="utf-8")
            args.s3_placeholder.chmod(0o444)

        print(body)
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
    ```
    **scope**: 본 스토리는 LUKS mount / S3 업로드 자체를 실제로 수행하지 않음 — `--out-local` 이 쓰기 가능한 경로면 무관하게 동작. Story 1.10 이 systemd timer + `athena-backup.service` wrapper 에서 본 script 를 매월 1일 03:00 KST 호출. Story 6.2 가 boto3 Object Lock 업로드로 `--s3-placeholder` 를 대체.

**Then** `packages/athena-execution/tests/test_segment_hash.py` (no marker — unit):
  1. **Empty month**: 0 entry → `entry_count=0, first_id=None, last_id=None, segment_hash` = `SHA256(prev_segment_hash="" || sorted_ids_hash=SHA256("") || policy_version_git_sha)` 정확 검증
  2. **Single entry month**: genesis 1건만 → `entry_count=1, first_id=1, last_id=1, sorted_ids_hash = SHA256(b"1")`
  3. **Multi-entry determinism**: 같은 entry 집합을 두 번 `compute_segment_hash` → bitwise 동일 `segment_hash`
  4. **Prev chain**: N 월 segment_hash → N+1 월의 `prev_segment_hash` 로 주입 → N+1 segment_hash 재현 가능
  5. **Policy version 영향**: 동일 entry + 다른 `policy_version_git_sha` → segment_hash 변경 (policy rotation 이 체인에 기록)

**And** `tests/integration/test_monthly_ledger_chain_cli.py` (`@pytest.mark.integration`):
  1. `subprocess` 로 `python scripts/monthly_ledger_chain.py --db ... --year 2026 --month 4 --out-local tmp/segment_2026_04.json --s3-placeholder tmp/s3/ledger/user_id=1/year=2026/month=04/segment_hash.json` → exit 0, 두 파일 모두 생성됨, 내용 bitwise 동일
  2. 동일 경로 재실행: `--out-local` 가 이미 존재 + 모드 444 → `PermissionError` 은 `tmp.replace(args.out_local)` 가 `os.replace` (Windows 에서 dest 가 read-only 시 `PermissionError` 발생 가능) — 이를 사전 처리: replace 전에 `args.out_local.chmod(0o644)` (존재 시) 로 풀어두기 → 재실행 idempotent. Linux `os.replace` 는 read-only dest 덮어쓰기 허용하므로 Linux 는 무영향. **Dev Note 에 cross-platform 기록**.
  3. `--year 2026 --month 13` → argparse `choices` 에 의해 exit 2 (argparse ValueError)
  4. `--prev-segment-hash deadbeef...` 가 출력 JSON 에 정확히 반영
  5. 산출 JSON 이 다음 7 key 모두 포함: `month, segment_hash, prev_segment_hash, entry_count, first_id, last_id, computed_at_utc, policy_version_git_sha`

**And** 디렉토리 경로 spec 확정 (Dev Note + playbook 기록):
  - 외장 SSD: `/mnt/external/ledger/user_id=<N>/year=YYYY/month=MM/segment_hash.json` (hive-partition-friendly)
  - S3 (placeholder 경로 형식): `s3://<bucket>/ledger/user_id=<N>/year=YYYY/month=MM/segment_hash.json` — epics.md line 585 와 정확히 일치

---

**AC-4: 외장 SSD LUKS 파티션 초기화 스크립트 `scripts/init_external_backup.sh` (dry-run 모드 포함) + LUKS 키 OS Keychain 저장 경로 명시 + `/mnt/external` systemd auto-mount unit** [Source: epics.md#Story-1.5 lines 577-580, architecture.md#D10 line 301 (LUKS + SSE-C, 키 OS Keychain), architecture.md#AR-SEC4, Story 1.4 Task 3 (dry-run 모드 패턴 재사용)]

**Given** Trading PC WSL2 Ubuntu 24.04 LTS (Story 1.2 Task 1 완료) + `cryptsetup` 패키지 설치 가능 (`apt install cryptsetup`) + 외장 SSD 실제 하드웨어 부재 가능성 (W1 Day 1) — 이 경우 본 스토리는 `DRY_RUN=1` 모드로 명령 시퀀스만 검증

**When** 본 Task 4 가 다음을 작성:
  - `scripts/init_external_backup.sh`:
    ```bash
    #!/usr/bin/env bash
    # scripts/init_external_backup.sh — LUKS 초기화 + ext4 포맷 + /mnt/external 마운트 설정.
    # DRY_RUN=1 → 명령 print 만 수행, 실 디스크 조작 없음 (Logger PC 또는 외장 SSD 부재 환경).
    set -euo pipefail

    DEVICE="${DEVICE:-}"
    MOUNT_POINT="${MOUNT_POINT:-/mnt/external}"
    LUKS_NAME="${LUKS_NAME:-athena_external}"
    KEY_KEYCHAIN_ID="${KEY_KEYCHAIN_ID:-ATHENA_LUKS_EXTERNAL}"
    DRY_RUN="${DRY_RUN:-0}"

    if [[ -z "$DEVICE" && "$DRY_RUN" == "0" ]]; then
      echo "ERROR: DEVICE (예: /dev/sdb1) 필수 — 또는 DRY_RUN=1 로 호출" >&2
      exit 1
    fi
    if [[ "$DRY_RUN" == "1" && -z "$DEVICE" ]]; then
      DEVICE="/dev/sdX1-DRY"  # placeholder
    fi

    run() {
      if [[ "$DRY_RUN" == "1" ]]; then echo "[dry-run] $*"; return 0; fi
      eval "$@"
    }

    # 1. LUKS 키 조회 — OS Keychain 에 없으면 signal to Khuk0
    if [[ "$DRY_RUN" == "0" ]]; then
      if ! python3 -c "from athena.core.keyring_client import get_secret; import sys; sys.exit(0 if get_secret('$KEY_KEYCHAIN_ID') else 1)"; then
        echo "ERROR: OS Keychain 에 '$KEY_KEYCHAIN_ID' 없음. 다음 명령으로 설정:" >&2
        echo "  python3 -c \"from athena.core.keyring_client import set_secret; set_secret('$KEY_KEYCHAIN_ID', '<32-char-passphrase>')\"" >&2
        exit 2
      fi
    fi

    # 2. LUKS 포맷 (파괴적 — 기존 데이터 wipe)
    run "python3 -c \"from athena.core.keyring_client import get_secret; import sys; sys.stdout.write(get_secret('$KEY_KEYCHAIN_ID'))\" | sudo cryptsetup luksFormat --type luks2 --batch-mode $DEVICE -"

    # 3. LUKS open
    run "python3 -c \"from athena.core.keyring_client import get_secret; import sys; sys.stdout.write(get_secret('$KEY_KEYCHAIN_ID'))\" | sudo cryptsetup luksOpen $DEVICE $LUKS_NAME -"

    # 4. ext4 포맷
    run "sudo mkfs.ext4 -L athena_external /dev/mapper/$LUKS_NAME"

    # 5. 마운트 포인트 + systemd auto-mount
    run "sudo mkdir -p $MOUNT_POINT"
    run "sudo mount /dev/mapper/$LUKS_NAME $MOUNT_POINT"
    run "sudo chown khuk0:khuk0 $MOUNT_POINT"
    run "sudo mkdir -p $MOUNT_POINT/ledger"
    run "sudo chown -R khuk0:khuk0 $MOUNT_POINT/ledger"

    # 6. systemd unit (mount 자동 재시도) — 설치는 별도 task 또는 Story 1.10
    echo "NOTE: systemd mount unit (/etc/systemd/system/mnt-external.mount) 는 infra/systemd/mnt-external.mount 로 add; sudo systemctl enable --now 은 Story 1.10 backup automation 단계."

    echo "[ok] LUKS device $DEVICE mounted at $MOUNT_POINT"
    ```
  - `infra/systemd/mnt-external.mount` (systemd unit, 설치는 Story 1.10):
    ```ini
    [Unit]
    Description=Athena External SSD (LUKS) mount
    After=dev-mapper-athena_external.device
    Requires=dev-mapper-athena_external.device

    [Mount]
    What=/dev/mapper/athena_external
    Where=/mnt/external
    Type=ext4
    Options=defaults,noatime

    [Install]
    WantedBy=multi-user.target
    ```
    systemd `.mount` unit 은 unit 이름이 마운트 포인트 경로의 systemd escape form 과 일치해야 함 (`mnt-external.mount` ↔ `/mnt/external`). 본 스토리는 파일 생성 + dry-run 설치 시퀀스, 실 `systemctl enable --now` 은 Story 1.10.
  - `infra/systemd/dev-mapper-athena_external.device.service` (optional helper — LUKS open 을 부팅 시 자동 수행) — **V1.0 scope 밖**, 사용자가 Khuk0 1인이고 부팅 시 수동 `cryptsetup luksOpen` 수용 가능 (이유: LUKS 키 prompt 를 keychain 에서 자동 조회하려면 추가 systemd-ask-password plugin 필요, Story 1.10 와 묶어 처리).

**Then** `tests/integration/test_init_external_backup_dryrun.py` (`@pytest.mark.integration`):
  1. `DRY_RUN=1 bash scripts/init_external_backup.sh` → exit 0, stdout 에 `[dry-run] ` prefix 라인 5개 이상 (cryptsetup luksFormat, luksOpen, mkfs.ext4, mount, mkdir) — sudo 호출 없음, 실 디스크 조작 없음
  2. `DRY_RUN=0` + OS Keychain 에 키 부재 → exit 2 + stderr 에 `OS Keychain 에 'ATHENA_LUKS_EXTERNAL' 없음` 포함
  3. `DRY_RUN=0` + `DEVICE` 미지정 → exit 1 + stderr 에 `DEVICE (예: /dev/sdb1) 필수` 포함
  4. `infra/systemd/mnt-external.mount` 가 configparser 로 파싱 가능, `[Mount] Where=/mnt/external`, `Type=ext4` 정확

**And** **shellcheck 검증**: 본 script 가 shellcheck pass (CI 에 shellcheck 가 아직 없으므로 수동 검증, playbook 기록). Story 1.9 에서 shellcheck pre-commit hook 추가 검토.

**And** **OS Keychain 키 이름 규약 확정**: `ATHENA_LUKS_EXTERNAL` (외장 SSD LUKS passphrase), 이후 Story 1.10 이 `ATHENA_S3_CREDENTIALS_*` 추가. 키 이름은 `athena.core.keyring_client` 의 정식 카탈로그 (`KeychainKeys` enum 또는 constants) 에 등록 — Story 1.2 의 `get_secret`/`set_secret` API 에 이미 존재.

**And** playbook `docs/operating_playbook.md` § "Story 1.5 — LUKS 초기화 절차" 추가:
  1. 외장 SSD 연결 + `lsblk` 로 device path 확인 (예: `/dev/sdb1`)
  2. LUKS passphrase 생성 + OS Keychain 저장: `python3 -c "from athena.core.keyring_client import set_secret; import secrets; set_secret('ATHENA_LUKS_EXTERNAL', secrets.token_urlsafe(32))"`
  3. `DRY_RUN=1 bash scripts/init_external_backup.sh` 로 명령 sequence 선험
  4. 실 실행: `DEVICE=/dev/sdb1 bash scripts/init_external_backup.sh`
  5. `ls -la /mnt/external/ledger/` 로 mount 검증

---

**AC-5: S3 (또는 Naver Cloud Object Storage) Object Lock Compliance bucket 초기화 script `scripts/init_s3_object_lock.py` + 최소 5년 retention + 객체 키 네이밍 규약 검증 + MinIO mock 기반 integration test** [Source: epics.md#Story-1.5 lines 582-585, architecture.md#D6 lines 289-291 (Object Lock Compliance 모드, 최소 5년), architecture.md#AR-SEC4 (SSE-C AES-256, 키 OS Keychain), architecture.md#Integration-Points line 1027 (boto3, Compliance 모드), Story 1.4 의 Logger PC 부재 fallback pattern 재사용]

**Given** `boto3` 또는 Naver Cloud SDK 가 새 의존으로 추가 필요 + 실제 AWS 계정 + bucket 없이는 실행 불가 — MinIO (또는 localstack) 로 unit test 대체 + 실 bucket 생성은 Story 1.10 prerequisite

**When** 본 Task 5 가 다음을 작성:
  - `packages/athena-execution/pyproject.toml` 에 dev-dep `boto3>=1.34` + `botocore-stubs` (mypy) 추가. Naver Cloud 전환 시 SDK 변경은 Story 1.10 에서 재평가.
  - `packages/athena-execution/athena/execution/ledger/backup.py`:
    ```python
    from __future__ import annotations
    from dataclasses import dataclass
    from pathlib import Path

    @dataclass(frozen=True)
    class ObjectLockConfig:
        bucket: str
        region: str
        retention_years: int = 5
        mode: str = "COMPLIANCE"  # 또는 "GOVERNANCE" — V1.0 은 COMPLIANCE 고정

    def object_key_for_segment(*, user_id: int, year: int, month: int) -> str:
        """Story 6.2 도 동일 함수 사용 — 객체 키 네이밍 single source of truth.

        Format: ledger/user_id=<N>/year=YYYY/month=MM/segment_hash.json

        Story 1.4 의 Parquet hive partition 규약 (year=YYYY/month=MM) 과 의도적으로 일치 —
        S3 prefix-based 쿼리 도구 (s3 select, Athena 외부 쿼리) 가 동일 패턴 재사용 가능.
        """
        return f"ledger/user_id={user_id}/year={year:04d}/month={month:02d}/segment_hash.json"
    ```
  - `scripts/init_s3_object_lock.py`:
    ```python
    from __future__ import annotations
    import argparse
    import sys
    from athena.execution.ledger.backup import ObjectLockConfig

    def main() -> int:
        ap = argparse.ArgumentParser()
        ap.add_argument("--endpoint-url", default=None,
                        help="MinIO/localstack 호환 endpoint (예: http://localhost:9000). None = 실 AWS")
        ap.add_argument("--bucket", required=True)
        ap.add_argument("--region", default="ap-northeast-2")
        ap.add_argument("--retention-years", type=int, default=5)
        ap.add_argument("--dry-run", action="store_true",
                        help="SDK 호출 없이 plan 만 print")
        args = ap.parse_args()

        cfg = ObjectLockConfig(
            bucket=args.bucket,
            region=args.region,
            retention_years=args.retention_years,
        )

        if args.dry_run:
            print(f"[dry-run] Would create_bucket + put_object_lock_configuration:")
            print(f"  endpoint_url={args.endpoint_url}")
            print(f"  bucket={cfg.bucket}  region={cfg.region}")
            print(f"  Object Lock: mode={cfg.mode}, retention_days={cfg.retention_years * 365}")
            return 0

        # Actual boto3 path — Story 1.10 가 수동 실행, Story 6.2 가 완전한 업로드 경로
        try:
            import boto3
            from athena.core.keyring_client import get_secret
        except ImportError as e:
            print(f"ERROR: boto3 / keyring_client import 실패: {e}", file=sys.stderr)
            return 1

        aws_key = get_secret("ATHENA_S3_ACCESS_KEY")
        aws_secret = get_secret("ATHENA_S3_SECRET_KEY")
        if not aws_key or not aws_secret:
            print("ERROR: OS Keychain 에 'ATHENA_S3_ACCESS_KEY'/'ATHENA_S3_SECRET_KEY' 없음",
                  file=sys.stderr)
            return 2

        s3 = boto3.client(
            "s3",
            endpoint_url=args.endpoint_url,
            region_name=cfg.region,
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
        )
        try:
            s3.create_bucket(
                Bucket=cfg.bucket,
                CreateBucketConfiguration={"LocationConstraint": cfg.region},
                ObjectLockEnabledForBucket=True,
            )
        except s3.exceptions.BucketAlreadyOwnedByYou:
            print(f"NOTE: bucket {cfg.bucket} already exists, continuing")
        s3.put_object_lock_configuration(
            Bucket=cfg.bucket,
            ObjectLockConfiguration={
                "ObjectLockEnabled": "Enabled",
                "Rule": {
                    "DefaultRetention": {
                        "Mode": cfg.mode,
                        "Days": cfg.retention_years * 365,
                    }
                },
            },
        )
        s3.put_bucket_versioning(
            Bucket=cfg.bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        print(f"[ok] bucket={cfg.bucket} Object Lock Compliance {cfg.retention_years}년 활성")
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
    ```
  - **Naver Cloud 대안 문서**: `docs/operating_playbook.md` § "Story 1.5 — S3 / Naver Cloud 선택" — 비용/지리 관점에서 S3 ap-northeast-2 (Seoul) vs Naver Cloud Object Storage Compliance Lock. 본 스토리는 S3 API-호환 엔드포인트를 `--endpoint-url` 로 수용하므로 둘 다 대응. 실 선택은 Story 1.10 가 실 credential + bucket 생성 시 확정.

**Then** `packages/athena-execution/tests/test_backup.py` (no marker — unit):
  1. `object_key_for_segment(user_id=1, year=2026, month=4)` → `"ledger/user_id=1/year=2026/month=04/segment_hash.json"` 정확 (epics.md line 585 spec 과 bytewise 일치)
  2. `object_key_for_segment(user_id=1, year=2026, month=12)` → month padding 2자리 검증
  3. `ObjectLockConfig(retention_years=5, mode="COMPLIANCE")` 가 frozen dataclass (mutation 시 `FrozenInstanceError`)

**And** `tests/integration/test_init_s3_object_lock_dryrun.py` (`@pytest.mark.integration`):
  1. `python scripts/init_s3_object_lock.py --bucket athena-ledger-test --dry-run` → exit 0, stdout 에 `[dry-run] Would create_bucket` 포함, `Object Lock: mode=COMPLIANCE, retention_days=1825` 정확
  2. `--retention-years 10` → `retention_days=3650`
  3. 실 boto3 경로 테스트는 MinIO docker container 또는 moto mock library 사용 — **V1.0 scope**: moto 가 `put_object_lock_configuration` 를 mock 가능 한지 확인 후 integration 테스트 1 case (bucket 생성 + configuration 적용) 추가. moto 미지원 시 skip with `@pytest.mark.skip(reason="moto does not support Object Lock yet — verified locally with MinIO, Story 1.10 integrates")` + deferred-work 기록.

**And** **OS Keychain 키 이름 확정**: `ATHENA_S3_ACCESS_KEY`, `ATHENA_S3_SECRET_KEY` (또는 Naver Cloud 대응 `ATHENA_NCP_ACCESS_KEY`/`ATHENA_NCP_SECRET_KEY`). Story 1.10 이 실 credential 주입 시 본 이름 사용.

**And** **retention_days 정확성**: epics.md line 584 "최소 5년 retention" + architecture.md D6 "최소 5년 권장". V1.0 은 정확히 5 × 365 = 1825일 (윤년 무시 — 5년 중 최대 2일 오차 허용, Dev Note 명시).

---

**AC-6: `scripts/verify_ledger.py` 월간 검증 CI job substrate (prev 월 segment_hash ↔ 현 월 genesis prev_hash 연속성 + 전체 체인 재계산 일치 + 불일치 시 Critical 알림 + Global CB hook placeholder)** [Source: epics.md#Story-1.5 lines 587-590, architecture.md#D20 line 355-359 (CI gate), epics.md#Story-6.2 lines 2160-2162 (3-way 검증 full version 은 Story 6.2), prd.md NFR-O3 line 1042 (Critical alert 분기)]

**Given** AC-1~3 의 인프라 완비 + `decisions.duckdb` 에 genesis + N append 존재 + (옵션) 외장 SSD 경로에 이전 월 segment_hash.json 파일 존재

**When** 본 Task 6 이 다음을 작성:
  - `scripts/verify_ledger.py`:
    ```python
    from __future__ import annotations
    import argparse
    import json
    import sys
    from pathlib import Path
    import duckdb
    from athena.core.version import POLICY_VERSION_SHA
    from athena.execution.ledger.hash_chain import compute_entry_hash
    from athena.execution.ledger.segment_hash import compute_segment_hash
    from athena.feature_store.duckdb_client import open_decisions_duckdb

    def verify_chain(conn: duckdb.DuckDBPyConnection) -> list[dict]:
        """전체 pre_trade_ledger 체인의 각 entry 를 hash 재계산 → DB 값과 비교.

        Returns: list of mismatch dicts (빈 list 면 체인 무결).
        """
        rows = conn.execute(
            "SELECT id, event_type, policy_version_git_sha, user_id, "
            "payload_json, prev_hash, this_hash FROM pre_trade_ledger ORDER BY id"
        ).fetchall()
        mismatches = []
        last_this = None
        for (eid, ev, psha, uid, pj, prev, this) in rows:
            expected_prev = last_this  # chain 순서에서 이전 entry 의 this_hash
            if prev != expected_prev and not (eid == 1 and prev is None and expected_prev is None):
                mismatches.append({
                    "id": eid, "kind": "prev_hash_chain_break",
                    "stored_prev": prev, "expected_prev": expected_prev,
                })
            expected_this = compute_entry_hash(
                prev_hash=prev, payload_json=pj,
                policy_version_git_sha=psha, event_type=ev, user_id=uid,
            )
            if this != expected_this:
                mismatches.append({
                    "id": eid, "kind": "this_hash_mismatch",
                    "stored_this": this, "recomputed_this": expected_this,
                })
            last_this = this
        return mismatches

    def main() -> int:
        ap = argparse.ArgumentParser()
        ap.add_argument("--db", type=Path, required=True)
        ap.add_argument("--prev-segment-json", type=Path, default=None,
                        help="이전 월 segment_hash.json — 지정 시 genesis prev 와 연속성 확인")
        ap.add_argument("--year", type=int, default=None)
        ap.add_argument("--month", type=int, default=None)
        args = ap.parse_args()

        result = {"db": str(args.db), "verdict": "OK", "mismatches": [],
                  "segment_continuity": None}

        try:
            with open_decisions_duckdb(args.db) as conn:
                mismatches = verify_chain(conn)
                result["mismatches"] = mismatches
                if mismatches:
                    result["verdict"] = "CHAIN_BROKEN"

                if args.prev_segment_json and args.year and args.month:
                    prev = json.loads(args.prev_segment_json.read_text())
                    seg = compute_segment_hash(
                        conn, year=args.year, month=args.month,
                        prev_segment_hash=prev["segment_hash"],
                        policy_version_git_sha=POLICY_VERSION_SHA,
                    )
                    result["segment_continuity"] = {
                        "prev_month": prev["month"],
                        "prev_segment_hash": prev["segment_hash"],
                        "this_segment_hash": seg.segment_hash,
                        "this_month": seg.month,
                    }
        except Exception as e:
            result["verdict"] = "VERIFY_FAILED"
            result["error"] = str(e)

        print(json.dumps(result, indent=2, sort_keys=True))
        if result["verdict"] != "OK":
            # Story 1.9 Prometheus rule + Story 5.6 Global CB hook 발동 지점.
            # 본 스토리는 exit 코드로만 신호 (CI gate 의 exit != 0 → pipeline fail).
            return 1
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
    ```
  - **CI integration**: `.github/workflows/ci.yml` (Story 1.3 의 7-stage gate) 의 stage-3 또는 stage-6 직전에 `uv run python scripts/verify_ledger.py --db $LEDGER_DB_PATH` 호출 — **단 본 스토리의 CI 추가는 optional** 이며 decisions.duckdb 파일이 CI 환경에 없을 수 있음 → CI 에서는 `if [[ -f $LEDGER_DB_PATH ]]; then uv run verify_ledger ...; fi` 조건 래핑. Story 1.10 가 실제 backup + 월간 verify CI job 을 systemd timer 로 분리.
  - `.github/workflows/monthly-ledger-verify.yml` (월 1회 scheduled action) placeholder — 본 스토리는 YAML 파일만 add, 실 cron schedule 과 `workflow_dispatch` manual trigger 는 Story 1.10 에서 튜닝:
    ```yaml
    name: Monthly Ledger Verify
    on:
      schedule:
        - cron: '0 20 1 * *'  # 매월 1일 20:00 UTC = 05:00 KST 다음날 (03:00 KST 는 self-hosted runner idle 시간대, 가용성 우선 05:00 KST 지연 허용)
      workflow_dispatch:
    jobs:
      verify:
        runs-on: self-hosted
        steps:
          - uses: actions/checkout@v4
            with: { fetch-depth: 1 }
          - run: uv sync --frozen --group dev
          - run: uv run python scripts/verify_ledger.py --db $HOME/.local/share/athena/decisions.duckdb
    ```
    secret: `LEDGER_DB_PATH` 는 runner 환경변수로 Khuk0 가 설정. self-hosted 라서 외부 노출 없음.

**Then** `packages/athena-execution/tests/test_verify_chain.py` (no marker — unit):
  1. **Clean chain**: genesis + 3 append → `verify_chain(conn)` 반환 `[]` (mismatches 없음)
  2. **Tampered payload**: `UPDATE pre_trade_ledger_raw SET payload_json='tampered' WHERE id=2` (DB-level 조작 시뮬레이션) → `verify_chain` 반환에 `{"id": 2, "kind": "this_hash_mismatch", ...}` 포함
  3. **Broken prev chain**: `UPDATE pre_trade_ledger_raw SET prev_hash='deadbeef'*8 WHERE id=3` → `{"id": 3, "kind": "prev_hash_chain_break", ...}` + downstream entries 의 this_hash 재계산이 영향받지 않음 (각 entry 는 저장된 prev_hash + 저장된 payload 로 독립적으로 this_hash 재계산)
  4. **Genesis 특례**: `id=1, prev_hash=NULL` 은 chain_break 로 분류 안 됨 (genesis 만 허용)
  5. **Segment continuity**: prev-month `segment_hash` 주입 → `compute_segment_hash` 결과가 주입값을 prev 로 포함

**And** `tests/integration/test_verify_ledger_cli.py` (`@pytest.mark.integration`):
  1. 정상 `decisions.duckdb` → exit 0 + stdout JSON `"verdict": "OK"`
  2. Tampered → exit 1 + stdout JSON `"verdict": "CHAIN_BROKEN"` + mismatches 배열 non-empty
  3. DB 파일 부재 → exit 1 + `"verdict": "VERIFY_FAILED"` + `"error"` key 포함
  4. `--prev-segment-json` + 유효한 JSON → `segment_continuity` 섹션 포함

**And** `.github/workflows/monthly-ledger-verify.yml` 이 actionlint (또는 `yq` 파싱) 통과. 실 cron 튜닝은 Story 1.10.

**And** **Critical alert hook placeholder** (architecture.md line 551 "`CRITICAL`: Ledger 해시 불일치", prd.md NFR-O3 line 1042):
  - 본 스토리는 exit code 1 + stdout JSON 만 emit. Story 1.9 가 `infra/prometheus/rules/ledger_integrity.rules.yml` 작성 (architecture.md line 828 에 이미 파일명 명시됨). 본 스토리는 해당 파일의 placeholder 를 생성하지 않음 — verify_ledger.py 의 exit code 가 systemd journal 에 노출되는 것만으로도 Story 1.9 observability 가 alert rule 을 정의할 수 있음.
  - **Global CB hook** (epics.md line 590 "Global CB 발동 Epic 5 연동 hook 준비") — 실 CB 트리거는 Story 5.6. 본 스토리는 verify_ledger.py 의 `"verdict": "CHAIN_BROKEN"` stdout 을 contract 로 고정 → Story 5.6 의 CB state machine 이 이 contract 를 consume.

## Tasks / Subtasks

Execute **in order**. Mark `[x]` only when both implementation AND tests pass. Run the full test suite (`uv run pytest -n auto`) after each code-bearing task — never proceed with failing tests. Host-setup tasks (Task 4 LUKS, Task 5 S3) allow `DRY_RUN=1` / `--dry-run` fallback in Logger PC–absent / no-disk / no-AWS environments; real setup defers to Story 1.10.

- [x] **Task 1: `packages/athena-execution/athena/execution/ledger/{schema.sql,schema.py,dto.py,__init__.py}` + DuckDB DDL + LedgerEntry Pydantic DTO + 1.4 invariant test 확장** (AC: 1)
  - [x] 1.1 `packages/athena-execution/pyproject.toml` 업데이트: `[project.dependencies]` 에 `athena-core` (workspace), `athena-feature-store` (workspace), `duckdb>=1`, `pyarrow>=17` 추가. Python 3.13 requires 유지. uv lock 재생성.
  - [x] 1.2 `packages/athena-execution/athena/execution/ledger/schema.sql` 작성 — AC-1 의 정확한 11 컬럼 DDL (raw table + view + sequence + CHECK constraint). `CREATE TABLE IF NOT EXISTS` / `CREATE OR REPLACE VIEW` / `CREATE SEQUENCE IF NOT EXISTS` 모두 idempotent.
  - [x] 1.3 `packages/athena-execution/athena/execution/ledger/dto.py` 작성 — `LedgerEntry(BaseDTO)` + `LedgerEventTypeV1 = Literal["genesis", "schema_segment_transition"]`. BaseDTO 상속으로 `frozen=True, strict=True, extra=forbid` + UTC validator 자동.
  - [x] 1.4 `packages/athena-execution/athena/execution/ledger/schema.py` 작성 — `create_pre_trade_ledger(conn)` + `SCHEMA_SQL` 상수 export.
  - [x] 1.5 `packages/athena-execution/athena/execution/ledger/__init__.py` — `LedgerClient`, `LedgerEntry`, `LedgerEventTypeV1`, `create_pre_trade_ledger` 재노출.
  - [x] 1.6 단위 테스트 `packages/athena-execution/tests/test_ledger_schema.py` — AC-1 "Then" 5 시나리오 (schema create idempotent, column set + user_id default, DROP TABLE view separation, CHECK constraint genesis / non-genesis).
  - [x] 1.7 **Invariant 갱신 (1.4 Source-of-Truth Invariant #7 의 연장)**:
    - `tests/regression/test_trading_pc_write_scope.py` — `FeatureStore.insert_*` 메서드 정확히 6개 (추가: `insert_ledger_entry`) assert. 단, `FeatureStore` 가 실제로 `insert_ledger_entry` 를 추가하지 **않음** — LedgerClient 로 전담 이관. 따라서 invariant test 는 두 방향 중 하나로 update: **(a)** `FeatureStore.insert_*` 는 5개 유지 + `LedgerClient.append` 가 `pre_trade_ledger_raw` 의 유일한 writer 임을 별도 AST 검사로 추가, 또는 **(b)** `FeatureStore` 에 `insert_ledger_entry(entry: LedgerEntry)` 메서드를 `NotImplementedError("use LedgerClient.append directly")` 로 stub 하여 1.4 의 5→6 unification 지킴. **본 스토리는 (a) 를 채택** — FeatureStore 는 market data read + 5 write 유지, LedgerClient 는 독립 진입점. 따라서 `test_trading_pc_write_scope.py` 에 다음 2 assertion 추가:
      - `LedgerClient.append` 메서드 정확히 1개 (ledger 단일 진입점)
      - `INSERT INTO pre_trade_ledger_raw` 문자열이 `packages/athena-execution/athena/execution/ledger/client.py` 외 어디에도 없음 (AST grep + 저장)
    - `tests/regression/test_dto_ddl_parity.py` — 4번째 테이블 (`pre_trade_ledger_raw`) parity 추가. `LedgerEntry` DTO field set vs `PRAGMA table_info('pre_trade_ledger_raw')` — 단 `id`, `created_at_utc` 는 server-side default 이므로 DTO 에서 Optional (`id: int | None = None`, `created_at_utc: datetime | None = None`) 로 매핑 후 parity 비교 포함.
  - [x] 1.8 mypy: schema.py / dto.py / `__init__.py` 가 `mypy --strict` 통과. `duckdb` type stub 없으면 `# type: ignore[import-untyped]` (1.4 Task 1.6 패턴).
  - [x] 1.9 `.pre-commit-config.yaml` mypy hook `additional_dependencies` 에 `athena-execution` 추가 불필요 (workspace local — hook 이 `uv run mypy` 경유하면 자동 해결). 단, boto3 stub 은 Task 5 에서 추가.
  - [x] 1.10 `uv run lint-imports` — `execution ← core`, `execution ← feature_store` Kept. 역방향 import 차단 검증.
  - [x] 1.11 전체 스위트 `uv run pytest -n auto` — baseline 204p + 신규 ~8p. 실패 없으면 진행. (실측: 213p/4s)
  - [ ] 1.12 커밋: `feat(execution): pre_trade_ledger DDL + LedgerEntry DTO + 6th table invariant update (Story 1.5 AC-1)` — signed. (WSL2 위임 — Task 7.6 에서 일괄 또는 사용자 수동)

- [x] **Task 2: `LedgerClient` + SHA-256 해시 체인 (`hash_chain.py`) + Genesis auto-seed + append() 유일 진입점** (AC: 2)
  - [x] 2.1 `packages/athena-execution/athena/execution/ledger/hash_chain.py` 작성 — `canonical_json`, `compute_entry_hash`, `HASH_PLACEHOLDER`.
  - [x] 2.2 `packages/athena-execution/athena/execution/ledger/client.py` 작성 — `LedgerClient(conn, *, user_id, module_version)` + `_ensure_genesis` + `append(event_type, payload, param_hash)`. (spec `"LedgerClient.v1.0.0"` → `"ledger_client.v0.1.0"` 로 정정 — BaseDTO `_MODULE_VERSION_PATTERN` 의 lowercase context 요구 충족. Dev Notes Decisions 에 기록.)
  - [x] 2.3 단위 테스트 `packages/athena-execution/tests/test_ledger_client.py` — AC-2 "Then" 8 시나리오 (+2 bonus: `EMPTY_PARAM_HASH = sha256(b"{}")` 검증 + genesis 부재 시 RuntimeError).
  - [x] 2.4 통합 테스트 `tests/integration/test_ledger_concurrency_smoke.py` (`@pytest.mark.integration`):
    - asyncio 5 task 동시 append → 체인 연속성 검증 (DuckDB connection mutex 증명)
    - 멀티 커넥션 case 는 `@pytest.mark.skip("V1.1+ — multi-writer scope lock")` + deferred-work 기록
  - [x] 2.5 mypy Literal 검증 `tests/regression/test_ledger_event_type_literal.py`:
    - 허용: legal V1.0 event_type (mypy pass)
    - 거부: `"entry_authorized"` (Story 6.1 set — mypy error — Literal mismatch)
    - test 실행: `subprocess.run(["uv", "run", "mypy", "--strict", fixture.py], check=False)` + returncode != 0 + 결과 문자열에 `event_type` 포함 assert.
    - `@pytest.mark.slow` 추가 (`pyproject.toml` 마커 + `test_pytest_markers_registered.py` 갱신).
    - Story 6.1 이 Literal 을 확장 시 본 테스트 fixture 도 함께 수정 — Dev Note 명시.
  - [x] 2.6 전체 스위트 재실행 — 실측: 226p/5s (baseline 213p + 13 신규).
  - [ ] 2.7 커밋: `feat(execution): LedgerClient single entry-point + SHA-256 chain + genesis auto-seed (Story 1.5 AC-2)` — signed. (WSL2 위임 — Task 7.6 에서 일괄)

- [x] **Task 3: `segment_hash.py` + `scripts/monthly_ledger_chain.py` CLI (월말 segment_hash 산출 placeholder)** (AC: 3)
  - [x] 3.1 `packages/athena-execution/athena/execution/ledger/segment_hash.py` 작성 — `compute_segment_hash`, `SegmentHashResult` dataclass. 빈 월 특례 포함.
  - [x] 3.2 `scripts/monthly_ledger_chain.py` 작성 — argparse CLI. atomic write (`tmp + replace`) + `chmod 444`. `--s3-placeholder` 옵션 (S3 실 업로드는 Story 6.2).
  - [x] 3.3 `pyproject.toml` `[tool.ruff.lint.per-file-ignores]` 에 `"scripts/monthly_ledger_chain.py" = ["S404", "S603", "S607"]` 추가 필요 여부 — 본 스크립트는 subprocess 호출 0건이므로 미추가. 1.4 Task 2.3 패턴 재확인.
  - [x] 3.4 단위 테스트 `packages/athena-execution/tests/test_segment_hash.py` — AC-3 "Then" 5 시나리오 (empty month, single entry, determinism, prev chain, policy version 영향).
  - [x] 3.5 통합 테스트 `tests/integration/test_monthly_ledger_chain_cli.py` (`@pytest.mark.integration`) — AC-3 "And" CLI 5 시나리오 + cross-platform read-only dest 재실행 (chmod 644 전처리).
  - [x] 3.6 전체 스위트 재실행. (실측: 236p/8s)
  - [ ] 3.7 커밋: `feat(execution): monthly segment hash computer + CLI placeholder (Story 1.5 AC-3)` — signed. (WSL2 위임)

- [x] **Task 4: `scripts/init_external_backup.sh` (LUKS 초기화 + dry-run 모드) + `infra/systemd/mnt-external.mount` unit 파일** (AC: 4)
  - [x] 4.1 `scripts/init_external_backup.sh` 작성 — AC-4 본문 bash 그대로. `chmod +x` (git tracked).
  - [x] 4.2 `infra/systemd/mnt-external.mount` 작성 — `[Mount]` + `[Install]` 섹션.
  - [x] 4.3 `shellcheck scripts/init_external_backup.sh` 수동 통과 (CI 에 shellcheck 없음 — playbook 에 명시).
  - [x] 4.4 통합 테스트 `tests/integration/test_init_external_backup_dryrun.py` (`@pytest.mark.integration`) — AC-4 "Then" 4 시나리오 (dry-run ≥5 lines · token 확인, DEVICE 부재 fail, mount unit ini 파싱, git mode 100755). Keychain-missing branch 는 DEVICE 설정 후에만 도달 가능 → 코드 리뷰 + Story 1.2 Keychain 테스트로 대체 (docstring 명시).
  - [x] 4.5 OS Keychain 키 이름 등록 — `KeychainKeys` 는 존재하지 않고 `SecretName(StrEnum)` 이 실 레지스트리. `LUKS_PASSPHRASE` 가 이미 등록되어 있어 추가 변경 불필요. 스크립트는 `SecretName.LUKS_PASSPHRASE` 참조.
  - [ ] 4.6 Khuk0 호스트 셋업 (manual, playbook 기록):
    - **외장 SSD 부재 시** (W1 Day 1 likely): 본 단계 skip → Task 7 의 playbook 에 "Story 1.10 prerequisite" 명시. **→ 본 스토리는 DRY_RUN 까지만 커버, 실 초기화는 deferred-work 로 이관.**
    - 외장 SSD 존재 시: passphrase 생성 + keychain 저장 + `DRY_RUN=1` 선험 → 실 실행.
  - [ ] 4.7 커밋: `feat(infra): external SSD LUKS init script + mount unit (dry-run supported) (Story 1.5 AC-4)` — signed. (WSL2 위임)

- [x] **Task 5: `scripts/init_s3_object_lock.py` + `backup.py` (object_key_for_segment SSOT) + MinIO/moto mock integration** (AC: 5)
  - [x] 5.1 `athena-execution` 런타임 의존에 `boto3>=1.34` 추가 + 루트 `[dependency-groups] dev` 에 `botocore-stubs>=1.34`, `moto[s3]>=5` 추가. uv lock 재생성.
  - [x] 5.2 `packages/athena-execution/athena/execution/ledger/backup.py` 작성 — `ObjectLockConfig` frozen dataclass + `object_key_for_segment` SSOT 함수.
  - [x] 5.3 `scripts/init_s3_object_lock.py` 작성 — argparse + `--dry-run` + OS Keychain credential 조회 + boto3 실 경로.
  - [x] 5.4 단위 테스트 `packages/athena-execution/tests/test_backup.py` — AC-5 "Then" 3 시나리오 + defaults 1건 (key format, month padding, frozen dataclass, COMPLIANCE/5y default).
  - [x] 5.5 통합 테스트 `tests/integration/test_init_s3_object_lock_dryrun.py` (`@pytest.mark.integration`) — AC-5 "And" 3 시나리오 완주 (dry-run, retention-years 변환, moto 5.x 로 Object Lock round-trip 성공 — skip 분기 준비되어 있으나 미발동).
  - [x] 5.6 OS Keychain 키 이름 확인 — 실 enum 은 `SecretName(StrEnum)`, `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` / `S3_SSE_C_KEY` 가 Story 1.2 에서 이미 등록됨. 스크립트는 이 이름을 참조. 추가 변경 없음.
  - [ ] 5.7 커밋: `feat(execution): S3 Object Lock Compliance bucket init + 5y retention + key SSOT (Story 1.5 AC-5)` — signed. (WSL2 위임)

- [x] **Task 6: `scripts/verify_ledger.py` CI substrate + `.github/workflows/monthly-ledger-verify.yml` placeholder** (AC: 6)
  - [x] 6.1 `scripts/verify_ledger.py` 작성 — `verify_chain` 함수 + argparse CLI + JSON stdout contract + exit code.
  - [x] 6.2 `.github/workflows/monthly-ledger-verify.yml` 작성 — self-hosted runner + monthly cron (`0 20 1 * *`, 다음날 05:00 KST) + `workflow_dispatch` + DB 부재 시 graceful exit. 실 cron 미세조정은 Story 1.10.
  - [x] 6.3 단위 테스트 `packages/athena-execution/tests/test_verify_chain.py` — AC-6 "Then" 5 시나리오 (clean, tampered payload, broken prev, genesis 특례, segment continuity).
  - [x] 6.4 통합 테스트 `tests/integration/test_verify_ledger_cli.py` (`@pytest.mark.integration`) — AC-6 "And" 4 CLI 시나리오.
  - [x] 6.5 YAML 수동 `yaml.safe_load` 파싱 통과 (name / jobs / schedule / workflow_dispatch 키 확인). actionlint 정식 hook 은 Story 1.9.
  - [ ] 6.6 커밋: `feat(ci): monthly ledger verify substrate + chain integrity checker (Story 1.5 AC-6)` — signed. (WSL2 위임)

- [x] **Task 7: Downstream invariant 갱신 + playbook + directory seeds + deferred-work** (AC: 1-6)
  - [x] 7.1 `docs/operating_playbook.md` 에 `## Story 1.5 — Pre-Trade Ledger 초기 세그먼트 & SHA-256 체인` 섹션 추가 (Story 1.4 섹션 직후), 5 sub-section 모두 완성.
  - [x] 7.2 디렉토리 시드 — 새 파일만 add (기존 디렉토리 재사용). `infra/systemd/mnt-external.mount` 추가 + 기존 `.github/workflows/` `packages/athena-execution/` 는 그대로 재사용.
  - [x] 7.3 `_bmad-output/implementation-artifacts/deferred-work.md` 에 Story 1.5 섹션 추가 (14 개 deferred 항목):
    - **외장 SSD 실제 마운트 + LUKS 실행** — Story 1.10 prerequisite (외장 SSD 하드웨어 + passphrase 입력). 본 스토리는 `DRY_RUN=1` 까지.
    - **S3 (또는 Naver Cloud) bucket 실제 생성 + credential 주입** — Story 1.10 또는 Story 6.2. 본 스토리는 `--dry-run` + moto mock 까지.
    - **monthly-ledger-verify.yml cron 미세조정** — 02:00 KST 실측 runner 가용성 검증 필요, Story 1.10.
    - **Story 1.9 관련**: `infra/prometheus/rules/ledger_integrity.rules.yml` 작성 (architecture.md line 828 에 명시된 파일). 본 스토리는 `verify_ledger.py` 의 exit 1 + stdout JSON 만 emit.
    - **Story 5.6 관련**: Global CB 트리거 hook 실장. 본 스토리의 `"verdict": "CHAIN_BROKEN"` stdout contract 를 CB state machine 이 consume.
    - **Story 6.1 관련**: 실 `LedgerWriter.append(LedgerEntry)` 전체 event_type 집합 + Pydantic Literal 확장. Task 2.5 의 mypy fixture 도 함께 확장 필요.
    - **Story 6.2 관련**: monthly_ledger_chain.py 의 실 S3 업로드 (`boto3.upload_file` + Object Lock retention 설정 per-object).
    - **Story 3.1 관련**: `anti_ego_events` 테이블이 본 스토리의 SHA-256 체인 패턴을 재사용 — `hash_chain.py` 의 `compute_entry_hash` 를 `anti_ego_events` 에도 사용 (패키지 경계: `alpha_defense/f5/hash_chain.py` 은 별도 파일로 두되 본 스토리의 `hash_chain.py` 를 import 재사용 하거나 동일 로직을 `athena-core` 로 승격 — 결정은 Story 3.1 시점).
    - **DuckDB row-level trigger 부재의 후속 대응**: Story 1.9 의 `ledger-direct-write` ruff custom rule 로 application-layer 차단을 영구화. 본 스토리는 test_trading_pc_write_scope.py 확장으로 대체.
    - **concurrent multi-connection append** — V1.1+ scope (V1.0 은 단일 asyncio 프로세스).
    - **LUKS mount systemd unit 실 enable** — 본 스토리는 파일 작성만. `sudo systemctl enable --now mnt-external.mount` 는 Story 1.10.
    - **retention_days 윤년 오차** — 5×365=1825 vs 실제 5년 = 1826 또는 1827일. V1.0 허용, Story 6.2 에서 정확화 검토.
  - [x] 7.4 5-gate 재실행 (1.4 Task 7.4 패턴):
    1. `uv sync --frozen --group dev` — 80 packages 체크, 신규 설치 없음 (이미 sync 됨).
    2. `uv run pytest -n auto` — **실측 256 passed, 5 skipped in 8.13s**. 신규 +43: AC-1 ledger schema 5 + 1.4 invariants 확장 2 (ledger append 1 / ledger writes only in client 1 / ledger_client contains INSERT 1 / parity 1) = +5, AC-2 client 10 + concurrency smoke 1 + mypy literal 2 + markers 0 = +13, AC-3 segment_hash 5 + CLI 5 = +10, AC-4 dry-run integration 4 = +4, AC-5 backup unit 4 + init_s3 integration 3 = +7, AC-6 verify_chain unit 5 + CLI integration 4 = +9, minus double counts = **+43 net**.
    3. `uv run pre-commit run --all-files` — 첫 실행에서 ruff format 2 파일 자동 정리 후 재실행 전 hook green.
    4. `uv run lint-imports` — 5 contracts all Kept (`execution ← core`, `execution ← feature_store`).
    5. `uv build --package athena-execution --wheel --out-dir /tmp/athena-1-5-check` — wheel 성공 + `schema.sql` force-include 로 ledger/ 8개 파일 모두 포함 (확인: `schema.sql`, `__init__.py`, `backup.py`, `client.py`, `dto.py`, `hash_chain.py`, `schema.py`, `segment_hash.py`).
  - [x] 7.5 sprint-status.yaml `1-5-*` → `review` + `last_updated=2026-04-23` 갱신 완료.
  - [ ] 7.6 핸드오프 commit: `chore(story-1.5): Pre-Trade Ledger SHA-256 chain substrate verified, hand off to Story 1.6` — signed. PR / squash merge 는 Khuk0 가 review 단계에서 WSL2 측에서 수행.

### Review Findings (2026-04-23, bmad-code-review · 3-layer adversarial)

3 병렬 레이어 실행 결과: Blind Hunter + Edge Case Hunter + Acceptance Auditor. Acceptance Auditor 은 6 AC · 11 Invariant · 7 Threat Model · File List 모두 conformance PASS. 아래는 Blind Hunter + Edge Case Hunter 가 중복 제거 후 남긴 32 finding 의 triage 결과.

**Decision-needed (1) — Resolved 2026-04-23 via 옵션 C (혼합)**:

- [x] [Review][Decision] **D1 — Monthly workflow 의 continuity/provision 검증 갭** — 옵션 C 채택: (a) `LEDGER_PROVISIONED=1` env flag gate 는 본 스토리에서 즉시 patch (P17 로 승격) — provision 이후 silent pass 전환을 차단. (b) continuity wiring (`--prev-segment-json` + `--year` + `--month` 호출) 은 Story 1.10 의 실 `LEDGER_DB_PATH` + `monthly_ledger_chain.py` 산출물 경로 wiring 과 함께 처리 — deferred-work.md W5 로 등록. 근거: provision flag 는 단순 bash gate 로 본 스토리에서 low-risk patch, continuity wiring 은 실 경로가 Trading PC 에서 확정되어야 정확히 계산되므로 1.10 의 backup automation 과 묶는 것이 설계상 자연스러움.

**Patch (17)** — 모호하지 않은 수정:

- [x] [Review][Patch] **P1 [CRITICAL] TIMESTAMPTZ vs naive `make_timestamp` 월 경계** [`packages/athena-execution/athena/execution/ledger/segment_hash.py:65-71`] — `created_at_utc` 는 `TIMESTAMPTZ` 이나 `make_timestamp(?, ?, 1, 0, 0, 0.0)` 는 naive `TIMESTAMP` 반환. DuckDB 는 naive literal 을 **세션 TZ** 로 interpret → Trading PC WSL2 가 KST 면 월 경계가 UTC 기준에서 9시간 밀림 → CI (UTC) 와 Trading PC (KST) 에서 동일 row 가 다른 월로 분기 → segment_hash 재현성 silent break. 수정: `make_timestamptz(?, ?, 1, 0, 0, 0.0, 'UTC')` 로 교체 또는 `TIMESTAMPTZ` 리터럴 + UTC offset.
- [x] [Review][Patch] **P2 [MAJOR] Empty Keychain passphrase 통과** [`scripts/init_external_backup.sh:38-50`] — Keychain probe 가 예외만 catch, `get_secret()` 이 빈 문자열 반환 시 probe pass → `cryptsetup luksFormat` 에 empty passphrase 파이프 → zero-passphrase LUKS 볼륨 생성. 수정: probe 에 `if not get_secret(...): sys.exit(1)` + 최소 길이 (예: 16) assert 추가.
- [x] [Review][Patch] **P3 [MAJOR] Object Lock `retention_years=0` silent bypass** [`scripts/init_s3_object_lock.py:29`] — `--retention-years 0` → `Days=0` → AWS 는 수락하고 retention 없음 == 즉시 삭제 가능. NFR-A2 "영구 보존" 우회. 수정: `type=lambda x: int(x) if int(x) >= 1 else argparse.error(...)` 또는 `choices=range(1, 100)`.
- [x] [Review][Patch] **P4 [MAJOR] `eval "$@"` + env-controlled DEVICE hardening** [`scripts/init_external_backup.sh:14, 33`] — `run()` 은 `eval "$@"`, `$DEVICE`/`$MOUNT_POINT`/`$LUKS_NAME` 는 환경변수 source. `DEVICE='/dev/sdb1; rm -rf ~'` 같은 hostile 값이 sudo 하에서 arbitrary exec. Khuk0 본인 운영 local script + sudo 권한 필요 맥락이라 threat 은 낮으나 hardening 가치 있음. 수정: DEVICE 는 `^/dev/[a-zA-Z0-9/_-]+$` regex match, MOUNT_POINT 는 `^/mnt/[a-zA-Z0-9/_-]+$` 로 fail-fast.
- [x] [Review][Patch] **P5 [MINOR] `verify_ledger.py` year/month argparse validator 누락** [`scripts/verify_ledger.py:88-89`] — `--month 0` / `--month 13` / `--year -1` 등이 argparse 에서 통과 → `compute_segment_hash` 안쪽 `make_timestamp` 에서 crash → `except Exception` 이 opaque `VERIFY_FAILED` 로 변환 → 사용자가 입력 오류 인지 어려움. 수정: `choices=range(1, 13)` on --month + `--year` 범위 validator (e.g. 2020-2100).
- [x] [Review][Patch] **P6 [MINOR] `args.month` truthy check 으로 연속성 silent skip** [`scripts/verify_ledger.py:106`] — `if args.prev_segment_json and args.year and args.month:` 에서 `args.month == 0` 이 falsy → 연속성 block 이 조용히 skip. 수정: 모두 `is not None` 비교.
- [x] [Review][Patch] **P7 [MINOR] `last_this` 무조건 업데이트 → avalanche mismatch** [`scripts/verify_ledger.py:75`] — `this_hash_mismatch` 감지 후에도 `last_this = this` 로 stored (tampered) 값이 다음 row 의 `expected_prev` 가 됨 → 변조 1건이 downstream 전부를 mismatch 로 만들어 audit 분류 혼란. 수정: mismatch 발견 시 `last_this = expected_this` (재계산값) 로 chain 계속.
- [x] [Review][Patch] **P8 [MINOR] `_atomic_write_readonly` fsync 누락 + .tmp leak** [`scripts/monthly_ledger_chain.py:29-43`] — (a) `tmp.write_text` 후 `os.replace` 전 crash 시 `.tmp` 파일 orphan + 이전 chmod 0o644 상태 유지 → 다음 run 이 0o644 파일 위에 쓰기 window 존재. (b) `os.fsync` 및 parent dir fsync 없음 → 전원 장애 시 rename 반영 누락 가능. 수정: `try/finally` 로 `.tmp` unlink + `os.fsync(tmp.fileno())` + `os.fsync(target.parent.fileno())` (Linux only — Windows 는 skip).
- [x] [Review][Patch] **P9 [MINOR] `--prev-segment-json` 스키마 validation 누락** [`scripts/verify_ledger.py:107`] — JSON 파일에 `segment_hash` 또는 `month` 키 부재 시 `KeyError` → `VERIFY_FAILED` opaque. 수정: `required_keys = {"segment_hash", "month"}` assert + 64-char hex regex on `segment_hash`.
- [x] [Review][Patch] **P10 [NIT] `hash_chain.py` docstring — U+0000 은 valid UTF-8 1-byte** [`packages/athena-execution/athena/execution/ledger/hash_chain.py:15-16, 60-61`] — 주석 "The null byte never appears in valid UTF-8 strings" 는 기술적으로 부정확 (U+0000 은 UTF-8 `\x00` 1-byte). 현실적 안전성은 `canonical_json` 이 `json.dumps` 를 사용해 U+0000 → `" "` 6-char escape 로 serialize 하고 다른 입력 (event_type Literal, 40-hex policy sha, int user_id) 에 NUL 이 없어서 유지됨. 주석을 정확히: "payload_json 은 canonical_json 을 통과해 U+0000 이 `\\u0000` escape 되고, 다른 필드는 [a-z0-9.]+ 제한이라 raw NUL 진입점이 없음."
- [x] [Review][Patch] **P11 [NIT] `segment_hash.py` docstring "sorted()" vs SQL ORDER BY** [`packages/athena-execution/athena/execution/ledger/segment_hash.py:52-55`] — docstring 은 `sorted(ids)` 라 하나 코드는 SQL `ORDER BY id` 에 의존. 결과 동일하나 docstring 정확화 또는 `ids = sorted(ids)` 명시 추가.
- [x] [Review][Patch] **P12 [NIT] dead `or` branch in regression** [`tests/regression/test_ledger_event_type_literal.py`] — `"entry_authorized" in combined or "event_type" in combined` 뒤에 바로 `"event_type" in combined` 가 오므로 `or` 좌항 의미 없음. `"event_type" in combined` 단독으로 정리.
- [x] [Review][Patch] **P13 [NIT] `test_ledger_schema.py` raw SQL fixture module_version case** [`packages/athena-execution/tests/test_ledger_schema.py`] — `"LedgerClient.v1.0.0"` (PascalCase) 가 raw SQL INSERT 에 하드코딩. 실 persisted 값은 `"ledger_client.v0.1.0"` (snake_case). DTO 우회이므로 기능 영향 없으나 future reader 가 snake_case 기대 위반 위험. 전체 snake_case 로 통일.
- [x] [Review][Patch] **P14 [NIT] mnt-external.mount ordering** [`infra/systemd/mnt-external.mount:3-4`] — `After=dev-mapper-athena_external.device` 만 있고 `After=cryptsetup.target` 없음. systemd 는 device unit 의존성으로 retry 하지만 boot race 경고 저감 위해 `After=cryptsetup.target` 추가 권장.
- [x] [Review][Patch] **P15 [NIT] `us-east-1` LocationConstraint 예외** [`scripts/init_s3_object_lock.py:75-79`] — 실 AWS `us-east-1` 은 `LocationConstraint=us-east-1` 을 reject. 기본 region 이 `ap-northeast-2` 이므로 발생 드물지만 runner/tester 가 us-east-1 을 설정할 경우 confusing 400. `if region == "us-east-1"` 시 `CreateBucketConfiguration` 생략.
- [x] [Review][Patch] **P16 [NIT] `sudo` NOPASSWD 요구사항 playbook 기록** [`scripts/init_external_backup.sh:53, 56` + `docs/operating_playbook.md`] — `python3 -c "...passphrase..." | sudo cryptsetup ... -` 파이프는 sudo 가 password 프롬프트 시 passphrase 를 소모 → deadlock. `NOPASSWD` sudoers rule 이 필수. operating_playbook 의 Story 1.5 LUKS sub-section 에 "host setup prerequisite: cryptsetup 전용 NOPASSWD sudoers rule" 한 줄 추가.
- [x] [Review][Patch] **P17 [MAJOR] `LEDGER_PROVISIONED` env gate 로 silent-pass 차단** [`.github/workflows/monthly-ledger-verify.yml:22-29`] — D1 옵션 C 결과. 현재 `if [[ ! -f "$DB_PATH" ]]; then exit 0` 은 Week 1-2 미provision 기간에는 정당하지만 provision 이후 우발적 DB 삭제/이동이 silent pass 로 변질될 위험. 수정: `LEDGER_PROVISIONED` env (repo secret 또는 Story 1.10 provisioner 가 setup 하는 runner env) 를 gate 로 사용 — unset 이면 "pre-provision, skip OK" (exit 0), `=1` 이면 DB missing → exit 1 + 명확한 ERROR 메시지. 환경변수 전환 시점이 provision event 로 기능.

**Defer (5)** — 이미 deferred 또는 scope 경계에 부합, deferred-work.md 에 동기:

- [x] [Review][Defer] **W1 Chain tip `SELECT … ORDER BY id DESC LIMIT 1`** [`packages/athena-execution/athena/execution/ledger/client.py:113-114`] — gap/replay ID 발생 시 잘못된 chain tip 선택 위험. V1.0 single-writer asyncio scope 에서는 문제없고 이미 deferred-work.md §11 ("multi-connection concurrent append — V1.1+") 로 scope 명시됨. V1.1+ 에서 chain tip 을 `prev_hash IS NULL` genesis 로부터 재구성하거나 `parent_id` 컬럼 도입 고려.
- [x] [Review][Defer] **W2 DELETE 후 genesis 재시드 불가능** [`schema.sql:30` + `client.py:67-99`] — CHECK `(id = 1 AND prev_hash IS NULL)` + `nextval()` sequence 누적 진행 → `DELETE FROM pre_trade_ledger_raw` 후 새 LedgerClient 생성 시 id=2+ 로 genesis 시도 → CHECK 위반. AR-DATA4 "새 스키마 = 새 DuckDB 파일 + 새 세그먼트" 가 명시적 design 이라 같은 파일 재사용은 scope 밖. 그러나 운영 중 우발적 wipe 복구 시나리오가 threat model §#2 ("DB 파일 삭제 후 새로 생성") 와 부합 — deferred-work 에 "DELETE 후 복구 절차는 Story 6.2 가 `ALTER SEQUENCE RESTART` + 외장 SSD segment_hash 복원 procedure 로 다룬다" 명시적 등록.
- [x] [Review][Defer] **W3 `_ensure_genesis` 명시적 transaction 누락** [`packages/athena-execution/athena/execution/ledger/client.py:67-99`] — DuckDB 는 single-statement autocommit 이라 `INSERT genesis` 단독은 atomic. 그러나 WAL checkpoint + crash 조합에서 sequence 가 advance 되고 genesis row 가 rollback 되는 corner case 이론적 가능. V1.0 low-probability 이나 V1.1+ 에서 `BEGIN ... COMMIT` 명시화 + sequence 복구 procedure 필요. Story 6.2 3-way verify 설계 시점에 재검토.
- [x] [Review][Defer] **W4 Object Lock `retention_years × 365` 윤년 오차** [`scripts/init_s3_object_lock.py:89, backup.py`] — 이미 deferred-work.md §14 (retention_days 윤년 오차) 에 등록됨. Story 6.2 retention 정확화 범위.
- [x] [Review][Defer] **W5 monthly-ledger-verify.yml continuity wiring** [`.github/workflows/monthly-ledger-verify.yml:28`] — D1 옵션 C 결과. 실 `LEDGER_DB_PATH` + `monthly_ledger_chain.py` 월간 산출물 경로가 Trading PC 에서 확정되어야 `--prev-segment-json` 을 정확히 전달 가능. Story 1.10 의 real cron tuning + `LEDGER_DB_PATH` env wiring 과 함께 처리. 본 스토리는 per-row this_hash 재계산만 CI 로 실행 (substrate).

**Dismissed (11)** — 허위경보/의도적/spec sanctioned:
- Hash `\x00` collision via payload_json raw NUL (canonical JSON 이 U+0000 escape 처리, collision 현실 경로 없음 — P10 docstring 정정으로 해소)
- `compute_segment_hash` implicit ORDER BY 의존 (P11 docstring fix 로 처리, 기능 OK)
- cron `0 20 1 * *` vs narrative "03:00 KST intent" drift (workflow comment 에 "가용성 우선 05:00 KST 지연 허용" 이미 명시)
- `create_pre_trade_ledger` 매 `LedgerClient()` 호출 (single-process scope, idempotent 안전)
- `computed_at_utc` ISO format `+00:00` vs `Z` (둘 다 valid ISO 8601)
- `BucketAlreadyOwnedByYou` 이후 retention 재검증 없음 (`put_object_lock_configuration` 이 바로 override 수행)
- `backup.py` year/month/user_id validation 누락 (pure SSOT function, CLI argparse 가 upstream validate)
- `init_s3_object_lock.py:60` bare `except Exception` (`# noqa: BLE001 — exit-code boundary` 의도적)
- `verify_ledger.py:121` bare `except Exception` (exit-code contract 의도, 동일 noqa 주석)
- `print(body)` systemd journal 유출 (segment_hash 는 hash 자체, workflow comment "no ledger content leaves" 와 약한 충돌이나 CI substrate intent 범위)
- `schema.sql` module_version pattern CHECK 부재 (DTO + LedgerClient 내부 controlled constant 로 enforce, raw SQL 경로 차단 이미 AST 검사)

### Review Summary

- Acceptance Auditor: **PASS** (6/6 AC · 11/11 Invariant · 7/7 Threat Model · File List 정합 · Sanctioned Divergence integrity 유지).
- Triage: 1 decision (resolved 옵션 C) · 17 patch (1 CRITICAL / 4 MAJOR / 5 MINOR / 7 NIT) · 5 defer · 11 dismiss.
- **Status 2026-04-23 진행 상황**: D1 resolve + 17 patch 모두 적용 완료. 5-gate post-patch 전수 green:
  1. `uv sync --frozen --group dev` — pass (venv 재빌드 후 264 packages sync).
  2. `uv run pytest -n auto` — **260 passed, 5 skipped in 11.26s** (baseline 256p + P3 regression 2 + P5/P9 regression 2 = +4, 모두 green).
  3. `uv run pre-commit run --all-files` — 10 hooks pass (ruff · ruff-format · mypy · secret scan · yaml · toml · merge-conflict · EOL · trailing whitespace).
  4. `uv run lint-imports` — 5 contracts Kept.
  5. `uv build --package athena-execution --wheel` — schema.sql 포함 ledger/ 8개 파일 wheel 에 present.
- Status: **review** (유지) — review-flip 재진입 준비 완료. WSL2 위임 커밋 1건 추가: `fix(story-1.5): apply 17 review patches (Story 1.5 review flip prep)`.

## Dev Notes

### Source-of-Truth Invariants (Story 1.5 가 Down-stream 전역에 고정하는 불변식)

1. **`pre_trade_ledger` 는 `decisions.duckdb` 의 6번째 테이블 — 1.4 의 5 테이블 (`modules_output`, `decisions`, `orders`, `anti_ego_events`, `labels_f1`) 에 추가** [Task 1.7, Story 1.4 Invariant #7]
   이는 1.4 의 "Trading PC 가 쓰는 `decisions.duckdb` 의 테이블 scope" 를 확장한다. `test_trading_pc_write_scope.py` 는 이제 `FeatureStore.insert_*` 5개 + `LedgerClient.append` 1개를 두 방향으로 검증. 후속 Story (3.1 anti_ego_events, 3.3 labels_f1, 4.3 orders) 가 `FeatureStore.insert_*` 를 구현할 때 본 invariant 는 그대로 유지 — `LedgerClient` 는 ledger 만 담당, FeatureStore 는 나머지 5 테이블 담당.

2. **`LedgerClient.append(entry)` 는 pre_trade_ledger 의 유일한 Python 진입점** [Task 2.2, architecture.md line 572-575]
   `conn.execute("INSERT INTO pre_trade_ledger_raw ...")` 직접 호출 영구 금지. `packages/athena-execution/athena/execution/ledger/client.py` 외 어디에도 `INSERT INTO pre_trade_ledger_raw` 문자열이 등장하지 않음 — `test_trading_pc_write_scope.py` 가 AST 레벨로 enforce. Story 1.9 의 ruff custom rule 로 승격 예정.

3. **SHA-256 해시 체인의 canonical form 은 `hash_chain.py` 가 SSOT** [Task 2.1]
   Entry hash input: `prev_hash || payload_json || policy_version_git_sha || event_type || user_id` (separator `\x00`). Segment hash input: `prev_segment_hash || sorted_ids_hash || policy_version_git_sha` (separator `\x00`). 본 함수는 Story 3.1 의 anti_ego_events 체인, Story 6.1 의 full LedgerWriter, Story 6.2 의 verify job 이 모두 재사용 — 복사-붙여넣기 금지, import 경유 필수. (Story 3.1 이 package 경계 이유로 동일 로직을 `athena-core` 로 승격할 수도 있음 — 그 경우 3.1 이 marshal 책임.)

4. **Canonical JSON: `json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)`** [Task 2.1]
   해시 재현성의 핵심. dict 키 순서, whitespace, float 직렬화가 직렬화 시점 의존이면 해시가 평문·디스크 재현 시 불일치. 본 포맷은 RFC 7159 canonical JSON 과 유사 (완전 동일은 아님 — Decimal 직렬화 시 `default=str` 경유). 후속 Story (3.1, 6.1) 가 다른 payload 형식 쓰려 할 때 **반드시 이 함수 경유**.

5. **Genesis entry auto-seed + schema_segment_transition 이 V1.0 LedgerClient 가 쓰는 유일한 event_type** [Task 2.2, AC-2]
   V1.0 `LedgerEventTypeV1 = Literal["genesis", "schema_segment_transition"]`. 본 스토리는 실 decision/order 를 append 하지 않음 — substrate 만. Story 6.1 이 full Literal (entry_authorized, entry_rejected_*, order_placed, order_filled, exit_*, compliance_*) 확장 시 mypy test (Task 2.5) fixture 도 함께 확장.

6. **segment_hash 는 "빈 월" 도 포함해 연속 — entry 0 건이어도 체인 유지** [Task 3.1]
   장 마감 주간 또는 시스템 downtime 월도 `segment_hash = SHA256(prev_segment_hash || SHA256("") || policy_version_git_sha)` 로 계산. 후속 월의 prev 가 빈 월을 건너뛰지 않음 → chain of custody 의 법률 수준 무결성. Story 6.2 verify job 이 "월 건너뛰기 = 조작 의심" 으로 탐지.

7. **2개 시각 컬럼 (`timestamp` vs `created_at_utc`) 은 의도적 중복** [Task 1.2]
   `timestamp` (BaseDTO 상속) = application-asserted 이벤트 발생 시각. `created_at_utc` = DB 삽입 시각 (server-side default `now()`). 두 시각의 delta 가 clock skew 또는 backfill 신호. Story 6.2 verify job 이 `|created_at_utc - timestamp| > 1h` 을 anomaly 로 reporting. 중복 비용 (~16 bytes/row) 은 법률 감사 가치에 비해 무시 가능.

8. **객체 키 네이밍: `ledger/user_id=<N>/year=YYYY/month=MM/segment_hash.json`** [Task 3.1 + Task 5.2, epics.md line 585]
   `object_key_for_segment` SSOT 함수 경유. Story 6.2 도 동일 함수 사용. Parquet hive partition (year=YYYY/month=MM) 과 의도적 일치 — S3 Select / Athena prefix 쿼리 도구 재사용.

9. **외장 SSD + S3 2-target 의 동기화 규칙 = "외장 SSD 먼저 atomic write + chmod 444, S3 업로드는 best-effort"** [Task 3.2]
   외장 SSD 는 `tmp + replace + chmod 444` 로 local atomic. S3 는 네트워크 실패 가능 → best-effort. 불일치 시 외장 SSD 가 truth, S3 는 재업로드. 이 규칙은 verify job 이 "외장 SSD ↔ S3 3-way 비교" (Story 6.2) 할 때의 진본 기준. Story 1.5 substrate 는 3-way 는 미구현 — Story 6.2.

10. **모든 `decisions.duckdb` 의 6 테이블은 `(timestamp, module_version, policy_version_git_sha, user_id)` 4-필드 prefix 유지** [Story 1.4 Invariant #7 의 직접 상속, AC-1]
    pre_trade_ledger 가 본 invariant 의 6번째 테이블. 차이: `id` (PK) + `event_type` + `payload_json` + `prev_hash` + `this_hash` + `param_hash` + `created_at_utc` 추가. 후속 Story (3.1) 의 anti_ego_events 테이블도 본 prefix 유지.

11. **DuckDB 1.x 는 row-level trigger 부재 — application-layer + AST invariant 로 대체** [Task 1.7, Task 1.2 "Dev Note"]
    epics.md line 565 의 "UPDATE/DELETE 물리 차단 (DuckDB view + trigger pattern)" 은 DuckDB 1.x 현실에서는 **view 계층 separation + LedgerClient 유일 진입점 + `test_trading_pc_write_scope.py` AST 검사 + (Story 1.9) ruff custom rule** 의 4층 방어로 재해석. 본 invariant 는 NFR-S3 "자기 override 로 수정 불가능한 tamper-evident" 의 application-layer 등가체. DB 레벨 차단이 아니라는 사실은 threat model (§Threat Model Notes) 에 명시.

### Scope Boundaries — 명시적으로 OUT of Story 1.5

| Out-of-scope 항목 | 귀속 스토리 | 이유 |
|---|---|---|
| Full LedgerWriter (event_type 전체 집합, 모든 decision/order lifecycle 이벤트 append) | Story 6.1 | 본 스토리는 substrate + genesis + schema_segment_transition 2 event_type 만 |
| 실 decision append (entry_authorized, entry_rejected_*) | Story 3.7 (이중 조건 entry gate) 가 호출, Story 6.1 이 구현 | 본 스토리는 LedgerClient 추상 진입점 + Literal 제약 enforcement |
| 실 order append (order_placed, order_filled) | Story 4.3 가 호출, Story 6.1 이 구현 | 동일 — substrate 만 |
| 실 exit event append (exit_oco_stop, exit_kill_switch_*) | Story 4.7 | 동일 |
| 실 compliance event append (compliance_email_sent 등) | Story 6.6/6.7 | 동일 |
| anti_ego_events 테이블 + 체인 | Story 3.1 | 본 스토리는 체인 로직 SSOT 를 제공 (재사용 대상) |
| 외장 SSD 실 LUKS 초기화 + 실 디스크 조작 | Story 1.10 (backup automation) + 운영자 수동 | 본 스토리는 `DRY_RUN=1` 모드 + systemd mount unit 작성까지 |
| S3 bucket 실 생성 + 실 credential 주입 | Story 1.10 (backup automation) 또는 Story 6.2 | 본 스토리는 `--dry-run` + moto mock 까지 |
| monthly_ledger_chain.py systemd timer 실 enable | Story 1.10 | 본 스토리는 script + YAML workflow 파일 작성까지 |
| verify_ledger.py 의 Prometheus rule 작성 (`ledger_integrity.rules.yml`) | Story 1.9 (observability) | architecture.md line 828 에 명시된 rule 파일 — 본 스토리는 verify script 의 exit code + stdout JSON contract 만 |
| Global CB (Epic 5) 로의 체인 불일치 트리거 | Story 5.6 | 본 스토리의 `"verdict": "CHAIN_BROKEN"` stdout 이 CB 의 consume contract |
| DuckDB row-level trigger 로 UPDATE/DELETE 물리 차단 | **영구 불가** (DuckDB 1.x 제약) | application-layer 4층 방어로 대체 (§Invariant #11) |
| `athena_ledger_chain_valid` Prometheus gauge | Story 1.9 | architecture.md line 430 에 네이밍 명시, rule 정의는 1.9 |
| 3-way 검증 (외장 SSD ↔ S3 ↔ 재계산 일치) | Story 6.2 | 본 스토리는 1-way 재계산 (DB 만) |
| Naver Cloud Object Storage API 호환 실 테스트 | Story 1.10 | 본 스토리는 S3 API 호환 `--endpoint-url` 옵션으로 path 만 열어둠 |
| LUKS passphrase rotation 정책 | Story 1.10 또는 별도 ops 스토리 | 본 스토리는 OS Keychain 저장만 |
| multi-connection / multi-process concurrent append | V1.1+ | V1.0 단일 asyncio 프로세스 가정 |

유혹이 들면 **멈추고 핸드오프**. substrate 스토리의 의의는 "후속 스토리가 합의된 형태 위에서 작업" 이지 "본 스토리에서 모든 것 구현" 이 아님. 특히 본 스토리는 **법률 수준 기록 체인의 뼈대** 역할 — Week 2 첫 decision 이 발생하기 전까지 완료돼야 함.

### Architecture Patterns & Constraints (이 스토리의 payload)

- **Ledger write 규칙** [architecture.md lines 571-575, Enforcement #5]: `LedgerClient.append(record)` 단일 진입점. 직접 `conn.execute("INSERT INTO pre_trade_ledger_raw ...")` 영구 금지. ruff custom rule (Story 1.9) + `test_trading_pc_write_scope.py` (본 스토리) 2층.
- **동기 append** [architecture.md line 575]: chain consistency 보장을 위해 `def append` (sync). async wrapper 금지. 단일 asyncio 프로세스 가정 시 cooperative scheduling 이 race 차단.
- **Canonical JSON + SHA-256 input 순서** [§Source-of-Truth Invariant #3, #4]: hash 재현성의 핵심. 평문만 보고도 해시 재계산 가능해야 법률 감사 도구 (외부) 가 같은 결과 도출.
- **2-target backup 분리 정책** [architecture.md#D6 lines 289-291, AR-DATA6]: 외장 SSD LUKS (실시간 mirror, truth) + S3 Object Lock Compliance (월간 체인 해시 + 5년 retention, backup). 두 개 모두 파괴되지 않는 한 복원 가능.
- **Object Lock Compliance vs Governance**: Compliance = **root 계정도 삭제 불가**. Governance = bypass 권한 있는 계정 가능. V1.0 은 Compliance 고정 (NFR-A2 "영구 보존").
- **SHA-256 입력 separator `\x00`** [hash_chain.py, segment_hash.py]: UTF-8 문자열에 나타나지 않으므로 ambiguity-free. 대안 (공백, `|`, `;`) 은 payload_json 에 등장 가능 → 충돌 위험.
- **Server-side timestamp vs client-side timestamp** [§Source-of-Truth Invariant #7]: `created_at_utc` (DB `now()`) + `timestamp` (Python `datetime.now(UTC)`) 동시 기록. 두 값의 delta 가 clock skew / backfill 신호.
- **Policy version embedding** [prd.md FR38, hash input 포함]: `policy_version_git_sha` 가 hash input 의 일부 → 정책 변경이 chain 에 자동 기록. policy 변경 즉시 `schema_segment_transition` event 를 append 하면 "이 entry 이후 정책 X" 가 추적 가능 (Story 6.1/6.8 activation).
- **Idempotent DDL** [Task 1.4]: `CREATE TABLE IF NOT EXISTS`, `CREATE OR REPLACE VIEW`, `CREATE SEQUENCE IF NOT EXISTS`. `LedgerClient.__init__` 이 매번 DDL 호출 해도 안전.
- **`LedgerEntry` BaseDTO 상속 + Literal event_type** [Task 1.3]: Pydantic 2 strict mode + frozen + Literal 타입 체킹 3층. mypy + Pydantic runtime 2층에서 잘못된 event_type 진입 차단.

### Threat Model Notes (본 스토리의 방어 범위 명시)

adversarial bypass 시나리오 (본 스토리 scope 내):

1. **본인이 과거 decision 을 soft-delete 하려 시도** (거래 실패를 감추고 싶은 충동). 방어: `UPDATE pre_trade_ledger_raw SET ...` 또는 `DELETE FROM pre_trade_ledger_raw WHERE id=N` 은 DuckDB 레벨은 허용 (§Invariant #11). 따라서 3층 방어:
   - **Application-layer**: `LedgerClient.append` 만 진입점, `update`/`delete` 메서드 부재.
   - **AST invariant**: `test_trading_pc_write_scope.py` 가 `UPDATE pre_trade_ledger_raw` / `DELETE FROM pre_trade_ledger_raw` 문자열 전체 repo 금지.
   - **Chain integrity**: verify_ledger.py 가 전체 chain 재계산 → 수정 흔적 즉시 발견. 수정 후 모든 downstream entry 의 this_hash 도 재계산 필요 — 인간이 수동으로 하기에는 실용적 불가능 (N 개 entry 대해 `prev_hash`, `this_hash` 모두 재작성).
   - **월간 segment_hash 외장 백업**: Story 6.2 가 구현하면 과거 월 segment_hash 는 외장 SSD + S3 에 chmod 444 + Object Lock Compliance 로 저장. 과거 chain 변조 시 segment_hash 불일치 발견.

2. **Trading PC 의 `decisions.duckdb` 파일 직접 삭제 후 새로 생성**. 방어: genesis entry 의 `policy_version_git_sha` + `timestamp` 가 git history / Prometheus retention / 외부 백업의 어디와도 불일치. Story 6.2 의 verify job 이 genesis 가 "너무 최근" 이면 경보.

3. **외장 SSD 의 LUKS 키 탈취 → 외장 SSD 내 segment_hash.json 변조**. 방어:
   - LUKS 키는 OS Keychain (NFR-S1) — OS 권한 + TPM (Windows Credential Manager) / libsecret 수준 방어.
   - Compliance-level S3 Object Lock 이 2차 복원 경로 (최소 5년 WORM).
   - segment_hash.json 은 chmod 444 — 외장 SSD 마운트 상태에서도 write 권한 필요.

4. **S3 credential 탈취 → S3 bucket 의 segment_hash 변조 시도**. 방어: Object Lock Compliance 모드는 **root 계정도 삭제/수정 불가** (retention 기간 동안). 따라서 credential 탈취로도 과거 segment_hash 조작 불가.

5. **시간 조작** (`GIT_COMMITTER_DATE=@0` 또는 시스템 clock). 방어: `created_at_utc` (DB `now()`) vs `timestamp` (Python `datetime.now(UTC)`) 2원 비교 + Story 1.3 의 `check_cooling.py` 음수 delta issue (Story 1.3 deferred-work #44) 와 관련. 본 스토리는 timestamp 2원 기록까지만 — 검증은 Story 6.2.

6. **process 중단 → genesis 삽입 중간에 crash**. 방어: `_ensure_genesis` 가 매 LedgerClient 생성 시 idempotent. crash 시 id=1 이 partial 이면 DuckDB 트랜잭션 롤백 (DuckDB 는 기본 auto-commit 이지만 단일 INSERT 는 atomic). 실제로 partial-insert 상태 발생 시 next init 이 "id=1 없음" 으로 재삽입.

7. **multi-writer race** (V1.0 scope 밖 but 명시 필요). V1.0 은 단일 asyncio 프로세스. V1.1+ 에서 multi-process 시 Advisory lock (PostgreSQL-style) 또는 application-level semaphore 필요 — deferred.

각 deeper bypass 는 후속 스토리 (Story 6.1 full writer, Story 6.2 3-way verify, Story 6.8 외부 승인권자 서명) 가 cover. 본 스토리는 "기본 운영 상태에서 Ledger 의 tamper-evidence substrate" 까지 책임.

### Testing Standards

- **Framework**: pytest + pytest-asyncio (`asyncio_mode=strict` — 1.4 Task 6.2 에서 확정). 본 스토리는 async 테스트 1건 (Task 2.4 concurrency smoke) — 명시적 `@pytest.mark.asyncio` 필요.
- **Determinism** [AR-TEST2]: SHA-256 은 결정론적이지만 `datetime.now(UTC)` 는 테스트 간 변동 — `timestamp` 필드 값은 smoke 기반 (범위 assertion `± 2초`), `this_hash` 는 payload 가 고정이면 재현 가능. 테스트는 "timestamp 는 제외하고 hash 검증" 패턴.
- **Marker 사용**:
  - 순수 단위 (DuckDB :memory:) → no marker, stage-2 — schemas / DTO / hash_chain / segment_hash / verify_chain / backup.
  - DuckDB 파일 IO + subprocess CLI + moto mock → `@pytest.mark.integration`, stage-3 — monthly_ledger_chain CLI / init_external_backup dry-run / init_s3_object_lock dry-run / verify_ledger CLI / ledger concurrency smoke.
  - 본 스토리는 `@pytest.mark.snapshot` / `walk_forward` / `@pytest.mark.asyncio` (1건) 사용.
- **`:memory:` vs 파일 DuckDB**: 단위 테스트는 `:memory:` (속도). 통합 테스트는 `tmp_path / "test.duckdb"`. Windows 락 경합 가능성 (1.4 Debug Log #7 패턴) → `gc.collect() + del client; gc.collect()` 후 재오픈.
- **moto / MinIO 선택**: 본 스토리는 `moto[s3]>=5` 선호 (in-process, 빠름). Object Lock 미지원 시 skip with 명시적 deferred-work. MinIO container 는 CI 복잡도 때문에 회피.
- **mypy Literal 위반 테스트 패턴** [Task 2.5]: fixture 파일 + subprocess `uv run mypy --strict fixture.py` + stderr regex assertion. CI 에서 느리면 `@pytest.mark.slow` 로 격리 후 선택 실행.
- **UTC datetime**: Story 1.4 Invariant 유지 — naive datetime 저장 금지. `BaseDTO._require_utc` 가 Pydantic validator 레벨 차단.
- **Coverage gate 없음** — 1.3/1.4 와 동일.

### Project Structure Notes

Story 1.5 는 `athena-execution` 패키지의 첫 실 코드 + 새 디렉토리 하나. 추가되는 경로:

```
packages/athena-execution/athena/execution/ledger/
  ├── __init__.py               # NEW Task 1.5 (재노출)
  ├── schema.sql                # NEW Task 1.2 (DDL 원문)
  ├── schema.py                 # NEW Task 1.4 (create_pre_trade_ledger)
  ├── dto.py                    # NEW Task 1.3 (LedgerEntry, LedgerEventTypeV1)
  ├── hash_chain.py             # NEW Task 2.1 (canonical_json, compute_entry_hash)
  ├── client.py                 # NEW Task 2.2 (LedgerClient)
  ├── segment_hash.py           # NEW Task 3.1 (compute_segment_hash, SegmentHashResult)
  └── backup.py                 # NEW Task 5.2 (ObjectLockConfig, object_key_for_segment)

packages/athena-execution/tests/
  ├── test_ledger_schema.py     # NEW Task 1.6 (5 시나리오)
  ├── test_ledger_client.py     # NEW Task 2.3 (8 시나리오)
  ├── test_segment_hash.py      # NEW Task 3.4 (5 시나리오)
  ├── test_backup.py            # NEW Task 5.4 (3 시나리오)
  └── test_verify_chain.py      # NEW Task 6.3 (5 시나리오)

scripts/
  ├── monthly_ledger_chain.py   # NEW Task 3.2 (CLI)
  ├── init_external_backup.sh   # NEW Task 4.1 (LUKS init w/ DRY_RUN)
  ├── init_s3_object_lock.py    # NEW Task 5.3 (S3 bucket + Object Lock)
  └── verify_ledger.py          # NEW Task 6.1 (chain verification CLI)

infra/systemd/
  └── mnt-external.mount        # NEW Task 4.2 (LUKS mount unit, 설치는 Story 1.10)

.github/workflows/
  └── monthly-ledger-verify.yml # NEW Task 6.2 (monthly scheduled verify, cron 미세조정 Story 1.10)

tests/integration/
  ├── test_ledger_concurrency_smoke.py       # NEW Task 2.4
  ├── test_monthly_ledger_chain_cli.py       # NEW Task 3.5
  ├── test_init_external_backup_dryrun.py    # NEW Task 4.4
  ├── test_init_s3_object_lock_dryrun.py     # NEW Task 5.5
  └── test_verify_ledger_cli.py              # NEW Task 6.4

tests/regression/
  └── test_ledger_event_type_literal.py      # NEW Task 2.5 (mypy 기반 Literal 검증)

packages/athena-execution/pyproject.toml     # MODIFIED Task 1.1, 5.1 (deps + dev-deps)
tests/regression/test_trading_pc_write_scope.py  # MODIFIED Task 1.7 (5 테이블 + LedgerClient 진입점)
tests/regression/test_dto_ddl_parity.py      # MODIFIED Task 1.7 (4번째 테이블 parity)
packages/athena-core/athena/core/keyring_client.py  # MODIFIED Task 4.5, 5.6 (KeychainKeys 추가)

docs/operating_playbook.md                   # MODIFIED Task 7.1 (§ Story 1.5 5 sub-section)
_bmad-output/implementation-artifacts/deferred-work.md  # MODIFIED Task 7.3
_bmad-output/implementation-artifacts/sprint-status.yaml  # MODIFIED Task 7.5
```

**명시적으로 생성 금지**:
- `packages/athena-execution/athena/execution/ledger/retention.py` — 본 스토리는 영구 보존, retention 은 없음 (NFR-A2).
- `packages/athena-execution/athena/execution/ledger/replicator.py` — 2-target 실시간 복제는 Story 1.10 / 6.2 가 systemd timer + 월간 job 으로 분리 처리.
- `infra/prometheus/rules/ledger_integrity.rules.yml` — architecture.md line 828 에 명시되지만 Story 1.9 가 Prometheus stack 설치 + rule 통합 시 작성.
- `packages/athena-execution/athena/execution/{kis_adapter,secondary_adapter,order_issuer,oco_hard_stop}.py` — Epic 4 (Story 4.1-4.7).
- `packages/athena-execution/athena/execution/{tax,compliance}/` — Epic 6 (Story 6.1-6.8).

**허용되는 architecture.md 이탈 (Dev Agent Record 에 기록)**:
- DuckDB row-level trigger 없음 → application-layer 4층 방어로 대체 (§Invariant #11). epics.md AC 본문의 "view + trigger pattern" 을 재해석 — 문서화된 이탈.
- `hash_chain.py` 가 execution 패키지에 있음 (architecture.md line 786 은 execution 내부 파일로 명시적). Story 3.1 이 재사용 시 동일 파일 import vs `athena-core` 승격은 3.1 시점 결정.
- `test_trading_pc_write_scope.py` 의 검증 방식이 1.4 의 "5 insert + INSERT INTO 금지" 에서 "5 insert + LedgerClient 단일 append + INSERT INTO pre_trade_ledger_raw 금지" 로 확장 — 의미는 동일 (Trading PC 의 write 경로 제한) 이지만 대상이 6번째 테이블로 확장.

### Previous Story Intelligence (Story 1.1/1.2/1.3/1.4 이관 사항 + 본 스토리 영향)

1. **`scripts/` 패턴 + per-file-ignore 일관성** [Story 1.3 invariant #6, 1.4 Task 2.3]
   본 스토리의 3개 새 `scripts/*.py` (`monthly_ledger_chain.py`, `init_s3_object_lock.py`, `verify_ledger.py`) 는 모두 subprocess 호출 0건 → per-file-ignore `S404/S603/S607` 미추가. `init_external_backup.sh` 는 bash → ruff 미적용.

2. **mypy hook `additional_dependencies` 일관성** [1.1 deferred-work 5번, 1.4 Task 1.7]
   본 스토리는 `boto3>=1.34` + `botocore-stubs` + (옵션) `moto[s3]>=5` 추가. `.pre-commit-config.yaml` mypy hook 에 동일 추가 필요 — Task 5.1 subtask 에 명시.

3. **Python 3.13 + uvloop 0.22.1 호환** [1.1 invariant #1]
   boto3 1.34+, moto 5+ 모두 Python 3.13 호환 (2026-04 시점 boto3 는 1.34-1.36 범위 권장). uv.lock 재생성 시 호환 실패 시 1.3x 범위 내 다른 버전 시도.

4. **`cp949 codec trap`** [1.1 Debug Log #8, 1.4 prev intel #3]
   본 스토리는 Windows 환경 실행 가능 (WSL2 Ubuntu 에서만 shellcheck / systemd / LUKS 동작 — 본 스토리의 bash/systemd 코드는 WSL2 에서 테스트, pytest 는 Windows cmd 에서도 동작). 모든 subprocess 호출 `encoding="utf-8"` 명시. `scripts/monthly_ledger_chain.py` 의 file IO 는 utf-8 encoding 명시 (본 스토리 이미 반영).

5. **`--dist=loadfile` 가 tmp_path 테스트 보호** [1.1 Debug Log #12]
   본 스토리의 fixture 모두 `tmp_path` 기반 — racing 없음.

6. **Pydantic 2 BaseDTO 상속 + 강제** [1.1 dto.py, 1.4 Invariant #1]
   `LedgerEntry(BaseDTO)` 가 frozen + strict + extra=forbid + UTC validator 자동 획득. 본 스토리는 `LedgerEventTypeV1` Literal 추가 → Pydantic 2 의 Literal 지원 (discriminated union 없이) 으로 runtime validation.

7. **DuckDB connection context manager** [1.4 Debug Log + prev intel #6]
   1.4 Task 2.2 에서 `with open_logger_duckdb(path) as conn:` 패턴 검증됨. `open_decisions_duckdb` 도 동일하게 동작 — 본 스토리 Task 3.2 monthly_ledger_chain.py 가 재사용.

8. **signed commit 자동화 + WSL2 commit 강제** [1.2 Task 5.4, 1.3 Task 5.6]
   본 스토리의 모든 commit (Task 1.12, 2.7, 3.7, 4.7, 5.7, 6.6, 7.6) 은 signed, WSL2 셸에서만. 현 Windows 세션의 feedback_windows_host_commit_boundary.md 가 명시적으로 요구: `git commit` 직접 실행 금지, WSL2 위임.

9. **`policy:` prefix 금지** [1.3 invariant #3]
   본 스토리는 어떤 정책 파일 (`config/policy.toml`, `config/flag_registry.toml`, `athena.core.flags`) 도 수정 안 함. 모든 commit 은 `feat`/`refactor`/`chore` prefix. `ledger/` 는 정책 아닌 **infra** 로 간주 — cooling gate 불필요.

10. **Source-of-Truth Invariants #1 BaseDTO 상속 + self-describing row** [1.4 Invariant #1]
    본 스토리의 `pre_trade_ledger_raw` 도 BaseDTO 3-필드 prefix 포함 → `timestamp/module_version/policy_version_git_sha` 가 모든 entry 에 자기 기술. `created_at_utc` 는 추가 중복 — DB server-side default.

11. **`test_trading_pc_write_scope.py` + `test_dto_ddl_parity.py` 확장** [1.4 Task 4.3, 6.1]
    본 스토리가 두 파일 모두 touch — invariant 의 pre-existing enforcement 를 깨지 않도록 주의. Task 1.7 의 명시적 subtask 로 업데이트.

12. **`FeatureStore.insert_*` 5개 유지 — `LedgerClient` 는 독립 진입점** [Task 1.7 결정]
    1.4 의 5개 `insert_*` 를 6개로 확장하지 않음. 이유: ledger append 는 FeatureStore 의 책임 경계 밖 (FeatureStore = market data read + 5 write). 혼동 방지 + 진입점 clarity. Invariant #2 (LedgerClient 유일 진입점) 의 구조적 뒷받침.

### Git Intelligence Summary

**Recent commits on `master` (상위 5건, 2026-04-22 기준):**
```
b25d80a chore(story-1.4): review-flip complete → done (40 findings closed)
7e50557 fix(story-1.4): review-flip MINOR patches + spec text reconciliation (Phase C)
9162f07 fix(story-1.4): review-flip MAJOR patches (Phase B, 17 findings)
52ab90d fix(story-1.4): review-flip CRITICAL patches (Phase A, 7 findings + decision)
370312a chore(story-1.4): DuckDB + Parquet shard + rsync pipeline verified, hand off to Story 1.5
```

Story 1.4 완료 상태로 master clean. 본 스토리의 신규 branch `story-1.5/pre-trade-ledger` 에서 작업.

**본 스토리의 커밋 전략** (총 7건 예상, 모두 signed WSL2 측에서 수행):
- T1 → `feat(execution): pre_trade_ledger DDL + LedgerEntry DTO + 6th table invariant update (Story 1.5 AC-1)`
- T2 → `feat(execution): LedgerClient single entry-point + SHA-256 chain + genesis auto-seed (Story 1.5 AC-2)`
- T3 → `feat(execution): monthly segment hash computer + CLI placeholder (Story 1.5 AC-3)`
- T4 → `feat(infra): external SSD LUKS init script + mount unit (dry-run supported) (Story 1.5 AC-4)`
- T5 → `feat(execution): S3 Object Lock Compliance bucket init + 5y retention + key SSOT (Story 1.5 AC-5)`
- T6 → `feat(ci): monthly ledger verify substrate + chain integrity checker (Story 1.5 AC-6)`
- T7 → `chore(story-1.5): Pre-Trade Ledger SHA-256 chain substrate verified, hand off to Story 1.6`

Task 4.6 (외장 SSD 실 셋업) 과 Task 5.6 (S3 실 credential) 은 하드웨어 / 계정 부재 시 `DRY_RUN=1` + `--dry-run` 까지만 수행, 실 셋업은 Story 1.10 prerequisite 로 defer.

### Latest Tech Information

| Library / Tool | Frozen Version | 본 스토리에서 검증할 동작 |
|---|---|---|
| duckdb | >=1 (1.4 확정) | `CREATE TABLE/VIEW/SEQUENCE IF NOT EXISTS`, `now()` default, `CHECK` constraint, view 와 table catalog separation |
| pydantic | >=2.5 (1.1 확정) | Literal type + BaseDTO frozen/strict/extra=forbid + UTC validator |
| hashlib | stdlib (Python 3.13) | SHA-256 hex digest, bytewise `\x00` separator |
| boto3 | >=1.34 (본 스토리 신규) | `create_bucket(ObjectLockEnabledForBucket=True)`, `put_object_lock_configuration(Mode='COMPLIANCE', Days=1825)`, `put_bucket_versioning`, SSE-C |
| botocore-stubs | (mypy dep) | `boto3` 타입 체킹 |
| moto | >=5 (옵션 dev-dep) | `mock_s3` decorator — Object Lock Compliance 지원 확인 필요 (2026-04 기준 moto 5.0+ 에서 개선 중) |
| systemd | 254+ (Ubuntu 24.04 — 1.4 prev intel) | `.mount` unit syntax, `Where=`, `Type=ext4`, escape form 일치 |
| cryptsetup | 2.6+ (Ubuntu 24.04) | `luksFormat --type luks2 --batch-mode`, `luksOpen`, stdin passphrase |
| keyring (jaraco) | >=25 (1.2 확정) | `get_secret` / `set_secret` (wincred + secret_service) |

**Platform-specific caveat:**
- bash `init_external_backup.sh`: WSL2 Ubuntu 에서만 실행. Windows cmd 에서 테스트 skip (`@pytest.mark.skipif(platform == 'Windows', reason='bash + LUKS are Linux-only')`).
- systemd `.mount` unit: WSL2 Ubuntu 24.04+ systemd 지원 (Story 1.2 에서 enable 확인).
- boto3 Object Lock: moto 의 Object Lock Compliance 지원이 2026-04 시점 제한적 — `put_object_lock_configuration` 는 stub 수준 support. 실 end-to-end 테스트는 MinIO container 또는 실 AWS (Story 1.10).
- Windows `os.replace` read-only 대상 처리: Task 3.5 에서 명시적 `chmod 0o644` 선처리.

### References

- **Epic · Story source**: `_bmad-output/planning-artifacts/epics.md#Epic-1` (line 420), `#Story-1.5` (lines 554-590)
- **Architecture 핵심 결정**:
  - `architecture.md#D4` (line 285 — 새 스키마 = Ledger 체인 새 세그먼트)
  - `architecture.md#D6` (lines 289-291 — Ledger 백업 2-target: LUKS + S3 Object Lock Compliance)
  - `architecture.md#D10` (line 301 — 백업 암호화 LUKS + SSE-C, 키 OS Keychain)
  - `architecture.md#D23` (lines 366-372 — 백업 schedule 표 — Ledger real-time mirror + 월간 S3 Object Lock)
  - `architecture.md#AR-DATA4,AR-DATA6,AR-SEC4` — story-header 에서 인용
  - `architecture.md#Process-Patterns` (lines 571-575 — `LedgerClient.append` 단일 진입점 규칙)
  - `architecture.md#Enforcement-Guidelines` §#5 (line 590 — Ledger 직접 SQL 금지)
- **Architecture file 구조**:
  - `architecture.md#Complete-Project-Directory-Structure` line 784-788 (`athena-execution/athena/execution/ledger/` 하위 4개 파일)
  - `architecture.md#Requirements-to-Structure-Mapping` line 986 (FR38-40 → `packages/athena-execution/athena/execution/ledger/`)
  - `architecture.md#Process-Boundaries` line 925 (`athena-backup` systemd timer — Story 1.10 이 실 unit)
- **Architecture naming**:
  - `architecture.md#Naming-Patterns` (lines 407-412 — DuckDB 테이블·컬럼·인덱스 네이밍)
  - `architecture.md#Format-Patterns` (line 503 — DECIMAL(18,4), line 497 — UTC naive 금지)
- **PRD 요구사항**:
  - `prd.md#FR38` (line 968 — Pre-Trade Authorization Ledger append-only §178-2 연계)
  - `prd.md#FR39` (line 969 — 월간 SHA-256 체인 해시 외장 백업)
  - `prd.md#NFR-S3` (line 1022 — tamper-evident + SHA-256 월간 체인 해시)
  - `prd.md#NFR-A1` (line 1047 — 모든 주문 의도·체결·거부 이벤트 월간 체인 해시 + 외장 write-only)
  - `prd.md#NFR-A2` (line 1048 — Ledger 영구 보존)
  - `prd.md#NFR-O3` (lines 1039-1042 — Critical alert 분기, Ledger 해시 불일치)
- **Downstream Story 상세 (선행 계약 확인)**:
  - `epics.md#Story-3.1` (lines 1131-1162 — anti_ego_events 가 본 스토리의 SHA-256 체인 패턴 재사용)
  - `epics.md#Story-3.7` (line 1387-1390 — Ledger writer seam 호출)
  - `epics.md#Story-4.7` (line 1687-1690 — 청산 이벤트 Ledger writer interface call)
  - `epics.md#Story-6.1` (lines 2099-2135 — Epic 1.5 substrate 위의 full LedgerWriter)
  - `epics.md#Story-6.2` (lines 2137-2173 — 월간 3-way 검증 full version)
- **Story 1.1 참조 (선행)**: `_bmad-output/implementation-artifacts/1-1-프로젝트-bootstrap-uv-monorepo-scaffold.md` § "Task 1.4" (athena-execution scaffold)
- **Story 1.2 참조 (선행)**: `_bmad-output/implementation-artifacts/1-2-환경-secrets-infrastructure-wsl2-os-keychain-ssh-signing.md` § "AC-2 OS Keychain" (`get_secret`/`set_secret` API + `KeychainKeys` enum)
- **Story 1.3 참조 (선행)**: `_bmad-output/implementation-artifacts/1-3-self-hosted-ci-cd-pipeline-7단계-gate.md` § "CI gates" (stage-2/3 marker 사용 패턴 + self-hosted runner + cooling gate)
- **Story 1.4 참조 (선행, 직접 상속)**: `_bmad-output/implementation-artifacts/1-4-duckdb-parquet-shard-rsync-data-pipeline.md`
  - § "Source-of-Truth Invariants" (1-7 모두 본 스토리에 적용, 특히 #7 — 4-필드 prefix + Trading PC write-scope 의 5→6 테이블 확장)
  - § "Threat Model Notes" (bypass 시나리오 분류 패턴)
  - § "Testing Standards" (marker + tmp_path + 결정론)
  - § "Project Structure Notes" (디렉토리 트리 확장 패턴)
  - § "Previous Story Intelligence" (templating 출처)
- **Story 1.3/1.4 deferred-work**: `_bmad-output/implementation-artifacts/deferred-work.md` § "Deferred from: Story 1.4" 의 Logger PC host setup 은 본 스토리에 무관 (본 스토리는 Trading PC only)
- **Implementation Readiness Report**: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-21.md` — READY verdict, Story 1.5 은 Critical/Major 없음
- **Project context (user memory)**:
  - `reference_athena_prd.md` — PRD 위치·구조
  - `reference_athena_architecture.md` — Architecture 위치·구조
  - `reference_athena_epics.md` — Epics 위치·구조
  - `feedback_task_completion_integrity.md` — "deferred" 라벨로 [ ] 회피 금지, review flip 전 모든 [ ] 의 이유 자문
  - `feedback_windows_host_commit_boundary.md` — Windows 세션 `git commit` 금지, WSL2 위임

## Dev Agent Record

### Agent Model Used

Amelia (bmad-agent-dev) on claude-opus-4-7[1m], auto-mode.

### Debug Log References

1. **cp949 codec trap on bash subprocess (Task 4.4)** — `test_init_external_backup_dryrun.py` subprocess.run() first attempt had `text=True` without explicit encoding. The Korean NOTE text in `init_external_backup.sh` caused `UnicodeDecodeError: 'cp949' codec can't decode byte 0xec` on Windows. Fix: added `encoding="utf-8", errors="replace"` to both subprocess.run calls. Story 1.1 Debug Log #8 / 1.4 prev intel #3 예고된 함정의 재발 — bash 경로는 Windows 로컬 cp949 기본 때문에 항상 encoding 명시 필요.

2. **BaseDTO module_version pattern mismatch (Task 2.2)** — 스펙 내부 코드 블록이 `"LedgerClient.v1.0.0"` 을 제안했으나 `BaseDTO._MODULE_VERSION_PATTERN = "^M\\d+\\.v\\d+\\.\\d+\\.\\d+$|^[a-z][a-z_]*\\.v\\d+\\.\\d+\\.\\d+$"` 가 소문자 snake context 를 요구 → `"LedgerClient"` 는 PascalCase 라 매치 실패. Fix: `LEDGER_CLIENT_MODULE_VERSION = "ledger_client.v0.1.0"` 상수로 정정. 스펙 narrative 와 구현 간 첫 sanctioned divergence — Change Log v0.2.0 기록.

3. **Hatchling 기본 wheel 이 .sql 파일을 제외 (Task 1.1)** — `only-include = ["athena/execution"]` 만으로는 파이썬 외 파일이 wheel 에 안 담긴다. Fix: `[tool.hatch.build.targets.wheel.force-include]` 섹션 추가해 `athena/execution/ledger/schema.sql` 명시 force-include. 확인: `uv build --wheel` 후 zip 내용에 `schema.sql` 포함.

4. **mypy `# type: ignore[no-untyped-call]` 사용처 불일치 (Task 5.3)** — 첫 drafting 에서 `boto3.client()` 호출에 `# type: ignore[no-untyped-call]` 를 달았으나 `botocore-stubs` 가 이미 `boto3.client` 를 typed 로 인식 → `error: Unused "type: ignore" comment`. Fix: `import boto3` 자체에 `# type: ignore[import-untyped]` 만 남기고 call-site 의 ignore 제거.

5. **`slow` pytest marker 레지스트리 외 사용 (Task 2.5)** — `@pytest.mark.slow` 추가 시 `--strict-markers` 가 reject. Fix: `pyproject.toml [tool.pytest.ini_options].markers` 에 `slow` 등록 + `tests/regression/test_pytest_markers_registered.py` 의 `EXPECTED_MARKERS` 집합에 `"slow"` 추가. 마커 테스트는 4 개 전체 regression 를 유지.

### Completion Notes List

- **AC-1 완료**: `pre_trade_ledger` DDL (raw table + view + sequence + CHECK constraint) + `LedgerEntry` DTO (BaseDTO 상속, Literal event_type) 작성, 11 컬럼 정확 일치 + 5 unit 시나리오 pass. `test_dto_ddl_parity.py` 에 4번째 테이블 parity 추가 (1 test). `test_trading_pc_write_scope.py` 에 LedgerClient 단일 append 메서드 + INSERT INTO pre_trade_ledger_raw 파일 한정 AST 검사 3 tests 추가. DuckDB 1.x 는 row-level trigger 부재라 view 계층 + AST 검사 + LedgerClient 진입점 3층 방어 (§Invariant #11).

- **AC-2 완료**: `LedgerClient(conn)` 생성 시 genesis auto-seed + idempotent. `append(event_type, payload, param_hash)` 는 prev_hash chain + this_hash = SHA256(prev || payload_json || policy_sha || event_type || user_id) 계산. canonical JSON (sort_keys + 최소 separators + default=str) 이 SSOT. 10 unit 시나리오 + asyncio 5 task concurrency smoke + mypy Literal 2 fixture regression.

- **AC-3 완료**: `compute_segment_hash(conn, year, month, prev_segment_hash, policy_sha)` 는 empty month 특례 (SHA256(b"")) + 체인 전파. `scripts/monthly_ledger_chain.py` 는 argparse + atomic write (`tmp + os.replace`) + `chmod 444` + cross-platform read-only dest 재실행 지원. 5 unit + 5 integration 시나리오.

- **AC-4 완료**: `scripts/init_external_backup.sh` 는 `DRY_RUN=1` fallback 으로 cryptsetup/mkfs/mount 을 print-only. OS Keychain `SecretName.LUKS_PASSPHRASE` (1.2 에서 이미 등록) 를 passphrase 소스로 사용. `infra/systemd/mnt-external.mount` 파일 추가 (enable 은 Story 1.10). 4 integration 시나리오 (dry-run 출력 tokens / DEVICE 부재 exit 1 / mount unit ini 파싱 / git exec mode 100755).

- **AC-5 완료**: `backup.py` 의 `ObjectLockConfig` (frozen, Compliance 5y 기본) + `object_key_for_segment` SSOT. `scripts/init_s3_object_lock.py --dry-run` 은 boto3 호출 없이 plan 출력. 실 boto3 경로는 OS Keychain credential 조회 + `put_object_lock_configuration`. moto 5.x 기반 in-process mock 이 Compliance/1825 day round-trip 성공 — skip 분기 준비돼 있으나 미발동. 4 unit + 3 integration.

- **AC-6 완료**: `scripts/verify_ledger.py` 의 `verify_chain(conn)` 은 각 entry 의 this_hash 를 재계산해 DB 값과 비교 + prev_hash 연속성 확인. stdout JSON contract: `{"verdict": "OK" | "CHAIN_BROKEN" | "VERIFY_FAILED", ...}`. exit 0/1. `.github/workflows/monthly-ledger-verify.yml` 은 매월 2일 05:00 KST cron + `workflow_dispatch` + DB 부재 시 graceful exit. 5 unit + 4 integration.

- **Task 7 완료**: operating_playbook.md `## Story 1.5` 섹션 5 sub-section 모두 추가, deferred-work.md `## Deferred from: Story 1.5` 14 항목 추가, 5-gate 모두 green, sprint-status `review` 전환.

- **Spec divergence (sanctioned)**: (a) `module_version` 상수 `"LedgerClient.v1.0.0"` → `"ledger_client.v0.1.0"` (BaseDTO pattern 호환). (b) `SecretName` enum 이름 `KeychainKeys` 아님 (Story 1.2 실 구현 확인). (c) `ATHENA_LUKS_EXTERNAL` / `ATHENA_S3_*` spec 이름 → 실 `LUKS_PASSPHRASE` / `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` (1.2 이미 등록). (d) pytest `slow` marker 추가.

- **WSL2 commit 위임**: Windows 세션이므로 Task 1.12 / 2.7 / 3.7 / 4.7 / 5.7 / 6.6 / 7.6 의 7 signed commit 은 Khuk0 의 WSL2 셸에서 일괄 수행. 본 스토리는 코드·테스트·문서 변경까지만 완료, review status 전환.

### File List

**신규 (NEW):**
- `packages/athena-execution/athena/execution/ledger/__init__.py` — 재노출 (Task 1.5)
- `packages/athena-execution/athena/execution/ledger/schema.sql` — DDL 원문 (Task 1.2)
- `packages/athena-execution/athena/execution/ledger/schema.py` — `create_pre_trade_ledger` + `SCHEMA_SQL` (Task 1.4)
- `packages/athena-execution/athena/execution/ledger/dto.py` — `LedgerEntry` + `LedgerEventTypeV1` (Task 1.3)
- `packages/athena-execution/athena/execution/ledger/hash_chain.py` — `canonical_json`, `compute_entry_hash`, `HASH_PLACEHOLDER` (Task 2.1)
- `packages/athena-execution/athena/execution/ledger/client.py` — `LedgerClient` + `EMPTY_PARAM_HASH` + `LEDGER_CLIENT_MODULE_VERSION` (Task 2.2)
- `packages/athena-execution/athena/execution/ledger/segment_hash.py` — `compute_segment_hash` + `SegmentHashResult` (Task 3.1)
- `packages/athena-execution/athena/execution/ledger/backup.py` — `ObjectLockConfig` + `object_key_for_segment` (Task 5.2)
- `packages/athena-execution/tests/test_ledger_schema.py` — AC-1 5 시나리오 (Task 1.6)
- `packages/athena-execution/tests/test_ledger_client.py` — AC-2 10 시나리오 (Task 2.3)
- `packages/athena-execution/tests/test_segment_hash.py` — AC-3 5 시나리오 (Task 3.4)
- `packages/athena-execution/tests/test_backup.py` — AC-5 4 시나리오 (Task 5.4)
- `packages/athena-execution/tests/test_verify_chain.py` — AC-6 5 시나리오 (Task 6.3)
- `scripts/monthly_ledger_chain.py` — 월말 segment hash CLI (Task 3.2)
- `scripts/init_external_backup.sh` — LUKS init with DRY_RUN (Task 4.1)
- `scripts/init_s3_object_lock.py` — S3 bucket + Object Lock Compliance init (Task 5.3)
- `scripts/verify_ledger.py` — 체인 검증 CLI + exit code contract (Task 6.1)
- `infra/systemd/mnt-external.mount` — LUKS mount unit (Task 4.2)
- `.github/workflows/monthly-ledger-verify.yml` — 월간 스케줄 verify job (Task 6.2)
- `tests/integration/test_ledger_concurrency_smoke.py` — asyncio 5 task + multi-conn skip (Task 2.4)
- `tests/integration/test_monthly_ledger_chain_cli.py` — AC-3 CLI 5 시나리오 (Task 3.5)
- `tests/integration/test_init_external_backup_dryrun.py` — AC-4 4 시나리오 (Task 4.4)
- `tests/integration/test_init_s3_object_lock_dryrun.py` — AC-5 3 시나리오 (Task 5.5)
- `tests/integration/test_verify_ledger_cli.py` — AC-6 CLI 4 시나리오 (Task 6.4)
- `tests/regression/test_ledger_event_type_literal.py` — mypy Literal regression 2 시나리오 (Task 2.5)

**수정 (MODIFIED):**
- `pyproject.toml` — `[dependency-groups].dev` 에 `botocore-stubs>=1.34`, `moto[s3]>=5` 추가; `[tool.pytest.ini_options].markers` 에 `slow` 등록 (Task 2.5, 5.1).
- `packages/athena-execution/pyproject.toml` — 런타임 dep 에 `boto3>=1.34`, `duckdb>=1`, `pyarrow>=17`, workspace siblings 추가; `[tool.hatch.build.targets.wheel.force-include]` 로 `schema.sql` 포함 (Task 1.1, 5.1).
- `tests/regression/test_trading_pc_write_scope.py` — LedgerClient 단일 `append` 메서드 assertion + `INSERT INTO pre_trade_ledger_raw` 외부 파일 금지 + positive control (Task 1.7).
- `tests/regression/test_dto_ddl_parity.py` — 4번째 테이블 (`pre_trade_ledger_raw`) parity 추가 (Task 1.7).
- `tests/regression/test_pytest_markers_registered.py` — `EXPECTED_MARKERS` 에 `slow` 포함 (Task 2.5).
- `docs/operating_playbook.md` — `## Story 1.5` 섹션 + 6 번째 테이블 write-scope 안내 추가 (Task 7.1).
- `_bmad-output/implementation-artifacts/deferred-work.md` — `## Deferred from: Story 1.5` 14 항목 (Task 7.3).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `1-5-*` status `ready-for-dev` → `review`, `last_updated=2026-04-23` (Task 7.5).
- `_bmad-output/implementation-artifacts/1-5-pre-trade-ledger-초기-세그먼트-sha-256-체인.md` — 본 파일 (status, task checkboxes, Dev Agent Record, File List, Change Log, Review Findings).
- `uv.lock` — `uv sync --group dev` 로 boto3 / moto / botocore-stubs + 파생 의존성 추가.
- `_bmad-output/implementation-artifacts/deferred-work.md` — review W1-5 (chain tip ORDER BY · DELETE reseed · genesis transaction · continuity wiring · previously §14 leap year) 등록 (Change Log v0.3.0).

**수정 (Review patch, Change Log v0.3.0):**
- `packages/athena-execution/athena/execution/ledger/segment_hash.py` — P1 `make_timestamp` → `make_timestamp(...) AT TIME ZONE 'UTC'` TIMESTAMPTZ anchor, P11 docstring sorted()/ORDER BY 정확화.
- `packages/athena-execution/athena/execution/ledger/hash_chain.py` — P10 docstring U+0000/UTF-8 정확화 + no-raw-NUL invariant 명시.
- `scripts/init_external_backup.sh` — P2 Keychain empty/<16-char passphrase reject + P4 DEVICE/MOUNT_POINT/LUKS_NAME regex hardening.
- `scripts/init_s3_object_lock.py` — P3 `_positive_retention_years` argparse type + P15 us-east-1 `LocationConstraint` 회피.
- `scripts/verify_ledger.py` — P5 --year/--month argparse validator, P6 `is not None` 비교, P7 `last_this = expected_this` on mismatch (avalanche 차단), P9 `_load_prev_segment` schema validation.
- `scripts/monthly_ledger_chain.py` — P8 fsync(tmp + parent dir) + `.tmp` try/finally cleanup.
- `.github/workflows/monthly-ledger-verify.yml` — P17 `LEDGER_PROVISIONED` env gate.
- `infra/systemd/mnt-external.mount` — P14 `After=cryptsetup.target` 추가.
- `tests/regression/test_ledger_event_type_literal.py` — P12 dead `or` branch 제거.
- `packages/athena-execution/tests/test_ledger_schema.py` — P13 `"LedgerClient.v1.0.0"` → `"ledger_client.v0.1.0"` 통일.
- `docs/operating_playbook.md` — P16 cryptsetup NOPASSWD sudoers prerequisite 블록 추가.
- `tests/integration/test_init_s3_object_lock_dryrun.py` — P3 regression test 2건 추가.
- `tests/integration/test_verify_ledger_cli.py` — P5/P9 regression test 2건 추가.

## Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-04-23 | 0.1.0 | Story 1.5 file created from epics.md (ready-for-dev). Comprehensive context engine analysis: 11 Source-of-Truth Invariants (pre_trade_ledger as 6th decisions.duckdb table, LedgerClient single entry-point, SHA-256 canonical form SSOT, canonical JSON, 2-target backup semantics, server-side vs client-side timestamp, object key SSOT, empty-month chain continuity, DuckDB trigger-absence application-layer 4-layer defense, 4-field prefix inheritance from 1.4, v1.0 Literal event_type subset), 13 Scope Boundary entries (full writer→6.1, anti_ego→3.1, real LUKS→1.10, real S3→1.10/6.2, 3-way verify→6.2, Prometheus rules→1.9, Global CB trigger→5.6, row-level trigger永久 impossible, multi-writer→V1.1+), 12 Previous Story Intelligence items (1.1/1.2/1.3/1.4 이관), 10 Architecture Pattern constraints, 7 Threat Model scenarios, 7 commit strategy commits, 7 Tasks (35+ subtasks), 6 ACs with detailed Given/When/Then. Dev-only dependency additions: boto3, botocore-stubs, optional moto[s3]. | Amelia via create-story skill |
| 2026-04-23 | 0.2.0 | Story 1.5 implementation complete → review. All 7 Tasks [x], 6 ACs satisfied. Net +43 tests (256p/5s from 213p baseline). 5-gate green (uv sync frozen / pytest / pre-commit / lint-imports / wheel build w/ schema.sql). Sanctioned spec divergences: (a) `module_version` spec string `"LedgerClient.v1.0.0"` → `"ledger_client.v0.1.0"` to satisfy BaseDTO pattern; (b) OS Keychain enum `SecretName(StrEnum)` (not `KeychainKeys`), reused existing `LUKS_PASSPHRASE` / `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` rather than spec-suggested `ATHENA_*` names; (c) pytest `slow` marker registered; (d) `hash_chain.compute_entry_hash` extends epics narrative hash input to include event_type + user_id (collision + multi-user defense, documented in hash_chain.py docstring). Real LUKS init + real S3 bucket provisioning deferred to Story 1.10 per scope. All 7 signed commits deferred to WSL2 per `feedback_windows_host_commit_boundary.md`. | Amelia via bmad-dev-story |
| 2026-04-23 | 0.3.1 | **Story 1.5 → done**. PR #10 (`884600a`) squash-merged to master after CI 7/7 green. 3 Gemini bot review threads resolved per PR #11 패턴 + deferred-work.md "PR #10" 섹션 3 항목 등록 (RETURNING id · segment_hash iterator · verify_ledger iterator — 모두 medium priority performance, V1.0 scope 에서 보류, Story 6.1/6.2 에서 일괄 처리). sprint-status `1-5-*` → done. | Amelia via bmad-code-review + WSL2 commit flow |
| 2026-04-23 | 0.3.0 | **Code review apply (bmad-code-review 3-layer adversarial, D1 resolved 옵션 C, 17 patch batch-applied, 5 defer synced to deferred-work.md)**. Triage: 1 decision · 17 patch (1 CRITICAL P1 `TIMESTAMPTZ vs naive make_timestamp` / 4 MAJOR P2-4+P17 / 5 MINOR P5-9 / 7 NIT P10-16) · 5 defer (W1-5) · 11 dismiss. Post-patch 5-gate: 260p/5s · pre-commit 10 hooks pass · lint-imports 5 Kept · wheel build w/ schema.sql. 신규 regression 테스트 +4: `test_retention_years_zero_rejected_at_boundary` (P3), `test_retention_years_negative_rejected_at_boundary` (P3), `test_month_out_of_range_rejected_by_argparse` (P5), `test_invalid_prev_segment_hash_rejected_with_specific_error` (P9). Acceptance Auditor 기존 PASS (6 AC · 11 Invariant · 7 Threat Model) 불변. | Amelia via bmad-code-review |
| 2026-04-23 | 0.2.1 | Pre-review-flip audit cleanup: (a) `client.py:147` S101 `assert row is not None` → explicit `if row is None: raise RuntimeError(...)` (production-grade — ruff S101 block 해소, 동작 불변); (b) orphan DuckDB file `--out-root` (Story 1.4 `tests/integration/test_parquet_shard_export.py` 가 pytest 실행 시마다 repo root 에 12 KB DuckDB 파일 생성하는 leftover bug — Story 1.4 review-flip 에서 미발견) 삭제 + `.gitignore` 에 `/--out-root` 패턴 추가로 커밋 오염 차단 + `deferred-work.md` 에 Story 1.4 post-review-flip bug 로 기록 (근본 수사는 별도 bugfix 스토리); (c) ruff-format 재포맷 4파일 (`client.py`, `test_ledger_client.py`, `test_ledger_schema.py`, `test_ledger_event_type_literal.py`) 재-stage → index ↔ working tree AM 상태 해소. 5-gate 재측정: pre-commit all-files green, `pytest -n auto` = **257 passed, 4 skipped in 45s** (WSL2 Linux, 이전 256p/5s Windows 대비 +1 pass — integration 1건 WSL2 환경에서 활성). 관련없는 M 상태 8파일 (1-3 story md, athena-logger-sync.service, scripts/check_*.py, scripts/setup_branch_protection.sh, tests/integration/conftest.py, test_policy_cooling_gate.py) 은 `git ls-files --eol` 결과 index=LF / working=CRLF 만 차이 — 실 내용 변경 0건, Story 1.5 커밋에 비포함. | Amelia via bmad-dev-story (audit) |

