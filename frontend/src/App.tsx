import { useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { useAuthStore } from '@/stores/useAuthStore';
import Header from '@/components/ui/Header';
import TryOnFlow from '@/components/ui/TryOnFlow';
import MyLooks from '@/components/ui/MyLooks';
import HeroLanding from '@/components/ui/HeroLanding';
import AuthModal from '@/components/ui/AuthModal';

export default function App() {
  const { initialize, user, loading } = useAuthStore();
  const [browsing, setBrowsing] = useState(false);
  const [showAuth, setShowAuth] = useState(false);

  useEffect(() => {
    initialize();
  }, [initialize]);

  // Loading state while auth initialises
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Guest landing — show unless they chose to browse
  if (!user && !browsing) {
    return (
      <div className="min-h-screen bg-surface-950 text-white">
        <Header />
        <HeroLanding
          onGetStarted={() => setShowAuth(true)}
          onBrowse={() => setBrowsing(true)}
        />
        <AnimatePresence>
          {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-950 text-white">
      <Header />

      <main>
        <Routes>
          <Route path="/" element={<TryOnFlow />} />
          <Route path="/my-looks" element={<MyLooks />} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 mt-16">
        <div className="max-w-7xl mx-auto px-4 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-white/20">
            &copy; {new Date().getFullYear()} The Dirty Laundry. AI-powered virtual try-on.
          </p>
          <div className="flex gap-6 text-xs text-white/20">
            <a href="#" className="hover:text-white/40 transition-colors">
              Privacy Policy
            </a>
            <a href="#" className="hover:text-white/40 transition-colors">
              Terms of Service
            </a>
            <a href="#" className="hover:text-white/40 transition-colors">
              Contact
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
