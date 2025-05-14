import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ClioApp from '../ClioApp';

/**
 * Main application routes
 * Handles routing based on URL patterns:
 * - /clio/ - Root app
 * - /clio/story/:storySlug - View a specific story
 * - /clio/story/:storySlug/:frameNum - View a specific frame in a story
 */
const AppRoutes: React.FC = () => {
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
};

export default AppRoutes;