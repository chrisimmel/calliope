/**
 * The signed-in reading surface. Owns the story/frame/UI state machine and
 * composes the media (FrameStack), the text pane, navigation (NavZones + swipe
 * + arrows), the chrome Toolbar, and — wired in later milestones — the library
 * drawer, create sheet, capture, bookmarks, and toasts.
 *
 * Routing: `/clio/story/:slug/:frame` (1-based) is canonical; `/clio/stories/
 * :storyId/:frame` is the transitional id form for freshly created stories that
 * don't have a slug yet. `/clio/` resolves the most-recent story.
 *
 * This component hosts `data-story-theme="atelier"` — the story container that
 * scopes Layer B tokens. A future per-story theme only re-scopes this subtree.
 */

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useSwipeable } from 'react-swipeable';

import FrameCounter from '../components/FrameCounter';
import Loader from '../components/Loader';
import MainDrawer from '../components/MainDrawer';
import StorytellerChip from '../components/StorytellerChip';
import Toast, { ToastState } from '../components/Toast';
import Toolbar from '../components/Toolbar';
import AudioCapture from '../audio/AudioCapture';
import PhotoCapture from '../photo/PhotoCapture';
import {
  createBookmark,
  createFrame,
  createStory,
  deleteBookmark,
  getStory,
  getStoryBySlug,
  listBookmarks,
  listStories,
  listStorytellers,
} from '../services/v3Api';
import {
  getAllowExperimental,
  getDefaultStoryAndFrame,
  getDefaultStrategy,
  withParams,
} from '../utils/url';
import BookmarksList from './BookmarksList';
import CreateStoryPanel from './CreateStoryPanel';
import FrameStack from './FrameStack';
import NavZones from './NavZones';
import StoryStatusMonitor from './StoryStatusMonitor';
import {
  Bookmark,
  Frame,
  FrameSeedMediaType,
  Story,
  StoryDetail,
  Storyteller,
} from './storyTypes';

import './StoryViewer.css';

const OVERLAY_IDLE_MS = 2000;

