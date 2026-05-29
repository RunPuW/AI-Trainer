import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

export interface AuthUser {
  id: string;
  username: string;
  email?: string;
  avatar_url?: string;
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'));
  const rawUser = localStorage.getItem('user');
  let parsedUser: AuthUser | null = null;
  try {
    parsedUser = rawUser ? (JSON.parse(rawUser) as AuthUser) : null;
  } catch {
    parsedUser = null;
  }
  const user = ref<AuthUser | null>(parsedUser);

  const isAuthenticated = computed(() => Boolean(token.value));

  function setSession(nextToken: string, nextUser?: AuthUser) {
    token.value = nextToken;
    localStorage.setItem('token', nextToken);

    if (nextUser) {
      user.value = nextUser;
      localStorage.setItem('user', JSON.stringify(nextUser));
    }
  }

  function updateUser(nextUser: AuthUser) {
    user.value = nextUser;
    localStorage.setItem('user', JSON.stringify(nextUser));
  }

  function logout() {
    token.value = null;
    user.value = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  return {
    token,
    user,
    isAuthenticated,
    setSession,
    updateUser,
    logout,
  };
});
