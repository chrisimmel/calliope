import { useEffect, useCallback } from 'react';
import {
  watchStoryStatus,
  watchStoryUpdates
} from '../services/firebase';
import { StoryUpdate } from './storyTypes';

interface StoryStatusMonitorProps {
  storyId: string;
  onNewFrame?: (frameNumber: number) => void;
}

/**
 * A component that silently monitors story status and updates in the background,
 * logging them to console but not displaying anything.
 * When a new frame is added, it calls the onNewFrame callback if provided.
 */
const StoryStatusMonitor: React.FC<StoryStatusMonitorProps> = ({
  storyId,
  onNewFrame
}) => {
  // Handler for new frames
  const handleNewFrame = useCallback((update: StoryUpdate) => {
    if (update.type === 'frame_added' && update.frame_number !== undefined && onNewFrame) {
      console.log(`New frame added: ${update.frame_number}`);
      onNewFrame(update.frame_number);
    }
  }, [onNewFrame]);

  useEffect(() => {
    if (!storyId) return;

    console.log(`Setting up Firebase monitors for story ${storyId}`);

    // Watch story status
    const statusUnsubscribe = watchStoryStatus(storyId, (newStatus) => {
      console.log('Story status update:', newStatus);
    });

    // Watch for updates, with special handling for frame_added events
    const updatesUnsubscribe = watchStoryUpdates(storyId, (newUpdates) => {
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

    // Clean up listeners
    return () => {
      console.log(`Cleaning up Firebase monitors for story ${storyId}`);
      statusUnsubscribe();
      updatesUnsubscribe();
    };
  }, [storyId, handleNewFrame]);

  // This component doesn't render anything
  return null;
};

export default StoryStatusMonitor;
