import { useEffect, useRef, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { useTryOnStore } from '@/stores/useTryOnStore';
import type { JobStatus } from '@/types';

/**
 * Subscribes to Supabase Realtime for a specific tryon job.
 * Falls back to polling if Realtime is unavailable.
 *
 * Usage:
 *   useTryOnRealtime(jobId);
 *   // Store is updated automatically via updateJobFromRealtime
 */
export function useTryOnRealtime(jobId: string | null) {
  const updateJobFromRealtime = useTryOnStore((s) => s.updateJobFromRealtime);
  const pollJobStatus = useTryOnStore((s) => s.pollJobStatus);
  const channelRef = useRef<ReturnType<typeof supabase.channel> | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanup = useCallback(() => {
    if (channelRef.current) {
      supabase.removeChannel(channelRef.current);
      channelRef.current = null;
    }
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!jobId) {
      cleanup();
      return;
    }

    let realtimeWorking = false;

    // ─── Attempt Realtime subscription ───
    const channel = supabase
      .channel(`tryon-job-${jobId}`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'tryon_jobs',
          filter: `id=eq.${jobId}`,
        },
        (payload) => {
          realtimeWorking = true;
          const row = payload.new as Record<string, unknown>;

          // DB columns: result_photo_url, result_video_url, result_mesh_url
          const hasResult = !!row.result_photo_url;

          updateJobFromRealtime({
            status: row.status as JobStatus,
            progress: (row.progress as number) ?? 0,
            currentStep: row.current_step as string | undefined,
            result: hasResult
              ? {
                  photo_url: row.result_photo_url as string | undefined,
                  video_url: row.result_video_url as string | undefined,
                  mesh_url: row.result_mesh_url as string | undefined,
                }
              : undefined,
            error: row.error as string | undefined,
          });

          // Stop polling if realtime is working
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }

          // Unsubscribe if terminal state
          const status = row.status as string;
          if (status === 'completed' || status === 'failed') {
            setTimeout(cleanup, 500);
          }
        },
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          // Give Realtime 5s to prove it works, else start polling
          setTimeout(() => {
            if (!realtimeWorking && !pollingRef.current) {
              startPolling();
            }
          }, 5000);
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          startPolling();
        }
      });

    channelRef.current = channel;

    // ─── Fallback polling ───
    function startPolling() {
      if (pollingRef.current) return;
      pollingRef.current = setInterval(async () => {
        try {
          await pollJobStatus(jobId!);
          const job = useTryOnStore.getState().activeJob;
          if (job?.status === 'completed' || job?.status === 'failed') {
            cleanup();
          }
        } catch {
          // Silently retry next interval
        }
      }, 3000);
    }

    // Do an initial poll to get current state
    pollJobStatus(jobId).catch(() => {});

    return cleanup;
  }, [jobId, updateJobFromRealtime, pollJobStatus, cleanup]);
}
