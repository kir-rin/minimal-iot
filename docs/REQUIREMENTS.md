# [채용 과제] IoT 환경 데이터 모니터링 시스템 구축

본 과제는 IoT 센서로부터 수집되는 환경 데이터를 효율적으로 처리하고, 이를 사용자에게 명확하게 시각화하는 능력을 평가하기 위함입니다. 지원하시는 직군(백엔드/프론트엔드)에 해당하는 요구사항을 확인하여 구현해 주시기 바랍니다.

## 1. 공통 시나리오 및 데이터 사양

### 시스템 개요

특정 구역의 환경 정보를 수집하는 IoT 센서들이 있으며, 이 센서들은 주기적으로 서버에 데이터를 전송합니다. 시스템은 수집된 데이터를 저장하고, 센서의 상태(정상/고장)를 판별하며, 센서의 작동 모드를 제어할 수 있어야 합니다.

### 데이터 모델 (Sensor Data Payload)

센서는 HTTP RestAPI를 통해 데이터를 전송합니다. 설정에 따라 **단일 객체** 또는 **배열(Array)** 형태로 전송될 수 있습니다.

| **필드명** | **타입** | **설명** |
| --- | --- | --- |
| `serial_number` | String | 센서 고유 식별 번호 |
| **`timestamp`** | **String** | 센서 기준 데이터 생성 시간 (ISO8601).
**※ 주의: 센서 설정에 따라 UTC 혹은 KST(+09:00) 포맷으로 혼재되어 전송됨** |
| `mode` | Enum | 작동 모드 (`NORMAL`, `EMERGENCY`) |
| `temperature` | Float | 온도 |
| `humidity` | Float | 습도 |
| `pressure` | Float | 기압 |
| `location` | Object | 위도(`lat`), 경도(`lng`) 정보를 포함한 객체 |
| `air_quality` | Integer | 공기질 지수 |

**메시지 예시 : 단일건 전송상황**

```json
{
  "serial_number": "SENSOR-A-1004",
  "timestamp": "2024-05-23T08:30:00Z", 
  "mode": "NORMAL",
  "temperature": 24.5,
  "humidity": 50.2,
  "pressure": 1013.2,
  "location": {
    "lat": 37.5665,
    "lng": 126.9780
  },
  "air_quality": 42
}
```

**메시지 예시 : 복수 건 전송상황**

```json
[
  {
    "serial_number": "SENSOR-B-2024",
    "timestamp": "2024-05-23T17:40:00+09:00",
    "mode": "EMERGENCY",
    "temperature": 28.1,
    "humidity": 65.4,
    "pressure": 1009.5,
    "location": {
      "lat": 35.1796,
      "lng": 129.0756
    },
    "air_quality": 88
  },
  {
    "serial_number": "SENSOR-B-2024",
    "timestamp": "2024-05-23T17:40:10+09:00",
    "mode": "EMERGENCY",
    "temperature": 28.2,
    "humidity": 65.5,
    "pressure": 1009.4,
    "location": {
      "lat": 35.1796,
      "lng": 129.0756
    },
    "air_quality": 90
  },
  {
    "serial_number": "SENSOR-B-2024",
    "timestamp": "2024-05-23T08:40:20Z",
    "mode": "EMERGENCY",
    "temperature": 28.4,
    "humidity": 65.7,
    "pressure": 1009.3,
    "location": {
      "lat": 35.1796,
      "lng": 129.0756
    },
    "air_quality": 95
  }
]
```

### 센서 작동 규칙

1. **전송 주기:** 일반 모드(`NORMAL`)는 10분, 긴급 모드(`EMERGENCY`)는 10초 주기로 데이터를 전송합니다.
2. **모드 전환:** 센서는 자체 로직 혹은 서버의 명령(외부 제어)에 의해 모드가 변경됩니다.
3. **데이터 누락(고장) 판단:** 정해진 주기 내에 데이터가 도착하지 않으면 시스템은 해당 센서의 상태에 이상이 있다고 판단해야 합니다.

---

## 2. [백엔드] 과제 요구사항

### 주요 구현 목표

1. **데이터 수집 API:** 단일 및 배치(Batch) 전송을 모두 처리해야 합니다.
2. **시간 정규화 및 적재:** **서로 다른 타임존(UTC/KST)으로 들어오는 `timestamp`를 서버에서 일관된 기준으로 정규화**하여 저장해야 합니다.
3. **조회 API:** 시리얼 넘버, 작동 모드, 기간별(서버 수집 시간 및 센서 생성 시간 기준) 필터링을 지원합니다.
4. **상태 검증 로직:** 방법 무관하게 데이터 누락 여부를 판단합니다. (메시지 큐 사용 제한)

