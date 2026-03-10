import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useTryOnStore } from '@/stores/useTryOnStore';
import { useAuthStore } from '@/stores/useAuthStore';
import AuthModal from './AuthModal';

export default function MyLooks() {
  const { history, historyLoading, fetchHistory, deleteLook } =
    useTryOnStore();
  const user = useAuthStore((s) => s.user);
  const [showAuth, setShowAuth] = useState(false);

  useEffect(() => {
    if (user) fetchHistory();
  }, [user, fetchHistory]);

  // Auth gate
  if (!user) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-white/[0.03] border border-white/5 flex items-center justify-center">
          <svg className="w-8 h-8 text-white/20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
          </svg>
        </div>
        <h2 className="text-3xl font-bold font-display mb-3">My Looks</h2>
        <p className="text-white/40 text-lg mb-6">
          Sign in to save and view your virtual try-on history.
        </p>
        <button
          onClick={() => setShowAuth(true)}
          className="px-6 py-3 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-semibold transition-colors"
        >
          Sign In to Continue
        </button>
        <AnimatePresence>
          {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
        </AnimatePresence>
      </div>
    );
  }

  if (historyLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h2 className="text-3xl font-bold font-display mb-8">My Looks</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="aspect-[3/4] bg-surface-800 rounded-2xl animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <h2 className="text-3xl font-bold font-display mb-4">My Looks</h2>
        <p className="text-white/40 text-lg mb-6">
          No looks yet. Start a virtual try-on to see your looks here.
        </p>
        <Link
          to="/"
          className="inline-flex px-6 py-3 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-semibold transition-colors"
        >
          Start a Try-On
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h2 className="text-3xl font-bold font-display mb-8">My Looks</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {history.map((item, idx) => (
          <motion.div
            key={item.id}
            className="glass-card overflow-hidden group relative"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
          >
            {/* Thumbnail */}
            <div className="aspect-[3/4] relative overflow-hidden">
              {item.hero_image_url ? (
                <img
                  src={item.hero_image_url}
                  alt={item.garment.name}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="w-full h-full bg-surface-800 flex items-center justify-center">
                  <span className="text-white/20">No preview</span>
                </div>
              )}

              {/* Hover overlay */}
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center gap-3">
                {item.mesh_url && (
                  <button
                    className="px-3 py-2 rounded-lg bg-white/10 backdrop-blur-sm text-white text-sm font-medium hover:bg-white/20 transition-colors"
                    title="View in 3D"
                  >
                    3D View
                  </button>
                )}
                {item.video_url && (
                  <button
                    className="px-3 py-2 rounded-lg bg-white/10 backdrop-blur-sm text-white text-sm font-medium hover:bg-white/20 transition-colors"
                    title="Play 360° video"
                  >
                    360°
                  </button>
                )}
              </div>

              {/* Status badge */}
              {item.status === 'failed' && (
                <div className="absolute top-3 left-3 px-2 py-1 rounded-md bg-red-500/80 text-xs text-white font-medium">
                  Failed
                </div>
              )}
            </div>

            {/* Info */}
            <div className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-white truncate">
                    {item.garment.name}
                  </p>
                  <p className="text-xs text-white/40">{item.garment.brand}</p>
                </div>
                <button
                  onClick={() => deleteLook(item.id)}
                  className="p-2 rounded-lg text-white/20 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  title="Delete look"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
              <p className="text-[11px] text-white/20">
                {new Date(item.created_at).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
