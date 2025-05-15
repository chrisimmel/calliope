import React, { useState, useEffect, useRef } from 'react';
import './MediaContainer.css';

interface MediaContainerProps {
  imageUrl?: string;
  videoUrl?: string;
  alt?: string;
  isVisible: boolean;
  isPriority: boolean;
  onLoad?: () => void;
}

const MediaContainer: React.FC<MediaContainerProps> = ({
  imageUrl,
  videoUrl,
  alt = '',
  isVisible,
  isPriority,
  onLoad
}) => {
  const [loaded, setLoaded] = useState<boolean>(false);
  const [loadStarted, setLoadStarted] = useState<boolean>(false);
  const mediaRef = useRef<HTMLImageElement | HTMLVideoElement>(null);

  useEffect(() => {
    // Start loading when this element becomes visible or is priority
    if ((isPriority || isVisible) && !loadStarted) {
      setLoadStarted(true);
    }
  }, [isVisible, isPriority, loadStarted]);

  const handleLoad = () => {
    setLoaded(true);
    if (onLoad) {
      onLoad();
    }
  };

  // Simple loading placeholder
  const placeholder = (
    <div 
      className="media-placeholder-container"
      style={{ opacity: loaded ? 0 : 0.6 }}
    >
      {isPriority ? 'Loading...' : ''}
    </div>
  );

  // Render different content based on what's available
  let mediaContent = null;
  if (loadStarted) {
    if (videoUrl) {
      mediaContent = (
        <div className="media-content-container">
          <video
            ref={mediaRef as React.RefObject<HTMLVideoElement>}
            autoPlay
            loop
            muted
            playsInline
            controls={false}
            poster={imageUrl}
            style={{ opacity: loaded ? 1 : 0 }}
            onLoadedData={handleLoad}
          >
            <source src={videoUrl} type="video/mp4" />
            {imageUrl && <img src={imageUrl} alt={alt} />}
          </video>
        </div>
      );
    } else if (imageUrl) {
      mediaContent = (
        <div className="media-content-container">
          <img
            ref={mediaRef as React.RefObject<HTMLImageElement>}
            src={imageUrl}
            alt={alt}
            style={{ opacity: loaded ? 1 : 0 }}
            onLoad={handleLoad}
          />
        </div>
      );
    }
  }

  return (
    <div className="media-outer-container">
      {!loaded && placeholder}
      {mediaContent}
    </div>
  );
};

export default MediaContainer;