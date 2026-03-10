import { useState } from 'react';
import { motion } from 'framer-motion';
import { useConsent } from '@/hooks/useConsent';

interface ConsentModalProps {
  onComplete: () => void;
  onClose: () => void;
}

export default function ConsentModal({ onComplete, onClose }: ConsentModalProps) {
  const { giveConsent, loading, error } = useConsent();
  const [consentGiven, setConsentGiven] = useState(false);
  const [privacyAcknowledged, setPrivacyAcknowledged] = useState(false);

  const canSubmit = consentGiven && privacyAcknowledged;

  const handleSubmit = async () => {
    try {
      await giveConsent({
        consent_given: consentGiven,
        privacy_acknowledged: privacyAcknowledged,
      });
      onComplete();
    } catch {
      // Error is displayed via the hook
    }
  };

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <motion.div
        className="relative glass-card p-8 max-w-md w-full space-y-6"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
      >
        <div className="space-y-2">
          <h3 className="text-xl font-bold font-display">Privacy & Consent</h3>
          <p className="text-sm text-white/50">
            Before we can create your virtual try-on, we need your consent to process your photo.
          </p>
        </div>

        <div className="space-y-4">
          {/* AI Processing Consent — required */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={consentGiven}
              onChange={(e) => setConsentGiven(e.target.checked)}
              className="mt-1 w-4 h-4 rounded border-white/20 bg-surface-800 text-brand-500 focus:ring-brand-500/50"
            />
            <div>
              <p className="text-sm font-medium text-white group-hover:text-brand-400 transition-colors">
                Body & Image Processing
                <span className="text-red-400 ml-1">*</span>
              </p>
              <p className="text-xs text-white/40">
                I consent to my photo being processed by AI models to estimate body shape and generate a virtual try-on image.
              </p>
            </div>
          </label>

          {/* Privacy Acknowledgement — required */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={privacyAcknowledged}
              onChange={(e) => setPrivacyAcknowledged(e.target.checked)}
              className="mt-1 w-4 h-4 rounded border-white/20 bg-surface-800 text-brand-500 focus:ring-brand-500/50"
            />
            <div>
              <p className="text-sm font-medium text-white group-hover:text-brand-400 transition-colors">
                Privacy Policy
                <span className="text-red-400 ml-1">*</span>
              </p>
              <p className="text-xs text-white/40">
                I have read and acknowledge the privacy policy regarding how my data is stored and processed.
              </p>
            </div>
          </label>
        </div>

        <p className="text-[11px] text-white/20">
          * Required. You can withdraw consent and request data deletion at any time.
        </p>

        {error && (
          <p className="text-sm text-red-400">{error}</p>
        )}

        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl border border-white/10 text-white/50 hover:text-white/80 text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit || loading}
            className="px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-30 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors"
          >
            {loading ? 'Saving…' : 'I Consent'}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
