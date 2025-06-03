import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously } from 'firebase/auth';
import {
  getFirestore,
  collection,
  doc,
  onSnapshot,
  getDoc,
  getDocs,
  addDoc,
  query,
  orderBy,
  limit,
  Firestore,
  Unsubscribe,
} from 'firebase/firestore';


// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY,
  authDomain: process.env.FIREBASE_AUTH_DOMAIN,
  projectId: process.env.FIREBASE_PROJECT_ID,
  storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.FIREBASE_APP_ID,
  measurementId: process.env.FIREBASE_MEASUREMENT_ID
};

// Determine which config to use based on environment
// In a real implementation, you would use environment variables or build configuration
const isProduction = process.env.NODE_ENV === 'production';

// Firebase instance
let firebaseApp: any = null;
let firestore: Firestore | null = null;

// Import the types from storyTypes
import { StoryStatus, StoryUpdate } from '../story/storyTypes';

// Choose the appropriate database based on environment
const databaseId = process.env.NODE_ENV === 'production'
  ? 'calliope-production'
  : 'calliope-development';

/**
 * Initialize Firebase and return the Firestore instance
 */
export async function initializeFirebaseApp(): Promise<void> {
  if (!firebaseApp) {
    // Check if Firebase config is properly set up
    if (!firebaseConfig.apiKey || !firebaseConfig.projectId) {
      console.error('Firebase configuration is missing. Check your environment variables.');
      throw new Error('Firebase configuration is incomplete. Make sure environment variables are set.');
    }

    firebaseApp = initializeApp(firebaseConfig);

    // Sign in anonymously first
    const auth = getAuth(firebaseApp);
    await signInAnonymously(auth);

    // Then initialize Firestore
    firestore = getFirestore(firebaseApp);

    console.log('Firebase initialized with anonymous auth');
  }
}

/**
 * Get the Firestore instance, initializing if necessary
 */
export function getFirestoreInstance(): Firestore {
  if (!firestore) {
    throw new Error("Firebase has not been initialized. Call initializeFirebaseApp() first.");
  }
  return firestore;
}

/**
 * Watch story status changes
 *
 * @param storyId - ID of the story to watch
 * @param callback - Function to call when status changes
 * @returns Unsubscribe function
 */
export function watchStoryStatus(
  storyId: string,
  callback: (status: StoryStatus) => void
): Unsubscribe {
  const db = getFirestoreInstance();
  const storyRef = doc(db, 'stories', storyId);

  return onSnapshot(storyRef, (snapshot) => {
    if (snapshot.exists()) {
      const data = snapshot.data();
      const status = data?.status as StoryStatus;
      callback(status || { status: 'unknown' });
    } else {
      callback({ status: 'unknown' });
    }
  });
}

/**
 * Watch story updates
 *
 * @param storyId - ID of the story to watch
 * @param callback - Function to call when updates change
 * @returns Unsubscribe function
 */
export function watchStoryUpdates(
  storyId: string,
  callback: (updates: StoryUpdate[]) => void
): Unsubscribe {
  const db = getFirestoreInstance();
  const updatesRef = collection(db, 'stories', storyId, 'updates');
  const updatesQuery = query(
    updatesRef,
    orderBy('timestamp', 'desc'),
    limit(20)
  );

  return onSnapshot(updatesQuery, (snapshot) => {
    const updates: StoryUpdate[] = [];

    snapshot.forEach((doc) => {
      updates.push({
        id: doc.id,
        ...doc.data()
      } as StoryUpdate);
    });

    callback(updates);
  });
}

/**
 * Get current story status once
 *
 * @param storyId - ID of the story
 * @returns Promise resolving to status
 */
export async function getStoryStatus(storyId: string): Promise<StoryStatus | null> {
  const db = getFirestoreInstance();
  const storyRef = doc(db, 'stories', storyId);

  const snapshot = await getDoc(storyRef);
  if (snapshot.exists()) {
    const data = snapshot.data();
    return data?.status as StoryStatus || null;
  }

  return null;
}

/**
 * Get story updates once
 *
 * @param storyId - ID of the story
 * @returns Promise resolving to updates
 */
export async function getStoryUpdates(storyId: string): Promise<StoryUpdate[]> {
  const db = getFirestoreInstance();
  const updatesRef = collection(db, 'stories', storyId, 'updates');
  const updatesQuery = query(
    updatesRef,
    orderBy('timestamp', 'desc'),
    limit(20)
  );

  const snapshot = await getDocs(updatesQuery);
  const updates: StoryUpdate[] = [];

  snapshot.forEach((doc) => {
    updates.push({
      id: doc.id,
      ...doc.data()
    } as StoryUpdate);
  });

  return updates;
}

/**
 * Add an update to a story (for client-originated events)
 *
 * @param storyId - ID of the story
 * @param update - Update data
 * @returns Promise resolving to the update ID
 */
export async function addStoryUpdate(
  storyId: string,
  update: Omit<StoryUpdate, 'id'>
): Promise<string> {
  const db = getFirestoreInstance();
  const updatesRef = collection(db, 'stories', storyId, 'updates');

  // Add timestamp if not provided
  if (!update.timestamp) {
    update.timestamp = new Date().toISOString();
  }

  // Add new update
  const docRef = await addDoc(updatesRef, update);
  return docRef.id;
}
