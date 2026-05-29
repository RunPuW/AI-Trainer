import { apiClient } from './client';

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  email?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  username: string;
  email?: string;
  avatar_url?: string;
}

export function login(payload: LoginPayload) {
  const params = new URLSearchParams();
  params.append('username', payload.username);
  params.append('password', payload.password);
  return apiClient.post<TokenResponse>('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
}

export function register(payload: RegisterPayload) {
  return apiClient.post<UserResponse>('/auth/register', payload);
}

export function getMe() {
  return apiClient.get<UserResponse>('/auth/me');
}
