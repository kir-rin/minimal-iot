"""GET /api/v1/sensors/status 통합 테스트"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestGetSensorStatus:
    """GET /api/v1/sensors/status 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, client: TestClient):
        """테스트 데이터 설정"""
        # 여러 센서 데이터 준비
        test_data = [
            {
                "serial_number": "STATUS-TEST-001",
                "timestamp": "2024-05-23T08:00:00Z",
                "mode": "NORMAL",
                "temperature": 24.5,
                "humidity": 50.2,
                "pressure": 1013.2,
                "location": {"lat": 37.5665, "lng": 126.9780},
                "air_quality": 42
            },
            {
                "serial_number": "STATUS-TEST-002",
                "timestamp": "2024-05-23T08:30:00Z",
                "mode": "EMERGENCY",
                "temperature": 28.1,
                "humidity": 65.4,
                "pressure": 1009.5,
                "location": {"lat": 35.1796, "lng": 129.0756},
                "air_quality": 88
            },
        ]
        
        # 데이터 저장
        for reading in test_data:
            response = client.post("/api/v1/readings", json=reading)
            assert response.status_code == 201
    
    def test_get_sensor_status_all(self, client: TestClient):
        """전체 센서 상태 조회"""
        response = client.get("/api/v1/sensors/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        
        # 최소 2개의 테스트 센서 존재
        serial_numbers = [s["serial_number"] for s in data["data"]]
        assert "STATUS-TEST-001" in serial_numbers
        assert "STATUS-TEST-002" in serial_numbers
    
    def test_get_sensor_status_by_serial_number(self, client: TestClient):
        """특정 시리얼 번호로 조회"""
        response = client.get("/api/v1/sensors/status?serial_number=STATUS-TEST-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        
        sensor = data["data"][0]
        assert sensor["serial_number"] == "STATUS-TEST-001"
        assert sensor["last_reported_mode"] == "NORMAL"
        assert "health_status" in sensor
        assert "telemetry_status" in sensor
    
    def test_get_sensor_status_nonexistent(self, client: TestClient):
        """존재하지 않는 시리얼 번호 조회"""
        response = client.get("/api/v1/sensors/status?serial_number=NONEXISTENT")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0
    
    def test_get_sensor_status_by_health_status_healthy(self, client: TestClient):
        """HEALTHY 상태로 필터링"""
        response = client.get("/api/v1/sensors/status?health_status=HEALTHY")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 모든 조회된 센서가 HEALTHY 상태
        for sensor in data["data"]:
            assert sensor["health_status"] == "HEALTHY"
    
    def test_get_sensor_status_by_health_status_faulty(self, client: TestClient):
        """FAULTY 상태로 필터링"""
        response = client.get("/api/v1/sensors/status?health_status=FAULTY")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 모든 조회된 센서가 FAULTY 상태
        for sensor in data["data"]:
            assert sensor["health_status"] == "FAULTY"
    
    def test_get_sensor_status_response_structure(self, client: TestClient):
        """응답 구조 검증"""
        response = client.get("/api/v1/sensors/status?serial_number=STATUS-TEST-001")
        
        assert response.status_code == 200
        data = response.json()
        sensor = data["data"][0]
        
        # 필수 필드 확인
        assert "serial_number" in sensor
        assert "last_sensor_timestamp" in sensor
        assert "last_server_received_at" in sensor
        assert "last_reported_mode" in sensor
        assert "health_status" in sensor
        assert "telemetry_status" in sensor
        assert "health_evaluated_at" in sensor
        assert "last_reading_id" in sensor
    
    def test_get_sensor_status_invalid_health_status(self, client: TestClient):
        """잘못된 health_status 값"""
        response = client.get("/api/v1/sensors/status?health_status=INVALID")
        
        assert response.status_code == 400
        assert "health_status must be either" in response.json()["detail"]
    
    def test_get_sensor_status_combined_filters(self, client: TestClient):
        """복합 필터 (serial_number + health_status)"""
        # 존재하는 센서 + HEALTHY 상태
        response = client.get(
            "/api/v1/sensors/status"
            "?serial_number=STATUS-TEST-001"
            "&health_status=HEALTHY"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        if len(data["data"]) > 0:
            sensor = data["data"][0]
            assert sensor["serial_number"] == "STATUS-TEST-001"
            assert sensor["health_status"] == "HEALTHY"
    
    def test_sensor_status_updated_after_new_reading(self, client: TestClient):
        """새로운 reading 수집 후 상태 갱신"""
        # 추가 데이터 수집
        new_reading = {
            "serial_number": "STATUS-TEST-001",
            "timestamp": "2024-05-23T09:00:00Z",
            "mode": "EMERGENCY",  # 모드 변경
            "temperature": 30.0,
            "humidity": 70.0,
            "pressure": 1008.0,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 90
        }
        
        response = client.post("/api/v1/readings", json=new_reading)
        assert response.status_code == 201
        
        # 상태 재조회
        response = client.get("/api/v1/sensors/status?serial_number=STATUS-TEST-001")
        data = response.json()
        sensor = data["data"][0]
        
        # 모드가 EMERGENCY로 변경되었는지 확인
        assert sensor["last_reported_mode"] == "EMERGENCY"


class TestSensorStatusVsReadings:
    """센서 상태 API와 readings API 비교 테스트"""
    
    def test_status_api_has_health_fields_not_readings(self, client: TestClient):
        """status API에는 상태 필드가 있고 readings에는 없음"""
        # 데이터 준비
        reading = {
            "serial_number": "COMPARE-001",
            "timestamp": "2024-05-23T10:00:00Z",
            "mode": "NORMAL",
            "temperature": 24.0,
            "humidity": 50.0,
            "pressure": 1013.0,
            "location": {"lat": 37.0, "lng": 127.0},
            "air_quality": 40
        }
        
        resp = client.post("/api/v1/readings", json=reading)
        assert resp.status_code == 201
        
        # readings API 응답 확인
        readings_resp = client.get("/api/v1/readings?serial_number=COMPARE-001")
        readings_data = readings_resp.json()
        
        assert readings_resp.status_code == 200
        reading_item = readings_data["data"][0]
        
        # readings에는 상태 필드 없음
        assert "health_status" not in reading_item
        assert "telemetry_status" not in reading_item
        
        # status API 응답 확인
        status_resp = client.get("/api/v1/sensors/status?serial_number=COMPARE-001")
        status_data = status_resp.json()
        
        assert status_resp.status_code == 200
        sensor = status_data["data"][0]
        
        # status API에는 상태 필드 있음
        assert "health_status" in sensor
        assert "telemetry_status" in sensor
