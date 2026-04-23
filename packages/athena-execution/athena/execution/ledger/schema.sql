-- Story 1.5 AC-1 — pre_trade_ledger DDL (decisions.duckdb 의 6번째 테이블).
--
-- 1.4 의 4-필드 prefix (timestamp / module_version / policy_version_git_sha / user_id)
-- 을 그대로 상속하고, 뒤에 ledger 전용 컬럼 (event_type / payload_json / prev_hash /
-- this_hash / param_hash / created_at_utc) 를 덧붙인다.
--
-- Write 진입점: athena.execution.ledger.client.LedgerClient.append — 직접 SQL
-- INSERT/UPDATE/DELETE 는 tests/regression/test_trading_pc_write_scope.py 가
-- AST 레벨로 차단한다 (DuckDB 1.x 는 row-level trigger 부재 — §Invariant #11).
--
-- Read 진입점: view `pre_trade_ledger`. 물리 테이블 `pre_trade_ledger_raw` 는
-- LedgerClient 외 호출자가 직접 참조하지 않도록 view 를 경유한다.
--
-- 모든 statement 는 idempotent: LedgerClient.__init__ 이 매번 호출해도 안전.

CREATE SEQUENCE IF NOT EXISTS seq_pre_trade_ledger_id START 1;

CREATE TABLE IF NOT EXISTS pre_trade_ledger_raw (
    id BIGINT PRIMARY KEY,
    "timestamp" TIMESTAMPTZ NOT NULL,
    module_version VARCHAR(64) NOT NULL,
    policy_version_git_sha VARCHAR(48) NOT NULL,
    user_id INTEGER NOT NULL DEFAULT 1,
    event_type VARCHAR(64) NOT NULL,
    payload_json VARCHAR NOT NULL,
    prev_hash VARCHAR(64),
    this_hash VARCHAR(64) NOT NULL,
    param_hash VARCHAR(64) NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((id = 1 AND prev_hash IS NULL) OR (id > 1 AND prev_hash IS NOT NULL))
);

CREATE OR REPLACE VIEW pre_trade_ledger AS
    SELECT * FROM pre_trade_ledger_raw;

CREATE INDEX IF NOT EXISTS idx_pre_trade_ledger_created_at
    ON pre_trade_ledger_raw(created_at_utc);
