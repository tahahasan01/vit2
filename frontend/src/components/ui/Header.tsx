import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { useAuthStore } from '@/stores/useAuthStore';
import AuthModal from './AuthModal';

const NAV_ITEMS = [
  { path: '/', label: 'Try On' },
  { path: '/my-looks', label: 'My Looks' },
];

export default function Header() {
  const { user, signOut } = useAuthStore();
  const location = useLocation();
  const [showAuth, setShowAuth] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 bg-surface-950/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center font-display font-bold text-sm text-white">
              DL
            </div>
            <span className="font-display font-semibold text-white/90 group-hover:text-white transition-colors hidden sm:block">
              The Dirty Laundry
            </span>
          </Link>

          {/* Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const isActive = location.pathname === item.path;
              const needsAuth = item.path === '/my-looks' && !user;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`
                    relative px-4 py-2 rounded-lg text-sm font-medium transition-colors
                    ${needsAuth ? 'text-white/20 cursor-default' : isActive ? 'text-white' : 'text-white/40 hover:text-white/70'}
                  `}
                >
                  {isActive && (
                    <motion.div
                      layoutId="nav-pill"
                      className="absolute inset-0 bg-white/5 rounded-lg"
                      transition={{ type: 'spring', bounce: 0.2, duration: 0.4 }}
                    />
                  )}
                  <span className="relative z-10">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Auth */}
          <div className="flex items-center gap-3">
            {user ? (
              <div className="relative">
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/5 transition-colors"
                >
                  <div className="w-7 h-7 rounded-full bg-brand-500/20 border border-brand-500/40 flex items-center justify-center text-xs font-semibold text-brand-400">
                    {(user.email ?? 'U')[0]!.toUpperCase()}
                  </div>
                  <span className="text-sm text-white/70 hidden sm:block">
                    {user.email?.split('@')[0] || 'User'}
                  </span>
                </button>

                <AnimatePresence>
                  {showMenu && (
                    <motion.div
                      className="absolute right-0 top-12 w-48 glass-card p-2 space-y-1"
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                    >
                      <div className="px-3 py-2 text-xs text-white/30 truncate">
                        {user.email}
                      </div>
                      <hr className="border-white/5" />
                      {/* Mobile nav items */}
                      <div className="md:hidden">
                        {NAV_ITEMS.map((item) => (
                          <Link
                            key={item.path}
                            to={item.path}
                            onClick={() => setShowMenu(false)}
                            className="block px-3 py-2 rounded-lg text-sm text-white/60 hover:text-white hover:bg-white/5 transition-colors"
                          >
                            {item.label}
                          </Link>
                        ))}
                        <hr className="border-white/5 my-1" />
                      </div>
                      <button
                        onClick={() => {
                          signOut();
                          setShowMenu(false);
                        }}
                        className="w-full text-left px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                      >
                        Sign Out
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <button
                onClick={() => setShowAuth(true)}
                className="px-4 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold transition-colors"
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      </header>

      <AnimatePresence>
        {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </AnimatePresence>
    </>
  );
}
