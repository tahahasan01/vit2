import { motion } from 'framer-motion';

interface PhotoViewProps {
  imageUrl: string;
  alt?: string;
}

/**
 * Hero 2D photo view — displays the synthesized VTO image.
 * Uses Framer Motion for a smooth fade-in.
 */
export default function PhotoView({ imageUrl, alt = 'Virtual Try-On Result' }: PhotoViewProps) {
  return (
    <motion.div
      className="w-full h-full min-h-[500px] flex items-center justify-center bg-surface-900 rounded-2xl overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <img
        src={imageUrl}
        alt={alt}
        className="max-w-full max-h-full object-contain"
        loading="eager"
        draggable={false}
      />
    </motion.div>
  );
}
