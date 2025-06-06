import { useEffect, useCallback, useState, useRef } from 'react';
import axios from 'axios';
import {
  watchStoryStatus,
  watchStoryUpdates,
  getStoryStatus,
  getStoryUpdates,
  initializeFirebaseApp,
  isFirestoreAvailable
} from '../services/firebase';
import { StoryUpdate, StoryStatus } from './storyTypes';

interface StoryStatusMonitorProps {
  storyId: string;
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
  onNewFrame,
  onStatusChange
}) => {
  const [initialized, setInitialized] = useState(false);
  const [firebaseAvailable, setFirebaseAvailable] = useState<boolean | null>(null);
  const retryCount = useRef<number>(0);

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
          console.warn('Max Firebase initialization retries reached, continuing without Firebase');
          setFirebaseAvailable(false);
          setInitialized(true);

          // Notify about error if we have a status change callback
          if (onStatusChange) {
            onStatusChange({
              status: 'warning',
              error: 'Firebase unavailable - some real-time updates may not work'
            });
          }
        }
      }
    };

    // Initialize Firebase
    initFirebase();
  }, [initialized, onStatusChange]);

  // Handler for new frames
  const handleNewFrame = useCallback(async (update: StoryUpdate) => {
    if (update.type === 'frame_added' && update.frame_number !== undefined) {
      console.log(`New frame added: ${update.frame_number}`);

      // When a new frame is added via the v2 API, we need to fetch the latest story data
      try {
        const response = await axios.get(
          `/v2/stories/${storyId}/`,
          {
            headers: {
              "X-Api-Key": "xyzzy",
            },
            params: {
              include_frames: true
            },
            timeout: 30000,
          }
        );

        // Notify the parent about the new frame so it can update the UI
        if (onNewFrame) {
          onNewFrame(update.frame_number);
        }
      } catch (error) {
        console.error('Error fetching updated story after new frame:', error);
      }
    }
  }, [storyId, onNewFrame]);

  // Handler for status changes
  const handleStatusChange = useCallback((status: StoryStatus) => {
    console.log('Story status update:', status);

    // Notify parent of status changes if callback provided
    if (onStatusChange) {
      onStatusChange(status);
    }
  }, [onStatusChange]);

  // Set up Firebase listeners when storyId changes or Firebase initializes
  useEffect(() => {
    if (!storyId || !initialized) return;

    console.log(`Setting up status monitors for story ${storyId}`);

    // If Firebase isn't available, we'll use polling instead
    if (firebaseAvailable === false) {
      console.log('Firebase unavailable, using polling for story updates');

      // Set up polling for story status
      const pollInterval = setInterval(async () => {
        try {
          const response = await axios.get(
            `/v2/stories/${storyId}/`,
            {
              headers: {
                "X-Api-Key": "xyzzy",
              },
              timeout: 10000,
            }
          );

          const storyData = response.data;
          if (storyData) {
            // Extract status and notify
            const status: StoryStatus = {
              status: storyData.status || 'unknown',
              frame_count: storyData.story_frame_count,
              title: storyData.title,
              created_at: storyData.date_created,
              updated_at: storyData.date_updated,
            };

            handleStatusChange(status);

            // Check if we need to notify about new frames
            if (storyData.frames && storyData.frames.length > 0) {
              const latestFrame = storyData.frames.length - 1;
              handleNewFrame({
                id: `poll-${Date.now()}`,
                type: 'frame_added',
                timestamp: new Date().toISOString(),
                frame_number: latestFrame
              });
            }
          }
        } catch (error) {
          console.error('Error polling for story updates:', error);
        }
      }, 5000); // Poll every 5 seconds

      return () => {
        clearInterval(pollInterval);
      };
    }

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
        const frameAddedUpdate = updates.find(update => update.type === 'frame_added');
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

    const setupListeners = async () => {
      try {
        // Watch story status
        statusUnsubscribe = watchStoryStatus(storyId, handleStatusChange);

        // Watch for updates, with special handling for frame_added events
        updatesUnsubscribe = watchStoryUpdates(storyId, (newUpdates) => {
          console.log('Story updates:', newUpdates);

          // Check for frame_added events in the latest batch of updates
          if (newUpdates.length > 0) {
            // Find the most recent frame_added update
            const frameAddedUpdate = newUpdates.find(update => update.type === 'frame_added');

            // If we found one, notify the parent component
            if (frameAddedUpdate) {
              handleNewFrame(frameAddedUpdate);
            }
          }
        });
      } catch (error) {
        console.error('Error setting up Firebase monitors:', error);

        // Notify about error if we have a status change callback
        if (onStatusChange) {
          onStatusChange({
            status: 'error',
            error: 'Failed to set up real-time updates'
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
    };
  }, [storyId, initialized, firebaseAvailable, handleNewFrame, handleStatusChange]);

  // This component doesn't render anything
  return null;
};

export default StoryStatusMonitor;
