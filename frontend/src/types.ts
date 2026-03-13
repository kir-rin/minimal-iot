// API Response Types

export interface SensorStatus {
  serial_number: string;
  last_sensor_timestamp: string;
  last_server_received_at: string;
  last_reported_mode: 'NORMAL' | 'EMERGENCY';
  health_status: 'HEALTHY' | 'FAULTY';
  telemetry_status: 'FRESH' | 'DELAYED' | 'CLOCK_SKEW' | 'OUT_OF_ORDER';
  health_evaluated_at: string;
  last_reading_id: number;
  temperature?: number;
  humidity?: number;
  pressure?: number;
  air_quality?: number;
}

export interface SensorStatusResponse {
  success: boolean;
  data: SensorStatus[];
}

export interface ReadingMetrics {
  temperature: number;
  humidity: number;
  pressure: number;
  air_quality: number;
}

export interface ReadingLocation {
  lat: number;
  lng: number;
}

export interface Reading {
  id: number;
  serial_number: string;
  timestamp: string;
  raw_timestamp: string;
  server_received_at: string;
  mode: 'NORMAL' | 'EMERGENCY';
  metrics: ReadingMetrics;
  location: ReadingLocation;
}

export interface Pagination {
  total_count: number;
  current_page: number;
  limit: number;
  total_pages: number;
  has_next_page: boolean;
  has_prev_page: boolean;
}

export interface ReadingQueryResponse {
  success: boolean;
  data: Reading[];
  pagination: Pagination;
}

export interface ModeChangeRequest {
  mode: 'NORMAL' | 'EMERGENCY';
}

export interface ModeChangeResponse {
  success: boolean;
  sensor_known: boolean;
  requested_mode: string;
  requested_at: string;
  message: string;
}

// Filter Types
export interface SensorFilters {
  serial_number?: string;
  health_status?: 'HEALTHY' | 'FAULTY';
}

export interface ReadingFilters {
  serial_number?: string;
  mode?: 'NORMAL' | 'EMERGENCY';
  sensor_from?: string;
  sensor_to?: string;
  received_from?: string;
  received_to?: string;
  page?: number;
  limit?: number;
}
