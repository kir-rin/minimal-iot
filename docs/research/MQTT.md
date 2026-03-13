# MQTT 도입을 위한 기술 조사

> **목적**: 현재 FastAPI 기반 IoT 센서 시스템을 MQTT로 마이그레이션하되, 기존 HTTP API와의 호환성을 유지하고 데이터 유실을 방지하기 위한 기술 조사

---

## 📋 현재 아키텍처 분석

### 시스템 개요
현재 시스템은 **FastAPI 기반 REST API**로 다음 기능을 제공:

| 기능 | HTTP Method | Endpoint | 설명 |
|------|-------------|----------|------|
| 센서 데이터 수집 | POST | `/api/v1/readings` | 단일/배치 데이터 수집 (ATOMIC/PARTIAL 모드) |
| 데이터 조회 | GET | `/api/v1/readings` | 필터링 및 페이지네이션 지원 조회 |
| 센서 상태 조회 | GET | `/api/v1/sensors/status` | 센서별 건강/텔레메트리 상태 |
| 모드 변경 요청 | POST | `/api/v1/sensors/{sn}/mode` | NORMAL/EMERGENCY 모드 변경 |

### 핵심 데이터 흐름

```
[센서] ──HTTP POST──> [FastAPI] ──> [IngestionService] ──> [PostgreSQL]
                                        ↓
                                   [ModeService] ──> [Reconcile]
```

### 데이터 스키마 핵심 필드

```python
# 센서 데이터 페이로드
{
    "serial_number": str,      # 센서 식별자
    "timestamp": str,          # ISO8601 센서 생성 시각
    "mode": "NORMAL|EMERGENCY", # 작동 모드
    "temperature": float,
    "humidity": float,
    "pressure": float,
    "air_quality": int,
    "location": {"lat": float, "lng": float}
}
```

---

## 🎯 MQTT 핵심 개념: 데이터 유실 방지

### 1. QoS (Quality of Service) 레벨

메시지 전달 보장 수준을 설정하는 핵심 메커니즘:

| QoS | 이름 | 전달 보장 | 사용 시나리오 | 오버헤드 |
|-----|------|-----------|---------------|----------|
| **0** | At most once | 최대 1회 (손실 가능) | 빈번한 주기적 데이터 (온도) | 낮음 |
| **1** | At least once | 최소 1회 (중복 가능) | 중요 데이터 (모드 변경 요청) | 중간 |
| **2** | Exactly once | 정확히 1회 (중복 없음) | 결제, 명령 실행 | 높음 |

#### QoS 동작 원리

```
QoS 0:  Publisher ──PUBLISH────> Broker ──PUBLISH────> Subscriber

QoS 1:  Publisher ──PUBLISH────> Broker ──PUBACK──────> Publisher
                      ↓
                 Broker ──PUBLISH────> Subscriber ──PUBACK──> Broker

QoS 2:  Publisher ──PUBLISH────> Broker ──PUBREC──────> Publisher
        Publisher ──PUBREL─────> Broker ──PUBCOMP─────> Publisher
                      ↓
                 Broker ──PUBLISH────> Subscriber ──PUBREC──> Broker
                 Subscriber <──PUBREL─── Broker
                 Subscriber ──PUBCOMP──> Broker
```

### 2. Retain 메시지

**마지막 메시지 영속화** - 새로운 구독자가 토픽을 구독할 때 마지막으로 발행된 메시지를 즉시 수신:

```python
# 센서 상태 토픽에 Retain 적용
client.publish(
    "sensors/SN001/status",
    payload=json.dumps({"health": "HEALTHY", "last_seen": "2024-01-01T00:00:00Z"}),
    qos=1,
    retain=True  # ← 마지막 상태 유지
)
```

**활용 시나리오**:
- 센서별 최신 건강 상태 유지
- 모드 변경 후 현재 모드 상태 유지
- 장치별 마지막 위치 정보 유지

### 3. Last Will and Testament (LWT)

