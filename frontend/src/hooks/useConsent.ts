import { useCallback, useState } from 'react';
import { useAuthStore } from '@/stores/useAuthStore';
import type { ConsentPayload } from '@/types';

interface UseConsentReturn {
  consentGiven: boolean;
  loading: boolean;
  error: string | null;
  giveConsent: (consent: ConsentPayload) => Promise<void>;
  needsConsent: boolean;
}

/**
 * Hook for managing GDPR consent flow (Layer 5 — Privacy & Consent).
 * Must be called before any try-on can begin.
 */
export function useConsent(): UseConsentReturn {
  const consentGiven = useAuthStore((s) => s.consentGiven);
  const user = useAuthStore((s) => s.user);
  const recordConsent = useAuthStore((s) => s.recordConsent);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsConsent = !!user && !consentGiven;

  const giveConsent = useCallback(
    async (consent: ConsentPayload) => {
      setLoading(true);
      setError(null);
      try {
        await recordConsent(consent);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to record consent';
        setError(msg);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [recordConsent],
  );

  return { consentGiven, loading, error, giveConsent, needsConsent };
}
