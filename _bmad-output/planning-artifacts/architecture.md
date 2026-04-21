---
stepsCompleted:
  - step-01-init
  - step-02-context
  - step-03-starter
  - step-04-decisions
  - step-05-patterns
  - step-06-structure
  - step-07-validation
  - step-08-complete
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief-athena.md
  - _bmad-output/planning-artifacts/product-brief-athena-distillate.md
  - _bmad-output/planning-artifacts/research/domain-korean-short-term-trading-infra-research-2026-04-20.md
  - _bmad-output/brainstorming/brainstorming-session-2026-04-19-2122.md
workflowType: 'architecture'
project_name: 'Athena'
user_name: 'Khuk0'
date: '2026-04-21'
lastStep: 8
status: 'complete'
completedAt: '2026-04-21'
---

# Architecture Decision Document — Athena

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (58 FRs / 8 Categories):**

1. **Entry Scoring & Veto Gate** (FR1-12) — L2 호가창 24/7 수집, DART·뉴스 파싱, M1-M14 스코어링, 52-flag 곱셈 집계, `S_entry > θ AND Firewall=1` 이중 조건, missing flag neutral(1) degrade. 아키텍처 함의: **Feature Store → Alpha Defense → Orchestrator** 파이프라인이 코어. DTO 기반 inter-module 계약과 module versioning(semver) 필수.

2. **Anti-Ego Firewall** (FR13-18) — F1 본인 언어 실시간 감지(250건+ 라벨 fine-tune), F5 장중 읽기전용 마운트 + append-only 해시체인, anti_ego_events append-only. 함의: **시장 데이터와 동일 파이프라인에 통합된 병렬 Bounded Context**. 읽기전용 파일시스템 마운트는 OS 레벨 자원이며 아키텍처가 OS 경계까지 내려간다.

3. **Exit & Stop** (FR19-22) — M19 2차 미분 감시, M22 서버측 OCO + tamper 저항. 함의: Exit 경로는 알파 경로와 **다른 reliability tier** (SLA 더 엄격). 증권사 서버측 실행으로 override 물리 차단.

4. **Operational Defense** (FR23-29) — 슬리피지 실측/discount, 3종목 상한+테마 중복 금지, 뉴스 지연 drop, NLP confidence neutral 처리. 함의: Alpha Defense와 **독립적**으로 동작하는 Cross-Cutting Layer. 한쪽이 실패해도 다른 쪽 보존.

5. **Risk Control & Kill Switch** (FR30-37) — 4층 CB(Global/Account/Session/Symbol) 독립 발동, heartbeat 4h auto-flatten, Secondary Adapter fallback. 함의: **층위 간 결합도 최소화**. 각 층은 독립 state machine, 서로 cascade 트리거만 허용.

6. **Compliance & Audit** (FR38-46) — Pre-Trade Ledger append-only SHA-256 체인, M_tax 세후 계산, 자본 임계치 자동 트리거(준법감시인·공증 위임). 함의: Ledger는 **write path의 mandatory sink**. 모든 decision·order가 통과해야 함. 감사 영속성은 Maintainability가 아닌 법률 요구.

7. **Monitoring & Alerting** (FR47-52) — Grafana dashboard, Prometheus histogram, KPI 누적, 주간·월간 자동 리포트, missing rate 감사. 함의: **관측성 = 1급 시민**. 계량이 불가능한 NFR은 존재하지 않는 것으로 취급.

8. **Model Lifecycle & Policy** (FR53-58) — F1 재학습·PSI 자동 전환, walk-forward backtest 러너, Bayesian 튜닝, **git signed commit + 72h cooling + Paper 재검증** enforce. 함의: **정책 = git commit hash**. 배포 파이프라인이 F5 하드락의 연장.

**Non-Functional Requirements (32 NFRs / 7 Categories):**

- **Performance** — p99 < 5s, KB-BERT < 100ms 로컬, LLM 2s timeout, DuckDB p95 < 500ms, 블로킹 경로 외부 호출 금지
- **Reliability** — 로거 uptime ≥ 99%, heartbeat 5m push / 4h auto-flatten, MTTR < 30m, 물리 이중화, 72h cooling
- **Security** — OS Keychain/HSM (.env 금지), 주문/조회 키 분리, append-only ledger, 읽기전용 마운트, SSH key 로컬 네트워크
- **Integration** — KIS REST 20 req/s / WS 41건/세션 throttle, robots.txt 준수, graceful degradation (neutral(1) 또는 drop, crash 금지)
- **Observability** — 구조화 JSON 로그, Prometheus histogram, Alertmanager 3단 라우팅 (Critical/High/Medium), asyncio trace ID
- **Auditability** — SHA-256 체인 + 외장 write-only 백업, **영구** 보존, override 로그 100% 완전성, 월간 compliance 자기감사
- **Maintainability** — Pydantic 2 DTO 타입화, 모듈 semver, Change Control 최대 1건, `user_id` commercialization-ready seam, 증권사 Adapter 교체 용이성
- **명시적 제외** — Scalability, Accessibility (Scope Lock 영구 단일 사용자)

**Scale & Complexity:**

- Primary domain: **api_backend** (headless personal fintech trading, 외부 API/SDK/공개 endpoint 없음)
- Complexity: **High** — 실시간 레이턴시 × 멀티소스 데이터 융합 × ML/NLP × 실자본 리스크 × 신규 아키텍처(곱셈형 Veto + Anti-Ego)
- 상위 컴포넌트: **5 Bounded Contexts** (Feature Store · Alpha Defense · Operational Defense · Decision Orchestrator · Execution Gateway)
- MVP 모듈: 10 (M1/M2/M3/M9/M13/M14/M19/M22/F1/F5) + 인프라 (L2 로거/Feature Store/Pre-Trade Ledger/4층 Kill Switch/Compliance Guardrails/Observability)
- Growth V1.1+: 20 모듈, V2.x: 7+ 연구 테마 (Meta-gate로 해금)
- 사용자: 1명 영구 고정 (Bus factor = 1)

### Technical Constraints & Dependencies

**외부 의존성:**
- **KIS Developers API** — python-kis 래퍼, REST 20 req/s 추정, WebSocket 41건/세션, EGW00201 rate limit, "No close frame received" 오류 패턴
- **DART OpenAPI** — 공시 실시간, 무료, 자체 rate limit 적용
- **뉴스 피드** — 네이버/다음/연합/매경/한경 크롤링·RSS, robots.txt 준수
- **NLP 모델** — KB-BERT 로컬(MVP 기본축) + HyperCLOVA X/Solar Pro 2 비동기 2단계(M13)
- **pykrx** — OHLCV·VI 이력 백필

**자체 축적 자산 (시간 비대칭, 대체 불가):**
- **L2 호가창 Tick** — KIS Tick 히스토리 미제공 → Week 1 Day 1부터 자체 WebSocket 로거 24/7. 2년 축적이 V1.1+ M4/M5/LOBFrame의 전제.
- **F1 라벨 250건** — 본인 일지 수작업. 외주 불가, 복제 불가.

**법·규제 제약 (아키텍처 내장):**
- 자본시장법 §176 (허수성 호가·취소율 < 30%·분당 주문 상한) / §178 / §178-2 (과실 처벌)
- §17/§18 (투자자문·투자일임업) — Scope Lock 근거, 타인 계좌·코드 공개 영구 금지
- §9/§21 전자금융거래법 — OS Keychain 요구
- KIS 준법감시인 조건부 통지 (자본 ≥ 1,000만 원 또는 일일 주문 > 50건)

**운영 환경:**
- 현재 Windows 11 → Linux (또는 WSL2) 전환 검토 대상 (PT-8)
- 물리 이중화: 로거 PC ≠ 트레이딩 PC, UPS, LTE 라우터
- 단일 호스트 상시 실행 (24/7), 주간 배치로 F1 재학습

**런타임 스택 (Tier 별):**
- MVP: Python 3.11+ · asyncio+uvloop · Polars · DuckDB · python-kis · pykrx · KB-BERT · NetworkX · Prometheus+Grafana
- V1.0 보강: LOBFrame · Numba 핫패스 · 비동기 LLM
- V1.1+/V2.x: PyTorch Geometric · TLOB/LiT fine-tune · Rust+PyO3 핫패스

### Cross-Cutting Concerns Identified

1. **Audit & Tamper-Evidence** — Pre-Trade Ledger가 모든 write path의 mandatory sink. SHA-256 체인 해시 · 외장 write-only 백업 · `policy_version_git_sha` embed는 Bounded Context를 관통하는 횡단 관심사.

2. **Latency Budget Enforcement** — p99 < 5s 예산을 Feature Store → Alpha/Ops Defense → Orchestrator → Execution 전 경로에 적용. 동기·비동기 경로 엄격 분리, 블로킹 외부 호출 금지, LLM 타임아웃 + fallback.

3. **Policy Versioning & Change Control** — 정책 = `(수식, 파라미터, 모듈 set, 가중치)` 4-튜플의 git commit hash. 모든 DTO·로그·주문에 embed. git signed commit + 72h cooling + Paper 재검증이 배포 파이프라인 gate.

4. **Graceful Degradation** — 52 flag missing → neutral(1) + 월간 감사, NLP confidence 미달 → neutral, 뉴스 > 30s 지연 → drop, 외부 API 장애 → neutral/drop (crash 금지). **곱셈형 파이프라인 오염 방지가 설계 원리**.

5. **Physical & DR Layer** — 로거 PC ≠ 트레이딩 PC, UPS + LTE fallback, heartbeat 4h auto-flatten, 서버측 OCO, 읽기전용 마운트. 아키텍처가 OS · 네트워크 · 하드웨어 경계까지 관통.

6. **Compliance Guardrails** — 자본시장법 §176/§178/§178-2 수식을 FR/NFR 양쪽에 내장. 분당 주문 수 상한 · 취소율 < 30% · 허수성 호가 · 대주주 요건 추적은 코어 로직에 embed (별도 계층 아님).

7. **Anti-Ego Parallel Pipeline** — 트레이더 내부 상태(F1-F5)를 시장 데이터(M1-M25)와 **동일 DTO 타입 시스템**에서 처리. Single-user self-integrated 파이프라인이 리테일 대비 유일한 혁신 요소.

