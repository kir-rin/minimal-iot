# IoT 환경 모니터링 백엔드

Python 기반 IoT 환경 모니터링 시스템 백엔드

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (로컬 개발 시에만 필요)
- UV (선택사항, 로컬 개발 시)

## Quick Start

```bash
# 처음 실행할 때 (한 번에 모든 설정 + 실행 + 테스트 데이터 + 브라우저 자동 열기)
make init

# 이후에는 (실행 + 브라우저 자동 열기)
make dev-docker
```

**`make init`이 자동으로 수행하는 것:**
1. ✅ 백엔드 의존성 설치
2. ✅ Docker 전체 스택 실행 (DB + Backend + Frontend)
3. ✅ 데이터베이스 마이그레이션
4. ✅ 🌱 **테스트 데이터 자동 생성**
5. ✅ 브라우저 자동 열기

**자동으로 열리는 URL:**
- 🌐 **Frontend:** http://localhost
- 📖 **API Docs:** http://localhost:8000/docs (자동으로 브라우저에 열림)

**수동 접속:**
- Backend API: http://localhost:8000

## Makefile 명령어

**🚀 Quick Start:**
- `make init` - 초기 설정 + 실행 + 브라우저 자동 열기 ⭐ 처음 실행 시
- `make dev-docker` - 전체 스택 Docker 실행 + 브라우저 자동 열기

**의존성 설치:**
- `make install-backend` - 백엔드 의존성 설치
- `make install-backend-dev` - 백엔드 개발 의존성 포함 설치
- `make install-frontend` - 프론트엔드 의존성 설치

**개발 서버:**
- `make dev-backend` - 백엔드 로컬 개발 서버 (hot reload)
- `make dev-frontend` - 프론트엔드 개발 서버
- `make dev-all` - 백엔드 + 프론트엔드 동시 실행

**데이터베이스:**
- `make db-up` - PostgreSQL Docker 실행
- `make db-down` - DB 중지 및 볼륨 삭제
- `make migrate` - Alembic 마이그레이션 실행 (Docker 안에서)
- `make migrate-create message="..."` - 새 마이그레이션 생성

**테스트/빌드:**
- `make test` - 전체 테스트 실행
- `make test-backend` - 백엔드 테스트만 실행
- `make lint-backend` - 백엔드 린트 검사
- `make build-backend` - 백엔드 Docker 이미지 빌드
- `make build-frontend` - 프론트엔드 빌드
- `make build-all` - 전체 Docker 빌드
- `make clean` - 캐시, 컨테이너, 빌드 파일 정리

**유틸리티:**
- `make logs-backend` - 백엔드 로그 확인
- `make shell-backend` - 백엔드 컨테이너 쉘 접속
- `make logs-frontend` - 프론트엔드 로그 확인
- `make shell-frontend` - 프론트엔드 컨테이너 쉘 접속

**전체 명령어 보기:**
```bash
make help
```

## 프로젝트 구조

```
.
├── src/                 # 소스 코드
├── tests/              # 테스트 코드
├── migrations/         # 데이터베이스 마이그레이션
├── scripts/            # 유틸리티 스크립트
├── frontend/           # 프론트엔드 (Vite + React + TypeScript)
├── pyproject.toml      # 프로젝트 설정 (UV 사용)
├── docker-compose.yml  # Docker Compose 설정
├── Dockerfile.backend  # 백엔드 Docker 이미지
├── Dockerfile.frontend # 프론트엔드 Docker 이미지
└── Makefile           # 개발 편의성 명령어
```

## UV 설치 (로컬 개발 시)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 주요 기술 스택

**백엔드:**
- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Alembic (마이그레이션)
- APScheduler

**프론트엔드:**
- Vite
- React 19
- TypeScript
- Tailwind CSS
- Recharts (차트)

**인프라:**
- Docker & Docker Compose
- UV (패키지 매니저)

---

## API Specification

### Base URL

```
http://localhost:8000
```

### Endpoints Overview

| Method | Endpoint | Description | Tags |
|--------|----------|-------------|------|
| GET | `/health` | 서버 상태 확인 | Health |
| POST | `/api/v1/readings` | 센서 데이터 수집 | Readings |
| GET | `/api/v1/readings` | 측정 데이터 조회 | Readings |
| GET | `/api/v1/sensors/status` | 센서 상태 조회 | Sensors |
| POST | `/api/v1/sensors/{serial_number}/mode` | 센서 모드 변경 | Sensors |

### 1. Health Check

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

