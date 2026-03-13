# Database Schema

## Overview

PostgreSQL을 사용하며, Alembic으로 마이그레이션을 관리합니다.

## Entity Relationship

```
readings (1) ←──── (1) sensor_current_status

mode_change_requests (N) → (1) [virtual sensor reference]
```

## Tables

### 1. readings

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

### 2. sensor_current_status

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

### 3. mode_change_requests

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

## Schema Version

- **Current Migration:** `54bb015b4dd8` (Initial Migration)
- **Created:** 2026-03-13
- **Tool:** Alembic

## Configuration

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
