import React, { useState, useEffect, useRef } from 'react';
import './LazyMedia.css';

interface LazyMediaProps {
  imageUrl?: string;
  videoUrl?: string;
  alt?: string;
  isVisible: boolean;
  isPriority: boolean;
  onLoad?: () => void;
}

const LazyMedia: React.FC<LazyMediaProps> = ({
  imageUrl,
  videoUrl,
  alt = '',
  isVisible,
  isPriority,
  onLoad,
}) => {
  const [loaded, setLoaded] = useState<boolean>(false);
  const [loadStarted, setLoadStarted] = useState<boolean>(false);
  const mediaRef = useRef<HTMLImageElement | HTMLVideoElement>(null);

  useEffect(() => {
    // Always load priority media immediately, or when the component becomes visible
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

  if (!imageUrl && !videoUrl) {
    // Return an empty placeholder with fixed dimensions to maintain layout
    return <div className="media-container empty-media-container"></div>;
  }

  // Common container styles to maintain consistent dimensions
  const containerStyle = {
    position: 'relative' as const,
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  if (videoUrl) {
    return (
      <div className="media-container" style={containerStyle}>
        {loadStarted && (
          <video
            ref={mediaRef as React.RefObject<HTMLVideoElement>}
            autoPlay
            loop
            muted
            playsInline
            controls={false}
            poster={imageUrl}
            style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              opacity: loaded ? 1 : 0,
              transition: 'opacity 0.3s ease-in',
            }}
            onLoadedData={handleLoad}
          >
            <source
              src={videoUrl}
              type='video/mp4; codecs="avc1.42E01E, mp4a.40.2"'
            />
            {imageUrl && <img src={imageUrl} alt={alt} />}
          </video>
        )}
        {/* Placeholder remains in DOM for consistent layout until loaded */}
        <div
          className="media-placeholder"
          style={{
            opacity: loaded ? 0 : 0.6,
            position: loaded ? 'absolute' : 'relative',
          }}
        >
          {isPriority ? 'Loading...' : ''}
        </div>
      </div>
    );
  }

  return (
    <div className="media-container" style={containerStyle}>
      {loadStarted && (
        <img
          ref={mediaRef as React.RefObject<HTMLImageElement>}
          src={imageUrl}
          alt={alt}
          style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            opacity: loaded ? 1 : 0,
            transition: 'opacity 0.3s ease-in',
          }}
          onLoad={handleLoad}
        />
      )}
      {/* Placeholder remains in DOM for consistent layout until loaded */}
      <div
        className="media-placeholder"
        style={{
          opacity: loaded ? 0 : 0.6,
          position: loaded ? 'absolute' : 'relative',
        }}
      >
        {isPriority ? 'Loading...' : ''}
      </div>
    </div>
  );
};

export default LazyMedia;
