import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import ClioApp from '../ClioApp';

/**
 * v3 Clio routes — numeric story IDs (the v1 slug-based URLs are gone since
 * /v3 doesn't expose slugs). The plan keeps the ``/clio/`` URL prefix so the
 * load-balancer cutover after Phase 9 is a clean DNS/path swap.
 *
 *   /clio/                       — home: sign-in + current user's stories
 *   /clio/stories/:storyId       — story detail view
 */
const AppRoutes: React.FC = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/clio/" element={<ClioApp />} />
      <Route path="/clio/stories/:storyId" element={<ClioApp />} />
      <Route path="*" element={<Navigate to="/clio/" replace />} />
    </Routes>
  </BrowserRouter>
);

export default AppRoutes;
