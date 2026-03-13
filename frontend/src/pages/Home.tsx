import { useState } from 'react';
import { Bell, Menu } from 'lucide-react';
import { useSensorStatus } from '../hooks/useApi';
import { FilterBar } from '../components/FilterBar';
import { SensorList } from '../components/SensorList';
import type { SensorFilters } from '../types';

interface HomeProps {
  onSensorClick: (serialNumber: string) => void;
}

export function Home({ onSensorClick }: HomeProps) {
  const [filters, setFilters] = useState<SensorFilters>({});
  const { data, isLoading, error } = useSensorStatus(filters);

  const sensors = data?.data || [];
  const healthyCount = sensors.filter(s => s.health_status === 'HEALTHY').length;
  const faultyCount = sensors.filter(s => s.health_status === 'FAULTY').length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <button className="p-2 -ml-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            <Menu className="w-6 h-6" />
          </button>
          <h1 className="text-lg font-semibold text-gray-900">센서 모니터링</h1>
          <button className="p-2 -mr-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            <Bell className="w-6 h-6" />
          </button>
        </div>
      </header>

      {/* 환영 메시지 */}
      <div className="px-4 py-4">
        <p className="text-gray-600">
          안녕하세요, <span className="text-green-600 font-semibold">관리자</span>님
        </p>
      </div>

      {/* 상태 요약 */}
      <div className="px-4 pb-4">
        <div className="flex gap-3">
          <div className="flex-1 bg-white rounded-xl p-4 border border-gray-100">
            <p className="text-sm text-gray-500 mb-1">정상</p>
            <p className="text-2xl font-bold text-green-600">{healthyCount}</p>
          </div>
          <div className="flex-1 bg-white rounded-xl p-4 border border-gray-100">
            <p className="text-sm text-gray-500 mb-1">고장</p>
            <p className="text-2xl font-bold text-red-600">{faultyCount}</p>
          </div>
        </div>
      </div>

      {/* 필터 */}
      <FilterBar filters={filters} onFiltersChange={setFilters} />

      {/* 센서 목록 */}
      <div className="px-4 py-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full animate-spin" />
            <p className="mt-4 text-gray-500">센서 정보를 불러오는 중...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-12 text-red-500">
            <p className="text-lg font-medium mb-2">오류가 발생했습니다</p>
            <p className="text-sm">{error instanceof Error ? error.message : '알 수 없는 오류'}</p>
          </div>
        ) : (
          <SensorList sensors={sensors} onSensorClick={onSensorClick} />
        )}
      </div>
    </div>
  );
}
