/* ─── Shared TypeScript types mirroring backend Pydantic schemas ─── */

/* ─── Enums ─── */

export enum JobStatus {
  Queued = 'queued',
  BodyEstimation = 'body_estimation',
  GarmentSynthesis = 'garment_synthesis',
  VideoRendering = 'video_rendering',
  Completed = 'completed',
  Failed = 'failed',
}

export enum GarmentCategory {
  UpperBody = 'upper_body',
  LowerBody = 'lower_body',
  Dresses = 'dresses',
}

export type ViewMode = '3d' | 'photo' | 'video';

/* ─── Auth ─── */

export interface UserProfile {
  id: string;
  email: string;
  consent_given: boolean;
  consent_given_at?: string;
  created_at: string;
}

/** Kept for convenience in components that only need basic info */
export type User = UserProfile;

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: UserProfile;
}

export interface AuthState {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
}

/* ─── Garment ─── */

export interface Garment {
  id: string;
  name: string;
  category: GarmentCategory;
  brand: string;
  description: string;
  image_url: string;
  thumbnail_url: string;
  created_at: string;
}

export interface GarmentCatalogResponse {
  garments: Garment[];
  total: number;
  categories: string[];
}

/* ─── Try-On ─── */

export interface TryOnJobCreated {
  job_id: string;
  status: JobStatus;
  estimated_seconds: number;
  created_at: string;
}

export interface TryOnResult {
  photo_url?: string;
  video_url?: string;
  mesh_url?: string;
}

export interface TryOnJobStatus {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step?: string;
  result?: TryOnResult;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface TryOnHistoryItem {
  job_id: string;
  garment_id: string;
  garment_name: string;
  garment_thumbnail: string;
  category: GarmentCategory;
  result: TryOnResult;
  created_at: string;
}

export interface TryOnHistory {
  looks: TryOnHistoryItem[];
  total: number;
}

/* ─── Realtime ─── */

export interface RealtimeJobUpdate {
  status: JobStatus;
  progress: number;
  current_step?: string;
  result_photo_url?: string;
  result_video_url?: string;
  result_mesh_url?: string;
  error?: string;
}

/* ─── Pipeline Steps (for progress tracker) ─── */

export interface PipelineStep {
  key: string;
  label: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
}

export const PIPELINE_STEPS: Omit<PipelineStep, 'status'>[] = [
  { key: 'queued', label: 'Queued', description: 'Preparing your try-on…' },
  { key: 'body_estimation', label: 'Body Scan', description: 'Analyzing your body shape…' },
  { key: 'garment_synthesis', label: 'Draping', description: 'Fitting the garment on you…' },
  { key: 'video_rendering', label: '360° Render', description: 'Generating 360° view…' },
  { key: 'completed', label: 'Done', description: 'Your look is ready!' },
];

/* ─── Health ─── */

export interface ExternalServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  circuit_state: string;
  latency_ms?: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  services: ExternalServiceStatus[];
}

/* ─── Consent ─── */

export interface ConsentPayload {
  consent_given: boolean;
  privacy_acknowledged: boolean;
}

/* ─── API Error ─── */

export interface ApiError {
  detail: string;
  status_code?: number;
}
