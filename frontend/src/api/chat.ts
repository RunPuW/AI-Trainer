import { apiClient } from './client';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: number;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  tool_calls?: any[];
}

export function sendChatMessage(request: ChatRequest) {
  return apiClient.post<ChatResponse>('/chat', request);
}

// WebSocket chat
export function createChatWebSocket(sessionId: string, token: string): WebSocket {
  const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${location.host}/api/ws/chat/${sessionId}?token=${token}`;
  return new WebSocket(wsUrl);
}
