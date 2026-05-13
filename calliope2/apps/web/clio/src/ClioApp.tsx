/**
 * v3 Clio — minimal shell.
 *
 * Three states tied to the URL:
 *   1. signed out (any path) → Google sign-in button
 *   2. /clio/ → story list + create-story panel
 *   3. /clio/stories/:storyId → story detail with live task status
 *
 * This is the foundation; richer UI (frame seed media, audio capture, swipe
 * navigation, sharing, the bookmarks browser) gets layered back on top in
 * follow-up commits. The plan's "schema-agnostic" components — Carousel,
 * MediaContainer, VideoLoop, LazyMedia — remain available and will be wired
 * in as the detail view fills out.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import {
  currentUser as fbCurrentUser,
  initializeFirebaseApp,
  onAuthChange,
  signInWithGoogle,
  signOut,
  watchTasksForStory,
} from './services/firebase';
import {
  createStory,
  getStory,
  listStories,
  listStorytellers,
} from './services/v3Api';
import {
  Story,
  StoryDetail,
  Storyteller,
  TaskStatus,
} from './story/storyTypes';

import './ClioApp.css';

type AuthState =
  | { kind: 'loading' }
  | { kind: 'signed-out' }
  | { kind: 'signed-in'; userId: string; displayName: string | null };

function useAuth(): AuthState {
  const [state, setState] = useState<AuthState>({ kind: 'loading' });
  useEffect(() => {
    initializeFirebaseApp();
    const unsub = onAuthChange(user => {
      if (user) {
        setState({
          kind: 'signed-in',
          userId: user.uid,
          displayName: user.displayName,
        });
      } else {
        setState({ kind: 'signed-out' });
      }
    });
    return () => unsub();
  }, []);
  return state;
}

function SignInScreen({ onError }: { onError: (msg: string) => void }) {
  const [pending, setPending] = useState(false);
  const handle = async () => {
    setPending(true);
    try {
      await signInWithGoogle();
    } catch (e) {
      onError(e instanceof Error ? e.message : 'sign-in failed');
    } finally {
      setPending(false);
    }
  };
  return (
    <div className="clio-center">
      <h1>Calliope</h1>
      <p>Sign in with your Google account to continue.</p>
      <button onClick={handle} disabled={pending}>
        {pending ? 'Signing in…' : 'Sign in with Google'}
      </button>
    </div>
  );
}

function CreateStoryPanel({
  storytellers,
  onCreated,
}: {
  storytellers: Storyteller[];
  onCreated: (storyId: number) => void;
}) {
  const [storyteller, setStoryteller] = useState(storytellers[0]?.name ?? '');
  const [title, setTitle] = useState('');
  const [pending, setPending] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!storyteller && storytellers.length > 0) {
      setStoryteller(storytellers[0].name);
    }
  }, [storytellers, storyteller]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!storyteller) return;
    setPending(true);
    setErr(null);
    try {
      const res = await createStory({
        storyteller,
        title: title || null,
        inputs: {},
      });
      onCreated(res.story_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'failed to create story');
    } finally {
      setPending(false);
    }
  };

  return (
    <form onSubmit={submit} className="clio-create-panel">
      <h2>New story</h2>
      <label>
        Storyteller
        <select
          value={storyteller}
          onChange={e => setStoryteller(e.target.value)}
        >
          {storytellers.map(s => (
            <option key={s.name} value={s.name}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Title
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="(optional)"
        />
      </label>
      <button type="submit" disabled={pending || !storyteller}>
        {pending ? 'Creating…' : 'Create'}
      </button>
      {err && <div className="clio-error">{err}</div>}
    </form>
  );
}

function StoryList({
  stories,
  onSelect,
}: {
  stories: Story[];
  onSelect: (id: number) => void;
}) {
  if (stories.length === 0) {
    return <p className="clio-muted">No stories yet.</p>;
  }
  return (
    <ul className="clio-story-list">
      {stories.map(s => (
        <li key={s.id}>
          <button onClick={() => onSelect(s.id)}>
            {s.title || `Story #${s.id}`}
            <span className="clio-muted">
              {' '}
              · {s.storyteller_name ?? 'unknown'}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function HomeView({ userId }: { userId: string }) {
  const navigate = useNavigate();
  const [stories, setStories] = useState<Story[]>([]);
  const [storytellers, setStorytellers] = useState<Storyteller[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [list, tellers] = await Promise.all([
        listStories(),
        listStorytellers(),
      ]);
      setStories(list);
      setStorytellers(tellers);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'failed to load');
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, userId]);

  return (
    <div className="clio-home">
      <CreateStoryPanel
        storytellers={storytellers}
        onCreated={id => navigate(`/clio/stories/${id}`)}
      />
      <h2>Your stories</h2>
      <StoryList
        stories={stories}
        onSelect={id => navigate(`/clio/stories/${id}`)}
      />
      {err && <div className="clio-error">{err}</div>}
    </div>
  );
}

function TaskBadge({ task }: { task: TaskStatus }) {
  const label =
    task.status === 'completed'
      ? 'done'
      : task.status === 'failed'
        ? `failed${task.error ? `: ${task.error}` : ''}`
        : task.status === 'running'
          ? `running (${Math.round(task.progress * 100)}%)`
          : task.status;
  return <span className={`clio-task clio-task-${task.status}`}>{label}</span>;
}

function StoryDetailView({
  storyId,
  userId,
}: {
  storyId: number;
  userId: string;
}) {
  const navigate = useNavigate();
  const [story, setStory] = useState<StoryDetail | null>(null);
  const [tasks, setTasks] = useState<TaskStatus[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStory(await getStory(storyId));
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'failed to load');
    }
  }, [storyId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Live task status from Firestore: refresh story when any task completes.
  useEffect(() => {
    const unsub = watchTasksForStory(userId, storyId, t => {
      setTasks(t);
      if (t.some(x => x.status === 'completed' || x.status === 'failed')) {
        void refresh();
      }
    });
    return () => unsub();
  }, [storyId, userId, refresh]);

  if (err) return <div className="clio-error">{err}</div>;
  if (!story) return <div className="clio-muted">Loading…</div>;

  return (
    <div className="clio-story-detail">
      <button onClick={() => navigate('/clio/')}>← Back</button>
      <h2>{story.title || `Story #${story.id}`}</h2>
      <div className="clio-muted">
        Storyteller: {story.storyteller_name ?? '—'}
      </div>
      <div className="clio-tasks">
        {tasks.map(t => (
          <TaskBadge key={`${t.story_id}-${t.started_at}`} task={t} />
        ))}
      </div>
      <ol className="clio-frames">
        {story.frames.map(f => (
          <li key={f.id} className="clio-frame">
            <div className="clio-frame-number">#{f.number}</div>
            {f.image_url && (
              <img src={f.image_url} alt={`frame ${f.number}`} />
            )}
            {f.text && <p>{f.text}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function ClioApp() {
  const auth = useAuth();
  const { storyId } = useParams<{ storyId?: string }>();
  const [topErr, setTopErr] = useState<string | null>(null);

  const parsedStoryId = useMemo(
    () => (storyId ? Number.parseInt(storyId, 10) : null),
    [storyId]
  );

  if (auth.kind === 'loading') {
    return <div className="clio-muted clio-center">Loading…</div>;
  }
  if (auth.kind === 'signed-out') {
    return <SignInScreen onError={setTopErr} />;
  }

  return (
    <div className="clio-shell">
      <header className="clio-header">
        <h1>Calliope</h1>
        <div className="clio-user">
          {auth.displayName ?? fbCurrentUser()?.email ?? auth.userId}
          <button onClick={() => signOut().catch(() => undefined)}>
            Sign out
          </button>
        </div>
      </header>
      {topErr && <div className="clio-error">{topErr}</div>}
      {parsedStoryId !== null && !Number.isNaN(parsedStoryId) ? (
        <StoryDetailView storyId={parsedStoryId} userId={auth.userId} />
      ) : (
        <HomeView userId={auth.userId} />
      )}
    </div>
  );
}