8. **Scope-Lock-Ready Seams** — `user_id` 컬럼 모든 테이블 유지 (V1.0 단일값 고정), 증권사 Adapter 추상화, 모듈 semver. Scope Lock은 기능 제약이지 아키텍처 제약이 아님 — 경계만 유지.

9. **Observability as Primary Interface** — 단일 사용자 전용이므로 UI는 최소, 대신 Grafana + Alertmanager가 사실상 "제품의 얼굴". 계량 불가능한 NFR은 존재하지 않는 것으로 취급.

## Starter Template Evaluation

### Primary Technology Domain

**Specialized Python backend (api_backend)** — headless 24/7 personal fintech trading service. 외부 public endpoint·SDK 없음, 단일 호스트 상시 실행, 실시간 이벤트 처리 + ML/NLP 추론 + DuckDB 영속 저장.

### Starter Options Considered

| 후보 | 평가 |
|---|---|
| `cookiecutter-pypackage` | 단일 Python 패키지 scaffold. Athena의 5 Bounded Context monorepo 요구와 불일치. ❌ |
| `cookiecutter-data-science` | Jupyter 중심 연구 템플릿. 24/7 서비스 구조 부재. ❌ |
| FastAPI full-stack template | 외부 REST endpoint 없음 (headless). 불필요한 의존성. ❌ |
| Airflow/Prefect DAG template | 스케줄 기반. Athena는 이벤트 기반 실시간 (WebSocket tick). ❌ |
| **`uv init` + 수동 scaffold (PT-I1 구조)** | 최소 편향, 현대 lockfile, Rust 기반 속도, 5-context 자유 배치. ✅ |

### Selected Starter: `uv init` + 수동 monorepo scaffold

**Rationale for Selection:**

Athena는 한국 증권사(KIS) + KB-BERT + L2 호가창 로거의 특화 조합으로, conventional starter가 제공하는 decision-opinionation이 대부분 **해당 영역 밖**이다. Generic scaffold를 채택하면 제거·수정 비용이 scaffold가 절감하는 타이핑보다 크다.

대신 uv의 project scaffold(`uv init`)로 최소 골격을 만들고, PRD PT-I1에 명시된 monorepo 구조를 수동 배치한다. uv는 2026-04 기준:

- pip 대비 10-100x 빠른 resolution (로컬 루프 시간 단축 = F5 72h cooling 내 Paper 재검증 iteration 여유 확보)
- `uv.lock` universal lockfile (`policy_version_git_sha` 4-튜플 중 "의존성 해시"를 재현 가능하게 고정 — NFR-A5 감사 요건과 맞물림)
- Rust 구현으로 Windows/WSL2/Linux 일관성 (운영 환경 전환 리스크 완화)
- Poetry 대비 가벼운 단일 바이너리 설치

**Initialization Command:**

```bash
# 1. uv 설치 (Windows PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. 프로젝트 초기화 (workspace 모드, monorepo 지원)
uv init --package athena --python 3.13

# 3. PT-I1 monorepo 구조 수동 배치 (Week 1 Day 1 이전)
#    athena/
#    ├── pyproject.toml (workspace root)
#    ├── uv.lock
#    ├── packages/
#    │   ├── athena-core/          (공통 DTO·config·logging, Pydantic 2)
#    │   ├── athena-feature-store/ (DuckDB Feature Store)
#    │   ├── athena-alpha-defense/ (M1-M25, F1-F5)
#    │   ├── athena-ops-defense/   (Slippage/Portfolio/Data Quality)
#    │   ├── athena-orchestrator/  (S_entry 집계 + Firewall 검증)
#    │   └── athena-execution/     (python-kis Adapter + Pre-Trade Ledger)
#    ├── scripts/                  (L2 로거 daemon, F1 라벨링 CLI)
#    ├── tests/                    (단위 + 통합 + 회귀)
#    └── _bmad-output/             (기존 planning artifacts)

# 4. 핵심 의존성 추가 (MVP Tier 1)
uv add python-kis polars duckdb pydantic uvloop
uv add --dev pytest ruff mypy black pre-commit
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**

- **Python 3.13** (PRD "3.11+" → 3.13 승격 권고)
  - asyncio 성숙도 최고치, uvloop 0.22.1 3.13 지원 확정 (2025-10)
  - python-kis Soju06 3.13 호환 확인 (2026-04 기준)
  - V2.x free-threading GIL 실험 시점 선택지 확보 (not blocking concern)
- **타입 체계:** Pydantic 2 DTO (inter-module 계약) + mypy/pyright strict
- **이벤트 루프:** uvloop 0.22.1 (asyncio 대비 2.6x, libuv C 기반)

**Dependency Management:**

- **uv 0.11.7** workspace 모드 (monorepo 5-context 단일 lockfile)
- `uv.lock` universal lockfile → 재현 가능 빌드 (감사 요건 NFR-A5)
- Tier 별 extras 분리 (MVP / V1.0 보강 / V1.1+)

**Build & Packaging:**

- `pyproject.toml` workspace 루트 + 각 package 하위 `pyproject.toml`
- Hatchling 기본 backend (uv 기본값, 설정 최소)
- 핫패스 Numba 삽입은 V1.0 보강(Tier 2)에서 개별 모듈 단위

**Testing Framework:**

- pytest + pytest-asyncio (asyncio 파이프라인 테스트)
- pytest-xdist (병렬 실행으로 회귀 스위트 W11-12 Paper 주기 단축)
- 결정론적 seed 고정 (PT-I2 요구)
- 과거 2건 실패 snapshot 회귀 CI 필수

**Code Quality Tooling:**

- ruff (lint + import sort, flake8/isort 통합 대체)
- black (formatter)
- mypy 또는 pyright (strict mode)
- pre-commit hook (F5 하드락 정신의 연장)

**Project Structure:**

- Monorepo workspace, package별 독립 버전 (semver NFR-M2)
- Inter-package 의존성은 workspace-internal path dep
- 공통 `athena-core`는 leaf, 나머지 context가 의존

**Development Experience:**

- uv의 `uv run` 으로 가상환경 자동 activation
- 핫패스 재시작 시간 < 2초 (Poetry install 수 분 대비 개발 주기 단축)
- Windows 11 (현재) ↔ WSL2/Linux (타겟) 간 lockfile 호환

**Note:** Project initialization using this command은 첫 번째 구현 스토리여야 한다 (Week 1 Day 1, L2 로거 구현의 직전 선행 작업). `uv.lock`은 git 커밋 필수 — 재현 가능성이 감사 요건(NFR-A5)의 물리 구현이다.

## Core Architectural Decisions

### Decision Priority Analysis

**Already Decided (PRD · Step 3 Starter — do not re-decide):**

- **데이터 엔진:** DuckDB Feature Store, Polars in-memory, 8 테이블 스키마 (PT-2), `user_id` seam
- **증권사:** python-kis Primary Adapter + Secondary 추상화 계층 (D-I1, D-I2)
- **감사:** Pre-Trade Ledger append-only SHA-256 체인, 외장 write-only 백업 (NFR-A1/A2)
- **보안:** OS Keychain (`.env` 금지), 주문/조회 key 분리, F5 읽기전용 마운트
- **리스크 제어:** 4층 Circuit Breaker, heartbeat 4h auto-flatten
- **관측성:** Prometheus + Grafana + Alertmanager, Telegram/카카오워크 3단 라우팅
- **런타임:** Python 3.13, uv 0.11.7, uvloop 0.22.1, Pydantic 2, monorepo workspace
- **개발 도구:** pytest + pytest-asyncio, ruff, mypy strict, pre-commit, Hatchling

**Critical Decisions (Block Implementation):**

- D1 Cross-PC 데이터 공유 패턴 (Parquet shard + rsync) — **DuckDB single-writer 제약의 불가피한 귀결**
- D9 읽기전용 마운트 구현 (WSL2 `chattr +i`) — F5 하드락 OS-레벨 enforcement
- D17 OS 분할 (Logger = Windows 11 / Trading = WSL2 Ubuntu 24.04 LTS)
- D19 Self-hosted GitHub runner — 72h cooling gate의 물리 구현

**Important Decisions (Shape Architecture):**

- D2-D6 데이터 계층 세부 (partitioning, retention, migration, cache, backup target)
- D7-D10 보안 구현 (keyring lib, SSH signing, LUKS)
- D12-D16 내부 통신·에러·버전·heartbeat 프로토콜
- D18, D20-D24 배포·CI·Config·metrics·backup·환경

**Deferred Decisions (V1.1+ 또는 자본 확장 시):**

- D11 YubiKey 2FA — 자본 확장 시 도입 검토
- Redis 캐시 계층 — V1.1+ 확장 시 재검토
- Mimir/Thanos 다중 Prometheus — 확장 필요 없음 (YAGNI)
- Staging 환경 추가 — Change Control 1건 소모 가치 없음

### Data Architecture

**D1. Cross-PC 데이터 공유 패턴 — Parquet Shard Rotation + rsync**

DuckDB는 multi-process write를 지원하지 않으며 한 번에 하나의 writer만 허용된다. 이는 PRD NFR-R4 "로거 PC ≠ 트레이딩 PC 물리 이중화" 요구와 직접 충돌하며, 다음 패턴으로 해결한다:

- **Logger PC (유일한 tick 데이터 writer):**
  - 자체 `features_logger.duckdb` (read-write)에 실시간 tick 쓰기 (hot 7일)
  - 매시간 **append-only Parquet shard** 로 export, `year=YYYY/month=MM/day=DD/hour=HH/symbol=XXX.parquet` 파티션
- **Trading PC (reader + decisions/orders writer):**
  - rsync pull 60초 주기로 Parquet shards sync
  - DuckDB external scan(`read_parquet('ticks/**/*.parquet')`) 로 feature 쿼리
  - 자체 `decisions.duckdb` (read-write)에 `modules_output`, `decisions`, `orders`, `anti_ego_events`, `labels_f1` 쓰기
- **이득:** shard는 idempotent → 네트워크 transient fail 복원력, Parquet은 Polars·DuckDB·PyTorch 모두 직접 소비.

**D2. 파일 분할:** Hot 7일 DuckDB direct + Cold Parquet archive 영구 보존. DuckDB single-writer 제약을 Logger PC 내부로 격리하고, Trading PC는 read-only external scan.

**D3. Retention 정책:** Raw L2 Tick Parquet **2년+ 영구 보존** (PRD "Time-Travel Rights" 해자 구현). DuckDB hot 데이터는 주간 배치로 Parquet 롤오프.

**D4. 스키마 마이그레이션:** Pydantic DTO = single source of truth. 새 스키마는 Polars ETL + 새 DuckDB 파일 생성 + Pre-Trade Ledger 체인 **새 세그먼트 시작** (이전 세그먼트 해시 종결 후). Alembic 없는 DuckDB 환경의 대안.

**D5. 캐시 계층:** Polars in-memory DataFrame 단독. Redis·Memcached 배제 (YAGNI). 350 종목 × feature 수 규모에서 충분하며, V1.1+ 유니버스 확장 시 재평가.

**D6. Ledger 백업 타겟 (2-target):**
- 주: 외장 SSD LUKS 암호화 (실시간 mirror)
- 보조: S3 (또는 Naver Cloud Object Storage) **Object Lock Compliance 모드** — 일정 기간 tamper-proof, 월간 업로드. `policy_version_git_sha` + month 해시를 객체 키로.

### Authentication & Security

**D7. Keyring library:** Python `keyring` (jaraco) — Windows Credential Manager `wincred` + Linux Secret Service 자동 backend. cross-platform 단일 API.

**D8. Git signed commit:** SSH signing (git 2.34+). YubiKey 기반 하드웨어 키 연결 용이, GPG keyring infra 관리 부담 회피.

**D9. 읽기전용 마운트:** Trading PC는 WSL2 Ubuntu 24.04 LTS에서 **`chattr +i` 장중 immutable**. Windows ACL 대비 tamper-resistant. 장 마감 후 정책 디렉토리 unlock → git commit + 72h cooling → 장 개시 전 relock.

**D10. 백업 암호화:** 외장 디스크 LUKS (Linux) / S3 SSE-C (AES-256). 키는 OS Keychain에만 저장.

**D11. YubiKey 2FA:** V1.0 MVP 제외. V1.1+ 자본 ≥ 1,000만 원 도달 시 SSH signing 키 하드웨어화 검토.

### API & Communication Patterns

**D12. Cross-PC 통신 프로토콜 (3-layer):**
- **데이터:** rsync over SSH, Trading PC pull 60초 주기
- **Heartbeat:** Prometheus `blackbox_exporter` ICMP ping + Alertmanager (5분 warn, 4h critical)
- **Control events:** 없음 (단방향 데이터 흐름. Trading PC는 Logger PC에게 signal 없음.)

**D13. Intra-process DTO 직렬화:** in-memory Pydantic 2 객체 참조 직접 전달 (asyncio.Queue). 직렬화 overhead 0. 디스크 영속은 Parquet (Arrow format).

**D14. Error taxonomy:**
```python
class ErrorCode(StrEnum):
    KIS_RATE_LIMIT = "EGW00201"
    FEATURE_MISSING = "FEATURE_MISSING"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    CONFIDENCE_BELOW_THRESHOLD = "CONFIDENCE_BELOW_THRESHOLD"
    DATA_STALE = "DATA_STALE"
    HEARTBEAT_LOST = "HEARTBEAT_LOST"
    SLIPPAGE_EXCEEDED = "SLIPPAGE_EXCEEDED"
    POLICY_NOT_COOLED = "POLICY_NOT_COOLED"
