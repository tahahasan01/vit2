import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { useAuthStore } from '@/stores/useAuthStore';
import Header from '@/components/ui/Header';
import TryOnFlow from '@/components/ui/TryOnFlow';
import MyLooks from '@/components/ui/MyLooks';

export default function App() {
  const initialize = useAuthStore((s) => s.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

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
