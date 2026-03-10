import { create } from 'zustand';
import { api } from '@/lib/api';
import type {
  JobStatus,
  TryOnJobStatus,
  TryOnHistoryItem,
  TryOnResult,
  ViewMode,
} from '@/types';

/* ─── Active Job ─── */

interface ActiveJob {
  jobId: string;
  garmentId: string;
  status: JobStatus;
  progress: number;
  currentStep?: string;
  result?: TryOnResult;
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

  fetchHistory: () => Promise<void>;
  deleteLook: (jobId: string) => Promise<void>;

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
    if (!userPhotoFile) throw new Error('No photo uploaded');

    const res = await api.startTryOn(selectedGarmentId, userPhotoFile);

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
    const res: TryOnJobStatus = await api.getTryOnStatus(jobId);

    set({
      activeJob: {
        jobId: res.job_id,
        garmentId: get().selectedGarmentId ?? '',
        status: res.status,
        progress: res.progress,
        currentStep: res.current_step,
        result: res.result,
        error: res.error,
      },
    });

    // Auto-set view mode when 3D mesh arrives
    if (res.result?.mesh_url && !get().activeJob?.result?.mesh_url) {
      set({ viewMode: '3d' });
    }
  },

  updateJobFromRealtime: (update) => {
    const current = get().activeJob;
    if (!current) return;

    const merged = { ...current, ...update };
    set({ activeJob: merged });

    // Auto-switch to 3D view when mesh arrives
    if (update.result?.mesh_url && !current.result?.mesh_url) {
      set({ viewMode: '3d' });
    }
  },

  clearActiveJob: () => set({ activeJob: null }),

  /* ─── History ─── */

  fetchHistory: async () => {
    set({ historyLoading: true });
    try {
      const res = await api.getTryOnHistory();
      set({ history: res.looks, historyLoading: false });
    } catch {
      set({ historyLoading: false });
    }
  },

  deleteLook: async (jobId) => {
    await api.deleteTryOn(jobId);
    set((state) => ({
      history: state.history.filter((item) => item.job_id !== jobId),
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
