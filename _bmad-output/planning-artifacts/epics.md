---
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
totalEpics: 8
totalStories: 65
frCoverage: "58/58"
completedAt: "2026-04-21"
---

# Athena V1.0 - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Athena V1.0, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**1. Entry Scoring & Veto Gate (Alpha Defense) — FR1-FR12**

- **FR1:** 시스템은 KIS WebSocket을 통해 L2 호가창 데이터를 Week 1 Day 1부터 24/7 실시간 수집·저장할 수 있다
- **FR2:** 시스템은 DART 공시·뉴스 피드(네이버·다음·연합·매경·한경)를 실시간 수집·파싱하여 Feature Store에 정규화 저장할 수 있다
- **FR3:** 시스템은 뉴스 문장의 언어적 확실성을 0-1 스코어로 산출할 수 있다 (M1)
- **FR4:** 시스템은 동일 서사의 생애주기(신규→피크→소진)를 추적하여 서사 나이 스코어를 산출할 수 있다 (M2, Omori law decay)
- **FR5:** 시스템은 뉴스 공시 전 비정상 가격·거래량 표류를 Z-score로 감지할 수 있다 (M3)
- **FR6:** 시스템은 시간대(장전·동시호가·장초·점심·마감·장후)별 가중치 multiplier를 산출할 수 있다 (M9)
- **FR7:** 시스템은 XGBoost 1단계 + 비동기 LLM 2단계 하이브리드 스코어링을 수행할 수 있다 (M13, LLM 2초 타임아웃 + 1단계 fallback)
- **FR8:** 시스템은 밸류체인 바스켓 내 선행주-후발주 Transfer Entropy를 계산하여 일관성 gate를 판정할 수 있다 (M14)
- **FR9:** 시스템은 `S_entry = 1[¬HardKill] · (αN+βV+γO) · Π G_i · M_regime · M_time` 수식으로 52개 veto flag를 곱셈 집계하여 종목별·시점별 S_entry 스코어를 산출할 수 있다
- **FR10:** 시스템은 `S_entry > θ_entry` **AND** `Anti-Ego Firewall = 1` 조건을 모두 충족한 경우에만 진입을 허용할 수 있다
- **FR11:** 시스템은 진입 거부 시 거부 이유(어떤 gate·flag가 0이었는지)를 M25 설명 리포트로 자동 생성할 수 있다
- **FR12:** 시스템은 52 veto flag 중 일부 결측 시 해당 flag를 neutral(1)로 degrade 처리하고 월간 missing_rate를 감사할 수 있다

**2. Anti-Ego Firewall (Internal Bias Defense) — FR13-FR18**

- **FR13:** 시스템은 사용자의 채팅·메모·장중 입력에서 흥정 언어 패턴(예: "조금만 더", "이번엔 다르다")을 실시간 감지할 수 있다 (F1)
- **FR14:** 사용자는 본인 과거 일지에서 흥정 언어 사례를 수작업 라벨링할 수 있으며, 시스템은 이 라벨 250건+ 으로 F1 모델을 fine-tune할 수 있다
- **FR15:** 시스템은 F1·F5 등 Anti-Ego 모듈 판정을 집계하여 Anti-Ego Firewall 상태 플래그(0 또는 1)를 산출할 수 있다
- **FR16:** 시스템은 장중 파라미터 수정·정책 변경·git revert를 물리적으로 차단할 수 있다 (F5, 읽기전용 마운트 + append-only 해시체인 로그)
- **FR17:** 시스템은 Anti-Ego Firewall 발동·시도 이력을 `anti_ego_events` 테이블에 append-only로 기록할 수 있다
- **FR18:** 사용자는 Anti-Ego Firewall 발동 상태를 대시보드에서 실시간 확인할 수 있다

**3. Exit & Stop Management — FR19-FR22**

- **FR19:** 시스템은 오픈 포지션의 손실 가속도(2차 미분)를 모니터링하여 파열적 하락을 감지할 수 있다 (M19)
- **FR20:** 시스템은 종목 단위 Hard-Locked Stop Loss를 서버측 OCO 주문으로 이중화하여 실행할 수 있으며, 트레이더 override가 물리적으로 불가능해야 한다 (M22)
- **FR21:** 시스템은 이벤트 근접도 기반 포지션 자동 축소 능력을 가진다 (M16, V1.1+ 목표. MVP는 수동 설정 + 이벤트 캘린더 alert)
- **FR22:** 시스템은 모든 청산 이벤트(M22, Kill Switch, DR auto-flatten)를 `orders` 테이블 및 Pre-Trade Ledger에 기록할 수 있다

**4. Operational Defense (Blind Spots A/B/C — 운영 방어 트랙) — FR23-FR29**

- **FR23:** 시스템은 주문 의도가(시그널가) vs 실제 체결가의 슬리피지를 tick 단위로 실측·기록할 수 있다 (D-T6)
- **FR24:** 시스템은 슬리피지 > 0.3% 시 후속 동일 신호의 S_entry × 0.5 discount를 적용할 수 있다 (D-T6)
- **FR25:** 시스템은 동시 오픈 포지션 수 상한(MVP: 3종목)을 enforce할 수 있다 (D-T8)
- **FR26:** 시스템은 동일 테마·섹터 2종목 이상 동시 보유를 금지할 수 있다 (D-T8)
- **FR27:** 시스템은 뉴스 피드 타임스탬프가 30초 초과 지연 시 해당 신호를 drop할 수 있다 (D-T7)
- **FR28:** 시스템은 NLP 모델 confidence가 임계값 이하인 feature를 neutral(1)로 자동 처리할 수 있다 (D-T7)
- **FR29:** 시스템은 취소·재주문 패턴을 자동 throttle할 수 있다 (§176 준수)

**5. Risk Control & Kill Switch — FR30-FR37**

- **FR30:** 시스템은 4층 Circuit Breaker(Global·Account·Session·Symbol)를 독립적으로 발동·해제할 수 있다
- **FR31:** 시스템은 일일 손실 ≥ -3% 시 Global CB를 발동하여 당일 신규 진입 전면 차단할 수 있다 (익일 자동 재개)
- **FR32:** 시스템은 MDD ≥ -8% 시 Account CB를 발동하여 주간 중지 + 자본 50% 축소 + 3일 냉각기 + Paper Trading 1주 재통과를 enforce할 수 있다
- **FR33:** 시스템은 연속 3회 손절 시 Session CB로 2시간 쿨다운할 수 있다
- **FR34:** 시스템은 M22 발동 종목에 대해 Symbol CB를 당일 차단할 수 있다
- **FR35:** 시스템은 heartbeat 무응답 4시간 경과 시 서버측 자동 전량 시장가 청산 + 신규 진입 영구 차단을 실행할 수 있다 (수동 해제 필수)
- **FR36:** 시스템은 heartbeat 지연 5분 시점에 모바일 푸시(Telegram/카카오워크)를 발송할 수 있다
- **FR37:** 시스템은 KIS API 장애 시 Secondary 증권사 Adapter로 fallback할 수 있다 (MVP는 추상화 계층, V1.1+ 실구현)

**6. Compliance & Audit — FR38-FR46**

- **FR38:** 시스템은 모든 주문 의도에 `S_entry 값`, `통과 Gate 목록`, `param_hash`, `policy_version_git_sha`, `시각 hash`를 포함하여 Pre-Trade Authorization Ledger에 append-only로 기록할 수 있다 (§178-2 연계)
- **FR39:** 시스템은 월간 SHA-256 체인 해시를 산출하여 외장 백업(외장 디스크 또는 S3 write-only)에 저장할 수 있다
- **FR40:** 시스템은 분당 주문 수 상한 및 취소율 < 30% 하드 제한을 enforce할 수 있다 (§176)
- **FR41:** 시스템은 본인 계좌 단일 사용만 허용하고 타 계좌 위임을 영구 차단할 수 있다 (§17/§18)
- **FR42:** 시스템은 세후 수익률을 계산할 수 있다 (M_tax: 증권거래세 0.18%, 배당세 15.4%, 금투세 폐지 반영)
- **FR43:** 시스템은 대주주 요건(종목당 지분 1% 또는 시가 10억 원) 근접 시 M_tax 경보를 발송할 수 있다
- **FR44:** 시스템은 자본 ≥ 1,000만 원 또는 일일 주문 > 50건 도달 시 KIS 준법감시인 통지 워크플로우를 자동 트리거할 수 있다
- **FR45:** 시스템은 KIS 준법감시인 통지 이메일 템플릿을 생성하고 회신 수령 기록을 Ledger에 append할 수 있다
- **FR46:** 시스템은 자본 ≥ 1,000만 원 도달 시 가족 1인 OTP 비상정지 권한 공증 위임 체크리스트와 외부 승인권자 서약서 템플릿을 자동 제시할 수 있다

**7. Monitoring & Alerting — FR47-FR52**

- **FR47:** 사용자는 L2 로거 uptime, 시그널 레이턴시 p99, Kill Switch 상태, KPI 누적을 실시간 대시보드(Grafana)에서 확인할 수 있다
- **FR48:** 시스템은 시그널 레이턴시를 Prometheus histogram으로 측정·기록할 수 있다 (histogram_quantile p99 지원)
- **FR49:** 시스템은 8대 KPI(월 수익률, Deflated Sharpe, MDD, 설거지 회피율, 이벤트 손실 경감률, 레이턴시 p99, override 로그 완전성, F1 PSI)를 실시간 누적 계산하여 대시보드에 표시할 수 있다
- **FR50:** 시스템은 KPI 선언 조건(n≥6개월, 50+ trades, bootstrap CI 하한 > 0) 충족 여부를 실시간 표시할 수 있다
- **FR51:** 시스템은 일별 거래 요약·override 시도 로그·KPI 변화를 주간 리포트로 자동 생성할 수 있다
- **FR52:** 시스템은 52 veto flag missing rate를 월간 감사 리포트로 자동 생성할 수 있다

**8. Model Lifecycle & Policy Management — FR53-FR58**

- **FR53:** 사용자는 주간 F1 라벨링 워크플로우(GUI 또는 CLI)로 새 override 시도 사례를 데이터셋에 추가할 수 있다
- **FR54:** 시스템은 F1 라벨 PSI를 월간 자동 계산할 수 있으며, PSI > 0.2 시 paper-only 모드로 자동 전환할 수 있다
- **FR55:** 시스템은 walk-forward 백테스트 러너로 공매도 재개(2025-03-31) 전후 레짐 분리 검증을 실행할 수 있다
- **FR56:** 시스템은 θ_entry 및 α/β/γ 가중치 튜닝을 Bayesian + walk-forward 조합으로 실행할 수 있다
- **FR57:** 시스템은 파라미터·정책 변경이 git signed commit + 72h cooling + Paper 재검증을 통과해야만 prod 반영하는 정책을 enforce할 수 있다
- **FR58:** 시스템은 정책 변경 이력(누가·언제·무엇을·왜)을 감사 로그에 기록할 수 있다

### NonFunctional Requirements

**Performance**

- **NFR-P1:** 시그널 생성 end-to-end 레이턴시 p99 < **5초** (Prometheus histogram_quantile 측정, 1000+ 신호/월 표본)
- **NFR-P2:** KB-BERT 로컬 추론 < 100ms per inference (MVP 기본축 조건)
- **NFR-P3:** LLM 2단계 호출 타임아웃 2초, 초과 시 1단계 XGBoost 결과로 fallback
- **NFR-P4:** DuckDB Feature Store 쿼리 p95 < 500ms (MVP 유니버스 350종목 × 2년 L2 데이터 기준)
- **NFR-P5:** 장중 블로킹 경로(시그널 생성 → 주문 의도 → 주문 발행)에서 외부 LLM·외부 API 블로킹 호출 금지 (비동기 Queue 경로만 허용)

**Reliability & Availability**

- **NFR-R1:** L2 호가창 WebSocket 로거 uptime **≥ 99%** (장중 기준, 월 허용 downtime 약 6시간 30분). 미달 시 paper-only 자동 전환.
- **NFR-R2:** heartbeat 정상 지연 < 60초. **5분** 초과 시 모바일 푸시, **4시간** 초과 시 서버측 자동 전량 시장가 청산 + 신규 진입 영구 차단 (수동 해제 필수)
- **NFR-R3:** MTTR (평균 복구 시간) < 30분 for Operator 수동 개입 가능 장애 (KIS reconnect, 로거 restart 등)
- **NFR-R4:** 물리 이중화: 로거 PC ≠ 트레이딩 PC, UPS + LTE 라우터 fallback 필수
- **NFR-R5:** 정책·파라미터 변경은 72h cooling + Paper 재검증 통과 전 prod 반영 금지 (F5 enforce)

**Security**

- **NFR-S1:** 모든 API key·secret은 **OS Keychain 또는 HSM** 수준 저장. `.env`·환경변수 평문·git·코드 하드코딩 영구 금지
- **NFR-S2:** KIS 주문 key와 조회 key는 분리 발급 및 별도 저장
- **NFR-S3:** Pre-Trade Authorization Ledger는 append-only이며, 외부 공격 또는 자기 override로 수정 불가능한 **tamper-evident** 구조여야 한다 (SHA-256 월간 체인 해시 + 외장 write-only 백업)
- **NFR-S4:** 장중 파라미터·정책 저장소는 **읽기전용 마운트**로 물리적 수정 차단
- **NFR-S5:** 로거 PC ↔ 트레이딩 PC 간 내부 통신은 로컬 네트워크 + SSH key 기반
- **NFR-S6:** KIS MTS 계정에서 일일·종목별 최대 주문금액 하드 제한 설정 (이중 안전장치)

**Integration**

- **NFR-I1:** KIS REST API: token-bucket 20 req/s 기준 throttle. `EGW00201` 에러 수신 시 재시도 최대 3회 + 지수 백오프 → 실패 시 Secondary Adapter fallback (V1.1+ 실구현)
- **NFR-I2:** KIS WebSocket: 41건/세션 상한 준수, 재연결 자동 복구 + 조회 자동 재등록 (python-kis 활용)
- **NFR-I3:** 뉴스 피드: 소스별 `robots.txt` 준수, 자체 rate limit 15 req/min default
- **NFR-I4:** 증권사 Adapter 경계는 KIS/Secondary 간 DTO 동일 interface 보장 (교체 비용 최소화)
- **NFR-I5:** 외부 API 장애 시 해당 신호는 neutral(1) degrade 또는 drop, 시스템 전체 crash 금지 (**graceful degradation**)

**Observability**

- **NFR-O1:** 모든 로그는 구조화 JSON 형식. 로컬 파일 저장 + 주간 외장 백업
- **NFR-O2:** Prometheus 필수 메트릭: 시그널 레이턴시 histogram, 모듈별 throughput (signals/min), error rate by code, Kill Switch 상태, 오픈 포지션 수
- **NFR-O3:** Alertmanager 우선순위별 라우팅: Critical (Global CB, heartbeat 4h, Ledger 체인 해시 불일치) / High (heartbeat 5분, PSI > 0.2, 취소율 > 20%, 로거 uptime < 99%) / Medium (slippage spike, missing rate, rate limit 근접)
- **NFR-O4:** asyncio 작업 단위 trace ID 부여 (M13 2단계 병렬 경로 및 비동기 파이프라인 디버깅 지원)

**Auditability & Compliance**

- **NFR-A1:** Pre-Trade Ledger는 모든 주문 의도·체결·거부 이벤트를 월간 SHA-256 체인 해시로 보호하며 외장 write-only 백업 (외장 디스크 또는 S3)
- **NFR-A2:** Ledger 보존 기간: **영구** (자본시장법 요구 및 감사 재현용)
- **NFR-A3:** override 시도 로그 완전성 **100%** (F1 자체 감지 + 사후 회고 교차검증으로 증명)
- **NFR-A4:** 월간 compliance 자기 감사 리포트 자동 생성 (취소율, 분당 주문 수, 대주주 근접, missing rate, PSI 포함)
- **NFR-A5:** 모든 정책 변경은 git signed commit에 기록 (누가·언제·무엇을·왜), 감사 로그에 복제 저장

**Maintainability & Evolvability**

- **NFR-M1:** 모든 inter-module 통신은 Pydantic 2 DTO 타입화. `timestamp`, `module_version`, `policy_version_git_sha` 필수 필드
- **NFR-M2:** 모듈 개별 semver (예: `M1.v1.2.0`), DTO 및 로그에 embed
- **NFR-M3:** Change Control: MVP 12주 중 모듈 추가·삭제 **최대 1건**. 초과 시 12주 일정 자동 리셋
- **NFR-M4:** 데이터 스키마 모든 테이블에 `user_id` 컬럼 유지 (V1.0 단일 값 고정, commercialization-ready seam)
- **NFR-M5:** 증권사 Adapter는 추상화 계층으로 분리 (KIS/Secondary 교체 시 코어 로직 영향 없음)

**Excluded (명시적)**

- **Scalability** — §17/§18 Scope Lock, 단일 사용자 영구 고정
- **Accessibility** — 공공 UI 없음, WCAG/Section 508 대상 아님

### Additional Requirements

**Starter Template (Week 1 Day 1, Epic 1 Story 1 선행 작업):**

- **AR-ST1:** `uv init --package athena --python 3.13` 으로 프로젝트 골격 생성
- **AR-ST2:** PT-I1 monorepo 구조 수동 배치: `packages/athena-core`, `athena-feature-store`, `athena-alpha-defense`, `athena-ops-defense`, `athena-orchestrator`, `athena-execution` + `scripts/`, `tests/`, `infra/`
- **AR-ST3:** 핵심 의존성 추가: `python-kis polars duckdb pydantic uvloop keyring pydantic-settings` + dev: `pytest pytest-asyncio ruff mypy pre-commit import-linter`
- **AR-ST4:** `uv.lock` git 커밋 필수 (재현 가능성이 NFR-A5 감사 요건의 물리 구현)

**Infrastructure & Deployment (D17-D24):**

- **AR-INF1:** OS 분할 — Logger PC는 Windows 11 유지 (python-kis WebSocket 안정성), Trading PC는 WSL2 Ubuntu 24.04 LTS 설치 (2029 지원 LTS)
- **AR-INF2:** Process supervisor — Logger PC는 NSSM (L2 WebSocket 로거·DART·뉴스 크롤러), Trading PC는 systemd (orchestrator, logger-sync, backup, readonly-mount, prometheus, grafana, alertmanager)
- **AR-INF3:** GitHub private repo + **self-hosted runner on Trading PC** (72h cooling gate·Paper 재검증·snapshot 회귀의 물리 enforce)
- **AR-INF4:** CI/CD 7단계 파이프라인: pre-commit → pytest unit → pytest integration (mock KIS, J1-J5) → 과거 2건 실패 snapshot 회귀 (S_entry ±5%) → Walk-forward smoke → 72h cooling gate → Paper 재검증 marker → prod deploy 수동 승인
- **AR-INF5:** Docker 미사용 — 단일 호스트 단일 워크로드 overhead 회피
- **AR-INF6:** 환경 분리 — `prod`(KIS 실계좌) / `paper`(KIS 모의계좌), 코드 경로 공유 계정 key만 분리. Staging 추가 금지 (Change Control 1건 소모 가치 없음)

**Data Architecture (D1-D6):**

- **AR-DATA1:** Cross-PC 데이터 공유 — Logger PC가 `features_logger.duckdb` (hot 7일) + 시간당 append-only Parquet shard export (`year=YYYY/month=MM/day=DD/hour=HH/symbol=XXX.parquet`), Trading PC가 rsync pull 60초 주기 + DuckDB external scan
- **AR-DATA2:** 8-테이블 DuckDB 스키마: `ticks`, `quotes`, `news`, `modules_output`, `decisions`, `orders`, `anti_ego_events`, `labels_f1` (모든 테이블 `user_id` 컬럼 유지 — NFR-M4 seam)
- **AR-DATA3:** Retention — Raw L2 Tick Parquet **2년+ 영구 보존** (Time-Travel Rights 해자), DuckDB hot → Parquet 주간 롤오프
- **AR-DATA4:** 스키마 마이그레이션 — Pydantic DTO = single source of truth, 새 스키마는 새 DuckDB 파일 + Ledger 체인 새 세그먼트 시작 (Alembic 미사용)
- **AR-DATA5:** 캐시 계층 — Polars in-memory DataFrame 단독 (Redis/Memcached 배제)
- **AR-DATA6:** Ledger 백업 2-target — 외장 SSD LUKS 실시간 mirror (주) + S3 Object Lock Compliance 모드 월간 (보조, 최소 5년 Lock)
- **AR-DATA7:** 디스크 용량 — 감시 유니버스 350종목 × L2 10호가 × 체결 × 거래일 ≈ 연 100GB, **외장 SSD 2TB 권장**

**Security & Access Control (D7-D11):**

- **AR-SEC1:** Python `keyring` (jaraco) — Windows Credential Manager (wincred) + Linux Secret Service auto backend
- **AR-SEC2:** Git signed commit — SSH signing (git 2.34+), YubiKey 하드웨어 키 연결 용이
- **AR-SEC3:** 읽기전용 마운트 — Trading PC WSL2 Ubuntu에서 **`chattr +i` 장중 immutable**, 장 마감 후 정책 디렉토리 unlock → commit → 장 개시 전 relock (systemd timer on 09:00/15:30 KST)
- **AR-SEC4:** 백업 암호화 — 외장 디스크 LUKS + S3 SSE-C (AES-256), 키는 OS Keychain에만 저장
- **AR-SEC5:** YubiKey 2FA — V1.0 MVP 제외, 자본 ≥ 1,000만 원 도달 시 SSH signing 키 하드웨어화 검토 (deferred)

**Communication & Internal Patterns (D12-D16):**

- **AR-COM1:** Cross-PC 통신 3-layer — 데이터: rsync over SSH (Trading PC pull 60초) / Heartbeat: Prometheus `blackbox_exporter` ICMP ping + HTTP 2중 체크 (5분 warn, 4h critical) / Control events: 없음 (단방향)
- **AR-COM2:** Intra-process DTO — in-memory Pydantic 2 객체 직접 참조 전달 (asyncio.Queue, bounded 1000), 디스크 영속은 Parquet (Arrow)
- **AR-COM3:** ErrorCode enum — `KIS_RATE_LIMIT`, `FEATURE_MISSING`, `LLM_TIMEOUT`, `CONFIDENCE_BELOW_THRESHOLD`, `DATA_STALE`, `HEARTBEAT_LOST`, `SLIPPAGE_EXCEEDED`, `POLICY_NOT_COOLED` — 구조화 JSON 로그 + Prometheus error rate 집계
- **AR-COM4:** Module version embedding — Hatchling build hook이 `git describe --always --dirty` → `athena._version.__commit__` 주입, DTO 자동 embed (`policy_version_git_sha`), 런타임 shell 호출 0
- **AR-COM5:** 큐 네이밍 — `<producer>_to_<consumer>_q` (예: `feature_to_alpha_q`, `alpha_to_orchestrator_q`), 오래된 메시지 drop + WARNING + counter 증가

**Architectural Boundaries (Import Hierarchy):**

- **AR-BND1:** Package import hierarchy (import-linter enforce): `athena-core` (leaf) ← `athena-feature-store` ← `athena-alpha-defense` + `athena-ops-defense` ← `athena-orchestrator` ← `athena-execution`
- **AR-BND2:** 역방향 import 금지 — `execution → orchestrator` 불가, `alpha_defense → execution` 불가, `core → 기타 athena-*` 불가

**Configuration Management:**

- **AR-CFG1:** `config/settings.toml` — p99 예산, rsync 주기, rate limit 등 비-보안 파라미터
- **AR-CFG2:** `config/universe.toml` — 감시 종목 (KOSPI200 + KOSDAQ150)
- **AR-CFG3:** `config/flag_registry.toml` — 52 veto flag ID 고정 리스트 (Change Control 필수, runtime 추가·삭제 금지)
- **AR-CFG4:** `config/policy.toml` — θ_entry, α/β/γ, M_regime, M_time — **F5 읽기전용 마운트 대상**
- **AR-CFG5:** `pydantic-settings 2.x` — 환경변수 + OS Keychain backend, `.env` 배제 런타임 enforce

**Observability Infrastructure:**

- **AR-OBS1:** Prometheus 단독 (Mimir/Thanos 미사용), 90일 metrics 보존, 월간 스냅샷 외장 백업
- **AR-OBS2:** Prometheus 메트릭 네이밍: `athena_<subsystem>_<metric>_<unit>`
- **AR-OBS3:** Alertmanager receivers: Telegram bot webhook + 카카오워크 webhook
- **AR-OBS4:** Grafana 대시보드: 8대 KPI 패널 + KPI 선언 조건 패널 + Anti-Ego events 패널 + L2 로거 uptime + Kill Switch 상태

**External Integrations:**

- **AR-EXT1:** KIS REST — python-kis, token-bucket 20 req/s, `EGW00201` 재시도 3회 + 지수 백오프
- **AR-EXT2:** KIS WebSocket — python-kis, 41 구독/세션, 재연결 자동 복구
- **AR-EXT3:** KIS 모의계좌 — 동일 adapter, `settings.environment="paper"`
- **AR-EXT4:** DART OpenAPI — 자체 rate limit, 공시 실시간
- **AR-EXT5:** 뉴스 피드 — RSS + HTTPS crawl, robots.txt 준수, 15 req/min default
- **AR-EXT6:** HyperCLOVA X / Solar Pro 2 — 비동기 only, 2s timeout, 1단계 XGBoost fallback
- **AR-EXT7:** pykrx — 일회성 OHLCV·VI 백필

**Backup Schedule (D23):**

| 대상 | 주기 | 위치 |
|---|---|---|
| Pre-Trade Ledger | real-time mirror | 외장 SSD (LUKS) |
| Parquet shards | 시간당 rsync | Trading PC |
| 전체 DuckDB | 주간 스냅샷 | 외장 SSD |
| 전체 시스템 이미지 | 월간 | 외장 SSD + S3 Object Lock |
| Ledger 월간 체인 해시 | 월간 | S3 Object Lock Compliance |

**Testing Requirements:**

- **AR-TEST1:** pytest + pytest-asyncio + pytest-xdist (병렬 실행)
- **AR-TEST2:** 결정론적 seed 고정 (PT-I2 요구)
- **AR-TEST3:** 과거 2건 실패 snapshot 회귀 (유리기판 A사 2025-11 / 바이오 C사 2023-12) — S_entry ±5% tolerance
- **AR-TEST4:** 5개 E2E 시나리오 (J1-J5) — Trading/Operator/Incident/Capital Gate
- **AR-TEST5:** 단위 테스트 co-located (`<module>/tests/`), 통합 테스트 `tests/integration/`

**Code Quality Tooling:**

- **AR-CQ1:** ruff (lint + import sort, flake8/isort 대체)
- **AR-CQ2:** black (formatter) 또는 ruff format
- **AR-CQ3:** mypy 또는 pyright (strict mode)
- **AR-CQ4:** pre-commit hook (F5 하드락 정신의 연장)
- **AR-CQ5:** secret scanner (CI gate 내장)

### UX Design Requirements

**N/A** — Athena V1.0은 headless backend service. 외부 공개 UI 없음. 사용자 인터페이스는 Grafana 대시보드 + Alertmanager 모바일 푸시 + CLI 도구로 구성되며, 관련 요구사항은 **Additional Requirements > Observability Infrastructure** (AR-OBS1-4) 및 FR47/FR18/FR53에 통합됨.

### FR Coverage Map

