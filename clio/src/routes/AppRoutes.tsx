import React from 'react';
import { BrowserRouter, HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import ClioApp from '../ClioApp';
import { isPlatform } from '../utils/platform';

/**
 * Main application routes
 * Handles routing based on URL patterns:
 * 
 * Web app routes:
 * - /clio/ - Root app
 * - /clio/story/:storySlug - View a specific story
 * - /clio/story/:storySlug/:frameNum - View a specific frame in a story
 * 
 * Native app routes (using HashRouter):
 * - / - Root app
 * - /story/:storySlug - View a specific story
 * - /story/:storySlug/:frameNum - View a specific frame in a story
 */
const AppRoutes: React.FC = () => {
  // Use HashRouter for mobile apps, BrowserRouter for web
  const isCapacitor = isPlatform.capacitor();
  console.log(`AppRoutes: Using ${isCapacitor ? 'HashRouter for mobile' : 'BrowserRouter for web'}`);
  
  if (isCapacitor) {
    // Mobile app routes (HashRouter doesn't need server support)
    return (
      <HashRouter>
        <Routes>
          {/* Root route */}
          <Route path="/" element={<ClioApp />} />
          
          {/* Story routes */}
          <Route path="/story/:storySlug" element={<ClioApp />} />
          <Route path="/story/:storySlug/:frameNum" element={<ClioApp />} />
          
          {/* Legacy routes for compatibility */}
          <Route path="/clio" element={<Navigate to="/" replace />} />
          <Route path="/clio/story/:storySlug" element={<ClioApp />} />
          <Route path="/clio/story/:storySlug/:frameNum" element={<ClioApp />} />
          
          {/* Redirect any other routes to root */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </HashRouter>
    );
  } else {
    // Web app routes
    return (
      <BrowserRouter>
        <Routes>
          {/* Root route */}
          <Route path="/clio/" element={<ClioApp />} />
          
          {/* Story routes */}
          <Route path="/clio/story/:storySlug" element={<ClioApp />} />
          <Route path="/clio/story/:storySlug/:frameNum" element={<ClioApp />} />
          
          {/* Redirect any other routes to /clio/ */}
          <Route path="*" element={<Navigate to="/clio/" replace />} />
        </Routes>
      </BrowserRouter>
    );
  }
};

export default AppRoutes;