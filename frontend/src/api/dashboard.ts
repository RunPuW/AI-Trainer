import { apiClient } from './client';

export interface DashboardStats {
  total_sessions: number;
  total_duration_min: number;
  total_exercises: number;
  streak_days: number;
}

export interface RecentSession {
  id: string;
  movement: string;
  date: string;
  reps: number;
  accuracy: number;
  duration_min?: number;
}

export function getDashboardStats() {
  return apiClient.get<DashboardStats>('/dashboard/stats');
}

export function getRecentSessions(limit = 10) {
  return apiClient.get<RecentSession[]>('/dashboard/recent-sessions', {
    params: { limit }
  });
}
