# 3. Architecture

## Content

### 문서 목적

이 문서는 `docs/SPECIFICATION.md`와 `docs/PSEUDOCODE.md`에서 정의한 요구사항과 처리 흐름을 실제 시스템 구조로 정리한 아키텍처 문서다. 목적은 기능 요구사항을 충족하는 구성 요소를 정의하고, 각 구성 요소의 책임, 상호작용, 저장 구조, 상태 평가 방식, 확장 포인트를 명확히 하여 구현 단계에서 설계의 일관성을 유지하는 것이다.

이 문서는 특정 프레임워크에 고정되지 않으며, 기본적인 웹 서비스 환경에서 동작 가능한 기술 중립적 구조를 제안한다.

### 아키텍처 목표

- 단건 및 배치 센서 데이터 수집을 안정적으로 처리한다.
- mixed timezone timestamp를 일관된 내부 기준 시각으로 정규화한다.
- 조회 API와 상태 API가 빠르게 응답할 수 있도록 저장 구조를 분리한다.
- 메시지 큐 없이도 센서 상태 판별과 모드 제어 요구사항을 만족한다.
- 구현 복잡도를 과도하게 높이지 않으면서 `atomic`과 `partial` 정책을 모두 수용한다.
- Docker 기반 실행과 테스트가 가능한 단순한 구성으로 유지한다.

### 아키텍처 스타일

이 시스템은 `계층형 모듈러 모놀리식 아키텍처`를 채택한다.

#### 선택 이유

- 과제의 범위가 단일 백엔드 서비스로 충분히 수용 가능하다.
- 메시지 큐, 별도 이벤트 버스, 다중 마이크로서비스 같은 복잡한 분산 구조 없이도 요구사항을 만족할 수 있다.
- 수집, 검증, 정규화, 저장, 조회, 상태 평가, 모드 제어를 계층별로 나누면 책임이 선명해지고 테스트가 쉬워진다.
- 향후 필요하면 모듈 단위로 서비스 분리도 가능하지만, 현재 단계에서는 단일 배포 단위가 더 적절하다.

#### 채택하지 않은 대안

- 마이크로서비스: 과제 규모 대비 과도한 운영 복잡도를 유발한다.
- 이벤트 드리븐 분산 아키텍처: 메시지 큐 제한과 상충하며 구현 범위를 불필요하게 확장한다.
- 단순 CRUD 중심 구조: 시간 정규화와 상태 판별 같은 핵심 규칙을 명확히 분리하기 어렵다.

### 시스템 컨텍스트

```text
[Sensor / Gateway Client]
        |
        | HTTP REST
        v
[Backend Service]
   |        |          |
   |        |          +--> [Scheduler / Health Evaluation Job]
   |        |
   |        +--> [Persistent Data Store]
   |
   +--> [Frontend / Operator Client]
```

#### 외부 행위자

- Sensor / Gateway Client: 센서 측정 데이터를 단건 또는 배치로 전송한다.
- Frontend / Operator Client: 조회, 상태 확인, 모드 제어 요청을 수행한다.
- Scheduler: 주기적으로 센서 상태를 재평가한다.

### 고수준 구성 요소

```text
Presentation Layer
  - Ingestion API
  - Readings Query API
  - Sensor Status API
  - Sensor Mode API

Application Layer
  - Ingestion Orchestrator
  - Query Orchestrator
  - Sensor Health Orchestrator
  - Mode Control Orchestrator

Domain Layer
  - Reading Validation Rules
  - Timestamp Normalization Rules
  - Health Evaluation Rules
  - Batch Ingestion Policy Rules

Persistence Layer
  - Sensor Readings Store
  - Sensor Current Status Store
  - Mode Change Request Store

Operational Layer
  - Logging
  - Error Mapping
  - Scheduling
```

### 계층별 책임

#### 1. Presentation Layer

책임:

- HTTP 요청/응답 처리
- request parameter 추출
- body 파싱 및 API 계약 적용
- application layer 호출
- 응답 포맷 표준화

포함 엔드포인트:

- `POST /api/v1/readings`
- `GET /api/v1/readings`
- `GET /api/v1/sensors/status`
- `POST /api/v1/sensors/{serial_number}/mode`

주의사항:

- 비즈니스 판단은 controller에 과도하게 두지 않는다.
- `atomic`, `partial` 분기 자체는 application layer에서 처리한다.

#### 2. Application Layer

책임:

- API 단위 유스케이스 실행
- 여러 domain rule과 repository 호출 순서 조정
- 트랜잭션 경계 제어
- 정책(`atomic`, `partial`)에 따른 분기
- 응답 조립에 필요한 결과 집계

주요 서비스:

- `IngestionService`
- `QueryService`
- `SensorHealthService`
- `SensorModeService`

#### 3. Domain Layer

책임:

