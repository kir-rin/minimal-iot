# TIMEZONE_NORMALIZATION Scenario

## 목적

이 문서는 서로 다른 타임존(UTC, KST)으로 들어오는 센서 `timestamp`를 서버가 어떻게 일관된 기준 시각으로 처리하는지 설명한다.
핵심은 센서마다 표현 방식이 달라도, 시스템 내부에서는 같은 기준으로 저장하고 비교해야 조회, 정렬, 상태 판별이 흔들리지 않는다는 점이다.
서술 안에서는 `docs/PSEUDOCODE.md`의 함수 이름을 그대로 언급해 실제 처리 흐름과 연결한다.

## 시나리오. 다른 시간 표현이 같은 사건을 가리킬 때

오전 11시, 두 센서가 거의 같은 시점의 환경 데이터를 서버로 보낸다.
하나는 `2024-05-23T08:30:00Z`처럼 UTC 기준으로 시간을 보내고, 다른 하나는 `2024-05-23T17:30:00+09:00`처럼 KST 기준으로 시간을 보낸다.
표현은 다르지만, 실제로는 같은 순간을 가리키는 데이터다.

운영자 입장에서는 이 차이가 중요하지 않다.
운영자가 보고 싶은 것은 "실제로 언제 측정된 데이터인가"이지, 센서가 어떤 타임존 문자열을 선택했는가는 아니다.
그래서 시스템은 입력 시점부터 시간 표현의 차이를 흡수해야 한다.

서버는 먼저 `handle_ingest_request(payload, ingest_mode)`로 요청을 받는다.
요청이 단건이든 배열이든, `validate_top_level_payload(payload)`가 최상위 구조를 확인하고 `normalize_payload_to_records(payload)`가 내부 처리 단위를 통일한다.
이 단계까지는 시간값의 의미를 아직 판단하지 않고, 일단 모든 레코드를 같은 파이프라인 위에 올려놓는다.

그 다음 각 레코드는 `validate_reading(record)` 검증을 거친다.
이 함수는 `timestamp`가 단순한 문자열인지 보는 데서 멈추지 않고, timezone 정보가 포함된 유효한 ISO8601 형식인지까지 확인한다.
즉, 시간 문자열은 존재만 하면 되는 값이 아니라, 서버가 해석 가능한 기준 시각이어야 한다.

검증을 통과한 시간값은 `parse_and_normalize_timestamp(raw_timestamp)`로 넘어간다.
여기서 서버는 UTC 문자열이든 KST 문자열이든 실제 시각으로 파싱한 뒤, 내부의 단일 canonical 표현으로 변환한다.
결과적으로 `2024-05-23T08:30:00Z`와 `2024-05-23T17:30:00+09:00`는 서로 다른 문자열이 아니라 같은 시점을 가리키는 동일한 내부 시간값으로 정리된다.

이후 `enrich_record(record, received_at, normalized_timestamp)`가 저장용 데이터를 만든다.
이 단계에서 시스템은 세 가지 시간 정보를 분리해서 보존한다.
센서가 원래 보낸 `raw_timestamp`, 비교와 정렬에 사용할 `sensor_timestamp`, 그리고 서버가 실제로 수신한 시각인 `server_received_at`이다.
이 분리가 있기 때문에 운영자는 나중에 원본 표현을 추적할 수도 있고, 시스템은 정규화된 기준 시간으로 안전하게 동작할 수도 있다.

저장 단계에 들어가면 `save_valid_records(records)`가 정규화된 레코드를 영속화한다.
이제 데이터베이스 안에서는 서로 다른 타임존으로 들어온 데이터도 하나의 기준 시간 위에서 정렬되고 비교된다.
같은 시점을 가리키는 두 레코드는 같은 시간축 위에 놓이고, 이후 로직은 문자열 차이 때문에 흔들리지 않는다.

이 안정성은 조회 시 더 분명하게 드러난다.
운영자가 특정 시간 구간의 데이터를 조회하면 서버는 `handle_query_request(request_params)`를 통해 요청을 받고,
`build_query_filters(request_params)`에서 `sensor_from`, `sensor_to`, `received_from`, `received_to` 같은 필터를 같은 기준 시간으로 해석한다.
그 다음 `query_readings(filters, pagination)`가 정규화된 `sensor_timestamp` 기준으로 데이터를 찾기 때문에, UTC로 들어온 데이터와 KST로 들어온 데이터가 하나의 일관된 시계열로 반환된다.

센서 상태 판별에서도 이 원칙은 중요하다.
건강 상태 자체는 `evaluate_sensor_health(last_mode, last_server_received_at, now)`처럼 서버 수신 시각을 기준으로 판단하더라도,
어떤 데이터가 더 최신인지, 어떤 측정값이 먼저 발생했는지는 결국 정규화된 센서 시각 위에서 판단해야 한다.
그래야 mixed timezone 환경에서도 out-of-order 판단이나 이력 정렬이 안정적으로 유지된다.

운영자는 화면에서 그저 "시간순으로 잘 정렬된 데이터"를 보게 되지만,
그 뒤에서는 `validate_reading`, `parse_and_normalize_timestamp`, `enrich_record`, `build_query_filters`, `query_readings` 같은 함수들이
센서마다 다른 시간 표현을 하나의 공통 언어로 번역하고 있다.

## 정리

이 시나리오는 타임존 혼재 상황의 핵심 문제가 문자열 형식의 차이가 아니라, 서로 다른 표현을 하나의 실제 시각으로 합쳐야 한다는 데 있음을 보여준다.
시스템은 `handle_ingest_request`에서 수집을 시작하고, `validate_reading`으로 시간값의 유효성을 검증하며, `parse_and_normalize_timestamp`로 내부 기준 시각을 만든다.
그리고 `enrich_record`와 `save_valid_records`를 통해 원본 시간과 정규화된 시간을 함께 보존하고, `build_query_filters`와 `query_readings`를 통해 일관된 시계열 조회를 가능하게 만든다.

즉, 이 시스템의 시간 정규화는 단순한 파싱 기능이 아니라,
mixed timezone 환경에서도 저장, 정렬, 조회, 상태 판단이 모두 같은 시간 축 위에서 동작하도록 만드는 핵심 운영 원칙이다.
