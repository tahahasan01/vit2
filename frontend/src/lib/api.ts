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
  TryOnJobCreated,
  TryOnJobStatus,
  TryOnHistory,
  GarmentCatalogResponse,
  Garment,
  HealthResponse,
  ConsentPayload,
  UserProfile,
  AuthResponse,
  ScrapeResponse,
} from '@/types';

export const api = {
  /* ── Auth ── */
  signUp: (email: string, password: string) =>
    request<AuthResponse>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  signIn: (email: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  signOut: () =>
    request<void>('/auth/logout', { method: 'POST' }),

  getMe: () => request<UserProfile>('/auth/me'),

  recordConsent: (consent: ConsentPayload) =>
    request<UserProfile>('/auth/consent', {
      method: 'POST',
      body: JSON.stringify(consent),
    }),

  /* ── Garments ── */
  getGarments: (limit = 50, offset = 0, category?: string) => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (category) params.set('category', category);
    return request<GarmentCatalogResponse>(`/garments?${params}`);
  },

  getGarment: (id: string) =>
    request<Garment>(`/garments/${id}`),

  uploadGarment: (formData: FormData) =>
    upload<Garment>('/garments', formData),

  /* ── Try-On ── */
  startTryOn: (garmentId: string, userPhotoFile: File, category = 'upper_body', garmentDescription = '') => {
    const formData = new FormData();
    formData.append('garment_id', garmentId);
    formData.append('category', category);
    formData.append('garment_description', garmentDescription);
    // Backend expects two files: selfie + fullbody.
    // Single-photo UX: send the same photo for both fields.
    formData.append('selfie', userPhotoFile);
    formData.append('fullbody', userPhotoFile);
    return upload<TryOnJobCreated>('/tryon', formData);
  },

  getTryOnStatus: (jobId: string) =>
    request<TryOnJobStatus>(`/tryon/${jobId}`),

  getTryOnHistory: (limit = 50) =>
    request<TryOnHistory>(`/tryon/history?limit=${limit}`),

  deleteTryOn: (jobId: string) =>
    request<void>(`/tryon/${jobId}`, { method: 'DELETE' }),

  /* ── Health ── */
  getHealth: () => request<HealthResponse>('/health'),

  /* ── Scraper ── */
  scrapeGarments: (url: string, importToCatalog = false) =>
    request<ScrapeResponse>('/scraper/scrape', {
      method: 'POST',
      body: JSON.stringify({ url, import_to_catalog: importToCatalog }),
    }),
};

export default api;
