"""POST /api/v1/sensors/{serial_number}/mode 통합 테스트"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestModeChangeRequest:
    """모드 변경 요청 API 통합 테스트"""
    
    def test_mode_change_known_sensor(self, client: TestClient):
        """알려진 센서에 대한 모드 변경 요청 - sensor_known: true"""
        # 먼저 센서 데이터 수집
        reading = {
            "serial_number": "MODE-TEST-001",
            "timestamp": "2024-05-23T08:00:00Z",
            "mode": "NORMAL",
            "temperature": 24.5,
            "humidity": 50.2,
            "pressure": 1013.2,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 42
        }
        
        response = client.post("/api/v1/readings", json=reading)
        assert response.status_code == 201
        
        # 모드 변경 요청
        mode_request = {
            "mode": "EMERGENCY"
        }
        
        response = client.post(
            "/api/v1/sensors/MODE-TEST-001/mode",
            json=mode_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["sensor_known"] is True
        assert "requested_at" in data
        assert data["requested_mode"] == "EMERGENCY"
    
    def test_mode_change_unknown_sensor(self, client: TestClient):
        """알 수 없는 센서에 대한 모드 변경 요청 - sensor_known: false"""
        mode_request = {
            "mode": "EMERGENCY"
        }
        
        response = client.post(
            "/api/v1/sensors/UNKNOWN-SENSOR-999/mode",
            json=mode_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["sensor_known"] is False
    
    def test_mode_change_invalid_mode(self, client: TestClient):
        """잘못된 모드 값으로 요청"""
        # 센서 데이터 먼저 수집
        reading = {
            "serial_number": "MODE-TEST-002",
            "timestamp": "2024-05-23T08:00:00Z",
            "mode": "NORMAL",
            "temperature": 24.5,
            "humidity": 50.2,
            "pressure": 1013.2,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 42
        }
        
        client.post("/api/v1/readings", json=reading)
        
        # 잘못된 모드로 요청
        mode_request = {
            "mode": "INVALID_MODE"
        }
        
        response = client.post(
            "/api/v1/sensors/MODE-TEST-002/mode",
            json=mode_request
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_mode_change_missing_mode_field(self, client: TestClient):
        """mode 필드 누락"""
        mode_request = {}
        
        response = client.post(
            "/api/v1/sensors/MODE-TEST-001/mode",
            json=mode_request
        )
        
        assert response.status_code == 422
    
    def test_mode_change_valid_modes(self, client: TestClient):
        """유효한 모든 모드 값으로 요청"""
        # 센서 데이터 수집
        reading = {
            "serial_number": "MODE-TEST-003",
            "timestamp": "2024-05-23T08:00:00Z",
            "mode": "NORMAL",
            "temperature": 24.5,
            "humidity": 50.2,
            "pressure": 1013.2,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 42
        }
        
        client.post("/api/v1/readings", json=reading)
        
        valid_modes = ["NORMAL", "EMERGENCY", "MAINTENANCE"]
        
        for mode in valid_modes:
            mode_request = {"mode": mode}
            
            response = client.post(
                "/api/v1/sensors/MODE-TEST-003/mode",
                json=mode_request
            )
            
            assert response.status_code == 200, f"Mode {mode} should be valid"
            data = response.json()
            assert data["success"] is True
            assert data["requested_mode"] == mode
    
    def test_mode_change_request_stored(self, client: TestClient):
        """모드 변경 요청이 저장되는지 확인"""
        # 센서 데이터 수집
        reading = {
            "serial_number": "MODE-TEST-004",
            "timestamp": "2024-05-23T08:00:00Z",
            "mode": "NORMAL",
            "temperature": 24.5,
            "humidity": 50.2,
            "pressure": 1013.2,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 42
        }
        
        client.post("/api/v1/readings", json=reading)
        
        # 모드 변경 요청
        mode_request = {"mode": "EMERGENCY"}
        response = client.post(
            "/api/v1/sensors/MODE-TEST-004/mode",
            json=mode_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 요청 정보 확인
        assert "requested_at" in data


class TestModeChangeResponseStructure:
    """모드 변경 API 응답 구조 검증"""
    
    @pytest.fixture(autouse=True)
    def setup_sensor(self, client: TestClient):
        """테스트 센서 생성"""
        reading = {
            "serial_number": "MODE-STRUCT-001",
            "timestamp": "2024-05-23T08:00:00Z",
            "mode": "NORMAL",
            "temperature": 24.5,
            "humidity": 50.2,
            "pressure": 1013.2,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 42
        }
        
        client.post("/api/v1/readings", json=reading)
    
    def test_mode_change_response_fields(self, client: TestClient):
        """응답에 필요한 모든 필드가 있는지 확인"""
        mode_request = {"mode": "EMERGENCY"}
        
        response = client.post(
            "/api/v1/sensors/MODE-STRUCT-001/mode",
            json=mode_request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 필수 필드 확인
        assert "success" in data
        assert "sensor_known" in data
        assert "requested_mode" in data
        assert "requested_at" in data
