# Implementation Plan

## 목표

이 문서는 `docs/REQUIREMENTS.md`, `docs/SPECIFICATION.md`, `docs/PSEUDOCODE.md`, `docs/ARCHITECTURE.md`를 바탕으로 실제 구현 순서와 테스트 전략을 정리한다.

이 과제의 핵심은 단순 CRUD 구현이 아니라 다음 세 가지를 안정적으로 검증 가능한 구조로 만드는 것이다.

- mixed timezone timestamp 정규화
- batch ingestion 정책(`atomic`, `partial`)
- 센서 상태 판별 및 모드 제어 반영

특히 중요한 기준은 "어떻게 테스트 가능한 구조로 만들 것인가"다.

---

## 구현 원칙

- 시간 처리, 상태 계산, 검증 로직은 가능한 한 순수 함수로 분리한다.
- `now` 같은 현재 시각 의존성은 주입 가능하게 만들어 테스트를 쉽게 한다.
- ingestion flow는 controller보다 service/domain에 규칙을 모은다.
- DB 의존 로직과 비즈니스 규칙을 분리해 unit test와 integration test 경계를 분명히 한다.
- 처음부터 모든 기능을 한 번에 만들기보다, 테스트 가능한 최소 단위부터 점진적으로 확장한다.

---

## 단계별 구현 및 검증 계획

구현 계획과 테스트 계획은 분리하지 않는다. 각 단계는 "무엇을 만든다"와 "어떻게 맞는지 확인한다"를 함께 정의하고, 마지막에 완료 조건까지 둔다.

### Phase 1. 프로젝트 골격과 테스트 기반 구성

구현:

- `src/`와 `tests/` 기본 구조를 만든다.
- 테스트 러너, fixture, 공통 helper, 시간 주입 전략을 먼저 정한다.
- 환경변수, 설정 객체, 테스트용 DB 분리 방식을 정한다.

추가 결정:

- 백엔드 프레임워크는 FastAPI를 사용한다.
- 요청/응답 스키마와 설정 검증은 Pydantic으로 처리한다.
- 영속 계층은 SQLAlchemy ORM을 사용한다.
- 기본 실행 DB는 PostgreSQL로 한다.
- 테스트는 pytest 기반으로 구성한다.
- API integration test는 FastAPI TestClient 또는 httpx 기반으로 구성한다.
- 현재 시각 의존성은 `Clock` 인터페이스 또는 `now_provider` 함수로 주입한다.

비범위:

- Phase 1에서는 비즈니스 규칙 구현을 시작하지 않는다.
- Phase 1에서는 ingestion 정책(`atomic`, `partial`)의 실제 분기 로직을 구현하지 않는다.
- Phase 1의 목표는 이후 단계를 안전하게 구현할 수 있는 실행/테스트 기반을 만드는 것이다.

예상 디렉터리 구조:

```text
src/
  api/
  services/
  domain/
  repositories/
  schedulers/
  config/
  models/

tests/
  unit/
  integration/
  e2e/
```

검증:

- 최소 1개의 smoke test가 실행된다.
- 테스트 환경에서 애플리케이션 설정과 테스트용 저장소 연결이 분리된다.
- `now`를 고정값으로 주입하는 테스트 유틸이 준비된다.

완료 조건:

- 개발자가 로컬에서 test command를 실행해 테스트 러너가 정상 기동된다.
- 이후 단계의 unit/integration/e2e 테스트를 올릴 기본 틀이 준비된다.

---

### Phase 2. 도메인 규칙 구현

구현:

- payload top-level 검증
- reading 단위 필드 검증
- timestamp 파싱 및 canonical time 정규화
- health status 계산
- telemetry status 계산
- batch policy 분기 규칙(`atomic`, `partial`)

이 단계가 먼저인 이유는 이 과제의 실패 가능성이 대부분 "입력 검증"과 "시간 처리"에서 발생하기 때문이다. 또한 이 영역은 DB 없이 빠르게 unit test를 만들 수 있다.

검증:

- unit test로 UTC/KST/mixed timezone 정규화를 검증한다.
- 필수 필드 누락, invalid mode, invalid timestamp, invalid location을 검증한다.
- `NORMAL` 12분, `EMERGENCY` 30초, `DELAYED`, `CLOCK_SKEW`, `OUT_OF_ORDER` 경계값을 검증한다.

완료 조건:

- 도메인 규칙이 DB 없이 모두 테스트 가능하다.
- 시간 정규화와 상태 계산의 핵심 경계값 테스트가 통과한다.
- 이 단계의 규칙만으로도 입력값의 accept/reject를 일관되게 설명할 수 있다.

---

### Phase 3. Ingestion와 persistence 구현

구현:

