import { create } from 'zustand';
import { api } from '@/lib/api';
import type {
  JobStatus,
  TryOnResult,
  TryOnHistoryItem,
  ViewMode,
} from '@/types';

/* ─── Active Job ─── */

interface ActiveJob {
  jobId: string;
  garmentId: string;
  status: JobStatus;
  progress: number;
  currentStep?: string;
  heroImageUrl?: string;
  meshUrl?: string;
  videoUrl?: string;
  error?: string;
}

/* ─── Store ─── */

interface TryOnStore {
  /* Flow state */
  selectedGarmentId: string | null;
  userPhotoFile: File | null;
  viewMode: ViewMode;

  /* Active job tracking */
  activeJob: ActiveJob | null;

  /* History ("My Looks") */
  history: TryOnHistoryItem[];
  historyLoading: boolean;

  /* Actions */
  selectGarment: (id: string) => void;
  setUserPhoto: (file: File | null) => void;
  setViewMode: (mode: ViewMode) => void;

  startTryOn: () => Promise<string>;
  pollJobStatus: (jobId: string) => Promise<void>;
  updateJobFromRealtime: (update: Partial<ActiveJob>) => void;
  clearActiveJob: () => void;

  fetchHistory: (page?: number) => Promise<void>;
  deleteLook: (id: string) => Promise<void>;

  /* Convenience */
  reset: () => void;
}

export const useTryOnStore = create<TryOnStore>()((set, get) => ({
  selectedGarmentId: null,
  userPhotoFile: null,
  viewMode: 'photo' as ViewMode,

  activeJob: null,
  history: [],
  historyLoading: false,

  /* ─── Selection ─── */

  selectGarment: (id) => set({ selectedGarmentId: id }),

  setUserPhoto: (file) => set({ userPhotoFile: file }),

  setViewMode: (mode) => set({ viewMode: mode }),

  /* ─── Try-On Pipeline ─── */

  startTryOn: async () => {
    const { selectedGarmentId, userPhotoFile } = get();
    if (!selectedGarmentId) throw new Error('No garment selected');

    const res = await api.startTryOn(selectedGarmentId, userPhotoFile ?? undefined);

    set({
      activeJob: {
        jobId: res.job_id,
        garmentId: selectedGarmentId,
        status: res.status,
        progress: 0,
        currentStep: 'queued',
      },
    });

    return res.job_id;
  },

  /** Fallback polling — only used if Supabase Realtime is unavailable */
  pollJobStatus: async (jobId) => {
    const res: TryOnResult = await api.getTryOnStatus(jobId);

    set({
      activeJob: {
        jobId: res.job_id,
        garmentId: get().selectedGarmentId ?? '',
        status: res.status,
        progress: res.progress,
        currentStep: res.current_step,
        heroImageUrl: res.hero_image_url,
        meshUrl: res.mesh_url,
        videoUrl: res.video_url,
        error: res.error,
      },
    });

    // Auto-set view mode when results arrive
    if (res.mesh_url && !get().activeJob?.meshUrl) {
      set({ viewMode: '3d' });
    }
  },

  updateJobFromRealtime: (update) => {
    const current = get().activeJob;
    if (!current) return;

    const merged = { ...current, ...update };
    set({ activeJob: merged });

    // Auto-switch to 3D view when mesh arrives
    if (update.meshUrl && !current.meshUrl) {
      set({ viewMode: '3d' });
    }
  },

  clearActiveJob: () => set({ activeJob: null }),

  /* ─── History ─── */

  fetchHistory: async (page = 1) => {
    set({ historyLoading: true });
    try {
      const res = await api.getTryOnHistory(page);
      set({ history: res.items, historyLoading: false });
    } catch {
      set({ historyLoading: false });
    }
  },

  deleteLook: async (id) => {
    await api.deleteTryOn(id);
    set((state) => ({
      history: state.history.filter((item) => item.id !== id),
    }));
  },

  /* ─── Reset ─── */

  reset: () =>
    set({
      selectedGarmentId: null,
      userPhotoFile: null,
      viewMode: 'photo',
      activeJob: null,
    }),
}));
