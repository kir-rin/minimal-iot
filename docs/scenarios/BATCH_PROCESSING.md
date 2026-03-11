# BATCH_PROCESSING Scenario

## 목적

이 문서는 여러 센서 측정값이 하나의 배열 payload로 들어왔을 때, 시스템이 이를 어떻게 일관된 배치 처리 흐름으로 다루는지 설명한다.
핵심은 단건 요청을 여러 번 따로 처리하는 것이 아니라, 하나의 요청 안에 담긴 여러 레코드를 같은 규칙으로 검증하고 저장하며 결과를 집계하는 데 있다.
서술 안에서는 `docs/PSEUDOCODE.md`의 함수 이름을 그대로 언급해 실제 구현 흐름과 연결한다.

## 시나리오. 게이트웨이가 여러 측정값을 한 번에 보낸다

오후 2시, 현장 게이트웨이는 각 센서가 짧은 시간 동안 모아 보낸 측정값을 배열 형태로 서버에 전달한다.
운영자 입장에서는 이것이 자연스러운 전송 방식이다.
센서가 하나씩 매번 따로 요청을 보내는 대신, 게이트웨이가 한 번에 묶어서 보내면 네트워크 사용도 단순해지고 서버 입장에서도 수집 단위를 분명하게 관리할 수 있다.

서버는 `handle_ingest_request(payload, ingest_mode)`로 이 요청을 받는다.
이번에는 여러 레코드가 담긴 배열 payload이므로, 이 요청의 핵심은 "각 레코드를 따로따로 흩어 처리하지 않고 하나의 배치로 어떻게 다룰 것인가"에 있다.

가장 먼저 `validate_top_level_payload(payload)`가 실행된다.
이 단계에서 서버는 요청이 배치로 처리 가능한 배열인지 확인한다.
배열 구조가 정상이라면 요청은 다음 단계로 넘어가고, `normalize_payload_to_records(payload)`는 내부적으로 다룰 레코드 목록을 만든다.
단건 입력도 결국 같은 구조로 바뀌지만, 이번 시나리오에서는 처음부터 여러 건이 명확하게 들어온다.

이제 시스템은 배치 안에 들어 있는 각 레코드를 같은 순서로 훑는다.
각 항목은 `validate_reading(record)`로 검증되고, 시간값은 필요할 경우 `parse_and_normalize_timestamp(raw_timestamp)`를 통해 내부 기준 시각으로 정리된다.
검증을 통과한 레코드는 `enrich_record(record, received_at, normalized_timestamp)`로 저장 가능한 형태가 된다.
이 과정이 중요한 이유는, 배치 안에 몇 건이 들어 있든 각 레코드가 동일한 규칙을 적용받아야 전체 결과를 예측 가능하게 만들 수 있기 때문이다.

이번 시나리오에서 게이트웨이가 보낸 데이터는 모두 정상이다.
따라서 기본 정책인 `atomic` 기준으로 `process_batch_atomic(records, received_at)`가 실행되더라도 중간에 배치를 멈출 이유가 없다.
시스템은 배치 전체를 하나의 논리 단위로 보고, 모든 레코드가 문제없음을 확인한 뒤 저장 단계로 넘어간다.

저장 시점에는 `save_valid_records(records)`가 배치 안의 정상 레코드들을 순서대로 영속화한다.
이후 `update_current_sensor_status(records)`는 방금 저장된 여러 레코드를 센서별로 묶어 최신 상태를 갱신한다.
즉, 배치 처리는 단순히 여러 줄을 한 번에 넣는 작업이 아니라, 저장 이후의 상태 관리까지 한 번의 흐름 안에서 이어지는 작업이다.

클라이언트는 응답으로 배치 전체에 대한 집계 결과를 받는다.
이 응답에는 `accepted_count`, `rejected_count`, `errors`가 포함되며, 운영자는 한 번의 요청이 실제로 몇 건을 처리했는지 바로 이해할 수 있다.
이번에는 모든 레코드가 정상 처리되었으므로 `accepted_count`는 배치 크기와 같고, `rejected_count`는 0이며, `errors`도 비어 있다.

이 배치 처리 흐름의 장점은 이후 정책 확장에도 그대로 이어진다는 점이다.
기본 시나리오에서는 `process_batch_atomic`이 전체 성공으로 끝나지만, 같은 진입점인 `handle_ingest_request` 아래에서 필요하면 `process_batch_partial(records, received_at)`로도 분기할 수 있다.
즉, 시스템은 배치를 처리하는 공통 뼈대를 먼저 갖추고, 그 위에서 운영 정책만 다르게 선택할 수 있도록 설계되어 있다.

운영자는 화면에서 단순히 "여러 건이 한 번에 잘 들어왔다"고 느끼겠지만,
그 뒤에서는 `validate_top_level_payload`, `normalize_payload_to_records`, `validate_reading`, `parse_and_normalize_timestamp`, `enrich_record`, `process_batch_atomic`, `save_valid_records`, `update_current_sensor_status`가 배치 전체를 흔들림 없이 처리하기 위해 역할을 나눠 맡고 있다.

## 정리

이 시나리오는 배치 데이터 처리가 단순히 배열을 받는 기능이 아니라, 여러 레코드를 하나의 요청 단위로 묶어 검증, 정규화, 저장, 상태 갱신까지 일관되게 수행하는 구조임을 보여준다.
시스템은 `handle_ingest_request`에서 시작해 `validate_top_level_payload`와 `normalize_payload_to_records`로 배치를 준비하고, `validate_reading`, `parse_and_normalize_timestamp`, `enrich_record`로 각 레코드를 같은 규칙으로 처리한다.
이후 `process_batch_atomic`과 `save_valid_records`, `update_current_sensor_status`를 통해 배치 전체 결과를 안정적으로 완성한다.

즉, 이 시스템의 배치 처리는 여러 데이터를 한 번에 받는 편의 기능이 아니라,
여러 레코드를 하나의 운영 단위로 안정적으로 다루기 위한 핵심 처리 전략이다.