| FR | Epic | 소유 모듈/컴포넌트 |
|---|---|---|
| FR1 | Epic 1 | `scripts/l2_logger.py` + Parquet shard |
| FR2 | Epic 1 | `scripts/dart_crawler.py`, `scripts/news_crawler.py` |
| FR3 | Epic 2 | M1 Linguistic Certainty Scorer |
| FR4 | Epic 2 | M2 Narrative Age (Omori decay) |
| FR5 | Epic 2 | M3 Pre-Announcement Drift Z-score |
| FR6 | Epic 2 | M9 Time-of-Day Multiplier |
| FR7 | Epic 2 | M13 XGBoost + 비동기 LLM 2단계 |
| FR8 | Epic 2 | M14 Transfer Entropy Basket Gate |
| FR9 | Epic 2 | `orchestrator/s_entry.py` 곱셈 집계 |
| FR10 | Epic 3 | `orchestrator/decision.py` 이중 조건 |
| FR11 | Epic 2 | `orchestrator/explain.py` (M25) |
| FR12 | Epic 2 | `orchestrator/degrade.py` + 월간 missing rate |
| FR13 | Epic 3 | F1 Bargaining Detector |
| FR14 | Epic 3 | F1 fine-tune pipeline (250+ 라벨) |
| FR15 | Epic 3 | `orchestrator/firewall.py` 집계 |
| FR16 | Epic 3 | F5 읽기전용 마운트 통합 (infra는 Epic 1) |
| FR17 | Epic 3 | `f5/hash_chain.py` → anti_ego_events |
| FR18 | Epic 3 | Grafana anti_ego_events 패널 (완성은 Epic 7) |
| FR19 | Epic 4 | M19 2차 미분 감시 |
| FR20 | Epic 4 | M22 서버측 OCO Hard Stop |
| FR21 | Epic 4 | MVP: 이벤트 캘린더 alert (M16은 V1.1+) |
| FR22 | Epic 4 | 청산 이벤트 orders + Ledger 기록 |
| FR23 | Epic 5 | `ops_defense/slippage.py` tick 단위 실측 |
| FR24 | Epic 5 | slippage > 0.3% → S_entry × 0.5 discount |
| FR25 | Epic 5 | `ops_defense/portfolio.py` 3종목 상한 |
| FR26 | Epic 5 | `ops_defense/portfolio.py` 테마 중복 금지 |
| FR27 | Epic 5 | `ops_defense/data_quality.py` 뉴스 30s drop |
| FR28 | Epic 5 | `ops_defense/data_quality.py` NLP confidence neutral |
| FR29 | Epic 5 | `ops_defense/throttle.py` 취소·재주문 |
| FR30 | Epic 5 | `ops_defense/kill_switch/` 4층 state machine |
| FR31 | Epic 5 | Global CB 일일 -3% |
| FR32 | Epic 5 | Account CB MDD -8% |
| FR33 | Epic 5 | Session CB 3회 손절 |
| FR34 | Epic 5 | Symbol CB M22 연계 |
| FR35 | Epic 5 | heartbeat 4h auto-flatten (blackbox_exporter) |
| FR36 | Epic 5 | heartbeat 5분 push (Alertmanager) |
| FR37 | Epic 4 | Secondary Adapter 추상화 (MVP 경계만) |
| FR38 | Epic 6 | `execution/ledger/` Pre-Trade append-only |
| FR39 | Epic 6 | 월간 SHA-256 체인 해시 + 외장 백업 |
| FR40 | Epic 6 | §176 분당 상한·취소율 enforce |
| FR41 | Epic 6 | `kis_adapter.py` 단일 계좌 assertion (§17/§18) |
| FR42 | Epic 6 | `execution/tax/m_tax.py` 세후 계산 |
| FR43 | Epic 6 | 대주주 근접 경보 |
| FR44 | Epic 6 | 자본 임계 워크플로우 트리거 |
| FR45 | Epic 6 | 준법감시인 통지 이메일 템플릿 |
| FR46 | Epic 6 | OTP 공증 위임 체크리스트 |
| FR47 | Epic 1 + Epic 7 | 기본 uptime(1) + 완전 대시보드(7) |
| FR48 | Epic 7 | `core/metrics.py` Prometheus histogram |
| FR49 | Epic 7 | 8 KPI 대시보드 |
| FR50 | Epic 7 | KPI 선언 조건 패널 |
| FR51 | Epic 7 | `scripts/weekly_report.py` |
| FR52 | Epic 7 | `scripts/monthly_audit.py` missing rate |
| FR53 | Epic 8 | `scripts/f1_labeler.py` |
| FR54 | Epic 8 | `alpha_defense/f1/psi_drift.py` + paper 자동 전환 |
| FR55 | Epic 8 | `scripts/walk_forward_runner.py` |
| FR56 | Epic 8 | `scripts/bayesian_tuner.py` |
| FR57 | Epic 8 | `.github/workflows/policy-cooling-gate.yml` |
| FR58 | Epic 8 | 정책 변경 감사 로그 |

**검증:** 58 FR 전량 매핑 ✅ (FR47은 Epic 1에서 기본 uptime, Epic 7에서 완성)

## Epic List

### Epic 1: Foundation & Market Truth Capture

**Week 1 Day 1 기반 구축.** 프로젝트 bootstrap (`uv init` monorepo + 6 packages) + CI/CD 7단계 self-hosted runner + OS 분할 (Win11 Logger / WSL2 Ubuntu 24.04 Trading) + 읽기전용 마운트 systemd 타이머 + Ledger 초기 세그먼트 + OS Keychain 통합. L2 WebSocket 로거·DART·뉴스 크롤러 24/7 가동 시작.

**User Outcome:** "W1 Day 1부터 2년 L2 tick이 시간 비대칭 자산으로 축적되기 시작하고, 모든 후속 개발이 감사·보안·법률 요건을 충족한 기반 위에서 진행된다."

**FRs covered:** FR1, FR2, FR47(partial)
**NFRs emphasized:** NFR-P5, NFR-R1, NFR-R4, NFR-S1, NFR-S2, NFR-S5, NFR-M1, NFR-M4, NFR-I2, NFR-I3, NFR-O1
**AR covered:** AR-ST1-4, AR-INF1-6, AR-DATA1-7, AR-SEC1-5, AR-CFG1-5, AR-BND1-2, AR-COM1-5, AR-EXT2, AR-EXT4-5, AR-TEST1-2, AR-CQ1-5

### Epic 2: Alpha Defense — 52-Flag Veto Gate

**M1-M14 핵심 방어 모듈 + S_entry 수식 + 거부 설명.** 언어 확실성(M1)·서사 나이 Omori decay(M2)·공시전 드리프트 Z-score(M3)·시간대 multiplier(M9)·XGBoost+비동기 LLM 2단계(M13)·Transfer Entropy 밸류체인 바스켓(M14) 구현. 52 veto flag 곱셈형 S_entry 집계와 M25 거부 설명 리포트.

**User Outcome:** "유니버스 350종목에 대해 52-flag 곱셈형 S_entry 스코어가 실시간으로 산출되며, 거부된 진입은 어떤 gate가 차단했는지 이유를 받는다."

**FRs covered:** FR3-FR9, FR11, FR12
**NFRs emphasized:** NFR-P1, NFR-P2, NFR-P3, NFR-P4, NFR-I5, NFR-A4(missing rate)
**AR covered:** AR-CFG3 (52 flag 고정 레지스트리), AR-EXT6 (LLM 2단계), AR-TEST3 (과거 2건 snapshot 회귀)

### Epic 3: Anti-Ego Firewall & Entry Authorization

**F1 흥정 언어 감지 + F5 읽기전용 마운트 + 이중 조건 최종 gate.** 본인 일지에서 250건+ 라벨 fine-tune한 F1 KB-BERT 분류기 + F5 장중 `chattr +i` 통합 + Firewall 집계 + `S_entry > θ_entry AND Firewall=1` 이중 조건 gate + anti_ego_events append-only 로그.

**User Outcome:** "내 흥정 언어는 실시간 감지되고, 장중 어떤 override도 물리적으로 불가능하며, 이중 조건을 통과한 주문 의도만 하류로 넘어간다."

**FRs covered:** FR10, FR13-FR18
**NFRs emphasized:** NFR-R5, NFR-S3, NFR-S4, NFR-A3 (override 로그 100% 완전성)
**AR covered:** AR-SEC3 (chattr +i), Anti-Ego 패러렐 파이프라인 패턴

### Epic 4: Execution & Hard-Locked Exit

**KIS Primary Adapter + Secondary 추상화 + 서버측 OCO Hard Stop + M19 2차 미분 감시.** python-kis 래퍼로 KIS REST/WebSocket 연동, OCO 이중화로 override 물리 차단, 모든 청산 이벤트 orders/Ledger 기록.

**User Outcome:** "승인된 주문이 KIS로 실행되고, M22 서버측 OCO 이중화가 내가 override할 수 없는 손절을 보장한다. 증권사 교체 seam이 Secondary Adapter 추상화로 준비되어 있다."

**FRs covered:** FR19-FR22, FR37
**NFRs emphasized:** NFR-I1, NFR-I2, NFR-I4, NFR-I5, NFR-M5
**AR covered:** AR-EXT1-3 (KIS), AR-COM3 (ErrorCode enum)

### Epic 5: Operational Defense & Risk Kill Switch

**운영 품질 방어 + 4층 Circuit Breaker + heartbeat 자동 청산.** 슬리피지 tick 단위 실측/discount, 3종목·테마 중복 상한, 뉴스 30s drop, NLP confidence degrade, 취소·재주문 throttle, Global(-3%)/Account(-8% MDD)/Session(3회 손절)/Symbol(M22) 4층 CB, blackbox_exporter 기반 heartbeat 5분 push + 4h auto-flatten.

**User Outcome:** "운영 품질 저하와 시장 shock에 대한 독립적 자동 방어선이 작동하여 파산 시나리오를 차단하고, 장애 상황에도 시스템이 자동 청산으로 안전 상태로 수렴한다."

**FRs covered:** FR23-FR36
**NFRs emphasized:** NFR-R2, NFR-R3, NFR-I5, NFR-O3 (Critical 알림)
**AR covered:** AR-COM1 (blackbox_exporter heartbeat), 4층 CB 독립 state machine 패턴

### Epic 6: Compliance, Audit & Capital Triggers

**Pre-Trade Ledger SHA-256 체인 + 자본시장법 자동 enforce + 자본 임계 워크플로우.** append-only Ledger에 모든 주문 의도·체결·거부 기록, 월간 SHA-256 체인 해시 외장 백업, §176 분당·취소율 하드 제한, FR41 단일 계좌 assertion(§17/§18), M_tax 세후 계산, 대주주 경보, 자본 1,000만 원 도달 시 준법감시인 통지·OTP 공증 위임 자동화.

**User Outcome:** "모든 의사결정이 tamper-evident로 기록되고, 자본시장법(§17/§18/§176/§178/§178-2) 요건이 자동 enforce되며, 자본 임계 도달 시 컴플라이언스 워크플로우가 자동 트리거된다."

**FRs covered:** FR38-FR46
**NFRs emphasized:** NFR-S3, NFR-S6, NFR-A1, NFR-A2 (영구 보존), NFR-A4
**AR covered:** AR-DATA6 (Ledger 2-target 백업), AR-SEC4 (LUKS + S3 SSE-C)

### Epic 7: Observability & Reporting

**Grafana 8-KPI 대시보드 + 주간·월간 자동 리포트.** Prometheus histogram 기반 시그널 레이턴시 p99 측정, 8대 KPI(월 수익률, Deflated Sharpe, MDD, 설거지 회피율, 이벤트 손실 경감, p99, override 로그 완전성, F1 PSI) 실시간 누적, KPI 선언 조건(n≥6개월, 50+ trades, bootstrap CI>0) 패널, 주간 거래 요약 리포트, 월간 compliance·missing rate 자기감사.

**User Outcome:** "시스템 건강·수익성·규정 준수 상태를 Grafana 대시보드와 자동 리포트로 전면 관측하며, KPI 선언 가능 시점을 실시간으로 파악한다."

**FRs covered:** FR47(complete), FR48-FR52
**NFRs emphasized:** NFR-O1, NFR-O2, NFR-O3, NFR-O4 (asyncio trace ID), NFR-A4
**AR covered:** AR-OBS1-4 (Prometheus/Alertmanager/Grafana)

### Epic 8: Model Lifecycle & Policy Change Gate

**F1 재학습 + PSI 감시 + walk-forward + Bayesian 튜닝 + 72h cooling gate enforce.** 주간 F1 라벨링 CLI, PSI > 0.2 시 자동 paper-only 전환, 공매도 재개(2025-03-31) 전후 레짐 분리 walk-forward 백테스트, Bayesian + walk-forward θ_entry·α/β/γ 튜닝, CI 파이프라인의 72h cooling + Paper 재검증 marker 물리 enforce, 정책 변경(누가·언제·무엇·왜) git signed commit + 감사 로그 복제.

**User Outcome:** "모델과 정책을 감사 가능한 경로로만 업데이트할 수 있으며, 장중 ad-hoc 변경이 물리적으로 불가능하다. PSI 드리프트는 paper-only 안전 상태로 자동 전환된다."

**FRs covered:** FR53-FR58
**NFRs emphasized:** NFR-R5 (72h cooling), NFR-A5 (git signed), NFR-M3 (Change Control)
**AR covered:** AR-INF3-4 (self-hosted runner + CI/CD 7단계), AR-SEC2 (SSH signing)

---

## Epic 1: Foundation & Market Truth Capture

**Epic Goal:** Week 1 Day 1 기반 구축. 프로젝트 bootstrap (uv monorepo) + CI/CD 7단계 self-hosted runner + OS 분할 (Win11 Logger / WSL2 Trading) + 읽기전용 마운트 systemd + Ledger 초기 세그먼트 + L2 WebSocket 로거·DART·뉴스 크롤러 24/7 가동. W1 Day 1부터 2년 L2 tick이 시간 비대칭 자산으로 축적되기 시작하고, 모든 후속 개발이 감사·보안·법률 요건을 충족한 기반 위에서 진행된다.

### Story 1.1: 프로젝트 Bootstrap — uv Monorepo Scaffold

As a Developer (Khuk0, Week 1 Day 1),
I want to initialize the Athena monorepo with uv + 6 package skeletons + toolchain enforcement,
So that all subsequent development has a reproducible, audit-compliant foundation.

**Acceptance Criteria:**

**Given** 빈 git repository와 Windows 11 Logger PC 호스트
**When** `uv init --package athena --python 3.13` + 6 package scaffold 생성 스크립트 실행
**Then** `packages/athena-core`, `athena-feature-store`, `athena-alpha-defense`, `athena-ops-defense`, `athena-orchestrator`, `athena-execution` 6개 package가 독립 `pyproject.toml` + semver `0.1.0` 상태로 존재
**And** 각 package는 own `tests/` subdirectory 포함

**Given** 6 package scaffold 완료
**When** `uv add python-kis polars duckdb pydantic uvloop keyring pydantic-settings` + `uv add --dev pytest pytest-asyncio pytest-xdist ruff mypy pre-commit import-linter`
**Then** `uv.lock` 생성 + git 커밋 필수 (NFR-A5 감사 요건의 물리 구현)
**And** `uv run python -c "import athena"` 성공

**Given** `.importlinter` 설정 (AR-BND1)
**When** CI에서 import-linter 실행
**Then** 계층 위반 (예: `core` → `execution` import) 발견 시 FAIL
**And** 역방향 import (execution → orchestrator, alpha_defense → execution, core → 기타) 발견 시 FAIL

**Given** pre-commit hook 설정
**When** `git commit` 시도
**Then** ruff (lint + format), mypy strict, secret scanner 4개 hook이 자동 실행됨
**And** 실패 시 commit 차단

**Given** Hatchling build hook 구현
**When** 어느 package `uv build` 실행
**Then** `git describe --always --dirty` 값이 `athena._version.__commit__` 에 주입됨 (AR-COM4)
**And** 런타임 shell 호출 overhead 0

### Story 1.2: 환경 & Secrets Infrastructure — WSL2 + OS Keychain + SSH Signing

As Khuk0 operating Trading PC,
I want WSL2 Ubuntu 환경 + OS Keychain 기반 secret 관리 + git SSH signing을 확립하여,
So that 모든 secret과 policy 변경이 첫 commit부터 OS-level primitives로 관리되고 `.env` 유출 가능성이 원천 차단된다.

**Acceptance Criteria:**

**Given** Windows 11 Trading PC (현재 호스트)
**When** WSL2 + Ubuntu 24.04 LTS 설치 + systemd 활성화 + SSH key 생성
**Then** `wsl -l -v` 에 Ubuntu-24.04 Running 표시
**And** `systemctl --user` 동작 (systemd 자식 프로세스 관리 가능)

**Given** Python `keyring` (jaraco) 설치
**When** `athena.core.keyring_client.get_secret("KIS_APP_KEY")` 호출
**Then** Windows Credential Manager (wincred) 또는 Linux Secret Service 에서 auto-backend 경유 fetch
**And** Key 미등록 시 구체적 `MissingSecretError("KIS_APP_KEY not in OS Keychain")` raise

**Given** `pydantic-settings` 기반 `athena.core.settings.Settings` 클래스
**When** 프로세스 시작 시 `.env` 파일 존재 감지
**Then** 즉시 `SystemExit(".env usage forbidden by NFR-S1")` 발생
**And** Settings는 key 이름만 참조, 실제 값은 keyring에서 lazy fetch

**Given** git 2.34+ 설치 + SSH key 등록
**When** `git commit -S` 실행
**Then** SSH key 기반 서명 commit 생성
**And** `git log --show-signature` 으로 검증 통과

**Given** Logger PC ↔ Trading PC 로컬 네트워크
**When** Trading PC에서 `ssh logger-pc` 시도
**Then** SSH key 인증 성공 (password prompt 없음)
**And** 외부 네트워크에서 접근 시 방화벽 차단 (NFR-S5)

### Story 1.3: Self-Hosted CI/CD Pipeline — 7단계 Gate

As Khuk0 changing policy 또는 code,
I want CI 파이프라인이 72h cooling + Paper 재검증 포함 7단계 gate를 enforce하여,
So that 어떤 변경도 cooling과 재검증을 bypass할 수 없고, 인간 규율 실패 지점이 물리적으로 제거된다.

**Acceptance Criteria:**

**Given** Trading PC WSL2 Ubuntu에 GitHub Actions self-hosted runner 등록
**When** `.github/workflows/ci.yml` 에 새 PR 이벤트 trigger 설정
**Then** PR 열림 시 runner가 자동 작업 수령

**Given** CI 파이프라인 7단계 정의
**When** PR job 실행
**Then** 단계 순서 보장: (1) pre-commit (2) pytest unit — seed 고정 (3) pytest integration mock KIS (4) snapshot 회귀 placeholder (5) walk-forward smoke placeholder (6) 72h cooling gate (7) Paper 재검증 marker 확인
**And** 모든 단계 통과 시에만 merge 허용

**Given** `scripts/check_cooling.py` 구현
**When** 직전 merge 타임스탬프가 현재로부터 72h 미만
**Then** 6단계 job이 `POLICY_NOT_COOLED` error code로 fail
**And** Alertmanager Medium 알림 발송

**Given** 과거 2건 실패 snapshot reference 데이터 (유리기판 A사 2025-11, 바이오 C사 2023-12) — MVP 초반엔 fixture placeholder
**When** 4단계 snapshot 회귀 실행 (Epic 2 완료 후 실 fixture 주입)
**Then** S_entry 값이 reference 대비 ±5% 이내
**And** 초과 시 FAIL, 코드 변경 회귀 증거 로 간주

**Given** 7단계 모두 통과한 상태
**When** prod deploy job
**Then** GitHub environment protection rule 로 수동 승인 대기
**And** paper 환경은 수동 승인 없이 auto deploy

### Story 1.4: DuckDB + Parquet Shard + rsync Data Pipeline

As Khuk0's system needing cross-PC data flow,
I want Logger → Trading PC 단방향 데이터 파이프라인 (Parquet shard + rsync)을 구축하여,
So that DuckDB single-writer 제약을 해결하면서 NFR-R4 물리 이중화를 만족한다.

**Acceptance Criteria:**

**Given** Logger PC 빈 상태
**When** `packages/athena-feature-store/` 초기화 + `features_logger.duckdb` 생성
**Then** `ticks`, `quotes`, `news` 3개 테이블 스키마 생성 (이 테이블은 이 스토리에서만 생성)
**And** 모든 테이블에 `user_id` 컬럼 포함 (NFR-M4 seam)

**Given** tick 데이터가 DuckDB `ticks` 테이블에 존재
**When** `scripts/export_parquet_shard.py` 매시간 실행
**Then** `/data/parquet/year=2026/month=04/day=21/hour=09/symbol=005930.parquet` 형식 파일 생성
**And** 전 시간 파일은 절대 수정되지 않음 (append-only shard)

**Given** Trading PC WSL2에 `athena-logger-sync.service` + 60초 주기 systemd timer
**When** timer 발동
**Then** `rsync -a logger-pc:/data/parquet/ /data/parquet/` 실행
**And** 네트워크 transient 장애 시 다음 주기 재시도, 손실 shard 없음 (idempotent)

**Given** Trading PC `decisions.duckdb` (빈 상태)
**When** `athena-orchestrator` 가 `read_parquet('/data/parquet/ticks/**/*.parquet')` external scan
**Then** 쿼리 p95 < 500ms (NFR-P4) — 350종목 × 2년 L2 기준 (초기엔 데이터 부족하므로 smoke만)
**And** Trading PC DuckDB 쓰기는 `modules_output`, `decisions`, `orders`, `anti_ego_events`, `labels_f1` 테이블만 (ticks/quotes/news는 read-only external scan)

**Given** rsync lag 모니터링 Prometheus metric
**When** rsync 주기가 120초 초과
**Then** High 알림 발송 (데이터 파이프라인 critical path)

### Story 1.5: Pre-Trade Ledger 초기 세그먼트 & SHA-256 체인

As Khuk0 needing legally-compliant audit trail from Week 1,
I want Pre-Trade Ledger를 append-only SHA-256 체인 + 2-target 백업으로 초기화하여,
So that 모든 미래 의사결정이 법률(§178-2) 요구 수준의 tamper-evident 기록에 남는다.

**Acceptance Criteria:**

**Given** Trading PC `decisions.duckdb`
**When** `pre_trade_ledger` 테이블 초기화
**Then** 컬럼: `id` (PK), `user_id`, `event_type`, `payload_json`, `prev_hash`, `this_hash`, `policy_version_git_sha`, `created_at_utc`, `param_hash`
**And** UPDATE/DELETE 물리 차단 (DuckDB view + trigger pattern)

**Given** ledger 초기 genesis entry
**When** 첫 삽입
**Then** `prev_hash=NULL`, `this_hash=SHA256(payload_json || policy_version_git_sha)`
**And** 다음 entry의 `prev_hash=이전.this_hash` 체인 유지

**Given** 월말 체인 해시 계산 job
**When** 매월 1일 03:00 KST 실행
**Then** 지난 월 모든 entry를 id 순 정렬하여 `segment_hash = SHA256(prev_segment_hash || sorted_ids_hash || policy_version_git_sha)` 계산
**And** 외장 SSD LUKS + S3 Object Lock 양쪽에 `segment_2026_04.hash` 저장

**Given** 외장 SSD 파티션 미초기화
**When** `scripts/init_external_backup.sh` 실행
**Then** LUKS 암호화 + ext4 포맷 + `/mnt/external` 마운트 (systemd auto)
**And** LUKS 키는 OS Keychain에만 저장 (AR-SEC4)

**Given** S3 bucket (또는 Naver Cloud Object Storage) 미초기화
**When** `scripts/init_s3_object_lock.py` 실행
**Then** bucket이 Object Lock Compliance 모드 활성화 + 최소 5년 retention
**And** 객체 키 네이밍: `ledger/user_id=1/year=2026/month=04/segment_hash.json`

**Given** `scripts/verify_ledger.py` 정기 검증 (월간 CI job)
**When** 실행
**Then** 전 월 `segment_hash` ↔ 현 월 genesis `prev_hash` 연속성 확인
**And** 불일치 시 Critical 알림 + Global CB 발동 (Epic 5 연동 hook 준비)

### Story 1.6: F5 읽기전용 마운트 systemd Timer Infrastructure

As the Athena system entering 장중,
I want `config/policy.toml` + `config/flag_registry.toml` 가 09:00 KST 자동 immutable / 15:30 KST 자동 mutable 되어,
So that F5 Parameter Hard-Lock이 application code가 아닌 OS primitives로 enforce되어 우회 불가능해진다.

**Acceptance Criteria:**

**Given** Trading PC WSL2 Ubuntu + `config/` 디렉토리
**When** `chattr +i config/policy.toml` 실행
**Then** root 계정도 파일 수정 시도 시 "Operation not permitted"
**And** `chattr -i` 로만 해제 가능

**Given** `athena-readonly-mount.service` + `.timer` 정의
**When** systemd timer 09:00 KST trigger (월-금, 공휴일 리스트 제외)
**Then** `chattr +i config/policy.toml config/flag_registry.toml` 자동 실행
**And** 발동 로그 `anti_ego_events` 연동 hook 준비 (실 로그는 Epic 3에서 완성)

**Given** 동일 서비스
**When** 15:30 KST trigger
**Then** `chattr -i` 실행 → 정책 수정 가능 상태
**And** 장 마감 후 git commit + 72h cooling window 시작

**Given** 장중 (immutable 상태)
**When** 사용자, git revert, 또는 편집기가 정책 파일 수정 시도
**Then** "Operation not permitted" 에러 반환
**And** inotify watcher 가 시도 이벤트 로그에 기록 (hook만 준비, 로그 구조는 Epic 3)

**Given** 공휴일 또는 주말
**When** systemd timer 09:00 KST
**Then** 실행 skip (한국 공휴일 캘린더 참조)
**And** 정책 디렉토리는 mutable 유지

### Story 1.7: L2 호가창 WebSocket 로거 24/7 (FR1)

As Khuk0,
I want L2 호가창 데이터가 KIS WebSocket에서 Week 1 Day 1부터 24/7 수집되어,
So that 2년 Time-Travel Rights 데이터 자산 축적이 즉시 시작된다 — 이 지연은 V1.1+ 해자 지연과 동일하다.

**Acceptance Criteria:**

**Given** Logger PC Windows 11 + python-kis 설치 + KIS WebSocket key (OS Keychain 저장)
**When** `scripts/l2_logger.py` 시작
**Then** `config/universe.toml` 감시 유니버스 (초기 KOSPI200 + KOSDAQ150 선별) 대해 41건/세션 상한 준수 구독 (NFR-I2)
**And** L2 10호가 + 체결 tick 실시간 수신

**Given** `athena-l2-logger` NSSM 서비스
**When** Windows 부팅
**Then** 24/7 자동 시작, crash 시 NSSM 자동 재시작
**And** 구조화 JSON 로그 `logs/l2_logger.log` 에 기록

**Given** WebSocket 연결 상태
**When** "No close frame received" 또는 네트워크 단절 이벤트
**Then** 자동 재연결 + 구독 자동 재등록 (python-kis reconnect 기능 활용)
**And** `athena_l2_reconnect_total` Prometheus counter 증가

**Given** tick 수신
**When** `features_logger.duckdb` `ticks` 테이블 INSERT
**Then** 컬럼: `user_id`, `symbol`, `timestamp_kst`, `bid_prices[10]`, `bid_volumes[10]`, `ask_prices[10]`, `ask_volumes[10]`, `trade_price`, `trade_volume`, `trade_side`
**And** `athena_l2_throughput_signals_per_min` gauge 실시간 업데이트

**Given** Logger uptime 모니터링 job
**When** 월간 uptime 계산
**Then** ≥ 99% (NFR-R1), 장중 기준 월 downtime < 6시간 30분
**And** 미달 시 paper-only 모드 자동 전환 플래그 set (Epic 5에서 전환 로직 완성)

### Story 1.8: DART + 뉴스 피드 실시간 크롤러 (FR2)

As Khuk0's Alpha Defense 파이프라인,
I want DART 공시 + 5개 뉴스 소스 (네이버·다음·연합·매경·한경)가 Feature Store에 정규화 저장되어,
So that M1/M2/M3 NLP 모듈이 분석할 substrate가 첫 주부터 쌓인다.

**Acceptance Criteria:**

**Given** DART OpenAPI key (OS Keychain 저장) + `scripts/dart_crawler.py`
**When** 서비스 시작
**Then** 신규 공시 실시간 수신 (polling 또는 webhook 지원 가능 방식)
**And** `features_logger.duckdb` `news` 테이블에 `source='dart'`, `headline`, `body`, `published_at_kst`, `fetched_at_kst`, `user_id` 저장

**Given** 5개 뉴스 소스별 RSS feed URL + HTTPS 크롤러
**When** `scripts/news_crawler.py` 실행
**Then** 각 소스 robots.txt 준수 (Python `robotparser`)
**And** 자체 rate limit 15 req/min default (NFR-I3), 소스별 독립

**Given** 신규 뉴스 수신
**When** `news` 테이블 insert
**Then** `source` 컬럼 값이 {dart, naver, daum, yonhap, maekyung, hankyung} 중 하나
**And** 시간당 Parquet export (Story 1.4)에 포함되어 Trading PC로 sync됨

**Given** 외부 소스 일시 장애
**When** HTTP 5xx 3회 연속 + 지수 백오프 실패
**Then** 해당 소스만 degrade (graceful, NFR-I5), 타 소스 영향 없음
**And** `athena_news_source_error_total{source="..."}` Prometheus counter 증가 + Medium 알림

