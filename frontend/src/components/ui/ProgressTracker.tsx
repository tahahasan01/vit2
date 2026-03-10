import { motion } from 'framer-motion';
import { PIPELINE_STEPS, type PipelineStep, type JobStatus } from '@/types';
import { useTryOnStore } from '@/stores/useTryOnStore';

function getStepStatus(
  stepKey: string,
  currentStatus: JobStatus,
): PipelineStep['status'] {
  const order = PIPELINE_STEPS.map((s) => s.key);
  const currentIdx = order.indexOf(currentStatus);
  const stepIdx = order.indexOf(stepKey);

  if (currentStatus === 'failed') {
    // Mark up to current as completed, current as failed
    if (stepIdx < currentIdx) return 'completed';
    if (stepIdx === currentIdx) return 'failed';
    return 'pending';
  }

  if (stepIdx < currentIdx) return 'completed';
  if (stepIdx === currentIdx) return 'active';
  return 'pending';
}

const statusColors: Record<PipelineStep['status'], string> = {
  pending: 'bg-surface-700',
  active: 'bg-brand-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
};

const statusTextColors: Record<PipelineStep['status'], string> = {
  pending: 'text-white/30',
  active: 'text-brand-400',
  completed: 'text-green-400',
  failed: 'text-red-400',
};

export default function ProgressTracker() {
  const activeJob = useTryOnStore((s) => s.activeJob);

  if (!activeJob) return null;

  const currentStatus = activeJob.status;
  const progress = activeJob.progress;

  return (
    <div className="glass-card p-6 space-y-4">
      {/* Overall progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs font-medium">
          <span className="text-white/60">Processing</span>
          <span className="text-white/40">{Math.round(progress)}%</span>
        </div>
        <div className="h-1.5 bg-surface-800 rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${
              currentStatus === 'failed'
                ? 'bg-red-500'
                : 'bg-gradient-to-r from-brand-400 to-brand-600'
            } ${
              currentStatus !== 'completed' && currentStatus !== 'failed'
                ? 'progress-stripe'
                : ''
            }`}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Step indicators */}
      <div className="flex items-start justify-between gap-2">
        {PIPELINE_STEPS.map((step, i) => {
          const status = getStepStatus(step.key, currentStatus);
          return (
            <div key={step.key} className="flex-1 flex flex-col items-center gap-2">
              {/* Dot + connector */}
              <div className="flex items-center w-full">
                {i > 0 && (
                  <div
                    className={`flex-1 h-0.5 ${
                      status === 'completed' || status === 'active'
                        ? 'bg-brand-500/50'
                        : 'bg-surface-700'
                    }`}
                  />
                )}
                <motion.div
                  className={`w-3 h-3 rounded-full flex-shrink-0 ${statusColors[status]}`}
                  animate={
                    status === 'active'
                      ? { scale: [1, 1.3, 1] }
                      : { scale: 1 }
                  }
                  transition={
                    status === 'active'
                      ? { duration: 1, repeat: Infinity }
                      : {}
                  }
                />
                {i < PIPELINE_STEPS.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 ${
                      status === 'completed'
                        ? 'bg-brand-500/50'
                        : 'bg-surface-700'
                    }`}
                  />
                )}
              </div>

              {/* Label */}
              <div className="text-center">
                <p
                  className={`text-[11px] font-medium ${statusTextColors[status]}`}
                >
                  {step.label}
                </p>
                {status === 'active' && (
                  <motion.p
                    className="text-[10px] text-white/40 mt-0.5"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    {step.description}
                  </motion.p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Error message */}
      {activeJob.error && (
        <motion.div
          className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {activeJob.error}
        </motion.div>
      )}
    </div>
  );
}
