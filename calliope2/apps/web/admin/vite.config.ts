import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// Build output is served by the FastAPI app at /admin, so we need an
// absolute base path; otherwise relative asset URLs will be wrong when the
// SPA is reached from /admin/stories/123.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react()],
    base: '/admin/',
    define: {
      'process.env.FIREBASE_API_KEY': JSON.stringify(env.FIREBASE_API_KEY ?? ''),
      'process.env.FIREBASE_AUTH_DOMAIN': JSON.stringify(env.FIREBASE_AUTH_DOMAIN ?? ''),
      'process.env.FIREBASE_PROJECT_ID': JSON.stringify(env.FIREBASE_PROJECT_ID ?? ''),
      'process.env.FIREBASE_APP_ID': JSON.stringify(env.FIREBASE_APP_ID ?? ''),
      'process.env.FIREBASE_STORAGE_BUCKET': JSON.stringify(env.FIREBASE_STORAGE_BUCKET ?? ''),
      'process.env.FIREBASE_MESSAGING_SENDER_ID': JSON.stringify(env.FIREBASE_MESSAGING_SENDER_ID ?? ''),
      'process.env.API_BASE_URL': JSON.stringify(env.API_BASE_URL ?? ''),
    },
    server: { port: 3001 },
  };
});