**비정상 연결 종료 감지** - 클라이언트가 graceful disconnect 없이 끊어지면 브로커가 대신 발행하는 메시지:

```python
# 연결 설정 시 LWT 구성
client.will_set(
    topic="sensors/SN001/lwt",
    payload=json.dumps({"status": "offline", "timestamp": "2024-01-01T00:00:00Z"}),
    qos=1,
    retain=True
)

# 정상 종료 시
client.disconnect()  # LWT 발행되지 않음

# 비정상 종료 (네트워크 단절, 전원 off 등)
# → 브로커가 자동으로 LWT 메시지 발행
```

**활용 시나리오**:
- 센서 오프라인 감지 및 알림
- 센서 상태를 FAULTY로 자동 전환

### 4. Persistent Session (Clean Session = False)

**오프라인 메시지 큐잉** - 클라이언트 재연결 시 누락된 메시지 수신:

```python
# 클라이언트 설정
client = mqtt.Client(
    client_id="backend-server-001",  # 고정 ID 필수
    clean_session=False               # ← 세션 유지
)

# 구독 설정 (QoS 1 이상)
client.subscribe("sensors/+/data", qos=1)
client.subscribe("sensors/+/mode", qos=1)

# 연결 끊김 동안 브로커가 메시지 큐잉
# 재연결 시 누락된 메시지 일괄 수신
```

**요구사항**:
- `clean_session=False` 설정
- 고정된 `client_id` 사용
- 구독 QoS 1 이상
- 브로커 설정 (max_queued_messages 등)

---

## 📚 라이브러리 비교 분석

### 1. Paho MQTT Python (Eclipse)

```python
import paho.mqtt.client as mqtt
import json

class SensorMqttClient:
    def __init__(self, broker_host: str, broker_port: int = 1883):
        self.client = mqtt.Client(
            client_id="sensor-backend-001",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # LWT 설정
        self.client.will_set(
            topic="backend/status",
            payload=json.dumps({"status": "offline"}),
            qos=1,
            retain=True
        )
        
        self.broker_host = broker_host
        self.broker_port = broker_port
    
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"Connection failed: {reason_code}")
            return
        
        # 구독은 반드시 on_connect에서 수행 (재연결 시 자동 구독)
        client.subscribe("sensors/+/data", qos=1)
        client.subscribe("sensors/+/mode_request", qos=1)
        
        # 상태 발행
        client.publish(
            "backend/status",
            json.dumps({"status": "online", "version": "1.0.0"}),
            qos=1,
            retain=True
        )
    
    def _on_message(self, client, userdata, message):
        topic = message.topic
        payload = json.loads(message.payload.decode())
        
        if "data" in topic:
            self._handle_sensor_data(payload)
        elif "mode_request" in topic:
            self._handle_mode_change(payload)
    
    def _handle_sensor_data(self, payload: dict):
        # 기존 IngestionService 로직 연동
        pass
    
    def _handle_mode_change(self, payload: dict):
        # 기존 ModeService 로직 연동
        pass
    
    def start(self):
        self.client.connect(self.broker_host, self.broker_port)
        self.client.loop_start()
    
    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
```

**장점**:
- ✅ 표준 MQTT 구현 (Eclipse Foundation)
- ✅ 세밀한 제어 가능 (QoS, retain, LWT 등)
- ✅ 동기/비동기 API 모두 지원
- ✅ 광범위한 문서와 커뮤니티

**단점**:
- ❌ FastAPI와 통합 시 추가 작업 필요
- ❌ 콜백 기반 API (async/await 불편)

### 2. FastAPI-MQTT

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_mqtt import FastMQTT, MQTTConfig

mqtt_config = MQTTConfig(
    host="mqtt.broker.com",
    port=1883,
    keepalive=60,
    # LWT 설정
    will_message_topic="backend/status",
    will_message_payload='{"status": "offline"}',
    will_delay_interval=5,
)