**Given** NSSM 서비스 `athena-dart-crawler`, `athena-news-crawler`
**When** 서비스 상태 확인
**Then** 두 서비스 Windows 부팅 시 auto 시작
**And** Story 1.9의 기본 uptime 대시보드에 표시됨

### Story 1.9: Observability Stack + 기본 uptime 대시보드 (FR47 partial)

As Khuk0,
I want Prometheus + Grafana + Alertmanager stack이 구동되고 "Foundation Health" 대시보드와 heartbeat 알림이 작동하여,
So that Week 1부터 Logger PC + Trading PC 상태를 실시간 관측할 수 있다.

**Acceptance Criteria:**

**Given** Trading PC WSL2 Ubuntu
**When** `prometheus.service`, `grafana-server.service`, `alertmanager.service` systemd 등록 + boot 활성화
**Then** 3개 서비스 auto 시작
**And** Grafana UI `http://localhost:3000` 접근 가능, admin 초기 password는 OS Keychain

**Given** `blackbox_exporter` 설정 (Logger PC ICMP + HTTP status endpoint 체크)
**When** 5초 주기 scrape
**Then** Prometheus 에 `athena_heartbeat_last_success_timestamp_seconds` 메트릭 저장
**And** 지연 5분 시 Alertmanager High 알림 (Telegram/카카오워크 push)
**And** 지연 4h 시 Critical 알림 + `athena-auto-flatten.service` 트리거 hook (실 청산 로직은 Epic 5)

**Given** Alertmanager receivers 설정 (Telegram bot token + 카카오워크 webhook URL, OS Keychain)
**When** 각 receiver 테스트 알림
**Then** 실제 모바일에 수신 확인
**And** Critical/High/Medium 3단 라우팅 정상 작동 (NFR-O3)

**Given** Grafana "Foundation Health" 대시보드
**When** 사용자 접근
**Then** 패널: L2 로거 uptime %, DART/뉴스 크롤러 uptime %, Heartbeat 상태, Parquet shard 최신 시각, rsync lag, 외장 SSD free space, DuckDB 파일 크기
**And** FR47 partial 충족 (Kill Switch·KPI 패널은 Epic 5/7에서 완성)

**Given** `athena-core/logging.py` 구조화 JSON 로거 (AR-OBS2 네이밍 규칙)
**When** 모듈에서 logger 사용
**Then** 모든 로그가 `{"ts": ..., "level": ..., "module": ..., "trace_id": ..., "error_code": ..., "msg": ...}` JSON 형식 (NFR-O1)
**And** 로컬 파일 + 주간 외장 백업 rotation (Story 1.10 활용)

### Story 1.10: Backup Schedule Automation (5-target)

As Khuk0,
I want 5-target 백업 schedule이 systemd timer로 자동 실행되어,
So that 운영 데이터(Parquet, DuckDB, Ledger, 시스템 이미지)가 수동 개입 없이 보호된다.

**Acceptance Criteria:**

**Given** systemd timer `athena-backup-hourly.timer`
**When** 매시간 실행
**Then** Story 1.4의 rsync pull job이 hourly basis로 동작
**And** `athena_backup_parquet_last_success_ts` Prometheus gauge 업데이트

**Given** systemd timer `athena-backup-weekly.timer`
**When** 매주 일요일 02:00 KST
**Then** `features_logger.duckdb` 및 `decisions.duckdb` 스냅샷이 외장 SSD LUKS `/mnt/external/weekly/` 로 복제
**And** 1년 초과 주간 스냅샷 자동 삭제 (외장 SSD 용량 관리)

**Given** systemd timer `athena-backup-monthly.timer`
**When** 매월 1일 03:00 KST
**Then** (a) 전체 시스템 이미지 외장 SSD + S3 Object Lock 업로드
**And** (b) Story 1.5의 Ledger 월간 체인 해시 계산 + S3 Object Lock 업로드
**And** (c) 로그 파일 외장 백업 rotation

**Given** 외장 SSD 미연결 또는 S3 인증 실패
**When** 백업 timer 실행
**Then** Critical 알림 (backup 실패 = 법률 리스크)
**And** 재시도 3회 (지수 백오프) 후 `athena_backup_consecutive_failures` counter 증가

**Given** 외장 SSD free space 모니터링
**When** free space < 20% 또는 < 100GB
**Then** High 알림 발송
**And** 2TB 초과 (Raw L2 Parquet 영구 보존) 시에도 경보 (용량 산정 재검토 필요)

---

## Epic 2: Alpha Defense — 52-Flag Veto Gate

**Epic Goal:** M1-M14 핵심 방어 모듈 + S_entry 곱셈 집계 수식 + 거부 설명을 구축한다. 52 veto flag 레지스트리 고정과 과거 2건 실패 snapshot fixture 주입으로 출발하여, 언어 확실성(M1)·서사 나이(M2)·공시 전 drift(M3)·시간대(M9)·XGBoost+비동기 LLM(M13)·밸류체인 TE(M14) 6개 모듈을 독립 구현한 뒤, `S_entry = 1[¬HardKill] · (αN+βV+γO) · Π G_i · M_regime · M_time` 수식으로 집계하고 end-to-end p99 < 5초(NFR-P1)를 실측 검증한다. 진입 거부 시 M25 설명 리포트 자동 생성과 결측 flag neutral degrade + 월간 missing rate 계산(NFR-A4 연계)까지 포함한다. 유니버스 350종목에 대해 52-flag 곱셈형 S_entry 스코어가 실시간 산출되며, 거부된 진입은 어떤 gate가 차단했는지 이유를 받는다.

### Story 2.1: 52 Flag Registry 고정 + Snapshot Fixture 주입

As Khuk0's Alpha Defense 파이프라인,
I want `config/flag_registry.toml` 에 52 veto flag ID를 불변 고정하고 과거 2건 실패 사례의 실 데이터 snapshot fixture를 주입하여,
So that 모든 후속 Alpha Defense 모듈이 고정된 flag namespace로 개발되고, Epic 1 Story 1.3의 CI Step 4 placeholder가 실 데이터 회귀로 전환된다.

**Acceptance Criteria:**

**Given** `config/flag_registry.toml` 미작성 상태
**When** 52개 flag ID + 소유 모듈(M1~M14, F1/F5, HardKill 그룹) + 한글 설명 + default(0 또는 1) 컬럼 작성
**Then** 52개 entry 유일성 보장 (중복 ID FAIL)
**And** AR-CFG3 준수: runtime 추가·삭제 금지 (pydantic frozen config + import-linter 규칙), 변경은 Change Control 1건 소모 (NFR-M3)

**Given** 유리기판 A사 2025-11 실패 사례 Raw 데이터 (KIS/DART 백필)
**When** 사건 전후 5영업일 구간 L2 tick + 뉴스/공시를 `tests/fixtures/snapshot/2025-11-glass-a/{ticks,news,events}.parquet` 로 저장
**Then** 총 30-60MB 범위 Parquet 파일 3개 + `README.md` (출처·라이선스 명시)
**And** `tests/fixtures/snapshot/2025-11-glass-a/reference.toml` 에 reference S_entry 값, 통과/실패 flag 목록, 당시 policy_version_git_sha 기록

**Given** 바이오 C사 2023-12 실패 사례
**When** 동일 구조로 `tests/fixtures/snapshot/2023-12-bio-c/` 저장
**Then** 공매도 재개(2025-03-31) 이전 레짐 데이터로 보존 (AR-TEST3 + FR55 레짐 분리 seam)
**And** fixture 무결성 pytest `tests/fixtures/test_integrity.py` 통과 (row count, 컬럼 스키마, 시간 범위)

**Given** Epic 1 Story 1.3의 CI Step 4 snapshot 회귀 placeholder
**When** `tests/snapshot/test_s_entry_regression.py` 본 구현 (이번 Story에서는 flag_registry 스펙 + fixture 로딩까지, 실 S_entry 계산은 Story 2.8에서 완성)
**Then** fixture 로딩 + flag_registry 참조 + 결정론적 seed(AR-TEST2) 실행 경로만 검증
**And** CI Step 4 job error_code `SNAPSHOT_FIXTURE_MISSING` 제거 (placeholder → real fixture)

**Given** `athena-alpha-defense/src/fixtures.py` 로딩 유틸
**When** `load_snapshot("2025-11-glass-a")` 호출
**Then** DuckDB in-memory에 3개 테이블 주입, 쿼리 p95 < 500ms (NFR-P4)
**And** `reference.toml` 의 S_entry 값·flags가 `SnapshotFixture` Pydantic DTO로 반환

### Story 2.2: M1 Linguistic Certainty Scorer (KB-BERT)

As Khuk0's Alpha Defense 파이프라인,
I want KB-BERT 로컬 추론 기반 M1 모듈이 뉴스 문장의 언어적 확실성을 0-1 스코어로 산출하여,
So that 52 flag 중 confidence 관련 flag들이 정량 평가되고, 근거 약한 뉴스 신호는 하류로 흘러가지 않는다.

**Acceptance Criteria:**

**Given** KB-BERT finance 사전학습 모델 weight (로컬 저장, OS Keychain credential 없이 로드)
**When** `athena-alpha-defense/m1/certainty.py` 초기화 + `transformers` 파이프라인 설정
**Then** CPU/GPU auto-detect, GPU 사용 가능 시 CUDA 활성화
**And** 모델 버전 해시가 `modules_output` DTO에 `module_version="M1.v{semver}+{git_sha8}"` 형식 embed (NFR-M1, NFR-M2, AR-COM4)

**Given** 뉴스 headline + body 텍스트 입력
**When** `m1.score(text: str) -> float` 호출
**Then** 0.0~1.0 float 반환 (재현성: 동일 text → 동일 score ±0.001)
**And** Prometheus histogram `athena_m1_inference_duration_seconds` p99 < 100ms (NFR-P2, 1000건 표본)

**Given** `features_logger.duckdb` `news` 테이블에서 batch 처리
**When** M1 batch 실행
**Then** 결과 `modules_output` 테이블 insert: `(user_id, news_id, module='M1', score, timestamp_kst, policy_version_git_sha)`
**And** 동일 `(user_id, news_id, module)` 중복 insert 방지 (UNIQUE 제약 + idempotent upsert)

**Given** 모델 confidence 임계값 미만 (예: logits softmax max < 0.3)
**When** M1 score 호출
**Then** error_code `CONFIDENCE_BELOW_THRESHOLD` 로그(AR-COM3) + flag neutral(1) degrade 대상 표식 반환 (실 degrade 취합은 Story 2.10)
**And** `athena_m1_low_confidence_total` counter 증가

**Given** Story 2.1의 snapshot fixture 2건
**When** 각 fixture 뉴스 feed 전체 M1 스코어링
**Then** reference score 대비 ±0.05 이내 (모든 뉴스 건)
**And** pytest `tests/snapshot/test_m1_certainty.py` 통과, CI Step 4 통합

### Story 2.3: M2 Narrative Age — Omori Law Decay

As Khuk0's Alpha Defense 파이프라인,
I want 동일 서사의 생애주기(신규→피크→소진)를 Omori law decay로 추적하는 M2 모듈을 확보하여,
So that 이미 소진된 서사에 뒤늦게 진입하는 "늦은 뉴스" 시그널이 자동 차단된다.

**Acceptance Criteria:**

**Given** `athena-alpha-defense/m2/narrative_age.py` 구현 + 뉴스 embedding 모델 (KB-BERT CLS token 또는 `ko-sroberta`)
**When** 신규 뉴스 도착 시 기존 cluster 대비 cosine similarity 계산
**Then** similarity ≥ threshold(0.85) 시 기존 cluster 편입, 미만이면 새 cluster 생성 + `birth_timestamp_kst` 기록
**And** cluster 테이블 `narrative_clusters(user_id, cluster_id, embedding, birth_timestamp_kst, last_update_kst)` 생성

**Given** cluster 존재 + Omori law 파라미터 $rate(t) = K / (t + c)^p$ 정의 (K, c, p from `config/policy.toml`)
**When** M2 score 요청
**Then** 0.0~1.0 반환 (t=0 최대, t→∞ 0에 점근), float 정밀도
**And** K/c/p는 F5 읽기전용 마운트 대상 (AR-CFG4), 장중 수정 시도 시 "Operation not permitted"

**Given** 서사 소진 기준 score < 0.1
**When** 해당 cluster 소속 뉴스로 진입 시도
**Then** 52 flag 중 `narrative_fresh` flag = 0 (veto)
**And** M25 리포트(Story 2.9)에 "narrative_age={val}, cluster_id={id}, birth={ts}" 전달 hook 준비

**Given** 뉴스 1000건/분 batch 처리
**When** M2 cluster 업데이트 + score 계산
**Then** batch 처리 latency p95 < 500ms (NFR-P4, DuckDB 쿼리 기준), 350종목 동시
**And** `athena_m2_cluster_count` gauge + `athena_m2_throughput_signals_per_min` gauge

**Given** 뉴스 text 결측 또는 embedding 실패
**When** M2 score 호출
**Then** flag neutral(1) degrade 표식 반환 + error_code `FEATURE_MISSING` (NFR-I5, AR-COM3)
**And** `athena_m2_missing_total` counter (월간 missing rate 기반, 집계는 Story 2.10)

**Given** Story 2.1 snapshot fixture (바이오 C사 2023-12 서사 재구성)
**When** 5영업일 뉴스 feed M2 처리
**Then** reference score 대비 ±0.05 + cluster 개수 reference 대비 ±1
**And** pytest `tests/snapshot/test_m2_narrative_age.py` 통과

### Story 2.4: M3 Pre-Announcement Drift Z-score

As Khuk0's Alpha Defense 파이프라인,
I want 뉴스·공시 직전 비정상 가격·거래량 표류를 Z-score로 감지하는 M3 모듈을 확보하여,
So that 정보 유출 또는 선행 포지셔닝에 물린 "이미 오른 뉴스" 시그널이 진입 전에 거부된다.

**Acceptance Criteria:**

**Given** `athena-alpha-defense/m3/drift_zscore.py` 구현 + rolling window N분 (default 30, `policy.toml`)
**When** 특정 종목 뉴스·공시 도착 시점
**Then** 이전 N분 가격 log-return + 거래량 rolling Z-score 2축 계산
**And** window 크기 N은 F5 읽기전용 마운트 대상 (AR-CFG4)

**Given** Z-score 계산 결과
**When** |Z_price| > 3.0 OR |Z_volume| > 3.0
**Then** 52 flag 중 `no_leak_drift` flag = 0 (veto)
**And** Z-score 값 `modules_output` 에 `score=max(|Z_price|, |Z_volume|)` 기록 + M25 리포트 전달

**Given** DuckDB external Parquet scan
**When** 350종목 × 30분 tick rolling 쿼리
**Then** p95 < 500ms per call (NFR-P4), 결정론적 seed (AR-TEST2)
**And** `athena_m3_query_duration_seconds` histogram 측정

**Given** 뉴스 직전 tick 데이터 window 내 결측 > 50%
**When** M3 계산 시도
**Then** flag neutral(1) degrade + error_code `DATA_STALE` (AR-COM3, NFR-I5)
**And** `athena_m3_data_stale_total{symbol}` counter + Medium 알림 (NFR-O3, rate > 5%/일 시)

**Given** Story 2.1 snapshot fixture 유리기판 A사 2025-11 공시 전 drift
**When** M3 실행
**Then** reference Z-score 대비 ±0.2 + `no_leak_drift` flag 일치
**And** pytest `tests/snapshot/test_m3_drift.py` 통과

### Story 2.5: M9 Time-of-Day Multiplier

As Khuk0's Alpha Defense 파이프라인,
I want 6구간 시간대(장전·동시호가·장초·점심·마감·장후)별 M_time 가중치 multiplier를 산출하는 M9 모듈을 확보하여,
So that 구간별 정보 환경·유동성 차이가 S_entry 수식에 정량 반영된다.

**Acceptance Criteria:**

**Given** `athena-alpha-defense/m9/time_multiplier.py` 구현 + KRX 시간 기준 6구간 정의
**When** 구간 경계 설정
**Then** 장전 (~08:30), 동시호가 (08:30-09:00), 장초 (09:00-10:00), 점심 (11:30-13:00), 마감 (15:00-15:20), 장후 (15:20~) 정확 매핑
**And** 한국 공휴일 캘린더 참조 (휴일은 모두 "장외" = multiplier 0)

**Given** `config/policy.toml` 의 M_time 벡터 (6개 float 0.0~2.0)
**When** multiplier 조회
**Then** 파라미터 출처 AR-CFG4 (F5 읽기전용 마운트), 장중 수정 불가
**And** 값 범위 validation: 0.0 ≤ m ≤ 2.0, 위반 시 config 로드 단계 SystemExit

**Given** 현재 시각 `now_kst`
**When** `m9.get_multiplier(now_kst) -> float` 호출
**Then** 해당 구간 multiplier 반환, 반환 latency p99 < 1ms (dict/bisect lookup)
**And** `athena_m9_lookup_duration_seconds` histogram

**Given** 장 외 시간대 (예: 20:00) 또는 공휴일
**When** 시그널 생성 파이프라인에서 M9 호출
**Then** multiplier = 0 → S_entry = 0 → 진입 거부
**And** M25 리포트(Story 2.9) 거부 이유 "off_market: now={ts}, bucket=out_of_hours" 전달

**Given** Story 2.1 snapshot fixture 2건의 뉴스·공시 발생 시각
**When** 각 시각 기준 M_time 적용
**Then** reference M_time 값과 deterministic 일치 (오차 0.0)
**And** pytest `tests/snapshot/test_m9_time_multiplier.py` 통과

### Story 2.6: M13 XGBoost 1단계 + 비동기 LLM 2단계 Hybrid

As Khuk0's Alpha Defense 파이프라인,
I want XGBoost 1단계 + HyperCLOVA X / Solar Pro 2 비동기 LLM 2단계 하이브리드 스코어링 M13 모듈을 구현하여,
So that 저비용·빠른 1단계가 장중 블로킹 경로를 통과시키고, 고비용·정교한 2단계는 비동기 경로에서만 작동하여 NFR-P5 를 위반하지 않는다.

**Acceptance Criteria:**

**Given** XGBoost 모델 파일 (pretrained, M1/M2/M3/M9 feature 입력 기대) + `athena-alpha-defense/m13/hybrid.py`
**When** `m13.stage1_xgboost(features) -> float` 호출
**Then** 0.0~1.0 확률 반환, inference p99 < 10ms
**And** asyncio trace_id 부여 (NFR-O4), 구조화 로그에 embed

**Given** 1단계 확률이 ambiguous band (기본 0.4~0.6, `policy.toml`)
**When** 2단계 LLM 호출 결정
**Then** `alpha_to_llm_q` (`asyncio.Queue`, bounded 1000, AR-COM2) 에 enqueue
**And** queue full 시 oldest drop + `athena_m13_llm_queue_drop_total` counter + WARNING 로그 (AR-COM5)

**Given** 2단계 LLM 호출 경로 (HyperCLOVA X 또는 Solar Pro 2, AR-EXT6)
**When** 비동기 호출 실행
**Then** 2초 timeout (NFR-P3), 초과 시 1단계 결과로 fallback (NFR-I5)
**And** error_code `LLM_TIMEOUT` 로그 + `athena_m13_llm_timeout_total` counter 증가

**Given** 장중 블로킹 경로 (시그널 생성 → 주문 의도 발행)
**When** M13 호출
**Then** 2단계 결과 대기 금지, 1단계 결과 즉시 반환 (NFR-P5 strict)
**And** 2단계 결과 도착 후 `modules_output` upsert만 수행 (사후 학습 트레이닝 데이터)

**Given** LLM API key (OS Keychain 저장, NFR-S1)
**When** 서비스 시작 시 key 조회
**Then** 키 없음 → `MissingSecretError("HYPERCLOVA_API_KEY not in OS Keychain")` 조기 실패
**And** `.env` 파일 존재 감지 시 `SystemExit(".env usage forbidden by NFR-S1")` (AR-CFG5)

**Given** Story 2.1 snapshot fixture 2건
**When** 1단계 XGBoost 추론 실행 (2단계 LLM은 deterministic mock 사용, 외부 API 호출 금지)
**Then** reference probability 대비 ±0.05 + mock LLM 응답 시 전체 score reference 대비 ±0.05
**And** pytest `tests/snapshot/test_m13_hybrid.py` 통과 (CI 오프라인 실행 가능)

### Story 2.7: M14 Transfer Entropy Basket Gate

As Khuk0's Alpha Defense 파이프라인,
I want 밸류체인 바스켓 내 선행주-후발주 Transfer Entropy 계산 기반 M14 일관성 gate 모듈을 확보하여,
So that 바스켓 일관성 없이 혼자 움직이는 종목(작전 의심 신호)이 자동 거부된다.

**Acceptance Criteria:**

**Given** `config/universe.toml` 의 밸류체인 바스켓 정의 (예: 2차전지 [양극재/음극재/전해질], 반도체 [메모리/장비/소재], 조선 [조선소/기자재])
**When** `athena-alpha-defense/m14/transfer_entropy.py` 구현 + PyInform 또는 자체 Symbolic TE 구현
**Then** `te_value(leader_series, follower_series, lag_k=5) -> float` 반환
**And** lag_k, bin 수 등 파라미터는 `policy.toml` 출처 (AR-CFG4)

**Given** 특정 종목 신호 발생
**When** 해당 종목 소속 바스켓의 선행주(시총·유동성 기반 사전 지정) tick 시계열 가져오기 + TE 계산
**Then** TE > threshold(기본 0.02, `policy.toml`) 시 `basket_coherent` flag = 1, 미만 시 0
**And** 바스켓 및 leader 매핑은 `universe.toml` 의 명시적 선언, 런타임 자동 선정 금지

**Given** 바스켓 내 활성 종목 < 3개 (데이터 결측 또는 거래정지)
**When** M14 계산 시도
**Then** flag neutral(1) degrade (NFR-I5) + error_code `FEATURE_MISSING`
**And** `athena_m14_insufficient_data_total{basket}` counter + rate > 10%/월 시 Medium 알림

**Given** TE 계산 처리 시간
**When** 1회 호출 (바스켓 5종목 × 5분 tick window)
**Then** p95 < 500ms (NFR-P4), 결정론적 seed (AR-TEST2)
**And** `athena_m14_te_duration_seconds` histogram

**Given** 바스켓 일관성 깨짐 (TE < threshold)
**When** 종목 신호 처리
**Then** `basket_coherent` flag = 0 → S_entry 곱셈 0 → 진입 거부
**And** M25 리포트(Story 2.9) "basket_incoherent: basket={name}, te={val}, threshold={th}" 전달

**Given** Story 2.1 snapshot fixture (유리기판 A사 소속 바스켓 재구성)
**When** M14 실행
**Then** reference TE 값 대비 ±10% + `basket_coherent` flag 일치
**And** pytest `tests/snapshot/test_m14_transfer_entropy.py` 통과

### Story 2.8: S_entry 곱셈 집계 수식 + End-to-End p99 검증

As Khuk0's Orchestrator,
I want `S_entry = 1[¬HardKill] · (αN+βV+γO) · Π G_i · M_regime · M_time` 수식을 구현하여 52 flag를 곱셈 집계하고 end-to-end 시그널 생성 p99 < 5초를 실측 검증하여,
So that MVP 유니버스 350종목에 대한 실시간 거부/승인 판정이 가능하고 성능 회귀가 숫자로 잡힌다.

**Acceptance Criteria:**

**Given** `athena-orchestrator/s_entry.py` 구현 + Story 2.2~2.7 모듈 6개 완성
**When** 52 flag 값 + α/β/γ + M_regime + M_time 입력
**Then** `S_entry = 1[¬HardKill] · (α·N + β·V + γ·O) · Π_{i=1..50} G_i · M_regime · M_time` 정확 계산
**And** α/β/γ 가중치 sum = 1 제약 검증, 위반 시 config 로드 단계 SystemExit

**Given** HardKill flag 그룹 정의 (거래정지, 관리종목, 공매도 제한 위반, VI 발동 등 `flag_registry.toml` 에 `group="hard_kill"` 태그)
**When** HardKill flag 중 하나라도 = 1 활성화
**Then** `S_entry = 0` 즉시 리턴 (short-circuit, 나머지 flag 계산 skip)
**And** 성능 최적화: HardKill 시 latency < 100ms 보장

**Given** 50개 G_i flag 곱셈 경로
**When** `Π G_i` 계산
**Then** 하나라도 0이면 전체 0 (veto), 전체 1이면 `(αN+βV+γO) · M_regime · M_time` 통과
**And** degrade 표식된 flag는 1 취급 (NFR-I5), degrade 개수는 `decisions.degraded_flag_count` 컬럼 기록

**Given** Prometheus histogram `athena_s_entry_duration_seconds` (feature 조회 → 모든 M 모듈 → 곱셈 집계 end-to-end)
**When** 1000+ 시그널 표본 수집
**Then** `histogram_quantile(0.99, athena_s_entry_duration_seconds)` < 5.0초 (NFR-P1)
**And** 실측 p99 미달 시 High 알림 (NFR-O3) + Epic 7 대시보드 panel 표시

**Given** Story 2.1 snapshot fixture 2건
**When** end-to-end S_entry 계산 (M1~M14 full 경로)
**Then** reference S_entry 값 대비 ±5% (AR-TEST3)
**And** CI Step 4 snapshot 회귀가 Story 2.1의 placeholder → real fixture 전환 완료, 회귀 시 `SNAPSHOT_REGRESSION` error_code FAIL

**Given** 계산 완료된 S_entry
**When** `decisions` 테이블 insert
**Then** DTO `SEntryResult(user_id, symbol, timestamp_kst, s_entry, flags_snapshot[52], α, β, γ, m_regime, m_time, hard_kill_triggered, degraded_flag_count, policy_version_git_sha, module_version)` (NFR-M1, NFR-M2)
**And** `timestamp_kst` 정밀도 millisecond, `policy_version_git_sha` 는 현재 HEAD (AR-COM4)

### Story 2.9: M25 거부 설명 리포트

As Khuk0 (and future compliance audit),
I want 진입 거부 시 어떤 gate·flag가 0이었는지와 정량 근거를 M25 설명 리포트로 자동 생성하여,
So that 모든 거부 결정이 사후 설명·감사 가능하며, 내 직관이 규율을 이긴 경우 즉시 식별된다.

**Acceptance Criteria:**

**Given** `athena-orchestrator/explain.py` 구현 + Story 2.8의 `SEntryResult` DTO
**When** `S_entry = 0` 거부 발생
**Then** 52 flag 중 0값 flag 전체 수집 + 각 flag의 소유 모듈(M1~M14) + 모듈이 리턴한 정량 값 + degrade 여부
**And** JSON 구조화 로그 + 인간가독 한국어 요약 2형식 동시 생성

**Given** M25 리포트 Pydantic DTO
**When** 리포트 생성
**Then** 스키마: `ExplainReport(user_id, symbol, timestamp_kst, s_entry, failed_flags: List[FailedFlag], hard_kill_triggered: bool, policy_version_git_sha)` + `FailedFlag(flag_id, module, value, reason_code, human_readable)`
**And** `decisions` 테이블에 `explain_json` JSON 컬럼으로 append, 인간가독은 별도 파일 `logs/rejections/{date}/{symbol}_{ts}.txt`

**Given** M25 생성 latency
**When** 거부 발생마다
**Then** p99 < 50ms (시그널 블로킹 경로 아님, 사후 기록)
**And** 구조화 JSON 로그에 trace_id 포함 (NFR-O1, NFR-O4)

**Given** 다중 flag 0 동시 발생 (예: `narrative_fresh=0` AND `basket_coherent=0` AND `no_leak_drift=0`)
**When** M25 리포트 생성
**Then** 모든 원인 나열 (단일 원인 추정 금지), 각 원인에 정량 수치 포함
**And** 인간가독 요약은 모듈 가중치 순으로 정렬 (중요도 판단은 제시, 결정은 사람)

**Given** HardKill 트리거 케이스
**When** M25 생성
**Then** `hard_kill_triggered=True` + 해당 HardKill flag 목록만 표시 (일반 flag 생략)
**And** 인간가독 요약: "진입 차단: 거래정지/관리종목/VI 발동 등 경성 사유"

**Given** Story 2.1 snapshot fixture 2건의 거부 시나리오
**When** M25 생성
**Then** reference `explain_json` 과 구조적 일치 (failed_flags 목록 + reason_code 매칭)
**And** pytest `tests/snapshot/test_m25_explain.py` 통과

### Story 2.10: Flag Degrade + 월간 Missing Rate 계산 로직 (NFR-A4 기반)