export default function StoryViewer({ userId }: { userId: string }) {
  const navigate = useNavigate();
  const params = useParams<{
    slug?: string;
    storyId?: string;
    frame?: string;
  }>();

  const [story, setStory] = useState<StoryDetail | null>(null);
  const [stories, setStories] = useState<Story[]>([]);
  const [selectedFrameNumber, setSelectedFrameNumber] = useState(0); // 0-based
  const [loadingStory, setLoadingStory] = useState(true);
  const [skipAnimation, setSkipAnimation] = useState(true);
  const [isImmersive, setIsImmersive] = useState(false);
  const [showOverlays, setShowOverlays] = useState(true);
  const [drawerIsOpen, setDrawerIsOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create + capture (M3)
  const [storytellers, setStorytellers] = useState<Storyteller[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [createPending, setCreatePending] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [captureMode, setCaptureMode] = useState<null | 'photo' | 'audio'>(
    null
  );
  // Whether the next capture seeds a new story or extends the current one.
  const captureIntent = useRef<{
    kind: 'new' | 'extend';
    storyteller?: string;
  }>({
    kind: 'extend',
  });

  // Bookmarks + toasts (M4)
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [toast, setToast] = useState<ToastState | null>(null);

  const allowExperimental = getAllowExperimental();
  const defaultStrategy = getDefaultStrategy();

  const frames: Frame[] = story?.frames ?? [];
  const isReadOnly = !!story?.is_read_only;

  // --- Dynamic viewport height (mobile URL-bar jump) ---
  useEffect(() => {
    const setVh = () => {
      document.documentElement.style.setProperty(
        '--vp-height',
        `${window.innerHeight}px`
      );
    };
    setVh();
    window.addEventListener('resize', setVh);
    window.addEventListener('orientationchange', setVh);
    return () => {
      window.removeEventListener('resize', setVh);
      window.removeEventListener('orientationchange', setVh);
    };
  }, []);

  // --- Load the requested story (slug → id → most-recent) ---
  const requestedFrame = params.frame ? parseInt(params.frame, 10) : null;

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoadingStory(true);
      setError(null);
      try {
        let detail: StoryDetail | null = null;
        if (params.slug) {
          detail = await getStoryBySlug(params.slug);
        } else if (params.storyId) {
          detail = await getStory(parseInt(params.storyId, 10));
          // Promote to the canonical slug URL once we know it.
          if (detail.slug && !cancelled) {
            const f = requestedFrame ?? 1;
            navigate(withParams(`/clio/story/${detail.slug}/${f}`), {
              replace: true,
            });
          }
        } else {
          // Root: ?story=<id>:<frame> deep link → else resume most-recent.
          const deepLink = getDefaultStoryAndFrame();
          if (deepLink) {
            navigate(
              withParams(`/clio/stories/${deepLink.storyId}/${deepLink.frame}`),
              { replace: true }
            );
            return;
          }
          const list = await listStories();
          if (!cancelled) setStories(list);
          if (list.length > 0) {
            const target = list[0];
            const path = target.slug
              ? `/clio/story/${target.slug}/1`
              : `/clio/stories/${target.id}/1`;
            if (!cancelled) navigate(withParams(path), { replace: true });
            return; // a re-render with params will load it
          }
        }
        if (detail && !cancelled) {
          setStory(detail);
          const initial =
            requestedFrame && requestedFrame >= 1
              ? Math.min(requestedFrame, detail.frames.length) - 1
              : 0;
          setSkipAnimation(true);
          setSelectedFrameNumber(Math.max(0, initial));
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'failed to load story');
        }
      } finally {
        if (!cancelled) setLoadingStory(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.slug, params.storyId, userId]);

  // --- Story list for the library drawer (loaded once per session) ---
  useEffect(() => {
    let cancelled = false;
    listStories()
      .then(list => {
        if (!cancelled) setStories(list);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const openStory = useCallback(
    (target: Story) => {
      setDrawerIsOpen(false);
      const path = target.slug
        ? `/clio/story/${target.slug}/1`
        : `/clio/stories/${target.id}/1`;
      navigate(withParams(path));
    },
    [navigate]
  );

  // --- Frame selection + URL sync ---
  const selectFrame = useCallback(
    (index: number, opts?: { skip?: boolean }) => {
      if (!story) return;
      const clamped = Math.max(0, Math.min(index, frames.length - 1));
      setSkipAnimation(!!opts?.skip);
      setSelectedFrameNumber(clamped);
      const base = story.slug
        ? `/clio/story/${story.slug}`
        : `/clio/stories/${story.id}`;
      navigate(withParams(`${base}/${clamped + 1}`), { replace: true });
    },
    [story, frames.length, navigate]
  );

  const goPrev = useCallback(
    () => selectFrame(selectedFrameNumber - 1),
    [selectFrame, selectedFrameNumber]
  );
  const goNext = useCallback(
    () => selectFrame(selectedFrameNumber + 1),
    [selectFrame, selectedFrameNumber]
  );

  const hasPrev = selectedFrameNumber > 0;
  const hasNext = selectedFrameNumber < frames.length - 1;

  // --- Swipe over the reading area (mobile) ---
  const swipe = useSwipeable({
    onSwipedLeft: () => hasNext && goNext(),
    onSwipedRight: () => hasPrev && goPrev(),
    trackMouse: false,
    preventScrollOnSwipe: true,
  });

  // --- Immersive: hide all chrome; pointer movement briefly reveals it. ---
  const overlayTimer = useRef<number | null>(null);
  const revealOverlays = useCallback(() => {
    if (!isImmersive) return;
    setShowOverlays(true);
    if (overlayTimer.current) window.clearTimeout(overlayTimer.current);
    overlayTimer.current = window.setTimeout(
      () => setShowOverlays(false),
      OVERLAY_IDLE_MS
    );
  }, [isImmersive]);

  const toggleImmersive = useCallback(() => {
    setIsImmersive(prev => {
      const next = !prev;
      setShowOverlays(!next); // entering immersive hides chrome immediately
      return next;
    });
  }, []);

  useEffect(() => {
    return () => {
      if (overlayTimer.current) window.clearTimeout(overlayTimer.current);
    };
  }, []);

  // --- Storytellers for the create sheet ---
  useEffect(() => {
    listStorytellers()
      .then(setStorytellers)
      .catch(() => undefined);
  }, [userId]);

  // Re-fetch the current story and advance to the newest frame (used when a
  // generation task completes).
  const refetchCurrent = useCallback(async () => {
    if (!story) return;
    try {
      const detail = story.slug
        ? await getStoryBySlug(story.slug)
        : await getStory(story.id);
      setStory(detail);
      setSkipAnimation(true);
      setSelectedFrameNumber(Math.max(0, detail.frames.length - 1));
    } catch {
      /* leave the current frames in place on a transient refetch error */
    }
  }, [story]);

  const onStatusFailed = useCallback((message: string) => {
    setToast({ message, kind: 'error' });
  }, []);

  // --- Bookmarks ---
  useEffect(() => {
    listBookmarks()
      .then(setBookmarks)
      .catch(() => undefined);
  }, [userId]);

  const toggleBookmark = useCallback(async () => {
    const frame = frames[selectedFrameNumber];
    if (!story || !frame) return;
    const existing = bookmarks.find(b => b.frame_id === frame.id);
    try {
      if (existing) {
        await deleteBookmark(existing.id);
        setBookmarks(prev => prev.filter(b => b.id !== existing.id));
      } else {
        const created = await createBookmark({
          story_id: story.id,
          frame_id: frame.id,
        });
        setBookmarks(prev => [...prev, created]);
      }
    } catch (e) {
      setToast({
        message: e instanceof Error ? e.message : 'bookmark failed',
        kind: 'error',
      });
    }
  }, [story, frames, selectedFrameNumber, bookmarks]);

  const shareCurrentUrl = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setToast({ message: 'Link copied' });
    } catch {
      setToast({ message: 'Could not copy link', kind: 'error' });
    }
  }, []);

  // --- Create a story ---
  const doCreateStory = useCallback(
    async (storyteller: string, inputs: Record<string, unknown>) => {
      setCreatePending(true);
      setCreateError(null);
      try {
        const res = await createStory({ storyteller, inputs });
        setCreateOpen(false);
        navigate(withParams(`/clio/stories/${res.story_id}/1`));
      } catch (e) {
        setCreateError(
          e instanceof Error ? e.message : 'failed to begin story'
        );
      } finally {
        setCreatePending(false);
      }
    },
    [navigate]
  );

  const handleBegin = useCallback(
    (storyteller: string, beginFrom: FrameSeedMediaType) => {
      if (beginFrom === 'none') {
        void doCreateStory(storyteller, {});
        return;
      }
      // Seed from captured media: collect it, then create.
      captureIntent.current = { kind: 'new', storyteller };
      setCreateOpen(false);
      setCaptureMode(beginFrom === 'photo' ? 'photo' : 'audio');
    },
    [doCreateStory]
  );

  // --- Extend the current story ---
  const addFrame = useCallback(async () => {
    if (!story) return;
    try {
      await createFrame(story.id, { inputs: {} });
      // StoryStatusMonitor advances to the new frame on completion.
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed to add a frame');
    }
  }, [story]);

  const startCamera = useCallback(() => {
    captureIntent.current = { kind: 'extend' };
    setCaptureMode('photo');
  }, []);
  const startMic = useCallback(() => {
    captureIntent.current = { kind: 'extend' };
    setCaptureMode('audio');
  }, []);

  // Seeded create/extend share the same media→inputs plumbing.
  const submitSeed = useCallback(
    async (inputs: Record<string, unknown>) => {
      const intent = captureIntent.current;
      if (intent.kind === 'new' && intent.storyteller) {
        await doCreateStory(intent.storyteller, inputs);
      } else if (story) {
        try {
          await createFrame(story.id, { inputs });
        } catch (e) {
          setError(e instanceof Error ? e.message : 'failed to add a frame');
        }
      }
    },
    [doCreateStory, story]
  );

  const handlePhoto = useCallback(
    (photo: string | null) => {
      setCaptureMode(null);
      if (!photo) return;
      // The capture is a base64 data URL; the v3 API decodes data URLs for
      // `source_image_url`, so photo seeding works end to end.
      void submitSeed({ source_image_url: photo });
    },
    [submitSeed]
  );
  const handleAudio = useCallback(
    (audio: string) => {
      setCaptureMode(null);
      if (!audio) return;
      // base64 data URL; the v3 API decodes it and audio-aware storytellers
      // (e.g. `echo`) transcribe it into the narration.
      void submitSeed({ source_audio_url: audio });
    },
    [submitSeed]
  );

  // No stories yet → invite creation.
  useEffect(() => {
    if (!loadingStory && !story && stories.length === 0) {
      setCreateOpen(true);
    }
  }, [loadingStory, story, stories.length]);

  const currentFrame = frames[selectedFrameNumber];
  const chromeVisible = !isImmersive || showOverlays;

  const rootClass = useMemo(
    () =>
      [
        'story-viewer',
        isImmersive ? 'is-immersive' : '',
        chromeVisible ? 'show-overlays' : '',
      ]
        .filter(Boolean)
        .join(' '),
    [isImmersive, chromeVisible]
  );

  // --- Render ---
  if (loadingStory && !story) {
    return (
      <div
        className="story-viewer story-viewer--center"
        data-story-theme="atelier"
      >
        <Loader />
      </div>
    );
  }

  const hasFrames = !!story && frames.length > 0;

  return (
    <div
      className={rootClass}
      data-story-theme="atelier"
      onPointerMove={revealOverlays}
    >
      {hasFrames ? (
        <>
          <div
            className="story-viewer__media"
            {...swipe}
            onClick={() => {
              if (isImmersive) revealOverlays();
            }}
          >
            <FrameStack
              frames={frames}
              selectedIndex={selectedFrameNumber}
              skipAnimation={skipAnimation}
            />
          </div>

          <div className="story-viewer__text">
            <div className="story-viewer__text-inner">
              <div className="story-viewer__kicker">
                <StorytellerChip name={story?.storyteller_name} />
                <FrameCounter
                  current={selectedFrameNumber + 1}
                  total={frames.length}
                />
              </div>
              <div className="type-story-body story-viewer__body">
                {currentFrame?.text}
              </div>
            </div>
          </div>

          <NavZones
            hasPrev={hasPrev}
            hasNext={hasNext}
            onPrev={goPrev}
            onNext={goNext}
            enabled={chromeVisible && !drawerIsOpen}
          />
        </>
      ) : (
        <div className="story-viewer__placeholder">
          {error ? (
            <p className="clio-error">{error}</p>
          ) : story ? (
            <>
              <Loader />
              <p className="clio-muted">Beginning the story…</p>
            </>
          ) : (
            <p className="clio-muted">Begin a new story.</p>
          )}
        </div>
      )}

      <Toolbar
        isImmersive={isImmersive}
        onToggleImmersive={toggleImmersive}
        canAddFrame={!!story && !isReadOnly}
        onAddFrame={addFrame}
        onCamera={startCamera}
        onMic={startMic}
        canSocial={!!currentFrame}
        isBookmarked={
          !!currentFrame && bookmarks.some(b => b.frame_id === currentFrame.id)
        }
        onToggleBookmark={toggleBookmark}
        onShare={shareCurrentUrl}
        onOpenMenu={() => setDrawerIsOpen(true)}
      />

      <MainDrawer
        open={drawerIsOpen}
        onClose={() => setDrawerIsOpen(false)}
        stories={stories}
        currentStoryId={story?.id ?? null}
        onSelectStory={openStory}
        onNewStory={() => {
          setDrawerIsOpen(false);
          setCreateOpen(true);
        }}
        renderBookmarks={() => (
          <BookmarksList
            bookmarks={bookmarks}
            stories={stories}
            onOpenStory={openStory}
          />
        )}
      />

      <CreateStoryPanel
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        storytellers={storytellers}
        allowExperimental={allowExperimental}
        defaultStrategy={defaultStrategy}
        onBegin={handleBegin}
        pending={createPending}
        error={createError}
      />

      {story && (
        <StoryStatusMonitor
          userId={userId}
          storyId={story.id}
          onCompleted={refetchCurrent}
          onFailed={onStatusFailed}
        />
      )}

      {captureMode === 'photo' && (
        <PhotoCapture
          sendPhoto={handlePhoto}
          closePhotoCapture={() => setCaptureMode(null)}
        />
      )}
      {captureMode === 'audio' && (
        <AudioCapture
          setIsOpen={open => {
            if (!open) setCaptureMode(null);
          }}
          sendAudio={handleAudio}
        />
      )}

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
