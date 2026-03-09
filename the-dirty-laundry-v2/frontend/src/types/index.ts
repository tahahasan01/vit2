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
  TopWear = 'top_wear',
  BottomWear = 'bottom_wear',
  FullBody = 'full_body',
  Outerwear = 'outerwear',
}

export type ViewMode = '3d' | 'photo' | 'video';

/* ─── Auth ─── */

export interface User {
  id: string;
  email: string;
  display_name?: string;
  avatar_url?: string;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
}

/* ─── Garment ─── */

export interface Garment {
  id: string;
  name: string;
  brand: string;
  category: GarmentCategory;
  description?: string;
  price?: number;
  currency?: string;
  image_url: string;
  thumbnail_url?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface GarmentCatalogResponse {
  garments: Garment[];
  total: number;
  page: number;
  per_page: number;
}

/* ─── Try-On ─── */

export interface TryOnRequest {
  garment_id: string;
  user_photo_url?: string;
}

export interface TryOnJobResponse {
  job_id: string;
  status: JobStatus;
  created_at: string;
}

export interface TryOnResult {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step?: string;
  hero_image_url?: string;
  mesh_url?: string;
  video_url?: string;
  error?: string;
  created_at: string;
  completed_at?: string;
}

export interface TryOnHistoryItem {
  id: string;
  garment: Garment;
  hero_image_url?: string;
  mesh_url?: string;
  video_url?: string;
  status: JobStatus;
  created_at: string;
}

/* ─── Realtime ─── */

export interface RealtimeJobUpdate {
  job_id: string;
  status: JobStatus;
  progress: number;
  current_step?: string;
  hero_image_url?: string;
  mesh_url?: string;
  video_url?: string;
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
  data_processing: boolean;
  image_storage: boolean;
  marketing?: boolean;
}

/* ─── API Error ─── */

export interface ApiError {
  detail: string;
  status_code?: number;
}
