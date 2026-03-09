import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import type { Garment, GarmentCategory } from '@/types';

interface UseGarmentsReturn {
  garments: Garment[];
  loading: boolean;
  error: string | null;
  page: number;
  totalPages: number;
  category: GarmentCategory | null;
  setCategory: (cat: GarmentCategory | null) => void;
  nextPage: () => void;
  prevPage: () => void;
  refresh: () => Promise<void>;
}

export function useGarments(perPage = 20): UseGarmentsReturn {
  const [garments, setGarments] = useState<Garment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [category, setCategory] = useState<GarmentCategory | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / perPage));

  const fetchGarments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getGarments(page, perPage, category ?? undefined);
      setGarments(res.garments);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load garments');
    } finally {
      setLoading(false);
    }
  }, [page, perPage, category]);

  useEffect(() => {
    fetchGarments();
  }, [fetchGarments]);

  // Reset page when category changes
  useEffect(() => {
    setPage(1);
  }, [category]);

  const nextPage = useCallback(() => {
    setPage((p) => Math.min(p + 1, totalPages));
  }, [totalPages]);

  const prevPage = useCallback(() => {
    setPage((p) => Math.max(p - 1, 1));
  }, []);

  return {
    garments,
    loading,
    error,
    page,
    totalPages,
    category,
    setCategory,
    nextPage,
    prevPage,
    refresh: fetchGarments,
  };
}
