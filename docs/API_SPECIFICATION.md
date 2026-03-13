# API Specification

## Base URL

```
http://localhost:8000
```

## Endpoints Overview

| Method | Endpoint | Description | Tags |
|--------|----------|-------------|------|
| GET | `/health` | 서버 상태 확인 | Health |
| POST | `/api/v1/readings` | 센서 데이터 수집 | Readings |
| GET | `/api/v1/readings` | 측정 데이터 조회 | Readings |
| GET | `/api/v1/sensors/status` | 센서 상태 조회 | Sensors |
| POST | `/api/v1/sensors/{serial_number}/mode` | 센서 모드 변경 | Sensors |

## 1. Health Check

**GET** `/health`

서버 상태를 확인합니다.

**Response:**
```json
{
  "status": "ok",
  "environment": "development",
  "now": "2026-03-13T10:30:00+00:00"
}
```

## 2. Ingest Sensor Readings

**POST** `/api/v1/readings`

센서 데이터를 수집합니다. 단일 레코드 또는 배치(여러 레코드) 전송 가능합니다.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `ingest_mode` | string | No | `atomic` | `atomic`: 전체 성공/실패, `partial`: 부분 허용 |

**Request Body:**

```json
{
  "serial_number": "SENSOR-001",
  "timestamp": "2026-03-13T10:30:00+09:00",
  "mode": "NORMAL",
  "temperature": 23.5,
  "humidity": 55.0,
  "pressure": 1013.25,
  "location": {
    "lat": 37.5665,
    "lng": 126.9780
  },
  "air_quality": 42
}
```

**Request Body Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `serial_number` | string | Yes | 센서 고유 식별자 |
| `timestamp` | string | Yes | ISO8601 형식 타임스탬프 |
| `mode` | string | Yes | `NORMAL` 또는 `EMERGENCY` |
| `temperature` | float | Yes | 온도 (°C) |
| `humidity` | float | Yes | 습도 (%) |
| `pressure` | float | Yes | 기압 (hPa) |
| `location.lat` | float | Yes | 위도 |
| `location.lng` | float | Yes | 경도 |
| `air_quality` | integer | Yes | 공기질 지수 |

**Success Response (200 OK):**

```json
{
  "success": true,
  "ingest_mode": "atomic",
  "accepted_count": 1,
  "rejected_count": 0,
  "errors": []
}
```

**Error Response (Partial):**

```json
{
  "success": false,
  "ingest_mode": "partial",
  "accepted_count": 2,
  "rejected_count": 1,
  "errors": [
    {
      "index": 1,
      "field": "temperature",
      "reason": "Temperature exceeds valid range"
    }
  ]
}
```

## 3. Query Readings

**GET** `/api/v1/readings`

측정 데이터를 조회합니다. 필터링과 페이지네이션을 지원합니다.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `serial_number` | string | No | - | 센서 시리얼 번호 필터 |
| `mode` | string | No | - | `NORMAL` 또는 `EMERGENCY` |
| `sensor_from` | datetime | No | - | 센서 생성 시각 시작 (ISO8601) |
| `sensor_to` | datetime | No | - | 센서 생성 시각 종료 (ISO8601) |
| `received_from` | datetime | No | - | 서버 수신 시각 시작 (ISO8601) |
| `received_to` | datetime | No | - | 서버 수신 시각 종료 (ISO8601) |
| `page` | integer | No | 1 | 페이지 번호 (1부터 시작) |
| `limit` | integer | No | 50 | 페이지당 항목 수 (1-100) |

**Success Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "serial_number": "SENSOR-001",
      "timestamp": "2026-03-13T10:30:00+09:00",
      "raw_timestamp": "2026-03-13T10:30:00+09:00",
      "server_received_at": "2026-03-13T01:30:05+00:00",
      "mode": "NORMAL",
      "metrics": {
        "temperature": 23.5,
        "humidity": 55.0,
        "pressure": 1013.25,
        "air_quality": 42
      },
      "location": {
        "lat": 37.5665,
        "lng": 126.9780
      }
    }
  ],
  "pagination": {
    "total_count": 150,
    "current_page": 1,
    "limit": 50,
    "total_pages": 3,
    "has_next_page": true,
    "has_prev_page": false
  }
}
```

## 4. Get Sensor Status

**GET** `/api/v1/sensors/status`

센서들의 현재 상태(건강 상태, 텔레메트리 상태)를 조회합니다.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serial_number` | string | No | 특정 센서 조회 |
| `health_status` | string | No | `HEALTHY` 또는 `FAULTY` 필터 |

**Success Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "serial_number": "SENSOR-001",
      "last_sensor_timestamp": "2026-03-13T10:30:00+09:00",
      "health_status": "HEALTHY",
      "telemetry_status": "FRESH",
      "last_reading_id": 1,
      "temperature": 23.5,
      "humidity": 55.0,
      "pressure": 1013.25,
      "air_quality": 42
    }
  ]
}
```

**Status Values:**

| Field | Values | Description |
|-------|--------|-------------|
| `health_status` | `HEALTHY`, `FAULTY` | 센서 연결 상태 |
| `telemetry_status` | `FRESH`, `DELAYED`, `CLOCK_SKEW`, `OUT_OF_ORDER` | 데이터 수신 상태 |

## 5. Change Sensor Mode

**POST** `/api/v1/sensors/{serial_number}/mode`

특정 센서의 작동 모드를 변경 요청합니다.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serial_number` | string | Yes | 센서 고유 식별자 |

**Request Body:**

```json
{
  "mode": "EMERGENCY"
}
```

**Request Body Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `NORMAL`, `EMERGENCY`, 또는 `MAINTENANCE` |

**Success Response (200 OK):**

```json
{
  "success": true,
  "sensor_known": true,
  "requested_mode": "EMERGENCY",
  "requested_at": "2026-03-13T01:30:00+00:00",
  "message": "Mode change request recorded. The device will switch to EMERGENCY mode on its next check-in."
}
```

**Unknown Sensor Response (200 OK):**

```json
{
  "success": true,
  "sensor_known": false,
  "requested_mode": "EMERGENCY",
  "requested_at": "2026-03-13T01:30:00+00:00",
  "message": "Mode change request recorded for unknown device. It will take effect when the device first connects."
}
```