```
- Pydantic BaseException class + `ErrorCode` enum → 구조화 JSON 로그 → Prometheus error rate 집계

**D15. Module version embedding:** Hatchling build hook이 `git describe --always --dirty` 을 `athena._version.__commit__` 으로 주입. DTO 생성 시 자동 embed (`policy_version_git_sha` 필드). 런타임 shell 호출 overhead 0.

**D16. Heartbeat 프로토콜:** 자체 구현 없음. Prometheus blackbox_exporter로 Logger PC ICMP + HTTP(로거 status endpoint) 2중 체크 → Alertmanager 규칙으로 5분 push / 4h auto-flatten 트리거 (systemd unit 실행).

### Frontend Architecture

**N/A (Headless Backend).** Athena는 외부 공개 UI가 없는 헤드리스 서비스다. 사용자 인터페이스는 **Grafana 대시보드 + Alertmanager 모바일 푸시 + CLI 도구**로 구성되며, 별도 프론트엔드 프레임워크(React/Vue 등) 결정 없음. 구체 대시보드 패널 구성은 §Implementation Patterns 에서 정의.

### Infrastructure & Deployment

**D17. OS 분할:**
- **Logger PC: Windows 11 유지** — python-kis WebSocket 안정성 실적, 증권사 MTS 앱 공존, 단순 데이터 로깅 workload 에서 Linux 이점 작음
- **Trading PC: WSL2 Ubuntu 24.04 LTS (2029 지원)** — `chattr +i` tamper-resistance, systemd 서비스 관리, Prometheus/Grafana 표준 배포
- Docker 미사용 — 단일 호스트 단일 워크로드에서 overhead 부담

**D18. Process 감시:**
- Logger PC: **NSSM** (L2 WebSocket 로거 단일 프로세스 24/7)
- Trading PC: **systemd** (`athena-orchestrator.service`, `athena-logger-sync.service`, `prometheus.service`, `grafana-server.service`)

**D19. Git hosting + CI:**
- **GitHub private repo** + **self-hosted runner on Trading PC**
- self-hosted의 이득: 비용 0, 네트워크 격리 유지, 72h cooling · Paper 재검증 · 과거 2건 snapshot 회귀를 CI gate로 **물리적 enforce**

**D20. CI/CD 파이프라인 단계:**
1. pre-commit (ruff, black, mypy, secret scanner)
2. pytest unit tests (seed 고정)
3. pytest integration (mock KIS, e2e 시나리오 A/B/C/D/E)
4. 과거 2건 실패 snapshot 회귀 (S_entry 값 tolerance ± 5%)
5. Walk-forward smoke (공매도 재개 전후 레짐 분리 일부)
6. **72h cooling gate** — 직전 merge 시점 타임스탬프 확인, 미달 시 block
7. Paper 재검증 marker 확인 (수동 tag)
8. Prod deploy는 **수동 승인**

**D21. Config 관리:** **pydantic-settings 2.x** — Pydantic 2 통합, 환경변수 + OS Keychain backend, `.env` 배제 원칙 런타임 enforce.

**D22. Metrics retention:** Prometheus 단독, 90일 보존. 월간 스냅샷을 외장 백업으로 장기 보존. Mimir/Thanos는 YAGNI.

**D23. Backup schedule:**
| 대상 | 주기 | 위치 |
|---|---|---|
| Pre-Trade Ledger | real-time mirror | 외장 SSD (LUKS) |
| Parquet shards | 시간당 rsync | Trading PC |
| 전체 DuckDB | 주간 스냅샷 | 외장 SSD |
| 전체 시스템 이미지 | 월간 | 외장 SSD + S3 Object Lock |
| Ledger 월간 체인 해시 | 월간 | S3 Object Lock Compliance |

**D24. 환경 분리:** `prod`(실자본 KIS 실계좌) + `paper`(KIS 모의계좌). 코드 경로 공유, 계정 key만 분리. Staging 추가는 Change Control 1건 소모 가치 없음.

### Decision Impact Analysis

**Implementation Sequence (Week 별 선·후행):**

1. **W1 Day 1:** D17 OS 분할 확정 → WSL2 Ubuntu 24.04 설치 (Trading PC), Logger PC Windows 11 유지
2. **W1 Day 1-2:** D19 GitHub private + self-hosted runner 셋업 → D21 pydantic-settings 구성 → D7 keyring + D8 SSH signing 키 세팅
3. **W1 Day 2-3:** D1 Parquet shard 로거 구현 + D2 DuckDB 스키마 확정 + D6 외장 SSD LUKS 초기화
4. **W1 Day 3-5:** L2 WebSocket 로거 가동 (PRD 최우선) + D12 blackbox_exporter + Alertmanager 규칙
5. **W2:** D9 WSL2 `chattr +i` 검증 + D18 systemd/NSSM 서비스 정의 + D10 백업 암호화 키 생성
6. **W3+:** 모듈 구현 (PRD W3-8 로드맵)
7. **W9-10:** D20 CI/CD 7단계 완성, 특히 72h cooling gate 구현 검증
8. **W11-12:** Paper Trading + D23 백업 schedule 실운용 테스트

**Cross-Component Dependencies (연쇄 함의):**

1. **D1 (Parquet shard)** → Trading PC rsync 의존 → UPS + LTE fallback 가 **데이터 파이프라인의 critical path** (단순 DR 요건 넘어섬)
2. **D9 (WSL2 chattr +i)** → FR16 "장중 파라미터 수정 물리 차단" 구현이 **OS 명령 직접 호출** (application 로직 아님) → 장중/비장중 전환 hook 필요
3. **D19 (self-hosted runner)** → FR57 "git signed commit + 72h cooling + Paper 재검증" 을 **CI gate로 자동 enforce** → 인간 규율 실패 지점 제거
4. **D17 (Trading = WSL2)** → 외장 디스크 마운트는 Linux-side (/mnt/external) → D10 LUKS 선택 자연스러움 → D23 백업 schedule은 systemd timer 로 구현
5. **D13 + D15 (in-memory Pydantic + build-time version)** → Orchestrator + Alpha Defense + Ops Defense + Execution이 **단일 asyncio 런타임** 에 공존 (cross-process 통신 없음) → NFR-P1 p99 < 5s 예산 확보에 유리
6. **D1 + D3 (Parquet 2년 영구)** → 디스크 용량 산정 필요: 감시 유니버스 350종목 × L2 10호가 × 체결 × 거래일 ≈ 연 100GB 추정, 외장 SSD 2TB 권장
7. **D6 (S3 Object Lock Compliance)** → 삭제 불가 기간 설정 필요 → 자본시장법 §178-2 "영구 보존" 요구에 맞춰 Lock 기간을 길게 잡아야 함 (최소 5년 권장)

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 9 영역 — Athena는 1인 개발이지만 미래의 본인 및 AI coding session이 기존 코드와 일관되게 추가 구현하도록 아래 패턴을 고정한다.

### Naming Patterns

**Database Naming (DuckDB):**
- 테이블: lowercase `snake_case` 복수형 — `ticks`, `quotes`, `news`, `modules_output`, `decisions`, `orders`, `anti_ego_events`, `labels_f1`
- 컬럼: `snake_case` — `user_id`, `policy_version_git_sha`, `param_hash`, `created_at_utc`
- 외래키: `<referenced_table_singular>_id` — `decision_id`, `order_id`
- 인덱스: `idx_<table>_<column>` — `idx_ticks_symbol_ts`
- Parquet 파티션: `year=YYYY/month=MM/day=DD/hour=HH/symbol=XXX.parquet`

**Module / Flag Naming:**
- 시장 방어 모듈: `M1` ~ `M25` (PRD 명칭 불변, 재할당 금지)
- Anti-Ego 모듈: `F1` ~ `F5` (PRD 명칭 불변)
- Veto flag ID: `g_<snake_name>` — 52개 flag의 ID는 `pyproject.toml` 에 고정 리스트로 선언, runtime 추가·삭제 불가 (Change Control 경유 필수)
- Kill Switch 층위: `CB_GLOBAL` / `CB_ACCOUNT` / `CB_SESSION` / `CB_SYMBOL`

**Python Code Naming:**
- 클래스: `PascalCase` — `LinguisticCertaintyScorer`, `PreTradeLedger`
- 함수·변수: `snake_case` — `compute_s_entry`, `veto_flags`
- 모듈 파일: `snake_case.py` — `alpha_defense/m1_linguistic_certainty.py`
- 상수: `SCREAMING_SNAKE_CASE` — `DEFAULT_RATE_LIMIT`, `KRX_TRADING_HOURS_KST`
- Pydantic DTO: `<Domain>DTO` 또는 `<Event>Event` — `DecisionDTO`, `OrderIntentEvent`
- 타입 별칭: `PascalCase` — `Symbol = NewType("Symbol", str)`

**Prometheus Metrics:**
- 네이밍: `athena_<subsystem>_<metric>_<unit>`
- 예: `athena_signal_latency_seconds`, `athena_veto_flag_missing_total`, `athena_ledger_chain_valid` (boolean gauge), `athena_kill_switch_active{layer="global"}`
- 레이블: 소문자 snake_case, 유한 cardinality (symbol은 레이블로 쓰지 말 것 — 종목 수 제한되나 tick 수 폭발)

**File/Directory Naming:**
- 각 모듈은 자기 하위 디렉토리: `alpha_defense/m1/{scorer.py, features.py, tests/}`
- 테스트: 모듈 옆 `tests/` 디렉토리 (co-located) — `test_<module_file>.py`
- Scripts: `scripts/<daemon_name>.py` — `scripts/l2_logger.py`, `scripts/f1_labeler.py`
- 마이그레이션: `migrations/YYYYMMDD_<snake_description>.py`

### Structure Patterns

**Monorepo Layout (uv workspace):**
```
athena/
├── pyproject.toml            # workspace root
├── uv.lock
├── packages/
│   ├── athena-core/          # leaf, 공통 의존
│   │   └── athena/core/{dto.py, logging.py, settings.py, errors.py, version.py}
│   ├── athena-feature-store/
│   │   └── athena/feature_store/{duckdb_client.py, parquet_shard.py, schemas.py}
│   ├── athena-alpha-defense/
│   │   └── athena/alpha_defense/{m1/, m2/, m3/, m9/, m13/, m14/, m19/, m22/, f1/, f5/}
│   ├── athena-ops-defense/
│   │   └── athena/ops_defense/{slippage.py, portfolio.py, data_quality.py, kill_switch.py}
│   ├── athena-orchestrator/
│   │   └── athena/orchestrator/{s_entry.py, firewall.py, decision.py}
│   └── athena-execution/
│       └── athena/execution/{kis_adapter.py, secondary_adapter.py, ledger.py}
├── scripts/                   # daemons, CLI tools
├── tests/                     # cross-package integration + regression
├── migrations/                # schema evolutions
├── dashboards/                # Grafana JSON
├── alertmanager/              # rule files
└── _bmad-output/              # planning artifacts (git-tracked)
```

**Import Hierarchy (일방향 의존성):**
- `athena-core` ← 모두 의존 (leaf)
- `athena-feature-store` ← alpha/ops defense, orchestrator, execution 의존
- `athena-alpha-defense` / `athena-ops-defense` ← orchestrator 의존
- `athena-orchestrator` ← execution 의존
- **역방향 import 금지** — execution이 orchestrator를 import하면 circular

### Format Patterns

**DTO 필수 3-필드 (모든 Pydantic DTO에 강제):**
```python
from datetime import datetime
from pydantic import BaseModel, Field

