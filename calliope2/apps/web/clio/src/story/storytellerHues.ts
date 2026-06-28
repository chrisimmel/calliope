/**
 * Storyteller identity hues (spec §05). Used only by the monogram chip and the
 * lowercase storyteller name — these are *identity* accents, not theme tokens,
 * so a TS map is cleaner than CSS custom properties. Any storyteller without an
 * explicit hue falls back to `default`.
 */

export const STORYTELLER_HUES: Record<string, string> = {
  fern: '#5b7a52',
  lavender: '#8a6db0',
  narcissus: '#b08a4a',
  tamarisk: '#9a8456',
  literal: '#6f7d8a',
  default: '#8b877d',
};

export function storytellerHue(name: string | null | undefined): string {
  if (!name) return STORYTELLER_HUES.default;
  return STORYTELLER_HUES[name.toLowerCase()] ?? STORYTELLER_HUES.default;
}
