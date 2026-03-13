import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sensorApi, readingApi } from '../api/client';
import type { SensorFilters, ReadingFilters } from '../types';

// Query keys
export const queryKeys = {
  sensors: {
    all: ['sensors'] as const,
    status: (filters?: SensorFilters) => ['sensors', 'status', filters] as const,
  },
  readings: {
    all: ['readings'] as const,
    list: (filters?: ReadingFilters) => ['readings', 'list', filters] as const,
  },
};

// Sensor Hooks
export const useSensorStatus = (filters?: SensorFilters) => {
  return useQuery({
    queryKey: queryKeys.sensors.status(filters),
    queryFn: () => sensorApi.getStatus(filters),
    refetchInterval: 30000, // 30초마다 자동 갱신
    staleTime: 10000, // 10초간 fresh 상태 유지
  });
};

export const useChangeMode = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ serialNumber, mode }: { serialNumber: string; mode: 'NORMAL' | 'EMERGENCY' }) =>
      sensorApi.changeMode(serialNumber, mode),
    onSuccess: () => {
      // 성공 시 센서 목록 캐시 무효화
      queryClient.invalidateQueries({ queryKey: queryKeys.sensors.all });
    },
  });
};

// Reading Hooks
export const useReadings = (filters?: ReadingFilters) => {
  return useQuery({
    queryKey: queryKeys.readings.list(filters),
    queryFn: () => readingApi.getReadings(filters),
    staleTime: 10000,
  });
};
