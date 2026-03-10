# 2. Pseudocode

## Content

### 문서 목적

이 문서는 `docs/SPECIFICATION.md`에 정의된 백엔드 요구사항을 실제 구현 흐름으로 옮기기 위한 의사코드 문서다. 목적은 요구사항을 코드 수준 설계 직전 단계까지 분해하여, 어떤 모듈이 어떤 순서로 동작하고 어떤 책임을 가져야 하는지 명확하게 드러내는 것이다.

이 문서는 특정 언어 또는 프레임워크 문법에 묶이지 않으며, 이후 `Architecture` 단계에서 구체적인 기술 스택으로 옮겨가기 위한 공통 로드맵 역할을 한다.

### 설계 원칙

- 수집, 검증, 정규화, 저장, 조회, 상태 판별, 모드 제어를 명확히 분리한다.
- 요청 수준 오류와 레코드 수준 오류를 구분한다.
- 단건 입력도 내부적으로는 배치 처리 흐름에 맞춰 일관되게 다룬다.
- 시간 정규화는 가능한 한 입력 경계에서 수행한다.
- `atomic`과 `partial`의 차이는 배치 제어 흐름에서만 분기되도록 하여 나머지 로직을 최대한 재사용한다.
- 센서 상태 판별은 조회 시 계산만 하는 방식보다 최신 상태 저장 또는 주기적 갱신이 가능한 구조로 설계한다.

### 주요 모듈 개요

```text
API Layer
  - IngestionController
  - QueryController
  - SensorStatusController
  - SensorModeController

Application Layer
  - IngestionService
  - QueryService
  - SensorHealthService
  - SensorModeService

Domain / Utility Layer
  - PayloadValidator
  - TimestampNormalizer
  - ErrorBuilder
  - FilterBuilder

Persistence Layer
  - SensorReadingRepository
  - SensorStatusRepository
  - ModeChangeRequestRepository

Background / Scheduler Layer
  - SensorHealthEvaluationJob
```

### 핵심 함수 목록

```text
handle_ingest_request(payload, ingest_mode)
validate_top_level_payload(payload)
normalize_payload_to_records(payload)
validate_reading(record)
parse_and_normalize_timestamp(raw_timestamp)
enrich_record(record, received_at)
process_batch_atomic(records, received_at)
process_batch_partial(records, received_at)
save_valid_records(records)
update_current_sensor_status(records)
handle_query_request(filters, pagination)
build_query_filters(request_params)
query_readings(filters, pagination)
handle_sensor_status_request(filters)
evaluate_sensor_health(last_mode, last_received_at, now)
refresh_all_sensor_health_statuses(now)
handle_mode_change_request(serial_number, target_mode)
record_mode_change_request(serial_number, target_mode, requested_at)
build_request_error(code, message)
build_record_error(index, field, reason)
build_ingest_response(result)
```

### 수집 API 처리 흐름

#### 목표

- 단건/배치 입력을 모두 수용한다.
- 요청 수준 오류와 레코드 수준 오류를 구분한다.
- `atomic`, `partial` 정책에 따라 저장 전략을 다르게 적용한다.

#### 최상위 흐름

```text
function handle_ingest_request(payload, ingest_mode):
    if ingest_mode is missing:
        ingest_mode = "atomic"

    if ingest_mode not in ["atomic", "partial"]:
        return build_request_error("INVALID_INGEST_MODE", "지원하지 않는 ingest_mode")

    validation_result = validate_top_level_payload(payload)
    if validation_result is failure:
        return build_request_error("INVALID_PAYLOAD", validation_result.message)

    records = normalize_payload_to_records(payload)
    received_at = get_current_server_time()

    if ingest_mode == "atomic":
        return process_batch_atomic(records, received_at)
    else:
        return process_batch_partial(records, received_at)
```

#### 최상위 payload 검증

TODO: 빈 배열을 허용할지 미리 결정하는 것이 좋음
```text
function validate_top_level_payload(payload):
    if payload is malformed JSON:
        return failure("malformed JSON")

    if payload is object:
        return success

    if payload is array:
        return success

    return failure("payload는 object 또는 array여야 함")
```

#### 단건/배치 입력 통일

