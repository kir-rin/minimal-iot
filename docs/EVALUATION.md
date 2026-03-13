1. 타임존 처리 — 가장 핵심적인 함정

"UTC/KST 혼재"를 언급한 건 그냥 기능 요구가 아닙니다.

KST +09:00과 UTC Z가 같은 시각을 가리킬 수도, 다른 시각일 수도 있음
이걸 그냥 문자열로 저장하거나, naive하게 파싱하면 데이터가 뒤섞임
"당신이 시간 데이터를 얼마나 진지하게 다루는지" 를 보는 것

2. 배치(Batch) 수신 — 트랜잭션 일관성 및 순서 처리 능력

배열로 들어오는 데이터가 이미 지나간 timestamp일 수 있음
같은 serial_number의 데이터가 순서 없이 올 수 있음
"그냥 insert"하면 안 되고, 트랜잭션 일관성(all-or-nothing)과 순서 처리 전략을 고민했는지 봄

3. 고장 판단 로직 — 설계 사고력 테스트

"방법 무관하게"라는 말이 의미심장합니다
단순 cron job인지, 마지막 수신 시각 기반 추론인지, 센서 모드별 주기가 다른 것(NORMAL 10분 vs EMERGENCY 10초)을 반영했는지 봄
경계 케이스: 센서가 NORMAL→EMERGENCY로 전환되면 판단 기준 주기도 바뀌어야 함

4. 명세에 없는 기능을 추가했는가

"꼭 있어야 한다고 판단되면 추가하라"는 문구

이건 사실상 주니어/시니어를 가르는 문항입니다.

아무것도 안 추가 → 시키는 것만 하는 사람
데이터 유효성 검증, 에러 로깅, 통계 API, 이상값 알림 등 추가 + 이유 설명 → 서비스를 운영 관점에서 생각하는 사람

---

## 현재 프로젝트 평가 결과

### 1. 타임존 처리 ✅ 만족

**근거:**
- `src/domain/timestamp.py:28-38` - ISO8601 파서가 Z suffix와 +09:00 모두 지원, 결과는 항상 UTC로 변환
- `tests/unit/test_timestamp.py:16-20,22-26` - KST→UTC 변환 및 UTC/KST 동일 시각 정규화 테스트
- `src/models/reading.py:19-20` - DB 컬럼이 `DateTime(timezone=True)`로 선언하여 timezone-aware 저장

**핵심:** 문자열이 아닌 canonical UTC datetime으로 통일 저장, naive timestamp 거부

### 2. 배치 수신 ✅ 만족

**근거:**
- `src/services/ingestion_service.py:42-80` - ATOMIC/PARTIAL 수집 모드 지원
- `src/domain/batch_policy.py:31-64` - Atomic 정책: 하나라도 실패 시 전체 거부 (멱등성 보장)
- `src/services/ingestion_service.py:134-145` - `last_sensor_timestamp` 기반 OUT_OF_ORDER 감지
- `tests/integration/test_readings_ingest.py:193-231` - 미래 데이터 수신 후 과거 데이터가 OUT_OF_ORDER로 표시되는 테스트

**핵심:** 단순 insert가 아닌 검증→정책 결정→저장의 트랜잭션 일관성 흐름, 순서 없는 데이터 처리

### 3. 고장 판단 로직 ✅ 만족

**근거:**
- `src/schedulers/health_evaluation_job.py:36-150` - 주기적 스케줄러 기반 재평가
- `src/domain/status.py:33-68` - 모드별 동적 임계값: NORMAL/MAINTENANCE 12분, EMERGENCY 30초
- `src/domain/status.py:60-63` - `last_reported_mode` 기준으로 임계값 동적 선택
- `tests/unit/test_health_time_elapsed.py:31-101` - 모드별 경계값(12분/30초) 정확성 테스트
- `tests/unit/test_health_time_elapsed.py:148-178` - 시간 진행에 따른 HEALTHY→FAULTY 상태 전이 테스트

**핵심:** 스케줄러 + 마지막 수신 시각 기반 추론 + 모드별 주기 반영, NORMAL→EMERGENCY 전환 시 주기 자동 변경
