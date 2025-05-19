import React, { useEffect, useRef, useState } from 'react';

interface VideoLoopProps {
  videoSrc: string;
  imageUrl: string;
  fadeDurationMs?: number;
  isVisible?: boolean;
}

/**
 * VideoLoop component that uses two video elements in order to fade from the end of the
 * video clip to the beginning when looping.
 * @param {string} videoSrc - The source URL of the video to be played.
 * @param {string} imageUrl - The poster image URL for the video.
 * @param {number} [fadeDurationMs=1000] - Duration of the fade effect in milliseconds.
 * @param {boolean} [isVisible=true] - Whether the component is visible or not.
 */
const VideoLoop: React.FC<VideoLoopProps> = ({
  videoSrc,
  imageUrl,
  fadeDurationMs = 1000,
  isVisible = true
}) => {
  const autoPlay = true;
  const fadeDurationS = fadeDurationMs / 1000;
  const video1Ref = useRef<HTMLVideoElement>(null);
  const video2Ref = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(autoPlay && isVisible);
  const [activeVideoIndex, setActiveVideoIndex] = useState(1);
  const fadeCheckIntervalRef = useRef<number | null>(null);

  // Helper functions to access the videos
  const getActiveVideo = (): HTMLVideoElement | null => {
    return activeVideoIndex === 1 ? video1Ref.current : video2Ref.current;
  };

  const getInactiveVideo = (): HTMLVideoElement | null => {
    return activeVideoIndex === 1 ? video2Ref.current : video1Ref.current;
  };

  // Function to switch between videos
  const switchVideos = () => {
    // Toggle active video index
    setActiveVideoIndex(prevIndex => (prevIndex === 1 ? 2 : 1));
  };

  // State to track video duration once loaded
  const [videoDuration, setVideoDuration] = useState<number | null>(null);

  // Calculate actual fade duration based on video length
  const [actualFadeDurationMs, setActualFadeDurationMs] = useState<number>(fadeDurationMs);
  const actualFadeDurationS = actualFadeDurationMs / 1000;

  // Update fade duration when video duration is known
  useEffect(() => {
    if (videoDuration) {
      // Use shorter fade duration for videos under 10 seconds
      if (videoDuration < 10) {
        setActualFadeDurationMs(1500); // Use 1.5 second fade for short videos
      } else {
        setActualFadeDurationMs(fadeDurationMs); // Use provided fade duration
      }
    }
  }, [videoDuration, fadeDurationMs]);

  // Handle video metadata loaded to get duration
  const handleMetadataLoaded = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget;
    if (video.duration && video.duration !== Infinity) {
      setVideoDuration(video.duration);
    }
  };

  // Start fading out the current video near the end
  const checkForFadeOut = () => {
    const activeVideo = getActiveVideo();
    const inactiveVideo = getInactiveVideo();

    if (!activeVideo || !inactiveVideo) return;

    const timeLeft = activeVideo.duration - activeVideo.currentTime;

    // If video is very short, ensure we don't start fading too early
    const fadeThreshold = Math.min(actualFadeDurationS, activeVideo.duration * 0.15);

    if (timeLeft < fadeThreshold && activeVideo.style.opacity !== '0') {
      console.log(`Starting fade with ${timeLeft}s left, using ${actualFadeDurationMs}ms fade`);

      // Start fade out animation
      activeVideo.style.opacity = '0';
      activeVideo.style.transition = `opacity ${actualFadeDurationS}s ease`;

      // Start fade in animation for inactive video
      inactiveVideo.currentTime = 0;
      inactiveVideo.style.opacity = '1';
      inactiveVideo.style.transition = `opacity ${actualFadeDurationS}s ease`;

      if (isPlaying) {
        inactiveVideo.play().catch(err => console.warn('Play error:', err));
      }

      // After fade completes, switch videos officially
      setTimeout(switchVideos, actualFadeDurationMs);
    }
  };

  // Pause videos when not visible, resume when visible
  useEffect(() => {
    const activeVideo = getActiveVideo();
    const inactiveVideo = getInactiveVideo();
    
    if (isVisible) {
      // Component is visible, attempt to resume playing active video
      if (activeVideo && !isPlaying) {
        activeVideo.play()
          .then(() => setIsPlaying(true))
          .catch(err => console.warn('Play error:', err));
      }
    } else {
      // Component is not visible, pause both videos to save resources
      if (activeVideo) {
        activeVideo.pause();
      }
      if (inactiveVideo) {
        inactiveVideo.pause();
      }
      setIsPlaying(false);
    }
  }, [isVisible]);

  // Set up and tear down the fade checking interval
  useEffect(() => {
    if (isPlaying && isVisible) {
      // Start checking for fade timing
      fadeCheckIntervalRef.current = window.setInterval(checkForFadeOut, 100);
    } else {
      // Stop checking when paused
      if (fadeCheckIntervalRef.current !== null) {
        clearInterval(fadeCheckIntervalRef.current);
        fadeCheckIntervalRef.current = null;
      }
    }

    return () => {
      // Clean up interval on component unmount
      if (fadeCheckIntervalRef.current !== null) {
        clearInterval(fadeCheckIntervalRef.current);
      }
    };
  }, [isPlaying, activeVideoIndex, isVisible, actualFadeDurationMs]);

  // Handle initial play/pause based on autoPlay prop and visibility
  useEffect(() => {
    const activeVideo = getActiveVideo();
    if (activeVideo && isVisible) {
      if (autoPlay) {
        activeVideo.play().catch(err => {
          console.warn('Auto-play was prevented:', err);
          setIsPlaying(false);
        });
      }
    }
  }, []);

  // Clean up videos on unmount
  useEffect(() => {
    return () => {
      // Pause and unload videos when component unmounts
      const v1 = video1Ref.current;
      const v2 = video2Ref.current;
      
      if (v1) {
        v1.pause();
        v1.src = '';
        v1.load();
      }
      
      if (v2) {
        v2.pause();
        v2.src = '';
        v2.load();
      }
    };
  }, []);

  return (
    <div className="video-container">
      <video
        ref={video1Ref}
        poster={imageUrl}
        className="video-element"
        preload="auto"
        muted
        playsInline
        controls={false}
        onLoadedMetadata={handleMetadataLoaded}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: activeVideoIndex === 1 ? 2 : 1,
          opacity: activeVideoIndex === 1 ? 1 : 0
        }}
      >
        <source src={videoSrc} type="video/mp4" />
        {imageUrl && <img src={imageUrl} alt="Video poster" />}
        Your browser does not support the video tag.
      </video>

      <video
        ref={video2Ref}
        poster={imageUrl}
        className="video-element"
        preload="auto"
        muted
        playsInline
        controls={false}
        onLoadedMetadata={handleMetadataLoaded}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: activeVideoIndex === 2 ? 2 : 1,
          opacity: activeVideoIndex === 2 ? 1 : 0
        }}
      >
        <source src={videoSrc} type="video/mp4" />
        {imageUrl && <img src={imageUrl} alt="Video poster" />}
        Your browser does not support the video tag.
      </video>
    </div>
  );
};

export default VideoLoop;
