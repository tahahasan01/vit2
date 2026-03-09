import { useTryOnStore } from '@/stores/useTryOnStore';
import type { ViewMode } from '@/types';
import { motion } from 'framer-motion';

const MODES: { key: ViewMode; label: string; icon: JSX.Element }[] = [
  {
    key: 'photo',
    label: 'Photo',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    key: '3d',
    label: '3D View',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
      </svg>
    ),
  },
  {
    key: 'video',
    label: '360°',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    ),
  },
];

interface ViewModeSwitcherProps {
  disabledModes?: ViewMode[];
}

export default function ViewModeSwitcher({ disabledModes = [] }: ViewModeSwitcherProps) {
  const viewMode = useTryOnStore((s) => s.viewMode);
  const setViewMode = useTryOnStore((s) => s.setViewMode);

  return (
    <div className="inline-flex bg-surface-800 rounded-xl p-1 gap-1">
      {MODES.map((mode) => {
        const isActive = viewMode === mode.key;
        const isDisabled = disabledModes.includes(mode.key);

        return (
          <button
            key={mode.key}
            onClick={() => !isDisabled && setViewMode(mode.key)}
            disabled={isDisabled}
            className={`
              relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
              transition-colors duration-200
              ${isDisabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'}
              ${isActive ? 'text-white' : 'text-white/50 hover:text-white/80'}
            `}
          >
            {isActive && (
              <motion.div
                layoutId="viewmode-pill"
                className="absolute inset-0 bg-brand-500/20 border border-brand-500/40 rounded-lg"
                transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
              />
            )}
            <span className="relative z-10 flex items-center gap-2">
              {mode.icon}
              {mode.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
