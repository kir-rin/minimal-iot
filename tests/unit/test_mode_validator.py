"""모드 변경 검증 단위 테스트"""
from __future__ import annotations

import pytest

from src.domain.types import Mode


class TestModeValidation:
    """모드 값 검증 테스트"""
    
    def test_valid_modes(self):
        """유효한 모드 값"""
        valid_modes = ["NORMAL", "EMERGENCY", "MAINTENANCE"]
        
        for mode in valid_modes:
            # Mode Enum 변환 시도
            result = Mode(mode)
            assert result is not None
            assert result.value == mode
    
    def test_invalid_mode_raises_error(self):
        """유효하지 않은 모드 값은 에러"""
        invalid_modes = ["invalid", "normal", "Emergency", "", "UNKNOWN", "STANDBY"]
        
        for mode in invalid_modes:
            with pytest.raises(ValueError):
                Mode(mode)
    
    def test_mode_enum_values(self):
        """Mode Enum 값 확인"""
        assert Mode.NORMAL.value == "NORMAL"
        assert Mode.EMERGENCY.value == "EMERGENCY"
        assert Mode.MAINTENANCE.value == "MAINTENANCE"
    
    def test_mode_case_sensitivity(self):
        """모드 값은 대소문자 구분"""
        # 대문자만 유효
        assert Mode("NORMAL") == Mode.NORMAL
        
        # 소문자는 유효하지 않음
        with pytest.raises(ValueError):
            Mode("normal")
        
        with pytest.raises(ValueError):
            Mode("Normal")
    
    def test_mode_from_reading_validation(self):
        """reading에서 모드 값 추출 및 검증"""
        # 유효한 모드
        assert Mode("NORMAL") == Mode.NORMAL
        assert Mode("EMERGENCY") == Mode.EMERGENCY
        
        # 센서에서 오는 mode 값과 API 요청의 mode 값은 동일한 Enum 사용
        reading_modes = ["NORMAL", "EMERGENCY"]  # 센서가 보내는 모드
        request_modes = ["NORMAL", "EMERGENCY", "MAINTENANCE"]  # API 요청 가능 모드
        
        # 모든 센서 모드는 요청 모드에 포함
        for m in reading_modes:
            assert m in [rm.value for rm in Mode]
