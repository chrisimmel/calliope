/**
 * Bookmarks panel for the library drawer's Bookmarks segment. Bookmarks are
 * grouped by story; selecting one opens that story. (v3 BookmarkOut keys on
 * `frame_id` but doesn't carry a frame number, so list entries open the story;
 * frame-level deep-linking from a bookmark is a follow-up that needs the number
 * on the API.)
 */

import React from 'react';

import { Bookmark, Story } from './storyTypes';

import './BookmarksList.css';

export default function BookmarksList({
  bookmarks,
  stories,
  onOpenStory,
}: {
  bookmarks: Bookmark[];
  stories: Story[];
  onOpenStory: (story: Story) => void;
}) {
  if (bookmarks.length === 0) {
    return <p className="clio-muted">No bookmarks yet.</p>;
  }

  const byStory = new Map<number, Bookmark[]>();
  for (const b of bookmarks) {
    const arr = byStory.get(b.story_id) ?? [];
    arr.push(b);
    byStory.set(b.story_id, arr);
  }

  return (
    <ul className="bookmarks">
      {[...byStory.entries()].map(([storyId, items]) => {
        const story = stories.find(s => s.id === storyId);
        const title = story?.title || `Story #${storyId}`;
        return (
          <li key={storyId} className="bookmarks__group">
            <button
              className="bookmarks__story"
              onClick={() => story && onOpenStory(story)}
              disabled={!story}
            >
              <span className="type-ui-label">{title}</span>
              <span className="bookmarks__count type-meta">{items.length}</span>
            </button>
            {items
              .filter(b => b.comments)
              .map(b => (
                <span key={b.id} className="bookmarks__note">
                  {b.comments}
                </span>
              ))}
          </li>
        );
      })}
    </ul>
  );
}