As Khuk0's Alpha Defense + Compliance seam,
I want 52 flag 결측 시 neutral(1) degrade 자동 처리와 월간 missing rate 계산 로직을 Epic 2 에서 완성하여,
So that graceful degradation(NFR-I5)이 보장되고 Epic 7 FR52 월간 자기감사 리포트(NFR-A4)가 참조할 단일 소스 함수가 확보된다.

**Acceptance Criteria:**

**Given** `athena-orchestrator/degrade.py` 구현
**When** 52 flag 중 어느 하나 계산 실패 (데이터 결측, 모델 오류, timeout)
**Then** 해당 flag = 1 (neutral) 자동 대입 + `modules_output` 에 `(flag_id, reason_code, timestamp_kst)` degrade 기록
**And** degrade된 flag는 S_entry 계산에서 G_i = 1 취급 (Story 2.8 일치)

**Given** reason_code enum 제한
**When** degrade 발생
**Then** `{DATA_STALE, FEATURE_MISSING, CONFIDENCE_BELOW_THRESHOLD, LLM_TIMEOUT, MODEL_ERROR}` 중 하나 (AR-COM3 확장)
**And** Prometheus counter `athena_flag_degrade_total{flag, reason}` 증가 + 구조화 JSON 로그

**Given** `athena-alpha-defense/src/missing_rate.py` 집계 함수
**When** `calculate_missing_rate(start_kst, end_kst) -> polars.DataFrame` 호출
**Then** 결과 스키마: `{flag_id, total_signals, degraded_signals, missing_rate, reason_breakdown: Dict[str, int]}`
**And** Polars in-memory 집계, DuckDB Parquet external scan (NFR-P4 < 500ms per flag)

**Given** 개별 flag missing rate > 20% (월간 기준)
**When** 월간 집계 종료
**Then** 해당 flag 구조적 작동 불가 경보 + Epic 8 Story 8.x 재훈련 트리거 hook (flag name emit only)
**And** `athena_flag_missing_rate_alert_total{flag}` counter 증가 + High 알림 (NFR-O3)

**Given** Epic 7 FR52 `scripts/monthly_audit.py` 설계 경계
**When** Epic 7 구현 시
**Then** 본 Story의 `missing_rate.py` 를 import 하여 사용 (중복 구현 금지, DRY)
**And** 책임 분리: Epic 2 = 계산 로직 + counter + 단일 함수 / Epic 7 = 리포트 포맷 + 배포 + Grafana 패널

**Given** Story 2.1 snapshot fixture
**When** 의도적으로 M1 모델 return None 강제 주입 (테스트 전용 fault injection)
**Then** degrade 정상 작동 + `missing_rate` 계산 1/1 = 100% + reason_code `MODEL_ERROR`
**And** pytest `tests/snapshot/test_degrade_missing_rate.py` 통과

---

## Epic 3: Anti-Ego Firewall & Entry Authorization

**Epic Goal:** F1 흥정 언어 감지 + F5 Override 시도 감시 + 이중 조건 최종 Entry Gate + anti_ego_events append-only 증거 체인을 구축한다. `anti_ego_events` 테이블(append-only + SHA-256 chain)로 기반을 세우고, 본인 일지에서 250건+ 라벨을 수작업 축적하는 CLI → KB-BERT fine-tune → 실시간 흥정 감지 3-step F1 파이프라인을 확보한다. Epic 1 Story 1.6의 F5 읽기전용 마운트 인프라 위에 inotify watcher를 얹어 장중 override 시도를 OS primitives로 감지·기록한다. 집계된 Firewall 플래그와 Epic 2 Story 2.8의 S_entry를 AND 조건으로 결합하는 이중 조건 Entry Gate가 "알파 방어(52 flag) + 내부 방어(Anti-Ego)" 두 층을 모두 통과한 주문 의도만 하류로 넘긴다. 내 흥정 언어는 실시간 감지되고, 장중 어떤 override도 물리적으로 불가능하며, 이중 조건을 통과한 주문 의도만 Execution 레이어로 넘어간다.

### Story 3.1: anti_ego_events Append-Only Table + SHA-256 Chain

As Khuk0's Anti-Ego Firewall,
I want `anti_ego_events` 테이블이 Pre-Trade Ledger(Story 1.5)와 동일한 append-only + SHA-256 해시 체인 구조로 초기화되어,
So that F1 흥정 감지·F5 override 시도·Firewall 상태 전환 모든 기록이 tamper-evident 증거 체인(NFR-S3, NFR-A3)으로 보호된다.

**Acceptance Criteria:**

**Given** Trading PC `decisions.duckdb`
**When** `anti_ego_events` 테이블 초기화
**Then** 스키마: `id` (PK), `user_id`, `event_type` (enum: `BARGAINING_DETECTED`, `OVERRIDE_ATTEMPT`, `FIREWALL_ACTIVATED`, `FIREWALL_DEACTIVATED`, `F1_TRAINED`, `POLICY_EDIT_AFTER_HOURS`, `WATCHER_GAP`), `payload_json`, `prev_hash`, `this_hash`, `policy_version_git_sha`, `created_at_utc`, `param_hash`
**And** UPDATE/DELETE 물리 차단 (DuckDB view + trigger, Story 1.5와 동일 패턴)

**Given** genesis entry 삽입
**When** 첫 레코드 append
**Then** `prev_hash=NULL`, `this_hash=SHA256(payload_json || policy_version_git_sha || event_type)`
**And** 다음 entry `prev_hash=이전.this_hash` 체인 유지, 체인 순서 위반 시 INSERT 차단

**Given** 월말 체인 해시 계산 job
**When** 매월 1일 03:30 KST (Story 1.5 Ledger 체인 03:00 KST 이후 30분 뒤)
**Then** `anti_ego_segment_hash = SHA256(prev_segment || sorted_ids_hash || policy_version_git_sha)` 계산 후 외장 SSD LUKS + S3 Object Lock Compliance(최소 5년) 양쪽 저장
**And** S3 object key `anti_ego/user_id=1/year=YYYY/month=MM/segment_hash.json`

**Given** `athena-core/anti_ego_ledger.py` writer 유틸
**When** 모듈에서 `append_event(event_type, payload: dict)` 호출
**Then** 체인 무결성 자동 유지 + async lock으로 동시 쓰기 보호
**And** write latency p99 < 20ms (NFR-P5 비블로킹 경로 보장)

**Given** `scripts/verify_anti_ego_chain.py` 월간 CI job
**When** 실행
**Then** 전 월 `anti_ego_segment_hash` ↔ 현 월 genesis `prev_hash` 연속성 + 전 체인 SHA 재계산 일치 검증
**And** 불일치 시 Critical 알림(NFR-O3) + Global CB 발동 hook (Epic 5 Story 5.x 연동 준비)

**Given** NFR-A3 override 로그 완전성 100% 요구
**When** 월간 감사 리포트 (Epic 7 FR52 연계)
**Then** `SELECT COUNT(*) FROM anti_ego_events WHERE event_type IN ('BARGAINING_DETECTED','OVERRIDE_ATTEMPT')` vs Story 3.4 F1 trigger counter + Story 3.5 inotify 이벤트 counter 교차검증
**And** 누락 > 0건 시 FAIL + Epic 8 재학습 트리거 hook

### Story 3.2: F1 흥정 언어 라벨링 CLI

As Khuk0 curating training data from my own journals,
I want `scripts/f1_label.py` CLI 도구로 본인 과거 일지·채팅·메모에서 흥정 언어 사례를 선별·라벨링하여,
So that F1 fine-tune용 250건+ positive 라벨 데이터셋(FR14)이 수작업 효율적으로 축적된다.

**Acceptance Criteria:**

**Given** `decisions.duckdb` + `labels_f1` 테이블 미초기화
**When** 테이블 생성 스크립트 실행
**Then** 스키마: `id`, `user_id`, `source_file`, `source_timestamp`, `text`, `label` (bool: is_bargaining), `labeler` (fixed 'khuk0'), `label_timestamp_utc`, `notes`, `policy_version_git_sha`, UNIQUE `(user_id, source_file, source_timestamp)`
**And** NFR-M4 user_id 컬럼 유지 (commercialization-ready seam 존재하나 V1.0은 단일 값)

**Given** 일지 소스 디렉토리 경로 (예: Obsidian vault, markdown journal)
**When** `python scripts/f1_label.py --source /path/to/journals` 실행
**Then** 파일 순회 + 문장 단위 분절 (`kss` 한국어 분절 라이브러리)
**And** 각 문장에 대해 CLI 프롬프트 "Bargaining? [y/n/s(skip)/q(quit)] > " + 선택적 `note:` 입력

**Given** 라벨링 세션 진행 중
**When** 사용자 y/n 응답
**Then** `labels_f1` INSERT + 진행률 표시 "42/500 processed, 12 positive labels"
**And** 세션 종료 시 summary 출력 (총 처리, positive/negative 비율, 소요 시간)

**Given** 세션 중단 → 재개
**When** 동일 소스로 재실행
**Then** 이미 처리된 `(source_file, source_timestamp)` skip (idempotent)
**And** UNIQUE 제약 위반 시 조용히 skip, 중복 에러 raise 금지

**Given** positive label 250건 도달
**When** `python scripts/f1_label.py --status`
**Then** "Positive labels: 250+, READY for fine-tune (Story 3.3)" 출력
**And** 250건 미만 시 "Need N more positive labels, current: M" 안내

**Given** Epic 8 FR54 PSI 드리프트 seam
**When** 월별 label distribution 집계 함수 호출
**Then** `athena_f1_labels_positive_rate` gauge + label text hash 분포 통계
**And** Epic 8 Story 8.x의 PSI 계산이 본 집계 함수 참조 (DRY, 중복 구현 금지)

### Story 3.3: F1 KB-BERT Fine-tune Pipeline

As Khuk0's Anti-Ego ML pipeline,
I want KB-BERT 기반 F1 흥정 감지 분류기를 본인 라벨 250건+ 으로 fine-tune 하는 재현 가능 파이프라인을 확보하여,
So that 내 고유 언어 패턴에 특화된 F1 모델이 생성되고, 모든 재학습이 결정론적·감사 가능하게 반복된다.

**Acceptance Criteria:**

**Given** `athena-alpha-defense/f1/finetune.py` + `labels_f1` 테이블 데이터
**When** fine-tune 실행
**Then** train/val split 80:20 stratified on label + seed 고정 (AR-TEST2) + 결정론적 reproducibility
**And** positive label < 250건 시 WARNING "production threshold not met, training smoke mode only" 출력 후 계속 진행 (smoke 테스트 허용)

**Given** KB-BERT finance 사전학습 모델 weight (M1과 동일 소스)
**When** fine-tune loop 실행
**Then** 2-3 epoch, AdamW optimizer, learning rate 2e-5, batch size 16 (hyperparam은 `config/policy.toml`, F5 대상 AR-CFG4)
**And** Trading PC WSL2 GPU 또는 CPU 실행 가능, 실행 시간 + device 정보 stdout 로깅

**Given** 학습 완료
**When** 모델 artifact 저장
**Then** `athena/models/f1/{yyyymmdd_hhmmss}_{git_sha8}/` 디렉토리에 weight + tokenizer + `meta.json`(hyperparam, dataset_hash, validation metrics, labeler='khuk0', sample_count, positive_rate)
**And** 모델 버전 = `F1.v{semver}+{git_sha8}` (NFR-M2), `athena._version.__commit__` 일치

**Given** validation set 평가
**When** 메트릭 계산
**Then** F1 score + precision + recall + AUC + confusion matrix 기록 `meta.json`
**And** validation AUC < 0.75 시 production 배포 차단 marker (실 배포 제어는 Epic 8 Story 8.x에서)

**Given** fine-tune 실행 audit 요구
**When** 학습 완료
**Then** `anti_ego_events` append `event_type='F1_TRAINED'`, payload={model_version, dataset_hash, metrics, sample_count} (Story 3.1 writer 사용)
**And** NFR-A3 완전성: 모든 학습 실행이 증거 체인에 남음

**Given** Epic 8 FR56 Bayesian 튜닝 + walk-forward seam
**When** Epic 8 Story 8.x 구현 시
**Then** 본 Story의 `finetune.py` `train_one_run(hyperparams) -> metrics` API 재사용 (DRY)
**And** 책임 분리: Epic 3 = single-run 학습 파이프라인 / Epic 8 = 튜닝 루프 + walk-forward 백테스트

### Story 3.4: F1 실시간 흥정 언어 감지

As Khuk0's Anti-Ego pipeline watching my own inputs,
I want F1 fine-tuned 분류기가 내 채팅·메모·장중 입력을 실시간 감지하여,
So that 흥정 언어 발화 즉시 Anti-Ego Firewall 상태가 0으로 전환되고 이중 조건 Entry Gate가 진입을 차단한다(FR13).

**Acceptance Criteria:**

**Given** `athena-alpha-defense/f1/detector.py` + Story 3.3으로 학습된 최신 모델
**When** 서비스 시작
**Then** 모델 weight + tokenizer lazy load, 로드 실패 시 `MODEL_ERROR` 로그 + Firewall 상태 0 강제 (fail-secure default)
**And** 모델 버전이 DTO에 embed (NFR-M1, NFR-M2)

**Given** 사용자 입력 소스 정의 (MVP: 지정 파일 `input/runtime_notes.txt` inotify 감시 또는 named pipe)
**When** 새 문장 도착
**Then** `f1.detect(text: str) -> (is_bargaining: bool, score: float, matched_phrases: List[str])` 리턴
**And** inference latency p99 < 100ms (NFR-P2, M1과 동급), Prometheus histogram `athena_f1_inference_duration_seconds`

**Given** score > threshold (기본 0.7, `policy.toml`, F5 대상)
**When** 흥정 감지 발생
**Then** `anti_ego_events` append (`event_type='BARGAINING_DETECTED'`, payload={text_sha256, score, matched_phrases_hash}) — **원문 text 평문 저장 금지**, hash만 (개인정보 보호)
**And** Firewall aggregator(Story 3.6)가 구독 → 상태 0 전환

**Given** score가 threshold 미만 (낮은 confidence)
**When** F1 호출
**Then** neutral 반환 (Firewall 상태 변화 없음) + `athena_f1_low_confidence_total` counter 증가
**And** Epic 8 재학습 신호 (confidence 분포 드리프트 감지용)

**Given** 장중 실시간 처리
**When** 분당 감지 수 측정
**Then** Prometheus gauge `athena_f1_bargaining_detected_per_minute`
**And** 분당 > 3건 시 Medium 알림 "high bargaining frequency, self-check required" (NFR-O3)

**Given** 테스트 fixture (가상 흥정 문장 20건 + non-흥정 20건, 본인 과거 사례 anonymized)
**When** 유닛 테스트
**Then** 정확도 > 80% (snapshot regression, threshold는 Epic 8 fine-tune 품질 개선 시 상향)
**And** pytest `tests/snapshot/test_f1_detector.py` 통과, CI Step 4 통합

### Story 3.5: F5 Override 시도 inotify Watcher + Logging

As Khuk0's Anti-Ego Firewall,
I want Epic 1 Story 1.6의 F5 읽기전용 마운트 인프라 위에 inotify watcher를 얹어 장중 파라미터·정책 파일 override 시도를 감지·기록하여,
So that 파라미터·정책 파일에 대한 모든 수정 시도(FR16, NFR-S4)가 anti_ego_events에 증거로 남고, 시도 자체가 규율 실패 데이터가 된다(NFR-A3).

**Acceptance Criteria:**

**Given** Trading PC WSL2에 `athena-f5-watcher.service` 정의
**When** systemd 활성화 (24/7, Restart=always)
**Then** `inotifywait -m config/policy.toml config/flag_registry.toml --event attrib,modify,close_write,delete_self` 실행
**And** 장중/장외 무관 상시 가동, crash 시 systemd 자동 재시작

**Given** 장중 09:00~15:30 KST (immutable 상태)
**When** 사용자 또는 프로세스가 정책 파일 수정 시도
**Then** `chattr +i`에 의해 OS "Operation not permitted" 에러 + inotify 이벤트 발생
**And** watcher가 `anti_ego_events` append: `event_type='OVERRIDE_ATTEMPT'`, payload={file_path, attempted_by_pid, attempted_by_uid, timestamp_kst, mount_state='immutable'} (Story 3.1 writer 사용)

**Given** 장외 시간 (15:30~09:00 KST, mutable 상태)
**When** 정책 파일 수정 발생
**Then** `event_type='POLICY_EDIT_AFTER_HOURS'` append (정상 경로, 위반 아님) + git commit 대기 marker 설정
**And** 72h cooling gate(Epic 1 Story 1.3)가 해당 marker 참조

**Given** inotify watcher 프로세스 crash
**When** systemd Restart 발동
**Then** 재시작 후 누락 기간을 `event_type='WATCHER_GAP'` append, payload={gap_start_utc, gap_end_utc, duration_seconds}
**And** watcher 재시작 자체가 override 가능성 → Critical 알림 (NFR-O3)

**Given** 월간 감사 집계
**When** `OVERRIDE_ATTEMPT` count 조회
**Then** `athena_f5_override_attempt_total` counter + 월간 감사 리포트 포함 (Epic 7 FR52 연계)
**And** 발생 횟수 > 0 자체가 정량 규율 실패 지표 (0 목표, 비-0 시 self-retrospective 트리거)

**Given** 통합 테스트 시나리오 (WSL2 전용)
**When** `chattr +i test.toml` 설정 후 `echo x > test.toml` 시도
**Then** "Operation not permitted" 에러 + watcher가 `OVERRIDE_ATTEMPT` event append 확인
**And** pytest `tests/integration/test_f5_watcher.py` 통과 (Trading PC WSL2 환경 마킹)

### Story 3.6: Anti-Ego Firewall Aggregator

As Khuk0's Orchestrator,
I want F1 감지 상태와 F5 시도 이력을 집계하여 Anti-Ego Firewall 단일 불리언 플래그(0 또는 1)를 산출하는 in-memory aggregator를 확보하여,
So that 이중 조건 Entry Gate(Story 3.7)가 참조할 단일 상태 값이 < 1ms latency로 실시간 제공된다(FR15).

**Acceptance Criteria:**

**Given** `athena-orchestrator/firewall.py` 구현
**When** aggregator 초기화
**Then** in-memory 상태: `{firewall_status: bool, last_bargaining_event_ts, last_override_attempt_ts, cooldown_expires_at}` + 프로세스 재시작 시 `anti_ego_events` 테이블 최근 24h 이벤트로 상태 재구성 (crash recovery)
**And** 초기화 실패 시 fail-secure: `firewall_status=False` 강제

**Given** Story 3.4 `BARGAINING_DETECTED` event 구독
**When** 이벤트 도착
**Then** `firewall_status=False` 즉시 전환 + cooldown 설정 (기본 30분, `policy.toml`, F5 대상)
**And** cooldown 만료 시 `firewall_status=True` 복귀 + `FIREWALL_DEACTIVATED` event append (Story 3.1)

**Given** Story 3.5 `OVERRIDE_ATTEMPT` event 구독
**When** 이벤트 도착
**Then** `firewall_status=False` 즉시 전환 + 장 마감(15:30 KST)까지 복귀 금지 (override 시도는 단순 흥정보다 심각)
**And** `FIREWALL_ACTIVATED` event append, payload={reason: 'override_attempt', trigger_event_id}

**Given** Story 3.7 dual gate에서 `firewall.get_status() -> bool` 호출
**When** 상태 조회
**Then** in-memory dict 읽기 O(1), latency < 1ms (반복 측정 p99)
**And** 상태 조회 자체는 event 기록 대상 아님 (read-only, 로그 오염 방지)

**Given** Prometheus 메트릭
**When** 상태 변화 발생
**Then** `athena_firewall_status` gauge (0/1) + `athena_firewall_activations_total{reason}` counter (reason ∈ {bargaining, override_attempt})
**And** Story 3.8 Grafana panel이 해당 메트릭 참조

**Given** 결정론적 시나리오 테스트
**When** 이벤트 주입 (BARGAINING @ T=0, T+10min, cooldown=30min)
**Then** T=0 → firewall=0, T+10 → firewall=0 (cooldown 연장), T+40 → firewall=1
**And** pytest `tests/integration/test_firewall_aggregator.py` 통과 (async 이벤트 순서 검증)

### Story 3.7: 이중 조건 Entry Gate (S_entry > θ_entry AND Firewall = 1)

As Khuk0's Orchestrator,
I want Epic 2 Story 2.8의 S_entry 결과와 Story 3.6의 Firewall 상태를 AND 조건으로 결합하는 최종 Entry Gate를 구현하여,
So that 알파 방어(52 flag)와 내부 방어(Anti-Ego) 두 층을 모두 통과한 주문 의도만 하류 Execution(Epic 4)으로 넘어간다(FR10).

**Acceptance Criteria:**

**Given** `athena-orchestrator/decision.py` 최종 gate
**When** Story 2.8 `SEntryResult` 수신
**Then** `authorized = (s_entry > θ_entry) AND (firewall_status == True)` 평가
**And** θ_entry는 `policy.toml` 출처 (AR-CFG4, F5 읽기전용 대상), 장중 수정 시도는 Story 3.5 OVERRIDE_ATTEMPT 기록

**Given** `authorized = True`
**When** 하류 전달
**Then** `OrderIntent` DTO 생성 (user_id, symbol, size_hint, timestamp_kst, s_entry, firewall_status, policy_version_git_sha, param_hash, module_version) 후 `orchestrator_to_execution_q` 전달 (AR-COM5 네이밍)
**And** `orders` 테이블 INSERT는 Epic 4 책임, 본 Story는 의도 발행까지만

**Given** `authorized = False` 거부
**When** 거부 원인 분류
**Then** (a) `s_entry ≤ θ_entry` → Epic 2 Story 2.9 M25 리포트 + `rejection_layer='alpha'` / (b) `firewall=False` → `anti_ego_events` append `event_type='ENTRY_BLOCKED_BY_FIREWALL'`, payload={s_entry, firewall_reason} + `rejection_layer='anti_ego'` / (c) 둘 다 실패 → `rejection_layer='both'`, 두 기록 모두 생성
**And** 거부 사유는 M25 + anti_ego 두 채널에서 독립적으로 감사 가능

**Given** 이중 조건 gate 추가 latency
**When** S_entry 계산 완료 이후 경로 (firewall.get_status + 판정 + 기록)
**Then** p99 < 100ms 추가 (NFR-P1 end-to-end 5초 내에 여유 포함)
**And** Firewall lookup 자체는 Story 3.6 AC#4에 의해 < 1ms

**Given** Pre-Trade Ledger(Epic 1 Story 1.5) 연계
**When** 모든 entry 판정 완료 (authorized 또는 rejected)
**Then** Ledger writer 호출 seam만 생성 (interface call), 실 ledger append는 Epic 6 FR38에서 완성
**And** 본 Story는 `LedgerWriter.submit(decision_record)` 추상 호출까지, 구현은 Epic 6

**Given** 이중 조건 snapshot 테스트
**When** 4개 시나리오 주입 — (1) s_entry=0.8>θ + firewall=1 → 승인, (2) s_entry=0.8 + firewall=0 → 거부 anti_ego, (3) s_entry=0.3 + firewall=1 → 거부 alpha, (4) s_entry=0.3 + firewall=0 → 거부 both
**Then** 기대 authorized + rejection_layer 일치 + anti_ego_events 적절히 생성
**And** pytest `tests/integration/test_dual_gate.py` 통과

### Story 3.8: Anti-Ego Firewall Grafana Panel (partial, Epic 7 완성)

As Khuk0 monitoring my own discipline,
I want Firewall 상태 실시간 + 활성화 이력 + F1 감지 이벤트를 Grafana 패널로 즉시 확인하여,
So that 장중 "지금 내가 어떤 상태인가"를 3초 내에 판단 가능하다(FR18).

**Acceptance Criteria:**

**Given** Epic 1 Story 1.9의 Grafana "Foundation Health" 대시보드
**When** "Anti-Ego Panel" 4-패널 그룹 추가
**Then** (a) `athena_firewall_status` 현재 상태 (Red=0, Green=1), (b) 최근 24h 활성화 이력 timeline, (c) `athena_f1_bargaining_detected_per_minute` 시계열, (d) `athena_f5_override_attempt_total` 누적 카운터
**And** 패널 refresh interval 5초, 모바일 가독 확보

**Given** Firewall=0 상태 유지 시간
**When** panel 시각화
**Then** 빨간색 banner + 예상 복귀 시각 (cooldown 기반, Story 3.6 상태 반영)
**And** Firewall=0 시간 누적 gauge `athena_firewall_down_seconds_total`

**Given** anti_ego_events 테이블 쿼리 경로
**When** Grafana → DuckDB 플러그인 또는 Prometheus 경유
**Then** read-only 쿼리만 허용 (Grafana DB user grants)
**And** panel 쿼리 p95 < 300ms (NFR-P4 여유 범위 내)

**Given** Alertmanager 연동
**When** `firewall_status` 0 전환 순간
**Then** Telegram/카카오워크 High 알림 발송 (NFR-O3): "Anti-Ego Firewall activated: reason={bargaining|override_attempt}, expected_recovery={ts}"
**And** 24h 내 3회 이상 활성화 시 Critical 알림 + 자기 회고 prompt 트리거

**Given** FR18 "실시간 확인 가능" 요구
**When** 사용자 대시보드 접근 → 상태 인지까지
**Then** panel load p95 < 3초 (체감 UX 기준)
**And** MVP 초기 scope: 기능적 구현까지, UX polish는 Epic 7 FR47/FR49 완성

**Given** Epic 7 통합 대시보드 경계
**When** Epic 7 Story 7.x 구현 시
**Then** 본 Story의 4개 패널을 "KPI 통합 대시보드" 로 merge (DRY 유지)
**And** 책임 분리: Epic 3 = Anti-Ego 전용 4패널 + Alertmanager rule / Epic 7 = 통합 대시보드 + KPI 선언 조건 패널

---

## Epic 4: Execution & Hard-Locked Exit

**Epic Goal:** KIS Primary Adapter (REST + Orders WebSocket) + broker-agnostic 추상화 경계(NFR-M5) + OrderIntent 소비 파이프라인 + 서버측 OCO Hard Stop Loss(M22, FR20)로 승인된 주문 의도가 KIS로 실행되고, 트레이더 override가 물리적으로 불가능한 손절이 이중화 enforce된다. 오픈 포지션 2차 미분 손실 가속도 감시(M19, FR19)로 파열적 하락을 조기 감지하고, 이벤트 캘린더 근접도 Alert(M16 MVP, FR21)로 V1.1+ 자동 축소 이전에도 이벤트 blind spot을 수동 방어한다. M22 OCO·Epic 5 Kill Switch·Epic 5 heartbeat auto-flatten 3가지 청산 경로를 단일 기록 파이프라인으로 통합(FR22)하여 모든 청산이 `orders` + Pre-Trade Ledger 에 일관 스키마로 남는다. 증권사 교체 seam은 Secondary Adapter 추상화(FR37)로 MVP 경계만 제공하고 실구현은 V1.1+ 로 유예한다.

### Story 4.1: Broker Adapter Abstraction + KIS Primary REST

As Khuk0's Execution layer,
I want broker-agnostic `BrokerAdapter` Protocol 추상화와 python-kis 기반 KIS REST Primary 구현을 확보하여,
So that 증권사 교체 비용이 interface 구현만으로 최소화되고(NFR-M5), KIS REST 주문·조회 경로가 token-bucket throttle 위에서 안정 작동한다(NFR-I1).

**Acceptance Criteria:**

**Given** `athena-execution/broker/protocol.py` 정의
**When** `BrokerAdapter` Protocol 선언
**Then** async 메서드: `place_order(intent: OrderIntent) -> OrderResult`, `cancel_order(order_id: str) -> bool`, `get_position(symbol: str) -> Position`, `get_account_balance() -> Balance`, `place_oco(order: OcoRequest) -> OcoResult`
**And** 모든 DTO Pydantic, 필수 필드 (`user_id`, `timestamp_kst`, `module_version`, `policy_version_git_sha`) 일관 (NFR-M1, NFR-I4)

**Given** `athena-execution/broker/kis_primary.py` 구현
**When** python-kis 클라이언트 초기화
**Then** OS Keychain에서 `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_NO` 조회 (NFR-S1), 주문 key와 조회 key 별도 저장 (NFR-S2)
**And** `settings.environment ∈ {prod, paper}` 에 따라 실계좌/모의계좌 switch, 동일 adapter 코드 공유 (AR-EXT3)

**Given** KIS REST 호출
**When** token-bucket throttle 적용
**Then** 20 req/s 상한 (NFR-I1), asyncio.Semaphore + 토큰 보충 task로 async-safe 구현, 버킷 소진 시 대기 + 요청 순서 보장
**And** Prometheus histogram `athena_kis_rest_duration_seconds` + `athena_kis_token_bucket_depth` gauge

