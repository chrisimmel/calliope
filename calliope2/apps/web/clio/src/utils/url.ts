/**
 * Sticky URL query params. The anonymous `client_id`/`sparrow_id` model from v1
 * is gone (auth is Firebase). What remains sticky across every internal
 * navigation:
 *   - `strategy` — preselect/force a storyteller (also persisted to localStorage)
 *   - `story`    — `<id>:<frame>` deep link on a fresh load
 *   - `x`        — experimental storytellers (x=1)
 */

const STICKY_KEYS = ['strategy', 'story', 'x'] as const;
const STRATEGY_STORAGE_KEY = 'calliope.strategy';

/** Current sticky params as a query string (leading `?`), or '' if none. */
export function stickyQuery(search: string = window.location.search): string {
  const incoming = new URLSearchParams(search);
  const kept = new URLSearchParams();
  for (const key of STICKY_KEYS) {
    const v = incoming.get(key);
    if (v !== null) kept.set(key, v);
  }
  const s = kept.toString();
  return s ? `?${s}` : '';
}

/** Append the preserved sticky params to a path. */
export function withParams(path: string, search?: string): string {
  return `${path}${stickyQuery(search)}`;
}

/** Experimental storytellers enabled (?x=1). */
export function getAllowExperimental(
  search: string = window.location.search
): boolean {
  return new URLSearchParams(search).get('x') === '1';
}

/** Default storyteller: URL `?strategy=` (also persisted) → localStorage. */
export function getDefaultStrategy(
  search: string = window.location.search
): string | null {
  const fromUrl = new URLSearchParams(search).get('strategy');
  if (fromUrl) {
    try {
      window.localStorage.setItem(STRATEGY_STORAGE_KEY, fromUrl);
    } catch {
      /* storage may be unavailable (private mode) — non-fatal */
    }
    return fromUrl;
  }
  try {
    return window.localStorage.getItem(STRATEGY_STORAGE_KEY);
  } catch {
    return null;
  }
}

/** Parse `?story=<id>:<frame>` into a deep-link target, if present. */
export function getDefaultStoryAndFrame(
  search: string = window.location.search
): { storyId: number; frame: number } | null {
  const raw = new URLSearchParams(search).get('story');
  if (!raw) return null;
  const [idPart, framePart] = raw.split(':');
  const storyId = parseInt(idPart, 10);
  if (Number.isNaN(storyId)) return null;
  const frame = framePart ? parseInt(framePart, 10) : 1;
  return { storyId, frame: Number.isNaN(frame) ? 1 : frame };
}