fast_mqtt = FastMQTT(config=mqtt_config)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await fast_mqtt.mqtt_startup()
    yield
    await fast_mqtt.mqtt_shutdown()

app = FastAPI(lifespan=lifespan)

@fast_mqtt.on_connect()
def connect(client, flags, rc, properties):
    # 자동 구독 (재연결 시에도 유지)
    fast_mqtt.client.subscribe("sensors/+/data", qos=1)
    fast_mqtt.client.subscribe("sensors/+/mode_request", qos=1)
    
    # 상태 발행
    fast_mqtt.publish(
        "backend/status",
        '{"status": "online"}',
        qos=1,
        retain=True
    )

@fast_mqtt.subscribe("sensors/+/data", qos=1)
async def handle_sensor_data(client, topic, payload, qos, properties):
    """와일드카드 토픽 구독"""
    data = json.loads(payload.decode())
    
    # 시리얼 번호 추출 (토픽: sensors/SN001/data)
    serial_number = topic.split("/")[1]
    
    # 기존 IngestionService 연동
    await ingest_service.ingest(data, IngestMode.PARTIAL)

@fast_mqtt.subscribe("sensors/+/mode_request", qos=2)  # 중요: QoS 2
async def handle_mode_request(client, topic, payload, qos, properties):
    """모드 변경 요청 처리 (중복 방지)"""
    request = json.loads(payload.decode())
    
    serial_number = topic.split("/")[1]
    mode = request.get("mode")
    
    # 기존 ModeService 연동
    await mode_service.request_mode_change(serial_number, Mode(mode))

@app.get("/publish/test")
async def publish_test():
    """HTTP 엔드포인트에서 MQTT 발행"""
    fast_mqtt.publish(
        "sensors/SN001/mode",
        '{"mode": "EMERGENCY"}',
        qos=1,
        retain=True
    )
    return {"result": "published"}
```

**장점**:
- ✅ FastAPI와 자연스러운 통합
- ✅ 데코레이터 기반 구독 핸들러
- ✅ async/await 기반
- ✅ Lifespan 관리 자동화

**단점**:
- ❌ gmqtt 기반 (paho-mqtt보다 생태계 작음)
- ❌ 세밀한 제어 한계

---

## 🏗️ 호환성 설계 방안

### Adapter 패턴 적용

HTTP와 MQTT를 동일한 인터페이스로 처리:

```python
from abc import ABC, abstractmethod
from typing import Any
from src.domain.types import IngestMode, Mode

class SensorTransport(ABC):
    """센서 통신 추상화 인터페이스"""
    
    @abstractmethod
    async def ingest_reading(self, data: dict, mode: IngestMode) -> dict:
        """센서 데이터 수집"""
        pass
    
    @abstractmethod
    async def request_mode_change(self, serial_number: str, mode: Mode) -> dict:
        """모드 변경 요청"""
        pass
    
    @abstractmethod
    async def get_sensor_status(self, serial_number: str | None = None) -> dict:
        """센서 상태 조회"""
        pass


class HttpSensorTransport(SensorTransport):
    """HTTP 기반 구현 (기존 유지)"""
    
    def __init__(self, ingestion_service, mode_service, query_service):
        self.ingestion = ingestion_service
        self.mode = mode_service
        self.query = query_service
    
    async def ingest_reading(self, data: dict, mode: IngestMode) -> dict:
        return await self.ingestion.ingest(data, mode)
    
    async def request_mode_change(self, serial_number: str, mode: Mode) -> dict:
        return await self.mode.request_mode_change(serial_number, mode)
    
    async def get_sensor_status(self, serial_number: str | None = None) -> dict:
        return await self.query.query_sensor_status(serial_number)