- `POST /api/v1/readings`
- payload 파싱
- `object | array` 검증
- 내부 records 배열로 정규화
- record 단위 검증
- timestamp 정규화
- 저장용 record 보강
- `atomic` 또는 `partial` 정책 적용
- readings 저장
- sensor current status 갱신
- mode change request reconcile

이 단계에서 중요한 점은 `atomic`과 `partial` 차이를 service 계층 분기로 제한하는 것이다. 검증과 정규화 로직은 가능한 한 재사용해야 한다.

검증:

- integration test로 단건 성공, 배열 성공, 빈 배열 no-op success를 검증한다.
- `atomic`에서 1건 실패 시 전체 rollback을 검증한다.
- `partial`에서 일부 성공/일부 실패, 전체 실패, 저장 실패 record-level error를 검증한다.
- 저장 후 current status가 함께 갱신되는지 검증한다.

완료 조건:

- 수집 API가 문서 계약대로 응답 구조를 반환한다.
- `atomic`과 `partial`의 차이가 테스트로 명확히 고정된다.
- mixed timezone batch가 정규화된 값으로 저장된다.

---

### Phase 4. 조회 API와 상태 조회 구현

구현:

- `GET /api/v1/readings`
- `GET /api/v1/sensors/status`
- `serial_number`, `mode` 필터
- `sensor_from`, `sensor_to`
- `received_from`, `received_to`
- pagination
- 안정 정렬: `sensor_timestamp DESC, id DESC`

조회 API는 상태 계산을 직접 하지 않고, 저장된 current status를 읽는 방식으로 단순하게 유지한다.

검증:

- integration test로 serial_number, mode, sensor time range, received time range 필터를 검증한다.
- 동일 `sensor_timestamp`에서 pagination이 흔들리지 않는지 검증한다.
- `total_count == 0`일 때 `total_pages == 0` 계약을 검증한다.
- `GET /readings`에 상태 필드가 없고, `GET /sensors/status`에서만 상태가 제공되는지 검증한다.

완료 조건:

- 조회 API가 시간 필터와 정렬 계약을 안정적으로 만족한다.
- 프론트엔드가 별도 계산 없이 상태 API만으로 센서 상태를 표시할 수 있다.

---

### Phase 5. 모드 제어와 reconcile 구현

구현:

- `POST /api/v1/sensors/{serial_number}/mode`
- 입력 mode 검증
- request 저장
- `sensor_known` 여부 반환
- 실제 적용 여부는 후속 telemetry로 확인
- reconcile 시 `server_received_at >= requested_at` 조건 적용

이 기능은 단독 구현보다 ingestion 이후 reconcile 흐름과 함께 검증해야 한다.

검증:

- integration test로 mode request 저장을 검증한다.
- readings가 없는 serial에 대해 `sensor_known: false`를 검증한다.
- 요청 이전 telemetry는 applied 판정이 되지 않음을 검증한다.
- 가장 최근 미해결 요청 1건만 reconcile 대상이 되는지 검증한다.

완료 조건:

- 서버 의도 기록과 센서 실제 반영이 분리되어 저장된다.
- applied 판정 오탐이 테스트로 방지된다.

---

### Phase 6. Scheduler와 운영 시나리오 검증

구현:

- 센서 상태 재평가 job
- 일정 주기로 모든 sensor current status 점검
- `NORMAL`은 12분 기준
- `EMERGENCY`는 30초 기준
- 권장 실행 주기: 10초
- Docker 실행 구성과 README 테스트 가이드

scheduler는 계산 자체보다 "시간 경과 후 상태가 바뀌는지"를 확인하는 운영 보정 역할에 가깝다.

검증:

- 시간 고정/fake clock 기반 테스트로 상태 전이 시점을 검증한다.
- e2e test로 단건 수집 -> 조회, mixed timezone batch -> 시간순 조회를 검증한다.
- mode request -> 후속 telemetry applied 전환을 검증한다.
- 시간 경과 + scheduler 실행 후 `FAULTY` 전환을 검증한다.

완료 조건:

- 운영 시나리오 단위 테스트가 문서 시나리오와 일치한다.
- 로컬 또는 Docker 환경에서 실행/테스트 절차가 재현 가능하다.

---

## 테스트 전략

이 프로젝트는 테스트를 세 층으로 나누는 것이 가장 적절하다.

테스트 인프라 계약:

- unit test는 DB 없이 순수 함수만 검증한다.
- integration test는 테스트용 PostgreSQL과 애플리케이션 wiring을 함께 검증한다.
- e2e test는 주요 사용자 시나리오만 검증하고, 상세 경계값 검증은 unit/integration에 둔다.
- 모든 시간 기반 테스트는 고정 `clock` fixture를 사용한다.

### 1. Unit Test

대상:

- validator
- timestamp normalizer
- health evaluator
- telemetry evaluator
- query filter parser
- pagination 계산기

