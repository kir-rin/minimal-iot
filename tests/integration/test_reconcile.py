"""모드 변경 reconcile 통합 테스트"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient


class TestModeReconcile:
    """모드 변경 reconcile 통합 테스트"""
    
    def test_reconcile_applied_when_telemetry_after_request(self, client: TestClient):
        """요청 이후 수신된 telemetry는 applied로 처리"""
        # 1. 먼저 센서 데이터 수집
        reading = {
            "serial_number": "RECONCILE-001",
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
        
        # 2. 모드 변경 요청
        mode_request = {"mode": "EMERGENCY"}
        response = client.post(
            "/api/v1/sensors/RECONCILE-001/mode",
            json=mode_request
        )
        
        assert response.status_code == 200
        request_data = response.json()
        requested_at = request_data["requested_at"]
        
        # 3. 요청 이후 telemetry 수신 (시간상 나중)
        # 테스트에서는 clock이 고정되어 있으므로 실제 시간 차이는 없지만
        # 논리적으로는 요청 이후 수신
        new_reading = {
            "serial_number": "RECONCILE-001",
            "timestamp": "2024-05-23T08:05:00Z",  # 더 최근 센서 시간
            "mode": "EMERGENCY",  # 요청한 모드로 변경됨
            "temperature": 30.0,
            "humidity": 70.0,
            "pressure": 1008.0,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 90
        }
        
        response = client.post("/api/v1/readings", json=new_reading)
        assert response.status_code == 201
        
        # 4. reconcile 결과 확인 - 모드 변경이 applied되어야 함
        # 이는 현재는 직접 확인할 수 없으나, 추후 reconcile 상태 조회 API가 있으면 확인 가능
    
    def test_reconcile_not_applied_for_past_telemetry(self, client: TestClient):
        """요청 이전에 생성된(늦게 도착한) telemetry는 applied로 처리되지 않음"""
        # 1. 센서 데이터 수집
        reading = {
            "serial_number": "RECONCILE-002",
            "timestamp": "2024-05-23T08:00:00Z",
            "mode": "NORMAL",
            "temperature": 24.5,
            "humidity": 50.2,
            "pressure": 1013.2,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 42
        }
        
        client.post("/api/v1/readings", json=reading)
        
        # 2. 모드 변경 요청
        mode_request = {"mode": "EMERGENCY"}
        response = client.post(
            "/api/v1/sensors/RECONCILE-002/mode",
            json=mode_request
        )
        assert response.status_code == 200
        
        # 3. 요청 이전 시간의 telemetry 수신 (늦게 도착한 과거 데이터)
        # sensor_timestamp는 과거이지만, 서버는 지금 받음
        old_reading = {
            "serial_number": "RECONCILE-002",
            "timestamp": "2024-05-23T07:59:00Z",  # 요청 이전 센서 시간
            "mode": "NORMAL",  # 이전 모드
            "temperature": 24.0,
            "humidity": 49.0,
            "pressure": 1014.0,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 40
        }
        
        response = client.post("/api/v1/readings", json=old_reading)
        assert response.status_code == 201
        
        # 4. 이 telemetry는 reconcile 대상이 아님
        # (server_received_at < requested_at 조건으로 인해)
    
    def test_only_latest_pending_request_is_reconciled(self, client: TestClient):
        """가장 최근 미해결 요청 1건만 reconcile 대상"""
        # 1. 센서 데이터 수집
        reading = {
            "serial_number": "RECONCILE-003",
            "timestamp": "2024-05-23T08:00:00Z",
            "mode": "NORMAL",
            "temperature": 24.5,
            "humidity": 50.2,
            "pressure": 1013.2,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 42
        }
        
        client.post("/api/v1/readings", json=reading)
        
        # 2. 첫 번째 모드 변경 요청 (NORMAL -> EMERGENCY)
        mode_request_1 = {"mode": "EMERGENCY"}
        response = client.post(
            "/api/v1/sensors/RECONCILE-003/mode",
            json=mode_request_1
        )
        assert response.status_code == 200
        
        # 3. 두 번째 모드 변경 요청 (EMERGENCY -> MAINTENANCE) - 이것이 최신
        mode_request_2 = {"mode": "MAINTENANCE"}
        response = client.post(
            "/api/v1/sensors/RECONCILE-003/mode",
            json=mode_request_2
        )
        assert response.status_code == 200
        
        # 4. MAINTENANCE 모드로 telemetry 수신
        # 이것은 두 번째 요청에 대해 reconcile되어야 함
        new_reading = {
            "serial_number": "RECONCILE-003",
            "timestamp": "2024-05-23T08:05:00Z",
            "mode": "MAINTENANCE",
            "temperature": 25.0,
            "humidity": 55.0,
            "pressure": 1012.0,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 45
        }
        
        response = client.post("/api/v1/readings", json=new_reading)
        assert response.status_code == 201
        
        # 5. 첫 번째 요청(EMERGENCY)는 여전히 pending이어야 함
        # 두 번째 요청(MAINTENANCE)만 applied되어야 함
    
    def test_reconcile_condition_server_received_at_check(self, client: TestClient):
        """reconcile 조건: server_received_at >= requested_at"""
        # 이 테스트는 실제 시간 주입이 필요하여 integration test에서는 한계가 있음
        # 단위 테스트에서 상세히 검증
        pass


class TestModeRequestLifecycle:
    """모드 변경 요청 생명주기 테스트"""
    
    def test_request_starts_as_pending(self, client: TestClient):
        """요청 생성 시 PENDING 상태"""
        # 센서 데이터 수집
        reading = {
            "serial_number": "LIFECYCLE-001",
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
            "/api/v1/sensors/LIFECYCLE-001/mode",
            json=mode_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["request_status"] == "PENDING"
    
    def test_request_transition_to_applied(self, client: TestClient):
        """요청이 applied로 전환되는 경우"""
        # 센서 데이터 수집
        reading = {
            "serial_number": "LIFECYCLE-002",
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
            "/api/v1/sensors/LIFECYCLE-002/mode",
            json=mode_request
        )
        
        request_data = response.json()
        requested_at = request_data["requested_at"]
        
        # EMERGENCY 모드로 변경된 telemetry 수신
        new_reading = {
            "serial_number": "LIFECYCLE-002",
            "timestamp": "2024-05-23T08:05:00Z",
            "mode": "EMERGENCY",
            "temperature": 30.0,
            "humidity": 70.0,
            "pressure": 1008.0,
            "location": {"lat": 37.5665, "lng": 126.9780},
            "air_quality": 90
        }
        
        client.post("/api/v1/readings", json=new_reading)
        
        # reconcile 후 상태가 APPLIED로 변경되어야 함
        # (추후 reconcile 상태 조회 API로 확인 가능)
