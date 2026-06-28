import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import ClioApp from '../ClioApp';

/**
 * Clio routes. The viewer is the single signed-in surface; the path tells it
 * which story + frame to show. `:frame` is 1-based.
 *
 *   /clio/                              — resume the most-recent story
 *   /clio/story/:slug/:frame            — canonical deep link
 *   /clio/story/:slug                   — slug, default to frame 1
 *   /clio/stories/:storyId/:frame       — transitional id form (no slug yet)
 *   /clio/stories/:storyId              — id form, default to frame 1
 */
const AppRoutes: React.FC = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/clio/" element={<ClioApp />} />
      <Route path="/clio/story/:slug/:frame" element={<ClioApp />} />
      <Route path="/clio/story/:slug" element={<ClioApp />} />
      <Route path="/clio/stories/:storyId/:frame" element={<ClioApp />} />
      <Route path="/clio/stories/:storyId" element={<ClioApp />} />
      <Route path="*" element={<Navigate to="/clio/" replace />} />
    </Routes>
  </BrowserRouter>
);

export default AppRoutes;
