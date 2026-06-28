/**
 * Calliope chrome toolbar (spec §6.5). A 60px rail on the left in landscape, a
 * bottom bar in portrait (inside the safe-area inset). Pure chrome — reads only
 * `--cal-*`. Buttons:
 *   immersive toggle · [add-frame · mic · camera] · | · bookmark · share · menu
 *
 * Read-only stories hide the add-frame/capture group (kept: read, bookmark,
 * share). The active immersive button fills with brass.
 */

import React from 'react';

import IconCamera from '../icons/IconCamera';
import IconFullscreen from '../icons/IconFullscreen';
import IconHeartEmpty from '../icons/IconHeartEmpty';
import IconHeartFull from '../icons/IconHeartFull';
import IconMenu from '../icons/IconMenu';
import IconMicrophone from '../icons/IconMicrophone';
import IconPlus from '../icons/IconPlus';
import IconShare from '../icons/IconShare';

import './Toolbar.css';

export type ToolbarProps = {
  isImmersive: boolean;
  onToggleImmersive: () => void;

  canAddFrame: boolean; // false in read-only / while loading
  onAddFrame: () => void;
  onCamera: () => void;
  onMic: () => void;

  canSocial: boolean; // a real frame is selected
  isBookmarked: boolean;
  onToggleBookmark: () => void;
  onShare: () => void;

  onOpenMenu: () => void;
};

export default function Toolbar({
  isImmersive,
  onToggleImmersive,
  canAddFrame,
  onAddFrame,
  onCamera,
  onMic,
  canSocial,
  isBookmarked,
  onToggleBookmark,
  onShare,
  onOpenMenu,
}: ToolbarProps) {
  const hasMic = typeof navigator !== 'undefined' && !!navigator.mediaDevices;
  return (
    <nav className="toolbar" aria-label="Story controls">
      <button
        className={`toolbar__btn${isImmersive ? ' toolbar__btn--active' : ''}`}
        onClick={onToggleImmersive}
        aria-pressed={isImmersive}
        aria-label={
          isImmersive ? 'Exit immersive mode' : 'Enter immersive mode'
        }
      >
        <IconFullscreen />
      </button>

      {canAddFrame && (
        <>
          <button
            className="toolbar__btn"
            onClick={onAddFrame}
            aria-label="Add a frame"
          >
            <IconPlus />
          </button>
          {hasMic && (
            <button
              className="toolbar__btn"
              onClick={onMic}
              aria-label="Record audio"
            >
              <IconMicrophone />
            </button>
          )}
          <button
            className="toolbar__btn"
            onClick={onCamera}
            aria-label="Take a photo"
          >
            <IconCamera />
          </button>
        </>
      )}

      {canSocial && <span className="toolbar__divider" aria-hidden="true" />}

      {canSocial && (
        <button
          className="toolbar__btn"
          onClick={onToggleBookmark}
          aria-pressed={isBookmarked}
          aria-label={isBookmarked ? 'Remove bookmark' : 'Bookmark this frame'}
        >
          {isBookmarked ? <IconHeartFull /> : <IconHeartEmpty />}
        </button>
      )}
      {canSocial && (
        <button
          className="toolbar__btn"
          onClick={onShare}
          aria-label="Share a link"
        >
          <IconShare />
        </button>
      )}

      <button
        className="toolbar__btn toolbar__btn--menu"
        onClick={onOpenMenu}
        aria-label="Open library"
      >
        <IconMenu />
      </button>
    </nav>
  );
}
