/**
 * Library drawer (spec §6.7): a sheet over the viewer — right-anchored on
 * desktop, bottom sheet on phones. Header "Stories" + count, a scrollable list
 * of StoryCards, an optional Bookmarks segment, and a sticky brass "New story"
 * at the foot. Closes on backdrop tap, the close button, Escape, or selecting a
 * story.
 *
 * The panel surface is a story-surface element (`--story-bg`); the New-story
 * action and close button are chrome.
 */

import React, { useEffect, useState } from 'react';

import IconClose from '../icons/IconClose';
import { Story } from '../story/storyTypes';
import StoryCard from './StoryCard';

import './MainDrawer.css';

export default function MainDrawer({
  open,
  onClose,
  stories,
  currentStoryId,
  onSelectStory,
  onNewStory,
  renderBookmarks,
}: {
  open: boolean;
  onClose: () => void;
  stories: Story[];
  currentStoryId: number | null;
  onSelectStory: (story: Story) => void;
  onNewStory: () => void;
  /** When provided, a Bookmarks segment is shown (wired in M4). */
  renderBookmarks?: () => React.ReactNode;
}) {
  const [view, setView] = useState<'stories' | 'bookmarks'>('stories');

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Reset to the Stories tab whenever the drawer reopens.
  useEffect(() => {
    if (open) setView('stories');
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="drawer"
      role="dialog"
      aria-modal="true"
      aria-label="Library"
    >
      <div className="drawer__backdrop" onClick={onClose} />
      <div className="drawer__panel" data-story-theme="atelier">
        <div className="drawer__header">
          {renderBookmarks ? (
            <div className="drawer__segments" role="tablist">
              <button
                role="tab"
                aria-selected={view === 'stories'}
                className={`drawer__segment${
                  view === 'stories' ? ' is-active' : ''
                }`}
                onClick={() => setView('stories')}
              >
                Stories
                <span className="drawer__count">{stories.length}</span>
              </button>
              <button
                role="tab"
                aria-selected={view === 'bookmarks'}
                className={`drawer__segment${
                  view === 'bookmarks' ? ' is-active' : ''
                }`}
                onClick={() => setView('bookmarks')}
              >
                Bookmarks
              </button>
            </div>
          ) : (
            <h2 className="type-section-title drawer__heading">
              Stories <span className="drawer__count">{stories.length}</span>
            </h2>
          )}
          <button
            className="drawer__close"
            onClick={onClose}
            aria-label="Close library"
          >
            <IconClose />
          </button>
        </div>

        <div className="drawer__body">
          {view === 'stories' ? (
            stories.length === 0 ? (
              <p className="clio-muted">No stories yet.</p>
            ) : (
              <ul className="drawer__list">
                {stories.map(s => (
                  <li key={s.id}>
                    <StoryCard
                      story={s}
                      isCurrent={s.id === currentStoryId}
                      onSelect={onSelectStory}
                    />
                  </li>
                ))}
              </ul>
            )
          ) : (
            renderBookmarks?.()
          )}
        </div>

        <div className="drawer__footer">
          <button className="cal-button drawer__new" onClick={onNewStory}>
            New story
          </button>
        </div>
      </div>
    </div>
  );
}