class MqttSensorTransport(SensorTransport):
    """MQTT 기반 구현 (신규)"""
    
    def __init__(self, mqtt_client, ingestion_service, mode_service, query_service):
        self.mqtt = mqtt_client
        self.ingestion = ingestion_service
        self.mode = mode_service
        self.query = query_service
        
        # MQTT 메시지 핸들러 등록
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.mqtt.subscribe("sensors/+/data", qos=1)
        async def on_data(client, topic, payload, qos, properties):
            serial_number = self._extract_sn(topic)
            data = json.loads(payload.decode())
            data["serial_number"] = serial_number
            
            result = await self.ingestion.ingest(data, IngestMode.PARTIAL)
            
            # 결과 발행 (선택적)
            if not result.success:
                self.mqtt.publish(
                    f"sensors/{serial_number}/error",
                    json.dumps({"errors": [e.dict() for e in result.errors]}),
                    qos=1
                )
        
        @self.mqtt.subscribe("sensors/+/mode/set", qos=2)
        async def on_mode_set(client, topic, payload, qos, properties):
            serial_number = self._extract_sn(topic)
            request = json.loads(payload.decode())
            
            result = await self.mode.request_mode_change(
                serial_number, 
                Mode(request["mode"])
            )
            
            # 모드 변경 요청 상태 발행
            self.mqtt.publish(
                f"sensors/{serial_number}/mode/status",
                json.dumps({
                    "requested_mode": result.requested_mode,
                    "status": result.request_status,
                    "requested_at": result.requested_at.isoformat()
                }),
                qos=1,
                retain=True
            )
    
    def _extract_sn(self, topic: str) -> str:
        return topic.split("/")[1]
    
    async def ingest_reading(self, data: dict, mode: IngestMode) -> dict:
        """MQTT로 데이터 발행 (게이트웨이 패턴)"""
        serial_number = data["serial_number"]
        self.mqtt.publish(
            f"sensors/{serial_number}/data",
            json.dumps(data),
            qos=1
        )
        return {"success": True, "message": "Published to MQTT"}
    
    async def request_mode_change(self, serial_number: str, mode: Mode) -> dict:
        """MQTT로 모드 변경 요청 발행"""
        self.mqtt.publish(
            f"sensors/{serial_number}/mode/set",
            json.dumps({"mode": mode.value}),
            qos=2  # 중복 방지
        )
        return {"success": True, "message": "Mode change request published"}
    
    async def get_sensor_status(self, serial_number: str | None = None) -> dict:
        """Retain 메시지로 상태 조회"""
        # Retain 메시지를 구독하여 마지막 상태 획득
        pass
```

### Topic 네이밍 컨벤션

```
sensors/
├── {serial_number}/
│   ├── data              # [Pub: 센서] 센서 측정 데이터 (QoS 1)
│   ├── status            # [Pub: 서버] 센서 상태 (retain)
│   ├── mode/
│   │   ├── set           # [Pub: 서버] 모드 변경 요청 (QoS 2)
│   │   └── status        # [Pub: 서버] 현재 모드 상태 (retain)
│   ├── error             # [Pub: 서버] 처리 오류
│   └── lwt               # [Pub: 브로커] 연결 끊김 감지 (retain)
└── all/
    ├── broadcast         # [Pub: 서버] 전체 센서 대상 브로드캐스트
    └── command           # [Pub: 서버] 전체 명령

backend/
├── status                # [Pub: 백엔드] 서버 상태 (retain)
├── health                # [Pub: 백엔드] 헬스체크
└── command_result        # [Pub: 백엔드] 명령 실행 결과
```

### 메시지 스키마 표준화

```json
// 센서 데이터 메시지 (기존 HTTP body와 호환)
{
    "message_type": "sensor_data",
    "version": "1.0",
    "timestamp": "2024-01-01T00:00:00Z",
    "payload": {
        "serial_number": "SN001",
        "timestamp": "2024-01-01T00:00:00Z",
        "mode": "NORMAL",
        "temperature": 22.5,
        "humidity": 60.0,
        "pressure": 1013.25,
        "air_quality": 42,
        "location": {"lat": 37.5665, "lng": 126.9780}
    }
}

