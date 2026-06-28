/**
 * Cross-fade frame renderer (spec §6.3, §09). Frames are absolutely stacked;
 * only the current frame sits at opacity 1, neighbors are mounted at opacity 0
 * (which also preloads their media). Moving frames is a 300ms opacity
 * cross-fade — not a slide. `skipAnimation` (deep-link / bookmark jump) cuts the
 * transition to instant, as does `prefers-reduced-motion` (handled in tokens).
 *
 * Images fade 0→1 once loaded (with a cached-image guard); video frames use the
 * looping `VideoLoop`, playing only when current. Video is preferred when both
 * media are present. Media is always `object-fit: contain` on `--story-bg`.
 */

import React, { useEffect, useRef, useState } from 'react';

import VideoLoop from '../components/VideoLoop';
import { Frame } from './storyTypes';

import './FrameStack.css';

function FrameImage({
  frame,
  isVisible,
}: {
  frame: Frame;
  isVisible: boolean;
}) {
  const ref = useRef<HTMLImageElement>(null);
  const [loaded, setLoaded] = useState(false);

  // Cached images may already be complete before onLoad attaches.
  useEffect(() => {
    const el = ref.current;
    if (el && el.complete && el.naturalWidth > 0) setLoaded(true);
  }, [frame.image_url]);

  return (
    <img
      ref={ref}
      className="frame-media frame-media--image"
      src={frame.image_url ?? undefined}
      alt={frame.situation ?? `Frame ${frame.number}`}
      style={{ opacity: loaded ? 1 : 0 }}
      onLoad={() => setLoaded(true)}
      // Current frame is fetched eagerly; neighbors lazily preload.
      loading={isVisible ? 'eager' : 'lazy'}
      decoding="async"
    />
  );
}

export default function FrameStack({
  frames,
  selectedIndex,
  skipAnimation,
}: {
  frames: Frame[];
  selectedIndex: number;
  skipAnimation: boolean;
}) {
  // Render a small window around the current frame: enough to cross-fade the
  // outgoing/incoming pair and warm the immediate neighbors.
  const windowFrames = frames
    .map((frame, index) => ({ frame, index }))
    .filter(({ index }) => Math.abs(index - selectedIndex) <= 1);

  return (
    <div className="frame-stack">
      {windowFrames.map(({ frame, index }) => {
        const isVisible = index === selectedIndex;
        const hasVideo = !!frame.video_url;
        return (
          <div
            key={frame.id}
            className="frame-stack__frame"
            style={{
              opacity: isVisible ? 1 : 0,
              transition: skipAnimation
                ? 'none'
                : `opacity var(--t-frame) var(--ease)`,
            }}
            aria-hidden={!isVisible}
          >
            {hasVideo ? (
              <VideoLoop
                videoSrc={frame.video_url as string}
                imageUrl={frame.image_url ?? ''}
                isVisible={isVisible}
              />
            ) : frame.image_url ? (
              <FrameImage frame={frame} isVisible={isVisible} />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