class BaseDTO(BaseModel):
    timestamp: datetime  # UTC aware, microsecond precision
    module_version: str  # semver: "M1.v1.2.0"
    policy_version_git_sha: str  # 40-char git sha

class DecisionDTO(BaseDTO):
    symbol: str
    s_entry: Decimal
    passed_gates: list[str]
    firewall_active: bool
```

**Timezone 규칙:**
- 내부 저장·DTO: **UTC aware `datetime`** 필수 (`datetime.now(UTC)`)
- 사용자 표시·로그: KST (`ZoneInfo("Asia/Seoul")`)
- 변환은 `athena.core.time.kst_to_utc()` / `utc_to_kst()` 단일 유틸만 사용
- 절대로 naive datetime 저장·전송 금지 (linter 규칙 추가)

**Numeric Types:**
- 가격·수량·금액: `Decimal` (정밀도 보장)
- 비율·확률·스코어: `float` 허용 (Polars/NumPy 호환)
- S_entry·veto flag 값: `Decimal` (곱셈 누적 오차 방지)
- DuckDB 컬럼: 가격 `DECIMAL(18,4)`, 비율 `DOUBLE`

**JSON Log Format (구조화):**
```json
{
  "timestamp": "2026-04-21T14:30:00.123456Z",
  "level": "INFO",
  "module": "athena.alpha_defense.m1",
  "module_version": "M1.v1.2.0",
  "policy_version_git_sha": "a3f2d1c...",
  "trace_id": "uuid4",
  "event": "scorer_output",
  "symbol": "005930",
  "payload": { }
}
```

**Error Code Enum (고정, PRD PT-3):**
```python
from enum import StrEnum

class ErrorCode(StrEnum):
    KIS_RATE_LIMIT = "EGW00201"
    FEATURE_MISSING = "FEATURE_MISSING"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    CONFIDENCE_BELOW_THRESHOLD = "CONFIDENCE_BELOW_THRESHOLD"
    DATA_STALE = "DATA_STALE"
    HEARTBEAT_LOST = "HEARTBEAT_LOST"
    SLIPPAGE_EXCEEDED = "SLIPPAGE_EXCEEDED"
    POLICY_NOT_COOLED = "POLICY_NOT_COOLED"
```

### Communication Patterns

**asyncio.Queue 네이밍:**
- `<producer>_to_<consumer>_q` — `feature_to_alpha_q`, `alpha_to_orchestrator_q`
- 모든 큐는 Pydantic DTO만 전송 (Any/dict 금지)
- 큐 크기 명시 (bounded, 기본 1000), 가득 차면 oldest drop + 경보

**Event Naming (내부 pub-sub 필요 시):**
- 이벤트 클래스: `<Domain><Past-tense-verb>Event` — `OrderIssuedEvent`, `VetoActivatedEvent`, `KillSwitchTriggeredEvent`
- 문자열 이벤트 이름 사용 금지 (타입 체킹 우회 방지)

**Logging Level 규칙:**
- `DEBUG`: 개발·디버깅용 (prod disable)
- `INFO`: 정상 flow — decision, order issued, module output
- `WARNING`: graceful degradation — FEATURE_MISSING, CONFIDENCE_BELOW_THRESHOLD
- `ERROR`: 복구 필요 — KIS API fail 3회 후, rsync fail
- `CRITICAL`: Kill Switch 발동, heartbeat 4h, Ledger 해시 불일치

### Process Patterns

**Graceful Degradation (필수, 업계 unique):**
- 모든 외부 신호·feature는 **실패 시 `neutral(1)` 로 degrade**, 예외로 전파 금지
- 예외: Kill Switch · M22 hard-lock · Ledger write 실패만 CRITICAL로 처리
- degrade 시점에 WARNING 로그 + Prometheus counter 증가 필수

**Retry Policy:**
- 외부 API 호출 (KIS, DART, 뉴스): `tenacity` + exponential backoff + jitter, 최대 3회
- retry 후 실패 → `ErrorCode` 에 매핑된 degrade 경로 (PT-3 표)
- 절대 무한 retry 금지

**Validation Timing:**
- DTO 경계: Pydantic 자동 validation (strict mode)
- 내부 신뢰 경로: 중복 validation 금지 (overhead + 노이즈)
- 외부 입력 (KIS WebSocket 원본, 뉴스 크롤링 원본): 즉시 Pydantic DTO 로 변환 후 downstream
- DuckDB ↔ Pydantic: `.model_validate()` 필수, raw dict 전달 금지

**Ledger Write 규칙:**
- `LedgerClient.append(record: LedgerRecordDTO)` 단일 진입점
- 직접 `conn.execute("INSERT INTO ledger ...")` 영구 금지 (ruff custom rule로 차단)
- 모든 decision·order·override 시도가 Ledger 를 거친 후에만 실행
- append는 동기 (해시체인 consistency 보장), 비동기 wrapper 금지

**Policy Change Workflow:**
- 정책 변경은 `policy:` prefix 커밋 메시지 필수 (conventional commits 확장)
- CI가 `policy:` 커밋 탐지 → 72h cooling timer 시작 + Paper 재검증 marker 대기
- `policy:` 커밋 중 `--no-verify` 사용 금지 (hook이 거부)

### Enforcement Guidelines

**All implementations MUST:**

1. **DTO 3-필드 지키기** — timestamp(UTC) + module_version(semver) + policy_version_git_sha. 없으면 `BaseDTO` 상속으로 자동 획득. 상속 안 한 DTO는 ruff custom rule로 차단.
2. **Decimal 규칙** — 가격·수량은 `Decimal`. `float` 사용 시 ruff S-category 경고.
3. **pandas import 금지** — `ruff TID252` 또는 custom rule로 차단. Polars only.
4. **blocking HTTP 금지** — `requests` · `urllib.request` import 차단. `httpx.AsyncClient` 만.
5. **Ledger 직접 SQL 금지** — `LedgerClient` 외 ledger 테이블 write 차단.
6. **naive datetime 금지** — `datetime.now()` (naive) 차단. `datetime.now(UTC)` 강제.
7. **asyncio.Queue에 dict/Any 금지** — 모든 inter-module 전송은 Pydantic DTO.
8. **`os.environ.get()` 직접 호출 금지** — `athena.core.settings` 단일 객체 경유.
9. **veto flag ID 하드코딩 금지** — `athena.core.flags.FLAG_REGISTRY` 경유.

**Pattern Enforcement (자동):**

- **pre-commit**: ruff(E,F,I,N,UP,B,S,TID), black, mypy strict, check-yaml, check-merge-conflict, private-key-detector, custom hook (ledger-direct-write, naive-datetime, pandas-import)
- **CI gate**: pytest 커버리지 > 80%, 과거 2건 snapshot 회귀, veto flag registry drift detection
- **ruff custom rules** (`pyproject.toml` 확장): 위 9개 MUST 항목 모두 자동 탐지

**Pattern Violation 처리:**

- CI fail 시 해당 커밋 merge 불가
- ruff rule 우회 필요 시 `# noqa: <rule_id>` + **이유 주석 필수**
- 우회는 월간 감사 리포트에 집계, 3건 초과 시 회고 트리거

