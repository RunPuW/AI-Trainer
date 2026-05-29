import { apiClient } from './client';

export interface ReportRequest {
  session_data: {
    session_id: string;
    movement: string;
    duration_seconds: number;
    rep_count: number;
    errors: string[];
    error_details?: Record<string, number>;
    captured_frames?: Array<string | { image: string; reason?: string; state?: string; timestamp?: number }>;
  };
}

export interface ReportResponse {
  overall_score: number;
  highlights: string[];
  corrections: string[];
  recovery_plan: string;
  next_session_goals: string[];
}

export interface TrainingReport {
  success: boolean;
  report_path: string;
  message: string;
}

export interface MosaicResponse {
  success: boolean;
  mosaic_path: string;
  message: string;
}

export function generateReport(request: ReportRequest) {
  return apiClient.post<ReportResponse>('/report', request);
}

export function generateHTMLReport(request: ReportRequest) {
  return apiClient.post<TrainingReport>('/report/generate', request);
}

export function generateMosaic(request: ReportRequest) {
  return apiClient.post<MosaicResponse>('/report/mosaic', request);
}