목표:

- 빠른 피드백
- 경계값 검증
- DB 없이 핵심 규칙 보장

가장 먼저 작성해야 할 테스트다.

### 2. Integration Test

대상:

- readings ingest API
- readings query API
- sensor status API
- sensor mode API
- repository + DB transaction
- upsert / partial update / reconcile

목표:

- HTTP + DB + service 흐름 검증
- API 계약 보장
- transaction / rollback / persistence failure 확인

### 3. End-to-End Test

대상 시나리오:

- 단건 수집 -> 조회 성공
- mixed timezone batch 수집 -> 시간순 조회
- partial batch 수집 -> 일부 저장 + 일부 실패 반환
- mode request -> 후속 telemetry로 applied 전환
- 시간 경과 + scheduler -> `FAULTY` 전환

목표:

- 운영 시나리오 단위 검증
- 문서 시나리오와 실제 동작 일치 여부 확인

---

## 우선순위 높은 테스트 목록

### 시간 정규화

- UTC timestamp 정상 파싱
- KST timestamp 정상 파싱
- UTC/KST mixed batch 정규화
- 같은 시각의 다른 표현이 같은 canonical time으로 저장되는지 확인

### 검증

- 필수 필드 누락
- invalid mode
- invalid timestamp
- invalid location 구조
- 위도/경도 범위 초과

### 배치 정책

- atomic 전체 성공
- atomic 1건 실패 시 전체 rollback
- partial 일부 성공 일부 실패
- partial 전체 실패 시 `success: false`
- 빈 배열 no-op success

### 상태 판별

- `NORMAL` 12분 경계
- `EMERGENCY` 30초 경계
- `DELAYED`
- `CLOCK_SKEW`
- `OUT_OF_ORDER`
- out-of-order 수신 시 current status partial update

### 조회

- serial_number 필터
- mode 필터
- sensor time range
- received time range
- 동일 `sensor_timestamp`에서 안정 pagination

### 모드 제어

- mode change request 저장
- 요청 이전 telemetry는 applied 판정 불가
- 가장 최근 미해결 요청 1건만 reconcile

---

## 구현 순서별 산출물

### Phase 1 - 프로젝트 골격 + 테스트 기반

산출물:

- 애플리케이션 엔트리포인트
- 설정 객체 및 환경변수 로더
- DB 세션/테스트 DB 분리 전략
- `Clock` 주입 인터페이스
- pytest 설정, fixture, smoke test

### Phase 2 - 도메인 규칙 + unit test

산출물:

- validator
- timestamp normalizer
- health/telemetry evaluator
- 관련 unit tests

### Phase 3 - ingestion + persistence

산출물:

- readings ingest API
- readings repository
- status upsert
- atomic/partial integration tests

### Phase 4 - query APIs

산출물:

- readings 조회 API
- sensor status API
- pagination/filter integration tests

### Phase 5 - mode control + reconcile

산출물:

- sensor mode API
- mode change request repository
- reconcile tests

### Phase 6 - scheduler + e2e + docker

산출물:

- health evaluation job
- time progression tests
- docker 실행 구성
- README 실행/테스트 가이드

---

## MVP 범위

먼저 완성할 최소 범위는 다음과 같다.

- `POST /api/v1/readings`
- timestamp 정규화
- `atomic` 정책
- readings 저장
- current status 갱신
- `GET /api/v1/readings`
- `GET /api/v1/sensors/status`
- 핵심 unit/integration tests

이 범위를 먼저 완료하면 과제의 핵심 평가 포인트 대부분을 보여줄 수 있다.

---

## 확장 우선순위

MVP 이후 우선순위는 다음과 같다.

1. `partial` batch policy
2. mode control request + reconcile
3. scheduler 기반 health reevaluation
4. Docker / README / sample requests
5. 추가 운영 로그 / observability

---

## 테스트 가능성을 높이는 핵심 설계 결정

- 현재 시각은 주입 가능하게 설계한다.
- timestamp 정규화는 순수 함수로 만든다.
- health 계산은 DB 없이 테스트 가능해야 한다.
- repository는 interface 기반으로 분리한다.
- scheduler는 얇게 유지하고 계산은 service로 위임한다.
- out-of-order / reconcile 같은 tricky rule은 반드시 integration test로 고정한다.

---

## 결론

이 구현 계획의 핵심은 "기능을 빨리 많이 만드는 것"이 아니라, 과제의 핵심 난제인 시간 정규화, 배치 정책, 상태 판별을 작은 단위로 쪼개고 각각을 테스트로 고정하는 것이다.

즉, 이 프로젝트는 구현 계획과 테스트 계획이 분리되지 않는다.
테스트 가능하게 설계하는 것이 곧 좋은 구현 계획이다.