- 입력 검증 규칙 정의
- timestamp 정규화 규칙 정의
- 센서 건강 상태 계산 규칙 정의
- 오류를 요청 수준/레코드 수준으로 분류하는 규칙 정의

도메인 규칙 예시:

- `mode`는 `NORMAL`, `EMERGENCY`만 허용
- `timestamp`는 timezone-aware ISO8601이어야 함
- `NORMAL`은 12분 초과 미수신 시 `FAULTY`
- `EMERGENCY`는 30초 초과 미수신 시 `FAULTY`

#### 4. Persistence Layer

책임:

- 측정값 저장
- 센서별 최신 상태 저장
- 모드 변경 요청 이력 저장
- 조회 필터 및 pagination 지원
- 상태 업데이트 및 upsert 지원

주의사항:

- 센서 이력 데이터와 최신 상태 데이터는 조회 목적이 다르므로 논리적으로 분리한다.
- 구현은 하나의 DB 안에 있어도 되지만, 테이블/컬렉션 역할은 분리한다.

#### 5. Operational Layer

책임:

- 주기적 센서 상태 재평가
- 에러 로깅 및 요청 추적
- 운영 시점 모니터링을 위한 로그 이벤트 기록

### 주요 유스케이스별 아키텍처 흐름

#### 1. 센서 데이터 수집 흐름

```text
Sensor/Gateway
  -> Ingestion API Controller
  -> IngestionService
  -> PayloadValidator
  -> TimestampNormalizer
  -> BatchPolicyProcessor (atomic | partial)
  -> SensorReadingRepository
  -> SensorStatusRepository
  -> Response Builder
  -> Client
```

핵심 설명:

- request body는 controller에서 파싱되지만, 유효성 판단은 service/domain 계층에서 수행한다.
- timestamp 정규화는 저장 전에 완료되어야 한다.
- 저장 성공 후 센서 최신 상태 저장소를 갱신한다.
- `partial` 모드에서는 valid/invalid 레코드를 분리해 처리한다.

#### 2. 조회 흐름

```text
Operator/Frontend
  -> Query API Controller
  -> QueryService
  -> FilterBuilder
  -> SensorReadingRepository
  -> SensorStatusRepository (optional join/read)
  -> Response Mapper
  -> Client
```

핵심 설명:

- 이력 조회는 `Sensor Readings Store`가 주 데이터 소스다.
- 상태 정보는 `Sensor Current Status Store`에서 보강한다.
- 시간 범위 필터는 정규화된 내부 시각 기준으로 처리한다.

#### 3. 센서 상태 평가 흐름

```text
Scheduler
  -> SensorHealthEvaluationJob
  -> SensorHealthService
  -> SensorStatusRepository.find_all()
  -> HealthRuleEvaluator
  -> SensorStatusRepository.update_health_status()
```

핵심 설명:

- 상태 평가는 이벤트 기반 메시지 처리 없이도 scheduled job으로 충분히 수행 가능하다.
- 새 데이터 수신 시 즉시 상태를 갱신하고, 스케줄러는 보정 역할을 수행할 수 있다.

#### 4. 모드 제어 흐름

```text
Operator/Frontend
  -> SensorModeController
  -> SensorModeService
  -> ModeChangeRequestRepository
  -> Response Builder
  -> Client
```

핵심 설명:

- 서버 요청은 우선 "의도 기록"으로 저장한다.
- 실제 센서 적용 여부는 후속 텔레메트리의 `mode`를 통해 확인한다.

### 배치 정책 설계

#### Atomic 모드

구조적 의미:

- 하나의 배치를 하나의 논리 단위로 취급한다.
- 검증 실패 또는 저장 실패가 발생하면 전체 저장을 취소한다.

아키텍처 요구사항:

- 트랜잭션 지원 필요
- 전체 검증 이후 저장 단계 진입
- 실패 시 rollback 가능해야 함

장점:

- 구현과 테스트가 상대적으로 단순하다.
- 클라이언트 입장에서 결과가 명확하다.

단점:

- 일부 정상 레코드까지 함께 버릴 수 있다.

#### Partial 모드

구조적 의미:

- 레코드 단위로 유효성 판단을 수행한다.
- 유효한 데이터는 저장하고 실패 데이터는 오류 리스트로 분리한다.

아키텍처 요구사항:

- 레코드 단위 오류 수집 구조 필요
- 성공 건수/실패 건수 집계 필요
- 응답에서 레코드별 오류를 표현할 수 있어야 함

장점:

- 운영 환경에서 데이터 유실을 줄일 수 있다.

단점:

- 응답 구조와 상태 추적이 더 복잡해진다.

### 데이터 모델과 저장 구조

#### 1. Sensor Readings Store

목적:

- 승인된 모든 측정 레코드의 원본에 가까운 이력을 저장한다.

권장 필드:

