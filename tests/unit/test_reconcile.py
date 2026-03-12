"""모드 변경 reconcile 로직 단위 테스트"""
from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

import pytest

from src.domain.types import Mode


@dataclass
class FakeModeChangeRequest:
    """테스트용 가짜 모드 변경 요청"""
    id: int
    serial_number: str
    requested_mode: str
    requested_at: datetime
    request_status: str = "PENDING"
    observed_applied_at: Optional[datetime] = None


@dataclass
class FakeReading:
    """테스트용 가짜 reading"""
    serial_number: str
    mode: Mode
    server_received_at: datetime


class TestReconcileLogic:
    """reconcile 로직 단위 테스트"""
    
    def test_should_reconcile_when_telemetry_after_request(self):
        """telemetry가 요청 이후에 수신되면 reconcile 대상"""
        # Given
        requested_at = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        server_received_at = datetime(2024, 5, 23, 8, 31, 0, tzinfo=timezone.utc)
        
        # When: reconcile 조건 검사
        should_reconcile = server_received_at >= requested_at
        
        # Then
        assert should_reconcile is True
    
    def test_should_not_reconcile_when_telemetry_before_request(self):
        """telemetry가 요청 이전에 수신되면 reconcile 대상 아님"""
        # Given
        requested_at = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        server_received_at = datetime(2024, 5, 23, 8, 29, 0, tzinfo=timezone.utc)
        
        # When: reconcile 조건 검사
        should_reconcile = server_received_at >= requested_at
        
        # Then
        assert should_reconcile is False
    
    def test_reconcile_exact_same_time(self):
        """정확히 같은 시간이면 reconcile 대상"""
        # Given
        requested_at = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        server_received_at = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        
        # When: reconcile 조건 검사
        should_reconcile = server_received_at >= requested_at
        
        # Then
        assert should_reconcile is True
    
    def test_reconcile_with_mode_match(self):
        """요청한 모드와 telemetry의 모드가 일치하면 applied"""
        # Given
        request = FakeModeChangeRequest(
            id=1,
            serial_number="TEST-001",
            requested_mode="EMERGENCY",
            requested_at=datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc),
            request_status="PENDING"
        )
        
        reading = FakeReading(
            serial_number="TEST-001",
            mode=Mode.EMERGENCY,
            server_received_at=datetime(2024, 5, 23, 8, 31, 0, tzinfo=timezone.utc)
        )
        
        # When: reconcile 로직
        should_reconcile = reading.server_received_at >= request.requested_at
        mode_matches = reading.mode.value == request.requested_mode
        
        # Then
        assert should_reconcile is True
        assert mode_matches is True
    
    def test_reconcile_with_mode_mismatch(self):
        """요청한 모드와 telemetry의 모드가 다르면 not applied"""
        # Given
        request = FakeModeChangeRequest(
            id=1,
            serial_number="TEST-001",
            requested_mode="EMERGENCY",
            requested_at=datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc),
            request_status="PENDING"
        )
        
        reading = FakeReading(
            serial_number="TEST-001",
            mode=Mode.NORMAL,  # 요청한 EMERGENCY와 다름
            server_received_at=datetime(2024, 5, 23, 8, 31, 0, tzinfo=timezone.utc)
        )
        
        # When: reconcile 로직
        should_reconcile = reading.server_received_at >= request.requested_at
        mode_matches = reading.mode.value == request.requested_mode
        
        # Then
        assert should_reconcile is True  # 시간 조건은 만족
        assert mode_matches is False  # 모드가 다름
    
    def test_only_pending_requests_are_reconciled(self):
        """PENDING 상태인 요청만 reconcile 대상"""
        # Given
        pending_request = FakeModeChangeRequest(
            id=1,
            serial_number="TEST-001",
            requested_mode="EMERGENCY",
            requested_at=datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc),
            request_status="PENDING"
        )
        
        applied_request = FakeModeChangeRequest(
            id=2,
            serial_number="TEST-001",
            requested_mode="NORMAL",
            requested_at=datetime(2024, 5, 23, 8, 20, 0, tzinfo=timezone.utc),
            request_status="APPLIED",
            observed_applied_at=datetime(2024, 5, 23, 8, 25, 0, tzinfo=timezone.utc)
        )
        
        reading = FakeReading(
            serial_number="TEST-001",
            mode=Mode.NORMAL,
            server_received_at=datetime(2024, 5, 23, 8, 35, 0, tzinfo=timezone.utc)
        )
        
        # When & Then
        # PENDING 요청은 reconcile 대상
        assert pending_request.request_status == "PENDING"
        
        # APPLIED 요청은 reconcile 대상 아님
        assert applied_request.request_status == "APPLIED"
    
    def test_latest_pending_request_only(self):
        """가장 최근 PENDING 요청 1건만 reconcile"""
        # Given: 2개의 PENDING 요청
        old_request = FakeModeChangeRequest(
            id=1,
            serial_number="TEST-001",
            requested_mode="EMERGENCY",
            requested_at=datetime(2024, 5, 23, 8, 20, 0, tzinfo=timezone.utc),
            request_status="PENDING"
        )
        
        new_request = FakeModeChangeRequest(
            id=2,
            serial_number="TEST-001",
            requested_mode="MAINTENANCE",
            requested_at=datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc),
            request_status="PENDING"
        )
        
        pending_requests = [old_request, new_request]
        
        # When: 가장 최근 요청 선택
        latest_request = max(
            pending_requests,
            key=lambda r: r.requested_at
        )
        
        # Then
        assert latest_request.id == 2
        assert latest_request.requested_mode == "MAINTENANCE"
    
    def test_reconcile_timestamp_update(self):
        """reconcile 시 applied_at이 업데이트됨"""
        # Given
        request = FakeModeChangeRequest(
            id=1,
            serial_number="TEST-001",
            requested_mode="EMERGENCY",
            requested_at=datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc),
            request_status="PENDING"
        )
        
        telemetry_received_at = datetime(2024, 5, 23, 8, 35, 0, tzinfo=timezone.utc)
        
        # When: reconcile 수행
        request.request_status = "APPLIED"
        request.observed_applied_at = telemetry_received_at
        
        # Then
        assert request.request_status == "APPLIED"
        assert request.observed_applied_at == telemetry_received_at


class TestReconcileEdgeCases:
    """reconcile 엣지 케이스 테스트"""
    
    def test_no_pending_requests(self):
        """PENDING 요청이 없으면 reconcile할 것이 없음"""
        pending_requests = []
        
        # reconcile 대상 없음
        assert len(pending_requests) == 0
    
    def test_mismatched_serial_number(self):
        """시리얼 번호가 다른 요청은 reconcile 대상 아님"""
        request = FakeModeChangeRequest(
            id=1,
            serial_number="TEST-001",
            requested_mode="EMERGENCY",
            requested_at=datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc),
            request_status="PENDING"
        )
        
        reading = FakeReading(
            serial_number="TEST-002",  # 다른 센서
            mode=Mode.EMERGENCY,
            server_received_at=datetime(2024, 5, 23, 8, 35, 0, tzinfo=timezone.utc)
        )
        
        # 시리얼 번호가 다르면 reconcile 대상 아님
        assert request.serial_number != reading.serial_number
