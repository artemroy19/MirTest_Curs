import axios from "axios";

import { useSessionStore } from "../store/sessionStore";


const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL,
  timeout: 15000
});

let refreshPromise: Promise<string | null> | null = null;

apiClient.interceptors.request.use((config) => {
  const token = useSessionStore.getState().tokens?.access;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

async function refreshAccessToken(): Promise<string | null> {
  const { tokens, clearSession, setSession, user } = useSessionStore.getState();
  if (!tokens?.refresh || !user) return null;

  try {
    const response = await axios.post(`${baseURL}/auth/refresh/`, { refresh: tokens.refresh });
    const newAccess = response.data.access as string;
    setSession({
      user,
      access: newAccess,
      refresh: tokens.refresh
    });
    return newAccess;
  } catch {
    clearSession();
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as any;
    if (!original || error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    original._retry = true;
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken();
    }

    const newAccess = await refreshPromise;
    refreshPromise = null;

    if (!newAccess) {
      return Promise.reject(error);
    }

    original.headers.Authorization = `Bearer ${newAccess}`;
    return apiClient(original);
  }
);