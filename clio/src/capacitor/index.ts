import { isPlatform } from "../utils/platform";
import PhotoCaptureAdapter from "../photo/PhotoCaptureAdapter";
import AudioCaptureAdapter from "../audio/AudioCaptureAdapter";

/**
 * This file exports Capacitor-enabled components that work across platforms
 * Both web and native apps can use these components
 */

// Export the platform detection utility
export { isPlatform };

// Export the adapted components
export { PhotoCaptureAdapter, AudioCaptureAdapter };

// Export all services
export { CameraService } from "../services/CameraService";
export { AudioService } from "../services/AudioService";
export { LocationService } from "../services/LocationService";

/**
 * Initialize Capacitor-specific features
 * This should be called once at app startup
 */
export function initCapacitor() {
  // Detect Capacitor presence and platform
  const capacitorObj = (window as any)?.Capacitor;
  const capacitorExists = !!capacitorObj && typeof capacitorObj === 'object';
  const platform = capacitorExists ? capacitorObj.platform : 'none';
  const isNative = capacitorExists && (
    platform === 'ios' || 
    platform === 'android' || 
    capacitorObj.isNative === true
  );
  
  // Log detailed information for debugging
  console.log('Initialization - Window Capacitor object:', {
    exists: capacitorExists,
    type: typeof capacitorObj,
    platform: platform,
    isObject: typeof capacitorObj === 'object',
    isWeb: isPlatform.web(),
    isCapacitor: isPlatform.capacitor(),
    isNative: isNative
  });

  // Force web mode if we detect we're in a browser with Capacitor.js included
  if (capacitorExists && platform === 'web') {
    console.log("Detected web browser with Capacitor.js included - forcing web mode");
    return;
  }

  // Only initialize Capacitor features when running in a native app
  if (isPlatform.capacitor() && isNative) {
    console.log("Initializing Capacitor features for native app");
    // Add any initialization code for Capacitor plugins here
    
    // Set up status bar (if available)
    import("@capacitor/status-bar").then(({ StatusBar, Style }) => {
      // Set status bar to light text on dark background
      StatusBar.setStyle({ style: Style.Dark }).catch(console.error);
    }).catch((err) => {
      console.log("StatusBar plugin not available", err);
    });
    
    // Set up splash screen (if available)
    import("@capacitor/splash-screen").then(({ SplashScreen }) => {
      // Hide the splash screen
      SplashScreen.hide().catch(console.error);
    }).catch((err) => {
      console.log("SplashScreen plugin not available", err);
    });
  } else {
    console.log("Running in web environment - Capacitor features not initialized");
  }
}