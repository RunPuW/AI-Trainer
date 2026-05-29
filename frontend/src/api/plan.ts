import { apiClient } from './client';

export interface UserProfile {
  gender: string;
  age: number;
  height_cm: number;
  weight_kg: number;
  experience: string;
  injuries: string[];
  available_equipment: string[];
  goal: string;
  sessions_per_week: number;
}

export interface PlanDay {
  day: string;
  focus: string;
  exercises: {
    name: string;
    sets: number;
    reps: string;
    rest_seconds: number;
    notes?: string;
  }[];
}

export interface PlanResponse {
  plan_id: string;
  duration_weeks: number;
  weekly_schedule: PlanDay[];
  notes: string;
}

export function generateTrainingPlan(profile: UserProfile) {
  return apiClient.post<PlanResponse>('/plan', { profile });
}