**Given** KIS 응답 에러 `EGW00201` (rate limit 초과)
**When** 감지
**Then** 지수 백오프 재시도 최대 3회 (1s, 2s, 4s), 3회 실패 시 `KIS_RATE_LIMIT` error_code raise (AR-COM3)
**And** `athena_kis_retry_total{error_code}` counter + retry 이력 구조화 JSON 로그 (NFR-O1)

**Given** KIS 네트워크 장애 또는 5xx 에러 누적 3회
**When** Primary Adapter 실패 상태 전환
**Then** Secondary Adapter fallback hook 호출 (`self.secondary.place_order(...)`) — V1.1+ 실구현 연계
**And** MVP scope: Secondary는 `NotImplementedError("Secondary Adapter deferred to V1.1+")` raise + `athena_broker_fallback_attempt_total` counter + 주문 의도는 `rejection_reason='broker_unavailable'` 기록 (Epic 6 Ledger 연계)

**Given** Protocol 준수 테스트
**When** KIS Primary + in-memory mock Secondary 각각 `BrokerAdapter` 의존성 주입
**Then** 동일 interface 로 `place_order`/`cancel_order` 호출 가능 (NFR-I4 duck typing 준수)
**And** pytest `tests/integration/test_broker_protocol.py` 통과 (mock KIS, 실 API 호출 없음)

### Story 4.2: KIS Orders WebSocket (체결·포지션 실시간 구독)

As Khuk0's Execution layer,
I want KIS Orders WebSocket으로 체결 통지와 포지션 변화를 실시간 수신하여,
So that 주문 상태 전환이 < 5초 latency로 `orders` 테이블과 M19 감시(Story 4.5)·Firewall aggregator(Story 3.6)로 전달된다(NFR-I2).

**Acceptance Criteria:**

**Given** `athena-execution/broker/kis_ws_orders.py` + Story 4.1 broker_adapter 인스턴스
**When** WebSocket 세션 시작
**Then** 주문 체결·포지션 변화 채널 구독 (Epic 1 Story 1.7의 L2 구독과 별도 세션)
**And** 41 구독/세션 상한 준수 (NFR-I2), 포지션 채널은 전체 오픈 종목 wildcard 구독 (구독 수 절감)

**Given** 체결 통지 수신
**When** KIS 응답 파싱
**Then** `OrderFill(user_id, symbol, order_id, filled_price, filled_qty, filled_at_kst, remaining_qty, fees, side)` DTO 생성 + `broker_to_orchestrator_q` enqueue (AR-COM5)
**And** `orders` 테이블 UPDATE (fill 정보 반영, 원본 row INSERT는 Story 4.3)

**Given** WebSocket 연결 장애 (`No close frame received` 또는 네트워크 단절)
**When** 자동 재연결
**Then** python-kis 재연결 + 구독 자동 재등록 + 재연결 직후 `get_outstanding_orders()` 호출로 상태 동기화 (놓친 체결 복구)
**And** `athena_kis_orders_ws_reconnect_total` counter 증가 + Medium 알림 (NFR-O3)

**Given** 포지션 변화 이벤트
**When** 수신
**Then** in-memory position tracker 갱신 (Story 4.5 M19가 직접 참조)
**And** Prometheus `athena_open_positions_count` gauge + `athena_position_pnl_percent{symbol}` gauge 실시간 업데이트

**Given** Orders WebSocket uptime 측정
**When** 월간 집계
**Then** ≥ 99% (NFR-R1 L2 로거 동급), 장중 기준 월 downtime < 6시간 30분
**And** 미달 시 paper-only 자동 전환 플래그 set (Epic 5 자동 전환 로직 연계 hook)

**Given** 장애 중 신규 주문 시도
**When** WebSocket 단절 감지
**Then** Story 4.3의 OrderIntent Consumer가 해당 기간 신규 주문을 reject (`rejection_reason='orders_ws_unavailable'`) + `HEARTBEAT_LOST` error_code 로그 (AR-COM3, NFR-I5 graceful)
**And** `athena_kis_orders_ws_degrade_total` counter 증가

### Story 4.3: OrderIntent Consumer + 주문 발행 Pipeline

As Khuk0's Execution layer,
I want Epic 3 Story 3.7의 `OrderIntent` DTO를 수신하여 Story 4.1 KIS Primary로 주문을 발행하고 `orders` 테이블에 원본 row를 INSERT 하여,
So that 이중 조건 Entry Gate를 통과한 모든 주문 의도가 추적 가능한 execution 경로를 탄다.

**Acceptance Criteria:**

**Given** `orchestrator_to_execution_q` (AR-COM5, bounded 1000) + `athena-execution/consumer.py`
**When** `OrderIntent` 수신
**Then** Story 4.1의 `adapter.place_order(intent)` 비동기 호출 → `OrderResult(order_id, status, placed_at_kst)` 반환
**And** 장중 블로킹 경로 NFR-P5 준수, 외부 호출 대기는 async await만

**Given** `orders` 테이블 미초기화
**When** 테이블 생성 스크립트 실행 (본 Story 소유)
**Then** 스키마: `id` (PK), `user_id`, `order_id` (KIS 반환), `parent_order_id` (청산 시 entry 참조), `symbol`, `side` (buy/sell), `intended_qty`, `filled_qty`, `intended_price`, `filled_price_avg`, `status` (placed/filled/partial/cancelled/rejected), `event_type` (entry/oco_stop/kill_switch_symbol/kill_switch_account/auto_flatten/manual_event_reduce), `s_entry`, `firewall_status`, `policy_version_git_sha`, `param_hash`, `placed_at_kst`, `filled_at_kst`, `cancelled_at_kst`, `rejection_reason`, `oco_stop_order_id`, `oco_tp_order_id`, `pnl_realized`
**And** NFR-M4 `user_id` 유지 + UNIQUE 제약 `(user_id, order_id)`

**Given** 주문 발행 성공
**When** KIS 응답 수신
**Then** `orders` INSERT (status='placed', order_id=KIS 반환값, event_type='entry') + OrderIntent의 `s_entry`·`firewall_status`·`policy_version_git_sha`·`param_hash` 모두 기록 (NFR-M1 감사 필드)
**And** Pre-Trade Ledger writer interface 호출 (Epic 6 FR38 구현, 본 Story는 seam만)

**Given** KIS 응답 에러 (잔고 부족, 거래정지 종목, HardKill 누락 등)
**When** 에러 분류
**Then** `orders` INSERT (status='rejected', rejection_reason={KIS error_code}) + Medium 알림 (NFR-O3)
**And** `athena_order_reject_total{reason}` counter 증가 + 구조화 JSON 로그

**Given** Story 4.2 체결 통지 도착
**When** `broker_to_orchestrator_q` consume
**Then** `orders` UPDATE (status='filled' 또는 'partial', filled_qty, filled_price_avg, filled_at_kst) + Story 4.4 M22 OCO 등록 트리거 호출
**And** 부분 체결(partial) 케이스는 잔여 수량에 대해 OCO 미등록 (전량 체결 시점에서만 등록)

**Given** 주문 발행 end-to-end latency
**When** OrderIntent 수신 → orders INSERT 완료까지
**Then** p99 < 1초 (KIS REST 응답 포함), Prometheus histogram `athena_order_placement_duration_seconds`
**And** 1초 초과 시 High 알림 (NFR-O3) + 원인 분석 trace_id 로그 (NFR-O4)

### Story 4.4: M22 서버측 OCO Hard Stop Loss

As Khuk0 needing stop loss that I physically cannot override,
I want 체결 성공 직후 KIS 서버측 OCO 주문(stop loss + take profit)을 즉시 등록하여,
So that 손절이 서버측에서 이중화 enforce되고 트레이더 override가 물리적으로 불가능해진다(FR20).

**Acceptance Criteria:**

**Given** Story 4.3 체결 통지 수신 (status='filled' 전환)
**When** `athena-execution/oco/hard_stop.py` 호출
**Then** 체결 통지 도착 후 OCO 등록 완료까지 latency p99 < 500ms (NFR-P5 비블로킹 경로)
**And** `athena_m22_oco_registration_duration_seconds` histogram

**Given** OCO 파라미터 계산
**When** stop price + take profit price 산출
**Then** stop_price = `filled_price_avg × (1 - stop_loss_pct)`, tp_price = `filled_price_avg × (1 + take_profit_pct)` — stop_loss_pct / take_profit_pct는 `policy.toml` (AR-CFG4, F5 읽기전용 마운트 대상)
**And** 두 price는 `orders` 테이블 UPDATE 로 기록 (oco_stop_order_id, oco_tp_order_id 컬럼)

**Given** KIS OCO 주문 REST 호출
**When** Story 4.1의 `adapter.place_oco(...)` 실행
**Then** 서버측 OCO 주문 등록 성공 → `OcoResult(stop_order_id, tp_order_id, registered_at_kst)` 반환 → `orders` UPDATE
**And** OCO 등록 실패 시 Critical 알림 (NFR-O3) + 해당 포지션 시장가 수동 청산 fallback (NFR-I5) + `exit_type='manual'` 기록

**Given** 트레이더가 KIS MTS 앱에서 OCO 주문 취소 시도
**When** Story 4.2 Orders WebSocket이 취소 이벤트 감지
**Then** `anti_ego_events` append `event_type='OVERRIDE_ATTEMPT'`, payload={action='oco_cancel_attempt', order_id, mts_uid} (Story 3.1 writer 사용)
**And** 즉시 동일 OCO 자동 재등록 + 3회 반복 시 Symbol CB 발동 hook (Epic 5 Story 5.x 연계)

**Given** OCO stop 발동 (KIS 서버측 체결)
**When** Story 4.2 체결 통지 수신
**Then** `orders` INSERT (event_type='oco_stop', parent_order_id=원본 entry, status='filled') + Story 4.7 `exit_recorder.record(ExitEvent)` 호출
**And** realized P&L 계산 `(exit_price - entry_price) × qty - fees` → `pnl_realized` 컬럼 + Pre-Trade Ledger hook

**Given** integration 테스트 (mock KIS)
**When** 체결 → OCO 등록 → mock 가격 하락 → OCO stop 발동 시뮬레이션
**Then** 전체 경로: 주문 → 체결 → OCO 등록 → stop 발동 → 청산 기록 검증 + override 시도 시 재등록 + anti_ego_events 기록 검증
**And** pytest `tests/integration/test_m22_oco.py` 통과

### Story 4.5: M19 손실 가속도 (2차 미분) 감시

As Khuk0's Execution layer monitoring open positions,
I want 오픈 포지션의 P&L 시계열에서 손실의 2차 미분(가속도)을 실시간 계산하여 파열적 하락을 감지하여,
So that OCO stop 발동 이전에도 비정상 가격 붕괴가 조기 감지되고 사전 경보·분석 근거가 축적된다(FR19).

**Acceptance Criteria:**

**Given** `athena-execution/m19/loss_accel.py` + Story 4.2 in-memory position tracker
**When** tick 수신 (L2 logger Epic 1 Story 1.7 → Parquet shard → DuckDB external scan)
**Then** 종목별 P&L 시계열 업데이트, rolling window 5분 (`policy.toml`, F5 대상 AR-CFG4)
**And** window 크기 수정 시도는 장중 불가 (AR-SEC3 읽기전용 마운트)

**Given** P&L 시계열 `p(t)`
**When** 1차 미분 (속도) + 2차 미분 (가속도) 계산
**Then** numerical 안정성 위해 Savitzky-Golay 필터 (window=5, polyorder=2) 또는 EMA smoothing 적용
**And** 계산 latency p95 < 50ms per position (NFR-P4 여유 범위 내), `athena_m19_compute_duration_seconds` histogram

**Given** 2차 미분 threshold 초과 (예: `d²p/dt² < -0.5%/min²`, `policy.toml`)
**When** 파열적 하락 감지
**Then** `m19_event(symbol, pnl_velocity, pnl_acceleration, timestamp_kst)` emit → `modules_output` INSERT
**And** `athena_m19_acceleration_alert_total{symbol}` counter + Medium 알림 (NFR-O3)

**Given** M19 이벤트 발생
**When** 후속 액션
**Then** (a) Prometheus gauge `athena_m19_worst_acceleration` 업데이트, (b) Grafana 패널 hook (Epic 7 Story 7.x 완성), (c) OCO stop threshold 동적 tightening은 V1.1+ 유예 (MVP 초기 감지·기록까지만)
**And** MVP scope: monitoring + alert + 기록, 자동 축소·동적 stop tightening 금지

**Given** 데이터 결측 또는 tick 간격 > 30초
**When** M19 계산 시도
**Then** `DATA_STALE` error_code (AR-COM3) → degrade (NFR-I5), 다음 유효 tick 도착 시 window 재구성
**And** `athena_m19_data_stale_total{symbol}` counter + 일별 rate > 10% 시 High 알림

**Given** 단위 테스트 fixture (정상 random walk vs 파열적 하락 시뮬레이션)
**When** M19 실행
**Then** 파열 시나리오 (급격한 -5%/5min drop)에서 정확 탐지 + 정상 walk false positive rate < 5%
**And** pytest `tests/integration/test_m19_loss_accel.py` 통과, 결정론적 seed (AR-TEST2)

### Story 4.6: 이벤트 캘린더 + 근접도 Alert (M16 MVP scope)

As Khuk0 managing event risk manually in V1.0,
I want 이벤트 캘린더(실적·FOMC·옵션만기 등)를 수동 관리하고 이벤트 근접 시 단계별 Alert를 받아,
So that FR21 M16 "자동 포지션 축소"는 V1.1+ 로 유예하면서도 MVP에서 이벤트 blind spot을 수동 방어할 수 있다.

**Acceptance Criteria:**

**Given** `config/event_calendar.toml` (수작업 관리, git version controlled)
**When** 이벤트 등록
**Then** 스키마: `[[event]] event_type, event_name, event_timestamp_kst, affected_symbols: [...] | "all", severity ∈ {low, medium, high}, source (data 출처), added_by_git_sha`
**And** event_type enum = {earnings, fomc, opex, korea_rate, us_cpi, custom}, 추가 enum은 Change Control 필요 (NFR-M3)

**Given** `athena-orchestrator/event_proximity.py` + 시그널 생성 경로
**When** 시그널 생성 시점
**Then** 24h 내 예정 이벤트 조회 + 영향 symbol 매칭 (`affected_symbols='all'` 은 전역 매칭)
**And** 매칭된 이벤트 정보를 `OrderIntent.meta.proximate_events` 에 첨부 (NFR-M1)

**Given** 이벤트 근접 3단계 (T-24h, T-2h, T-30min)
**When** 임박 감지
**Then** Alertmanager 단계별 발송: T-24h Medium, T-2h High, T-30min Critical (NFR-O3) via Telegram/카카오워크
**And** `athena_event_proximity_alert_total{event_type, severity, stage}` counter

**Given** 고위험 이벤트 (`severity='high'`) + 오픈 포지션 존재
**When** T-30min 도달
**Then** Grafana persistent banner + 수동 축소 권고 "Event {name} @ {ts}, consider reducing position {symbol}"
**And** MVP scope: alert + banner 표시만, 자동 축소 금지 (V1.1+ M16 유예)

**Given** V1.1+ M16 자동 축소 seam
**When** 현재 MVP
**Then** `athena-execution/m16/auto_reduce.py` 에 `NotImplementedError("M16 auto-reduce deferred to V1.1+")` placeholder 함수 존재 (seam 보존)
**And** 수동 축소 실행 시 `orders` INSERT `event_type='manual_event_reduce'` 로 추적 + Story 4.7 exit_recorder 경로 활용

**Given** 캘린더 수동 편집
**When** `event_calendar.toml` 수정 → git commit
**Then** F5 읽기전용 마운트 대상 **아님** (policy.toml / flag_registry.toml 와 분리 관리) — 중요 이벤트 추가는 장중 즉시 반영 필요
**And** 편집 이력은 git log로 추적, 정책 파일과 달리 72h cooling 비대상 (속보 대응)

### Story 4.7: 청산 이벤트 orders + Ledger 통합 기록

As Khuk0 ensuring every exit is audit-traceable,
I want M22 OCO stop·Kill Switch(Epic 5)·heartbeat auto-flatten(Epic 5) 3가지 청산 경로를 단일 기록 파이프라인으로 통합하여,
So that 모든 청산이 `orders` + Pre-Trade Ledger(Epic 6 FR38) 에 일관 스키마로 남고, 사후 재현·감사 가능해진다(FR22).

**Acceptance Criteria:**

**Given** `athena-execution/exit_recorder.py` + 단일 entrypoint `record(event: ExitEvent)`
**When** 청산 이벤트 수신 (M22 Story 4.4 / Kill Switch·auto-flatten Epic 5 hook)
**Then** `ExitEvent(user_id, symbol, exit_type, trigger_order_id, exit_qty, exit_price_avg, pnl_realized, exit_timestamp_kst, policy_version_git_sha, param_hash)` DTO 검증 + 스키마 필수 필드 보장
**And** exit_type ∈ {oco_stop, kill_switch_symbol, kill_switch_account, auto_flatten, manual, manual_event_reduce} (AR-COM3 확장)

**Given** `orders` 테이블 event_type 컬럼
**When** 청산 기록 INSERT
**Then** event_type = `ExitEvent.exit_type` + `parent_order_id` = 원본 entry order 참조
**And** 원본 entry row는 status UPDATE (status='filled' 또는 'partial_filled') 로 sync

**Given** Pre-Trade Ledger writer (Epic 1 Story 1.5 infrastructure + Epic 6 FR38 실구현)
**When** 청산 발생
**Then** Ledger writer interface 호출 `writer.append(event_type='exit', payload=ExitEvent)` (seam only, 본 Story는 interface call까지)
**And** 실 SHA-256 체인 append 는 Epic 6에서 완성, 책임 분리 명시

**Given** Epic 5 Kill Switch 또는 auto-flatten 청산 경로
**When** Epic 5 Story 5.x 구현 시
**Then** Epic 5 모듈은 trigger 조건 판정만 담당, 실제 기록은 본 Story의 `exit_recorder.record(...)` 호출 (DRY)
**And** 책임 분리: Epic 5 = trigger 조건 + CB state machine / Epic 4 = 기록·orders·Ledger hook

**Given** 청산 이벤트 기록 latency
**When** M22 stop 체결 → orders UPDATE + Ledger hook 호출까지
**Then** p99 < 500ms (NFR-P5 비블로킹 경로), `athena_exit_recording_duration_seconds` histogram
**And** 500ms 초과 시 High 알림 + trace_id 로그 (NFR-O4)

**Given** 3가지 exit_type 통합 테스트
**When** 각 시나리오 시뮬레이션 — (1) M22 OCO 발동, (2) Kill Switch mock trigger 주입, (3) heartbeat timeout mock
**Then** 3가지 모두 `orders.event_type` 정확 + Ledger writer mock 호출 정확 + DTO schema 일치
**And** pytest `tests/integration/test_exit_recorder.py` 통과

---

## Epic 5: Operational Defense & Risk Kill Switch

**Epic Goal:** 운영 품질 방어(슬리피지 tick 실측·discount, 3종목·테마 중복 상한, 뉴스 30초 drop, NLP confidence degrade, 취소·재주문 throttle) + 4층 Circuit Breaker 독립 state machine(Global -3% / Account MDD -8% cascade / Session 3회 손절 / Symbol M22 연계) + heartbeat monitoring(blackbox_exporter 기반 5분 push · 4h 서버측 auto-flatten · Logger uptime 미달 paper-only 자동 전환)으로 구성된 독립 자동 방어선. 운영 품질 저하와 시장 shock에 대한 독립적 자동 방어선이 작동하여 파산 시나리오를 차단하고, 장애 상황에서도 시스템이 자동 청산으로 안전 상태에 수렴한다.

### Story 5.1: Slippage tick 실측 + S_entry × 0.5 Discount

As Khuk0's Operational Defense layer,
I want 주문 의도가(시그널가) vs 실제 체결가의 슬리피지를 tick 단위로 실측하고 > 0.3% 시 동일 신호의 S_entry × 0.5 discount를 자동 적용하여,
So that 시장 마찰(유동성 부족·호가 슬리피지)이 수익성을 잠식하는 시나리오가 정량 지표로 자동 차단된다(FR23, FR24).

**Acceptance Criteria:**

**Given** `athena-ops-defense/slippage.py` + Epic 4 Story 4.3의 `OrderIntent.intended_price` + Epic 4 Story 4.2의 `OrderFill.filled_price`
**When** 체결 통지 수신
**Then** `realized_slippage_pct = (filled_price - intended_price) / intended_price` 계산 (매수는 positive=불리, 매도는 부호 반전) + `modules_output` INSERT `(module='slippage', value=realized_slippage_pct, order_id, symbol, timestamp_kst)`
**And** tick 단위 정밀도 (반올림 금지, 소수 6자리 유지)

**Given** 슬리피지 시계열
**When** Prometheus histogram `athena_slippage_pct` 업데이트
**Then** 월간 p50/p95/p99 분포 집계 + Grafana 패널 hook (Epic 7)
**And** 일별 평균 슬리피지 > 0.15% 시 Medium 알림 (NFR-O3)

**Given** `realized_slippage_pct > 0.3%` 감지
**When** 동일 신호 패턴 식별 (같은 symbol + 같은 시간대 bucket + 같은 테마)
**Then** discount state DB (`slippage_discount` 테이블) INSERT: `(pattern_key, discount_factor=0.5, expires_at=placed_at+24h)`
**And** 24h 후 자동 expire (rolling window, `policy.toml` 설정 가능 AR-CFG4)

**Given** 시그널 생성 경로 (Epic 2 Story 2.8 S_entry 집계 직후)
**When** orchestrator 가 discount lookup
**Then** 해당 pattern_key 에 활성 discount 존재 시 `S_entry × 0.5` 적용 후 decision gate로 전달
**And** M25 리포트(Story 2.9)에 discount 적용 기록 `discount_applied: {factor: 0.5, reason: 'high_slippage', source_pattern_key}`

**Given** discount 적용 중 후속 주문이 동일 패턴 체결
**When** 슬리피지 재측정
**Then** 슬리피지 ≤ 0.3% 시 discount 즉시 해제 (단, 최근 3회 모두 ≤ 0.3% 조건, 단발 개선은 무시)
**And** 해제 이벤트 `athena_slippage_discount_clear_total{pattern_key}` counter

**Given** integration 테스트 (mock KIS)
**When** 의도가 100원 → 체결 101원 (1% slippage) 시나리오 주입
**Then** `slippage_discount` 테이블 row 생성 확인 + 동일 패턴 후속 신호에서 S_entry × 0.5 적용 확인
**And** pytest `tests/integration/test_slippage_discount.py` 통과

### Story 5.2: Portfolio 동시 상한 (3종목) + 테마 중복 금지

As Khuk0's Operational Defense layer,
I want 동시 오픈 포지션 수를 3종목 상한으로 enforce하고 동일 테마·섹터 2종목 이상 동시 보유를 금지하여,
So that 집중 리스크와 테마 상관관계 폭발이 구조적으로 차단된다(FR25, FR26).

**Acceptance Criteria:**

**Given** `athena-ops-defense/portfolio.py` + Epic 4 Story 4.2 in-memory position tracker
**When** 신규 OrderIntent 도착 (Epic 3 Story 3.7 dual gate 통과 후)
**Then** 현재 open position count 조회 (`SELECT COUNT(*) FROM orders WHERE status IN ('placed','filled','partial') AND event_type='entry' AND user_id=?`)
**And** count ≥ 3 시 `rejection_reason='portfolio_limit_exceeded'` 로 reject + Medium 알림

**Given** 신규 OrderIntent 의 symbol 테마·섹터 정보
**When** `config/universe.toml` 의 `[theme_mapping]` 참조 (KRX 공식 섹터 + 커스텀 테마 e.g. '2차전지_양극재', '반도체_메모리')
**Then** 현재 오픈 포지션 중 동일 테마·섹터 존재 여부 확인
**And** 동일 테마 포지션 ≥ 1 시 `rejection_reason='theme_concentration'` 로 reject (신규 진입 포함 ≥ 2 금지)

**Given** `orders` 테이블 상태 조회 latency
**When** Portfolio 체크 실행
**Then** p99 < 100ms (DuckDB local query, NFR-P4 여유 범위)
**And** Prometheus histogram `athena_portfolio_check_duration_seconds`

**Given** 테마 매핑 누락 종목 (universe.toml 에 테마 미지정)
**When** Portfolio 체크 실행
**Then** 보수적 처리: `theme='unknown'` 취급, 모든 unknown 종목은 서로 동일 테마로 간주 (false-safe)
**And** `athena_theme_mapping_missing_total{symbol}` counter + 월간 누락 > 5종목 시 High 알림 + universe.toml 업데이트 trigger

**Given** 상한 조정 요구 (V1.1+ 자본 증가 시)
**When** `policy.toml` 의 `max_concurrent_positions` 파라미터 조회
**Then** MVP default=3, Change Control 필요 (NFR-M3, 72h cooling 통과 후 변경)
**And** F5 읽기전용 마운트 대상 (AR-CFG4)

**Given** 거부 기록 audit
**When** Portfolio 제약으로 reject 발생
**Then** `orders` INSERT `status='rejected'`, rejection_reason, param_hash, policy_version_git_sha + M25 리포트 생성
**And** `athena_portfolio_reject_total{reason}` counter ({reason ∈ 'portfolio_limit_exceeded', 'theme_concentration'})

### Story 5.3: Data Quality Guardrails — 뉴스 30초 Drop + NLP Confidence Degrade

As Khuk0's Operational Defense layer,
I want 뉴스 피드 타임스탬프가 30초 초과 지연 시 해당 신호를 drop하고 NLP 모델 confidence가 임계값 이하인 feature를 neutral(1) 로 자동 처리하여,
So that 오래된 신호와 낮은 품질 NLP 출력이 S_entry 집계를 오염시키지 않는다(FR27, FR28).

**Acceptance Criteria:**

**Given** `athena-ops-defense/data_quality.py` + 뉴스 DTO (Epic 1 Story 1.8 수집, `published_at_kst` + `fetched_at_kst`)
**When** 시그널 생성 시점 뉴스 소비
**Then** `lag_seconds = (now_kst - published_at_kst).total_seconds()` 계산
**And** `lag_seconds > 30` 시 해당 뉴스 기반 시그널 drop + `rejection_reason='stale_news'` 기록

**Given** drop 통계
**When** Prometheus counter `athena_news_drop_stale_total{source}` 업데이트
**Then** 일별 drop rate 집계 + 소스별 (dart/naver/daum/yonhap/maekyung/hankyung) breakdown
**And** 일별 특정 소스 drop rate > 20% 시 High 알림 (소스 장애 가능성)

**Given** orchestrator 레벨 confidence aggregator (Epic 2 Story 2.2 M1 + Story 3.4 F1 통합)
**When** NLP 모듈 confidence 측정값 전달
**Then** `confidence < threshold` (기본 0.3, `policy.toml`) 감지 시 해당 flag degrade 경로 호출 (Story 2.10 `degrade.py` 사용, DRY)
**And** error_code `CONFIDENCE_BELOW_THRESHOLD` (AR-COM3) + reason_code 일관

**Given** M1 + F1 이외 향후 추가될 NLP 모듈 seam
**When** 새 NLP 모듈 등록
**Then** 공통 interface `NLPModule.detect(text) -> (value, confidence)` 준수 + data_quality.py 의 central threshold 경로 자동 적용
**And** NLP 모듈 추가는 Change Control 1건 소모 (NFR-M3)

**Given** 30초 지연 threshold 조정 요구
**When** `policy.toml` 의 `news_stale_threshold_seconds` 파라미터
**Then** F5 읽기전용 대상 (AR-CFG4), 장중 수정 시도 시 Story 3.5 OVERRIDE_ATTEMPT 기록
**And** default=30, 변경은 72h cooling + Paper 재검증

**Given** integration 테스트
**When** 뉴스 `published_at_kst = now - 45s` 시나리오 주입
**Then** 해당 뉴스 drop 확인 + `athena_news_drop_stale_total{source='test'}` counter 증가 확인
**And** pytest `tests/integration/test_data_quality.py` 통과

### Story 5.4: 취소·재주문 Throttle

As Khuk0's Operational Defense layer,
I want 취소·재주문 패턴을 자동 throttle하여,
So that 과도한 취소·재주문으로 인한 시장 마찰·거래소 제재가 operational 계층에서 선제 차단된다(FR29).

**Acceptance Criteria:**

