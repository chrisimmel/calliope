/**
 * Firebase wiring for the admin SPA. Same Firebase project as Clio, but a
 * separate bundle. Sign-in is gated server-side by ``User.is_admin``.
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

const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY,
  authDomain: process.env.FIREBASE_AUTH_DOMAIN,
  projectId: process.env.FIREBASE_PROJECT_ID,
  appId: process.env.FIREBASE_APP_ID,
  storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
};

let firebaseApp: FirebaseApp | null = null;
let auth: Auth | null = null;

export function initialize(): void {
  if (firebaseApp) return;
  if (!firebaseConfig.apiKey || !firebaseConfig.projectId) {
    console.warn(
      'Firebase config missing; admin sign-in disabled. Set FIREBASE_API_KEY and FIREBASE_PROJECT_ID.'
    );
    return;
  }
  firebaseApp = initializeApp(firebaseConfig);
  auth = getAuth(firebaseApp);
}

export async function signInWithGoogle(): Promise<User> {
  if (!auth) {
    initialize();
    if (!auth) throw new Error('Firebase auth not configured');
  }
  const result = await signInWithPopup(auth, new GoogleAuthProvider());
  return result.user;
}

export async function signOut(): Promise<void> {
  if (auth) await fbSignOut(auth);
}

export function onAuthChange(cb: (user: User | null) => void): () => void {
  if (!auth) {
    initialize();
    if (!auth) {
      cb(null);
      return () => undefined;
    }
  }
  return onAuthStateChanged(auth, cb);
}

export async function currentIdToken(): Promise<string | null> {
  return auth?.currentUser ? auth.currentUser.getIdToken() : null;
}