### Pattern Examples

**Good — Decision DTO 생성:**
```python
from athena.core.dto import BaseDTO
from athena.core.version import POLICY_VERSION_SHA, MODULE_VERSION
from datetime import datetime, UTC
from decimal import Decimal

class DecisionDTO(BaseDTO):
    symbol: str
    s_entry: Decimal
    passed_gates: list[str]
    firewall_active: bool

decision = DecisionDTO(
    timestamp=datetime.now(UTC),
    module_version=MODULE_VERSION,
    policy_version_git_sha=POLICY_VERSION_SHA,
    symbol="005930",
    s_entry=Decimal("0.014"),
    passed_gates=["m1", "m2"],
    firewall_active=True,
)
```

**Anti-pattern — 여러 규칙 동시 위반:**
```python
# naive datetime, float price, dict 전송, pandas, Ledger 우회 (모두 차단)
import pandas as pd  # ruff 차단
df = pd.read_csv(...)  # ruff 차단
now = datetime.now()  # ruff 차단 (naive)
price = 70500.0  # ruff S 경고 (should be Decimal)
await queue.put({"symbol": "005930", "price": price})  # dict 금지
conn.execute("INSERT INTO pre_trade_ledger ...")  # LedgerClient 우회, 차단
```

**Good — Graceful Degradation:**
```python
try:
    score = await llm_client.score(text, timeout=2.0)
except (TimeoutError, LLMError) as e:
    logger.warning(
        "llm_degrade",
        extra={"error_code": ErrorCode.LLM_TIMEOUT, "symbol": symbol},
    )
    llm_timeout_counter.labels(module="m13").inc()
    score = xgboost_fallback_score  # neutral degrade path
```

**Anti-pattern — 예외 전파:**
```python
# 곱셈 파이프라인 오염 + 시스템 crash (금지)
score = await llm_client.score(text, timeout=2.0)  # 예외 처리 없음
# TimeoutError 발생 시 downstream 전파 → orchestrator crash
```

## Project Structure & Boundaries

### Complete Project Directory Structure

```
athena/
├── README.md
├── pyproject.toml                          # workspace root
├── uv.lock
├── .python-version                         # 3.13
├── .gitignore
├── .gitattributes                          # LFS for Parquet samples
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/
│       ├── ci.yml                          # pytest + ruff + mypy + snapshot 회귀
│       ├── policy-cooling-gate.yml         # policy: 커밋 72h timer enforce
│       └── nightly-backup.yml              # 외장 SSD + S3 월간 업로드
│
├── packages/
│   ├── athena-core/                        # leaf: 공통 유틸, 모두가 의존
│   │   ├── pyproject.toml
│   │   └── athena/core/
│   │       ├── __init__.py
│   │       ├── dto.py                      # BaseDTO, DecisionDTO, OrderIntentDTO, ...
│   │       ├── settings.py                 # pydantic-settings Settings 싱글톤
│   │       ├── logging.py                  # 구조화 JSON 로거
│   │       ├── errors.py                   # ErrorCode StrEnum + Exception hierarchy
│   │       ├── version.py                  # __version__, POLICY_VERSION_SHA, MODULE_VERSION
│   │       ├── time.py                     # kst_to_utc, utc_to_kst
│   │       ├── flags.py                    # FLAG_REGISTRY (52 veto flag ID 고정)
│   │       ├── keyring_client.py           # OS Keychain wrapper
│   │       └── metrics.py                  # Prometheus client helpers
│   │
│   ├── athena-feature-store/               # 데이터 layer, DuckDB + Parquet
│   │   ├── pyproject.toml
│   │   └── athena/feature_store/
│   │       ├── __init__.py
│   │       ├── schemas.py                  # DuckDB DDL + Pydantic 매핑
│   │       ├── duckdb_client.py            # DuckDB 연결, read-only vs read-write
│   │       ├── parquet_shard.py            # 시간당 shard rotation (Logger PC)
│   │       ├── parquet_reader.py           # DuckDB external scan (Trading PC)
│   │       ├── rsync_client.py             # Logger→Trading sync (systemd timer)
│   │       ├── feature_query.py            # Polars-backed feature 조회
│   │       └── retention.py                # 7일 hot → cold Parquet rollover
│   │
│   ├── athena-alpha-defense/               # M1-M25, F1-F5 (MVP 10 모듈)
│   │   ├── pyproject.toml
│   │   └── athena/alpha_defense/
│   │       ├── __init__.py
│   │       ├── base.py                     # VetoFlag, Scorer 추상 기반
│   │       ├── m1/                         # Linguistic Certainty Scorer
│   │       │   ├── scorer.py               # KB-BERT inference
│   │       │   ├── fine_tune.py            # finance_sentiment_corpus + 본인 라벨
│   │       │   └── features.py
│   │       ├── m2/                         # Narrative Age Tracker (Omori decay)
│   │       │   ├── tracker.py
│   │       │   ├── sbert_cluster.py
│   │       │   └── omori.py
│   │       ├── m3/                         # Pre-News Drift Z-Detector
│   │       │   └── z_detector.py
│   │       ├── m9/                         # Time-of-Day Regime Multiplier
│   │       │   └── time_regime.py
│   │       ├── m13/                        # Two-Stage Hybrid Scorer
│   │       │   ├── xgboost_stage1.py
│   │       │   └── llm_stage2_async.py     # HyperCLOVA X / Solar Pro 2
│   │       ├── m14/                        # Basket Coherence Gate
│   │       │   ├── transfer_entropy.py
│   │       │   └── basket_graph.py         # NetworkX
│   │       ├── m19/                        # Loss Acceleration Trigger
│   │       │   └── accel_detector.py
│   │       ├── m22/                        # Hard-Locked Stop Loss
│   │       │   └── hard_stop.py            # 서버측 OCO ↔ KIS adapter
│   │       ├── f1/                         # Bargaining Language Detector
│   │       │   ├── detector.py
│   │       │   ├── labeler_cli.py          # 수작업 라벨링 CLI
│   │       │   └── psi_drift.py            # 월간 PSI 계산 + paper-only 전환
│   │       └── f5/                         # Parameter Hard-Lock
│   │           ├── readonly_mount.py       # chattr +i 래퍼 (장중/비장중)
│   │           ├── hash_chain.py           # append-only SHA-256 체인
│   │           └── git_revert_guard.py
│   │
│   ├── athena-ops-defense/                 # Blind Spot A/B/C + Kill Switch
│   │   ├── pyproject.toml
│   │   └── athena/ops_defense/
│   │       ├── __init__.py
│   │       ├── slippage.py                 # D-T6, FR23-24
│   │       ├── portfolio.py                # D-T8, FR25-26 (3종목 상한, 테마 중복 금지)
│   │       ├── data_quality.py             # D-T7, FR27-28 (뉴스 30s drop, confidence neutral)
│   │       ├── kill_switch/
│   │       │   ├── base.py                 # CircuitBreaker 추상
│   │       │   ├── global_cb.py            # FR31 (-3% 당일 차단)
│   │       │   ├── account_cb.py           # FR32 (-8% MDD 주간)
│   │       │   ├── session_cb.py           # FR33 (3회 손절 2h 쿨다운)
│   │       │   └── symbol_cb.py            # FR34 (M22 발동 종목 당일 차단)
│   │       ├── heartbeat.py                # FR35-36 (5분 push, 4h auto-flatten)
│   │       ├── throttle.py                 # FR29 (취소·재주문 자동 throttle)
│   │       └── compliance_guards.py        # §176 허수성 호가·분당 주문 상한·취소율
│   │
│   ├── athena-orchestrator/                # S_entry 집계 + Firewall 검증
│   │   ├── pyproject.toml
│   │   └── athena/orchestrator/
│   │       ├── __init__.py
│   │       ├── pipeline.py                 # 전체 asyncio pipeline 조립
│   │       ├── s_entry.py                  # FR9: Π G_i × M_regime × M_time 계산
│   │       ├── firewall.py                 # FR15: F1-F5 집계 → 0/1
│   │       ├── decision.py                 # FR10: S_entry > θ AND Firewall=1
│   │       ├── explain.py                  # FR11: M25 설명 리포트 생성
│   │       └── degrade.py                  # FR12: neutral(1) 처리 + 월간 감사
│   │
│   └── athena-execution/                   # 주문·증권사·Ledger
│       ├── pyproject.toml
│       └── athena/execution/
│           ├── __init__.py
│           ├── adapter_base.py             # Secondary Adapter 추상 (D-I2)
│           ├── kis_adapter.py              # python-kis Primary (D-I1)
│           ├── secondary_adapter.py        # MVP 설계 stub, V1.1+ 구현
│           ├── order_issuer.py             # 주문 발행 entry point
│           ├── oco_hard_stop.py            # M22 서버측 OCO
│           ├── ledger/
│           │   ├── client.py               # LedgerClient (유일 진입점)
│           │   ├── hash_chain.py           # 월간 SHA-256 체인
│           │   ├── backup.py               # 외장 SSD mirror + S3 Object Lock
│           │   └── schema.sql              # Pre-Trade Ledger DDL
│           ├── tax/
│           │   └── m_tax.py                # FR42-43 (세후 수익률, 대주주)
│           └── compliance/
│               ├── capital_monitor.py      # FR44: ≥1,000만 or >50건 트리거
│               ├── notification_templates/ # FR45-46 이메일·공증 템플릿
│               │   ├── kis_compliance_officer.md
│               │   ├── family_otp_delegation.md
│               │   └── external_approver_oath.md
│               └── audit_report.py         # 월간 자기 감사 리포트
│
├── scripts/                                # Daemons & CLI tools
│   ├── l2_logger.py                        # FR1: KIS WebSocket 24/7 (Logger PC)
│   ├── dart_crawler.py                     # FR2: DART 공시 실시간
│   ├── news_crawler.py                     # FR2: 뉴스 피드 통합
│   ├── pykrx_backfill.py                   # 2년 OHLCV + VI 백필
│   ├── orchestrator_daemon.py              # Trading PC systemd entry
│   ├── f1_labeler.py                       # FR53: F1 라벨링 CLI (GUI 아님)
│   ├── walk_forward_runner.py              # FR55: 공매도 전후 레짐 분리
│   ├── bayesian_tuner.py                   # FR56: θ, α/β/γ 튜닝
│   ├── snapshot_regenerate.py              # 과거 2건 in-sample 재계산
│   ├── ledger_verify.py                    # 월간 해시체인 검증
│   └── paper_trade_gate.py                 # 72h cooling + Paper 재검증 enforce
│
├── infra/
│   ├── systemd/                            # Trading PC (WSL2 Ubuntu)
│   │   ├── athena-orchestrator.service
│   │   ├── athena-logger-sync.service      # rsync from Logger PC
│   │   ├── athena-backup.timer
│   │   ├── athena-backup.service
│   │   └── athena-readonly-mount.service   # 장 개시 chattr +i / 마감 해제
│   ├── nssm/                               # Logger PC (Windows 11)
│   │   ├── athena-l2-logger.xml
│   │   └── athena-dart-crawler.xml
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   ├── rules/
│   │   │   ├── latency.rules.yml
│   │   │   ├── heartbeat.rules.yml
│   │   │   ├── kill_switch.rules.yml
│   │   │   ├── ledger_integrity.rules.yml
│   │   │   └── drift.rules.yml             # PSI > 0.2 경보
│   │   └── blackbox_exporter.yml           # Logger PC ICMP + HTTP
│   ├── alertmanager/
│   │   ├── alertmanager.yml
│   │   ├── telegram_receiver.yml
│   │   └── kakaowork_receiver.yml
│   └── grafana/
│       ├── dashboards/
│       │   ├── trading_overview.json       # FR47 메인 대시보드
│       │   ├── kpi_8.json                  # FR49 8대 KPI
│       │   ├── kpi_declaration.json        # FR50 선언 조건
│       │   ├── latency.json                # FR48 레이턴시 histogram
│       │   ├── ledger_audit.json
│       │   └── anti_ego_events.json
│       └── datasources/
│           └── prometheus.yml
│
├── migrations/                             # Pydantic DTO 기반 스키마 evolution
│   ├── README.md
│   └── 20260420_initial_schema.py
│
├── config/
│   ├── settings.toml                       # 비-secret 파라미터 (pydantic-settings 로드)
│   ├── universe.toml                       # 감시 종목 (KOSPI200 + KOSDAQ150)
│   ├── flag_registry.toml                  # 52 veto flag ID 고정 (source of truth)
│   └── policy.toml                         # θ_entry, α, β, γ, M_regime, M_time
│
├── tests/                                  # cross-package integration + 회귀
│   ├── conftest.py                         # seed 고정, mock KIS fixture
│   ├── integration/
│   │   ├── test_journey_a_washtrade.py     # J1 설거지 회피 e2e
│   │   ├── test_journey_b_override.py      # J2 임상 override 차단 e2e
│   │   ├── test_journey_c_f1_retrain.py    # J3 주간 재학습 e2e
│   │   ├── test_journey_d_heartbeat.py     # J4 DR 시나리오
│   │   └── test_journey_e_capital_gate.py  # J5 자본 ≥1,000만 트리거
│   ├── regression/
│   │   ├── test_case1_sillerg_snapshot.py  # S_entry = 0.014 ± 5%
│   │   └── test_case2_clinical_snapshot.py # 77% 경감 ± 5%
│   └── property/
│       └── test_s_entry_multiplicative.py  # 한 flag 0 → 전체 0 (hypothesis)
│
├── dashboards/                             # Grafana JSON 소스 관리 (infra/grafana/ 로 symlink)
├── docs/
│   ├── operating_playbook.md               # DR·Kill Switch 수동 절차
│   ├── weekly_ops_checklist.md
│   └── monthly_audit_checklist.md
│
├── data/                                   # .gitignore 에 추가, 외장 SSD 마운트 포인트 심볼릭
│   ├── duckdb/                             # Hot 7일 features_logger.duckdb / decisions.duckdb
│   ├── parquet/                            # 2년+ Cold Parquet archive
│   ├── ledger/                             # Pre-Trade Ledger (append-only, LUKS 외장 mirror)
│   ├── labels/                             # F1 250건+ 라벨 파일
│   └── models/                             # KB-BERT fine-tuned 체크포인트
│
└── _bmad-output/                           # planning artifacts (git-tracked)
    ├── planning-artifacts/
    │   ├── product-brief-athena.md
    │   ├── product-brief-athena-distillate.md
    │   ├── prd.md
    │   ├── architecture.md
    │   └── research/
    └── brainstorming/
```

