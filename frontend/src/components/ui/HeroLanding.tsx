import { motion } from 'framer-motion';

interface HeroLandingProps {
  onGetStarted: () => void;
  onBrowse: () => void;
}

const FEATURES = [
  { icon: '✨', label: 'AI-Powered Try-On' },
  { icon: '🔄', label: '360° 3D Preview' },
  { icon: '⚡', label: 'Instant Results' },
  { icon: '🔒', label: 'Privacy First' },
];

export default function HeroLanding({ onGetStarted, onBrowse }: HeroLandingProps) {
  return (
    <div className="relative min-h-[calc(100vh-4rem)] flex flex-col items-center justify-center px-4 overflow-hidden">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-brand-500/8 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 left-1/3 w-[400px] h-[400px] bg-brand-600/5 rounded-full blur-[100px]" />
      </div>

      <motion.div
        className="relative z-10 text-center max-w-2xl mx-auto space-y-8"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
      >
        {/* Badge */}
        <motion.div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
          <span className="text-xs font-medium text-brand-400">
            AI Virtual Try-On — Now Live
          </span>
        </motion.div>

        {/* Headline */}
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-display font-bold leading-tight tracking-tight">
          <span className="text-white">Try Before</span>
          <br />
          <span className="bg-gradient-to-r from-brand-400 to-brand-600 bg-clip-text text-transparent">
            You Buy
          </span>
        </h1>

        {/* Subtext */}
        <p className="text-lg text-white/50 max-w-md mx-auto leading-relaxed">
          See how our streetwear looks on you — powered by AI. Upload a photo,
          pick a garment, get a photorealistic try-on in seconds.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <motion.button
            onClick={onGetStarted}
            className="px-8 py-3.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white font-semibold text-base transition-colors shadow-lg shadow-brand-500/20"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            Get Started — It's Free
          </motion.button>

          <motion.button
            onClick={onBrowse}
            className="px-8 py-3.5 rounded-xl border border-white/10 hover:border-white/20 text-white/60 hover:text-white/80 font-medium text-base transition-colors"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            Browse Collection
          </motion.button>
        </div>

        {/* Feature Pills */}
        <motion.div
          className="flex flex-wrap items-center justify-center gap-3 pt-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {FEATURES.map((feat) => (
            <div
              key={feat.label}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/5 text-xs text-white/40"
            >
              <span>{feat.icon}</span>
              <span>{feat.label}</span>
            </div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
}
