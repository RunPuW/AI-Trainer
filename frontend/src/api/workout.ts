import { apiClient } from './client';

export interface WorkoutStats {
  total_sessions: number;
  total_reps: number;
  total_duration_min: number;
  exercise_types: string[];
  streak_days: number;
}

export interface SaveWorkoutRequest {
  session_id: string;
  exercise_type: string;
  duration_min: number;
  rep_count: number;
  errors?: string[];
  error_details?: Record<string, number>;
  angles_log?: any[];
}

export interface SaveWorkoutResponse {
  success: boolean;
  id: string;
}

export interface WorkoutLog {
  id: string;
  session_date: string;
  exercise_type: string;
  duration_min: number;
  rep_count: number;
  errors?: string[];
}

export function getWorkoutStats() {
  return apiClient.get<WorkoutStats>('/workout/stats');
}

export function saveWorkout(request: SaveWorkoutRequest) {
  return apiClient.post<SaveWorkoutResponse>('/workout/save', request);
}

export function getWorkoutHistory(limit = 20) {
  return apiClient.get<WorkoutLog[]>('/workout/history', { params: { limit } });
}
