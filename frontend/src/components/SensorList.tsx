import { SensorCard } from './SensorCard';
import type { SensorStatus } from '../types';

interface SensorListProps {
  sensors: SensorStatus[];
  onSensorClick: (serialNumber: string) => void;
}

export function SensorList({ sensors, onSensorClick }: SensorListProps) {
  if (sensors.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-500">
        <p className="text-lg font-medium mb-2">등록된 센서가 없습니다</p>
        <p className="text-sm">센서에서 데이터가 수신되면 자동으로 표시됩니다</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sensors.map((sensor) => (
        <SensorCard
          key={sensor.serial_number}
          sensor={sensor}
          onClick={() => onSensorClick(sensor.serial_number)}
        />
      ))}
    </div>
  );
}
