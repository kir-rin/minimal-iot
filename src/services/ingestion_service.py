from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.domain.clock import Clock
from src.domain.types import (
    BatchDecision,
    HealthStatus,
    IngestMode,
    NormalizedReading,
    RecordValidationResult,
    TelemetryStatus,
    ValidationError,
)
from src.domain.status import evaluate_health_status, evaluate_telemetry_status
from src.domain.validation import validate_reading, validate_top_level_payload
from src.models.reading import Reading
from src.repositories.reading_repository import ReadingRepository
from src.repositories.sensor_status_repository import SensorStatusRepository


class IngestionService:
    """센서 데이터 수집 서비스"""
    
    def __init__(
        self,
        session: Session,
        clock: Clock,
    ):
        self._session = session
        self._clock = clock
        self._reading_repo = ReadingRepository(session)
        self._status_repo = SensorStatusRepository(session)
    
    def ingest(
        self,
        payload: Any,
        ingest_mode: IngestMode = IngestMode.ATOMIC,
    ) -> BatchDecision:
        """센서 데이터 수집"""
        # 1. 최상위 payload 검증
        top_level_result = validate_top_level_payload(payload)
        if not top_level_result.is_valid:
            return BatchDecision(
                success=False,
                ingest_mode=ingest_mode,
                accepted_count=0,
                rejected_count=1,
                errors=top_level_result.errors,
                accepted_records=[],
                is_request_level_error=True,
            )
        
        records = top_level_result.records
        
        # 빈 배열 처리
        if len(records) == 0:
            return BatchDecision(
                success=True,
                ingest_mode=ingest_mode,
                accepted_count=0,
                rejected_count=0,
                errors=[],
                accepted_records=[],
            )
        
        # 2. 각 레코드 검증
        validation_results: list[RecordValidationResult] = []
        for idx, record in enumerate(records):
            result = validate_reading(record)
            if not result.accepted and result.error:
                result.error.index = idx
            validation_results.append(result)
        
        # 3. 정책별 처리
        if ingest_mode == IngestMode.ATOMIC:
            return self._process_atomic(validation_results)
        else:  # PARTIAL
            return self._process_partial(validation_results)
    
    def _process_atomic(self, results: list[RecordValidationResult]) -> BatchDecision:
        """Atomic 정책 처리 - 전체 성공 또는 전체 실패"""
        failed_results = [r for r in results if not r.accepted]
        
        if failed_results:
            # 하나라도 실패하면 전체 실패
            errors = [r.error for r in failed_results if r.error]
            return BatchDecision(
                success=False,
                ingest_mode=IngestMode.ATOMIC,
                accepted_count=0,
                rejected_count=len(failed_results),
                errors=errors,
                accepted_records=[],
            )
        
        # 전체 성공 - 저장
        accepted_readings = [r.reading for r in results if r.reading]
        server_received_at = self._clock.now()
        
        try:
            for reading in accepted_readings:
                self._save_reading_and_update_status(reading, server_received_at)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        
        return BatchDecision(
            success=True,
            ingest_mode=IngestMode.ATOMIC,
            accepted_count=len(accepted_readings),
            rejected_count=0,
            errors=[],
            accepted_records=accepted_readings,
        )
    
    def _process_partial(self, results: list[RecordValidationResult]) -> BatchDecision:
        """Partial 정책 처리 - 일부 성공/일부 실패 허용"""
        accepted_readings: list[NormalizedReading] = []
        errors: list[ValidationError] = []
        
        server_received_at = self._clock.now()
        
        # 성공한 레코드 먼저 저장
        for result in results:
            if result.accepted and result.reading:
                try:
                    self._save_reading_and_update_status(result.reading, server_received_at)
                    accepted_readings.append(result.reading)
                except Exception as e:
                    # 저장 실패 시 record-level error
                    if result.error:
                        result.error.reason = f"Storage failed: {str(e)}"
                        errors.append(result.error)
            elif result.error:
                errors.append(result.error)
        
        # 커밋 (부분 성공은 롤백하지 않음)
        self._session.commit()
        
        # 성공 여부: 하나라도 성공했으면 True
        success = len(accepted_readings) > 0
        
        return BatchDecision(
            success=success,
            ingest_mode=IngestMode.PARTIAL,
            accepted_count=len(accepted_readings),
            rejected_count=len(errors),
            errors=errors,
            accepted_records=accepted_readings,
        )
    
    def _save_reading_and_update_status(
        self,
        reading: NormalizedReading,
        server_received_at: datetime,
    ) -> Reading:
        """Reading 저장 및 SensorStatus 갱신"""
        # 1. Reading 저장
        db_reading = self._reading_repo.create(reading, server_received_at)
        
        # 2. 기존 상태 조회 (OUT_OF_ORDER 판단용)
        existing_status = self._status_repo.get_by_serial_number(reading.serial_number)
        last_sensor_timestamp = (
            existing_status.last_sensor_timestamp if existing_status else None
        )
        
        # 3. Telemetry status 평가
        telemetry_status = evaluate_telemetry_status(
            sensor_timestamp=reading.sensor_timestamp,
            server_received_at=server_received_at,
            last_sensor_timestamp=last_sensor_timestamp,
        )
        
        # 4. Health status 평가 (항상 HEALTHY로 설정 - 데이터가 도착했으므로)
        health_status = HealthStatus.HEALTHY
        
        # 5. OUT_OFORDER 여부 판단
        is_out_of_order = telemetry_status == TelemetryStatus.OUT_OF_ORDER
        
        # 6. SensorStatus 갱신
        self._status_repo.upsert(
            reading=reading,
            reading_id=db_reading.id,
            server_received_at=server_received_at,
            health_status=health_status,
            telemetry_status=telemetry_status,
            is_out_of_order=is_out_of_order,
        )
        
        return db_reading
