# MQTT 대비 Adapter 패턴 적용 완료

## 개요

현재 HTTP 기반 FastAPI 시스템을 MQTT와도 호환될 수 있도록 Adapter 패턴을 적용했습니다. Service Layer는 그대로 유지하고, Transport Layer를 추가하여 프로토콜 독립적인 구조를 만들었습니다.

## 구조

```
[HTTP Router] ──┐
[MQTT Handler] ─┼──> [Transport] ──> [Service] ──> [Repository/Domain]
                │
         [SensorTransport Interface]
```

## 생성된 파일

### 1. Transport 인터페이스
**파일**: `src/transports/sensor_transport.py`

프로토콜 독립적인 추상 인터페이스를 정의합니다.

```python
class SensorTransport(ABC):
    @abstractmethod
    async def ingest_data(self, payload: Any, ingest_mode: str) -> IngestResult: ...
    
    @abstractmethod
    async def request_mode_change(self, serial_number: str, mode: str) -> ModeChangeResult: ...
    
    @abstractmethod
    async def get_sensor_status(self, ...) -> SensorStatusResult: ...
```

**특징**:
- HTTP/MQTT 모두 동일한 인터페이스로 Service 호출 가능
- 결과 객체는 프로토콜 독립적 (IngestResult, ModeChangeResult, SensorStatusResult)
- 각 Protocol Handler가 결과를 자신의 방식으로 변환

### 2. HTTP Transport 구현
**파일**: `src/transports/http_transport.py`

HTTP 전용 Transport 구현체입니다.

```python
class HttpSensorTransport(SensorTransport):
    def __init__(self, session, clock, ...):
        # Service Layer 인스턴스 생성
        self._ingestion_service = IngestionService(session, clock)
        self._mode_service = ModeService(session, clock)
        self._query_service = QueryService(session)
```

**동작**:
- HTTP Router에서 DI로 주입받아 사용
- Service Layer 호출 후 프로토콜 독립적 결과 반환
- Router에서 HTTP 응답 코드/JSON 변환 수행

### 3. Router 수정

#### readings_router.py
- `HttpSensorTransport`를 DI로 주입
- `transport.ingest_data()` 호출 후 HTTP 응답 코드 결정
- 읽기 전용 쿼리는 `QueryService` 직접 사용 (Transport 불필요)

#### sensors_router.py
- 모드 변경: `HttpSensorTransport.request_mode_change()` 사용
- 상태 조회: `QueryService` 직접 사용 (단순 조회)

## MQTT 추가 시 구현 방법

### 1. MqttTransport 구현

```python
# src/transports/mqtt_transport.py
class MqttSensorTransport(SensorTransport):
    def __init__(self, mqtt_client, session, clock):
        self._mqtt = mqtt_client
        self._ingestion_service = IngestionService(session, clock)
        self._mode_service = ModeService(session, clock)
    
    async def ingest_data(self, payload, ingest_mode) -> IngestResult:
        # Service Layer 호출 (HTTP와 동일)
        result = await self._ingestion_service.ingest(payload, IngestMode(ingest_mode))
        # 결과를 MQTT 메시지로 발행 가능
        return IngestResult(...)
```

### 2. MQTT Handler 등록

```python
# MQTT 메시지 핸들러
@mqtt.subscribe("sensors/+/data")
async def handle_sensor_data(topic, payload):
    serial_number = extract_sn(topic)
    transport = MqttSensorTransport(mqtt_client, session, clock)
    result = await transport.ingest_data(payload, "PARTIAL")
    
    # MQTT 방식으로 결과 처리 (HTTP 응답 대신 메시지 발행)
    if not result.success:
        mqtt.publish(f"sensors/{serial_number}/error", json.dumps(result.errors))
```

### 3. 토픽 네이밍 컨벤션

```
sensors/
├── {serial_number}/
│   ├── data              # [Pub: 센서] 센서 데이터 (QoS 1)
│   ├── status            # [Pub: 서버] 센서 상태 (retain)
│   ├── mode/
│   │   ├── set           # [Pub: 서버] 모드 변경 요청 (QoS 2)
│   │   └── status        # [Pub: 서버] 현재 모드 상태 (retain)
│   └── lwt               # [Pub: 브로커] 연결 끊김 감지 (retain)
```

## 테스트 결과

- **125개 테스트 통과** (97%)
- **2개 실패**: `test_status.py`의 경계값 테스트 (기존 이슈, Transport와 무관)
- **1개 스킵**: 스케줄러 관련

## 장점

1. **Service Layer 재사용**: HTTP와 MQTT가 동일한 비즈니스 로직 사용
2. **Protocol 독립성**: Service는 HTTP/MQTT를 알 필요 없음
3. **점진적 마이그레이션**: Feature flag로 센서별 HTTP/MQTT 선택 가능
4. **테스트 용이성**: Transport Mock으로 단위 테스트 가능

## 향후 작업

### Phase 1: 브로커 도입 (1-2주)
- Mosquitto 또는 EMQX 설치
- `docker-compose.yml`에 MQTT 브로커 추가

### Phase 2: MqttTransport 구현 (1주)
- `paho-mqtt` 또는 `fastapi-mqtt` 선택
- 메시지 핸들러 구현

### Phase 3: Dual Mode 운영 (2-4주)
- 센서별 HTTP/MQTT 라우팅
- 모니터링 체계 구축

### Phase 4: 완전 전환 (미래)
- 모든 센서 MQTT 전환
- HTTP API는 레거시 지원 또는 제거

---

**구현일**: 2025-03-13
**버전**: 1.0
