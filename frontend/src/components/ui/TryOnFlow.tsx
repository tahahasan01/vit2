import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { useTryOnStore } from '@/stores/useTryOnStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { useConsent } from '@/hooks/useConsent';
import { useTryOnRealtime } from '@/hooks/useTryOnRealtime';
import GarmentCatalog from './GarmentCatalog';
import ProgressTracker from './ProgressTracker';
import ViewModeSwitcher from './ViewModeSwitcher';
import ConsentModal from './ConsentModal';
import AuthModal from './AuthModal';
import Scene from '@/components/viewer/Scene';
import PhotoView from '@/components/viewer/PhotoView';
import VideoPlayer from '@/components/viewer/VideoPlayer';
import FallbackState from './FallbackState';
import type { ViewMode } from '@/types';

type FlowStep = 'select-garment' | 'upload-photo' | 'processing' | 'result';

export default function TryOnFlow() {
  const [step, setStep] = useState<FlowStep>('select-garment');
  const [error, setError] = useState<string | null>(null);
  const [showConsent, setShowConsent] = useState(false);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);

  const user = useAuthStore((s) => s.user);

  const {
    selectedGarmentId,
    userPhotoFile,
    setUserPhoto,
    activeJob,
    viewMode,
    startTryOn,
  } = useTryOnStore();

  const { needsConsent } = useConsent();

  // Realtime subscription (auto-subscribes when activeJob exists)
  useTryOnRealtime(activeJob?.jobId ?? null);

  // Auto-progress flow when job completes
  const jobStatus = activeJob?.status;
  if (jobStatus === 'completed' && step === 'processing') {
    setStep('result');
  }

  /* ─── Photo upload dropzone ─── */
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (file) {
        setUserPhoto(file);
        setError(null);
      }
    },
    [setUserPhoto],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  /* ─── Start pipeline ─── */
  const handleStartTryOn = async () => {
    if (!user) {
      setShowAuthPrompt(true);
      return;
    }

    if (needsConsent) {
      setShowConsent(true);
      return;
    }

    setError(null);
    try {
      await startTryOn();
      setStep('processing');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start try-on');
    }
  };

  /* ─── View mode disabled states ─── */
  const disabledModes: ViewMode[] = [];
  if (!activeJob?.meshUrl) disabledModes.push('3d');
  if (!activeJob?.videoUrl) disabledModes.push('video');
  if (!activeJob?.heroImageUrl) disabledModes.push('photo');

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Auth prompt modal */}
      <AnimatePresence>
        {showAuthPrompt && (
          <AuthModal onClose={() => setShowAuthPrompt(false)} />
        )}
      </AnimatePresence>

      {/* Consent modal */}
      <AnimatePresence>
        {showConsent && (
          <ConsentModal
            onComplete={() => {
              setShowConsent(false);
              handleStartTryOn();
            }}
            onClose={() => setShowConsent(false)}
          />
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {/* ─── Step 1: Select Garment ─── */}
        {step === 'select-garment' && (
          <motion.div
            key="select"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-8"
          >
            <div className="text-center space-y-2">
              <h2 className="text-3xl font-bold font-display">
                Choose Your Look
              </h2>
              <p className="text-white/50 max-w-md mx-auto">
                Select a garment from the collection to try on virtually.
              </p>
            </div>

            <GarmentCatalog />

            <div className="flex justify-center">
              <button
                onClick={() => {
                  if (!user) {
                    setShowAuthPrompt(true);
                    return;
                  }
                  if (selectedGarmentId) setStep('upload-photo');
                }}
                disabled={!selectedGarmentId}
                className="px-8 py-3 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-30 disabled:cursor-not-allowed text-white font-semibold transition-colors"
              >
                Continue with Selected
              </button>
            </div>
          </motion.div>
        )}

        {/* ─── Step 2: Upload Photo ─── */}
        {step === 'upload-photo' && (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="max-w-xl mx-auto space-y-8"
          >
            <div className="text-center space-y-2">
              <h2 className="text-3xl font-bold font-display">
                Upload Your Photo
              </h2>
              <p className="text-white/50 max-w-md mx-auto">
                Stand straight, facing the camera. Good lighting helps for the best results.
              </p>
            </div>

            <div
              {...getRootProps()}
              className={`dropzone ${isDragActive ? 'active' : ''}`}
            >
              <input {...getInputProps()} />

              {userPhotoFile ? (
                <div className="text-center space-y-3">
                  <img
                    src={URL.createObjectURL(userPhotoFile)}
                    alt="Your photo"
                    className="w-40 h-56 object-cover rounded-xl mx-auto"
                  />
                  <p className="text-sm text-white/60">{userPhotoFile.name}</p>
                  <p className="text-xs text-white/30">Click or drop to replace</p>
                </div>
              ) : (
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 mx-auto rounded-2xl bg-brand-500/10 flex items-center justify-center">
                    <svg
                      className="w-8 h-8 text-brand-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={1.5}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                      />
                    </svg>
                  </div>
                  <p className="text-white/70 font-medium">
                    {isDragActive
                      ? 'Drop your photo here'
                      : 'Drag & drop or click to upload'}
                  </p>
                  <p className="text-xs text-white/30">
                    JPG, PNG or WebP — Max 10 MB
                  </p>
                </div>
              )}
            </div>

            {error && (
              <p className="text-sm text-red-400 text-center">{error}</p>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={() => setStep('select-garment')}
                className="px-6 py-3 rounded-xl border border-white/10 hover:border-white/20 text-white/60 hover:text-white/80 font-medium transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleStartTryOn}
                disabled={!userPhotoFile}
                className="px-8 py-3 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-30 disabled:cursor-not-allowed text-white font-semibold transition-colors"
              >
                Start Virtual Try-On
              </button>
            </div>
          </motion.div>
        )}

        {/* ─── Step 3: Processing ─── */}
        {step === 'processing' && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="max-w-2xl mx-auto space-y-8"
          >
            <div className="text-center space-y-2">
              <h2 className="text-3xl font-bold font-display">
                Creating Your Look
              </h2>
              <p className="text-white/50 max-w-md mx-auto">
                Our AI is scanning your body, draping the garment, and rendering a 360° view.
              </p>
            </div>

            <ProgressTracker />

            {/* Show partial results as they arrive */}
            {activeJob?.heroImageUrl && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="rounded-2xl overflow-hidden"
              >
                <PhotoView imageUrl={activeJob.heroImageUrl} />
              </motion.div>
            )}

            {activeJob?.status === 'failed' && (
              <div className="flex justify-center">
                <button
                  onClick={() => {
                    useTryOnStore.getState().clearActiveJob();
                    setStep('upload-photo');
                  }}
                  className="px-6 py-3 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-red-400 font-medium transition-colors"
                >
                  Try Again
                </button>
              </div>
            )}
          </motion.div>
        )}

        {/* ─── Step 4: Result ─── */}
        {step === 'result' && activeJob && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-6"
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold font-display">Your Look</h2>
                <p className="text-white/40 text-sm">
                  Rotate, zoom, or switch views to explore
                </p>
              </div>
              <ViewModeSwitcher disabledModes={disabledModes} />
            </div>

            {/* Viewer */}
            <div className="glass-card overflow-hidden" style={{ minHeight: '550px' }}>
              {viewMode === '3d' && activeJob.meshUrl ? (
                <Scene meshUrl={activeJob.meshUrl} />
              ) : viewMode === 'video' && activeJob.videoUrl ? (
                <VideoPlayer
                  videoUrl={activeJob.videoUrl}
                  poster={activeJob.heroImageUrl}
                />
              ) : activeJob.heroImageUrl ? (
                <PhotoView imageUrl={activeJob.heroImageUrl} />
              ) : (
                <FallbackState
                  title="No result available"
                  message="Something went wrong. Try again."
                />
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => {
                  useTryOnStore.getState().reset();
                  setStep('select-garment');
                }}
                className="px-6 py-3 rounded-xl border border-white/10 hover:border-white/20 text-white/60 hover:text-white/80 font-medium transition-colors"
              >
                Try Another
              </button>
              {activeJob.heroImageUrl && (
                <a
                  href={activeJob.heroImageUrl}
                  download
                  className="px-6 py-3 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-semibold transition-colors inline-flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download
                </a>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
