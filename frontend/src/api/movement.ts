import { apiClient } from './client';

export interface Movement {
  id: string;
  name: string;
  name_en?: string;
  category?: string;
  muscle_group?: string;
  secondary_muscles?: string[];
  equipment?: string;
  difficulty?: string;
  description?: string;
  instructions?: string[];
  key_points?: string[];
  common_mistakes?: string[];
  video_url?: string;
  contraindications?: string[];
}

export interface MovementFilters {
  muscle_group?: string;
  category?: string;
  difficulty?: string;
  equipment?: string;
  search?: string;
}

export interface MovementCategories {
  muscle_groups: string[];
  categories: string[];
  equipment: string[];
}

export function getMovements(filters?: MovementFilters) {
  return apiClient.get<Movement[]>('/movements', {
    params: filters
  });
}

export function getMovementCategories() {
  return apiClient.get<MovementCategories>('/movements/categories');
}

export function getMovement(id: string) {
  return apiClient.get<Movement>(`/movements/${id}`);
}
