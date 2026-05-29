import { apiClient } from './client';

export interface ProfileQuestionnaire {
  gender: string;
  age: number | null;
  height: number | null;
  weight: number | null;
  goal: string;
  trainingFrequency: string;
  injuryNotes: string;
  equipment: string[];
}

interface BackendQuestionnairePayload {
  gender: string;
  birth_date: string | null;
  height_cm: number;
  weight_kg: number;
  body_fat_pct: null;
  fitness_level: string;
  goal: string;
  weekly_days: number;
  session_minutes: number;
  equipment: string[];
  injuries: { area: string; severity: string; note: string }[];
  medical_notes: string | null;
}

function toBackendPayload(form: ProfileQuestionnaire): BackendQuestionnairePayload {
  const freqMap: Record<string, number> = { '0-1': 1, '2-3': 3, '3-4': 4, '5+': 5 };
  const currentYear = new Date().getFullYear();
  const birthYear = form.age ? currentYear - form.age : null;

  return {
    gender: form.gender,
    birth_date: birthYear ? `${birthYear}-01-01` : null,
    height_cm: form.height ?? 170,
    weight_kg: form.weight ?? 70,
    body_fat_pct: null,
    fitness_level: 'beginner',
    goal: form.goal || 'general',
    weekly_days: freqMap[form.trainingFrequency] ?? 3,
    session_minutes: 60,
    equipment: form.equipment,
    injuries: form.injuryNotes
      ? [{ area: 'general', severity: 'mild', note: form.injuryNotes }]
      : [],
    medical_notes: form.injuryNotes || null,
  };
}

export function saveQuestionnaire(payload: ProfileQuestionnaire) {
  return apiClient.post('/profile/questionnaire', toBackendPayload(payload));
}

export function getProfile() {
  return apiClient.get('/profile/me');
}