### Architectural Boundaries

**Package Import Hierarchy (import-linter 로 enforce):**

```
athena-core                          (leaf)
    ↑
athena-feature-store
    ↑
athena-alpha-defense ─┐
athena-ops-defense ───┤
    ↑                 │
athena-orchestrator ←─┘
    ↑
athena-execution
```

**역방향 import 금지** — `import-linter` contracts:

- `athena.execution` 은 `athena.orchestrator` 를 import 불가 (의존 inversion 시 명시 DTO 인터페이스로)
- `athena.alpha_defense` 는 `athena.execution` 을 import 불가
- `athena.core` 는 다른 athena-* 패키지 import 불가

**Process Boundaries (OS 프로세스 레벨):**

| 프로세스 | 호스트 | supervisor | 책임 |
|---|---|---|---|
| `athena-l2-logger` | Logger PC (Windows) | NSSM | FR1: WebSocket L2 24/7 → DuckDB + Parquet shard |
| `athena-dart-crawler` | Logger PC | NSSM | FR2: DART 공시 실시간 |
| `athena-news-crawler` | Logger PC | NSSM | FR2: 뉴스 피드 |
| `athena-logger-sync` | Trading PC (WSL2) | systemd timer | rsync pull 60초 주기 |
| `athena-orchestrator` | Trading PC | systemd | 메인 의사결정 pipeline (asyncio 단일 프로세스) |
| `athena-backup` | Trading PC | systemd timer | Ledger 실시간 mirror, 주간·월간 full, S3 월간 |
| `athena-readonly-mount` | Trading PC | systemd (timers on 09:00/15:30 KST) | chattr +i / -i |
| `prometheus` | Trading PC | systemd | 메트릭 수집 |
| `grafana-server` | Trading PC | systemd | 대시보드 |
| `alertmanager` | Trading PC | systemd | Telegram/카카오워크 push |

**Orchestrator Internal Boundaries (Single asyncio Process):**

```
L2 ticks / news ─→ FeatureStore → [Alpha tasks] ─┐
                                    M1, M2, M3,   │
                                    M9, M13, M14  │
                                    F1            ├─→ S_entry computer ─→ Decision ─→ LedgerClient ─→ Execution
                                                  │    (Π G_i × 승수)       (θ & firewall)     (append)       (KIS adapter)
                              ─→ [Ops tasks] ─────┤
                                    slippage,     │
                                    portfolio,    │
                                    data_quality  │
                                                  │
                                  [Anti-Ego] ─────┘
                                    F5 (read-only mount 상태 확인)
                                  [Kill Switch] state machine (independent)
                                  [Heartbeat] emit (external blackbox_exporter observes)
```

### Requirements to Structure Mapping

**Entry Scoring & Veto Gate (FR1-12):**

- FR1 (L2 수집): `scripts/l2_logger.py` + `packages/athena-feature-store/athena/feature_store/parquet_shard.py`
- FR2 (DART·뉴스): `scripts/dart_crawler.py`, `scripts/news_crawler.py`
- FR3-8 (M1-M14): `packages/athena-alpha-defense/athena/alpha_defense/{m1,m2,m3,m9,m13,m14}/`
- FR9 (S_entry 집계): `packages/athena-orchestrator/athena/orchestrator/s_entry.py`
- FR10 (이중 조건): `packages/athena-orchestrator/athena/orchestrator/decision.py`
- FR11 (M25 설명): `packages/athena-orchestrator/athena/orchestrator/explain.py`
- FR12 (neutral degrade): `packages/athena-orchestrator/athena/orchestrator/degrade.py`

**Anti-Ego Firewall (FR13-18):**

- FR13-14 (F1): `packages/athena-alpha-defense/athena/alpha_defense/f1/`
- FR15 (Firewall 집계): `packages/athena-orchestrator/athena/orchestrator/firewall.py`
- FR16 (F5 물리 차단): `packages/athena-alpha-defense/athena/alpha_defense/f5/` + `infra/systemd/athena-readonly-mount.service`
- FR17 (anti_ego_events 로그): `packages/athena-alpha-defense/athena/alpha_defense/f5/hash_chain.py`
- FR18 (대시보드): `infra/grafana/dashboards/anti_ego_events.json`

**Exit & Stop (FR19-22):**

- FR19-22: `packages/athena-alpha-defense/athena/alpha_defense/{m19,m22}/` + `packages/athena-execution/athena/execution/oco_hard_stop.py`

**Operational Defense (FR23-29):**

- FR23-29: `packages/athena-ops-defense/athena/ops_defense/{slippage,portfolio,data_quality,throttle,compliance_guards}.py`

**Kill Switch (FR30-37):**