// 모드 변경 요청
{
    "message_type": "mode_change_request",
    "version": "1.0",
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "uuid-1234",
    "payload": {
        "mode": "EMERGENCY"
    }
}

// 모드 변경 상태 (retain)
{
    "message_type": "mode_status",
    "version": "1.0",
    "timestamp": "2024-01-01T00:00:00Z",
    "payload": {
        "current_mode": "EMERGENCY",
        "requested_mode": "EMERGENCY",
        "request_status": "PENDING|APPLIED|FAILED",
        "requested_at": "2024-01-01T00:00:00Z",
        "applied_at": "2024-01-01T00:00:05Z"
    }
}

// 오류 응답
{
    "message_type": "error",
    "version": "1.0",
    "timestamp": "2024-01-01T00:00:00Z",
    "payload": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid temperature value",
        "field": "temperature",
        "request_id": "uuid-1234"
    }
}
```

---

## 🔄 Dual Mode 지원 전략

### 단계별 마이그레이션 로드맵

```
Phase 1: 병행 운영 (현재)
┌─────────────┐     ┌──────────────┐     ┌──────────┐
│   센서      │────>│   HTTP API   │────>│   DB     │
│  (기존)     │     │  (기존 유지)  │     │          │
└─────────────┘     └──────────────┘     └──────────┘
                           ↑
                    ┌──────┴──────┐
                    │  MQTT Adapter │ (신규, HTTP 포워딩)
                    │  (선택적)     │
                    └─────────────┘

Phase 2: 점진적 전환
┌─────────────┐     ┌──────────────┐
│   센서 A    │────>│   MQTT       │────┐
│  (신규)     │     │   Broker     │    │
└─────────────┘     └──────────────┘    │
                           ↓            │    ┌──────────┐
                    ┌──────────────┐    └───>│   DB     │
                    │ MQTT Adapter │         │          │
                    │  (Consumer)  │────────>└──────────┘
                    └──────────────┘
                           ↑
┌─────────────┐     ┌──────────────┐
│   센서 B    │────>│   HTTP API   │
│  (기존)     │     │  (유지보수)  │
└─────────────┘     └──────────────┘

Phase 3: 완전 전환 (미래)
┌─────────────┐     ┌──────────────┐     ┌──────────┐
│   센서      │────>│   MQTT       │────>│   DB     │
│  (전체)     │     │   Broker     │     │          │
└─────────────┘     └──────────────┘     └──────────┘
                           ↑
                    ┌──────────────┐
                    │  MQTT Adapter │
                    └──────────────┘
```

### Feature Flag 기반 라우팅

```python
from fastapi import Request, HTTPException
from src.config.settings import Settings

