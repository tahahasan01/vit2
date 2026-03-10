import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

interface VideoPlayerProps {
  videoUrl: string;
  poster?: string;
  autoPlay?: boolean;
  loop?: boolean;
}

/**
 * 360° orbital video player — plays the Wan 2.2 I2V output.
 * Auto-plays on mount with seamless loop for continuous rotation feel.
 */
export default function VideoPlayer({
  videoUrl,
  poster,
  autoPlay = true,
  loop = true,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (autoPlay) {
      video.play().catch(() => {
        // Autoplay blocked — user needs to interact
      });
    }
  }, [videoUrl, autoPlay]);

  return (
    <motion.div
      className="w-full h-full min-h-[500px] flex items-center justify-center bg-surface-900 rounded-2xl overflow-hidden relative"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <video
        ref={videoRef}
        src={videoUrl}
        poster={poster}
        loop={loop}
        muted
        playsInline
        controls
        className="max-w-full max-h-full object-contain"
      />

      {/* 360° badge */}
      <div className="absolute top-4 right-4 px-3 py-1.5 rounded-full bg-black/60 backdrop-blur-sm text-xs font-medium text-white/80 flex items-center gap-1.5">
        <svg
          className="w-3.5 h-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        360° View
      </div>
    </motion.div>
  );
}
