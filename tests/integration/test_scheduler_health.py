"""Phase 6: Scheduler 통합 테스트

스케줄러가 DB의 모든 센서 상태를 재평가하고,
시간 경과에 따라 FAULTY 상태로 전환하는지 검증
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.clock import FixedClock
from src.domain.types import Mode, HealthStatus
from src.models.reading import Reading
from src.models.sensor_status import SensorCurrentStatus
from src.schedulers.health_evaluation_job import HealthEvaluationJob
from src.repositories.sensor_status_repository import SensorStatusRepository


class TestHealthEvaluationJob:
    """HealthEvaluationJob 통합 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_evaluates_all_sensors(
        self, async_db_session: AsyncSession, setup_multiple_sensors
    ):
        """스케줄러가 모든 센서를 재평가하는지 검증"""
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        # 13분 경과 (NORMAL 모드 임계값 초과)
        current_time = base_time + timedelta(minutes=13)
        clock = FixedClock(current_time)
        
        # 스케줄러 생성 및 실행
        job = HealthEvaluationJob(async_db_session, clock)
        result = await job.evaluate_all_sensors()
        
        # 모든 센서가 재평가되었는지 확인
        assert result["evaluated_count"] == 3
        
        # DB에서 상태 확인
        repo = SensorStatusRepository(async_db_session)
        statuses = await repo.get_all()
        
        # 모든 센서가 FAULTY로 변경되었는지 확인 (13분 경과)
        assert len(statuses) == 3
        for status in statuses:
            assert status.health_status == HealthStatus.FAULTY.value
            # SQLite stores without timezone, so compare ignoring timezone
            assert status.health_evaluated_at.replace(tzinfo=None) == current_time.replace(tzinfo=None)

    @pytest.mark.asyncio
    async def test_normal_mode_not_faulty_before_12_minutes(
        self, async_db_session: AsyncSession, setup_sensor_with_reading
    ):
        """NORMAL 모드: 12분 미만은 HEALTHY 유지"""
        serial_number, _ = setup_sensor_with_reading
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        # 11분 경과
        current_time = base_time + timedelta(minutes=11)
        clock = FixedClock(current_time)
        
        job = HealthEvaluationJob(async_db_session, clock)
        await job.evaluate_all_sensors()
        
        # 상태 확인
        repo = SensorStatusRepository(async_db_session)
        status = await repo.get_by_serial_number(serial_number)
        
        assert status is not None
        assert status.health_status == HealthStatus.HEALTHY.value

    @pytest.mark.asyncio
    async def test_normal_mode_faulty_after_12_minutes(
        self, async_db_session: AsyncSession, setup_sensor_with_reading
    ):
        """NORMAL 모드: 12분 초과 시 FAULTY로 전환"""
        serial_number, _ = setup_sensor_with_reading
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        # 13분 경과
        current_time = base_time + timedelta(minutes=13)
        clock = FixedClock(current_time)
        
        job = HealthEvaluationJob(async_db_session, clock)
        await job.evaluate_all_sensors()
        
        # 상태 확인
        repo = SensorStatusRepository(async_db_session)
        status = await repo.get_by_serial_number(serial_number)
        
        assert status is not None
        assert status.health_status == HealthStatus.FAULTY.value
        # SQLite stores without timezone, so compare ignoring timezone
        assert status.health_evaluated_at.replace(tzinfo=None) == current_time.replace(tzinfo=None)

    @pytest.mark.asyncio
    async def test_emergency_mode_faulty_after_30_seconds(
        self, async_db_session: AsyncSession
    ):
        """EMERGENCY 모드: 30초 초과 시 FAULTY로 전환"""
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        serial_number = "EMERGENCY-SENSOR"
        
        # EMERGENCY 모드 reading 생성
        reading = Reading(
            serial_number=serial_number,
            raw_timestamp="2024-05-23T08:30:00+00:00",
            sensor_timestamp=base_time,
            server_received_at=base_time,
            mode=Mode.EMERGENCY.value,
            temperature=25.0,
            humidity=60.0,
            pressure=1013.0,
            latitude=37.5665,
            longitude=126.9780,
            air_quality=50,
        )
        async_db_session.add(reading)
        await async_db_session.flush()
        
        status = SensorCurrentStatus(
            serial_number=serial_number,
            last_sensor_timestamp=base_time,
            last_server_received_at=base_time,
            last_reported_mode=Mode.EMERGENCY.value,
            health_status=HealthStatus.HEALTHY.value,
            telemetry_status="FRESH",
            health_evaluated_at=base_time,
            last_reading_id=reading.id,
        )
        async_db_session.add(status)
        await async_db_session.commit()
        
        # 35초 경과
        current_time = base_time + timedelta(seconds=35)
        clock = FixedClock(current_time)
        
        job = HealthEvaluationJob(async_db_session, clock)
        await job.evaluate_all_sensors()
        
        # 상태 확인
        repo = SensorStatusRepository(async_db_session)
        updated_status = await repo.get_by_serial_number(serial_number)
        
        assert updated_status is not None
        assert updated_status.health_status == HealthStatus.FAULTY.value

    @pytest.mark.asyncio
    async def test_scheduler_returns_transition_summary(
        self, async_db_session: AsyncSession, setup_multiple_sensors
    ):
        """스케줄러 실행 결과에 상태 전이 요약 포함"""
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        current_time = base_time + timedelta(minutes=13)
        clock = FixedClock(current_time)
        
        job = HealthEvaluationJob(async_db_session, clock)
        result = await job.evaluate_all_sensors()
        
        # 결과에 필요한 정보 포함
        assert "evaluated_count" in result
        assert "transitioned_to_faulty" in result
        assert result["transitioned_to_faulty"] == 3
        assert "failed_count" in result  # 에러 처리 결과 포함

    @pytest.mark.asyncio
    async def test_empty_database_no_error(self, async_db_session: AsyncSession):
        """센서가 없어도 오류 없이 완료"""
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        clock = FixedClock(base_time)
        
        job = HealthEvaluationJob(async_db_session, clock)
        result = await job.evaluate_all_sensors()
        
        assert result["evaluated_count"] == 0
        assert result["transitioned_to_faulty"] == 0
        assert result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_sensor_already_faulty_stays_faulty(
        self, async_db_session: AsyncSession, setup_sensor_with_reading
    ):
        """이미 FAULTY인 센서는 FAULTY 유지"""
        serial_number, _ = setup_sensor_with_reading
        
        # FAULTY로 설정
        repo = SensorStatusRepository(async_db_session)
        status = await repo.get_by_serial_number(serial_number)
        assert status is not None
        status.health_status = HealthStatus.FAULTY.value
        await async_db_session.commit()
        
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        # 20분 경과 (이미 오래 전에 FAULTY)
        current_time = base_time + timedelta(minutes=20)
        clock = FixedClock(current_time)
        
        job = HealthEvaluationJob(async_db_session, clock)
        result = await job.evaluate_all_sensors()
        
        # 여전히 FAULTY
        updated_status = await repo.get_by_serial_number(serial_number)
        assert updated_status is not None
        assert updated_status.health_status == HealthStatus.FAULTY.value
        assert result["transitioned_to_faulty"] == 0  # 새로 전환된 것 없음

    @pytest.mark.asyncio
    async def test_scheduler_updates_health_evaluated_at(
        self, async_db_session: AsyncSession, setup_sensor_with_reading
    ):
        """스케줄러 실행 시 health_evaluated_at 갱신"""
        serial_number, _ = setup_sensor_with_reading
        base_time = datetime(2024, 5, 23, 8, 30, 0, tzinfo=timezone.utc)
        current_time = base_time + timedelta(minutes=13)
        clock = FixedClock(current_time)
        
        job = HealthEvaluationJob(async_db_session, clock)
        await job.evaluate_all_sensors()
        
        repo = SensorStatusRepository(async_db_session)
        status = await repo.get_by_serial_number(serial_number)
        
        assert status is not None
        # SQLite stores without timezone, so compare ignoring timezone
        assert status.health_evaluated_at.replace(tzinfo=None) == current_time.replace(tzinfo=None)