### 2. Ingest Sensor Readings

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

### 3. Query Readings

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

### 4. Get Sensor Status

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

### 5. Change Sensor Mode

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

---

## Database Schema

### Overview

PostgreSQL을 사용하며, Alembic으로 마이그레이션을 관리합니다.

### Entity Relationship

```
readings (1) ←──── (1) sensor_current_status

mode_change_requests (N) → (1) [virtual sensor reference]
```

### Tables

#### 1. readings

센서 측정 데이터를 저장합니다.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, Auto Increment | 레코드 ID |
| `serial_number` | VARCHAR(255) | NOT NULL, Index | 센서 고유 식별자 |
| `raw_timestamp` | VARCHAR(50) | NOT NULL | 원본 타임스탬프 문자열 |
| `sensor_timestamp` | TIMESTAMPTZ | NOT NULL, Index | 정규화된 센서 기준 시각 |
| `server_received_at` | TIMESTAMPTZ | NOT NULL, Index | 서버 수신 시각 |
| `mode` | VARCHAR(50) | NOT NULL, Index | 작동 모드 (`NORMAL`/`EMERGENCY`) |
| `temperature` | FLOAT | NOT NULL | 온도 (°C) |
| `humidity` | FLOAT | NOT NULL | 습도 (%) |
| `pressure` | FLOAT | NOT NULL | 기압 (hPa) |
| `latitude` | FLOAT | NOT NULL | 위도 |
| `longitude` | FLOAT | NOT NULL | 경도 |
| `air_quality` | INTEGER | NOT NULL | 공기질 지수 |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | 레코드 생성 시각 |

**Indexes:**
- `ix_readings_serial_number` on `serial_number`
- `ix_readings_sensor_timestamp` on `sensor_timestamp`
- `ix_readings_server_received_at` on `server_received_at`
- `ix_readings_mode` on `mode`

#### 2. sensor_current_status

센서별 최신 상태를 저장합니다. 각 센서당 1개 레코드만 유지됩니다 (UPSERT).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `serial_number` | VARCHAR(255) | PK | 센서 고유 식별자 |
| `last_sensor_timestamp` | TIMESTAMPTZ | NOT NULL | 마지막 센서 시각 |
| `last_server_received_at` | TIMESTAMPTZ | NOT NULL | 마지막 서버 수신 시각 |
| `last_reported_mode` | VARCHAR(50) | NOT NULL | 마지막 보고된 모드 |
| `health_status` | VARCHAR(50) | NOT NULL, DEFAULT 'HEALTHY' | 건강 상태 |
| `telemetry_status` | VARCHAR(50) | NOT NULL, DEFAULT 'FRESH' | 텔레메트리 상태 |
| `health_evaluated_at` | TIMESTAMPTZ | NOT NULL | 건강 상태 평가 시각 |
| `last_reading_id` | INTEGER | FK → readings.id, NOT NULL | 마지막 측정값 ID 참조 |

**Foreign Keys:**
- `last_reading_id` → `readings.id`

**Status Values:**
- `health_status`: `HEALTHY`, `FAULTY`, `UNKNOWN`
- `telemetry_status`: `FRESH`, `DELAYED`, `CLOCK_SKEW`, `OUT_OF_ORDER`

#### 3. mode_change_requests

센서 모드 변경 요청을 저장합니다.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, Auto Increment | 요청 ID |
| `serial_number` | VARCHAR(255) | NOT NULL, Index | 대상 센서 식별자 |
| `requested_mode` | VARCHAR(50) | NOT NULL | 요청된 모드 |
| `requested_at` | TIMESTAMPTZ | NOT NULL | 요청 시각 |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | 레코드 생성 시각 |

**Indexes:**
- `ix_mode_change_requests_serial_number` on `serial_number`

### Schema Version

- **Current Migration:** `54bb015b4dd8` (Initial Migration)
- **Created:** 2026-03-13
- **Tool:** Alembic

### Configuration

**Health Evaluation Thresholds:**

| Mode | Threshold | Description |
|------|-----------|-------------|
| NORMAL | 720s (12min) | 마지막 데이터 수신 후 HEALTHY 유지 시간 |
| EMERGENCY | 30s | 마지막 데이터 수신 후 HEALTHY 유지 시간 |
| DELAYED | 120s (2min) | 데이터 지연 판단 기준 |
| CLOCK_SKEW | 30s | 시계 차이 판단 기준 |

**Scheduler:**
- Health 평가 주기: 10초
- Automatic health evaluation enabled by default
