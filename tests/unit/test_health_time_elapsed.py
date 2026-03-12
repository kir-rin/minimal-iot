"""Phase 6: 시간 경과에 따른 건강 상태 재평가 단위 테스트

NORMAL 모드: 12분 경과 시 FAULTY
EMERGENCY 모드: 30초 경과 시 FAULTY
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.domain.clock import FixedClock
from src.domain.status import evaluate_health_status, StatusThresholds
from src.domain.types import HealthStatus, Mode


@pytest.fixture
def base_time() -> datetime:
    """기준 시간: 2024-05-23 08:30 UTC"""
    return datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def fixed_clock(base_time: datetime) -> FixedClock:
    """고정된 시계"""
    return FixedClock(base_time)


class TestHealthEvaluationTimeElapsed:
    """시간 경과에 따른 건강 상태 평가 테스트"""

    def test_normal_mode_healthy_before_12_minutes(self, fixed_clock: FixedClock):
        """NORMAL 모드: 12분 미만 경과 시 HEALTHY"""
        last_received = fixed_clock.now() - timedelta(minutes=11, seconds=59)
        
        result = evaluate_health_status(
            last_mode=Mode.NORMAL,
            last_server_received_at=last_received,
            now=fixed_clock.now(),
        )
        
        assert result == HealthStatus.HEALTHY

    def test_normal_mode_faulty_at_exactly_12_minutes(self, fixed_clock: FixedClock):
        """NORMAL 모드: 정확히 12분 경과 시 FAULTY"""
        last_received = fixed_clock.now() - timedelta(minutes=12)
        
        result = evaluate_health_status(
            last_mode=Mode.NORMAL,
            last_server_received_at=last_received,
            now=fixed_clock.now(),
        )
        
        assert result == HealthStatus.FAULTY

    def test_normal_mode_faulty_after_12_minutes(self, fixed_clock: FixedClock):
        """NORMAL 모드: 12분 초과 경과 시 FAULTY"""
        last_received = fixed_clock.now() - timedelta(minutes=12, seconds=1)
        
        result = evaluate_health_status(
            last_mode=Mode.NORMAL,
            last_server_received_at=last_received,
            now=fixed_clock.now(),
        )
        
        assert result == HealthStatus.FAULTY

    def test_emergency_mode_healthy_before_30_seconds(self, fixed_clock: FixedClock):
        """EMERGENCY 모드: 30초 미만 경과 시 HEALTHY"""
        last_received = fixed_clock.now() - timedelta(seconds=29)
        
        result = evaluate_health_status(
            last_mode=Mode.EMERGENCY,
            last_server_received_at=last_received,
            now=fixed_clock.now(),
        )
        
        assert result == HealthStatus.HEALTHY

    def test_emergency_mode_faulty_at_exactly_30_seconds(self, fixed_clock: FixedClock):
        """EMERGENCY 모드: 정확히 30초 경과 시 FAULTY"""
        last_received = fixed_clock.now() - timedelta(seconds=30)
        
        result = evaluate_health_status(
            last_mode=Mode.EMERGENCY,
            last_server_received_at=last_received,
            now=fixed_clock.now(),
        )
        
        assert result == HealthStatus.FAULTY

    def test_emergency_mode_faulty_after_30_seconds(self, fixed_clock: FixedClock):
        """EMERGENCY 모드: 30초 초과 경과 시 FAULTY"""
        last_received = fixed_clock.now() - timedelta(seconds=31)
        
        result = evaluate_health_status(
            last_mode=Mode.EMERGENCY,
            last_server_received_at=last_received,
            now=fixed_clock.now(),
        )
        
        assert result == HealthStatus.FAULTY

    def test_maintenance_mode_uses_normal_threshold(self, fixed_clock: FixedClock):
        """MAINTENANCE 모드: NORMAL과 동일한 12분 임계값 사용"""
        last_received = fixed_clock.now() - timedelta(minutes=11)
        
        result = evaluate_health_status(
            last_mode=Mode.MAINTENANCE,
            last_server_received_at=last_received,
            now=fixed_clock.now(),
        )
        
        assert result == HealthStatus.HEALTHY

    def test_no_last_received_returns_unknown(self, fixed_clock: FixedClock):
        """마지막 수신 시간 없음: UNKNOWN 반환"""
        result = evaluate_health_status(
            last_mode=Mode.NORMAL,
            last_server_received_at=None,
            now=fixed_clock.now(),
        )
        
        assert result == HealthStatus.UNKNOWN

    def test_custom_thresholds_override_defaults(self, fixed_clock: FixedClock):
        """사용자 정의 임계값으로 기본값 재정의"""
        custom_thresholds = StatusThresholds(
            normal_health=timedelta(minutes=5),
            emergency_health=timedelta(seconds=10),
        )
        
        # 6분 경과 시 (기본 12분이면 HEALTHY, 커스텀 5분이면 FAULTY)
        last_received = fixed_clock.now() - timedelta(minutes=6)
        
        result = evaluate_health_status(
            last_mode=Mode.NORMAL,
            last_server_received_at=last_received,
            now=fixed_clock.now(),
            thresholds=custom_thresholds,
        )
        
        assert result == HealthStatus.FAULTY


class TestHealthStateTransitions:
    """건강 상태 전이 테스트 - 시간 진행 시뮬레이션"""

    def test_transition_from_healthy_to_faulty_over_time(self):
        """시간 진행에 따른 HEALTHY -> FAULTY 전이"""
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(base_time)
        last_received = base_time
        
        # 초기 상태: HEALTHY
        result = evaluate_health_status(
            last_mode=Mode.NORMAL,
            last_server_received_at=last_received,
            now=clock.now(),
        )
        assert result == HealthStatus.HEALTHY
        
        # 11분 59초 후: 여전히 HEALTHY
        clock.advance(minutes=11, seconds=59)
        result = evaluate_health_status(
            last_mode=Mode.NORMAL,
            last_server_received_at=last_received,
            now=clock.now(),
        )
        assert result == HealthStatus.HEALTHY
        
        # 2초 더 (총 12분 1초): FAULTY
        clock.advance(seconds=2)
        result = evaluate_health_status(
            last_mode=Mode.NORMAL,
            last_server_received_at=last_received,
            now=clock.now(),
        )
        assert result == HealthStatus.FAULTY

    def test_emergency_mode_transitions_faster(self):
        """EMERGENCY 모드는 더 빠르게 FAULTY로 전이"""
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(base_time)
        last_received = base_time
        
        # 29초 후: HEALTHY
        clock.advance(seconds=29)
        result = evaluate_health_status(
            last_mode=Mode.EMERGENCY,
            last_server_received_at=last_received,
            now=clock.now(),
        )
        assert result == HealthStatus.HEALTHY
        
        # 2초 더 (총 31초): FAULTY
        clock.advance(seconds=2)
        result = evaluate_health_status(
            last_mode=Mode.EMERGENCY,
            last_server_received_at=last_received,
            now=clock.now(),
        )
        assert result == HealthStatus.FAULTY
