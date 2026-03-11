# NORMAL Scenario

## 목적

이 문서는 엣지 케이스를 제외하고, 센서 데이터가 정상적으로 수집되고 조회되며 모드 변경 요청이 반영되는 일반적인 흐름을 스토리처럼 설명한다.
서술 안에서는 `docs/PSEUDOCODE.md`에 정의된 핵심 함수 이름을 그대로 언급해, 실제 구현 흐름과 문서의 연결점을 분명히 한다.

## 시나리오 1. 센서가 평소처럼 데이터를 보낸다

아침 9시, `SN-NORMAL-01` 센서는 평소와 다름없이 `NORMAL` 모드로 동작하고 있다.
이 센서는 10분 주기로 환경 정보를 측정하고, 서버에 JSON 객체 하나를 전송한다.

서버는 먼저 `handle_ingest_request(payload, ingest_mode)`로 요청을 받는다.
이번 요청에는 별도의 정책 지정이 없으므로 기본값인 `atomic`이 적용된다.

가장 먼저 `validate_top_level_payload(payload)`가 실행된다.
payload는 단일 객체이며 형식도 올바르기 때문에 요청 수준 오류는 발생하지 않는다.
이후 `normalize_payload_to_records(payload)`가 단건 객체를 내부적으로 배열 1건으로 변환한다.
겉으로는 단건 요청이지만, 시스템은 이후 흐름을 배치와 동일한 방식으로 다룬다.

이제 레코드 검증 단계로 넘어간다.
`validate_reading(record)`는 `serial_number`, `timestamp`, `mode`, `temperature`, `humidity`, `pressure`, `location`, `air_quality`가 모두 존재하는지 확인한다.
모든 값은 정상이며, `mode`도 `NORMAL`이므로 문제없이 통과한다.

시간 정보는 `parse_and_normalize_timestamp(raw_timestamp)`에서 정리된다.
센서가 보낸 시각이 UTC이든 KST이든 상관없이, 서버는 이를 내부 기준 시각으로 변환한다.
이 덕분에 이후 저장, 조회, 정렬, 상태 계산이 모두 같은 시간 기준 위에서 동작할 수 있다.

정규화가 끝난 뒤 `enrich_record(record, received_at, normalized_timestamp)`가 저장용 데이터를 만든다.
이 단계에서 원본 `timestamp`, 정규화된 `sensor_timestamp`, 그리고 서버가 실제로 받은 시각인 `server_received_at`이 함께 묶인다.

이번 요청은 정상 단건이므로 `process_batch_atomic(records, received_at)` 안에서도 실패 없이 흘러간다.
`save_valid_records(records)`가 측정값을 저장하고, 이어서 `update_current_sensor_status(records)`가 이 센서의 최신 상태를 갱신한다.
센서가 방금 데이터를 보냈기 때문에 상태 계산에는 `evaluate_sensor_health(last_mode, last_received_at, now)`가 사용되고, 결과는 자연스럽게 `HEALTHY`가 된다.

클라이언트는 최종적으로 성공 응답을 받는다.
운영자 입장에서는 "센서가 정상적으로 값을 보냈고, 서버도 그것을 정상적으로 기록했다"는 아주 평범한 하루의 한 장면이다.

## 시나리오 2. 운영자가 최근 데이터를 조회한다

잠시 뒤 운영자는 대시보드에서 `SN-NORMAL-01`의 최근 측정 이력을 확인하고 싶어진다.
프론트엔드는 센서 번호와 시간 범위를 담아 조회 API를 호출한다.

서버는 `handle_query_request(request_params)`로 요청을 처리한다.
먼저 `build_query_filters(request_params)`가 `serial_number`, `sensor_from`, `sensor_to` 같은 조건을 내부 필터 구조로 바꾼다.
그 다음 `query_readings(filters, pagination)`가 저장된 이력 데이터에서 조건에 맞는 레코드를 찾는다.

조회 결과는 최신 측정값이 먼저 보이도록 정렬되어 반환된다.
운영자가 화면에서 보는 데이터는 조금 전 센서가 보낸 값이며, 시간도 이미 정규화된 기준으로 정렬되어 있어서 혼동이 없다.

운영자가 이어서 센서 상태 화면을 열면, 서버는 `handle_sensor_status_request(filters)`를 통해 현재 상태 정보를 반환한다.
여기서도 조금 전 갱신된 최신 상태가 사용되므로, `SN-NORMAL-01`은 `HEALTHY` 상태로 표시된다.

운영자는 복잡한 내부 로직을 알지 못해도 괜찮다.
다만 시스템 내부에서는 수집 API에서 저장한 정보가 조회 API와 상태 API까지 자연스럽게 이어지고 있다.

## 시나리오 3. 운영자가 모드 변경을 요청한다

오후가 되어 운영자는 특정 상황에 대비해 `SN-NORMAL-01`을 `EMERGENCY` 모드로 전환해두기로 한다.
대시보드에서 모드 변경 버튼을 누르면 서버는 `handle_mode_change_request(serial_number, target_mode)`를 실행한다.

이 함수는 우선 요청값이 유효한지 확인한 뒤, `record_mode_change_request(serial_number, target_mode, requested_at)`를 호출해 "서버가 이 센서에 EMERGENCY 모드를 요청했다"는 사실을 기록한다.
이 시점에는 아직 센서가 실제로 모드를 바꿨는지 확정하지 않는다.
서버는 요청의 의도를 저장할 뿐이다.

잠시 후 센서는 새 측정 데이터를 다시 전송한다.
이번에는 `mode` 값이 `EMERGENCY`로 담겨 있다.
서버는 다시 `handle_ingest_request(payload, ingest_mode)`부터 동일한 수집 과정을 거친다.
`validate_reading(record)`, `parse_and_normalize_timestamp(raw_timestamp)`, `enrich_record(record, received_at, normalized_timestamp)`, `save_valid_records(records)`, `update_current_sensor_status(records)`가 차례로 실행되며 새로운 측정값이 저장된다.

그리고 저장 후에는 mode change 요청과 실제 telemetry를 맞춰 보는 정산 흐름이 이어진다.
문서상 함수 목록에는 직접 드러나지 않지만, 이 단계는 앞서 기록된 요청과 방금 저장된 레코드를 비교해 "요청한 모드가 실제로 적용되었는지"를 확인하는 역할을 한다.
센서가 요청 이후 시점에 `EMERGENCY` 모드를 보고했으므로, 운영자는 시스템에서 해당 요청이 정상적으로 반영된 것으로 확인할 수 있다.

## 정리

이 일반 시나리오에는 오류도, 누락도, 충돌도 없다.
센서는 데이터를 정상적으로 보내고, 서버는 `handle_ingest_request`를 시작으로 검증과 정규화, 저장과 상태 갱신을 수행한다.
운영자는 `handle_query_request`와 `handle_sensor_status_request`를 통해 결과를 확인하고, 필요할 때 `handle_mode_change_request`로 모드 전환을 요청한다.

즉, 이 문서가 보여주는 것은 시스템이 가장 기대한 방식으로 움직일 때의 자연스러운 하루다.
그리고 그 평범한 흐름을 안정적으로 만들기 위해 `validate_top_level_payload`, `normalize_payload_to_records`, `validate_reading`, `parse_and_normalize_timestamp`, `enrich_record`, `process_batch_atomic`, `save_valid_records`, `update_current_sensor_status`, `evaluate_sensor_health`, `build_query_filters`, `query_readings`, `record_mode_change_request` 같은 함수들이 각자의 자리에서 책임을 나눠 가진다.
