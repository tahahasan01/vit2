import { create } from 'zustand';

/**
 * Viewer store — controls the 3D scene state, camera, and environment.
 * Separated from TryOnStore so the R3F canvas only re-renders
 * when viewer-specific state changes.
 */

interface CameraState {
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
  autoRotate: boolean;
  autoRotateSpeed: number;
}

interface ViewerStore {
  /* Camera */
  camera: CameraState;
  setCameraPosition: (pos: [number, number, number]) => void;
  setCameraTarget: (target: [number, number, number]) => void;
  toggleAutoRotate: () => void;
  setAutoRotateSpeed: (speed: number) => void;

  /* Environment */
  environmentPreset: string;
  setEnvironmentPreset: (preset: string) => void;
  showGrid: boolean;
  toggleGrid: () => void;

  /* Model info */
  modelLoading: boolean;
  modelError: string | null;
  setModelLoading: (loading: boolean) => void;
  setModelError: (error: string | null) => void;

  /* Quality */
  quality: 'low' | 'medium' | 'high';
  setQuality: (quality: 'low' | 'medium' | 'high') => void;

  /* Screenshot */
  requestScreenshot: boolean;
  triggerScreenshot: () => void;
  clearScreenshotRequest: () => void;

  /* Reset */
  resetCamera: () => void;
}

const DEFAULT_CAMERA: CameraState = {
  position: [0, 1.2, 3],
  target: [0, 0.8, 0],
  fov: 45,
  autoRotate: false,
  autoRotateSpeed: 2,
};

export const useViewerStore = create<ViewerStore>()((set, _get) => ({
  camera: { ...DEFAULT_CAMERA },

  setCameraPosition: (position) =>
    set((s) => ({ camera: { ...s.camera, position } })),

  setCameraTarget: (target) =>
    set((s) => ({ camera: { ...s.camera, target } })),

  toggleAutoRotate: () =>
    set((s) => ({
      camera: { ...s.camera, autoRotate: !s.camera.autoRotate },
    })),

  setAutoRotateSpeed: (autoRotateSpeed) =>
    set((s) => ({ camera: { ...s.camera, autoRotateSpeed } })),

  /* Environment */
  environmentPreset: 'studio',
  setEnvironmentPreset: (environmentPreset) => set({ environmentPreset }),
  showGrid: false,
  toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),

  /* Model */
  modelLoading: false,
  modelError: null,
  setModelLoading: (modelLoading) => set({ modelLoading }),
  setModelError: (modelError) => set({ modelError }),

  /* Quality */
  quality: 'high',
  setQuality: (quality) => set({ quality }),

  /* Screenshot */
  requestScreenshot: false,
  triggerScreenshot: () => set({ requestScreenshot: true }),
  clearScreenshotRequest: () => set({ requestScreenshot: false }),

  /* Reset */
  resetCamera: () => set({ camera: { ...DEFAULT_CAMERA } }),
}));
