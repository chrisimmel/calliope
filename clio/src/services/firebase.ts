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
// Use explicit database ID if provided, otherwise fall back to environment-based naming
const databaseId = process.env.FIREBASE_DATABASE_ID || 
  (process.env.NODE_ENV === 'production' ? 'calliope-production' : 'calliope-development');

/**
 * Initialize Firebase and return the Firestore instance
 *
 * This function is idempotent - it can be called multiple times without side effects
 */
export async function initializeFirebaseApp(): Promise<void> {
  if (firebaseApp && firestore) {
    // Already initialized
    return;
  }

  // Log configuration presence at the beginning (not actual values)
  console.log('Firebase configuration status:', {
    apiKeyPresent: Boolean(firebaseConfig.apiKey),
    authDomainPresent: Boolean(firebaseConfig.authDomain),
    projectIdPresent: Boolean(firebaseConfig.projectId),
    storageBucketPresent: Boolean(firebaseConfig.storageBucket),
    messagingSenderIdPresent: Boolean(firebaseConfig.messagingSenderId),
    appIdPresent: Boolean(firebaseConfig.appId),
    measurementIdPresent: Boolean(firebaseConfig.measurementId),
    environment: process.env.NODE_ENV,
  });
  
  // Debug: log partial values to check if they're actually coming through
  console.log('Firebase config values (partial):', {
    apiKeyStart: firebaseConfig.apiKey?.substring(0, 10) + '...',
    projectId: firebaseConfig.projectId,
    authDomain: firebaseConfig.authDomain
  });

  // Check if Firebase config is properly set up
  if (!firebaseConfig.apiKey || !firebaseConfig.projectId) {
    console.warn('Firebase configuration is missing. Check your environment variables.');
    console.warn('Missing config:', {
      apiKey: !firebaseConfig.apiKey,
      projectId: !firebaseConfig.projectId
    });

    // Allow initialization in development with missing config
    // This prevents crashes but will show appropriate warnings
    if (process.env.NODE_ENV === 'development') {
      console.warn('Proceeding with empty Firebase config in development environment');

      // Create a temporary app with minimal config
      const tempConfig = {
        apiKey: firebaseConfig.apiKey || 'dev-placeholder-key',
        projectId: firebaseConfig.projectId || 'dev-placeholder-project',
        appId: firebaseConfig.appId || '1:000000000000:web:0000000000000000000000',
      };

      try {
        firebaseApp = initializeApp(tempConfig);

        // Initialize Firestore first to ensure it's available even if auth fails
        firestore = getFirestore(firebaseApp, databaseId);

        // Skip authentication in development mode with placeholder config
        // This prevents the auth/configuration-not-found error
        console.warn('Skipping authentication with placeholder config');
        console.warn('Firebase initialized with placeholder config for development');
      } catch (error) {
        console.error('Error initializing Firebase with placeholder config:', error);
        // Don't create empty objects - let the system handle the error properly
        throw error;
      }
      return;
    } else {
      throw new Error('Firebase configuration is incomplete. Make sure environment variables are set.');
    }
  }

  try {
    console.log('Initializing Firebase with real config...');
    // Initialize the app
    firebaseApp = initializeApp(firebaseConfig);

    // MOVED: Initialize Firestore FIRST (before auth) to ensure it's available even if auth fails
    // Use the same database ID as the server
    firestore = getFirestore(firebaseApp, databaseId);
    console.log('Firebase Firestore initialized successfully with database:', databaseId);
    console.log('Expected server database ID: calliope-development (from FIREBASE_DATABASE_ID)');
    console.log('Database IDs match:', databaseId === 'calliope-development');
    console.log('Firestore instance type:', typeof firestore);
    console.log('Firestore has collection method:', 'collection' in firestore);
    console.log('Firestore object keys:', Object.keys(firestore));
    console.log('Firestore constructor name:', firestore.constructor.name);
    console.log('Firestore prototype:', Object.getOwnPropertyNames(Object.getPrototypeOf(firestore)));

    // Try to sign in anonymously AFTER Firestore is initialized
    // Check for authDomain before attempting authentication
    if (firebaseConfig.authDomain) {
      try {
        const auth = getAuth(firebaseApp);

        // Check if we actually need authentication
        // Only attempt auth if we have the necessary configs
        if (firebaseConfig.apiKey && firebaseConfig.projectId) {
          try {
            const userCredential = await signInAnonymously(auth);
            console.log('Firebase initialized with anonymous auth');
            console.log('Anonymous user ID:', userCredential.user.uid);
            console.log('Anonymous user is anonymous:', userCredential.user.isAnonymous);
            
            const tokenResult = await userCredential.user.getIdTokenResult();
            console.log('Anonymous user token claims:', tokenResult.claims);
            console.log('Anonymous user sign-in provider:', tokenResult.signInProvider);
            console.log('Anonymous user auth time:', tokenResult.authTime);
          } catch (authError: any) {
            // Enhanced error handling with specific error codes and user-friendly instructions
            switch (authError.code) {
              case 'auth/configuration-not-found':
                console.warn('Firebase auth configuration is missing or invalid.');
                console.warn('SOLUTION: Check that your Firebase project is properly configured with correct API key and project ID.');
                console.warn('Verify the project exists and has Authentication enabled in Firebase Console.');
                break;
              case 'auth/internal-error':
                console.warn('Firebase auth internal error.');
                console.warn('SOLUTION: Check your configuration and Firebase console for error logs.');
                console.warn('Try clearing browser cache and cookies, then reload the application.');
                break;
              case 'auth/operation-not-allowed':
                console.warn('Anonymous authentication is not enabled in your Firebase project.');
                console.warn('SOLUTION:');
                console.warn('1. Go to Firebase Console > Authentication > Sign-in method');
                console.warn('2. Enable the "Anonymous" provider');
                console.warn('3. Save your changes');
                console.warn('4. Reload this application');
                break;
              case 'auth/network-request-failed':
                console.warn('Network error when authenticating with Firebase.');
                console.warn('SOLUTION:');
                console.warn('1. Check your internet connection');
                console.warn('2. Verify that your firewall or proxy settings allow access to Firebase services');
                console.warn('3. Try again when connection is stable');
                break;
              case 'auth/app-deleted':
                console.warn('Firebase app was deleted from Firebase Console.');
                console.warn('SOLUTION: Create a new Firebase project and update your configuration.');
                break;
              case 'auth/app-not-authorized':
                console.warn('Firebase app is not authorized to use Authentication.');
                console.warn('SOLUTION:');
                console.warn('1. Check your Firebase API key and project settings');
                console.warn('2. Verify the domain is whitelisted in Firebase Console > Authentication > Settings > Authorized domains');
                console.warn('3. Ensure your API key restrictions in Google Cloud Console are properly configured');
                break;
              case 'auth/invalid-api-key':
                console.warn('The Firebase API key is invalid.');
                console.warn('SOLUTION:');
                console.warn('1. Check the FIREBASE_API_KEY environment variable for typos');
                console.warn('2. Verify the API key in Firebase Console > Project Settings > Web API Key');
                console.warn('3. Generate a new API key if necessary');
                break;
              case 'auth/invalid-tenant-id':
                console.warn('The Firebase tenant ID is invalid.');
                console.warn('SOLUTION: If you are using multi-tenancy, check your tenant configuration.');
                break;
              default:
                console.warn(`Anonymous authentication failed: ${authError.code}`, authError);
                console.warn('SOLUTION: Check Firebase console logs for more details');
            }
            console.warn('Continuing without auth - some operations may be limited');
          }
        } else {
          console.warn('Skipping Firebase auth due to incomplete config - missing apiKey or projectId');
          console.warn('SOLUTION: Make sure FIREBASE_API_KEY and FIREBASE_PROJECT_ID environment variables are set');
        }
      } catch (authError) {
        // Handle generic auth error, but continue with initialization
        console.warn('Anonymous authentication failed, continuing without auth:', authError);
        console.warn('SOLUTION: Check the error message above for specific troubleshooting steps');
        // We can still use Firestore for reading even without auth
      }
    } else {
      console.warn('Skipping Firebase auth due to missing authDomain.');
      console.warn('SOLUTION to enable authentication:');
      console.warn('1. Make sure FIREBASE_AUTH_DOMAIN environment variable is set');
      console.warn('2. Format should be: your-project-id.firebaseapp.com');
      console.warn('3. You can find this in Firebase Console > Project settings > Your apps > SDK setup and configuration');
    }
  } catch (error) {
    console.error('Error initializing Firebase:', error);

    // If app is already initialized (duplicate app error), try to recover
    if (error instanceof Error && error.message.includes('already exists')) {
      console.log('Attempting to recover from duplicate Firebase app');

      // Get the existing app
      try {
        firebaseApp = initializeApp();

        // Initialize Firestore with recovered app
        firestore = getFirestore(firebaseApp, databaseId);

        console.log('Recovered existing Firebase app');
      } catch (recoverError) {
        console.error('Failed to recover existing Firebase app:', recoverError);
        throw error;
      }
    } else {
      // Rethrow other errors
      throw error;
    }
  }
}