```text
function normalize_payload_to_records(payload):
    if payload is object:
        return [payload]

    return payload
```

이 통일 과정은 이후 로직이 단건과 배치를 별도 구현하지 않고 동일한 검증/정규화/저장 파이프라인을 재사용할 수 있도록 한다.

### 레코드 검증 및 정규화 흐름

#### 단일 레코드 검증

```text
function validate_reading(record):
    required_fields = [
        "serial_number",
        "timestamp",
        "mode",
        "temperature",
        "humidity",
        "pressure",
        "location",
        "air_quality"
    ]

    for each field in required_fields:
        if field is missing in record:
            return failure(field, "필수 필드 누락")

    if record.mode not in ["NORMAL", "EMERGENCY"]:
        return failure("mode", "지원하지 않는 mode")

    if record.location is not object:
        return failure("location", "location은 객체여야 함")

    if record.location.lat is missing or not numeric:
        return failure("location.lat", "유효하지 않은 위도")

    if record.location.lng is missing or not numeric:
        return failure("location.lng", "유효하지 않은 경도")

    if temperature, humidity, pressure, air_quality are not valid numeric types:
        return failure("metrics", "유효하지 않은 측정값 타입")

    timestamp_result = parse_and_normalize_timestamp(record.timestamp)
    if timestamp_result is failure:
        return failure("timestamp", "유효하지 않은 ISO8601 timestamp")

    return success(timestamp_result.normalized_timestamp)
```

#### timestamp 정규화

```text
function parse_and_normalize_timestamp(raw_timestamp):
    parsed = parse_datetime_with_timezone(raw_timestamp)

    if parsed is invalid:
        return failure

    normalized_timestamp = convert_to_canonical_timezone(parsed)

    return success(normalized_timestamp)
```

#### 저장용 레코드 보강

```text
function enrich_record(record, received_at, normalized_timestamp):
    return {
        serial_number: record.serial_number,
        raw_timestamp: record.timestamp,
        sensor_timestamp: normalized_timestamp,
        server_received_at: received_at,
        mode: record.mode,
        temperature: record.temperature,
        humidity: record.humidity,
        pressure: record.pressure,
        latitude: record.location.lat,
        longitude: record.location.lng,
        air_quality: record.air_quality
    }
```

### 배치 처리 정책 흐름

#### Atomic 처리 흐름

```text
function process_batch_atomic(records, received_at):
    valid_records = []
    errors = []

    for each record with index i in records:
        result = validate_reading(record)

        if result is failure:
            errors.append(build_record_error(i, result.field, result.reason))
        else:
            enriched = enrich_record(record, received_at, result.normalized_timestamp)
            valid_records.append(enriched)

    if errors is not empty:
        return {
            success: false,
            ingest_mode: "atomic",
            accepted_count: 0,
            rejected_count: len(records),
            errors: errors
        }

    begin_transaction()

    try:
        save_valid_records(valid_records)
        update_current_sensor_status(valid_records)
        commit_transaction()
    catch persistence_error:
        rollback_transaction()
        return build_request_error("PERSISTENCE_ERROR", "배치 저장 실패")

    return {
        success: true,
        ingest_mode: "atomic",
        accepted_count: len(valid_records),
        rejected_count: 0,
        errors: []
    }
```

#### Partial 처리 흐름

NOTE: persistence 실패는 전체 오류로 뭉개짐. 
그러면 "일부는 이미 저장됨" 상태가 생길 수 있음.
이미 계약으로 명확히 못박아야 함
QUESTION: 이거 무슨 말이지? 전체 오류로 뭉개지는데, 어떻게 일부는 이미 저장됨 상태가 생긴다는거지?
```text
function process_batch_partial(records, received_at):
    valid_records = []
    errors = []

    for each record with index i in records:
        result = validate_reading(record)

        if result is failure:
            errors.append(build_record_error(i, result.field, result.reason))
            continue

        enriched = enrich_record(record, received_at, result.normalized_timestamp)
        valid_records.append(enriched)

    if valid_records is not empty:
        try:
            save_valid_records(valid_records)
            update_current_sensor_status(valid_records)
        catch persistence_error:
            return build_request_error("PERSISTENCE_ERROR", "부분 저장 처리 중 오류 발생")

    return {
        success: true,
        ingest_mode: "partial",
        accepted_count: len(valid_records),
        rejected_count: len(errors),
        errors: errors
    }
```

