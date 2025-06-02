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


// Firebase configuration objects - separate for dev and prod
const firebaseConfig = {
  apiKey: "AIzaSyAzQGGL947jPY47wrOfDprQ5tloB_qXH_g",
  authDomain: "ardent-course-370411.firebaseapp.com",
  projectId: "ardent-course-370411",
  storageBucket: "ardent-course-370411.firebasestorage.app",
  messagingSenderId: "59295831264",
  appId: "1:59295831264:web:ab96869323b36ab28b2c85",
  measurementId: "G-XDBEEP5KTS"
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
