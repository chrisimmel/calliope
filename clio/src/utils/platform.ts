/**
 * Utility functions to detect which platform the app is running on
 */
export const isPlatform = {
  /**
   * Check if running in a Capacitor native app
   */
  capacitor: (): boolean => {
    // More robust check that handles potential null/undefined values
    const hasCapacitor = !!(window as any)?.Capacitor;
    const isCapacitorObject = typeof (window as any)?.Capacitor === 'object';
    const platformValue = (window as any)?.Capacitor?.platform;
    const isValidPlatform = platformValue === 'ios' || platformValue === 'android';
    
    // Check user agent for Android WebView as fallback detection method
    const userAgent = window.navigator.userAgent.toLowerCase();
    const isAndroidWebView = userAgent.includes('android') && 
                           (userAgent.includes('wv') || userAgent.includes('webview'));
    const isIosMobileApp = userAgent.includes('iphone') && !userAgent.includes('safari');
    
    // Either standard detection works OR we're in a mobile WebView
    const isCapacitorEnv = (hasCapacitor && isCapacitorObject && isValidPlatform) || 
                           isAndroidWebView || 
                           isIosMobileApp;
    
    // If we're in a WebView but platform isn't set, use the user agent to determine it
    if (isCapacitorEnv && !platformValue) {
      // Set platform property for other components that might need it
      if ((window as any).Capacitor && typeof (window as any).Capacitor === 'object') {
        if (isAndroidWebView) {
          (window as any).Capacitor.platform = 'android';
        } else if (isIosMobileApp) {
          (window as any).Capacitor.platform = 'ios';
        }
      }
    }
    
    return isCapacitorEnv;
  },
  
  /**
   * Check if running in a web browser
   */
  web: (): boolean => {
    return !isPlatform.capacitor();
  },
  
  /**
   * Check if running on iOS
   */
  ios: (): boolean => {
    return (window as any)?.Capacitor?.platform === 'ios';
  },
  
  /**
   * Check if running on Android
   */
  android: (): boolean => {
    return (window as any)?.Capacitor?.platform === 'android';
  }
};