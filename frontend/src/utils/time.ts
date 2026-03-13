import { formatDistanceToNow } from 'date-fns';
import { formatInTimeZone } from 'date-fns-tz';

/**
 * UTC 타임스탬프를 사용자 로컬 시간대로 변환
 */
export function formatToLocal(utcString: string, formatStr: string = 'yyyy-MM-dd HH:mm:ss'): string {
  try {
    const date = new Date(utcString);
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return formatInTimeZone(date, userTimezone, formatStr);
  } catch (error) {
    console.error('Error formatting time:', error);
    return utcString;
  }
}

/**
 * 상대 시간 표시 (e.g., "2분 전", "3시간 전")
 */
export function formatRelativeTime(utcString: string): string {
  try {
    const date = new Date(utcString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch (error) {
    console.error('Error formatting relative time:', error);
    return utcString;
  }
}

/**
 * 간단한 시간 포맷 (e.g., "14:30")
 */
export function formatTime(utcString: string): string {
  return formatToLocal(utcString, 'HH:mm');
}

/**
 * 날짜 포맷 (e.g., "05/23")
 */
export function formatDate(utcString: string): string {
  return formatToLocal(utcString, 'MM/dd');
}

/**
 * ISO8601 포맷으로 변환 (API 요청용)
 */
export function toISOString(date: Date): string {
  return date.toISOString();
}

/**
 * 현재 시간을 ISO8601 포맷으로 반환
 */
export function getCurrentISOString(): string {
  return new Date().toISOString();
}