**Given** `athena-ops-defense/throttle.py` + Epic 4 Story 4.3 주문 발행 경로
**When** 새 OrderIntent 도착
**Then** 직전 60초 내 동일 symbol 취소 건수 조회 (`orders` WHERE cancelled_at_kst > now - 60s AND symbol=?)
**And** 취소 건수 ≥ 3 시 해당 symbol 재주문 60초간 throttle (`rejection_reason='throttle_cancel_pattern'`)

**Given** 취소율 rolling window (10분 기준)
**When** 취소 건수 / 전체 주문 건수 계산
**Then** 비율 > 20% 시 Medium 알림 + 신규 주문 Throttle (소프트 제한, 분당 주문 수 * 0.5 적용)
**And** `athena_cancel_rate_10min` gauge 실시간 업데이트

**Given** §176 FR40 하드 제한 (취소율 < 30%, 분당 주문 상한)
**When** Epic 6 FR40 구현 경계
**Then** 본 Story(5.4)는 operational soft throttle 담당 + Epic 6 FR40 은 규정 compliance hard block 담당 (책임 분리)
**And** 두 계층 모두 실패 시 Pre-Trade Ledger reject 기록 (Epic 6)

**Given** throttle 상태 expose
**When** 대시보드 접근
**Then** 현재 throttle 활성 symbol 목록 + expire_at 표시 (Grafana hook, Epic 7)
**And** `athena_throttle_active_symbols` gauge

**Given** KIS API 측 차단 선행 가능성
**When** KIS 응답에 `throttle` 관련 에러 코드 도착
**Then** KIS adapter(Story 4.1) 가 `EGW_THROTTLE` 로 translate + 본 Story throttle state 자동 연장 (NFR-I5 graceful)
**And** `athena_kis_throttle_response_total` counter

**Given** throttle 해제 조건
**When** 60초 경과 + 해당 symbol 취소 이벤트 없음
**Then** throttle expire + 신규 주문 허용
**And** pytest `tests/integration/test_throttle.py` 통과 (mock 시나리오: 3회 취소 → throttle → 60s 대기 → 해제 → 재진입 성공)

### Story 5.5: 4층 CB State Machine 공통 기반

As Khuk0's Risk Kill Switch layer,
I want Global·Account·Session·Symbol 4층 Circuit Breaker가 공유하는 독립 state machine 공통 기반 모듈을 확보하여,
So that 4개 CB가 서로 coupling 없이 독립적으로 발동·해제되고(FR30), 각 계층의 trigger·expire·reset 로직이 일관된 패턴으로 구현된다.

**Acceptance Criteria:**

**Given** `athena-ops-defense/kill_switch/base.py` 공통 CB abstract class
**When** `CircuitBreaker` ABC 선언
**Then** 메서드: `check_trigger(context) -> bool`, `arm(reason, trigger_event)`, `disarm(reason)`, `is_armed() -> bool`, `get_state_snapshot() -> dict`
**And** state enum `{DISARMED, ARMED, COOLING, PAPER_ONLY_SUSPENDED}`, 전환 그래프 명시적 정의

**Given** CB 상태 persistence
**When** state 변화 발생
**Then** `circuit_breaker_events` 테이블 INSERT: `(cb_layer, from_state, to_state, reason, trigger_payload_json, policy_version_git_sha, timestamp_utc)`
**And** append-only (UPDATE/DELETE 차단), 재시작 시 최근 state 복구 (crash recovery)

**Given** CB 상태 조회
**When** Epic 3 Story 3.7 dual gate 이전에 `any_cb_armed()` 호출
**Then** 4개 CB 중 하나라도 ARMED 상태면 True 반환, 신규 OrderIntent 즉시 reject (`rejection_reason='cb_armed:{layer}'`)
**And** 조회 latency < 1ms (in-memory state)

**Given** 4층 CB 독립성 보장
**When** Global CB ARMED 전환
**Then** Account·Session·Symbol CB 상태는 영향 없음 (직교 state machine)
**And** 반대 방향도 동일 — 각 CB의 trigger 조건은 독립

**Given** CB 알림 공통 경로
**When** 모든 CB arm/disarm 이벤트
**Then** Alertmanager 라우팅: Global/Account arm = Critical, Session/Symbol arm = High, disarm = Medium (NFR-O3)
**And** Prometheus `athena_circuit_breaker_state{layer}` gauge (0=disarmed, 1=armed, 2=cooling, 3=paper_only_suspended)

**Given** Manual override 절대 금지 원칙
**When** 사용자가 CB 상태를 코드·config로 강제 해제 시도
**Then** F5 읽기전용 마운트(Epic 1 Story 1.6) + SSH signed commit 요구(NFR-A5) 로 장중 물리 차단 + Story 3.5 OVERRIDE_ATTEMPT 기록
**And** Account CB 수동 해제는 Story 5.7의 Paper 재통과 cascade 완료 후에만 허용

### Story 5.6: Global CB — 일일 -3% 발동 + 익일 자동 재개

As Khuk0's Global risk floor,
I want 일일 실현·미실현 손실 합계가 -3% 도달 시 Global CB를 발동하여 당일 신규 진입을 전면 차단하고 익일 00:00 KST 자동 재개하여,
So that 최악의 1일이 파산 시나리오로 이어지는 경로가 하드 차단된다(FR31).

**Acceptance Criteria:**

**Given** `athena-ops-defense/kill_switch/global_cb.py` extends `CircuitBreaker` (Story 5.5)
**When** 실시간 daily P&L 계산 (`realized_pnl_today + unrealized_pnl_now` / `account_balance_start_of_day`)
**Then** 주기: tick 도착마다 또는 10초 주기 중 짧은 쪽 (NFR-P4 쿼리 여유)
**And** `athena_daily_pnl_pct` gauge 실시간 업데이트

**Given** `daily_pnl_pct ≤ -3.0%` 도달
**When** Global CB trigger
**Then** `arm(reason='daily_loss_threshold', trigger_payload={pnl_pct, breach_timestamp})` 호출 → 당일 신규 OrderIntent 전면 reject
**And** Critical 알림 즉시 발송 (NFR-O3): Telegram + 카카오워크 + SMS (옵션)

**Given** Global CB ARMED 상태에서 오픈 포지션 존재
**When** 기존 포지션 관리
**Then** 신규 진입만 차단, 기존 M22 OCO stop 은 정상 작동 (기존 포지션 정리는 허용)
**And** M22 exit 로 daily P&L 개선되어도 CB 해제 안 됨 (당일 전체 동결)

**Given** 익일 00:00 KST 도달
**When** 일간 자동 리셋
**Then** `disarm(reason='next_day_auto_reset')` 자동 호출 + daily P&L 누적 리셋
**And** `account_balance_start_of_day` 를 전일 종가 잔고로 재계산

**Given** Global CB 발동 이력 통계
**When** 월간 집계
**Then** 월 3회 이상 발동 시 High 알림 + 정책 재검토 권고 (Epic 8 Bayesian 튜닝 trigger)
**And** `athena_global_cb_arm_total` counter

**Given** integration 테스트 (mock KIS)
**When** 시뮬레이션: 계좌 1000만 원 → -30만 원 (-3%) 도달
**Then** Global CB ARMED + 후속 OrderIntent reject + 익일 자동 disarm 확인
**And** pytest `tests/integration/test_global_cb.py` 통과

### Story 5.7: Account CB — MDD -8% Cascade 복귀 워크플로우

As Khuk0's Account-level capital defense,
I want MDD(Maximum Drawdown)가 -8% 도달 시 주간 중지 + 자본 50% 축소(MTS 수동 + 시스템 paper-only) + 3일 쿨다운 + Paper Trading 1주 재통과 cascade를 enforce하여,
So that 자본 잠식 시나리오에서 복귀 조건이 물리적으로 통과 불가능하지 않다는 경로를 유지하면서도 심리적 재기 압박을 구조적으로 완충한다(FR32).

**Acceptance Criteria:**

**Given** `athena-ops-defense/kill_switch/account_cb.py` extends `CircuitBreaker` + MDD 계산 경로
**When** 실시간 MDD 산출 (`peak_balance_rolling_30d - current_balance) / peak_balance_rolling_30d`)
**Then** 30일 rolling peak 기준, tick 또는 분당 1회 갱신
**And** `athena_mdd_pct` gauge 실시간 업데이트 + Prometheus 30일 보존

**Given** `mdd_pct ≤ -8.0%` 도달
**When** Account CB cascade trigger
**Then** 다음 4단계 state 순차 enforce: (1) 즉시 신규 진입 중단 + 기존 포지션 청산 계획 수립 (5.10 Auto-Flatten과 별개), (2) 주간 중지 (7일 suspension), (3) 자본 50% 축소 체크리스트 emit, (4) 3일 쿨다운 시작
**And** Critical 알림 + 사용자 수동 개입 요구 banner (Grafana persistent)

**Given** 자본 50% 축소 요구 (NFR-S6 수동 체크리스트)
**When** CB cascade 2단계
**Then** 시스템 측: Paper-only 모드 자동 전환 + 실계좌 신규 진입 영구 차단 (수동 해제까지)
**And** 사용자 측: MTS 앱에서 일일·종목별 최대 주문금액 50% 축소 manual checklist (Epic 6 Story 6.x 의 OTP 공증 워크플로우 hook 연계)

**Given** 3일 쿨다운 경과 + 사용자가 Paper 재진입 선언
**When** Paper Trading 1주 재통과 단계
**Then** Paper 계좌로만 1주(7 거래일) 운영 + 해당 기간 Deflated Sharpe > 0 + MDD 재발생 없음 조건 충족 시 prod 복귀 허용
**And** Paper 기간 중 실패 시 cascade 처음부터 재시작 (3일 쿨다운 재적용)

**Given** prod 복귀 조건 충족
**When** 사용자가 수동 disarm 시도
**Then** SSH signed commit 으로 `disarm()` 실행 + 복귀 이벤트 `circuit_breaker_events` 에 payload={paper_trading_days, deflated_sharpe, mdd_paper} 기록 (NFR-A5)
**And** 복귀 직후 Global CB 일일 한도는 정상 -3% 로 복원, Account CB 는 30일 MDD 재계산 baseline 갱신

**Given** 실계좌 잔고 변화 추적
**When** 손실 10% 이상 누적 중 KIS 응답 지연
**Then** boundary 케이스: 실 MDD 측정 불가 시 Conservative fallback (`mdd_pct = max(last_known, -9%)` 취급, fail-safe)
**And** pytest `tests/integration/test_account_cb.py` 통과 (cascade 4단계 전체)

### Story 5.8: Session CB — 연속 3회 손절 2h 쿨다운

As Khuk0's Session-level discipline defense,
I want 연속 3회 손절 발생 시 Session CB 로 2시간 쿨다운을 강제하여,
So that 연속 손절로 인한 감정적 보복매매 패턴이 구조적으로 차단된다(FR33).

**Acceptance Criteria:**

**Given** `athena-ops-defense/kill_switch/session_cb.py` extends `CircuitBreaker` + 연속 손절 카운터
**When** Epic 4 Story 4.4 M22 OCO stop 또는 수동 손절 체결 통지 수신
**Then** `consecutive_stop_count` 증가, `last_stop_timestamp` 갱신
**And** 익절(take profit) 또는 break-even 체결 시 카운터 0 리셋

**Given** `consecutive_stop_count ≥ 3`
**When** Session CB trigger
**Then** `arm(reason='consecutive_stop_3', trigger_payload={stop_order_ids})` + 2시간 쿨다운 시작
**And** High 알림 (NFR-O3) + Grafana banner "Session CB armed: 3 consecutive stops, cooldown 2h"

**Given** Session CB ARMED 상태
**When** 신규 OrderIntent 도착
**Then** 즉시 reject (`rejection_reason='session_cb_armed'`)
**And** 기존 포지션 관리는 영향 없음 (M22 OCO stop 정상 작동)

**Given** 쿨다운 2시간 경과
**When** 자동 disarm check
**Then** `disarm(reason='cooldown_expired')` 호출 + `consecutive_stop_count` 자동 리셋 (2시간 무활동 자체가 쿨다운 효과)
**And** `athena_session_cb_arm_total` counter + 쿨다운 시간 `athena_session_cb_cooldown_seconds` gauge

**Given** 장 마감 cross
**When** Session CB 쿨다운 중 장 마감 도달 (15:30)
**Then** 익일 장 시작 시 카운터 0 리셋 + CB 자동 disarm (장외 시간은 쿨다운 자동 경과)
**And** 단, 매 세션 독립 (어제 3회 손절은 오늘로 carry-over 안 됨)

**Given** integration 테스트
**When** 시뮬레이션: M22 OCO 3회 연속 발동 → Session CB arm → 2h 후 disarm
**Then** 각 state 전환 타임라인 정확 + 중간 신규 OrderIntent reject 확인
**And** pytest `tests/integration/test_session_cb.py` 통과

### Story 5.9: Symbol CB — M22 발동 당일 차단

As Khuk0's Symbol-level re-entry prevention,
I want Epic 4 Story 4.4 M22 OCO stop이 발동된 종목에 대해 당일 Symbol CB를 발동하여 재진입을 물리 차단하여,
So that 동일 종목에서 반복 손절을 쫓아가는 "자극 추종" 패턴이 구조적으로 차단된다(FR34).

**Acceptance Criteria:**

**Given** `athena-ops-defense/kill_switch/symbol_cb.py` extends `CircuitBreaker` + Symbol별 state 관리 (dict 기반)
**When** Epic 4 Story 4.4 M22 OCO stop 발동 이벤트 수신
**Then** 해당 symbol Symbol CB `arm(reason='m22_stop_triggered', payload={stop_order_id, fill_price, pnl_realized})` + 당일 차단 flag set
**And** `athena_symbol_cb_armed_today_total` gauge (현재 armed 종목 수)

**Given** Symbol CB ARMED 종목에 대한 OrderIntent
**When** 신규 진입 시도
**Then** 즉시 reject (`rejection_reason='symbol_cb_armed'`) + M25 리포트(Story 2.9)에 포함
**And** `athena_symbol_cb_reject_total{symbol}` counter 증가

**Given** 장 마감 (15:30 KST)
**When** 일간 자동 리셋
**Then** 모든 Symbol CB 자동 disarm + `circuit_breaker_events` 에 disarm 이벤트 기록
**And** 익일 장 시작 시 모든 symbol 신규 진입 허용 (단, 다른 CB 상태는 독립)

**Given** 동일 종목 복수 M22 발동 (예: 양매수 후 동시 stop)
**When** 두 번째 M22 이벤트 도착
**Then** 이미 ARMED 상태면 state 유지 + `arm_count` 증가 (재arm 기록)
**And** `arm_count ≥ 2` 인 종목은 익일 장 시작 시점에도 CB 유지 (72시간 강화 쿨다운, `policy.toml`)

**Given** Symbol CB 상태 조회
**When** Epic 2 Story 2.8 S_entry 집계 경로에서 종목별 확인
**Then** ARMED 종목의 S_entry 는 즉시 0 반환 (short-circuit 최적화)
**And** 조회 latency < 1ms (in-memory dict)

**Given** integration 테스트
**When** 시뮬레이션: 종목 A M22 stop → Symbol CB arm → 동일 종목 OrderIntent reject → 익일 자동 disarm
**Then** 각 state 전환 + reject 동작 검증
**And** pytest `tests/integration/test_symbol_cb.py` 통과

### Story 5.10: Heartbeat 5분 Push + 4h Auto-Flatten + Paper-only 자동 전환

As Khuk0 needing automatic safe state convergence on system failure,
I want blackbox_exporter 기반 heartbeat 모니터링이 5분 지연 시 모바일 push를 발송하고 4시간 무응답 시 서버측 자동 전량 시장가 청산 + 신규 진입 영구 차단을 실행하며, Logger uptime < 99% 도달 시 paper-only 자동 전환하여,
So that 물리 장애·네트워크 단절·Logger 품질 저하 모든 시나리오에서 시스템이 자동으로 안전 상태로 수렴한다(FR35, FR36, NFR-R1 연계).

**Acceptance Criteria:**

**Given** Epic 1 Story 1.9의 `blackbox_exporter` heartbeat 인프라 + `athena_heartbeat_last_success_timestamp_seconds` 메트릭
**When** Alertmanager rule 정의
**Then** heartbeat 지연 5분 → High 알림 (NFR-R2, NFR-O3): "Heartbeat delayed 5min, expected auto-flatten in 4h" via Telegram/카카오워크 + Critical 수준 별도 SMS 옵션
**And** `athena_heartbeat_delay_seconds` gauge 실시간 업데이트

**Given** heartbeat 지연 4시간 경과
**When** `athena-auto-flatten.service` systemd trigger (NFR-R2 4h 임계)
**Then** 서버측 자동 전량 시장가 청산 실행: `get_open_positions()` → 각 포지션에 `place_order(side=opposite, qty=full, price=market)` 호출
**And** 각 청산은 Epic 4 Story 4.7 `exit_recorder.record(ExitEvent(exit_type='auto_flatten'))` 경로로 기록

**Given** auto-flatten 실행 완료
**When** 신규 진입 영구 차단 mode enter
**Then** Account CB state = `PAPER_ONLY_SUSPENDED` 로 전환 (Story 5.5 state enum) + 수동 SSH signed commit + OTP 2FA 로만 해제 가능 (NFR-A5)
**And** Critical 알림 "Auto-flatten executed, {N} positions closed, manual reset required"

