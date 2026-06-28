/**
 * Auth gate. Three states:
 *   1. loading      → spinner
 *   2. signed-out   → Google sign-in
 *   3. signed-in    → the StoryViewer reading surface
 *
 * The full reading/library/create/capture state machine lives in
 * `story/StoryViewer.tsx`. Auth is Firebase Google sign-in; the v3Api axios
 * interceptor attaches the Bearer ID token.
 */

import React, { useEffect, useState } from 'react';

import Loader from './components/Loader';
import StoryViewer from './story/StoryViewer';
import {
  initializeFirebaseApp,
  onAuthChange,
  signInWithGoogle,
} from './services/firebase';

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

function SignInScreen() {
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
    <div className="clio-center" data-story-theme="atelier">
      <h1>Calliope</h1>
      <p>Sign in with your Google account to continue.</p>
      <button className="cal-button" onClick={handle} disabled={pending}>
        {pending ? 'Signing in…' : 'Sign in with Google'}
      </button>
      {err && <div className="clio-error">{err}</div>}
    </div>
  );
}

export default function ClioApp() {
  const auth = useAuth();

  if (auth.kind === 'loading') {
    return (
      <div className="clio-center" data-story-theme="atelier">
        <Loader />
      </div>
    );
  }
  if (auth.kind === 'signed-out') {
    return <SignInScreen />;
  }
  return <StoryViewer userId={auth.userId} />;
}
