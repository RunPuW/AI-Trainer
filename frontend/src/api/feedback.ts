import { apiClient } from './client';

export interface FeedbackRequest {
  frame_data: {
    landmarks: any[];
    timestamp: number;
    angles?: Record<string, number>;
    state?: string;
  };
}

export interface FeedbackResponse {
  immediate_feedback: string;
  encouragement: string;
  should_speak: boolean;
}

export function getRealtimeFeedback(request: FeedbackRequest) {
  return apiClient.post<FeedbackResponse>('/feedback', request);
}