---

## 3. [프론트엔드] 과제 요구사항

### 주요 구현 목표

1. **데이터 시각화 및 필터링:** 수집된 데이터를 리스트 또는 차트로 구성합니다. (시리얼 넘버, 시간 범위, 모드 필터 포함)
2. **시간 표시 최적화:** 서버에서 전달받은 시계열 데이터를 **사용자의 브라우저 환경에 맞춰 일관된 시간대로 출력**해야 합니다.
3. **상태 모니터링 및 제어:** 센서별 정상/고장 상태 시각화 및 모드 변경 UI를 구현합니다.

---

## 4. 공통 제출 가이드 및 기술 제약

- **환경 제한:** 기본적인 웹 서비스 환경 이상의 구조(MQTT 같은 메시지 큐 등) 사용은 제한합니다.
- **제출물:** GitHub 저장소 링크 및 프로젝트 실행 방법이 적힌 `README.md`. 실행시 Docker로 이미지를 만들어서 실행할수 있음 좋습니다.
- **설계 문서:** (백엔드) API 명세 및 DB 스키마 / (프론트엔드) 상태 관리 및 컴포넌트 설계안.

---

## 💡 [Tip] 지원자를 위한 힌트

- 이 과제는 데이터의 유실 없는 수집, **타임존 혼재 상황에서의 시간 데이터 처리**, 그리고 배치 데이터 처리에 대한 고민을 평가합니다.
- **본 과제 명세에 명확히 적혀있지 않더라도, 지원자 본인이 생각하기에 시스템 운영상 이런 기능이 꼭 있어야 한다고 판단된다면 자유롭게 추가해 주세요.** 추가한 기능과 그 이유를 설계 문서나 README에 설명해 주신다면 좋은 평가 요소가 됩니다. (예: 데이터 유효성 검증, 간단한 통계 기능, 에러 로그 기록, 타임존 처리 로직에 대한 설명 등)

---

**DB 내 예제 데이터 샘플**

```json
id,serial_number,timestamp,created_at,mode,temperature,humidity,pressure,latitude,longitude,air_quality
1,SN-NORMAL-01,2024-05-23T09:00:00Z,2024-05-23T09:00:05Z,NORMAL,24.7,59.5,1012.7,37.5665,126.9780,59
2,SN-NORMAL-01,2024-05-23T09:10:00Z,2024-05-23T09:10:08Z,NORMAL,21.2,46.5,1011.7,37.5665,126.9780,52
3,SN-NORMAL-01,2024-05-23T09:20:00Z,2024-05-23T09:20:12Z,NORMAL,21.9,52.4,1014.9,37.5665,126.9780,52

```

**조회 API의 예시(프론트엔드 개발자 위한 샘플로 백엔드 개발자가 굳이 이 명세를 따를 필요는 없습니다.)**

```json
{
  "success": true,
  "data": [
    {
      "id": 100,
      "serial_number": "SN-NORMAL-01",
      "timestamp": "2024-05-23T09:00:00Z",
      "server_received_at": "2024-05-23T09:00:05Z",
      "mode": "NORMAL",
      "metrics": {
        "temperature": 24.7,
        "humidity": 59.5,
        "pressure": 1012.7,
        "air_quality": 59
      },
      "location": {
        "lat": 37.5665,
        "lng": 126.978
      },
      "status": "HEALTHY"
    },
    {
      "id": 99,
      "serial_number": "SN-NORMAL-01",
      "timestamp": "2024-05-23T09:10:00Z",
      "server_received_at": "2024-05-23T09:10:08Z",
      "mode": "NORMAL",
      "metrics": {
        "temperature": 21.2,
        "humidity": 46.5,
        "pressure": 1011.7,
        "air_quality": 52
      },
      "location": {
        "lat": 37.5665,
        "lng": 126.978
      },
      "status": "HEALTHY"
    }
    /* ... 8개의 데이터 객체 추가 ... */
  ],
  "pagination": {
    "total_count": 100,
    "current_page": 1,
    "limit": 10,
    "total_pages": 10,
    "has_next_page": true,
    "has_prev_page": false
  }
}
```
