/**
 * API client — typed wrapper around fetch for the FastAPI backend.
 * Automatically attaches the Supabase JWT token from localStorage.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

/* ─── Helpers ─── */

function getToken(): string | null {
  try {
    const raw = localStorage.getItem('sb-auth-token');
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.access_token ?? null;
  } catch {
    return null;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? 'Request failed', res.status);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json();
}

/* ─── Upload helper (multipart) ─── */

async function upload<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? 'Upload failed', res.status);
  }

  return res.json();
}

/* ─── Error class ─── */

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/* ─── Typed API methods ─── */

import type {
  TryOnJobResponse,
  TryOnResult,
  TryOnHistoryItem,
  GarmentCatalogResponse,
  Garment,
  HealthResponse,
  ConsentPayload,
  User,
} from '@/types';

export const api = {
  /* ── Auth ── */
  signUp: (email: string, password: string, displayName?: string) =>
    request<{ user: User; token: string }>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    }),

  signIn: (email: string, password: string) =>
    request<{ user: User; token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  signOut: () =>
    request<void>('/auth/logout', { method: 'POST' }),

  getMe: () => request<User>('/auth/me'),

  recordConsent: (consent: ConsentPayload) =>
    request<{ ok: boolean }>('/auth/consent', {
      method: 'POST',
      body: JSON.stringify(consent),
    }),

  /* ── Garments ── */
  getGarments: (page = 1, perPage = 20, category?: string) => {
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    });
    if (category) params.set('category', category);
    return request<GarmentCatalogResponse>(`/garments?${params}`);
  },

  getGarment: (id: string) =>
    request<Garment>(`/garments/${id}`),

  uploadGarment: (formData: FormData) =>
    upload<Garment>('/garments', formData),

  /* ── Try-On ── */
  startTryOn: (garmentId: string, userPhotoFile?: File) => {
    const formData = new FormData();
    formData.append('garment_id', garmentId);
    if (userPhotoFile) {
      formData.append('user_photo', userPhotoFile);
    }
    return upload<TryOnJobResponse>('/tryon', formData);
  },

  getTryOnStatus: (jobId: string) =>
    request<TryOnResult>(`/tryon/${jobId}`),

  getTryOnHistory: (page = 1, perPage = 20) =>
    request<{ items: TryOnHistoryItem[]; total: number }>(
      `/tryon/history?page=${page}&per_page=${perPage}`,
    ),

  deleteTryOn: (id: string) =>
    request<void>(`/tryon/${id}`, { method: 'DELETE' }),

  /* ── Health ── */
  getHealth: () => request<HealthResponse>('/health'),
};

export default api;