/**
 * Check if Firestore is properly initialized and available
 */
export function isFirestoreAvailable(): boolean {
  // Firebase v9+ uses a modular approach where you import functions like `collection(firestore, path)`
  // instead of calling methods on the firestore instance like `firestore.collection(path)`
  // So we just need to check if we have a valid firestore instance
  const isAvailable = Boolean(firestore && typeof firestore === 'object');
  
  // Debug logging to understand why Firestore is not available
  if (!isAvailable) {
    console.warn('Firestore availability check failed:', {
      firestoreExists: Boolean(firestore),
      firestoreType: typeof firestore,
      hasCollectionMethod: firestore && 'collection' in firestore,
      collectionType: firestore && typeof (firestore as any).collection
    });
  } else {
    console.log('Firestore is available for modular SDK usage');
  }
  
  return isAvailable;
}

/**
 * Get the Firestore instance, initializing if necessary
 */
export async function getFirestoreInstance(): Promise<Firestore> {
  if (!firestore) {
    console.log("Firebase not initialized, initializing now...");
    await initializeFirebaseApp();

    if (!firestore) {
      throw new Error("Firebase initialization failed. Check your configuration.");
    }
  }

  // Check if we have a proper Firestore instance
  if (!isFirestoreAvailable()) {
    console.warn('Firestore is not fully initialized. Some features may not work.');
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
  // Variable to store the actual unsubscribe function when we get it
  let actualUnsubscribe: Unsubscribe | null = null;
  // Flag to track if we've been unsubscribed already
  let isUnsubscribed = false;

  try {
    // Initialize Firebase if needed
    getFirestoreInstance().then(db => {
      // If the caller already unsubscribed, don't set up the listener
      if (isUnsubscribed) {
        return;
      }

      try {
        if (!isFirestoreAvailable()) {
          console.warn('Firestore not fully initialized - cannot watch story status');
          callback({ status: 'error', error: 'Firestore not available' });
          return;
        }

        const storyRef = doc(db, 'stories', storyId);

        // Set up the snapshot listener
        console.log(`Setting up snapshot listener for story ${storyId}`);
        actualUnsubscribe = onSnapshot(storyRef, (snapshot) => {
          console.log(`Story ${storyId} snapshot received:`, {
            exists: snapshot.exists(),
            id: snapshot.id,
            metadata: snapshot.metadata
          });
          
          if (snapshot.exists()) {
            const data = snapshot.data();
            console.log(`Story ${storyId} data:`, data);
            const status = data?.status as StoryStatus;
            callback(status || { status: 'unknown' });
          } else {
            console.log(`Story ${storyId} does not exist`);
            callback({ status: 'unknown' });
          }
        }, error => {
          console.error('Error in watchStoryStatus snapshot:', error);
          console.error('Error code:', error.code);
          console.error('Error message:', error.message);
          callback({ status: 'error', error: error.message });
        });
      } catch (error) {
        console.error('Error setting up watchStoryStatus:', error);
        if (error instanceof Error) {
          callback({ status: 'error', error: error.message });
        } else {
          callback({ status: 'error', error: 'Unknown error watching story status' });
        }
      }
    }).catch(error => {
      console.error('Error getting Firestore instance:', error);
      callback({ status: 'error', error: 'Failed to initialize Firebase' });
    });
  } catch (error) {
    console.error('Unexpected error in watchStoryStatus:', error);
    if (error instanceof Error) {
      callback({ status: 'error', error: error.message });
    } else {
      callback({ status: 'error', error: 'Unknown error watching story status' });
    }
  }

  // Return an unsubscribe function that will use the actual one when available
  return () => {
    isUnsubscribed = true;
    if (actualUnsubscribe) {
      actualUnsubscribe();
    }
  };
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
  // Variable to store the actual unsubscribe function when we get it
  let actualUnsubscribe: Unsubscribe | null = null;
  // Flag to track if we've been unsubscribed already
  let isUnsubscribed = false;

  try {
    // Initialize Firebase if needed
    getFirestoreInstance().then(db => {
      // If the caller already unsubscribed, don't set up the listener
      if (isUnsubscribed) {
        return;
      }

      try {
        if (!isFirestoreAvailable()) {
          console.warn('Firestore not fully initialized - cannot watch story updates');
          callback([]);
          return;
        }

        const updatesRef = collection(db, 'stories', storyId, 'updates');
        const updatesQuery = query(
          updatesRef,
          orderBy('timestamp', 'desc'),
          limit(20)
        );

        // Set up the snapshot listener
        actualUnsubscribe = onSnapshot(updatesQuery, (snapshot) => {
          const updates: StoryUpdate[] = [];

          snapshot.forEach((doc) => {
            updates.push({
              id: doc.id,
              ...doc.data()
            } as StoryUpdate);
          });

          callback(updates);
        }, error => {
          console.error('Error in watchStoryUpdates snapshot:', error);
          callback([]);
        });
      } catch (error) {
        console.error('Error setting up watchStoryUpdates:', error);
        callback([]);
      }
    }).catch(error => {
      console.error('Error getting Firestore instance for updates:', error);
      callback([]);
    });
  } catch (error) {
    console.error('Unexpected error in watchStoryUpdates:', error);
    callback([]);
  }

  // Return an unsubscribe function that will use the actual one when available
  return () => {
    isUnsubscribed = true;
    if (actualUnsubscribe) {
      actualUnsubscribe();
    }
  };
}

/**
 * Get current story status once
 *
 * @param storyId - ID of the story
 * @returns Promise resolving to status
 */
export async function getStoryStatus(storyId: string): Promise<StoryStatus | null> {
  try {
    // Get Firebase instance (initializing if needed)
    const db = await getFirestoreInstance();
    const storyRef = doc(db, 'stories', storyId);

    const snapshot = await getDoc(storyRef);
    if (snapshot.exists()) {
      const data = snapshot.data();
      return data?.status as StoryStatus || null;
    }
    return null;
  } catch (error) {
    console.error('Error getting story status:', error);
    // Return a status object with error information
    return { status: 'error', error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

/**
 * Get story updates once
 *
 * @param storyId - ID of the story
 * @returns Promise resolving to updates
 */
export async function getStoryUpdates(storyId: string): Promise<StoryUpdate[]> {
  try {
    // Get Firebase instance (initializing if needed)
    const db = await getFirestoreInstance();
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
  } catch (error) {
    console.error('Error getting story updates:', error);
    return [];
  }
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
  try {
    // Get Firebase instance (initializing if needed)
    const db = await getFirestoreInstance();
    const updatesRef = collection(db, 'stories', storyId, 'updates');

    // Add timestamp if not provided
    if (!update.timestamp) {
      update.timestamp = new Date().toISOString();
    }

    // Add new update
    const docRef = await addDoc(updatesRef, update);
    return docRef.id;
  } catch (error) {
    console.error('Error adding story update:', error);
    throw error;
  }
}
