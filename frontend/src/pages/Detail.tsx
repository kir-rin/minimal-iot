import { useState } from 'react';
import { ArrowLeft, Activity, Thermometer, Droplets, Gauge, Wind } from 'lucide-react';
import { useSensorStatus, useReadings } from '../hooks/useApi';
import { formatToLocal } from '../utils/time';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { Reading } from '../types';

interface DetailProps {
  serialNumber: string;
  onBack: () => void;
}

export function Detail({ serialNumber, onBack }: DetailProps) {
  const [activeTab, setActiveTab] = useState<'chart' | 'table'>('chart');
  
  const { data: statusData } = useSensorStatus({ serial_number: serialNumber });
  const { data: readingsData, isLoading } = useReadings({ 
    serial_number: serialNumber,
    limit: 50 
  });

  const sensor = statusData?.data?.[0];
  const readings = readingsData?.data || [];

  // 차트 데이터 준비
  const chartData = readings.map((r) => ({
    time: formatToLocal(r.timestamp, 'HH:mm'),
    temperature: r.metrics.temperature,
    humidity: r.metrics.humidity,
    pressure: r.metrics.pressure,
    air_quality: r.metrics.air_quality,
  })).reverse();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center gap-3">
          <button 
            onClick={onBack}
            className="p-2 -ml-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <h1 className="text-lg font-semibold text-gray-900">센서 상세</h1>
        </div>
      </header>

      {!sensor ? (
        <div className="flex flex-col items-center justify-center py-12 text-gray-500">
          <p className="text-lg font-medium">센서 정보를 찾을 수 없습니다</p>
        </div>
      ) : (
        <>
          {/* 센서 정보 카드 */}
          <div className="px-4 py-4">
            <div className="sensor-card">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-gray-600" />
                  <span className="font-semibold text-gray-900">{sensor.serial_number}</span>
                </div>
                <span className={sensor.health_status === 'HEALTHY' ? 'badge-healthy' : 'badge-faulty'}>
                  {sensor.health_status === 'HEALTHY' ? '정상' : '고장'}
                </span>
              </div>
              
              <div className="flex items-center gap-2 mb-2">
                <span className={sensor.last_reported_mode === 'EMERGENCY' ? 'badge-mode-emergency' : 'badge-mode-normal'}>
                  {sensor.last_reported_mode === 'EMERGENCY' ? '긴급 모드' : '일반 모드'}
                </span>
              </div>

              <p className="text-sm text-gray-500">
                마지막 수신: {formatToLocal(sensor.last_server_received_at)}
              </p>
            </div>
          </div>

          {/* 탭 */}
          <div className="px-4 pb-2">
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setActiveTab('chart')}
                className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'chart' 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600'
                }`}
              >
                차트
              </button>
              <button
                onClick={() => setActiveTab('table')}
                className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'table' 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600'
                }`}
              >
                테이블
              </button>
            </div>
          </div>

          {/* 탭 내용 */}
          <div className="px-4 py-4">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <div className="w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : readings.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <p>측정 데이터가 없습니다</p>
              </div>
            ) : activeTab === 'chart' ? (
              <div className="space-y-6">
                {/* 온도 차트 */}
                <div className="bg-white rounded-xl p-4 border border-gray-100">
                  <div className="flex items-center gap-2 mb-4">
                    <Thermometer className="w-5 h-5 text-orange-500" />
                    <span className="font-medium text-gray-900">온도</span>
                  </div>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                        <XAxis dataKey="time" tick={{fontSize: 12}} />
                        <YAxis tick={{fontSize: 12}} />
                        <Tooltip />
                        <Line 
                          type="monotone" 
                          dataKey="temperature" 
                          stroke="#f97316" 
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 습도 차트 */}
                <div className="bg-white rounded-xl p-4 border border-gray-100">
                  <div className="flex items-center gap-2 mb-4">
                    <Droplets className="w-5 h-5 text-blue-500" />
                    <span className="font-medium text-gray-900">습도</span>
                  </div>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                        <XAxis dataKey="time" tick={{fontSize: 12}} />
                        <YAxis tick={{fontSize: 12}} />
                        <Tooltip />
                        <Line 
                          type="monotone" 
                          dataKey="humidity" 
                          stroke="#3b82f6" 
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 기압 차트 */}
                <div className="bg-white rounded-xl p-4 border border-gray-100">
                  <div className="flex items-center gap-2 mb-4">
                    <Gauge className="w-5 h-5 text-purple-500" />
                    <span className="font-medium text-gray-900">기압</span>
                  </div>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                        <XAxis dataKey="time" tick={{fontSize: 12}} />
                        <YAxis tick={{fontSize: 12}} />
                        <Tooltip />
                        <Line 
                          type="monotone" 
                          dataKey="pressure" 
                          stroke="#a855f7" 
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 공기질 차트 */}
                <div className="bg-white rounded-xl p-4 border border-gray-100">
                  <div className="flex items-center gap-2 mb-4">
                    <Wind className="w-5 h-5 text-green-500" />
                    <span className="font-medium text-gray-900">공기질</span>
                  </div>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                        <XAxis dataKey="time" tick={{fontSize: 12}} />
                        <YAxis tick={{fontSize: 12}} />
                        <Tooltip />
                        <Line 
                          type="monotone" 
                          dataKey="air_quality" 
                          stroke="#22c55e" 
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-600">시간</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">온도</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">습도</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">기압</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-600">공기질</th>
                    </tr>
                  </thead>
                  <tbody>
                    {readings.map((reading: Reading) => (
                      <tr key={reading.id} className="border-b border-gray-100 last:border-0">
                        <td className="px-4 py-3 text-gray-900">
                          {formatToLocal(reading.timestamp, 'MM/dd HH:mm')}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-900">
                          {reading.metrics.temperature.toFixed(1)}°C
                        </td>
                        <td className="px-4 py-3 text-right text-gray-900">
                          {reading.metrics.humidity.toFixed(1)}%
                        </td>
                        <td className="px-4 py-3 text-right text-gray-900">
                          {reading.metrics.pressure.toFixed(1)}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-900">
                          {reading.metrics.air_quality}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