#### 배치 정책 차이의 핵심

```text
atomic:
    - 전체 검증 후 하나라도 실패하면 전체 저장 취소
    - 트랜잭션 경계가 명확함
    - 구현과 테스트가 단순함

partial:
    - 유효 레코드는 저장, 실패 레코드는 분리 반환
    - 데이터 유실을 줄이는 운영 친화적 정책
    - 응답 구조와 오류 추적이 더 중요해짐
```

### 저장 처리 흐름

#### 센서 측정값 저장

```text
function save_valid_records(records):
    for each record in records:
        SensorReadingRepository.insert(record)
```

#### 최신 센서 상태 갱신

TODO: 개선 필요 (늦게 도착한 backfill 데이터가 현재 상태를 되돌릴 수 있음) 
```text
function update_current_sensor_status(records):
    grouped = group_records_by_serial_number(records)

    for each serial_number in grouped:
        latest_record = get_latest_record_by_sensor_timestamp(grouped[serial_number])
        health_status = evaluate_sensor_health(
            latest_record.mode,
            latest_record.server_received_at,
            get_current_server_time()
        )

        SensorStatusRepository.upsert({
            serial_number: serial_number,
            last_sensor_timestamp: latest_record.sensor_timestamp,
            last_server_received_at: latest_record.server_received_at,
            last_reported_mode: latest_record.mode,
            health_status: health_status,
            health_evaluated_at: get_current_server_time(),
            last_reading_id: latest_record.id_or_placeholder
        })
```

여기서 `id_or_placeholder`는 실제 DB 저장 후 생성되는 식별자를 어떤 시점에 확보할지에 따라 구현이 달라질 수 있으므로, 아키텍처 단계에서 구체화한다.

### 조회 API 처리 흐름

#### 요청 파라미터 해석
TODO: page/limit 기본값과 최대값을 미리 확정하는 것이 좋음

TODO: query time filter의 timezone 요구사항은 구현 전에 확정하는 것이 좋음
QUESTION: 언제부터 언제까지 볼 것인지 대한 time filter를 말하는건가?
```text
function handle_query_request(request_params):
    filters = build_query_filters(request_params)
    pagination = build_pagination(request_params.page, request_params.limit)
    result = query_readings(filters, pagination)
    return build_query_response(result)
```

#### 필터 구성

```text
function build_query_filters(request_params):
    filters = {}

    if request_params.serial_number exists:
        filters.serial_number = request_params.serial_number

    if request_params.mode exists:
        filters.mode = request_params.mode

    if request_params.sensor_from or request_params.sensor_to exists:
        filters.sensor_timestamp_range = [request_params.sensor_from, request_params.sensor_to]

    if request_params.received_from or request_params.received_to exists:
        filters.server_received_range = [request_params.received_from, request_params.received_to]

    return filters
```

#### 데이터 조회

```text
function query_readings(filters, pagination):
    query = SensorReadingRepository.new_query()

    apply_serial_number_filter(query, filters.serial_number)
    apply_mode_filter(query, filters.mode)
    apply_sensor_timestamp_range(query, filters.sensor_timestamp_range)
    apply_server_received_range(query, filters.server_received_range)

    order_by_sensor_timestamp_desc(query)
    apply_pagination(query, pagination)

    rows = query.execute()
    total_count = query.count_without_pagination()

    return { rows, total_count }
```

#### 응답 매핑