**Given** Logger PC uptime 모니터링 (Epic 1 Story 1.7 AC#5 의 flag 소비)
**When** 월간 uptime < 99% (NFR-R1 미달) 판정
**Then** paper-only 자동 전환 (실계좌 신규 진입 차단, paper 계좌만 허용) + High 알림
**And** 익월 uptime 회복 시 수동 SSH signed commit 으로 prod 복귀

**Given** 수동 해제 시도
**When** 사용자가 auto-flatten mode 해제
**Then** (1) SSH signed commit 필수 (NFR-A5), (2) 원인 분석 report (payload={downtime_start, downtime_end, auto_flattened_positions, total_loss_realized}) 제출 필수, (3) 72h cooling 통과 (NFR-R5)
**And** 해제 이력은 `anti_ego_events` + `circuit_breaker_events` 양쪽 append

**Given** integration 테스트 (mock heartbeat)
**When** 시뮬레이션: heartbeat 5분 지연 → push 발송 → 4h 지연 → auto-flatten 실행
**Then** 5분 push 확인 + 4h 후 `get_open_positions()` 호출 + 각 symbol `place_order(market)` 실행 + `ExitEvent(exit_type='auto_flatten')` 기록 + `PAPER_ONLY_SUSPENDED` state 전환
**And** pytest `tests/integration/test_auto_flatten.py` 통과

---

## Epic 6: Compliance, Audit & Capital Triggers

**Epic Goal:** Pre-Trade Ledger Writer 완성(FR38)으로 Epic 1 Story 1.5 infrastructure 위에 모든 decision·주문·청산 이벤트가 S_entry·Gate·param_hash·policy_version_git_sha·timestamp_hash와 함께 append-only로 기록되는 단일 entry point를 확립한다. 월간 SHA-256 체인 해시를 외장 SSD LUKS + S3 Object Lock Compliance 2-target 백업(FR39)으로 영구 보존하고, §176 regulatory hard block(분당 주문 상한·취소율 < 30%, FR40)과 §17/§18 단일 계좌 assertion(FR41)으로 자본시장법 경계를 물리 enforce한다. M_tax 세후 수익률(FR42) + 대주주 근접 경보(FR43)로 세금·규제 영향을 정량화하고, 자본 ≥ 1,000만 원 또는 일일 주문 > 50건 도달 시 준법감시인 통지 워크플로우(FR44/FR45) 및 가족 OTP 공증 위임·외부 승인권자 서약서(FR46)가 자동 트리거되어 시스템 실패 시 인간 fail-safe가 법적 구속력으로 성립한다. 모든 의사결정이 tamper-evident로 기록되고, 자본시장법(§17/§18/§176/§178/§178-2) 요건이 자동 enforce되며, 자본 임계 도달 시 compliance 워크플로우가 자동 트리거된다.

### Story 6.1: Pre-Trade Ledger Writer 완성

As Khuk0 ensuring every decision is legally reproducible,
I want Epic 1 Story 1.5의 Ledger infrastructure(table + genesis + SHA-256 chain) 위에 완전한 Writer를 구축하여 모든 주문 의도(승인/거부/청산)를 S_entry·Gate·param_hash·policy_version_git_sha·timestamp_hash와 함께 append-only로 기록하여,
So that §178-2 법률 수준 tamper-evident 기록 체인이 Epic 3/4/5의 모든 decision 경로에서 단일 entry point로 보장된다(FR38).

**Acceptance Criteria:**

**Given** Epic 1 Story 1.5의 `pre_trade_ledger` 테이블 + genesis entry + SHA-256 체인 infrastructure
**When** `athena-execution/ledger/writer.py` 완성 구현
**Then** `LedgerWriter.append(event: LedgerEntry)` 단일 entry point + Pydantic DTO `LedgerEntry(event_type, payload_json, policy_version_git_sha, param_hash, timestamp_hash, user_id)`
**And** `timestamp_hash = SHA256(timestamp_kst_iso || nonce_uuid4)` 로 시각 hash 생성 (재현성 + 고유성)

**Given** Epic 3 Story 3.7 dual gate decision
**When** authorized 또는 rejected 판정 완료
**Then** Ledger append 필수: event_type ∈ `{'entry_authorized', 'entry_rejected_alpha', 'entry_rejected_anti_ego', 'entry_rejected_both', 'entry_rejected_cb'}` + payload={s_entry, failed_flags, firewall_status, rejection_layer}
**And** 누락 시 SYSTEM FAILURE (Epic 3 Story 3.7 AC#5 의 Ledger hook 완성)

**Given** Epic 4 Story 4.3/4.4/4.7 주문·청산 경로
**When** 각 이벤트 발생
**Then** Ledger append: event_type ∈ `{'order_placed', 'order_filled', 'order_rejected', 'exit_oco_stop', 'exit_kill_switch_symbol', 'exit_kill_switch_account', 'exit_auto_flatten', 'exit_manual', 'exit_manual_event_reduce'}`
**And** 모든 주문 lifecycle 이벤트가 Ledger 1:1 대응, 누락 발생 시 NFR-A3 override log 완전성 위반 간주

**Given** 체인 무결성 보장
**When** `append()` 호출
**Then** async lock + `prev_hash` 조회 + `this_hash = SHA256(payload_json || policy_version_git_sha || timestamp_hash || prev_hash)` 계산 (NFR-S3)
**And** write latency p99 < 30ms (NFR-P5 비블로킹, Epic 4 Story 4.3 p99<1초 예산 내)

**Given** 모든 entry에 `policy_version_git_sha` embed
**When** Hatchling build hook 자동 주입 (AR-COM4)
**Then** 런타임 shell 호출 0, `athena._version.__commit__` 에서 직접 가져오기
**And** 재현성: 같은 commit + 같은 input + 같은 nonce_seed → 같은 this_hash (결정론)

**Given** integration 테스트
**When** 전체 decision 경로 시뮬레이션 (Epic 3 dual gate 4 케이스 + Epic 4 주문/청산 전 경로)
**Then** Ledger entry 수 = 이벤트 수 1:1 일치 + 체인 연속성 검증 + 각 entry의 timestamp_hash uniqueness
**And** pytest `tests/integration/test_ledger_writer.py` 통과

### Story 6.2: 월간 SHA-256 체인 해시 + 2-target 외장 백업

As Khuk0 needing legally compliant audit trail retention,
I want 월말 Ledger segment hash가 외장 SSD LUKS + S3 Object Lock Compliance 2-target에 저장되고 월간 검증 job이 체인 연속성을 검증하여,
So that Ledger가 물리 파기·변조되어도 두 대상지에서 법적 증거 체인이 복원 가능하다(FR39, NFR-A1, NFR-A2 영구 보존).

**Acceptance Criteria:**

**Given** Epic 1 Story 1.5의 월말 체인 해시 job placeholder + AR-DATA6 2-target 정책
**When** `scripts/monthly_ledger_backup.py` 완성 (매월 1일 03:00 KST systemd timer)
**Then** 전 월 모든 Ledger entry id 오름차순 정렬 → `segment_hash = SHA256(prev_segment_hash || sorted_ids_hash || policy_version_git_sha)` 계산
**And** 산출물 `segment_2026_04.json`: `{month, segment_hash, prev_segment_hash, entry_count, first_id, last_id, computed_at_utc}`

**Given** 외장 SSD LUKS 마운트 (AR-SEC4)
**When** segment_hash 파일 저장
**Then** 경로: `/mnt/external/ledger/year=YYYY/month=MM/segment_hash.json` + read-only 파일 권한 (`chmod 444`)
**And** LUKS 키는 OS Keychain 조회, mount 실패 시 Critical 알림 + 3회 지수 백오프

**Given** S3 Object Lock Compliance 모드 bucket (또는 Naver Cloud Object Storage)
**When** 동일 파일 업로드
**Then** 객체 키 `ledger/user_id=1/year=YYYY/month=MM/segment_hash.json` + 최소 5년 retention (AR-DATA6) + SSE-C 암호화 (AR-SEC4, 키는 OS Keychain)
**And** 업로드 실패 시 Critical 알림 + 3회 지수 백오프 + 실패 영구 지속 시 Global CB 강제 발동

**Given** 월간 검증 job `scripts/verify_ledger_chain.py`
**When** 매월 15일 04:00 KST 자동 실행
**Then** (a) 전 월 segment_hash ↔ 현 월 genesis prev_hash 연속성, (b) 전 체인 재계산 후 local vs external vs S3 일치 3-way 검증
**And** 불일치 시 Critical 알림 + Global CB 강제 발동 (Epic 5 Story 5.6 hook) + 상세 불일치 레포트 생성

**Given** 영구 보존 요구 (NFR-A2)
**When** 외장 SSD 용량 관리
**Then** segment_hash 파일은 삭제 금지 (Raw ledger entry는 보존 정책 별도, segment hash는 영구)
**And** 외장 SSD free space < 5% 도달 시 Critical 알림 + 외장 디스크 증설 워크플로우 trigger

**Given** integration 테스트
**When** mock 시나리오: 월말 실행 → segment 계산 → 외장 SSD + S3 양쪽 저장 → 다음 달 genesis prev_hash 일치 확인 → 검증 job 3-way 일치
**Then** 2-target 백업 모두 성공 + 검증 job 통과
**And** pytest `tests/integration/test_monthly_ledger_backup.py` 통과 (S3는 MinIO mock)

### Story 6.3: §176 FR40 — 분당 주문 수 + 취소율 30% Regulatory Hard Block

As Khuk0's Compliance layer,
I want 분당 주문 수 상한(default 20/min)과 취소율 < 30% 하드 제한을 §176 regulatory compliance 계층에서 enforce하여,
So that Epic 5 Story 5.4 operational soft throttle이 실패해도 regulatory hard block이 최종 방어선으로 작동한다(FR40, NFR-S6 이중 안전장치).

**Acceptance Criteria:**

**Given** `athena-execution/compliance/rate_limiter.py`
**When** 주문 발행 전 (Epic 4 Story 4.3 consumer → Story 4.1 adapter 사이)
**Then** 분당 주문 수 hard cap 체크 (default 20/min, `policy.toml` Change Control + F5 읽기전용 AR-CFG4) — 초과 시 즉시 reject
**And** `rejection_reason='regulatory_rate_limit_per_minute'`, Ledger append (Story 6.1 경유)

**Given** 취소율 rolling 1시간 window
**When** 계산
**Then** `cancel_rate_1h = cancelled_orders_1h / total_orders_1h`
**And** `cancel_rate_1h ≥ 30%` 도달 시 신규 주문 전면 block + 60분 쿨다운, `rejection_reason='regulatory_cancel_rate_exceeded'`

**Given** Epic 5 Story 5.4 operational soft throttle 관계
**When** 두 계층 모두 통과 요구
**Then** 책임 분리 명시: 5.4 = symbol-level 60s operational throttle / 본 Story = account-level 분/시간 regulatory hard block
**And** 두 계층 모두 reject 시 rejection_reason 둘 다 Ledger 기록

**Given** hard block 활성 시
**When** 거부 발생
**Then** Story 6.1 LedgerWriter append: event_type=`'compliance_rate_limit_reject'`, payload={cancel_rate_1h, orders_per_min, threshold}
**And** §176 audit 대비 모든 거부 tamper-evident 보존 (NFR-A1)

**Given** 분당 주문 수 접근
**When** rolling 측정
**Then** Prometheus gauge `athena_orders_per_min_current` + 80% (16건/분) 도달 시 Medium 알림, 95% (19건/분) 도달 시 High 알림 (NFR-O3)
**And** 사전 경보로 자기 페이싱 유도, 스트레스 상황에서도 hard block 발동 최소화

**Given** integration 테스트
**When** 시뮬레이션: 분당 25건 주문 시도 → 20건째까지 허용 → 21건째부터 reject
**Then** 정확한 경계 동작 + Ledger 기록 + 알림 발송 검증
**And** pytest `tests/integration/test_regulatory_rate_limit.py` 통과

### Story 6.4: §17/§18 단일 계좌 Assertion

As Khuk0 ensuring compliance with §17/§18 scope lock,
I want KIS adapter(Epic 4 Story 4.1) 및 모든 compliance 경로에서 계좌번호가 본인 계좌와 완전 일치하지 않으면 영구 거부하는 assertion을 배치하여,
So that 타 계좌 위임이 구조적으로 불가능함이 런타임에서 물리 enforce되고 자본시장법 §17/§18 scope lock이 테크니컬 방어선으로 성립한다(FR41).

**Acceptance Criteria:**

**Given** `athena-execution/compliance/account_guard.py` + OS Keychain 저장된 본인 `KIS_ACCOUNT_NO`
**When** Epic 4 Story 4.1 adapter 초기화
**Then** `self.expected_account_no = keychain.get('KIS_ACCOUNT_NO')` 로 고정 후 이후 모든 KIS 호출 전 account assertion
**And** account_no 누락 시 `SystemExit("KIS_ACCOUNT_NO not in OS Keychain, §17/§18 assertion failed")` 즉시 종료

**Given** 모든 주문·조회 API 호출
**When** 요청 payload 검증
**Then** `if request.account_no != self.expected_account_no: raise AccountMismatchError("§17/§18 violation")`
**And** error_code `ACCOUNT_MISMATCH` (AR-COM3 확장) + Critical 알림 즉시 발송

**Given** KIS 응답에서 계좌번호 echo
**When** 응답 파싱
**Then** 응답의 account_no도 양방향 assertion (KIS 측 변조·혼동 가능성 차단)
**And** 불일치 시 즉시 Global CB 강제 발동 (Epic 5 Story 5.6) + Ledger append

**Given** account_no 변경 필요 (V1.1+ 계좌 이전 시)
**When** Change Control 경로
**Then** (1) OS Keychain 변경, (2) 72h cooling 통과, (3) SSH signed commit 필수 (NFR-A5), (4) anti_ego_events append `event_type='ACCOUNT_NO_CHANGED'` 필수
**And** 변경 이력은 Ledger에도 append `event_type='account_no_changed'`, payload={old_hash, new_hash, reason}

**Given** Compliance Ledger 기록 (방어적)
**When** account mismatch 감지 (본래 발생 불가)
**Then** Story 6.1 LedgerWriter append: event_type=`'account_mismatch_blocked'`, payload={attempted_account_no_hash, expected_account_no_hash, caller_stack_trace}
**And** Ledger 기록 + Global CB 강제 발동 + 수동 리뷰 전까지 paper-only mode

**Given** integration 테스트 (mock KIS)
**When** mock adapter에 엉뚱한 account_no 주입
**Then** `AccountMismatchError` raise + Critical 알림 + Global CB 활성화 + Ledger 기록 검증
**And** pytest `tests/integration/test_account_guard.py` 통과

### Story 6.5: M_tax 세후 수익률 + 대주주 근접 경보

As Khuk0 managing tax-adjusted net returns and large-shareholder risk,
I want 증권거래세 0.18% + 배당세 15.4% + 금투세 폐지 반영한 M_tax 세후 계산과 대주주 요건(지분 1% 또는 시가 10억 원) 근접 경보를 제공하여,
So that 세후 기준 수익성이 정확히 측정되고 대주주 전환으로 인한 예상치 못한 세율 증가가 사전 경보된다(FR42, FR43).

**Acceptance Criteria:**

**Given** `athena-execution/tax/m_tax.py` + `config/tax_schedule.toml` (거래세 0.18%, 배당세 15.4%, 금투세 `apply_financial_investment_tax=false`)
**When** Epic 4 Story 4.2 체결 이벤트 수신
**Then** `tax_securities = filled_price × filled_qty × 0.0018` (매도 시만) 계산 + `orders` 테이블 `tax_securities` 컬럼 기록
**And** 세율 변경은 Change Control + config 별도 파일, `tax_schedule.toml`은 F5 읽기전용 대상 (AR-CFG4)

**Given** 배당 수령 이벤트 (KIS 조회 또는 예탁원 통지)
**When** 분기별 배당 수신
**Then** `tax_dividend = dividend_gross × 0.154` (배당소득세 + 지방세 통합) + `dividend_net = dividend_gross - tax_dividend` 계산
**And** 2025년 금투세 폐지로 반영 생략, 2026+ 재도입 시 Change Control + tax_schedule.toml 업데이트

**Given** Epic 4 Story 4.7 `ExitEvent.pnl_realized`
**When** 세후 수익 계산
**Then** `pnl_net_of_tax = pnl_realized - tax_securities - tax_dividend` + `modules_output` INSERT (module='M_tax')
**And** 월간 세후 수익 요약이 Epic 7 FR49 8대 KPI 중 "월 수익률" 의 기준값

**Given** 대주주 요건 (2024 기준: 종목당 지분 1% OR 시가 10억 원 이상, `tax_schedule.toml` 정의)
**When** 오픈 포지션 평가 (매일 15:35 KST)
**Then** 각 종목 `holding_ratio = holding_qty / total_issued_shares` + `holding_value = holding_qty × close_price` 계산
**And** 85% 도달 (0.85% 또는 8.5억) Medium 알림, 95% (0.95% 또는 9.5억) High 알림, 임계 초과 Critical + 해당 종목 신규 매수 차단

**Given** 대주주 요건 자료 출처
**When** `total_issued_shares` 조회
**Then** KIS REST `inquire-stock-info` 또는 pykrx (AR-EXT7) 활용, 캐시 하루 1회 갱신
**And** 데이터 결측 시 보수적 추정 (`holding_ratio = 1.0` fail-safe) + High 알림

**Given** 세후 KPI 통합 + Ledger 기록
**When** 월말 세후 요약
**Then** Story 6.1 LedgerWriter append: event_type=`'tax_calculated'`, payload={month, gross, tax_securities, tax_dividend, net_of_tax, major_shareholder_symbols: [...]}
**And** pytest `tests/integration/test_m_tax.py` 통과 (거래세·배당세·대주주 경보 시나리오)

### Story 6.6: 준법감시인 통지 워크플로우 자동 트리거

As Khuk0 ensuring regulatory notification obligations,
I want 자본 ≥ 1,000만 원 또는 일일 주문 > 50건 도달 시 KIS 준법감시인 통지 워크플로우를 자동 감지·트리거하는 detector + state machine을 확보하여,
So that 법령상 통지 의무가 manual 추적에 의존하지 않고 시스템이 threshold 도달을 즉시 감지하여 워크플로우를 start한다(FR44).

**Acceptance Criteria:**

**Given** `athena-execution/compliance/notification_trigger.py`
**When** 매일 15:35 KST (장 마감 직후) account balance 체크
**Then** `account_balance ≥ 10_000_000` 감지 시 state = `CAPITAL_THRESHOLD_TRIGGERED` 전환
**And** 단일 threshold 크로스 이벤트만 1회 발동 (중복 방지, 계좌 balance가 threshold 위·아래 왕복해도 1회만)

**Given** 일일 주문 수 모니터링
**When** `orders` 테이블 당일 집계
**Then** `daily_order_count > 50` 감지 시 state = `ORDER_VOLUME_THRESHOLD_TRIGGERED` 전환
**And** 매일 리셋 (자정 KST 카운터 0), 당일 임계 도달 시 즉시 1회 트리거

**Given** 두 threshold 중 하나 도달
**When** notification 워크플로우 start
**Then** (1) Grafana persistent banner "Notification obligation triggered: {threshold_type}", (2) Critical 알림 (NFR-O3), (3) Story 6.7 이메일 템플릿 생성 자동 호출, (4) Story 6.1 LedgerWriter append `event_type='compliance_notification_triggered'`, payload={threshold, value, notified_at}
**And** 자본 threshold 발동 시 Story 6.8 가족 OTP 공증 체크리스트 trigger도 동시 호출

**Given** 워크플로우 state 관리 테이블
**When** `compliance_workflow` 테이블 생성
**Then** 스키마: `id`, `trigger_type` (capital | order_volume), `triggered_at`, `email_template_generated_at`, `email_sent_manually_at`, `kis_response_received_at`, `workflow_status ∈ {triggered, email_generated, sent_pending_response, response_received, closed}`, `notes`
**And** append-only (상태 UPDATE는 명시적 write 경로만 허용, 수동 편집 차단 + SSH signed commit 필수)

**Given** 워크플로우 미완료 지속
**When** triggered → 7일 경과까지 `closed` 미전환
**Then** Critical 알림 매일 반복 "Compliance workflow pending, {days_elapsed} days since trigger"
**And** 30일 경과 시 Account CB 강제 발동 (Epic 5 Story 5.7 hook, 규제 리스크 물리 차단)

**Given** integration 테스트
**When** mock balance 1,000만 원 도달 시뮬레이션
**Then** 트리거 이벤트 1회 발동 + Ledger 기록 + Story 6.7 호출 + Story 6.8 호출 + banner 활성화 검증
**And** pytest `tests/integration/test_compliance_trigger.py` 통과

### Story 6.7: 준법감시인 이메일 템플릿 + 회신 Ledger 기록

As Khuk0 executing regulatory notification,
I want Story 6.6 트리거 시 KIS 준법감시인 대상 통지 이메일 템플릿이 자동 생성되고 회신 수령이 Ledger에 tamper-evident로 기록되어,
So that 규정 준수 행위(이메일 발송·회신 수령)가 법적 분쟁 시 증거 체인으로 보존되고 수동 개입 최소 원칙을 지킨다(FR45).

**Acceptance Criteria:**

**Given** `athena-execution/compliance/email_template.py` + Story 6.6 트리거
**When** 이메일 템플릿 생성 호출
**Then** `notifications/outgoing/{triggered_at_kst}_{trigger_type}.eml` 파일 생성 (read-only 권한)
**And** 템플릿 섹션: 수신자 (KIS 준법감시인), 발신자 (본인 실명 + 계좌번호 부분 마스킹), 본문 (트리거 조건 + 도달 시각 + 거래 내역 요약 표), 첨부 (월별 거래 요약 PDF 옵션)

**Given** 템플릿 본문 데이터 자동 채움
**When** 데이터 조회
**Then** (a) 자본 도달 케이스: 최근 30일 주문 수·체결률·순이익·세후 수익 (Story 6.5 사용), (b) 주문 수 초과 케이스: 해당 일 전체 주문 내역 테이블
**And** 데이터는 Story 6.1 Ledger에서 직접 조회 (신뢰성 보장, orders 테이블 단독 사용 금지)

**Given** 사용자 수동 이메일 발송 (SMTP 자동 발송 금지 — 법적 행위는 본인 확인 필수)
**When** `scripts/mark_email_sent.py --workflow-id X` 실행
**Then** `compliance_workflow.email_sent_manually_at` 업데이트 + 발송 이메일 SHA256 계산 + Story 6.1 Ledger append `event_type='compliance_email_sent'`, payload={workflow_id, email_sha256, sent_at_kst}
**And** 실행에는 SSH signed commit 필요 (NFR-A5)

**Given** KIS 준법감시인 회신 수령
**When** `scripts/record_kis_response.py --workflow-id X --response-file path/to/response.eml` 실행
**Then** 응답 이메일 SHA256 + `compliance_workflow.kis_response_received_at` 업데이트 + Ledger append `event_type='compliance_response_received'`, payload={workflow_id, response_sha256, received_at_kst, response_summary}
**And** 응답 파일 원본은 `notifications/incoming/{received_at_kst}_{workflow_id}.eml` 에 append-only 저장 (read-only 권한)

**Given** 워크플로우 closure
**When** 모든 단계 완료 + 사용자 수동 close
**Then** `workflow_status='closed'` 전환 + Story 6.6 banner 해제 + Ledger append `event_type='compliance_workflow_closed'`, payload={workflow_id, total_duration_days, kis_response_summary_hash}
**And** 이후 동일 trigger_type 의 반복 threshold 크로스 시 새 워크플로우 시작 (독립 id)

**Given** integration 테스트
**When** mock 전체 워크플로우 (trigger → template gen → sent → response → closed)
**Then** 5개 Ledger entry 순서 append + 각 this_hash 체인 유지 + compliance_workflow 테이블 최종 state='closed'
**And** pytest `tests/integration/test_compliance_email_workflow.py` 통과

### Story 6.8: 가족 OTP 공증 위임 체크리스트 + 외부 승인권자 서약서

As Khuk0 preparing human-layer fail-safe at capital threshold,
I want 자본 ≥ 1,000만 원 도달 시 가족 1인 OTP 비상정지 권한 공증 위임 체크리스트와 외부 승인권자 서약서 템플릿이 자동 제시되어,
So that 시스템·인간 실패 시에도 신뢰받는 제3자가 시스템 정지를 강제할 수 있는 human fail-safe가 법적 구속력으로 성립한다(FR46, Epic 5 Story 5.7 Account CB cascade 연계).

**Acceptance Criteria:**

**Given** Story 6.6의 자본 threshold 트리거 (자본 ≥ 1,000만 원)
**When** 자본 도달 감지
**Then** `notifications/outgoing/human_failsafe/{triggered_at_kst}/` 디렉토리 생성 + 3개 문서 템플릿 자동 생성
**And** 생성 문서: (1) 가족 OTP 위임 공증 신청서, (2) 외부 승인권자 서약서, (3) `completion_checklist.md`

**Given** 가족 OTP 위임 공증 신청서 template
**When** 자동 채움
**Then** 본인 실명 + 계좌번호 마스킹 + OTP 기기 정보 + 가족 1인 수동 입력 필드 (실명·관계·연락처) + 공증 범위 ("긴급 시스템 정지 1회 권한" 한정) + 위임 유효기간 (1년 자동 갱신 옵션)
**And** 한국 공증법 요건 양식 + 변호사·공증인 검토 권고 문구 포함

**Given** 외부 승인권자 서약서 template
**When** 자동 채움
**Then** 승인권자 역할 명시 (변호사·회계사·신뢰 가능한 제3자) + 정책 변경 승인 범위 + 책임 한계 + 임기 1년 자동 갱신
**And** MVP 초기 승인권자 1인 요구, 자본 ≥ 1억 원 도달 시 2인 요구 (V1.1+ deferred scope)

**Given** completion_checklist.md 생성
**When** 체크리스트 항목
**Then** [ ] 공증 신청서 인쇄, [ ] 가족 1인과 공증사무소 방문, [ ] 공증 완료 후 스캔본 `notifications/completed/{workflow_id}/notarization.pdf` 저장, [ ] OTP 권한 위임 체크, [ ] 외부 승인권자 서약서 서명 받기, [ ] 모든 원본 보관 위치 기록
**And** 각 단계 완료 시 `scripts/mark_checklist_complete.py --item X` 로 Ledger 기록 (SSH signed commit, NFR-A5)

**Given** 체크리스트 미완료 지속
**When** 자본 threshold 후 30일 경과까지 완료 안 됨
**Then** Critical 알림 매일 반복 + Epic 5 Story 5.7 Account CB 강제 발동 (자본 50% 축소 cascade의 "수동 체크리스트" 미완료 = fail-safe trigger)
**And** 완료 이전까지 실계좌 신규 진입 차단 (paper-only 모드 강제 유지)

**Given** 모든 체크리스트 완료
**When** 사용자 최종 확인 + Ledger 최종 append
**Then** Story 6.1 LedgerWriter append: event_type=`'human_failsafe_established'`, payload={family_delegate_name_sha256, external_approver_name_sha256, notarization_date, completion_scan_sha256}
**And** Account CB 수동 해제 허용 조건 충족 (Epic 5 Story 5.7 복귀 조건의 "인간 fail-safe 완성" 항목)

---

## Epic 7: Observability & Reporting

**Epic Goal:** Prometheus histogram 기반 시그널 레이턴시 p99 측정(FR48)과 8대 KPI(월 수익률·Deflated Sharpe·MDD·설거지 회피율·이벤트 손실 경감률·레이턴시 p99·override 로그 완전성·F1 PSI) 실시간 누적 계산(FR49) + KPI 선언 조건(n≥6개월·50+ trades·bootstrap CI 하한 > 0) 실시간 패널(FR50)로 시스템 관측성을 완성한다. Epic 1 Story 1.9의 "Foundation Health" 대시보드와 Epic 3 Story 3.8의 "Anti-Ego Panel"을 통합 Grafana 대시보드(FR47 complete)로 흡수하고, 주간 거래 요약 리포트(FR51)와 월간 52 flag missing rate 감사 리포트(FR52, NFR-A4)를 자동 생성한다. 시스템 건강·수익성·규정 준수 상태를 Grafana 대시보드와 자동 리포트로 전면 관측하며, KPI 선언 가능 시점을 실시간으로 파악한다.

### Story 7.1: Prometheus Histogram Latency + 공식 메트릭 레지스트리

As Khuk0 monitoring signal pipeline performance,
I want 시그널 생성 end-to-end 레이턴시를 Prometheus histogram(NFR-O2 필수)으로 측정하고 모든 `athena_*` 메트릭이 AR-OBS2 네이밍 규칙을 따르는 공식 레지스트리로 관리되어,
So that `histogram_quantile(0.99, ...)` 쿼리가 p99 < 5초(NFR-P1)를 실측 검증하고 trace_id(NFR-O4)로 비동기 파이프라인 디버깅이 가능하다(FR48).

**Acceptance Criteria:**

**Given** `athena-core/metrics.py` Prometheus client + 공식 메트릭 레지스트리 `athena-core/metrics_registry.py`
**When** 메트릭 정의
**Then** 모든 메트릭은 `athena_<subsystem>_<metric>_<unit>` 네이밍 규칙 준수 (AR-OBS2), 등록 시 네이밍 검증 + 중복 거부
**And** 미등록 메트릭 emit 시도 시 ValueError raise, 모든 메트릭은 registry 선언 필수 (shadow metric 차단)

**Given** 시그널 생성 end-to-end histogram
**When** 각 pipeline stage에서 `.observe(duration_seconds)` 호출
**Then** `athena_signal_generation_duration_seconds` histogram + bucket boundaries `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]` 정의 (NFR-P1 p99=5s 검증 해상도)
**And** label `{stage ∈ 'feature_fetch', 'm1', 'm2', 'm3', 'm9', 'm13_stage1', 'm13_stage2', 'm14', 's_entry_aggregation', 'decision'}`

**Given** asyncio 비동기 파이프라인 (Epic 2 Story 2.6 M13 2단계)
**When** 각 async 작업 시작
**Then** `trace_id = uuid4()` 부여 + 구조화 JSON 로그 각 단계에 embed (NFR-O4) + Prometheus exemplar로 trace_id 첨부
**And** trace_id 로 단일 요청의 전체 경로(feature → M1/2/3/9 → M13 → M14 → S_entry → decision → order) 재구성 가능

**Given** NFR-O2 필수 메트릭 목록
**When** Epic 1~6 에서 emit된 메트릭 전수 검증
**Then** 필수 메트릭 존재 확인: 시그널 레이턴시 histogram / 모듈별 throughput (signals/min) / error rate by code / Kill Switch 상태 (4층) / 오픈 포지션 수
**And** 누락 시 CI Step 4 FAIL (metrics_registry 자동 검증 스크립트)

**Given** histogram_quantile 쿼리 성능
**When** Grafana panel `histogram_quantile(0.99, rate(athena_signal_generation_duration_seconds_bucket[5m]))`
**Then** 쿼리 응답 < 500ms (Prometheus 90일 보존 기준, AR-OBS1)
**And** 1000+ 시그널 표본 이상에서만 p99 신뢰 (AR-OBS1 90일 retention)

**Given** integration 테스트
**When** mock pipeline 실행 (각 stage에 의도적 duration 주입)
**Then** histogram 버킷 카운트 정확 + exemplar에 trace_id 포함 + 레지스트리 네이밍 검증 통과
**And** pytest `tests/integration/test_metrics_registry.py` 통과

### Story 7.2: 8대 KPI 실시간 누적 계산 엔진

As Khuk0 measuring system performance with discipline-aware KPIs,
I want 월 수익률·Deflated Sharpe·MDD·설거지 회피율·이벤트 손실 경감률·레이턴시 p99·override 로그 완전성·F1 PSI 8대 KPI를 실시간 누적 계산하는 단일 엔진을 확보하여,
So that 기능별 계산 로직이 각 Epic에서 산재하지 않고 중앙 집계 layer 에서 일관 처리되며 선언 조건(Story 7.3)이 참조할 수치가 단일 source of truth로 존재한다(FR49).

**Acceptance Criteria:**

**Given** `athena-orchestrator/kpi_engine.py` 단일 엔진
**When** 각 KPI 계산 함수 정의
**Then** 계산 주기 표: (1) 월 수익률 = 일간 갱신 (매 15:35 KST), (2) Deflated Sharpe = 월간, (3) MDD = 실시간 (Epic 5 Story 5.7 재사용, DRY), (4) 설거지 회피율 = 일간, (5) 이벤트 손실 경감률 = 이벤트 발생 시, (6) 레이턴시 p99 = Story 7.1 histogram 조회, (7) override 완전성 = 월간 (Epic 3 Story 3.1 AC#6 재사용), (8) F1 PSI = 월간 (Epic 8 Story 8.x 연계)
**And** 각 KPI 결과 `kpi_snapshots` 테이블 append: `(user_id, kpi_name, value, computed_at_kst, calculation_period, confidence_interval_lower, confidence_interval_upper)`

**Given** 월 수익률 (tax-adjusted)
**When** 계산
**Then** Epic 6 Story 6.5 `pnl_net_of_tax` 월간 집계 / 기초 잔고 × 100 (세후 기준, 거래세·배당세 반영)
**And** KPI name = `'monthly_return_net_of_tax_pct'`

**Given** Deflated Sharpe (Bailey & López de Prado 공식)
**When** 월간 계산
**Then** `DSR = Sharpe × sqrt(N) - 0.5 × sqrt(2π) × ln(max_trials)` — Sharpe는 일별 수익률 기준, max_trials는 시도된 전략 수 (policy.toml, MVP=1)
**And** `n < 6 months` 또는 `trades < 50` 인 기간엔 CI를 매우 넓게 산출 (선언 조건 Story 7.3 참조)

**Given** MDD + 설거지 회피율
**When** 계산
**Then** MDD는 Epic 5 Story 5.7 `athena_mdd_pct` gauge 그대로 사용 (DRY) / 설거지 회피율 = (거부된 entry 중 사후 -5% 이상 하락 종목 비율) / (전체 거부 entry)
**And** 설거지 회피율 산출은 Story 2.1 snapshot fixture 2건 + 누적 실거래 거부 데이터 기반, 월간 집계

**Given** 이벤트 손실 경감률 + 레이턴시 p99
**When** 계산
**Then** 이벤트 손실 경감률 = (Epic 4 Story 4.6 event proximity alert로 인한 수동 축소로 회피한 손실 추정치) / (이벤트 근접 포지션 총 exposure) — 이벤트 발생 후 재계산
**And** 레이턴시 p99 = Story 7.1 histogram_quantile(0.99) 의 5분 rolling

**Given** override 완전성 + F1 PSI
**When** 월간 계산
**Then** override 완전성 = Epic 3 Story 3.1 AC#6 의 교차검증 결과 (`SELECT COUNT(*) FROM anti_ego_events` vs F1/F5 trigger counter), 값 ∈ [0.0, 1.0], 목표 1.0 (NFR-A3)
**And** F1 PSI = Epic 8 Story 8.x 의 PSI 계산 결과 조회 (seam 제공, 구현 Epic 8)

**Given** 8대 KPI Prometheus expose
**When** 각 KPI 계산 완료
**Then** gauge `athena_kpi_{name}` 실시간 업데이트 + Story 7.4 Grafana panel이 직접 참조
**And** integration 테스트 pytest `tests/integration/test_kpi_engine.py` 통과 (8개 KPI 각 계산 검증)

### Story 7.3: KPI 선언 조건 패널

As Khuk0 knowing when I can legitimately claim performance,
I want KPI 선언 조건(n≥6개월 운영·50+ trades·bootstrap CI 하한 > 0) 충족 여부를 실시간 표시하는 Grafana 패널을 확보하여,
So that "성과를 선언해도 되는가"가 주관적 판단이 아닌 객관적 통계 기준으로 즉시 확인 가능하다(FR50).

**Acceptance Criteria:**

**Given** `athena-orchestrator/kpi_declaration.py`
**When** 3개 선언 조건 계산
**Then** (1) `months_since_first_trade ≥ 6`, (2) `total_trades_count ≥ 50` (Epic 4 orders 테이블 entry event_type), (3) `bootstrap_ci_lower_95 > 0` (Sharpe 기준 10,000회 resampling)
**And** 모든 조건 `AND` 충족 시 `kpi_declaration_allowed = True`, Prometheus gauge `athena_kpi_declaration_allowed` (0/1)

**Given** bootstrap CI 계산
**When** Sharpe 기준 10,000회 resampling (일별 수익률 vector)
**Then** 95% CI = percentile(resamples, [2.5, 97.5]) 산출 + `ci_lower`, `ci_upper` gauge
**And** `trades < 50` 시 CI 매우 넓게 산출 (통계적으로 무효), `kpi_declaration_allowed = False` 고정

**Given** Grafana "KPI Declaration" 패널 (Story 7.4 통합 대시보드 내)
**When** 사용자 접근
**Then** 3개 조건 각각 Red(미충족)/Green(충족) 표시 + 충족까지 남은 거리 ("need 12 more trades" 등)
**And** 전체 선언 가능 여부는 hero banner (Red="NOT READY", Green="READY TO DECLARE")

**Given** KPI 선언 이력 (수동 선언은 위험 억제, 자동 판단만)
**When** `kpi_declaration_allowed` 최초 True 전환
**Then** Epic 6 Story 6.1 LedgerWriter append `event_type='kpi_declaration_threshold_reached'`, payload={months, trades, ci_lower, ci_upper, kpi_snapshot}
**And** Critical 알림 발송: "KPI declaration threshold reached — review before public claim"

**Given** 선언 조건 퇴행 (예: 손실로 CI 하락)
**When** `kpi_declaration_allowed` True → False 재전환
**Then** High 알림 + Ledger append `event_type='kpi_declaration_threshold_lost'`, payload={reason: which condition failed}
**And** 사용자에게 "이전 선언은 retract 필요" 수동 checklist 제시

**Given** integration 테스트
**When** mock 시나리오 (5개월 동안 trades=30, CI=[-0.5, 0.3] → 실패 / 7개월, trades=60, CI=[0.1, 0.5] → 성공)
**Then** 두 케이스에서 `kpi_declaration_allowed` 정확 판정 + Ledger 기록 검증
**And** pytest `tests/integration/test_kpi_declaration.py` 통과

### Story 7.4: 통합 Grafana 대시보드 완성

As Khuk0 monitoring the full system from a single pane of glass,
I want Epic 1 Story 1.9 "Foundation Health" + Epic 3 Story 3.8 "Anti-Ego Panel" + 8-KPI 패널 + KPI 선언 패널 + Kill Switch 상태 + Ops Defense 지표를 하나의 통합 Grafana 대시보드로 merge하여,
So that 시스템 건강·수익성·규정 준수 상태를 단일 대시보드 load로 3초 내 파악 가능하다(FR47 complete).

**Acceptance Criteria:**

**Given** Grafana 통합 대시보드 "Athena V1.0 Command Center"
**When** 대시보드 provisioning (JSON config, git version controlled)
**Then** Row 구성: (1) Hero — KPI 선언 상태 + Global CB 상태, (2) KPI — 8대 KPI 그래프, (3) Alpha Defense — S_entry 분포·flag missing rate·M13 latency, (4) Anti-Ego — Firewall status·F1 감지·F5 override, (5) Execution — 주문 발행 p99·체결률·슬리피지, (6) Kill Switch — 4층 CB 상태·발동 횟수, (7) Infrastructure — L2 uptime·rsync lag·외장 SSD free
**And** refresh interval 5초, 모바일 가독 (responsive)

**Given** Epic 1 Story 1.9 "Foundation Health" 대시보드 흡수
**When** Row 7 (Infrastructure) 에 기존 패널 migrate
**Then** 기존 패널 deprecated (삭제 금지, `[deprecated]` 태그만 추가, Change Control NFR-M3 준수)
**And** 통합 대시보드가 Foundation Health 기능 superset 확인

**Given** Epic 3 Story 3.8 "Anti-Ego Panel" 흡수
**When** Row 4 (Anti-Ego) 에 4-패널 그룹 migrate + alert rule 통합
**Then** 기존 panel alert rule은 그대로 유지 (NFR-O3 3단 라우팅)
**And** 이벤트 timeline이 Ledger event_type별로 색상 구분 (BARGAINING=red, OVERRIDE_ATTEMPT=critical, FIREWALL_ACTIVATED=orange)

**Given** 대시보드 load 성능
**When** 사용자 접근
**Then** 전체 패널 load p95 < 3초 (FR18 체감 기준) + 개별 패널 쿼리 p95 < 500ms (NFR-P4 범위)
**And** DuckDB Grafana plugin 사용 시 read-only user grant 적용

**Given** Alertmanager 통합 rule (NFR-O3)
**When** rule 설정
**Then** Critical (Global CB / heartbeat 4h / Ledger 불일치 / Account mismatch / auto-flatten), High (heartbeat 5분 / PSI > 0.2 / 취소율 > 20% / 로거 uptime < 99% / session CB / symbol CB / 재연결), Medium (slippage spike / missing rate / rate limit 근접 / bargaining detected)
**And** 각 rule은 `_alerts.yml` 에 선언, git version controlled

**Given** integration 테스트
**When** 대시보드 JSON 유효성 + 패널 쿼리 성능 + alert rule 문법 검증
**Then** `scripts/validate_grafana_dashboards.py` 자동 실행 (CI Step 4 통합)
**And** pytest `tests/integration/test_dashboard_completeness.py` 통과 (모든 FR47 요구 패널 존재)

### Story 7.5: 주간 거래 요약 리포트 자동 생성

As Khuk0 reviewing my trading week with discipline,
I want 매주 일요일 자동 생성되는 거래 요약 리포트가 일별 거래 내역·override 시도 로그·KPI 변화를 한 문서에 담아,
So that 한 주의 실제 활동·규율 실패·성과 변화를 구조화된 형식으로 매주 review 가능하다(FR51).

**Acceptance Criteria:**

**Given** `scripts/weekly_report.py` + systemd timer 매주 일요일 02:00 KST
**When** 리포트 생성 실행
**Then** 산출물: `reports/weekly/{year}_W{week_num}_report.md` + PDF 버전 (pandoc 변환) + Markdown 원본 양쪽 저장
**And** 리포트 섹션: (1) Summary (주간 수익·거래 수·승률), (2) Daily Breakdown (일별 거래 테이블), (3) Rejection Analysis (M25 리포트 집계, 가장 많은 거부 이유), (4) Anti-Ego Activity (override 시도·bargaining detected·Firewall 활성화 횟수), (5) KPI Delta (전주 대비 8대 KPI 변화)

**Given** 일별 거래 테이블
**When** 데이터 조회
**Then** `orders` 테이블 WHERE placed_at_kst 주간 범위 + entry 이벤트 + 각 주문의 s_entry·filled_price·pnl_realized·exit_type 포함
**And** Epic 6 Story 6.1 Ledger 조회로 신뢰성 보장 (tamper-evident)

**Given** Rejection Analysis 섹션
**When** M25 리포트 집계
**Then** 주간 거부 entry 수 + rejection_layer (alpha/anti_ego/both) breakdown + top 5 거부 이유 flag
**And** 각 flag별 거부 count + 정량 수치 범위 (예: "narrative_fresh=0, 평균 score 0.08")

**Given** Anti-Ego Activity 섹션
**When** anti_ego_events 테이블 조회
**Then** 주간 BARGAINING_DETECTED 수·OVERRIDE_ATTEMPT 수·FIREWALL_ACTIVATED 수 + 발생 timeline 요약
**And** 발생 횟수 > 0 시 self-retrospective prompt 문구 자동 추가 "{N}회 감지. 주간 회고 권고"

**Given** KPI Delta 섹션
**When** 전주 대비 변화 계산
**Then** `kpi_snapshots` 테이블에서 금주 vs 전주 값 조회 + 변화율 표시
**And** 선언 조건 (Story 7.3) 상태 포함 (NOT READY / READY TO DECLARE)

**Given** 리포트 배포
**When** 생성 완료
**Then** Telegram에 PDF 전송 (Alertmanager Medium 경로, NFR-O3) + 로컬 `reports/weekly/` 영구 보존 (NFR-O1 주간 외장 백업)
**And** pytest `tests/integration/test_weekly_report.py` 통과 (mock 주간 데이터 → 리포트 섹션 7개 검증)

### Story 7.6: 월간 52 Flag Missing Rate 감사 리포트

As Khuk0 self-auditing my system's data quality monthly,
I want 52 flag 각각의 missing rate + reason breakdown + 임계 초과 flag 목록을 월간 자기감사 리포트로 자동 생성하여,
So that NFR-A4 월간 compliance 자기 감사가 시스템 품질(어느 flag가 데이터 결측으로 neutral degrade 되었는지)까지 포함하여 완성된다(FR52).

**Acceptance Criteria:**

**Given** `scripts/monthly_flag_audit.py` + systemd timer 매월 1일 04:00 KST (Story 6.2 월간 Ledger 백업 이후)
**When** 리포트 생성
**Then** Epic 2 Story 2.10 `athena-alpha-defense/src/missing_rate.py` 의 `calculate_missing_rate(start, end)` 를 **import 재사용** (DRY 원칙, 중복 구현 금지)
**And** 산출물: `reports/monthly/{year}_M{month}_flag_audit.md` + PDF

**Given** 52 flag 전수 집계
**When** 리포트 섹션 구성
**Then** (1) Summary 표 (flag_id, total_signals, degraded_count, missing_rate, primary_reason), (2) 임계 초과 flag 목록 (missing_rate > 20% → 재학습 권고), (3) reason breakdown 파이 차트 ({DATA_STALE, FEATURE_MISSING, CONFIDENCE_BELOW_THRESHOLD, LLM_TIMEOUT, MODEL_ERROR}), (4) 월별 추세 (최근 6개월 비교)
**And** 리포트 상단에 전체 flag missing rate 평균 + 목표 < 5%

**Given** 임계 초과 flag 감지
**When** missing_rate > 20% 인 flag 존재
**Then** Epic 8 Story 8.x 재학습 트리거 emit (flag name → Story 8.x detector 가 구독) + Critical 알림
**And** Epic 6 Story 6.1 Ledger append: event_type=`'monthly_flag_audit'`, payload={month, overall_missing_rate, alerting_flags: [...], report_sha256}

**Given** NFR-A4 compliance 요구 커버리지
**When** 기존 Epic 6 월간 Ledger 백업 + 본 Story 월간 flag 감사 통합
**Then** 월간 자기감사 리포트 2종(Ledger chain 검증 + flag missing 감사) 모두 자동 생성 + 통합 대시보드에 표시
**And** 두 리포트 모두 Story 6.1 Ledger에 생성 이벤트 append

**Given** 리포트 배포 + 외장 백업
**When** 생성 완료
**Then** Telegram Medium 알림 + 외장 SSD LUKS `/mnt/external/reports/monthly/` 복제 (NFR-O1 외장 백업)
**And** 로컬 `reports/monthly/` 영구 보존, 1년 초과 파일 외장 아카이브

**Given** integration 테스트
**When** mock 월간 데이터 (52 flag 중 3개 missing_rate > 20%)
**Then** 리포트에 3개 flag 명시 + Epic 8 재학습 트리거 emit 확인 + Ledger append 검증
**And** pytest `tests/integration/test_monthly_flag_audit.py` 통과

---

## Epic 8: Model Lifecycle & Policy Change Gate

**Epic Goal:** F1 모델 재학습·PSI 드리프트 감시·walk-forward 백테스트·Bayesian 튜닝·72h cooling gate·정책 변경 감사를 통해 모델과 정책의 라이프사이클 전체가 감사 가능 경로로만 업데이트되고 장중 ad-hoc 변경이 물리적으로 불가능함을 완성한다. Epic 3 Story 3.2의 라벨링 CLI를 확장하여 anti_ego_events의 override 시도 사례를 자동 import(FR53)하고, Epic 7 Story 7.2의 F1 PSI seam을 월간 계산 + PSI > 0.2 시 Epic 5 Story 5.5 state machine으로 paper-only 자동 전환(FR54)으로 완성한다. 공매도 재개(2025-03-31) 전후 레짐 분리 walk-forward 러너(FR55)와 Bayesian + walk-forward θ_entry·α/β/γ 튜닝 loop(FR56)는 Epic 3 Story 3.3의 `train_one_run()` API 재사용으로 DRY를 유지한다. Epic 1 Story 1.3의 CI 파이프라인 Step 6·7 placeholder 위에 72h cooling gate + Paper 재검증 marker를 물리 enforce(FR57)하고, 모든 정책 변경을 git signed commit + anti_ego_events + Ledger 이중 기록 + Epic 6 Story 6.8 외부 승인권자 서명 경로로 통합(FR58)한다. 모델과 정책을 감사 가능한 경로로만 업데이트할 수 있으며, 장중 ad-hoc 변경이 물리적으로 불가능하다. PSI 드리프트는 paper-only 안전 상태로 자동 전환된다.

### Story 8.1: 주간 F1 라벨링 확장 + anti_ego_events 자동 import

As Khuk0 continuously curating F1 training data,
I want Epic 3 Story 3.2의 라벨링 CLI를 확장하여 주간 실행 시 anti_ego_events의 override 시도 사례를 label candidate로 자동 제시받아,
So that 실제 발생한 override 시도 사례가 다음 재학습 주기의 학습 데이터에 누락 없이 포함된다(FR53).

**Acceptance Criteria:**

**Given** Epic 3 Story 3.2의 `scripts/f1_label.py` + `labels_f1` 테이블
**When** `--source anti_ego_events` 옵션 추가
**Then** anti_ego_events 테이블에서 `event_type IN ('BARGAINING_DETECTED', 'OVERRIDE_ATTEMPT')` + `NOT EXISTS (SELECT 1 FROM labels_f1 WHERE source_file='anti_ego_events' AND source_timestamp=anti_ego_events.created_at_utc)` 쿼리로 신규 candidate 추출
**And** 원문 text는 `payload.text_sha256` (hash만 저장 — Story 3.4 개인정보 보호 원칙)로 label candidate 식별, 라벨링 시 텍스트는 사용자가 기억에서 재구성 또는 일지 원본과 대조

**Given** 주간 라벨링 세션 (매주 일요일 사용자 수동 실행 권고)
**When** `python scripts/f1_label.py --weekly` 실행
**Then** (a) 일반 일지 소스 + (b) anti_ego_events 소스 두 경로 통합 순회 + 각 candidate 에 source 표시 + 순서는 시간순
**And** weekly summary 출력: "This week: {N} general, {M} from anti_ego_events → {K} positive labels added"

**Given** 라벨링 완료 후 labels_f1 업데이트
**When** 새 라벨 누적 시
**Then** Epic 3 Story 3.3 fine-tune pipeline의 "250+ positive label" threshold 재확인 + 미달 시 WARNING "Production retrain threshold not met: {positive_count} / 250"
**And** 250+ 도달 시 자동 안내 "Ready for retrain — invoke Story 8.4 tuning"

**Given** anti_ego_events import 중 event 구조 변경 가능성
**When** payload 스키마 버전 불일치
**Then** `athena_labeling_import_schema_error_total` counter + 해당 event skip + Medium 알림 (anti_ego_events 스키마 변경은 NFR-M3 Change Control)
**And** schema 호환성 검증은 Story 3.1의 Pydantic DTO validation 재사용

**Given** Epic 7 Story 7.5 주간 리포트 연계
**When** 주간 리포트 Anti-Ego Activity 섹션
**Then** "This week: {N} labels added (from anti_ego_events: {M})" 자동 포함 + 사용자 labeling 활동 visibility
**And** 라벨링 skip 지속 시 (4주 이상 무활동) Medium 알림

**Given** integration 테스트
**When** mock anti_ego_events에 10건 BARGAINING + 5건 OVERRIDE 주입 → CLI 실행 → 사용자 y/y/n/... 라벨링
**Then** labels_f1에 정확히 라벨링된 건수 저장 + source='anti_ego_events' 컬럼 기록 + 재실행 시 중복 skip
**And** pytest `tests/integration/test_weekly_labeling.py` 통과

### Story 8.2: F1 라벨 PSI 월간 계산 + Paper-only 자동 전환

As Khuk0 detecting model staleness,
I want F1 라벨 분포 Population Stability Index(PSI)를 월간 자동 계산하고 PSI > 0.2 도달 시 Epic 5 Story 5.5 state machine을 통해 paper-only 모드로 자동 전환하여,
So that 시간 경과로 인한 모델 드리프트가 실거래 손실로 이어지기 전에 안전 상태로 수렴한다(FR54, Epic 7 Story 7.2의 F1 PSI seam 완성).

**Acceptance Criteria:**

**Given** `athena-alpha-defense/f1/psi_drift.py` + Epic 3 Story 3.2 label aggregation 함수 재사용 (DRY)
**When** 매월 1일 05:00 KST (Epic 7 Story 7.6 monthly flag audit 이후) PSI 계산
**Then** 기준 분포 = 초기 Story 3.3 fine-tune 시 `meta.json`의 dataset 분포 + 비교 분포 = 최근 월간 라벨 분포
**And** PSI 공식: `PSI = Σ (actual_% - expected_%) × ln(actual_% / expected_%)` over 10 bins

**Given** PSI 값 해석
**When** 임계값 평가
**Then** PSI < 0.1 → 안정 (로그만), 0.1 ≤ PSI < 0.2 → 드리프트 경고 (Medium 알림), PSI ≥ 0.2 → 심각 드리프트 (Critical 알림 + 자동 조치 trigger)
**And** Prometheus gauge `athena_f1_psi_monthly` + Epic 7 Story 7.2 `athena_kpi_f1_psi` gauge (seam 완성)

**Given** PSI ≥ 0.2 도달
**When** 자동 조치 trigger
**Then** (1) Epic 5 Story 5.5 state machine의 Account CB state를 `PAPER_ONLY_SUSPENDED` 로 전환 (경감된 cascade, MDD -8% 와 다름 — 자본 축소·3일 쿨다운은 건너뛰고 paper-only + 재학습 요구만 적용), (2) Epic 7 Story 7.6 재학습 트리거 emit, (3) Epic 6 Story 6.1 Ledger append `event_type='f1_psi_drift_triggered'`, payload={psi, reference_month, current_month, sample_sizes}
**And** Critical 알림: "F1 PSI={val} ≥ 0.2, system in paper-only, retrain required"

**Given** paper-only 복귀 조건 (MDD cascade와 달리 단순화)
**When** 재학습 완료 + 재계산 PSI < 0.1
**Then** SSH signed commit 으로 수동 disarm 가능 (NFR-A5) + Paper 1주 재검증 통과 시 prod 복귀
**And** 복귀 이벤트 Ledger append `event_type='f1_psi_drift_recovered'`, payload={retrained_model_version, post_retrain_psi, paper_validation_metrics}

**Given** 재학습 없이 PSI 자연 회복 가능성 (라벨 분포 원상복귀)
**When** 다음 달 재계산 시 PSI < 0.1
**Then** 자동 disarm 금지 (NFR-A3 override 로그 완전성 관점: 드리프트 이력은 무결성 보존), 수동 SSH signed commit + 회고 report 필수
**And** "자동 회복" 경로는 영구 차단 (재학습 evidence 없이는 prod 복귀 불가)

**Given** integration 테스트
**When** mock 라벨 분포 주입 (기준 대비 20% shift) → PSI 계산 → 0.25 결과 → 자동 조치
**Then** Account CB state `PAPER_ONLY_SUSPENDED` 전환 확인 + Ledger 기록 + 재학습 트리거 emit 확인
**And** pytest `tests/integration/test_f1_psi.py` 통과

### Story 8.3: Walk-forward 백테스트 러너 (공매도 재개 레짐 분리)

As Khuk0 validating models with temporal integrity,
I want walk-forward 백테스트 러너가 in-sample → out-of-sample 시간순 슬라이딩 검증을 실행하고 공매도 재개(2025-03-31) 전후 레짐 분리 검증을 강제하여,
So that 미래 정보 누설 없는 역사 검증과 2-레짐 비교가 Bayesian 튜닝(Story 8.4)의 input으로 신뢰 가능하게 제공된다(FR55).

**Acceptance Criteria:**

**Given** `scripts/walk_forward_runner.py` + 과거 데이터 (Epic 1 Story 1.7 L2 tick + Story 1.8 뉴스 + Epic 2 Story 2.1 snapshot fixture)
**When** walk-forward 실행
**Then** window 스케줄: train window 90일 → validation window 30일 → 한 step 30일씩 rolling (총 N 개 window 생성)
**And** 미래 정보 누설 검증: train window 말일 기준으로 validation window 데이터 접근 금지 (테스트 케이스에서 명시적 assertion)

**Given** 공매도 재개 2025-03-31 경계
**When** 레짐 분리
**Then** Period A: 공매도 금지 (2020~2025-03-30, 약 5년), Period B: 공매도 재개 (2025-03-31~현재) — 두 레짐 각각 독립 walk-forward 실행
**And** 경계 straddle window (2025-03-31 포함 window) 는 skip 또는 별도 표시 (AR-TEST3)

**Given** 각 walk-forward step의 backtest
**When** Epic 2 Story 2.8의 S_entry 집계 로직을 검증 데이터에 적용
**Then** decision 결과 + 가상 주문 + Epic 4 Story 4.7의 exit_recorder mock → realized P&L 산출
**And** 결정론적 seed 고정 (AR-TEST2) + `policy_version_git_sha` 기록 + 재현 가능성 보장

**Given** 결과 수집
**When** 각 window 완료
**Then** `backtest_runs` 테이블 INSERT: `(run_id, policy_version_git_sha, regime ∈ {A, B}, train_start, train_end, val_start, val_end, trades_count, sharpe, sortino, mdd, deflated_sharpe_bailey, bootstrap_ci_lower, bootstrap_ci_upper)`
**And** 한 run의 완전 재현 정보 모두 포함 (git SHA, seed, policy hash, fixture hash)

**Given** Epic 2 Story 2.1 snapshot fixture 2건 특별 처리
**When** fixture 구간이 walk-forward validation window 에 포함
**Then** 해당 2건은 validation 결과에 반드시 포함 확인 + 정량 평가 (Story 2.1의 reference S_entry 대비 ±5%, AR-TEST3)
**And** 불일치 시 FAIL → walk-forward 전체 run 무효

**Given** 레짐별 비교 리포트
**When** 두 레짐의 walk-forward 완료
**Then** Period A vs B 통계 비교 (Sharpe, Deflated Sharpe, MDD, 승률) + 통계적 유의성 검정 (Welch's t-test)
**And** 결과 `reports/backtest/walk_forward_{run_id}.md` + pytest `tests/integration/test_walk_forward.py` 통과

### Story 8.4: Bayesian + Walk-forward θ_entry / α/β/γ 튜닝

As Khuk0 optimizing policy parameters with disciplined search,
I want θ_entry 임계값 및 α/β/γ 가중치 튜닝을 Bayesian optimization + Story 8.3 walk-forward 조합 loop로 실행하여 최적 파라미터 후보를 수동 검토용으로 제시하여,
So that 파라미터 튜닝이 결정론적·재현 가능한 경로로 수행되고 자동 적용은 절대 금지되어 장중 우회 경로가 생기지 않는다(FR56).

**Acceptance Criteria:**

**Given** `scripts/bayesian_tuner.py` + Gaussian Process (`skopt` 또는 `optuna`)
**When** 튜닝 공간 정의
**Then** 탐색 파라미터: θ_entry ∈ [0.3, 0.9], α ∈ [0.1, 0.7], β ∈ [0.1, 0.7], γ ∈ [0.1, 0.7] with α+β+γ=1 제약
**And** 각 trial 당 Story 8.3 walk-forward 1회 full 실행 (2개 레짐) + objective = Deflated Sharpe (Period B, 공매도 재개 후 레짐 가중)

**Given** Epic 3 Story 3.3의 `train_one_run(hyperparams)` API 재사용 원칙
**When** F1 하이퍼파라미터도 포함 탐색 시
**Then** F1 learning rate·epoch·batch size 도 탐색 공간 확장 가능 (동일 loop 재사용, DRY)
**And** 책임 분리 명시: Story 3.3 = 단일 학습 / 본 Story = 튜닝 loop

**Given** Bayesian loop 실행
**When** 각 trial
**Then** `tuning_runs` 테이블 INSERT: `(tuning_id, trial_num, hyperparams_json, walk_forward_result, objective_value, wall_clock_seconds)`
**And** 최대 trial 수 50건 default (`policy.toml`), 시간 상한 24시간 내 완료

**Given** 튜닝 완료
**When** 결과 제시
**Then** top 5 후보 hyperparam set + 각각의 walk-forward 성능 비교 리포트 `reports/tuning/{tuning_id}.md`
**And** **자동 적용 절대 금지**: 결과는 "제안 only", policy.toml 변경은 Story 8.6 정책 변경 경로로만 가능

**Given** Epic 6 Story 6.1 Ledger 기록
**When** 튜닝 시작·완료
**Then** event_type=`'tuning_started'` + `'tuning_completed'` append, payload={tuning_id, param_space, n_trials, top_candidates_summary}
**And** 튜닝 loop 자체가 정책 변경이 아님 (제안 생성) — cooling gate 대상 아님

**Given** 결정론 재현성 검증
**When** 동일 seed + 동일 데이터로 2회 실행
**Then** 동일 top 후보 + 동일 objective value (AR-TEST2)
**And** pytest `tests/integration/test_bayesian_tuner.py` 통과 (smoke mode 2 trial)

### Story 8.5: 72h Cooling Gate + Paper 재검증 Marker CI 완성

As Khuk0 preventing in-market policy changes,
I want Epic 1 Story 1.3의 CI 파이프라인 Step 6 (72h cooling gate) + Step 7 (Paper 재검증 marker) placeholder를 실제 enforce 로직으로 완성하여,
So that 어떤 정책·파라미터 변경도 72시간 cooling + Paper 환경 1주 재검증을 bypass할 수 없고 인간 규율 실패 지점이 물리적으로 제거된다(FR57, NFR-R5, AR-INF4).

**Acceptance Criteria:**

**Given** Epic 1 Story 1.3 `scripts/check_cooling.py` placeholder
**When** 본 Story 실 구현
**Then** 직전 동일 파일 변경 commit의 타임스탬프 조회 (git log `config/policy.toml` `config/flag_registry.toml` `config/tax_schedule.toml`) + 현재 머지 시도 시각 대비 72시간 경과 여부 검증
**And** 미경과 시 CI Step 6 `POLICY_NOT_COOLED` error_code FAIL (AR-COM3) + Alertmanager Medium 알림 + 남은 시간 출력

**Given** Paper 재검증 marker 실 구현
**When** CI Step 7 (기존 placeholder)
**Then** `.github/workflows/artifacts/paper_validation_{commit_sha}.marker` 파일 존재 + 내용 검증: `{paper_run_start, paper_run_end, paper_duration_days ≥ 7, deflated_sharpe_paper, mdd_paper, trades_count_paper}`
**And** marker 미존재 또는 duration < 7일 시 FAIL + `PAPER_VALIDATION_MISSING` error_code

**Given** Paper 환경 1주 실제 실행
**When** 정책 변경 commit 후 paper deploy 자동 배포 (Epic 1 Story 1.3 AC#5)
**Then** paper 환경에서 1주(7 거래일, 주말·공휴일 제외) 자동 실행 + 결과가 marker 파일 생성 → commit 저자가 PR에 marker 커밋
**And** paper 실행 중 MDD > -5% 또는 Global CB 발동 시 marker 생성 금지 + PR reopen 요구

**Given** cooling gate 경유 불가 시나리오
**When** 긴급 보안 패치 등 cooling bypass 필요 상황
**Then** 절대 bypass 금지 — 긴급 시에도 72h + Paper 통과 필수, 예외 조항 영구 차단 (NFR-M3 Change Control 원칙)
**And** 대신 "긴급 축소 모드" (Account CB 강제 발동 + paper-only) 로 운영, 정책 변경 없이 수동 대응

**Given** 정책 변경 감사 이벤트
**When** Step 6/7 통과한 commit이 prod deploy
**Then** Story 8.6 의 git signed commit + anti_ego_events + Ledger 경로 호출 (본 Story는 CI gate, Story 8.6은 기록)
**And** CI deploy job이 `policy_version_git_sha` 를 새 commit SHA로 업데이트 + 런타임 embed (AR-COM4)

**Given** integration 테스트 (mock CI 환경)
**When** 3개 시나리오 — (1) 24h 전 commit → Step 6 FAIL, (2) 72h 초과 + marker 없음 → Step 7 FAIL, (3) 72h + marker 정상 → pass
**Then** 각 케이스 정확 판정 + 에러 메시지 + Ledger 기록
**And** pytest `tests/integration/test_cooling_gate.py` 통과

### Story 8.6: 정책 변경 감사 로그 + 외부 승인권자 서명

As Khuk0 recording every policy change with tamper-evident accountability,
I want 모든 정책 파일 변경을 git signed commit + anti_ego_events + Ledger 3중 기록 + Epic 6 Story 6.8 외부 승인권자 서명 경로로 통합하여,
So that "누가·언제·무엇을·왜" 변경했는지의 증거 체인이 법적 구속력과 함께 영구 보존되고 외부 감사에 즉시 제출 가능하다(FR58, NFR-A5).

**Acceptance Criteria:**

**Given** `athena-execution/compliance/policy_change_auditor.py` + Story 8.5 CI gate 통과 후 prod deploy 트리거
**When** deploy 이벤트 감지
**Then** (1) commit SSH signing 검증 (`git verify-commit`) — 미서명 시 deploy FAIL, (2) commit author·timestamp·파일 diff·commit message 추출, (3) 3중 기록 경로 호출
**And** commit message 필수 필드 enforce: `Reason:` + `WalkForwardRunId:` + `ExternalApproverSignature:` (Story 8.4 + Story 8.6 linking)

**Given** 3중 기록 — (1) Git 자체 (자동), (2) anti_ego_events, (3) Pre-Trade Ledger
**When** policy change 이벤트
**Then** anti_ego_events append `event_type='POLICY_CHANGED'`, payload={commit_sha, author, timestamp_kst, file_paths, diff_summary, reason, walk_forward_run_id, external_approver_signature_hash}
**And** Story 6.1 LedgerWriter append `event_type='policy_change_deployed'`, payload={동일 내용 + pre_change_policy_sha, post_change_policy_sha}

**Given** 외부 승인권자 서명 (Epic 6 Story 6.8 의 서약서 기반)
**When** 정책 변경 전 필수 단계
**Then** 변경 PR 에 외부 승인권자의 signed review 첨부 (GitHub Review signed with SSH key 또는 별도 서명 파일 `approvals/{commit_sha}.sig`) + 서명 검증 통과 필수
**And** 서명 검증 실패 또는 누락 시 deploy FAIL + `EXTERNAL_APPROVAL_MISSING` error_code

**Given** 자본 < 1,000만 원 (Epic 6 Story 6.6 미트리거) 단계
**When** 외부 승인권자 서약서 미체결 상태
**Then** MVP 초기: 본인 자체 서명 + 사유 상세 설명 (50자 이상)으로 대체 허용 (자본 threshold 이전 buffer)
**And** 자본 ≥ 1,000만 원 도달 이후 (Story 6.8 체크리스트 완료) 부터는 외부 승인권자 서명 필수, 본인 서명만으로는 FAIL

**Given** 정책 변경 통계 + 월간 감사
**When** Epic 7 Story 7.6 월간 감사 리포트
**Then** "This month: {N} policy changes (M with external approver signature, K emergency paper-only)" 섹션 추가 + 변경 건수 > 정상 범위 (Change Control NFR-M3 상한 = 1건/월) 초과 시 High 알림
**And** 초과는 "12주 일정 자동 리셋" trigger (NFR-M3)

**Given** integration 테스트
**When** 3개 시나리오 — (1) 정상 signed commit + external approver → 통과, (2) 미서명 commit → FAIL, (3) 자본 1,000만 원 이후 external approver 누락 → FAIL
**Then** 각 케이스 판정 정확 + 3중 기록 체인 유지 + 에러 메시지
**And** pytest `tests/integration/test_policy_change_auditor.py` 통과

---
