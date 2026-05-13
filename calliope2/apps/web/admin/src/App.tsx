import axios from 'axios';
import React, { useCallback, useEffect, useState } from 'react';
import { Link, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';

import {
  NotAuthorizedError,
  getStory,
  listStories,
  search as adminSearch,
} from './services/adminApi';
import {
  initialize as initializeFirebase,
  onAuthChange,
  signInWithGoogle,
  signOut,
} from './services/firebase';
import {
  AdminSearchHit,
  AdminStory,
  AdminStoryDetail,
} from './types';

type AuthState =
  | { kind: 'loading' }
  | { kind: 'signed-out' }
  | { kind: 'signed-in'; displayName: string | null; email: string | null };

function useAuth(): AuthState {
  const [state, setState] = useState<AuthState>({ kind: 'loading' });
  useEffect(() => {
    initializeFirebase();
    const unsub = onAuthChange(user => {
      setState(
        user
          ? { kind: 'signed-in', displayName: user.displayName, email: user.email }
          : { kind: 'signed-out' }
      );
    });
    return () => unsub();
  }, []);
  return state;
}

function SignIn() {
  const [pending, setPending] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const handle = async () => {
    setPending(true);
    setErr(null);
    try {
      await signInWithGoogle();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'sign-in failed');
    } finally {
      setPending(false);
    }
  };
  return (
    <div className="center">
      <h1>Calliope Admin</h1>
      <button onClick={handle} disabled={pending}>
        {pending ? 'Signing in…' : 'Sign in with Google'}
      </button>
      {err && <p className="error">{err}</p>}
    </div>
  );
}

function NotAuthorized() {
  return (
    <div className="center">
      <h1>403 — Admin only</h1>
      <p>
        Your account doesn&rsquo;t have admin access. Ask a current admin to
        flip <code>users.is_admin</code> for your row.
      </p>
      <button onClick={() => signOut()}>Sign out</button>
    </div>
  );
}

function StoryListPage() {
  const navigate = useNavigate();
  const [stories, setStories] = useState<AdminStory[]>([]);
  const [q, setQ] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  const load = useCallback(async (query?: string) => {
    setErr(null);
    try {
      const r = await listStories(undefined, query);
      setStories(r.items);
    } catch (e) {
      if (e instanceof NotAuthorizedError) {
        setForbidden(true);
      } else if (axios.isAxiosError(e) && e.response?.status === 403) {
        setForbidden(true);
      } else {
        setErr(e instanceof Error ? e.message : 'failed to load');
      }
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (forbidden) return <NotAuthorized />;

  return (
    <div className="page">
      <header className="bar">
        <h1>Stories</h1>
        <button onClick={() => signOut()}>Sign out</button>
      </header>
      <form
        onSubmit={e => {
          e.preventDefault();
          void load(q || undefined);
        }}
      >
        <input
          placeholder="Filter by title…"
          value={q}
          onChange={e => setQ(e.target.value)}
        />
        <button type="submit">Search</button>
      </form>
      {err && <p className="error">{err}</p>}
      <table>
        <thead>
          <tr>
            <th>id</th>
            <th>title</th>
            <th>storyteller</th>
            <th>owner</th>
            <th>created</th>
          </tr>
        </thead>
        <tbody>
          {stories.map(s => (
            <tr key={s.id} onClick={() => navigate(`/admin/stories/${s.id}`)}>
              <td>{s.id}</td>
              <td>{s.title || <span className="muted">—</span>}</td>
              <td>{s.storyteller_name ?? '—'}</td>
              <td>{s.owner_email ?? `#${s.owner_id}`}</td>
              <td>{new Date(s.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StoryDetailPage() {
  const { storyId } = useParams<{ storyId: string }>();
  const [story, setStory] = useState<AdminStoryDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const id = storyId ? Number.parseInt(storyId, 10) : NaN;
    if (Number.isNaN(id)) return;
    getStory(id)
      .then(setStory)
      .catch(e => setErr(e instanceof Error ? e.message : 'failed'));
  }, [storyId]);

  if (err) return <p className="error">{err}</p>;
  if (!story) return <p className="muted">Loading…</p>;

  return (
    <div className="page">
      <Link to="/admin/">← Stories</Link>
      <h1>{story.title || `Story #${story.id}`}</h1>
      <p className="muted">
        Owner: {story.owner_email ?? `#${story.owner_id}`} · Storyteller:{' '}
        {story.storyteller_name ?? '—'}
      </p>
      <ol className="frames">
        {story.frames.map(f => (
          <li key={f.id}>
            <div className="muted">
              #{f.number} · {f.has_embedding ? 'embedded' : 'no embedding'}
            </div>
            {f.image_url && <img src={f.image_url} alt={`frame ${f.number}`} />}
            {f.text && <p>{f.text}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}

function SearchPage() {
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<AdminSearchHit[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      const r = await adminSearch(q);
      setHits(r.hits);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'search failed');
    }
  };

  return (
    <div className="page">
      <Link to="/admin/">← Stories</Link>
      <h1>Semantic search</h1>
      <form onSubmit={run}>
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="quiet kitchen, late afternoon"
        />
        <button type="submit">Search</button>
      </form>
      {err && <p className="error">{err}</p>}
      <ul className="hits">
        {hits.map(h => (
          <li key={h.frame_id}>
            <Link to={`/admin/stories/${h.story_id}`}>
              {h.story_title || `story #${h.story_id}`} · frame #{h.frame_number}
            </Link>
            <div className="muted">
              {h.owner_email ?? `owner #${h.owner_id}`} · distance{' '}
              {h.distance.toFixed(3)}
            </div>
            {h.frame_text && <p>{h.frame_text}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function App() {
  const auth = useAuth();
  if (auth.kind === 'loading') return <p className="muted center">Loading…</p>;
  if (auth.kind === 'signed-out') return <SignIn />;

  return (
    <div className="shell">
      <nav className="sidebar">
        <strong>Admin</strong>
        <Link to="/admin/">Stories</Link>
        <Link to="/admin/search">Search</Link>
        <div className="muted small">
          {auth.displayName ?? auth.email ?? 'signed in'}
        </div>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/admin/" element={<StoryListPage />} />
          <Route path="/admin/stories/:storyId" element={<StoryDetailPage />} />
          <Route path="/admin/search" element={<SearchPage />} />
          <Route path="*" element={<Navigate to="/admin/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