TODO: status 필드명 변경 or /sensors/status에서만 주는 편이 안전 
(구조상 이 값은 "해당 reading 시점의 상태"가 아니라 "센서의 현재 상태"에 가까움)  
=> 아하 서버가 읽을 때랑, 클라이언트에서 이 값을 볼 때랑 상태 차이가 있을 수도 있음
ex. 이 값은 HEALTHY지만 이걸 읽었을 때의 시점은 HEALTHY가 아닐 수도 
```text
function build_query_response(result):
    response_items = []

    // TODO: 조회 응답 매핑에서 row마다 status를 개별 조회하면 N+1 문제 생김.
    // batch fetch나 join 전략을 넣는 게 architecture에 한 줄 더 넣는게 좋음
    for each row in result.rows:
        latest_status = SensorStatusRepository.find_by_serial_number(row.serial_number)

        response_items.append({
            id: row.id,
            serial_number: row.serial_number,
            timestamp: row.sensor_timestamp,
            server_received_at: row.server_received_at,
            mode: row.mode,
            metrics: {
                temperature: row.temperature,
                humidity: row.humidity,
                pressure: row.pressure,
                air_quality: row.air_quality
            },
            location: {
                lat: row.latitude,
                lng: row.longitude
            },
            status: latest_status.health_status
        })

    return build_paginated_response(response_items, result.total_count)
```

### 센서 상태 API 처리 흐름

```text
function handle_sensor_status_request(filters):
    query = SensorStatusRepository.new_query()

    if filters.serial_number exists:
        query.where_serial_number(filters.serial_number)

    if filters.health_status exists:
        query.where_health_status(filters.health_status)

    rows = query.execute()

    return {
        success: true,
        data: rows
    }
```

### 센서 건강 상태 평가 흐름

#### 단일 센서 상태 계산

NOTE: 지연 전송/재전송 패킷이 들어오면 실제 센서 freshness와 어긋날 수 있음.
server_received_at 기반으로 갈지, sensor_timestamp 기반으로 갈지,
혹은 둘 다 보되 health는 무엇을 따를지 명시가 필요함
QUESTION: 지연 전송/재전송 패킷을 대비하기 위해 실제 sensor_timestamp가 아니라, server_received_at으로 보는 거 아닌가?
위에서 지적한 문제가 실제 문제인지 궁금하네..
```text
function evaluate_sensor_health(last_mode, last_server_received_at, now):
    if last_mode == "NORMAL":
        threshold = 12 minutes
    else if last_mode == "EMERGENCY":
        threshold = 30 seconds
    else:
        return "UNKNOWN"

    elapsed = now - last_server_received_at

    if elapsed > threshold:
        return "FAULTY"

    return "HEALTHY"
```

#### 주기적 상태 재평가

```text
function refresh_all_sensor_health_statuses(now):
    statuses = SensorStatusRepository.find_all()

    for each status in statuses:
        recalculated = evaluate_sensor_health(
            status.last_reported_mode,
            status.last_server_received_at,
            now
        )

        SensorStatusRepository.update_health_status(
            serial_number = status.serial_number,
            health_status = recalculated,
            health_evaluated_at = now
        )
```

#### 스케줄러 진입점

```text
function SensorHealthEvaluationJob.run():
    now = get_current_server_time()
    refresh_all_sensor_health_statuses(now)
```

### 모드 제어 API 처리 흐름

```text
function handle_mode_change_request(serial_number, target_mode):
    if target_mode not in ["NORMAL", "EMERGENCY"]:
        return build_request_error("INVALID_MODE", "지원하지 않는 target_mode")

    requested_at = get_current_server_time()
    result = record_mode_change_request(serial_number, target_mode, requested_at)

    return {
        success: true,
        serial_number: serial_number,
        requested_mode: target_mode,
        requested_at: requested_at
    }
```

```text
function record_mode_change_request(serial_number, target_mode, requested_at):
    return ModeChangeRequestRepository.insert({
        serial_number: serial_number,
        requested_mode: target_mode,
        requested_at: requested_at,
        request_status: "REQUESTED"
    })
```

이 흐름은 서버의 요청 의도를 저장하는 책임에 집중하며, 실제 센서가 모드를 바꿨는지는 이후 텔레메트리로 확인한다.

### 오류 처리 흐름

#### 요청 수준 오류 생성

```text
function build_request_error(code, message):
    return {
        success: false,
        error: {
            code: code,
            message: message
        }
    }
```

#### 레코드 수준 오류 생성

```text
function build_record_error(index, field, reason):
    return {
        index: index,
        field: field,
        reason: reason
    }
```

#### 오류 처리 분류 원칙

```text
request-level error:
    - malformed JSON
    - invalid top-level payload
    - unsupported ingest_mode
    - authorization failure (if implemented later)

record-level error:
    - missing field
    - invalid enum value
    - invalid timestamp
    - invalid location structure
    - invalid numeric field type
```

