import { useCallback, useRef, useState, useEffect } from 'react';
import axios from 'axios';
import browserID from 'browser-id';
import { useParams, useNavigate } from 'react-router-dom';

import './ClioApp.css';
import AudioCapture from './audio/AudioCapture';
import Carousel, { CarouselItem } from './components/Carousel';
import {
  Bookmark,
  BookmarksResponse,
  Frame,
  FrameSeedMediaType,
  Story,
  Strategy,
} from './story/storyTypes';
import IconChevronLeft from './icons/IconChevronLeft';
import IconChevronRight from './icons/IconChevronRight';
import Loader from './components/Loader';
import PhotoCapture from './photo/PhotoCapture';
import Toolbar from './components/Toolbar';
import VideoLoop from './components/VideoLoop';
import { StoryStatus } from './story/storyTypes';
import StoryStatusMonitor from './story/StoryStatusMonitor';
import { initializeFirebaseApp } from './services/firebase';

const FRAMES_TIMEOUT = 180_000;
const DEFAULT_TIMEOUT = 30_000;

const audioConstraints = {
  suppressLocalAudioPlayback: true,
  noiseSuppression: true,
};
const thisBrowserID = browserID();

const getDefaultStrategy: () => string | null = () => {
  const queryParameters = new URLSearchParams(window.location.search);
  const urlStrategy = queryParameters.get('strategy');
  const savedStrategy = localStorage.getItem('strategy');

  return urlStrategy || (savedStrategy != '' ? savedStrategy : null);
};
const getDefaultStoryAndFrame: () => [string | null, number | null] = () => {
  const queryParameters = new URLSearchParams(window.location.search);
  const urlStory = queryParameters.get('story');
  const parts = urlStory ? urlStory?.split(':') : [];
  const storyId = parts.length ? parts[0] : null;
  const frameNumber =
    parts.length > 1 ? parseInt(parts[1]) : storyId != null ? 0 : null;

  return [storyId, frameNumber];
};
const getAllowExperimental: () => boolean = () => {
  const queryParameters = new URLSearchParams(window.location.search);
  const xParam = queryParameters.get('x');
  return xParam != null && xParam == '1';
};

// Utility function to preserve query parameters during navigation
const preserveQueryParams = (url: string): string => {
  const currentParams = new URLSearchParams(window.location.search);

  // If there are no query parameters, return the original URL
  if (!currentParams.toString()) {
    return url;
  }

  // Check if the URL already has query parameters
  const hasQuery = url.includes('?');
  const separator = hasQuery ? '&' : '?';

  // Append the current query parameters to the URL
  return `${url}${separator}${currentParams.toString()}`;
};

let getFramesInterval: ReturnType<typeof setTimeout> | null = null;
let hideOverlaysInterval: ReturnType<typeof setTimeout> | null = null;