- `id`
- `serial_number`
- `raw_timestamp`
- `sensor_timestamp`
- `server_received_at`
- `mode`
- `temperature`
- `humidity`
- `pressure`
- `latitude`
- `longitude`
- `air_quality`
- `created_at`

역할:

- 이력 조회의 기준 데이터
- 시간 필터링과 분석의 기준
- 추후 통계/집계 확장의 기반

권장 인덱스:

- `serial_number`
- `sensor_timestamp`
- `server_received_at`
- `serial_number + sensor_timestamp`

#### 2. Sensor Current Status Store

목적:

- 센서별 최신 상태를 빠르게 조회한다.

권장 필드:

- `serial_number`
- `last_sensor_timestamp`
- `last_server_received_at`
- `last_reported_mode`
- `health_status`
- `health_evaluated_at`
- `last_reading_id`

역할:

- 상태 API의 주 데이터 소스
- 조회 응답에 `status`를 빠르게 보강
- 스케줄러가 갱신 대상으로 활용

#### 3. Mode Change Request Store

목적:

- 서버가 요청한 모드 제어 이력을 저장한다.

권장 필드:

- `id`
- `serial_number`
- `requested_mode`
- `requested_at`
- `request_status`
- `observed_applied_at`

역할:

- 운영 감사 로그
- 센서 보고 모드와 서버 요청 모드 비교 근거

### 시간 처리 아키텍처

#### 원칙

- 모든 외부 입력 시각은 파싱 즉시 canonical time으로 변환한다.
- 저장, 필터링, 정렬, 상태 판별은 canonical time 기준으로 수행한다.
- raw timestamp는 별도 보존하여 디버깅과 추적에 활용한다.

#### 시간 관련 필드 역할 분리

- `raw_timestamp`: 센서가 보낸 원본 문자열
- `sensor_timestamp`: 센서 생성 시각의 정규화 결과
- `server_received_at`: 서버가 수신한 시각

#### 시간 처리 파이프라인

```text
raw input timestamp
  -> parse with timezone awareness
  -> convert to canonical time
  -> persist canonical time
  -> use canonical time in filtering / ordering / health checks
```

### 상태 판별 아키텍처

#### 규칙 엔진 수준 설계

```text
if last_reported_mode == NORMAL:
    threshold = 12 minutes
else if last_reported_mode == EMERGENCY:
    threshold = 30 seconds
else:
    status = UNKNOWN

if now - last_server_received_at > threshold:
    status = FAULTY
else:
    status = HEALTHY
```

#### 평가 시점

- 새 텔레메트리 저장 직후
- 주기적 재평가 작업 실행 시
- 필요하다면 상태 API 호출 시 보정 계산 가능

#### 왜 최신 상태 저장소가 필요한가

- 모든 조회 요청마다 이력 전체를 탐색하면 비효율적이다.
- 운영 UI는 현재 상태를 빠르게 받아야 한다.
- 상태 평가 책임을 응답 시점 계산에만 의존하면 일관성이 떨어질 수 있다.

### 컴포넌트 간 상호작용 규칙

#### IngestionService

- validator와 normalizer를 호출한다.
- batch policy에 따라 atomic/partial 흐름을 선택한다.
- repository를 호출해 readings를 저장한다.
- 저장 후 status store를 갱신한다.

#### QueryService

- request parameter를 filter 조건으로 변환한다.
- readings store를 조회한다.
- 필요 시 current status store의 상태를 결합한다.
- pagination 메타데이터를 포함해 응답을 조립한다.

#### SensorHealthService

- 상태 판별 규칙을 캡슐화한다.
- 스케줄러 및 수집 후 갱신 흐름에서 재사용된다.

#### SensorModeService

- 입력 모드를 검증한다.
- 모드 변경 요청을 기록한다.
- 실제 적용은 후속 telemetry를 통해 확인한다.

### 오류 처리 아키텍처

#### 오류 계층 구분

```text
Request-level Error
  - malformed JSON
  - invalid top-level payload
  - unsupported ingest_mode

Record-level Error
  - missing required field
  - invalid enum value
  - invalid timestamp
  - invalid location value
  - invalid metric type

Persistence-level Error
  - transaction failure
  - repository unavailable
  - storage write failure
```

#### 처리 전략

- request-level error는 즉시 실패 응답 반환
- record-level error는 batch policy에 따라 전체 실패 또는 부분 실패로 처리
- persistence-level error는 로그를 남기고 안전한 실패 응답으로 매핑

### 보안 및 운영 고려사항

현재 과제 범위에서는 인증/인가가 핵심 요구사항은 아니지만, 아키텍처는 향후 보강 가능해야 한다.

권장 포인트:

- API 인증 계층을 추후 삽입 가능하도록 controller 외부에서 처리 가능하게 설계
- 요청 단위 correlation id 또는 trace id 기록
- ingestion 실패 로그와 health status 변경 로그 기록
- mode change 요청 로그 보존