### 테스트 관점 의사코드 체크포인트

#### 수집 관련 테스트

```text
test_single_object_payload_success()
test_array_payload_success()
test_invalid_top_level_payload_failure()
test_invalid_ingest_mode_failure()
```

#### 검증 및 시간 처리 테스트

```text
test_missing_required_field_failure()
test_invalid_mode_failure()
test_invalid_timestamp_failure()
test_utc_timestamp_normalization()
test_kst_timestamp_normalization()
test_mixed_timezone_batch_normalization()
```

#### 배치 정책 테스트

```text
test_atomic_batch_all_success()
test_atomic_batch_one_invalid_all_fail()
test_partial_batch_mixed_success_and_failure()
test_partial_batch_all_invalid()
```

#### 상태 판별 테스트

```text
test_normal_mode_health_within_threshold()
test_normal_mode_fault_after_12_minutes()
test_emergency_mode_health_within_threshold()
test_emergency_mode_fault_after_30_seconds()
```

#### 조회 및 모드 제어 테스트

```text
test_query_by_serial_number()
test_query_by_mode()
test_query_by_sensor_time_range()
test_query_by_server_received_range()
test_mode_change_request_recorded()
```

### 구현 시 보류 가능한 세부사항

다음 항목은 pseudocode 단계에서 의도적으로 추상화하고, 이후 architecture 또는 implementation 단계에서 구체화한다.

- 실제 트랜잭션 처리 방식
- DB generated id를 상태 저장과 어떻게 연결할지
- pagination 기본값과 최대값
- 인증/인가 방식
- health status enum에 `UNKNOWN` 외의 중간 상태를 둘지 여부
- 부분 성공 응답의 HTTP status code 정책
- idempotency key 지원 여부

## Reflection

이 의사코드는 `Specification`의 내용을 구현 가능한 흐름으로 옮기되, 가능한 한 책임 경계를 분명히 하도록 구성했다. 가장 중요한 결정은 수집 흐름을 `검증 -> 정규화 -> 정책 분기 -> 저장`으로 나눈 것이다. 이렇게 하면 입력 형태가 단건이든 배치든, 시간 정보가 UTC든 KST든, 동일한 파이프라인 안에서 처리할 수 있다.

또한 `atomic`과 `partial` 정책의 차이를 배치 제어 흐름으로 한정했다. 이는 나머지 검증 및 정규화 로직을 중복 없이 재사용하게 해주며, 구현 복잡도를 불필요하게 늘리지 않는다. 기본값을 `atomic`으로 둔 이유도 여기서 드러난다. 처음 구현 시에는 롤백 경계와 테스트 시나리오가 더 단순해지고, 이후 필요하면 `partial`을 확장할 수 있다.

시간 정규화를 입력 경계에서 수행하는 것도 중요한 선택이다. 이를 뒤로 미루면 저장 구조, 조회 필터, 상태 판별 모두가 복잡해지고 버그 가능성이 커진다. 따라서 pseudocode는 timestamp를 가능한 한 초기에 canonical 형태로 변환하는 방향을 강하게 유지한다.

센서 건강 상태 평가는 단순 조회 시 계산만으로도 구현할 수 있지만, 본 문서는 별도의 상태 저장소와 주기적 재평가 흐름을 포함했다. 이는 프론트엔드가 건강 상태를 쉽게 소비할 수 있게 해주고, 운영자 입장에서도 현재 상태를 빠르게 확인할 수 있게 한다. 메시지 큐 없이도 이 정도 수준의 상태 관리와 점검은 충분히 단순한 구조 안에서 구현 가능하다.

마지막으로, 이 문서는 실제 코드가 아니라 의사코드이므로 세부적인 트랜잭션 전략, 인증 방식, 저장소 구현 세부사항은 의도적으로 열어두었다. 그 대신 어떤 함수가 어떤 책임을 가져야 하는지와 어떤 순서로 흐름이 이어져야 하는지를 명확히 해두어, 다음 단계인 `Architecture`에서 기술 선택과 구조 설계가 흔들리지 않도록 한다.