- FR30-34: `packages/athena-ops-defense/athena/ops_defense/kill_switch/`
- FR35-36 (heartbeat): `packages/athena-ops-defense/athena/ops_defense/heartbeat.py` + `infra/prometheus/blackbox_exporter.yml`
- FR37 (Secondary Adapter): `packages/athena-execution/athena/execution/{adapter_base,secondary_adapter}.py`

**Compliance & Audit (FR38-46):**

- FR38-40: `packages/athena-execution/athena/execution/ledger/`
- FR41 (단일 계좌): `packages/athena-execution/athena/execution/kis_adapter.py` (assertion)
- FR42-43 (M_tax): `packages/athena-execution/athena/execution/tax/m_tax.py`
- FR44-46 (자본 트리거): `packages/athena-execution/athena/execution/compliance/`

**Monitoring (FR47-52):**

- FR47 (Grafana): `infra/grafana/dashboards/`
- FR48 (Prometheus histogram): `packages/athena-core/athena/core/metrics.py`
- FR49-50 (KPI): `infra/grafana/dashboards/{kpi_8,kpi_declaration}.json`
- FR51-52 (주간·월간 리포트): `scripts/{weekly_report,monthly_audit}.py` + `packages/athena-execution/athena/execution/compliance/audit_report.py`

**Model Lifecycle (FR53-58):**

- FR53-54 (F1 재학습 + PSI): `scripts/f1_labeler.py` + `packages/athena-alpha-defense/athena/alpha_defense/f1/psi_drift.py`
- FR55 (walk-forward): `scripts/walk_forward_runner.py`
- FR56 (Bayesian 튜닝): `scripts/bayesian_tuner.py`
- FR57-58 (정책 변경 enforce): `.github/workflows/policy-cooling-gate.yml` + `scripts/paper_trade_gate.py`

**NFR Cross-Cutting:**

- NFR-P1 (p99<5s): `packages/athena-core/athena/core/metrics.py` + Prometheus rule
- NFR-R2 (heartbeat): `packages/athena-ops-defense/athena/ops_defense/heartbeat.py`
- NFR-S1 (OS Keychain): `packages/athena-core/athena/core/keyring_client.py`
- NFR-A1-A5 (Ledger + audit): `packages/athena-execution/athena/execution/ledger/`
- NFR-M1-M5 (DTO, semver, Change Control): `packages/athena-core/athena/core/{dto,version}.py` + `pyproject.toml` per package

### Integration Points

**External Integrations:**

| 외부 시스템 | 방향 | 위치 | 프로토콜 |
|---|---|---|---|
| KIS REST API | out | `athena-execution/.../kis_adapter.py` | python-kis, token-bucket 20 req/s |
| KIS WebSocket | in | `scripts/l2_logger.py` | python-kis, 41 구독/세션 |
| KIS 모의계좌 | both | 동일 adapter, `settings.environment="paper"` | 동일 |
| DART OpenAPI | in | `scripts/dart_crawler.py` | HTTPS REST, 자체 rate limit |
| 뉴스 피드 | in | `scripts/news_crawler.py` | RSS + HTTPS crawl, robots.txt |
| HyperCLOVA X / Solar Pro 2 | out | `athena-alpha-defense/.../m13/llm_stage2_async.py` | 비동기 only, 2s timeout |
| Telegram bot | out | `alertmanager` → Alertmanager receiver | HTTPS webhook |
| 카카오워크 | out | Alertmanager receiver | HTTPS webhook |
| S3 Object Lock | out | `athena-execution/.../ledger/backup.py` | boto3, Compliance 모드 |
| pykrx | in | `scripts/pykrx_backfill.py` | 일회성 백필 |

**Internal Communication (Process-to-Process):**

- Logger PC → Trading PC: **rsync over SSH** (Trading PC pull side, 60s polling)
- Trading PC ↔ Logger PC heartbeat: **Prometheus blackbox_exporter ICMP + HTTP**
- 제어 이벤트: 없음 (단방향 데이터 흐름)

**Internal Communication (Intra-Process):**

- Orchestrator 내부 모든 통신: `asyncio.Queue` (bounded, Pydantic DTO, 1000 크기)
- 큐 네이밍: `<producer>_to_<consumer>_q` — `feature_to_alpha_q`, `alpha_to_orchestrator_q`
- 오래된 메시지 drop + WARNING 로그 + counter 증가

**Data Flow:**

```
Logger PC:
  KIS WebSocket → l2_logger.py → DuckDB (hot 7일) + Parquet shard (hourly)
  DART API → dart_crawler.py → DuckDB news table + 로컬 Parquet
  뉴스 RSS → news_crawler.py → DuckDB news table + 로컬 Parquet

  [rsync over SSH] → Trading PC /data/parquet/

Trading PC:
  FeatureStore (read-only Parquet + 자체 decisions.duckdb)
    ↓
  Orchestrator (asyncio 단일 프로세스)
    ├─ Alpha Defense tasks (병렬)
    ├─ Ops Defense tasks (병렬)
    ├─ Anti-Ego Firewall tasks (병렬)
    ↓
  S_entry computer → Decision
    ├─ [거부] → LedgerClient.append(rejection) → M25 설명
    └─ [승인] → LedgerClient.append(intent) → Execution → KIS adapter → OCO hard stop
                                                              ↓
                                                         LedgerClient.append(fill)

  병렬: Kill Switch state machine (독립) · Heartbeat emit · Prometheus scrape
```

### File Organization Patterns

**Configuration Files (비-secret):**

- `config/settings.toml`: p99 예산, rsync 주기, rate limit 등 비-보안 파라미터
- `config/universe.toml`: 감시 종목 (KOSPI200 + KOSDAQ150), runtime 수정 허용 (DB 테이블 반영도 고려)
- `config/flag_registry.toml`: 52 veto flag ID 고정 (Change Control 필수)
- `config/policy.toml`: θ_entry, α/β/γ, M_regime, M_time — **F5 읽기전용 마운트 대상 디렉토리**

**Secrets:**

- 절대 파일 저장 금지. 모두 **OS Keychain** (`keyring` lib 경유)
- `athena.core.settings.Settings` 가 key 이름만 참조, 실제 값은 런타임에 keyring으로 fetch

**Source Organization:**

- package별 독립 `pyproject.toml` + semver
- inter-package 의존성은 workspace path dep (`uv.lock` 로 고정)
- 모듈별 하위 디렉토리 내 `tests/` co-located

**Test Organization:**

- **단위 테스트**: 모듈 옆 `tests/` (co-located)
- **통합 테스트**: `tests/integration/` (cross-package, J1-J5 시나리오)
- **회귀 테스트**: `tests/regression/` (과거 2건 snapshot)
- **속성 기반 테스트**: `tests/property/` (hypothesis 라이브러리, 곱셈형 파이프라인의 수학적 속성 검증)

**Data / Artifact 위치:**

- `data/` (gitignored, 외장 SSD 마운트 심볼릭): DuckDB, Parquet, Ledger, 라벨, 모델 체크포인트
- `_bmad-output/` (git-tracked): planning artifacts, PRD, architecture

### Development Workflow Integration

**개발 서버 구조:**

- Local dev는 `uv run scripts/orchestrator_daemon.py --env=dev --mock-kis`
- Paper Trading: `uv run scripts/orchestrator_daemon.py --env=paper` → KIS 모의계좌
- Prod: systemd service (`athena-orchestrator.service`) 수동 start (72h cooling 통과 후)

**Build Process:**

- `uv sync` → `uv.lock` 기반 재현 빌드
- Hatchling 빌드 훅: `git describe --always --dirty` → `athena.core.version.POLICY_VERSION_SHA` 주입
- Docker 이미지 생성 없음 (bare metal systemd/NSSM)

**Deployment Structure:**

- Logger PC: `git pull` → NSSM `restart athena-l2-logger`
- Trading PC: `git pull` → `uv sync` → `sudo systemctl restart athena-orchestrator` (수동 승인)
- **정책 커밋 (`policy:` prefix) 은 CI 72h cooling gate + Paper 재검증 marker 대기 후에만 deploy 허용**

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**

모든 결정이 상호 양립한다. 주요 호환 포인트:

- Python 3.13 + uvloop 0.22.1 + python-kis(3.13 호환) + Polars + DuckDB + Pydantic 2 = 2026-04 기준 전원 호환
- uv workspace monorepo + Hatchling build hook + git sha 주입 = 재현 가능 빌드 + policy_version embed 연쇄 성립
- Parquet shard + rsync + DuckDB external scan = DuckDB single-writer 제약 해소하면서 NFR-A5 재현성 보존
- WSL2 `chattr +i` + systemd timer (09:00/15:30 KST) = F5 하드락의 OS-레벨 enforcement
- GitHub self-hosted runner + `policy:` 커밋 탐지 + 72h cooling = FR57 정책 변경 규율의 CI 자동 enforce

**Pattern Consistency:**

- 9개 MUST 규칙(naive datetime, pandas, Decimal 등)이 `ruff` + pre-commit + custom hook로 전부 자동 탐지 가능
- 네이밍 컨벤션이 DuckDB, Python code, Prometheus metrics, 파일 경로 전반에 일관 적용
- 의존성 방향 (athena-core leaf ← feature-store ← alpha/ops-defense ← orchestrator ← execution) 이 `import-linter` contract로 강제 가능

**Structure Alignment:**

- 5 Bounded Context가 5개 packages에 1:1 매핑
- 58 FR이 전부 구체 파일·디렉토리에 매핑
- Process boundary (Logger PC vs Trading PC) 가 supervisor (NSSM vs systemd) 로 물리 분리

### Requirements Coverage Validation ✅

**Functional Requirements Coverage: 58/58 (100%)**

| 카테고리 | FR 범위 | 매핑 상태 |
|---|---|---|
| Entry Scoring & Veto Gate | FR1-12 | ✅ |
| Anti-Ego Firewall | FR13-18 | ✅ |
| Exit & Stop | FR19-22 | ✅ |
| Operational Defense | FR23-29 | ✅ |
| Kill Switch | FR30-37 | ✅ |
| Compliance & Audit | FR38-46 | ✅ |
| Monitoring & Alerting | FR47-52 | ✅ (addendum: `scripts/weekly_report.py`, `monthly_audit.py` 추가) |
| Model Lifecycle | FR53-58 | ✅ |

**Non-Functional Requirements Coverage: 32/32 (100%)**

모든 NFR에 대응 구성요소 존재. 다음 3개 NFR은 **W1 벤치마크로 실측 확인 필요**:

