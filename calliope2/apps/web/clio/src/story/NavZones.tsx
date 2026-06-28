/**
 * Frame navigation affordances (spec §6.4): left/right full-height tap zones,
 * desktop chevrons in overlay circles, and arrow-key support. Horizontal swipe
 * is handled by the viewer (it owns the reading-area container). Movement
 * clamps at the first/last frame — `hasPrev`/`hasNext` hide the dead controls.
 *
 * Chrome element: the chevron circles read `--cal-*` only.
 */

import React, { useEffect } from 'react';

import IconChevronLeft from '../icons/IconChevronLeft';
import IconChevronRight from '../icons/IconChevronRight';

import './NavZones.css';

export default function NavZones({
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  enabled = true,
}: {
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  /** When false (e.g. an overlay is open), arrow keys are ignored. */
  enabled?: boolean;
}) {
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      // Don't hijack arrows while typing in a field.
      const t = e.target as HTMLElement | null;
      if (
        t &&
        (t.tagName === 'INPUT' ||
          t.tagName === 'TEXTAREA' ||
          t.isContentEditable)
      ) {
        return;
      }
      if (e.key === 'ArrowLeft' && hasPrev) {
        onPrev();
      } else if (e.key === 'ArrowRight' && hasNext) {
        onNext();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled, hasPrev, hasNext, onPrev, onNext]);

  return (
    <>
      {hasPrev && (
        <div className="nav-zone nav-zone--left">
          <button
            className="nav-zone__button"
            onClick={onPrev}
            aria-label="Previous frame"
          >
            <span className="nav-zone__chevron">
              <IconChevronLeft />
            </span>
          </button>
        </div>
      )}
      {hasNext && (
        <div className="nav-zone nav-zone--right">
          <button
            className="nav-zone__button"
            onClick={onNext}
            aria-label="Next frame"
          >
            <span className="nav-zone__chevron">
              <IconChevronRight />
            </span>
          </button>
        </div>
      )}
    </>
  );
}
