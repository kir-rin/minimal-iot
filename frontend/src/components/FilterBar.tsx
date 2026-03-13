import { useState } from 'react';
import { Search, Filter, X } from 'lucide-react';
import type { SensorFilters } from '../types';

interface FilterBarProps {
  filters: SensorFilters;
  onFiltersChange: (filters: SensorFilters) => void;
}

export function FilterBar({ filters, onFiltersChange }: FilterBarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [localFilters, setLocalFilters] = useState<SensorFilters>(filters);

  const handleApply = () => {
    onFiltersChange(localFilters);
    setIsOpen(false);
  };

  const handleClear = () => {
    setLocalFilters({});
    onFiltersChange({});
    setIsOpen(false);
  };

  const hasActiveFilters = filters.serial_number || filters.health_status;

  return (
    <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
      {/* 검색 바 */}
      <div className="flex items-center gap-2 p-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="시리얼 번호 검색..."
            className="w-full pl-10 pr-4 py-2 bg-gray-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            value={localFilters.serial_number || ''}
            onChange={(e) => setLocalFilters({ ...localFilters, serial_number: e.target.value })}
            onKeyDown={(e) => e.key === 'Enter' && handleApply()}
          />
        </div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`p-2 rounded-lg transition-colors ${
            hasActiveFilters ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
          }`}
        >
          <Filter className="w-5 h-5" />
        </button>
      </div>

      {/* 필터 드로어 */}
      {isOpen && (
        <div className="border-t border-gray-200 p-4 space-y-4">
          {/* 상태 필터 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              상태
            </label>
            <div className="flex gap-2">
              {(['HEALTHY', 'FAULTY'] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setLocalFilters({
                    ...localFilters,
                    health_status: localFilters.health_status === status ? undefined : status
                  })}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    localFilters.health_status === status
                      ? status === 'HEALTHY'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {status === 'HEALTHY' ? '정상' : '고장'}
                </button>
              ))}
            </div>
          </div>

          {/* 버튼 */}
          <div className="flex gap-2 pt-2">
            <button
              onClick={handleApply}
              className="flex-1 py-2 bg-green-500 text-white rounded-lg text-sm font-medium hover:bg-green-600 transition-colors"
            >
              적용
            </button>
            <button
              onClick={handleClear}
              className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
            >
              초기화
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
