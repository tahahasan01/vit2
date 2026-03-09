import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore } from '@/stores/useAuthStore';

interface AuthModalProps {
  onClose: () => void;
}

type AuthTab = 'sign-in' | 'sign-up';

export default function AuthModal({ onClose }: AuthModalProps) {
  const [tab, setTab] = useState<AuthTab>('sign-in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { signIn, signUp } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (tab === 'sign-in') {
        await signIn(email, password);
      } else {
        await signUp(email, password, displayName || undefined);
      }
      onClose();
    } catch (err: any) {
      setError(err?.message ?? 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      <motion.div
        className="relative glass-card p-8 max-w-sm w-full space-y-6"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
      >
        {/* Tabs */}
        <div className="flex bg-surface-800 rounded-xl p-1">
          {(['sign-in', 'sign-up'] as AuthTab[]).map((t) => (
            <button
              key={t}
              onClick={() => {
                setTab(t);
                setError(null);
              }}
              className={`
                flex-1 py-2 rounded-lg text-sm font-medium transition-colors relative
                ${tab === t ? 'text-white' : 'text-white/40 hover:text-white/60'}
              `}
            >
              {tab === t && (
                <motion.div
                  layoutId="auth-tab"
                  className="absolute inset-0 bg-brand-500/20 border border-brand-500/40 rounded-lg"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
                />
              )}
              <span className="relative z-10">
                {t === 'sign-in' ? 'Sign In' : 'Sign Up'}
              </span>
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <AnimatePresence mode="wait">
            {tab === 'sign-up' && (
              <motion.div
                key="name"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
              >
                <input
                  type="text"
                  placeholder="Display name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-white/10 text-white placeholder-white/30 focus:outline-none focus:border-brand-500/50 text-sm"
                />
              </motion.div>
            )}
          </AnimatePresence>

          <input
            type="email"
            placeholder="Email address"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-white/10 text-white placeholder-white/30 focus:outline-none focus:border-brand-500/50 text-sm"
          />

          <input
            type="password"
            placeholder="Password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-surface-800 border border-white/10 text-white placeholder-white/30 focus:outline-none focus:border-brand-500/50 text-sm"
          />

          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white font-semibold text-sm transition-colors"
          >
            {loading
              ? 'Loading…'
              : tab === 'sign-in'
              ? 'Sign In'
              : 'Create Account'}
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
}
