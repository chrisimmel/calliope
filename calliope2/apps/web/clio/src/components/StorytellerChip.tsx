/**
 * Storyteller identity chip: a hue-tinted monogram square + the storyteller's
 * lowercase name. The hue comes from `storytellerHues`. Used in the story
 * viewer kicker, library cards, and the create sheet's storyteller list.
 */

import React from 'react';

import { storytellerHue } from '../story/storytellerHues';

import './StorytellerChip.css';

export default function StorytellerChip({
  name,
  size = 'sm',
}: {
  name: string | null | undefined;
  /** `sm` for inline kicker/cards; `md` for the create sheet's option rows. */
  size?: 'sm' | 'md';
}) {
  const label = (name ?? 'unknown').toLowerCase();
  const hue = storytellerHue(name);
  const monogram = label.charAt(0).toUpperCase();

  return (
    <span className={`storyteller-chip storyteller-chip--${size}`}>
      <span
        className="storyteller-chip__monogram"
        style={{ backgroundColor: hue }}
        aria-hidden="true"
      >
        {monogram}
      </span>
      <span className="storyteller-chip__name">{label}</span>
    </span>
  );
}
