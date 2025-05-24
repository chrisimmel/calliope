import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.chrisimmel.calliope.app',
  appName: 'Calliope',
  webDir: 'build',
  server: {
    // Allow loading resources from any URL (needed for API requests to backend)
    allowNavigation: ['*', 'http://localhost:8008/*', 'http://10.0.2.2:8008/*'],
    // Clear default hostname to load from local assets
    hostname: 'app',
    // Set cleartext for Android
    androidScheme: 'http',
    cleartext: true,
  },
  android: {
    // Ensure webview shows debugging logs
    loggingBehavior: 'debug',
    // Allow cleartext traffic for development
    allowMixedContent: true
  },
  ios: {
    // Set limitsNavigationsToAppBoundDomains to false to allow API calls
    limitsNavigationsToAppBoundDomains: false
  }
};

export default config;
