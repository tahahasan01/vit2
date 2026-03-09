interface FallbackStateProps {
  title?: string;
  message?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

/**
 * Generic empty/error/fallback state component.
 */
export default function FallbackState({
  title = 'Nothing here yet',
  message = 'Content will appear once available.',
  action,
}: FallbackStateProps) {
  return (
    <div className="w-full h-full min-h-[400px] flex flex-col items-center justify-center gap-4 text-center p-8">
      <div className="w-16 h-16 rounded-2xl bg-surface-800 flex items-center justify-center">
        <svg
          className="w-8 h-8 text-white/20"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
          />
        </svg>
      </div>
      <div className="space-y-1">
        <p className="text-white/60 font-medium">{title}</p>
        <p className="text-sm text-white/30">{message}</p>
      </div>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-2 px-5 py-2 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
