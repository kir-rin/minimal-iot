"""GET /api/v1/readings 통합 테스트"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


class TestGetReadings:
    """GET /api/v1/readings 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, client: TestClient):
        """테스트 데이터 설정"""
        # 센서 데이터 준비
        self.test_data = [
            {
                "serial_number": "QUERY-TEST-001",
                "timestamp": "2024-05-23T08:00:00Z",
                "mode": "NORMAL",
                "temperature": 24.5,
                "humidity": 50.2,
                "pressure": 1013.2,
                "location": {"lat": 37.5665, "lng": 126.9780},
                "air_quality": 42
            },
            {
                "serial_number": "QUERY-TEST-001",
                "timestamp": "2024-05-23T08:30:00Z",
                "mode": "NORMAL",
                "temperature": 25.0,
                "humidity": 51.0,
                "pressure": 1014.0,
                "location": {"lat": 37.5665, "lng": 126.9780},
                "air_quality": 45
            },
            {
                "serial_number": "QUERY-TEST-002",
                "timestamp": "2024-05-23T08:15:00Z",
                "mode": "EMERGENCY",
                "temperature": 28.1,
                "humidity": 65.4,
                "pressure": 1009.5,
                "location": {"lat": 35.1796, "lng": 129.0756},
                "air_quality": 88
            },
            {
                "serial_number": "QUERY-TEST-003",
                "timestamp": "2024-05-23T09:00:00Z",
                "mode": "NORMAL",
                "temperature": 22.0,
                "humidity": 48.0,
                "pressure": 1015.0,
                "location": {"lat": 36.0, "lng": 127.0},
                "air_quality": 30
            },
        ]
        
        # 데이터 저장
        for reading in self.test_data:
            response = client.post("/api/v1/readings", json=reading)
            assert response.status_code == 201
    
    def test_get_readings_no_filter(self, client: TestClient):
        """필터 없이 전체 조회"""
        response = client.get("/api/v1/readings")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 4  # 최소 4개의 테스트 데이터
        assert "pagination" in data
        
        # pagination 검증
        pagination = data["pagination"]
        assert pagination["current_page"] == 1
        assert pagination["limit"] == 50
        assert pagination["total_pages"] >= 1
        assert pagination["has_prev_page"] is False
    
    def test_get_readings_by_serial_number(self, client: TestClient):
        """시리얼 번호로 필터링"""
        response = client.get("/api/v1/readings?serial_number=QUERY-TEST-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        
        for reading in data["data"]:
            assert reading["serial_number"] == "QUERY-TEST-001"
    
    def test_get_readings_by_mode(self, client: TestClient):
        """모드로 필터링"""
        response = client.get("/api/v1/readings?mode=EMERGENCY")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # EMERGENCY 모드 데이터만 조회됨
        for reading in data["data"]:
            assert reading["mode"] == "EMERGENCY"
    
    def test_get_readings_by_sensor_time_range(self, client: TestClient):
        """센서 생성 시각 범위로 필터링"""
        response = client.get(
            "/api/v1/readings"
            "?sensor_from=2024-05-23T08:00:00Z"
            "&sensor_to=2024-05-23T08:20:00Z"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 08:00:00 ~ 08:20:00 사이 데이터만 (문자열 비교로 검증)
        for reading in data["data"]:
            ts_str = reading["timestamp"]
            # Z suffix 제거하고 naive datetime으로 변환
            if ts_str.endswith('Z'):
                ts_str = ts_str[:-1]
            ts = datetime.fromisoformat(ts_str)
            start_time = datetime(2024, 5, 23, 8, 0, 0)
            end_time = datetime(2024, 5, 23, 8, 20, 0)
            assert ts >= start_time, f"Timestamp {ts} should be >= {start_time}"
            assert ts <= end_time, f"Timestamp {ts} should be <= {end_time}"
    
    def test_get_readings_by_received_time_range(self, client: TestClient):
        """서버 수신 시각 범위로 필터링"""
        response = client.get(
            "/api/v1/readings"
            "?received_from=2024-01-01T00:00:00Z"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 현재 시점 이후로 받은 데이터
        assert len(data["data"]) >= 4
    
    def test_get_readings_combined_filters(self, client: TestClient):
        """복합 필터 조합"""
        response = client.get(
            "/api/v1/readings"
            "?serial_number=QUERY-TEST-001"
            "&mode=NORMAL"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # QUERY-TEST-001이면서 NORMAL 모드
        for reading in data["data"]:
            assert reading["serial_number"] == "QUERY-TEST-001"
            assert reading["mode"] == "NORMAL"
    
    def test_get_readings_pagination(self, client: TestClient):
        """페이지네이션 동작"""
        response = client.get("/api/v1/readings?serial_number=QUERY-TEST-001&limit=1&page=1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        
        pagination = data["pagination"]
        assert pagination["limit"] == 1
        assert pagination["total_count"] == 2
        assert pagination["total_pages"] == 2
        assert pagination["has_next_page"] is True
        assert pagination["has_prev_page"] is False
        
        # 두 번째 페이지
        response2 = client.get("/api/v1/readings?serial_number=QUERY-TEST-001&limit=1&page=2")
        data2 = response2.json()
        assert data2["pagination"]["has_next_page"] is False
        assert data2["pagination"]["has_prev_page"] is True
    
    def test_get_readings_empty_result(self, client: TestClient):
        """결과 없음"""
        response = client.get("/api/v1/readings?serial_number=NONEXISTENT")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0
        
        # total_count == 0 이면 total_pages == 0
        pagination = data["pagination"]
        assert pagination["total_count"] == 0
        assert pagination["total_pages"] == 0
    
    def test_get_readings_response_structure(self, client: TestClient):
        """응답 구조 검증 (상태 필드 없음)"""
        response = client.get("/api/v1/readings?serial_number=QUERY-TEST-001&limit=1")
        
        assert response.status_code == 200
        data = response.json()
        reading = data["data"][0]
        
        # 필수 필드 확인
        assert "id" in reading
        assert "serial_number" in reading
        assert "timestamp" in reading
        assert "raw_timestamp" in reading
        assert "server_received_at" in reading
        assert "mode" in reading
        assert "metrics" in reading
        assert "location" in reading
        
        # metrics 하위 필드
        metrics = reading["metrics"]
        assert "temperature" in metrics
        assert "humidity" in metrics
        assert "pressure" in metrics
        assert "air_quality" in metrics
        
        # location 하위 필드
        location = reading["location"]
        assert "lat" in location
        assert "lng" in location
        
        # 상태 필드는 없음
        assert "health_status" not in reading
        assert "telemetry_status" not in reading
    
    def test_get_readings_invalid_mode(self, client: TestClient):
        """잘못된 모드 값"""
        response = client.get("/api/v1/readings?mode=INVALID")
        
        assert response.status_code == 400
        assert "mode must be either" in response.json()["detail"]
    
    def test_get_readings_invalid_datetime_format(self, client: TestClient):
        """잘못된 ISO8601 형식"""
        response = client.get("/api/v1/readings?sensor_from=invalid-datetime")
        
        assert response.status_code == 400
        assert "Invalid ISO8601" in response.json()["detail"]
    
    def test_get_readings_time_range_reversed(self, client: TestClient):
        """시간 범위 역전"""
        response = client.get(
            "/api/v1/readings"
            "?sensor_from=2024-05-23T10:00:00Z"
            "&sensor_to=2024-05-23T08:00:00Z"
        )
        
        assert response.status_code == 400
        assert "sensor_from must be less than or equal to sensor_to" in response.json()["detail"]
    
    def test_get_readings_stable_sort(self, client: TestClient):
        """동일 sensor_timestamp에서 안정 정렬"""
        # 같은 시각의 데이터 2개 저장
        same_time_data = [
            {
                "serial_number": "SAME-TIME-001",
                "timestamp": "2024-05-23T12:00:00Z",
                "mode": "NORMAL",
                "temperature": 24.0,
                "humidity": 50.0,
                "pressure": 1013.0,
                "location": {"lat": 37.0, "lng": 127.0},
                "air_quality": 40
            },
            {
                "serial_number": "SAME-TIME-002",
                "timestamp": "2024-05-23T12:00:00Z",  # 같은 시각
                "mode": "NORMAL",
                "temperature": 25.0,
                "humidity": 51.0,
                "pressure": 1014.0,
                "location": {"lat": 38.0, "lng": 128.0},
                "air_quality": 45
            },
        ]
        
        for reading in same_time_data:
            resp = client.post("/api/v1/readings", json=reading)
            assert resp.status_code == 201
        
        # 조회 - 같은 시각의 데이터들
        response = client.get("/api/v1/readings?sensor_from=2024-05-23T12:00:00Z&sensor_to=2024-05-23T12:00:00Z")
        
        assert response.status_code == 200
        data = response.json()
        
        # 같은 시각의 데이터들이 id DESC로 정렬되어야 함
        same_time_readings = [r for r in data["data"] if "SAME-TIME" in r["serial_number"]]
        assert len(same_time_readings) == 2
        
        # id DESC 순으로 정렬되었는지 확인 (먼저 저장된 것이 나중에 조회됨)
        ids = [r["id"] for r in same_time_readings]
        assert ids[0] > ids[1]


class TestKSTTimezoneQuery:
    """KST 타임존 쿼리 테스트"""
    
    def test_get_readings_kst_timestamp_normalized(self, client: TestClient):
        """KST timestamp가 UTC로 정규화되어 저장되고 조회됨"""
        # KST 데이터 저장
        kst_data = {
            "serial_number": "KST-QUERY-001",
            "timestamp": "2024-05-23T17:00:00+09:00",  # KST = UTC 08:00
            "mode": "NORMAL",
            "temperature": 24.0,
            "humidity": 50.0,
            "pressure": 1013.0,
            "location": {"lat": 37.0, "lng": 127.0},
            "air_quality": 40
        }
        
        resp = client.post("/api/v1/readings", json=kst_data)
        assert resp.status_code == 201
        
        # UTC 기준으로 조회
        response = client.get(
            "/api/v1/readings"
            "?serial_number=KST-QUERY-001"
            "&sensor_from=2024-05-23T08:00:00Z"
            "&sensor_to=2024-05-23T08:30:00Z"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        
        # 저장된 timestamp는 UTC로 정규화됨
        reading = data["data"][0]
        assert reading["timestamp"].startswith("2024-05-23T08:00:00")
        # raw_timestamp는 원본 KST 유지
        assert reading["raw_timestamp"] == "2024-05-23T17:00:00+09:00"