class TransportRouter:
    """HTTP/MQTT 라우터"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.http_transport = HttpSensorTransport(...)
        self.mqtt_transport = None
        
        if settings.MQTT_ENABLED:
            self.mqtt_transport = MqttSensorTransport(...)
    
    async def ingest(self, data: dict, mode: IngestMode) -> dict:
        # 센서별 라우팅 (Feature flag 또는 센서 설정 기반)
        serial_number = data.get("serial_number")
        
        if self._use_mqtt_for_sensor(serial_number):
            return await self.mqtt_transport.ingest_reading(data, mode)
        else:
            return await self.http_transport.ingest_reading(data, mode)
    
    def _use_mqtt_for_sensor(self, serial_number: str) -> bool:
        # 설정 기반 또는 DB 조회
        return self.settings.MQTT_ENABLED and serial_number.startswith("SN-MQTT-")
```

---

## 🛡️ 데이터 유실 방지 체크리스트

### 센서 데이터 수집

| 위험 요소 | 방지책 | MQTT 설정 |
|-----------|--------|-----------|
| 네트워크 단절 | Persistent Session | `clean_session=False` |
| 메시지 중복 | Idempotent 처리 | QoS 1 + 중복 필터링 |
| 순서 뒤바뀜 | 타임스탬프 기반 정렬 | QoS 1 + `sensor_timestamp` 검증 |
| 브로커 장애 | 클러스터링/이중화 | 클러스터 설정 |

### 모드 변경 요청

| 위험 요소 | 방지책 | MQTT 설정 |
|-----------|--------|-----------|
| 요청 유실 | QoS 2 사용 | `qos=2` |
| 중복 실행 | Request ID 기반 중복 제거 | QoS 2 + request_id 검증 |
| 상태 불일치 | Retain 메시지 + 주기적 reconcile | `retain=True` |

### 코드 예시: 중복 방지

```python
class DeduplicationMiddleware:
    """MQTT 메시지 중복 방지"""
    
    def __init__(self, redis_client, ttl_seconds: int = 300):
        self.redis = redis_client
        self.ttl = ttl_seconds
    
    async def is_duplicate(self, message_id: str) -> bool:
        """중복 메시지 여부 확인"""
        key = f"mqtt:processed:{message_id}"
        
        # SETNX: 키가 없을 때만 설정 (중복 아님)
        is_new = await self.redis.set(key, "1", nx=True, ex=self.ttl)
        return is_new is None
    
    async def process_with_dedup(self, message: dict, handler):
        """중복 방지 처리 래퍼"""
        msg_id = message.get("message_id") or message.get("timestamp")
        
        if await self.is_duplicate(msg_id):
            print(f"Duplicate message ignored: {msg_id}")
            return {"status": "duplicate_ignored"}
        
        return await handler(message)
```

---

## 📊 MQTT vs HTTP 비교 요약

| 항목 | HTTP | MQTT | 권장 사용처 |
|------|------|------|------------|
| **연결** | Stateless | Persistent | MQTT: 실시간 데이터 스트림 |
| **오버헤드** | 높음 (Header) | 낮음 (2 Byte 고정) | MQTT: 빈번한 소량 데이터 |
| **실시간성** | Polling 필요 | Push 가능 | MQTT: 실시간 알림 |
| **배터리** | 높은 소모 | 낮은 소모 | MQTT: 배터리 기반 IoT |
| **방화벽** | 포트 80/443 | 포트 1883/8883 | HTTP: 기업 환경 |
| **QoS** | 없음 (앱 레벨) | 내장 (3단계) | MQTT: 데이터 유실 방지 |
| **오프라인** | 불가능 | Persistent Session | MQTT: 네트워크 불안정 |
| **디버깅** | 쉬움 (curl) | 어려움 (특수 도구) | HTTP: 개발/테스트 |

---

## 🚀 추천 구현 방향

### 1단계: Adapter 패턴 도입 (즉시)
- `SensorTransport` 인터페이스 정의
- 기존 HTTP 로직을 `HttpSensorTransport`로 이동
- 기존 테스트 유지

### 2단계: MQTT 브로커 도입 (1-2주)
- Mosquitto 또는 EMQX 브로커 설치
- `MqttSensorTransport` 구현
- Paho-mqtt 선택 (유연성 + 표준성)

### 3단계: Dual Mode 운영 (2-4주)
- 센서별 HTTP/MQTT 라우팅
- Feature flag 기반 점진적 전환
- 모니터링 및 알림 체계 구축

### 4단계: 완전 전환 (미래)
- 모든 센서 MQTT 전환
- HTTP API는 레거시 지원 또는 제거

---

## 📚 참고 자료

- [MQTT 3.1.1 Specification](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html)
- [Paho MQTT Python Docs](https://eclipse.dev/paho/index.php?page=clients/python/docs/index.php)
- [FastAPI-MQTT GitHub](https://github.com/sabuhish/fastapi-mqtt)
- [Mosquitto Broker](https://mosquitto.org/)
- [EMQX Broker](https://www.emqx.io/)

---

**작성일**: 2024-01  
**버전**: 1.0  
**담당자**: 개발팀