const renderFrame = (frame: Frame, index: number, currentIndex: number) => {
  // Calculate if this frame is visible (current or adjacent)
  const isVisible = Math.abs(index - currentIndex) <= 1;
  // Only the current frame is priority loaded
  const isPriority = index === currentIndex;

  // Only process media URLs if the frame is visible
  // This prevents unnecessary downloads of images/videos for frames far from current view
  const image_url = frame.image && frame.image.url ? `/${frame.image.url}` : '';
  const video_url = frame.video && frame.video.url ? `/${frame.video.url}` : '';
  const hasVideo = Boolean(frame.video && frame.video.url);

  // Create a fixed-height wrapper to prevent text shifting
  const imageContainerStyle = {
    position: 'relative' as const,
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  // When loading placeholder is displayed, ensure there's a consistent background
  const placeholderStyle = {
    display: !isVisible || (!image_url && !video_url) ? 'block' : 'none',
  };

  // Added loading state handling for images with fade-in transition
  const mediaStyles = {
    width: '100%',
    height: '100%',
    objectFit: 'contain' as const,
    opacity: 0, // Start invisible for fade-in effect
    transition: 'opacity 0.3s ease-in-out', // Smooth fade-in transition
  };

  return (
    <CarouselItem key={index}>
      <div className="clio_app">
        <div className="image" style={imageContainerStyle}>
          {/* Empty placeholder div to maintain height when no media is present */}
          <div className="media_placeholder" style={placeholderStyle}></div>

          {/* Only render media if this frame is visible */}
          {isVisible && (
            <>
              {/* Conditionally render media with proper loading strategy */}
              {hasVideo ? (
                // Only actually create VideoLoop component when in view
                <VideoLoop
                  videoSrc={video_url}
                  imageUrl={image_url}
                  fadeDurationMs={2000} // Use shorter duration for videos under 10 seconds (handled in component)
                  isVisible={isPriority} // Only play video when it's the current frame
                />
              ) : (
                // Display image with preloaded dimensions
                image_url && (
                  <img
                    src={image_url}
                    alt={`Frame ${index + 1}`}
                    style={mediaStyles}
                    loading={isPriority ? 'eager' : 'lazy'}
                    onLoad={e => {
                      // When image is loaded, fade it in
                      e.currentTarget.style.opacity = '1';
                    }}
                  />
                )
              )}
            </>
          )}
        </div>
        {/* Text container with immediate rendering - text is always shown for all frames */}
        <div className="textFrame">
          <div className="textContainer">
            <div className="textInner">
              <div className="textScroll">{frame.text}</div>
            </div>
          </div>
        </div>
      </div>
    </CarouselItem>
  );
};

const resetStory = async () => {
  const params: { client_id: string } = {
    client_id: thisBrowserID,
  };

  await axios.put('/v1/story/reset/', null, {
    headers: {
      'X-Api-Key': 'xyzzy',
    },
    params: params,
    timeout: DEFAULT_TIMEOUT,
  });
};

export default function ClioApp() {
  type ClioState = {
    handleFullScreen: () => void;
    getFrames: (image: string | null, audio: string | null) => void;
  };

  // Get URL parameters
  const { storySlug, frameNum } = useParams<{
    storySlug?: string;
    frameNum?: string;
  }>();
  const navigate = useNavigate();

  const stateRef = useRef<ClioState>({
    handleFullScreen: () => null,
    getFrames: () => null,
  });
  const [frames, setFrames] = useState<Frame[]>([]);
  const [selectedFrameNumber, setSelectedFrameNumber] = useState<number>(-1);
  const [loadingFrames, setLoadingFrames] = useState<boolean>(false);
  const [loadingStrategies, setLoadingStrategies] = useState<boolean>(true);
  const [loadingStory, setLoadingStory] = useState<boolean>(true);
  const [loadingStories, setLoadingStories] = useState<boolean>(true);
  const [currentStoryStatus, setCurrentStoryStatus] =
    useState<StoryStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [captureActive, setCaptureActive] = useState<boolean>(false);
  const [captureAudioActive, setCaptureAudioActive] = useState<boolean>(false);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [defaultStrategy, setDefaultStrategy] = useState<string | null>(
    getDefaultStrategy()
  );
  const [allowExperimental, setAllowExperimental] = useState<boolean>(
    getAllowExperimental()
  );
  const [strategy, setStrategy] = useState<string | null>(defaultStrategy);
  const [isFullScreen, setIsFullScreen] = useState<boolean>(false);
  const [stories, setStories] = useState<Story[]>([]);
  const [storyId, setStoryId] = useState<string | null>(null);
  const [storySlugState, setStorySlugState] = useState<string | null>(null);
  const [currentStory, setCurrentStory] = useState<Story | null>(null);
  const [drawerIsOpen, setDrawerIsOpen] = useState<boolean>(false);
  const [showOverlays, setShowOverlays] = useState<boolean>(false);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [loadingBookmarks, setLoadingBookmarks] = useState<boolean>(false);
  const [showBookmarksList, setShowBookmarksList] = useState<boolean>(false);
  const [showShareNotification, setShowShareNotification] =
    useState<boolean>(false);
  const [isReadOnly, setIsReadOnly] = useState<boolean>(false);
  // True when we should skip transition animations (initial load or direct jumps)
  const [skipAnimation, setSkipAnimation] = useState<boolean>(true);

  useEffect(() => {
    initializeFirebaseApp().catch(err => {
      console.error('Failed to initialize Firebase:', err);
    });
  }, []);

  function handleResize() {
    const root: HTMLElement | null = document.querySelector(':root');
    if (root) {
      const vp_height = `${document.documentElement.clientHeight}px`;
      root.style.setProperty('--vp-height', vp_height);
      console.log(`Set --vp-height to ${vp_height}`);
    }
  }

  function navigateToFrame(storySlug: string, frameNumber: number) {
    // Navigate to the proper URL for the current story and frame
    const frameForUrl = frameNumber + 1; // Convert to 1-based for URL
    const baseUrl = `/clio/story/${storySlug}/${frameForUrl}`;

    // Preserve query parameters
    const urlWithParams = preserveQueryParams(baseUrl);

    navigate(urlWithParams, { replace: true });
  }

  useEffect(() => {
    function handleMouseMove(e: any) {
      e.preventDefault();

      if (!hideOverlaysInterval) {
        const rootElement: HTMLElement | null = document.getElementById('root');
        if (rootElement) {
          rootElement.classList.add('show-overlays');
          setShowOverlays(true);

          hideOverlaysInterval = setInterval(() => {
            if (hideOverlaysInterval) {
              clearInterval(hideOverlaysInterval);
              hideOverlaysInterval = null;
            }
            rootElement.classList.remove('show-overlays');
            setShowOverlays(false);
          }, 2000);
        }
      }
    }

    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [isFullScreen, hideOverlaysInterval]);

  useEffect(() => {
    handleResize();

    window.addEventListener('resize', handleResize);
    if (window.screen && window.screen.orientation) {
      try {
        window.addEventListener('orientationchange', handleResize);
        window.screen.orientation.onchange = handleResize;
      } catch (e) {
        console.error(e);
      }
    }
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
      if (window.screen && window.screen.orientation) {
        window.screen.orientation.onchange = null;
      }
    };
  }, []);

  const toggleFullScreen = useCallback(() => {
    const newIsFullScreen = !isFullScreen;
    console.log(`Setting isFullScreen to ${newIsFullScreen}.`);
    setIsFullScreen(newIsFullScreen);
    if (newIsFullScreen) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  }, [isFullScreen]);

  const startCameraCapture = useCallback(() => {
    setCaptureActive(true);
  }, []);
  const startAudioCapture = useCallback(() => {
    setCaptureAudioActive(true);
    console.log('Starting audio capture...');
  }, []);

  const handleFullScreen = useCallback(() => {
    const isCurrentlyFullScreen = !!document.fullscreenElement;
    console.log(
      `handleFullScreen, isCurrentlyFullScreen=${isCurrentlyFullScreen}`
    );
    handleResize();

    const rootElement = document.getElementById('root');
    if (isCurrentlyFullScreen) {
      setIsFullScreen(true);
    } else {
      setIsFullScreen(false);
    }
  }, [isFullScreen]);

  stateRef.current.handleFullScreen = handleFullScreen;
  useEffect(() => {
    const dynHandleFullScreen = () => stateRef.current.handleFullScreen();

    document.addEventListener('fullscreenchange', dynHandleFullScreen);
    return () => {
      document.removeEventListener('fullscreenchange', dynHandleFullScreen);
    };
  }, []);

  const updateStoryWithFrames = useCallback(
    (
      story_id: string,
      newFrames: Frame[],
      story_frame_count: number,
      generationDate: string,
      strategy_name: string
    ) => {
      console.log(`Updating story ${story_id} with ${frames.length} frames.`);
      let storyFound = false;
      const dateUpdated = generationDate.split(' ')[0];

      let newStories = stories;
      let updatedStory: Story | null = null;

      for (let i = 0; i < newStories.length; i++) {
        const story = stories[i];
        if (story.story_id == story_id) {
          storyFound = true;
          story.story_frame_count = story_frame_count;
          story.date_updated = dateUpdated;
          story.is_current = true;
          updatedStory = story;
        } else {
          story.is_current = false;
        }
      }

      if (!storyFound) {
        const maxLength = 64;
        let title = newFrames[0].text || story_id;
        const lines = title.split('\n');
        title = '';
        for (let i = 0; i < lines.length; i++) {
          if (title.length) {
            title += ' ';
          }
          title += lines[i];
          if (title.length > maxLength) {
            break;
          }
        }
        if (title.length > maxLength) {
          title = title.substring(0, maxLength) + '...';
        }

        const newStory: Story = {
          story_id: story_id,
          title: title,
          story_frame_count: story_frame_count,
          is_bookmarked: false,
          is_current: true,
          is_read_only: false,
          strategy_name: strategy_name,
          created_for_sparrow_id: thisBrowserID,
          thumbnail_image: newFrames[0].image || null, // We'll use the image for thumbnails even for video frames
          date_created: dateUpdated,
          date_updated: dateUpdated,
          slug: null, // We don't have the slug yet, it will be populated on the next fetch
        };
        console.log('Adding new story.');
        newStories = [...newStories, newStory];
        updatedStory = newStory;
      }

      // Update the current story state
      if (updatedStory) {
        setCurrentStory(updatedStory);
      }

      setStories(newStories);
    },
    [stories]
  );

  const getFrames = useCallback(
    async (image: string | null, audio: string | null) => {
      console.log(`Enter getFrames. isPlaying=${isPlaying}`);
      setLoadingFrames(true);
      try {
        if (getFramesInterval) {
          clearInterval(getFramesInterval);
          getFramesInterval = null;
        }

        const imagePrefix = image ? image.substring(0, 20) : '(none)';
        console.log(
          `Calling Calliope with strategy ${strategy}, image ${imagePrefix}...`
        );
        setCaptureActive(false);

        // Import the utilities for v2 API
        const { createFrameRequestPayload, createStoryRequestPayload } =
          await import('./utils/apiUtils');

        let response;

        // If we have an existing story, add a frame to it
        if (storyId) {
          // Create the request payload for adding a frame to an existing story
          const payload = createFrameRequestPayload(
            thisBrowserID,
            image,
            audio,
            strategy,
            allowExperimental // generateVideo parameter
          );

          // Call the v2 API to add a frame
          response = await axios.post(
            `/v2/stories/${storyId}/frames/`,
            payload,
            {
              headers: {
                'X-Api-Key': 'xyzzy',
              },
              params: {
                client_id: thisBrowserID,
              },
              timeout: FRAMES_TIMEOUT,
            }
          );

          console.log(
            'Frame request accepted with task ID:',
            response.data.task_id
          );

          // The v2 API is asynchronous, so we need to wait for Firebase updates
          // StoryStatusMonitor will handle the updates and trigger UI refreshes

          // We need to fetch the story state to get the latest frames
          await new Promise(resolve => setTimeout(resolve, 2000)); // Wait a bit for task to start

          // Get the updated story data
          const storyResponse = await axios.get(`/v2/stories/${storyId}/`, {
            headers: {
              'X-Api-Key': 'xyzzy',
            },
            params: {
              client_id: thisBrowserID,
              include_frames: true,
            },
            timeout: DEFAULT_TIMEOUT,
          });

          // Update our UI with the new story data
          const newFrames = storyResponse.data?.frames || [];

          // The rest of the processing remains similar
          const newSelectedFrameNumber = frames ? frames.length : 0;
          setSelectedFrameNumber(newSelectedFrameNumber);

          if (storySlugState) {
            navigateToFrame(storySlugState, newSelectedFrameNumber);
          }

          // Update frames and story data
          if (newFrames && newFrames.length > 0) {
            setFrames(newFrames);

            if (storyResponse.data) {
              updateStoryWithFrames(
                storyId,
                newFrames,
                newFrames.length,
                new Date().toISOString(), // Use current date as generation date
                storyResponse.data.strategy || strategy || ''
              );
            }
          }
        } else {
          // We need to create a new story
          const payload = createStoryRequestPayload(
            thisBrowserID,
            strategy,
            null, // title
            image,
            audio,
            allowExperimental // generateVideo
          );

          // Call the v2 API to create a story
          response = await axios.post('/v2/stories/', payload, {
            headers: {
              'X-Api-Key': 'xyzzy',
            },
            params: {
              client_id: thisBrowserID,
            },
            timeout: FRAMES_TIMEOUT,
          });

          console.log(
            'Story creation accepted with ID:',
            response.data.story_id
          );
          console.log('Task ID:', response.data.task_id);

          // Save the new story ID IMMEDIATELY to start Firebase monitoring
          // This ensures we don't miss the frame_added update from the background task
          const newStoryId = response.data.story_id;
          setStoryId(newStoryId);

          // Give the StoryStatusMonitor a moment to set up Firebase listeners
          // before the background task might complete
          await new Promise(resolve => setTimeout(resolve, 100));

          // For new story creation, we rely on Firebase updates to refresh the UI
          // The handleNewFrameFromFirebase callback will fetch the story data
          // when the first frame is complete, so we don't need to poll here
          console.log('Story created, waiting for Firebase updates...');
        }

        setError(null);
        console.log(`Got frames. isPlaying=${isPlaying}`);
        if (isPlaying) {
          console.log('Scheduling frames request in 20s.');
          getFramesInterval = setInterval(
            () => stateRef.current.getFrames(null, null),
            20000
          );
        }
      } catch (err: any) {
        console.error('Error getting frames:', err);
        setError(err.message || 'Failed to get frames');
      } finally {
        setLoadingFrames(false);
        setCaptureActive(false);
      }
    },
    [
      thisBrowserID,
      frames,
      setCaptureActive,
      isPlaying,
      strategy,
      storyId,
      updateStoryWithFrames,
      setStoryId,
      storySlugState,
      navigateToFrame,
      allowExperimental,
    ]
  );
  stateRef.current.getFrames = getFrames;

  const getStory = useCallback(
    async (story_id: string | null, frame_num: number | null) => {
      // When loading a new story, disable animations
      setSkipAnimation(true);
      setLoadingStory(true);

      if (!story_id) {
        const [defaultStoryId, defaultFrameNum] = getDefaultStoryAndFrame();
        story_id = defaultStoryId; // storyId;
        frame_num = defaultFrameNum;
      }

      // If we still don't have a valid story_id, don't make the API call
      if (!story_id || story_id === 'null') {
        console.log('No valid story ID, skipping getStory API call');
        setLoadingStory(false);
        return;
      }

      try {
        console.log(`Getting story ${story_id}...`);

        // Use v2 API to get the story
        const response = await axios.get(`/v2/stories/${story_id}/`, {
          headers: {
            'X-Api-Key': 'xyzzy',
          },
          params: {
            client_id: thisBrowserID,
            include_frames: true,
          },
          timeout: DEFAULT_TIMEOUT,
        });

        const newFrames = response.data?.frames || [];
        setFrames(newFrames);
        setStrategy(response.data?.strategy || defaultStrategy);
        setStoryId(story_id);
        const maxFrameNum = newFrames ? newFrames.length - 1 : 0;
        if (frame_num != null) {
          frame_num = Math.min(frame_num, maxFrameNum);
        } else {
          frame_num = maxFrameNum;
        }
        setSelectedFrameNumber(frame_num);
        setIsReadOnly(response.data?.is_read_only || false);
        const storySlug = response.data?.slug || null;
        setStorySlugState(storySlug);

        // Create a complete Story object from the API response
        if (story_id) {
          const apiStory: Story = {
            story_id: story_id,
            title: response.data.title || '',
            slug: response.data.slug || null,
            story_frame_count: newFrames.length || 0,
            is_bookmarked: response.data.is_bookmarked || false,
            is_current: true,
            is_read_only: response.data.is_read_only || false,
            strategy_name: response.data.strategy || '',
            created_for_sparrow_id: response.data.created_for_sparrow_id || '',
            thumbnail_image: newFrames[0]?.image || null,
            date_created: response.data.date_created || '',
            date_updated: response.data.date_updated || '',
            // Include the Firebase status if available
            status: response.data.status,
          };

          // Set the current story
          setCurrentStory(apiStory);
        }
        console.log(`Got story ${storySlug} (${newFrames.length} frames).`);
        console.log(
          `Story is ${response.data?.is_read_only ? '' : 'not'} read only.`
        );

        if (story_id && newFrames.length) {
          navigateToFrame(storySlug, frame_num);
        }

        if (!newFrames.length && !getFramesInterval) {
          // If the story is empty, display the menu.
          setDrawerIsOpen(true);
        }

        // Get Firebase status updates
        if (story_id) {
          await initializeFirebaseApp();
        }
      } catch (err: any) {
        console.error('Error getting story:', err);
        setError(err.message || 'Failed to get story');
      } finally {
        setLoadingStory(false);
      }
    },
    [
      stories,
      navigate,
      setSkipAnimation,
      defaultStrategy,
      setStorySlugState,
      navigateToFrame,
    ]
  );

  const getStoryBySlug = useCallback(
    async (slug: string, desiredFrameNum?: number) => {
      // When loading a new story by slug, disable animations
      setSkipAnimation(true);
      setLoadingStory(true);

      try {
        const params = {
          client_id: thisBrowserID,
          debug: true,
        };
        console.log(`Getting story by slug ${slug}...`);
        const response = await axios.get(`/v1/story/slug/${slug}`, {
          headers: {
            'X-Api-Key': 'xyzzy',
          },
          params: params,
          timeout: DEFAULT_TIMEOUT,
        });
        const newFrames = response.data?.frames || [];
        setFrames(newFrames);
        setStrategy(response.data?.strategy || defaultStrategy);
        setStoryId(response.data?.story_id || null);
        setStorySlugState(response.data?.slug || null);

        setIsReadOnly(response.data?.is_read_only || false);
        const storySlug = response.data?.slug || null;
        console.log(`Got story ${storySlug} (${newFrames.length} frames).`);
        console.log(
          `Story is ${response.data?.is_read_only ? '' : 'not'} read only.`
        );

        // Create a complete Story object from the API response
        if (response.data?.story_id) {
          const apiStory: Story = {
            story_id: response.data.story_id,
            title: response.data.title || '',
            slug: response.data.slug || null,
            story_frame_count: response.data.frames?.length || 0,
            is_bookmarked: response.data.is_bookmarked || false,
            is_current: true,
            is_read_only: response.data.is_read_only || false,
            strategy_name: response.data.strategy || '',
            created_for_sparrow_id: response.data.created_for_sparrow_id || '',
            thumbnail_image: newFrames[0]?.image || null,
            date_created: response.data.date_created || null,
            date_updated: response.data.date_updated || null,
          };

          // Set the current story
          setCurrentStory(apiStory);
        }

        // Calculate frame number
        let frameNumber;
        if (desiredFrameNum !== undefined) {
          // Convert from 1-based (URL) to 0-based (internal)
          const zeroBasedFrameNum = Math.max(0, desiredFrameNum - 1);
          const maxFrameNum = newFrames ? newFrames.length - 1 : 0;
          frameNumber = Math.min(zeroBasedFrameNum, maxFrameNum);
        } else {
          frameNumber = 0; // Default to first frame
        }

        setSelectedFrameNumber(frameNumber);

        if (!newFrames.length && !getFramesInterval) {
          // If the story is empty, display the menu.
          setDrawerIsOpen(true);
        }

        // After loading is done, enable animations for subsequent navigation within this story
        setTimeout(() => {
          setSkipAnimation(false);
        }, 100);
      } catch (err: any) {
        setError(err.message);
        console.error('Error fetching story by slug:', err);
      } finally {
        setLoadingStory(false);
      }
    },
    [defaultStrategy, stories, setSkipAnimation, skipAnimation]
  );

  // Track the last loaded story slug to avoid unnecessary reloads
  const lastLoadedStorySlugRef = useRef<string | null>(null);

  useEffect(() => {
    // Check if we have URL parameters for story slug and frame
    if (storySlug) {
      const frameNumInt = frameNum ? parseInt(frameNum, 10) : undefined;

      // Only load from the server if it's a different story
      // or if we're on the initial load
      if (storySlug !== lastLoadedStorySlugRef.current) {
        console.log(
          `Loading new story: ${storySlug} (was: ${lastLoadedStorySlugRef.current})`
        );
        lastLoadedStorySlugRef.current = storySlug;

        // Always disable animations when changing stories
        setSkipAnimation(true);

        // Load the story from the server
        getStoryBySlug(storySlug, frameNumInt);
      } else {
        // Same story, just a different frame - use local navigation.
        // Just update the selected frame number locally - don't reload from server.
        if (frameNumInt !== undefined) {
          // Convert from 1-based (URL) to 0-based (internal)
          const frameIndex = Math.max(0, frameNumInt - 1);
          setSelectedFrameNumber(frameIndex);
        }
      }
    } else {
      // No URL parameters, use the default behavior
      lastLoadedStorySlugRef.current = null;
      getStory(null, null);
    }
  }, [getStory, getStoryBySlug, storySlug, frameNum, setSkipAnimation]);

  useEffect(() => {
    const getStories = async () => {
      setLoadingStories(true);
      try {
        console.log('Getting stories...');
        const response = await axios.get('/v1/stories/', {
          headers: {
            'X-Api-Key': 'xyzzy',
          },
          params: {
            client_id: thisBrowserID,
            debug: true,
          },
          timeout: DEFAULT_TIMEOUT,
        });
        console.log(`Got ${response.data?.stories?.length} stories.`);
        const newStories: [Story] = response.data?.stories || [];

        // Find the current story if any
        const currentStoryFromList = newStories.find(story => story.is_current);
        if (currentStoryFromList) {
          // Ensure date fields are preserved
          const updatedStory = {
            ...currentStoryFromList,
            date_updated: currentStoryFromList.date_updated || '',
            date_created: currentStoryFromList.date_created || '',
          };
          setCurrentStory(updatedStory);
        }

        setStories(newStories);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoadingStories(false);
      }
    };

    getStories();
  }, []);

  const selectFrameNumber = useCallback(
    async (newSelectedFrameNumber: number) => {
      const frameCount = frames.length;
      if (newSelectedFrameNumber < 0) {
        newSelectedFrameNumber = 0;
      } else if (newSelectedFrameNumber >= frameCount) {
        newSelectedFrameNumber = frameCount - 1;
      }

      if (newSelectedFrameNumber != selectedFrameNumber) {
        // When navigating within the same story, we always want animations
        // Animation state is controlled by the navigation methods (aheadOne, backOne, etc.)
        // So we don't modify skipAnimation here

        console.log(
          `New index is ${newSelectedFrameNumber}, total frames: ${frameCount}, skipAnimation=${skipAnimation}`
        );

        setSelectedFrameNumber(newSelectedFrameNumber);

        // Update URL to reflect the current story and frame (1-based for URL)
        if (storyId && storySlugState) {
          navigateToFrame(storySlugState, newSelectedFrameNumber);
        }

        /*
                No more getFrames on navigation!
                if (newSelectedFrameNumber >= frames.length && !getFramesInterval) {
                    console.log(`newSelectedFrameNumber=${newSelectedFrameNumber}, frames.length=${frames.length}. Scheduling frames request.`);
                    getFramesInterval = setInterval(() => stateRef.current.getFrames(null), 500);
                }
                */
      }
    },
    [
      frames,
      selectedFrameNumber,
      setSelectedFrameNumber,
      storyId,
      storySlugState,
      navigate,
      skipAnimation,
    ]
  );

  const toggleIsPlaying = useCallback(() => {
    const newIsPlaying = !isPlaying;
    console.log(`Setting isPlaying to ${newIsPlaying}.`);
    setIsPlaying(newIsPlaying);
    if (newIsPlaying) {
      // Kick things off by generating and moving to a new frame.
      selectFrameNumber(frames.length);
    } else {
      if (getFramesInterval) {
        clearInterval(getFramesInterval);
        getFramesInterval = null;
      }
    }
  }, [isPlaying, frames, selectFrameNumber]);

  useEffect(() => {
    const getStrategies = async () => {
      setLoadingStrategies(true);
      try {
        const params = {
          client_id: thisBrowserID,
        };
        console.log('Getting strategies...');
        const response = await axios.get('/v1/config/strategy/', {
          headers: {
            'X-Api-Key': 'xyzzy',
          },
          params: params,
          timeout: DEFAULT_TIMEOUT,
        });
        const newStrategies = response.data || [];
        console.log(`Got ${response.data?.length} strategies.`);
        setStrategies(newStrategies);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoadingStrategies(false);
      }
    };

    getStrategies();
  }, []);

  const aheadOne = useCallback(() => {
    // Always animate for normal navigation within a story
    setSkipAnimation(false);
    selectFrameNumber(selectedFrameNumber + 1);
  }, [selectedFrameNumber, selectFrameNumber, setSkipAnimation]);
  const backOne = useCallback(() => {
    // Always animate for normal navigation within a story
    setSkipAnimation(false);
    selectFrameNumber(selectedFrameNumber - 1);
  }, [selectedFrameNumber, selectFrameNumber, setSkipAnimation]);
  const toStart = useCallback(() => {
    // Always animate for navigation within a story, even for jumps
    setSkipAnimation(false);
    selectFrameNumber(0);
  }, [setSkipAnimation, selectFrameNumber]);
  const toEnd = useCallback(() => {
    // Always animate for navigation within a story, even for jumps
    setSkipAnimation(false);
    selectFrameNumber(frames.length - 1);
  }, [frames, setSkipAnimation, selectFrameNumber]);
  const sendPhoto = useCallback((image: string | null) => {
    if (!isPlaying) {
      setCaptureActive(false);
    }
    const parts = image ? image.split(',') : null;
    image = parts && parts.length > 1 ? parts[1] : null;

    console.log('Scheduling frames request with image.');
    getFramesInterval = setInterval(
      () => stateRef.current.getFrames(image, null),
      10
    );
  }, []);
  const sendAudio = useCallback((audio: string) => {
    setCaptureAudioActive(false);
    const parts = audio ? audio.split(',') : null;
    audio = parts && parts.length > 1 ? parts[1] : audio;

    console.log(`Scheduling frames request with audio.`);
    getFramesInterval = setInterval(
      () => stateRef.current.getFrames(null, audio),
      10
    );
  }, []);
  const closePhotoCapture = useCallback(() => {
    setCaptureActive(false);
  }, []);
  const startNewStory = useCallback(
    async (strategy: string | null, media_type: FrameSeedMediaType) => {
      console.log(
        `Starting new story with ${strategy} and media: ${media_type}.`
      );
      localStorage.setItem('strategy', strategy || '');
      setStrategy(strategy);
      setStoryId(null);
      setFrames([]);
      setSelectedFrameNumber(-1);

      await resetStory();

      if (media_type == 'photo') {
        startCameraCapture();
      } else if (media_type == 'audio') {
        startAudioCapture();
      } else {
        console.log('Scheduling frames request.');
        getFramesInterval = setInterval(
          () => stateRef.current.getFrames(null, null),
          10
        );
      }

      // After a short delay, enable animations for subsequent navigation within this story
      setTimeout(() => {
        setSkipAnimation(false);
      }, 100);
    },
    [resetStory, startCameraCapture, startAudioCapture, setSkipAnimation]
  );

  const findNearestStrategy = useCallback(
    (strategy_name: string | null) => {
      const matchingPrefixLength = (str1: string, str2: string) => {
        let j = 0;
        for (; j < str1.length && j < str2.length && str1[j] == str2[j]; j++) {}
        return j;
      };

      if (strategies && strategy_name) {
        let closestStrategyName: string | null = null;
        let longestPrefixLength = 0;
        if (strategy_name.startsWith('continuous-v0')) {
          console.log(
            `Story created by deprecated ${strategy_name}. Resetting to tamarisk.`
          );
          closestStrategyName = 'tamarisk';
          longestPrefixLength = 5;
        } else {
          for (let k = 0; k < strategies.length; k++) {
            const candidateStrategy = strategies[k].slug;
            const prefixLength = matchingPrefixLength(
              strategy_name,
              candidateStrategy
            );
            if (prefixLength > longestPrefixLength) {
              closestStrategyName = candidateStrategy;
              longestPrefixLength = prefixLength;
            }
          }
        }
        if (closestStrategyName && longestPrefixLength > 5) {
          console.log(
            `Story created by ${strategy_name}. Nearest current strategy is ${closestStrategyName}.`
          );
          strategy_name = closestStrategyName;
        } else {
          console.log(
            `No match found for strategy ${strategy_name}. Using default strategy: ${defaultStrategy}`
          );
          strategy_name = defaultStrategy || 'tamarisk';
        }
      }
      if (!strategy_name) {
        strategy_name = defaultStrategy || 'tamarisk';
      }

      return strategy_name;
    },
    [strategies, defaultStrategy]
  );

  const updateStory = useCallback(
    (story_id: string | null, frame_number: number = 0) => {
      console.log(`Setting story to ${story_id}, frame ${frame_number}.`);

      // Disable animations when changing stories
      setSkipAnimation(true);
      setStoryId(story_id);

      // Set the strategy to match the selected story.
      let storySlug = null;
      let selectedStory = null;

      for (let i = 0; i < stories.length; i++) {
        const story = stories[i];
        if (story.story_id == story_id) {
          selectedStory = story;
          const strategy_name = findNearestStrategy(story.strategy_name);
          console.log(`Setting strategy to ${strategy_name}.`);
          setStrategy(strategy_name);
          storySlug = story.slug;
          break;
        }
      }

      // If we found the story in the stories array, update currentStory
      if (selectedStory) {
        // Mark this story as current, make sure others are not
        // Ensure date_updated is preserved
        const updatedStory = {
          ...selectedStory,
          is_current: true,
          date_updated: selectedStory.date_updated || '',
          date_created: selectedStory.date_created || '',
        };
        setCurrentStory(updatedStory);
      }

      if (storySlug) {
        setStorySlugState(storySlug);

        navigateToFrame(storySlug, frame_number);
      }

      // Get the selected story and jump to the specified frame.
      getStory(story_id, frame_number);

      // After the story is loaded, getStory will re-enable animations
    },
    [
      stories,
      strategies,
      getStory,
      findNearestStrategy,
      navigate,
      setSkipAnimation,
    ]
  );

  const addNewFrame = useCallback(() => {
    selectFrameNumber(frames.length - 1);
    console.log('Scheduling frames request.');
    getFramesInterval = setInterval(
      () => stateRef.current.getFrames(null, null),
      10
    );
  }, [selectedFrameNumber, selectFrameNumber, frames]);

  const fetchBookmarks = useCallback(
    async (specific_story_id: string | null = null) => {
      setLoadingBookmarks(true);
      try {
        const params: { client_id: string; story_id?: string } = {
          client_id: thisBrowserID,
        };

        if (specific_story_id) {
          params.story_id = specific_story_id;
        }

        console.log('Getting bookmarks...');
        const response = await axios.get<BookmarksResponse>(
          '/v1/bookmarks/frame/',
          {
            headers: {
              'X-Api-Key': 'xyzzy',
            },
            params: params,
            timeout: DEFAULT_TIMEOUT,
          }
        );

        console.log(`Got ${response.data?.bookmarks?.length} bookmarks.`);
        setBookmarks(response.data?.bookmarks || []);
      } catch (err: any) {
        setError(err.message);
        console.error('Error fetching bookmarks:', err);
      } finally {
        setLoadingBookmarks(false);
      }
    },
    []
  );

  const toggleBookmark = useCallback(async () => {
    if (
      !storyId ||
      selectedFrameNumber < 0 ||
      selectedFrameNumber >= frames.length
    ) {
      console.error('Cannot bookmark: invalid story or frame');
      return;
    }

    try {
      // Check if this frame is already bookmarked
      const existingBookmark = bookmarks.find(
        b => b.story_id === storyId && b.frame_number === selectedFrameNumber
      );

      if (existingBookmark) {
        // Delete the bookmark
        await axios.delete(`/v1/bookmarks/frame/${existingBookmark.id}`, {
          headers: {
            'X-Api-Key': 'xyzzy',
          },
          params: {
            client_id: thisBrowserID,
          },
          timeout: DEFAULT_TIMEOUT,
        });
        console.log(`Deleted bookmark for frame ${selectedFrameNumber}`);

        // Update local state
        setBookmarks(bookmarks.filter(b => b.id !== existingBookmark.id));
      } else {
        // Create a new bookmark
        const response = await axios.post(
          '/v1/bookmarks/frame',
          {
            story_id: storyId,
            frame_number: selectedFrameNumber,
            comments: null, // Optional comments could be added in the future
          },
          {
            headers: {
              'X-Api-Key': 'xyzzy',
            },
            params: {
              client_id: thisBrowserID,
            },
            timeout: DEFAULT_TIMEOUT,
          }
        );

        console.log(`Created bookmark for frame ${selectedFrameNumber}`);

        // Update local state
        if (response.data) {
          setBookmarks([...bookmarks, response.data]);
        }
      }
    } catch (err: any) {
      setError(err.message);
      console.error('Error toggling bookmark:', err);
    }
  }, [storyId, selectedFrameNumber, frames, bookmarks]);

  const isCurrentFrameBookmarked = useCallback(() => {
    if (
      !storyId ||
      selectedFrameNumber < 0 ||
      selectedFrameNumber >= frames.length
    ) {
      return false;
    }

    return bookmarks.some(
      b => b.story_id === storyId && b.frame_number === selectedFrameNumber
    );
  }, [storyId, selectedFrameNumber, frames, bookmarks]);

  // Function to share the current URL
  const shareCurrentUrl = useCallback(() => {
    try {
      // Copy the current URL to clipboard
      navigator.clipboard.writeText(window.location.href);

      // Show notification
      setShowShareNotification(true);

      // Hide notification after 2 seconds
      setTimeout(() => {
        setShowShareNotification(false);
      }, 2000);
    } catch (err) {
      console.error('Failed to copy URL to clipboard:', err);
    }
  }, []);

  // Load bookmarks when the component mounts
  useEffect(() => {
    fetchBookmarks();
  }, [fetchBookmarks]);

  // Helper function to check if we're currently processing frames
  const isProcessingFrames = Boolean(
    currentStoryStatus &&
      (currentStoryStatus.status === 'processing' ||
        currentStoryStatus.status === 'adding_frame')
  );

  const loading =
    loadingStories ||
    loadingStory ||
    loadingStrategies ||
    loadingFrames ||
    loadingBookmarks ||
    isProcessingFrames;

  /*
    One panel for each frame, including an empty rightmost panel whose selection
    triggers a request for a new frame. When the new rightmost panel contents
    arrive, a _new_ rightmost panel is made available for the same purpose.

    It is also always possible to scroll back through all prior frames of the
    story.
    */
  // Get the current frame index for the carousel
  const currentCarouselIndex = Math.max(
    0,
    Math.min(selectedFrameNumber, frames.length - 1)
  );

  // Handler for when a new frame is added via Firebase
  const handleNewFrameFromFirebase = useCallback(
    (frameNumber: number) => {
      console.log(
        `Firebase reported new frame ${frameNumber} - fetching the latest story data`
      );

      // Fetch the latest story data, including the new frame
      getStory(storyId, null);

      // For new stories (when we only have 1 frame), navigate to that frame
      if (frames.length === 0 || (frames.length === 1 && frameNumber === 0)) {
        console.log('Navigating to first frame of new story');
        setSelectedFrameNumber(frameNumber);
      }
    },
    [storyId, getStory, frames.length]
  );

  // Handler for story status changes
  const handleStatusChange = useCallback(
    (status: StoryStatus) => {
      console.log(`Firebase reported status change: ${status.status}`);

      // Store the current status from Firebase
      setCurrentStoryStatus(status);

      if (status.status === 'error') {
        // Display error to user
        setError(status.error || 'An error occurred processing your request');
      } else if (
        status.status === 'processing' ||
        status.status === 'adding_frame'
      ) {
        // Clear any previous errors when processing starts
        setError(null);
      } else if (status.status === 'completed') {
        // Refresh story data when processing is complete
        getStory(storyId, null);
      }
    },
    [storyId, getStory]
  );

  return (
    <>
      {/* Silent monitor for Firebase updates - enhanced for v2 API */}
      {storyId && storyId !== 'null' && (
        <StoryStatusMonitor
          clientId={thisBrowserID}
          storyId={storyId}
          onNewFrame={handleNewFrameFromFirebase}
          onStatusChange={handleStatusChange}
        />
      )}

      {selectedFrameNumber > 0 && (
        <div className="navLeft">
          <button
            className="navButton"
            onClick={() => {
              backOne();
            }}
          >
            <IconChevronLeft />
          </button>
        </div>
      )}
      <div className="clio_app_overlay">
        {captureActive && (
          <PhotoCapture
            sendPhoto={sendPhoto}
            closePhotoCapture={closePhotoCapture}
          />
        )}
        {!loading && !captureActive && !frames.length && (
          <div className="empty-story">Start by creating a story...</div>
        )}
      </div>
      <Carousel
        selectedIndex={currentCarouselIndex}
        incrementSelectedIndex={aheadOne}
        decrementSelectedIndex={backOne}
        skipAnimation={skipAnimation}
      >
        {/* Render all frames but only load media for visible ones */}
        {frames.map((frame, index) =>
          renderFrame(frame, index, currentCarouselIndex)
        )}
      </Carousel>
      {selectedFrameNumber < frames.length - 1 && (
        <div className="navRight">
          <button
            className="navButton"
            onClick={() => {
              aheadOne();
            }}
          >
            <IconChevronRight />
          </button>
        </div>
      )}
      {
        <Toolbar
          toggleIsPlaying={toggleIsPlaying}
          isPlaying={isPlaying}
          isLoading={loading}
          isFullScreen={isFullScreen}
          toggleFullScreen={toggleFullScreen}
          startAudioCapture={startAudioCapture}
          startCameraCapture={startCameraCapture}
          addNewFrame={addNewFrame}
          allowExperimental={allowExperimental}
          strategies={strategies}
          strategy={strategy}
          startNewStory={startNewStory}
          stories={stories}
          story_id={storyId}
          currentStory={currentStory}
          isReadOnly={isReadOnly}
          setStory={updateStory}
          jumpToBeginning={toStart}
          jumpToEnd={toEnd}
          selectedFrameNumber={selectedFrameNumber}
          frames={frames}
          drawerIsOpen={drawerIsOpen}
          setDrawerIsOpen={setDrawerIsOpen}
          toggleBookmark={toggleBookmark}
          isCurrentFrameBookmarked={isCurrentFrameBookmarked()}
          bookmarks={bookmarks}
          showBookmarksList={showBookmarksList}
          setShowBookmarksList={setShowBookmarksList}
          shareCurrentUrl={shareCurrentUrl}
        />
      }
      {captureAudioActive && (
        <AudioCapture setIsOpen={setCaptureAudioActive} sendAudio={sendAudio} />
      )}
      {loading && !drawerIsOpen && !showOverlays && (
        <div className="spinnerFrame">
          <Loader />
        </div>
      )}
      {showShareNotification && (
        <div className="share-notification">URL copied to clipboard!</div>
      )}
    </>
  );
}