### 성능 및 확장성 고려사항

#### 현재 범위에서 중요한 성능 포인트

- batch 수집 시 단건 반복 요청보다 네트워크 오버헤드를 줄일 수 있음
- 읽기 성능을 위해 readings 이력과 current status를 분리
- 시간 범위 조회와 serial number 조회를 위한 인덱스 필요

#### 미래 확장 가능성

- 새로운 센서 모드 추가
- 측정값 필드 확장
- 통계/집계 API 추가
- idempotency key 기반 중복 방지
- 알림 기능 추가

### 배포 관점 구조

```text
[Container]
  - Backend Application
  - Scheduler Process (same container or separate process)

[Persistent Store]
  - relational or equivalent persistent storage
```

#### 배포 관점 원칙

- 과제 제출 기준으로는 단일 서비스 이미지 구성이 가장 단순하다.
- 스케줄러는 동일 프로세스 내부 task, 별도 worker, 또는 별도 컨테이너로 분리 가능하다.
- 실제 구현 단계에서는 가장 단순한 실행 방법을 우선 선택하는 것이 적절하다.

### 파일/모듈 구조 제안

```text
docs/
  REQUIREMENTS.md
  SPECIFICATION.md
  PSEUDOCODE.md
  ARCHITECTURE.md

src/
  api/
    ingestion_controller
    query_controller
    sensor_status_controller
    sensor_mode_controller

  services/
    ingestion_service
    query_service
    sensor_health_service
    sensor_mode_service

  domain/
    validation_rules
    timestamp_normalizer
    health_rules
    error_types

  repositories/
    sensor_reading_repository
    sensor_status_repository
    mode_change_request_repository

  schedulers/
    sensor_health_evaluation_job

  config/
  models/

tests/
  unit/
  integration/
```

### Architecture Decision Summary

```text
Decision 1:
    Use modular monolith instead of microservices
Reason:
    Simpler deployment and lower operational complexity for assignment scope

Decision 2:
    Normalize timestamps at ingestion boundary
Reason:
    Prevent inconsistent filtering, ordering, and health evaluation

Decision 3:
    Separate readings history store and current status store
Reason:
    Improve query performance and simplify status retrieval

Decision 4:
    Support both atomic and partial batch ingestion policies
Reason:
    Balance simple default implementation with operational flexibility

Decision 5:
    Use scheduler-based health reevaluation instead of MQ/event-driven monitoring
Reason:
    Meets assignment constraints with lower complexity
```

## Reflection

이 아키텍처는 과제의 핵심 난제를 해결하는 데 집중하도록 설계되었다. 특히 mixed timezone 처리, batch ingestion policy, 센서 상태 판별은 단순 CRUD 구조로는 쉽게 흡수되지 않는 요구사항이므로, domain rule과 application orchestration을 분리하는 방향이 적절하다. 이 분리는 구현 단계에서 테스트 용이성과 변경 대응력 모두를 높여준다.

가장 중요한 구조적 선택은 모듈러 모놀리식 아키텍처다. 지금 단계에서 마이크로서비스를 도입하면 분산 트랜잭션, 서비스 간 통신, 운영 복잡도 같은 문제가 오히려 과제의 본질을 흐릴 가능성이 크다. 반면 모듈 경계를 명확히 둔 단일 서비스는 요구사항을 충분히 만족시키면서도 이후 확장 가능성을 남겨둔다.

또 하나 중요한 결정은 이력 저장소와 현재 상태 저장소를 분리한 점이다. 센서 이력은 append 중심 데이터이고, 상태는 최신성 중심 데이터다. 두 역할을 하나의 구조에 동시에 담으려 하면 조회 비용과 상태 계산 책임이 섞이기 쉽다. 따라서 논리적 분리는 단순한 최적화가 아니라 책임 분리를 위한 설계 선택이다.

상태 평가를 스케줄러 기반으로 보완한 것도 과제 제약을 잘 활용한 선택이다. 메시지 큐가 없는 환경에서도 최신 상태를 유지하려면 새 데이터 수신 시 즉시 갱신과 주기적 재평가를 조합하는 방식이 현실적이다. 이는 과도한 인프라 없이도 운영자에게 유용한 상태 정보를 제공할 수 있게 한다.

마지막으로, 이 문서는 기술 중립적이지만 실제 구현에 충분히 가까운 수준의 구조를 제공한다. 다음 단계에서는 이 아키텍처를 바탕으로 구체적인 기술 스택, 데이터베이스 타입, 스케줄링 방식, 트랜잭션 전략을 선택하면 된다. 즉, 이제부터는 무엇을 만들지보다 어떻게 구체 기술로 옮길지를 결정하는 단계로 넘어갈 수 있다.