- NFR-P1 (p99 < 5s) — WSL2 I/O + rsync 60초 주기 조합에서 가능 여부 실측
- NFR-P2 (KB-BERT < 100ms) — Python 3.13 + uvloop 런타임에서 실측
- NFR-P4 (DuckDB p95 < 500ms) — external Parquet scan 경로에서 실측

### Implementation Readiness Validation ✅

**Decision Completeness:**

- 24개 Critical+Important 결정 전체 문서화, 버전 고정 (uv 0.11.7, Python 3.13, uvloop 0.22.1 등)
- Deferred 결정은 trigger 조건 명시 (Redis 캐시 · V1.1+ 확장 시 / YubiKey · 자본 확장 시)

**Structure Completeness:**

- 완전 디렉토리 트리 제시 (placeholder 없음)
- 외부 연동 10건 모두 위치·프로토콜 명시
- Process-to-process + Intra-process 통신 모두 정의

**Pattern Completeness:**

- 9개 MUST 규칙 자동 enforce 가능
- 5 카테고리 (Naming/Structure/Format/Communication/Process) 전체 커버
- Good/Anti-pattern 예제 제공

### Gap Analysis Results

**Important Gaps (5건 — 본 섹션에서 즉시 해소):**

1. **[해소] 누락 스크립트 추가:** 트리에 다음 3개 파일 추가
   - `scripts/weekly_report.py` (FR51 주간 리포트)
   - `scripts/monthly_audit.py` (FR52 월간 감사)
   - `scripts/seed_universe.py` (초기 KOSPI200+KOSDAQ150 시드)

2. **[해소] Async Blocking Pattern (§Implementation Patterns 보강):**
   - 모든 CPU-bound blocking 호출은 `asyncio.to_thread()` 래핑 의무
   - KB-BERT 추론은 ProcessPoolExecutor 검토 대상 (W1 벤치마크 결과에 따라 결정)
   - DuckDB 쿼리는 thread-safe connection + `asyncio.to_thread()` 래핑

   ```python
   # Good
   score = await asyncio.to_thread(kb_bert.score_sync, text)

   # Anti-pattern (asyncio 루프 블로킹)
   score = kb_bert.score_sync(text)
   ```

3. **[해소] WSL2 파일시스템 경로 제약:**
   - `chattr +i` 는 Linux ext4 전용, Windows 드라이브(`/mnt/c`) 에 작동 불가
   - **규칙:** policy · ledger · data 디렉토리는 **WSL2 ext4 내부** 배치
     - `/var/lib/athena/policy/` (F5 readonly mount 대상)
     - `/var/lib/athena/ledger/` (Pre-Trade Ledger)
     - `/var/lib/athena/data/` → 외장 SSD 마운트 포인트 심볼릭
   - Windows 드라이브 경유 금지

4. **[해소] Backtest Sandbox 모드:**
   - `settings.environment` enumeration 확장: `{dev, paper, prod, backtest}`
   - `backtest` 모드는 LedgerClient · KISAdapter · SecondaryAdapter가 no-op stub
   - `walk_forward_runner` 는 반드시 `backtest` 환경에서만 실행 (assertion)

5. **[해소] 구조화 로그 저장 경로:**
   - Logger PC (Windows): `C:\ProgramData\Athena\logs\*.jsonl`
   - Trading PC (WSL2): `/var/log/athena/*.jsonl`
   - 주간 외장 SSD 아카이브 (NFR-O1)

**Minor Gaps (3건 — 후속 작업 식별):**

6. **W1 벤치마크 리스트 (필수 실측 3건):**
   - WSL2 ↔ Windows rsync 실 latency vs p99 < 5s 예산
   - DuckDB external Parquet scan p95 < 500ms
   - KB-BERT 추론 p99 < 100ms (Python 3.13 기준)

7. **S3 Object Lock 대안:**
   - 네이버 클라우드 Object Storage Compliance Lock 지원 확인
   - 대안: 외장 SSD 2벌 + 가족 1인 신뢰 사본 분산 (MVP 시 비용 0)

8. **DR 테스트 하네스:**
   - `tests/integration/dr/` 신설
   - toxiproxy 또는 Python chaos injection 라이브러리로 네트워크 fail · KIS 장애 시뮬레이션
   - MVP W11-12 Paper 단계에서 실훈련과 병행

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed (58 FR + 32 NFR + 5 Bounded Context)
- [x] Scale and complexity assessed (High complexity, single-user fintech backend)
- [x] Technical constraints identified (KIS rate limits, §176/§178/§178-2, OS Keychain)
- [x] Cross-cutting concerns mapped (9개 관통 영역)

**Architectural Decisions**
- [x] 24개 Critical + Important 결정 문서화, 버전 고정
- [x] Technology stack fully specified (Python 3.13, uv 0.11.7, uvloop 0.22.1 ...)
- [x] Integration patterns defined (Parquet shard + rsync, asyncio.Queue)
- [x] Performance considerations addressed (p99 < 5s, blocking 금지 규칙)

**Implementation Patterns**
- [x] Naming conventions established (DuckDB · Python · Prometheus · 파일)
- [x] Structure patterns defined (monorepo, co-located tests)
- [x] Communication patterns specified (asyncio.Queue, 단방향 rsync)
- [x] Process patterns documented (graceful degradation, retry, ledger write)
- [x] 9개 MUST 규칙 ruff/pre-commit 자동 enforce

**Project Structure**
- [x] Complete directory structure defined (5 packages + scripts + infra + tests)
- [x] Component boundaries established (import hierarchy)
- [x] Integration points mapped (외부 10건 + 내부 통신)
- [x] Requirements to structure mapping complete (FR/NFR → 파일 100%)

### Architecture Readiness Assessment

**Overall Status:** ✅ **READY FOR IMPLEMENTATION**

**Confidence Level:** **High** — 다음 근거에서:

- 58 FR · 32 NFR 전부 구체 파일·컴포넌트에 매핑 완료
- 24개 Critical+Important 결정 전원 버전 고정 (2026-04 검증)
- Important Gap 5건 본 섹션에서 즉시 해소
- Minor Gap 3건 (W1 벤치마크 · S3 대안 · DR 하네스) 은 구현 중 해소 가능, 블로커 아님

**Key Strengths:**

1. **2-Track Defense 구조 분리의 물리 구현** — Alpha (Veto Gate + Anti-Ego) ↔ Operational (Slippage/Portfolio/Data Quality/Kill Switch) 이 완전히 다른 패키지·파일·책임으로 분리됨. 한쪽 실패가 다른 쪽 오염 불가.
2. **F5 하드락의 OS-레벨 물리 구현** — `chattr +i` + systemd timer로 application 로직 없이도 장중 파라미터 수정 차단. tamper-resistant.
3. **CI gate를 정책 규율의 enforce 장치로 활용** — `policy:` 커밋 + 72h cooling + Paper 재검증 marker 가 GitHub self-hosted runner 에서 자동 실행. 인간 규율 실패 지점 제거.
4. **Time-Travel Rights 자산 보호** — Parquet shard 2년+ 영구 보존 · LUKS 암호화 + S3 Object Lock (또는 네이버 클라우드 Object Lock) 이중 백업. 해자 상실 리스크 구조적 차단.
5. **Scope Lock-Ready Seams 유지** — 모든 테이블 `user_id` 컬럼, 증권사 Adapter 추상화, 모듈 semver. 코드는 Scope Lock을 물리적으로 강제하지만 경계는 재사용 가능.

**Areas for Future Enhancement (V1.1+ 에서 다룰 것):**

- PyTorch Geometric GNN (M7/M11/M18) 도입 시 별도 서비스 분리 검토
- Rust + PyO3 핫패스 (p99 레이턴시 극한 단축 필요 시)
- V2.x 연구 테마용 Red Team GAN 샌드박스 (sandbox 환경 확장)
- Multi-region DR (자본 확장 시)

### Implementation Handoff

**AI Agent Guidelines (Athena 구현 세션 시 준수 사항):**

1. 본 아키텍처 문서와 PRD의 FR/NFR을 **단일 진실의 원천**으로 참조
2. 9개 MUST 규칙 (§Implementation Patterns) 전원 ruff/pre-commit 자동 검증 — 우회 `# noqa` 필요 시 반드시 이유 주석
3. 새 모듈 추가는 **Change Control 1건** 원칙 존중, V1.0 MVP 범위 밖 제안은 V1.1+ 대기열로 직행
4. `policy:` 접두사 커밋은 **72h cooling + Paper 재검증** 통과 전 prod deploy 금지 (CI gate 우회 불가)
5. 외부 API (KIS, DART, 뉴스, LLM) 호출은 graceful degradation 필수 — crash 금지, neutral(1)/drop으로 퇴화

**First Implementation Priority (Week 1 Day 1 선·후행 관계):**

```bash
# Day 1 아침 — 환경 세팅
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv init --package athena --python 3.13

# Day 1 저녁 — WSL2 Trading PC 셋업
wsl --install -d Ubuntu-24.04
# /var/lib/athena/{policy,ledger,data} 디렉토리 생성 + LUKS 외장 SSD 마운트

# Day 1 말 — Git + CI
gh repo create athena --private
# self-hosted runner Trading PC에 등록

# Day 2 — L2 로거 구현 시작 (PRD 최우선)
# 모든 다른 작업의 prerequisite
```

**검증 Gate 통과 조건 (V1.0 Launch 전 필수 — PRD § MVP 검증 Gate 참조):**

1. Paper Trading 2주 완주
2. Kill Switch 4층 각 1회 이상 실발동·회복
3. DR 시나리오 (heartbeat fail → auto flatten) 실훈련
4. OOS 미경험 사건 5-10건 재계산 (88% 손실 경감 가설 검증)
5. 공매도 재개(2025-03-31) 전후 레짐 분리 walk-forward 통과
6. 자본시장법 체크리스트 (KIS 준법감시인 조건부 트리거 확정)

**본 아키텍처 문서 자체의 업데이트 정책:**

- 주요 결정 변경(패키지 구조, 런타임, DuckDB/Parquet 전략 등)은 `policy:` 접두사 git commit + 본 문서 Change Log append
- MVP 12주 중 아키텍처 변경은 **Change Control 1건** 원칙과 별개로 엄격히 제한 — 반드시 회고·이슈 트리거 후 재검토
