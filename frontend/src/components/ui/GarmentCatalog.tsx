import { useState } from 'react';
import { motion } from 'framer-motion';
import { useGarments } from '@/hooks/useGarments';
import { useTryOnStore } from '@/stores/useTryOnStore';
import { GarmentCategory } from '@/types';
import ScrapeModal from './ScrapeModal';

const CATEGORIES = [
  { key: null, label: 'All' },
  { key: GarmentCategory.UpperBody, label: 'Tops' },
  { key: GarmentCategory.LowerBody, label: 'Bottoms' },
  { key: GarmentCategory.Dresses, label: 'Dresses' },
];

export default function GarmentCatalog() {
  const {
    garments,
    loading,
    error,
    page,
    totalPages,
    category,
    setCategory,
    nextPage,
    prevPage,
    refresh,
  } = useGarments();

  const selectedGarmentId = useTryOnStore((s) => s.selectedGarmentId);
  const selectGarment = useTryOnStore((s) => s.selectGarment);
  const [scrapeOpen, setScrapeOpen] = useState(false);

  return (
    <div className="space-y-6">
      {/* Header with scrape button */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2 flex-wrap">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.label}
              onClick={() => setCategory(cat.key)}
              className={`
                px-4 py-2 rounded-full text-sm font-medium transition-colors
                ${
                  category === cat.key
                    ? 'bg-brand-500/20 text-brand-400 border border-brand-500/40'
                    : 'bg-surface-800 text-white/50 hover:text-white/80 border border-transparent'
                }
              `}
            >
              {cat.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => setScrapeOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-surface-800 hover:bg-surface-700 border border-white/10 hover:border-brand-500/40 text-white/70 hover:text-brand-400 rounded-full text-sm font-medium transition-all"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
          </svg>
          Scrape Website
        </button>
      </div>

      <ScrapeModal
        open={scrapeOpen}
        onClose={() => setScrapeOpen(false)}
        onImported={() => refresh()}
      />

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="aspect-[3/4] bg-surface-800 rounded-xl animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="text-center py-12">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Garment grid */}
      {!loading && !error && (
        <motion.div
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
          layout
        >
          {garments.map((garment) => {
            const isSelected = selectedGarmentId === garment.id;
            return (
              <motion.button
                key={garment.id}
                layout
                onClick={() => selectGarment(garment.id)}
                className={`
                  group relative aspect-[3/4] rounded-xl overflow-hidden
                  border-2 transition-all duration-300
                  ${
                    isSelected
                      ? 'border-brand-500 ring-2 ring-brand-500/30'
                      : 'border-transparent hover:border-white/20'
                  }
                `}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <img
                  src={garment.thumbnail_url || garment.image_url}
                  alt={garment.name}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />

                {/* Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                {/* Info */}
                <div className="absolute bottom-0 left-0 right-0 p-3 translate-y-2 group-hover:translate-y-0 opacity-0 group-hover:opacity-100 transition-all duration-300">
                  <p className="text-sm font-semibold text-white truncate">
                    {garment.name}
                  </p>
                  <p className="text-xs text-white/60">{garment.brand}</p>
                </div>

                {/* Selected badge */}
                {isSelected && (
                  <motion.div
                    className="absolute top-3 right-3 w-6 h-6 rounded-full bg-brand-500 flex items-center justify-center"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                  >
                    <svg
                      className="w-3.5 h-3.5 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={3}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </motion.div>
                )}
              </motion.button>
            );
          })}
        </motion.div>
      )}

      {/* Empty state */}
      {!loading && !error && garments.length === 0 && (
        <div className="text-center py-16 space-y-3">
          <p className="text-white/40 text-lg">No garments found</p>
          <p className="text-white/20 text-sm">Try a different category</p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={prevPage}
            disabled={page <= 1}
            className="px-4 py-2 rounded-lg bg-surface-800 text-white/60 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm"
          >
            Previous
          </button>
          <span className="text-white/40 text-sm">
            {page} / {totalPages}
          </span>
          <button
            onClick={nextPage}
            disabled={page >= totalPages}
            className="px-4 py-2 rounded-lg bg-surface-800 text-white/60 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-sm"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
