import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import type { ScrapedGarment } from '@/types';

interface ScrapeModalProps {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}

export default function ScrapeModal({ open, onClose, onImported }: ScrapeModalProps) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ScrapedGarment[] | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [importing, setImporting] = useState(false);
  const [imported, setImported] = useState(false);

  const reset = () => {
    setUrl('');
    setLoading(false);
    setError(null);
    setResults(null);
    setSelected(new Set());
    setImporting(false);
    setImported(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleScrape = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    setSelected(new Set());
    setImported(false);

    try {
      const res = await api.scrapeGarments(url.trim(), false);
      if (res.garments.length === 0) {
        setError('No garments found on this page. Try a product listing page.');
      } else {
        setResults(res.garments);
        // Select all by default
        setSelected(new Set(res.garments.map((_, i) => i)));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scrape failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const toggleAll = () => {
    if (!results) return;
    if (selected.size === results.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(results.map((_, i) => i)));
    }
  };

  const handleImport = async () => {
    if (!url.trim()) return;
    setImporting(true);
    setError(null);

    try {
      const res = await api.scrapeGarments(url.trim(), true);
      setImported(true);
      if (res.errors.length > 0) {
        setError(`Imported ${res.imported} garments. ${res.errors.length} failed.`);
      }
      onImported();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={handleClose} />

          {/* Modal */}
          <motion.div
            className="relative w-full max-w-2xl max-h-[85vh] bg-surface-900 border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-white/10">
              <div>
                <h2 className="text-lg font-semibold text-white">Scrape Garments</h2>
                <p className="text-sm text-white/40 mt-0.5">
                  Paste any clothing website URL to extract garments
                </p>
              </div>
              <button
                onClick={handleClose}
                className="p-1.5 rounded-lg hover:bg-white/10 text-white/40 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* URL Input */}
            <div className="p-5 border-b border-white/10">
              <div className="flex gap-3">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleScrape()}
                  placeholder="https://example.com/collections/dresses"
                  className="flex-1 px-4 py-2.5 bg-surface-800 border border-white/10 rounded-xl text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-brand-500/50 text-sm"
                  disabled={loading || importing}
                />
                <button
                  onClick={handleScrape}
                  disabled={!url.trim() || loading || importing}
                  className="px-5 py-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-colors whitespace-nowrap"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                        <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                      </svg>
                      Scraping…
                    </span>
                  ) : (
                    'Scrape'
                  )}
                </button>
              </div>
              <p className="text-xs text-white/30 mt-2">
                Works with Shopify, WooCommerce, Magento, Zara, H&M, ASOS, and most clothing sites
              </p>
            </div>

            {/* Results / Error */}
            <div className="flex-1 overflow-y-auto p-5">
              {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                  {error}
                </div>
              )}

              {imported && !error && (
                <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-xl text-green-400 text-sm">
                  Garments imported to your catalog successfully!
                </div>
              )}

              {results && results.length > 0 && (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm text-white/50">
                      Found {results.length} garment{results.length > 1 ? 's' : ''}
                    </span>
                    <button
                      onClick={toggleAll}
                      className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
                    >
                      {selected.size === results.length ? 'Deselect all' : 'Select all'}
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {results.map((g, idx) => {
                      const isSelected = selected.has(idx);
                      return (
                        <button
                          key={idx}
                          onClick={() => toggleSelect(idx)}
                          className={`relative rounded-xl overflow-hidden border-2 transition-all text-left ${
                            isSelected
                              ? 'border-brand-500 ring-1 ring-brand-500/30'
                              : 'border-white/5 hover:border-white/20'
                          }`}
                        >
                          {g.image_url ? (
                            <img
                              src={g.image_url}
                              alt={g.name}
                              className="w-full aspect-[3/4] object-cover"
                              loading="lazy"
                            />
                          ) : (
                            <div className="w-full aspect-[3/4] bg-surface-800 flex items-center justify-center">
                              <span className="text-white/20 text-xs">No image</span>
                            </div>
                          )}
                          <div className="p-2">
                            <p className="text-xs font-medium text-white truncate">{g.name}</p>
                            <p className="text-xs text-white/40 truncate">
                              {g.brand}{g.price ? ` · ${g.price}` : ''}
                            </p>
                            <span className="inline-block mt-1 px-1.5 py-0.5 text-[10px] rounded bg-white/5 text-white/30">
                              {g.category.replace('_', ' ')}
                            </span>
                          </div>
                          {isSelected && (
                            <div className="absolute top-2 right-2 w-5 h-5 bg-brand-500 rounded-full flex items-center justify-center">
                              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                              </svg>
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </>
              )}

              {!loading && !results && !error && (
                <div className="text-center py-12 text-white/20">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <p className="text-sm">Enter a URL to start scraping</p>
                </div>
              )}
            </div>

            {/* Footer actions */}
            {results && results.length > 0 && (
              <div className="p-5 border-t border-white/10 flex items-center justify-between">
                <span className="text-sm text-white/40">
                  {selected.size} of {results.length} selected
                </span>
                <button
                  onClick={handleImport}
                  disabled={selected.size === 0 || importing || imported}
                  className="px-6 py-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-colors"
                >
                  {importing ? (
                    <span className="flex items-center gap-2">
                      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                        <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                      </svg>
                      Importing…
                    </span>
                  ) : imported ? (
                    'Imported!'
                  ) : (
                    `Import ${selected.size} to Catalog`
                  )}
                </button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
