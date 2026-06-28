/** Monospace frame counter "NN / MM" (1-based). A story-surface element. */

import React from 'react';

export default function FrameCounter({
  current,
  total,
}: {
  current: number; // 1-based
  total: number;
}) {
  if (total <= 0) return null;
  const pad = (n: number) => String(n).padStart(2, '0');
  return (
    <span
      className="type-counter frame-counter"
      aria-label={`Frame ${current} of ${total}`}
    >
      {pad(current)} / {pad(total)}
    </span>
  );
}
