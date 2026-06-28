import React from 'react';
import { createRoot } from 'react-dom/client';

// Token layers and fonts load first so every component sees the custom
// properties and self-hosted families. Order matters: tokens → theme →
// typography → app/component styles (imported transitively below).
import './styles/tokens.css';
import './styles/theme.css';
import './styles/typography.css';

// Self-hosted fonts (keeps the PWA shell offline-cacheable, no third-party req).
import '@fontsource/newsreader/400.css';
import '@fontsource/newsreader/500.css';
import '@fontsource/hanken-grotesk/600.css';
import '@fontsource/space-mono/400.css';

import AppRoutes from './routes/AppRoutes';

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<AppRoutes />);
} else {
  console.error("The 'root' element wasn't found.");
}

// Register the app-shell service worker (PWA). Scoped to /clio/.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/clio/sw.js', { scope: '/clio/' })
      .catch(() => undefined);
  });
}
