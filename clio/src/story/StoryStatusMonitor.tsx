import { useEffect, useCallback, useState, useRef } from 'react';
import axios from 'axios';
import {
  watchStoryStatus,
  watchStoryUpdates,
  getStoryStatus,
  getStoryUpdates,
  initializeFirebaseApp,
  isFirestoreAvailable,
} from '../services/firebase';
import { StoryUpdate, StoryStatus } from './storyTypes';

interface StoryStatusMonitorProps {
  storyId: string;
  clientId: string;
  onNewFrame?: (frameNumber: number) => void;
  onStatusChange?: (status: StoryStatus) => void;
}

/**
 * A component that silently monitors story status and updates in the background,
 * logging them to console but not displaying anything.
 * When a new frame is added, it calls the onNewFrame callback if provided.
 *
 * For v2 API, this component is crucial as it handles the asynchronous nature
 * of frame generation and provides real-time updates to the UI.
 */
const StoryStatusMonitor: React.FC<StoryStatusMonitorProps> = ({
  storyId,
  clientId,
  onNewFrame,
  onStatusChange,
}) => {
  const [initialized, setInitialized] = useState(false);
  const [firebaseAvailable, setFirebaseAvailable] = useState<boolean | null>(
    null
  );
  const retryCount = useRef<number>(0);
  const onNewFrameRef = useRef(onNewFrame);
  const onStatusChangeRef = useRef(onStatusChange);

  // Update refs when props change
  useEffect(() => {
    onNewFrameRef.current = onNewFrame;
    onStatusChangeRef.current = onStatusChange;
  }, [onNewFrame, onStatusChange]);

  // Initialize Firebase once on component mount
  useEffect(() => {
    const initFirebase = async () => {
      // Skip if already initialized
      if (initialized) return;

      try {
        await initializeFirebaseApp();

        // Check if Firebase is actually properly initialized
        const available = isFirestoreAvailable();
        setFirebaseAvailable(available);
        setInitialized(true);

        if (available) {
          console.log('Firebase fully initialized for StoryStatusMonitor');
        } else {
          console.warn('Firebase initialized but Firestore is not available');
          // Still mark as initialized to prevent further attempts
        }
      } catch (error) {
        console.error('Failed to initialize Firebase:', error);

        // Try again after a short delay, but only retry 3 times
        if (retryCount.current < 3) {
          retryCount.current += 1;
          console.log(`Retry attempt ${retryCount.current}/3...`);
          setTimeout(initFirebase, 1000);
        } else {
          console.warn(
            'Max Firebase initialization retries reached, continuing without Firebase'
          );
          setFirebaseAvailable(false);
          setInitialized(true);

          // Notify about error if we have a status change callback
          if (onStatusChangeRef.current) {
            onStatusChangeRef.current({
              status: 'warning',
              error:
                'Firebase unavailable - some real-time updates may not work',
            });
          }
        }
      }
    };

    // Initialize Firebase
    initFirebase();
  }, [initialized]);

  // Handler for new frames
  const handleNewFrame = useCallback(async (update: StoryUpdate) => {
    if (update.type === 'frame_added' && update.frame_number !== undefined) {
      console.log(`New frame added: ${update.frame_number}`);

      // Notify the parent about the new frame so it can update the UI
      // The parent (ClioApp) will handle fetching the latest story data
      if (onNewFrameRef.current) {
        onNewFrameRef.current(update.frame_number);
      }
    }
  }, []);

  // Handler for status changes
  const handleStatusChange = useCallback((status: StoryStatus) => {
    console.log('Story status update:', status);

    // Notify parent of status changes if callback provided
    if (onStatusChangeRef.current) {
      onStatusChangeRef.current(status);
    }
  }, []);

  // Set up Firebase listeners when storyId changes or Firebase initializes
  useEffect(() => {
    if (!storyId || storyId === 'null' || !initialized) return;

    // If Firebase isn't available, we'll use polling instead
    if (firebaseAvailable === false) {
      console.log(
        'Firebase unavailable. Unable to receive real-time story updates.'
      );
      return;
    }

    console.log(`Setting up status monitors for story ${storyId}`);

    // Firebase is available, use real-time updates
    // Initial fetch of status and updates
    const fetchInitialState = async () => {
      try {
        // Get current status
        const currentStatus = await getStoryStatus(storyId);
        if (currentStatus) {
          console.log('Initial story status:', currentStatus);
          handleStatusChange(currentStatus);
        }

        // Get recent updates
        const updates = await getStoryUpdates(storyId);
        console.log('Initial story updates:', updates);

        // Check for frame_added events
        const frameAddedUpdate = updates.find(
          update => update.type === 'frame_added'
        );
        if (frameAddedUpdate) {
          handleNewFrame(frameAddedUpdate);
        }
      } catch (error) {
        console.error('Error fetching initial story state:', error);
      }
    };

    // Set up Firebase listeners
    let statusUnsubscribe: (() => void) | null = null;
    let updatesUnsubscribe: (() => void) | null = null;
    let backupPollCleanup: (() => void) | null = null;

    const setupListeners = async () => {
      try {
        // Watch story status
        statusUnsubscribe = watchStoryStatus(storyId, handleStatusChange);

        // Watch for updates, with special handling for frame_added events
        updatesUnsubscribe = watchStoryUpdates(storyId, newUpdates => {
          console.log('Story updates:', newUpdates);

          // Check for frame_added events in the latest batch of updates
          if (newUpdates.length > 0) {
            // Find the most recent frame_added update
            const frameAddedUpdate = newUpdates.find(
              update => update.type === 'frame_added'
            );

            // If we found one, notify the parent component
            if (frameAddedUpdate) {
              handleNewFrame(frameAddedUpdate);
            }
          }
        });
      } catch (error) {
        console.error('Error setting up Firebase monitors:', error);

        // Notify about error if we have a status change callback
        if (onStatusChangeRef.current) {
          onStatusChangeRef.current({
            status: 'error',
            error: 'Failed to set up real-time updates',
          });
        }
      }
    };

    // Only fetch initial state and set up listeners if Firebase is available
    if (firebaseAvailable) {
      fetchInitialState();
      setupListeners();
    }

    // Return cleanup function
    return () => {
      console.log(`Cleaning up monitors for story ${storyId}`);

      // Clean up Firebase listeners if they were set up
      if (statusUnsubscribe) {
        try {
          statusUnsubscribe();
        } catch (error) {
          console.error('Error cleaning up status monitor:', error);
        }
      }

      if (updatesUnsubscribe) {
        try {
          updatesUnsubscribe();
        } catch (error) {
          console.error('Error cleaning up updates monitor:', error);
        }
      }

      // Clean up backup polling
      if (backupPollCleanup) {
        try {
          backupPollCleanup();
        } catch (error) {
          console.error('Error cleaning up backup polling:', error);
        }
      }
    };
  }, [storyId, clientId, initialized, firebaseAvailable]);

  // This component doesn't render anything
  return null;
};

export default StoryStatusMonitor;
