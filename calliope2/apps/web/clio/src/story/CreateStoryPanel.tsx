/**
 * Create-story sheet (spec §6.4 / §07). A modal listing storytellers as
 * hue-chipped options (experimental ones only when `allowExperimental`), a
 * "Begin from" segmented control (A photo · Spoken words · Thin air), and a
 * brass "Begin story". Selection only — the viewer performs the create and,
 * for photo/audio, opens capture first.
 */

import React, { useEffect, useMemo, useState } from 'react';

import StorytellerChip from '../components/StorytellerChip';
import IconClose from '../icons/IconClose';
import { FrameSeedMediaType, Storyteller } from './storyTypes';

import './CreateStoryPanel.css';

const BEGIN_OPTIONS: { value: FrameSeedMediaType; label: string }[] = [
  { value: 'photo', label: 'A photo' },
  { value: 'audio', label: 'Spoken words' },
  { value: 'none', label: 'Thin air' },
];

export default function CreateStoryPanel({
  open,
  onClose,
  storytellers,
  allowExperimental,
  defaultStrategy,
  onBegin,
  pending,
  error,
}: {
  open: boolean;
  onClose: () => void;
  storytellers: Storyteller[];
  allowExperimental: boolean;
  defaultStrategy: string | null;
  onBegin: (storyteller: string, beginFrom: FrameSeedMediaType) => void;
  pending: boolean;
  error: string | null;
}) {
  const visible = useMemo(
    () => storytellers.filter(s => allowExperimental || !s.experimental),
    [storytellers, allowExperimental]
  );

  const [storyteller, setStoryteller] = useState<string>('');
  const [beginFrom, setBeginFrom] = useState<FrameSeedMediaType>('none');

  // Default selection: ?strategy / persisted → first available.
  useEffect(() => {
    if (!open || visible.length === 0) return;
    const preferred =
      (defaultStrategy &&
        visible.find(s => s.name === defaultStrategy)?.name) ||
      visible[0].name;
    setStoryteller(prev => prev || preferred);
  }, [open, visible, defaultStrategy]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !pending) onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, pending, onClose]);

  if (!open) return null;

  const hasCamera =
    typeof navigator !== 'undefined' && !!navigator.mediaDevices;

  return (
    <div
      className="create-modal"
      role="dialog"
      aria-modal="true"
      aria-label="New story"
    >
      <div
        className="create-modal__backdrop"
        onClick={() => !pending && onClose()}
      />
      <div className="create-modal__panel" data-story-theme="atelier">
        <div className="create-modal__header">
          <h2 className="type-section-title">New story</h2>
          <button
            className="create-modal__close"
            onClick={onClose}
            disabled={pending}
            aria-label="Close"
          >
            <IconClose />
          </button>
        </div>

        <div className="create-modal__body">
          <fieldset className="create-modal__group">
            <legend className="type-kicker">Storyteller</legend>
            <ul className="create-modal__tellers">
              {visible.map(s => (
                <li key={s.name}>
                  <button
                    className={`teller-option${
                      storyteller === s.name ? ' is-selected' : ''
                    }`}
                    onClick={() => setStoryteller(s.name)}
                    aria-pressed={storyteller === s.name}
                  >
                    <StorytellerChip name={s.name} size="md" />
                    {s.description && (
                      <span className="teller-option__desc">
                        {s.description}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </fieldset>

          <fieldset className="create-modal__group">
            <legend className="type-kicker">Begin from</legend>
            <div
              className="segmented"
              role="radiogroup"
              aria-label="Begin from"
            >
              {BEGIN_OPTIONS.map(opt => {
                const disabled = opt.value === 'photo' && !hasCamera;
                return (
                  <button
                    key={opt.value}
                    role="radio"
                    aria-checked={beginFrom === opt.value}
                    className={`segmented__option${
                      beginFrom === opt.value ? ' is-selected' : ''
                    }`}
                    disabled={disabled}
                    onClick={() => setBeginFrom(opt.value)}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          {error && <div className="clio-error">{error}</div>}
        </div>

        <div className="create-modal__footer">
          <button
            className="cal-button-ghost"
            onClick={onClose}
            disabled={pending}
          >
            Cancel
          </button>
          <button
            className="cal-button"
            disabled={pending || !storyteller}
            onClick={() => onBegin(storyteller, beginFrom)}
          >
            {pending ? 'Beginning…' : 'Begin story'}
          </button>
        </div>
      </div>
    </div>
  );
}
