from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def valid_reading_payload():
    """유효한 단일 센서 데이터"""
    return {
        "serial_number": "TEST-001",
        "timestamp": "2024-05-23T08:30:00Z",
        "mode": "NORMAL",
        "temperature": 24.5,
        "humidity": 50.2,
        "pressure": 1013.2,
        "location": {"lat": 37.5665, "lng": 126.9780},
        "air_quality": 42
    }


@pytest.fixture
def valid_batch_payloads():
    """유효한 배치 센서 데이터"""
    return [
        {
            "serial_number": "TEST-001",
            "timestamp": "2024-05-23T08:30:00Z",
            "mode": "NORMAL",
            "temperature": 24.5,
            "humidity": 50.2,
            "pressure": 1013.2,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 42
        },
        {
            "serial_number": "TEST-002",
            "timestamp": "2024-05-23T08:31:00Z",
            "mode": "EMERGENCY",
            "temperature": 28.1,
            "humidity": 65.4,
            "pressure": 1009.5,
            "location": {"lat": 35.1796, "lng": 129.0756},
            "air_quality": 88
        }
    ]


class TestPostReadings:
    """POST /api/v1/readings 통합 테스트"""

    def test_post_single_reading_success(self, client: TestClient, valid_reading_payload):
        """단일 센서 데이터 수집 성공"""
        response = client.post("/api/v1/readings", json=valid_reading_payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["ingest_mode"] == "atomic"
        assert data["accepted_count"] == 1
        assert data["rejected_count"] == 0
        assert len(data["errors"]) == 0

    def test_post_batch_readings_atomic_success(self, client: TestClient, valid_batch_payloads):
        """배열 형태 데이터 수집 성공 (atomic 모드)"""
        response = client.post("/api/v1/readings", json=valid_batch_payloads)
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["ingest_mode"] == "atomic"
        assert data["accepted_count"] == 2
        assert data["rejected_count"] == 0
        assert len(data["errors"]) == 0

    def test_post_empty_array_no_op(self, client: TestClient):
        """빈 배열은 no-op success"""
        response = client.post("/api/v1/readings", json=[])
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["accepted_count"] == 0
        assert data["rejected_count"] == 0

    def test_post_batch_atomic_rollback_on_failure(self, client: TestClient, valid_batch_payloads):
        """atomic에서 1건 실패 시 전체 롤백"""
        # 두 번째 레코드를 유효하지 않게 만듦
        invalid_batch = valid_batch_payloads.copy()
        invalid_batch[1]["mode"] = "INVALID_MODE"
        
        response = client.post("/api/v1/readings", json=invalid_batch)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["ingest_mode"] == "atomic"
        assert data["accepted_count"] == 0
        assert data["rejected_count"] == 1  # 하나만 실패
        assert len(data["errors"]) == 1
        assert data["errors"][0]["index"] == 1
        
        # DB에는 아무것도 저장되지 않았는지 확인
        # (이후 조회 API로 검증 가능)

    def test_post_batch_partial_mixed(self, client: TestClient, valid_batch_payloads):
        """partial에서 일부 성공/일부 실패"""
        # 두 번째 레코드를 유효하지 않게 만듦
        mixed_batch = valid_batch_payloads.copy()
        mixed_batch[1]["timestamp"] = "invalid-timestamp"
        
        response = client.post("/api/v1/readings?ingest_mode=partial", json=mixed_batch)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True  # 일부 성공이므로 success=True
        assert data["ingest_mode"] == "partial"
        assert data["accepted_count"] == 1
        assert data["rejected_count"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["index"] == 1
        assert data["errors"][0]["field"] == "timestamp"

    def test_post_batch_partial_all_fail(self, client: TestClient, valid_batch_payloads):
        """partial에서 전체 실패 시 success: false"""
        # 모든 레코드를 유효하지 않게 만듦
        all_invalid = [
            {"serial_number": "TEST-001", "timestamp": "bad", "mode": "BAD"},
            {"serial_number": "TEST-002", "timestamp": "bad", "mode": "WORSE"}
        ]
        
        response = client.post("/api/v1/readings?ingest_mode=partial", json=all_invalid)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False  # 전체 실패이므로 success=False
        assert data["ingest_mode"] == "partial"
        assert data["accepted_count"] == 0
        assert data["rejected_count"] == 2
        assert len(data["errors"]) == 2

    def test_timestamp_normalization_stored(self, client: TestClient):
        """UTC/KST mixed batch 정규화되어 저장"""
        # UTC와 KST 섞은 배치
        mixed_timezone_batch = [
            {
                "serial_number": "TEST-001",
                "timestamp": "2024-05-23T08:30:00Z",  # UTC
                "mode": "NORMAL",
                "temperature": 24.5,
                "humidity": 50.2,
                "pressure": 1013.2,
                "location": {"lat": 37.5665, "lng": 126.9780},
                "air_quality": 42
            },
            {
                "serial_number": "TEST-002",
                "timestamp": "2024-05-23T17:30:00+09:00",  # KST (UTC와 같은 시각)
                "mode": "NORMAL",
                "temperature": 25.0,
                "humidity": 51.0,
                "pressure": 1014.0,
                "location": {"lat": 35.1796, "lng": 129.0756},
                "air_quality": 45
            }
        ]
        
        response = client.post("/api/v1/readings", json=mixed_timezone_batch)
        
        assert response.status_code == 201
        # 실제 저장된 데이터는 canonical UTC로 변환되어야 함
        # 이후 GET /api/v1/readings로 검증

    def test_sensor_status_updated_after_ingest(self, client: TestClient, valid_reading_payload):
        """수집 후 sensor current status 자동 갱신"""
        # 먼저 데이터 수집
        response = client.post("/api/v1/readings", json=valid_reading_payload)
        assert response.status_code == 201
        
        # 센서 상태 조회
        status_response = client.get(f"/api/v1/sensors/status?serial_number=TEST-001")
        
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["success"] is True
        assert len(status_data["data"]) == 1
        
        sensor = status_data["data"][0]
        assert sensor["serial_number"] == "TEST-001"
        assert sensor["last_reported_mode"] == "NORMAL"
        assert sensor["health_status"] == "HEALTHY"

    def test_out_of_order_partial_update(self, client: TestClient):
        """out-of-order 레코드는 부분 갱신"""
        # 먼저 최신 데이터 수집
        latest = {
            "serial_number": "TEST-003",
            "timestamp": "2024-05-23T10:00:00Z",
            "mode": "NORMAL",
            "temperature": 24.5,
            "humidity": 50.2,
            "pressure": 1013.2,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 42
        }
        client.post("/api/v1/readings", json=latest)
        
        # 과거 데이터 수집 (out-of-order)
        older = {
            "serial_number": "TEST-003",
            "timestamp": "2024-05-23T09:00:00Z",  # 1시간 전
            "mode": "EMERGENCY",
            "temperature": 28.0,
            "humidity": 60.0,
            "pressure": 1010.0,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 50
        }
        response = client.post("/api/v1/readings", json=older)
        assert response.status_code == 201
        
        # 센서 상태 조회 - last_sensor_timestamp는 여전히 10:00이어야 함
        status_response = client.get("/api/v1/sensors/status?serial_number=TEST-003")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        sensor = status_data["data"][0]
        # OUT_OF_ORDER이므로 last_sensor_timestamp는 갱신되지 않음
        # SQLite는 timezone 정보를 저장하지 않으므로 Z suffix 없이 비교
        assert sensor["last_sensor_timestamp"] in ["2024-05-23T10:00:00", "2024-05-23T10:00:00Z"]
        assert sensor["telemetry_status"] == "OUT_OF_ORDER"


class TestRequestLevelErrors:
    """요청 수준 오류 테스트"""

    def test_malformed_json(self, client: TestClient):
        """잘못된 JSON은 요청 수준 실패"""
        response = client.post(
            "/api/v1/readings",
            content=b"not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # FastAPI validation error

    def test_unsupported_payload_type(self, client: TestClient):
        """지원하지 않는 payload 타입"""
        response = client.post("/api/v1/readings", json="string payload")
        
        assert response.status_code == 422

    def test_invalid_ingest_mode(self, client: TestClient, valid_reading_payload):
        """유효하지 않은 ingest_mode"""
        response = client.post(
            "/api/v1/readings?ingest_mode=invalid",
            json=valid_reading_payload
        )
        
        assert response.status_code == 422
