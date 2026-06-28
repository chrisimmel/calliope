/**
 * Firebase wiring for v3 Clio.
 *
 * - Google sign-in via popup (no anonymous auth).
 * - Firestore listener targets the narrowed ``tasks/{task_id}`` mailbox; each
 *   document carries ``user_id``, ``story_id``, ``type``, ``status``,
 *   ``progress``, ``error?``, ``started_at``, ``completed_at?``.
 * - Tasks for a story are queried as ``where('user_id', '==', uid) AND
 *   where('story_id', '==', id)``.
 *
 * The Firebase project is selected via env vars at build time. In dev, missing
 * config logs a single warning and returns; auth and listeners are no-ops.
 */

import { FirebaseApp, initializeApp } from 'firebase/app';
import {
  Auth,
  GoogleAuthProvider,
  User,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  signOut as fbSignOut,
} from 'firebase/auth';
import {
  Firestore,
  Unsubscribe,
  collection,
  doc,
  getFirestore,
  onSnapshot,
  query,
  where,
} from 'firebase/firestore';

import { TaskStatus } from '../story/storyTypes';

const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY,
  authDomain: process.env.FIREBASE_AUTH_DOMAIN,
  projectId: process.env.FIREBASE_PROJECT_ID,
  storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.FIREBASE_APP_ID,
  measurementId: process.env.FIREBASE_MEASUREMENT_ID,
};

const databaseId =
  process.env.FIREBASE_DATABASE_ID ||
  (process.env.NODE_ENV === 'production'
    ? 'calliope-production'
    : 'calliope-development');

const TASKS_COLLECTION = 'tasks';

let firebaseApp: FirebaseApp | null = null;
let firestore: Firestore | null = null;
let auth: Auth | null = null;

/** Idempotent. Returns silently with a console warning if config is missing. */
export function initializeFirebaseApp(): void {
  if (firebaseApp) return;
  if (!firebaseConfig.apiKey || !firebaseConfig.projectId) {
    console.warn(
      'Firebase config missing (FIREBASE_API_KEY / FIREBASE_PROJECT_ID). ' +
        'Sign-in and realtime status are disabled.'
    );
    return;
  }
  firebaseApp = initializeApp(firebaseConfig);
  firestore = getFirestore(firebaseApp, databaseId);
  auth = getAuth(firebaseApp);
}

export function isFirebaseReady(): boolean {
  return firebaseApp !== null && firestore !== null && auth !== null;
}

/** Trigger Google sign-in via popup; returns the resulting User. */
export async function signInWithGoogle(): Promise<User> {
  if (!auth) {
    initializeFirebaseApp();
    // User-facing: don't surface "Firebase" (the auth provider is an
    // implementation detail). The console warning above keeps the dev signal.
    if (!auth) throw new Error('Google auth not configured');
  }
  const provider = new GoogleAuthProvider();
  const result = await signInWithPopup(auth, provider);
  return result.user;
}

export async function signOut(): Promise<void> {
  if (!auth) return;
  await fbSignOut(auth);
}

/** Subscribe to auth-state changes. ``user`` is null when signed out. */
export function onAuthChange(
  callback: (user: User | null) => void
): Unsubscribe {
  if (!auth) {
    initializeFirebaseApp();
    if (!auth) {
      callback(null);
      return () => undefined;
    }
  }
  return onAuthStateChanged(auth, callback);
}

/** Return the current user's Firebase ID token (refreshed if expired). */
export async function currentIdToken(): Promise<string | null> {
  if (!auth?.currentUser) return null;
  return auth.currentUser.getIdToken();
}

export function currentUser(): User | null {
  return auth?.currentUser ?? null;
}

/** Watch a single task by its id. */
export function watchTask(
  taskId: string,
  callback: (status: TaskStatus | null) => void
): Unsubscribe {
  if (!firestore) {
    initializeFirebaseApp();
    if (!firestore) {
      callback(null);
      return () => undefined;
    }
  }
  const ref = doc(firestore, TASKS_COLLECTION, taskId);
  return onSnapshot(
    ref,
    snap => callback(snap.exists() ? (snap.data() as TaskStatus) : null),
    err => {
      console.error(`watchTask ${taskId} error:`, err);
      callback(null);
    }
  );
}

/** Watch all tasks for a (user, story) pair. Useful for the story-detail view.
 *
 * ``firebaseUid`` is the Firebase Auth UID string (``user.uid``), which the
 * backend writes to Firestore as ``firebase_uid``. This keeps the query
 * type-correct — Firestore equality is type-sensitive and the DB user id
 * (an integer) would never match. */
export function watchTasksForStory(
  firebaseUid: string,
  storyId: number,
  callback: (tasks: TaskStatus[]) => void
): Unsubscribe {
  if (!firestore) {
    initializeFirebaseApp();
    if (!firestore) {
      callback([]);
      return () => undefined;
    }
  }
  const q = query(
    collection(firestore, TASKS_COLLECTION),
    where('firebase_uid', '==', firebaseUid),
    where('story_id', '==', storyId)
  );
  return onSnapshot(
    q,
    snap => {
      const tasks: TaskStatus[] = [];
      snap.forEach(d => tasks.push(d.data() as TaskStatus));
      callback(tasks);
    },
    err => {
      console.error(`watchTasksForStory ${storyId} error:`, err);
      callback([]);
    }
  );
}
