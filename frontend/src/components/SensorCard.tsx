import { useState } from 'react';
import { Activity, Thermometer, Droplets, AlertCircle } from 'lucide-react';
import type { SensorStatus } from '../types';
import { formatRelativeTime } from '../utils/time';
import { useChangeMode } from '../hooks/useApi';

interface SensorCardProps {
  sensor: SensorStatus;
  onClick?: () => void;
}

export function SensorCard({ sensor, onClick }: SensorCardProps) {
  const [isToggling, setIsToggling] = useState(false);
  const changeMode = useChangeMode();

  const isHealthy = sensor.health_status === 'HEALTHY';
  const isEmergency = sensor.last_reported_mode === 'EMERGENCY';

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isToggling) return;

    setIsToggling(true);
    const newMode = isEmergency ? 'NORMAL' : 'EMERGENCY';
    
    try {
      await changeMode.mutateAsync({
        serialNumber: sensor.serial_number,
        mode: newMode,
      });
    } catch (error) {
      console.error('Failed to change mode:', error);
      alert('모드 변경에 실패했습니다.');
    } finally {
      setIsToggling(false);
    }
  };

  return (
    <div 
      className="sensor-card cursor-pointer"
      onClick={onClick}
    >
      {/* 헤더: 센서명 + 상태 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-gray-600" />
          <span className="font-semibold text-gray-900">{sensor.serial_number}</span>
        </div>
        <span className={isHealthy ? 'badge-healthy' : 'badge-faulty'}>
          {isHealthy ? '정상' : '고장'}
        </span>
      </div>

      {/* 모드 + 마지막 수신 시간 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={isEmergency ? 'badge-mode-emergency' : 'badge-mode-normal'}>
            {isEmergency ? '긴급' : '일반'}
          </span>
          {sensor.telemetry_status !== 'FRESH' && (
            <span className="flex items-center gap-1 text-xs text-amber-600">
              <AlertCircle className="w-3 h-3" />
              {sensor.telemetry_status === 'DELAYED' && '지연'}
              {sensor.telemetry_status === 'CLOCK_SKEW' && '시계오차'}
              {sensor.telemetry_status === 'OUT_OF_ORDER' && '순서이상'}
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500">
          {formatRelativeTime(sensor.last_server_received_at)}
        </span>
      </div>

      {/* 메트릭 미리보기 */}
      <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
        <div className="flex items-center gap-1">
          <Thermometer className="w-4 h-4" />
          <span>{sensor.temperature !== undefined ? `${sensor.temperature.toFixed(1)}°C` : '--°C'}</span>
        </div>
        <div className="flex items-center gap-1">
          <Droplets className="w-4 h-4" />
          <span>{sensor.humidity !== undefined ? `${sensor.humidity.toFixed(1)}%` : '--%'}</span>
        </div>
      </div>

      {/* 모드 변경 토글 */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <span className="text-sm text-gray-600">모드 변경</span>
        <button
          onClick={handleToggle}
          disabled={isToggling}
          className={`toggle ${isEmergency ? 'active' : ''}`}
        >
          <div className="toggle-circle" />
        </button>
      </div>
    </div>
  );
}
