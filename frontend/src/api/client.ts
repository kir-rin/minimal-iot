import axios from 'axios';
import type {
  SensorStatusResponse,
  ReadingQueryResponse,
  ModeChangeRequest,
  ModeChangeResponse,
  SensorFilters,
  ReadingFilters,
  SensorStatus,
  Reading,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true' || true; // MVP: 기본적으로 목업 사용

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.params);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// 목업 데이터
const mockSensors: SensorStatus[] = [
  {
    serial_number: 'SN-NORMAL-01',
    last_sensor_timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    last_server_received_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    last_reported_mode: 'NORMAL',
    health_status: 'HEALTHY',
    telemetry_status: 'FRESH',
    health_evaluated_at: new Date().toISOString(),
    last_reading_id: 1,
  },
  {
    serial_number: 'SN-EMERGENCY-01',
    last_sensor_timestamp: new Date(Date.now() - 20 * 1000).toISOString(),
    last_server_received_at: new Date(Date.now() - 20 * 1000).toISOString(),
    last_reported_mode: 'EMERGENCY',
    health_status: 'HEALTHY',
    telemetry_status: 'FRESH',
    health_evaluated_at: new Date().toISOString(),
    last_reading_id: 2,
  },
  {
    serial_number: 'SN-FAULTY-01',
    last_sensor_timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    last_server_received_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    last_reported_mode: 'NORMAL',
    health_status: 'FAULTY',
    telemetry_status: 'DELAYED',
    health_evaluated_at: new Date().toISOString(),
    last_reading_id: 3,
  },
];

const generateMockReadings = (serialNumber: string): Reading[] => {
  const readings: Reading[] = [];
  const now = new Date();
  
  for (let i = 0; i < 20; i++) {
    const timestamp = new Date(now.getTime() - i * 10 * 60 * 1000);
    readings.push({
      id: i + 1,
      serial_number: serialNumber,
      timestamp: timestamp.toISOString(),
      raw_timestamp: timestamp.toISOString(),
      server_received_at: new Date(timestamp.getTime() + 5000).toISOString(),
      mode: i % 3 === 0 ? 'EMERGENCY' : 'NORMAL',
      metrics: {
        temperature: 20 + Math.random() * 10,
        humidity: 40 + Math.random() * 30,
        pressure: 1000 + Math.random() * 20,
        air_quality: 30 + Math.random() * 50,
      },
      location: {
        lat: 37.5665 + (Math.random() - 0.5) * 0.01,
        lng: 126.978 + (Math.random() - 0.5) * 0.01,
      },
    });
  }
  
  return readings;
};

// Sensor APIs
export const sensorApi = {
  // Get sensor status list
  getStatus: async (filters?: SensorFilters): Promise<SensorStatusResponse> => {
    if (USE_MOCK) {
      console.log('[MOCK] getStatus', filters);
      let data = [...mockSensors];
      
      if (filters?.serial_number) {
        data = data.filter(s => s.serial_number.includes(filters.serial_number!));
      }
      if (filters?.health_status) {
        data = data.filter(s => s.health_status === filters.health_status);
      }
      
      return { success: true, data };
    }

    const params: Record<string, string> = {};
    if (filters?.serial_number) params.serial_number = filters.serial_number;
    if (filters?.health_status) params.health_status = filters.health_status;
    
    const response = await apiClient.get<SensorStatusResponse>('/api/v1/sensors/status', { params });
    return response.data;
  },

  // Change sensor mode
  changeMode: async (serialNumber: string, mode: 'NORMAL' | 'EMERGENCY'): Promise<ModeChangeResponse> => {
    if (USE_MOCK) {
      console.log('[MOCK] changeMode', { serialNumber, mode });
      const sensor = mockSensors.find(s => s.serial_number === serialNumber);
      if (sensor) {
        sensor.last_reported_mode = mode;
      }
      return {
        success: true,
        sensor_known: !!sensor,
        requested_mode: mode,
        requested_at: new Date().toISOString(),
        message: `Mode changed to ${mode}`,
      };
    }

    const body: ModeChangeRequest = { mode };
    const response = await apiClient.post<ModeChangeResponse>(`/api/v1/sensors/${serialNumber}/mode`, body);
    return response.data;
  },
};

// Reading APIs
export const readingApi = {
  // Get readings with filters
  getReadings: async (filters?: ReadingFilters): Promise<ReadingQueryResponse> => {
    if (USE_MOCK) {
      console.log('[MOCK] getReadings', filters);
      const readings = filters?.serial_number 
        ? generateMockReadings(filters.serial_number)
        : [];
      
      return {
        success: true,
        data: readings,
        pagination: {
          total_count: readings.length,
          current_page: 1,
          limit: 50,
          total_pages: 1,
          has_next_page: false,
          has_prev_page: false,
        },
      };
    }

    const params: Record<string, string | number> = {};
    
    if (filters?.serial_number) params.serial_number = filters.serial_number;
    if (filters?.mode) params.mode = filters.mode;
    if (filters?.sensor_from) params.sensor_from = filters.sensor_from;
    if (filters?.sensor_to) params.sensor_to = filters.sensor_to;
    if (filters?.received_from) params.received_from = filters.received_from;
    if (filters?.received_to) params.received_to = filters.received_to;
    if (filters?.page) params.page = filters.page;
    if (filters?.limit) params.limit = filters.limit;
    
    const response = await apiClient.get<ReadingQueryResponse>('/api/v1/readings', { params });
    return response.data;
  },
};
