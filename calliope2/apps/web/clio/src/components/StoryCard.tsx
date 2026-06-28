/**
 * Library row: thumbnail + Newsreader title + storyteller chip, with a current
 * marker and optional bookmark glyph. The whole row is the tap target. A
 * story-surface element (reads `--story-*`); the bookmark accent is brass.
 */

import React from 'react';

import IconHeartFull from '../icons/IconHeartFull';
import { Story } from '../story/storyTypes';
import StorytellerChip from './StorytellerChip';

import './StoryCard.css';

export default function StoryCard({
  story,
  isCurrent,
  onSelect,
}: {
  story: Story;
  isCurrent: boolean;
  onSelect: (story: Story) => void;
}) {
  const title = story.title || `Story #${story.id}`;
  return (
    <button
      className={`story-card${isCurrent ? ' story-card--current' : ''}`}
      onClick={() => onSelect(story)}
      aria-current={isCurrent ? 'true' : undefined}
    >
      <span className="story-card__thumb">
        {story.thumbnail_url ? (
          <img src={story.thumbnail_url} alt="" loading="lazy" />
        ) : (
          <span className="story-card__thumb-empty" aria-hidden="true" />
        )}
      </span>
      <span className="story-card__meta">
        <span className="type-story-title story-card__title">{title}</span>
        <span className="story-card__sub">
          <StorytellerChip name={story.storyteller_name} />
          {story.is_bookmarked && (
            <span className="story-card__bookmark" aria-label="Bookmarked">
              <IconHeartFull />
            </span>
          )}
        </span>
      </span>
    </button>
  );
}
