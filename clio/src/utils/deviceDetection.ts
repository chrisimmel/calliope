/**
 * Shared utility functions for device detection
 * 
 * This module provides low-level device detection functions that can be
 * used by the platform, environment, and server configuration modules.
 */

/**
 * Basic Capacitor detection - checks if Capacitor is available and properly initialized
 */
export function hasCapacitor(): boolean {
  const capacitorObj = (window as any)?.Capacitor;
  // Make sure Capacitor object exists and is initialized properly
  // In a web browser that includes Capacitor.js without native functionality,
  // the platform property is often set to 'web' or undefined
  return !!capacitorObj && 
         typeof capacitorObj === 'object' && 
         capacitorObj.platform !== 'web';
}

/**
 * Get the current platform from Capacitor if available
 */
export function getCapacitorPlatform(): string | null {
  if (!hasCapacitor()) {
    return null;
  }
  
  const platform = (window as any)?.Capacitor?.platform;
  return platform || null;
}

/**
 * Check if platform is valid (ios or android)
 */
export function isValidPlatform(): boolean {
  const platform = getCapacitorPlatform();
  return platform === 'ios' || platform === 'android';
}

/**
 * Get the user agent in lowercase
 */
export function getUserAgent(): string {
  return navigator.userAgent.toLowerCase();
}

/**
 * Check if this is potentially an iPad simulator based on user agent patterns
 * iPad simulators often appear as macOS devices in the user agent
 */
export function isIpadSimulator(): boolean {
  // First check if we're in a Capacitor native environment
  if (!hasCapacitor()) {
    return false;
  }
  
  const userAgent = getUserAgent();
  
  // Additional checks for iPad simulator in Capacitor environment
  // We need more criteria to avoid false positives on macOS web browsers
  return userAgent.includes('macintosh') && 
         userAgent.includes('applewebkit') && 
         // Check for Xcode or simulator specific patterns
         (isXcodeEnvironment() || 
          window.location.href.includes('capacitor') || 
          window.location.href.includes('ios-sim'));
}

/**
 * Check if this is an iOS device based on user agent
 */
export function isIosDeviceByUserAgent(): boolean {
  const userAgent = getUserAgent();
  return userAgent.includes('iphone') || 
         userAgent.includes('ipad') || 
         userAgent.includes('ipod');
}

/**
 * Check if this is an iOS simulator based on user agent
 */
export function isIosSimulatorByUserAgent(): boolean {
  const userAgent = getUserAgent();
  return userAgent.includes('iphone simulator') || 
         userAgent.includes('ipad simulator') || 
         userAgent.includes('ipod simulator') ||
         userAgent.includes('simulator') && isIosDeviceByUserAgent();
}

/**
 * Check if this is an Android WebView
 */
export function isAndroidWebView(): boolean {
  const userAgent = getUserAgent();
  return userAgent.includes('android') && 
         (userAgent.includes('wv') || userAgent.includes('webview'));
}

/**
 * Check if this is an iOS WebView (not Safari)
 */
export function isIosWebView(): boolean {
  const userAgent = getUserAgent();
  return isIosDeviceByUserAgent() && !userAgent.includes('safari');
}

/**
 * Check if we're in an Xcode environment
 */
export function isXcodeEnvironment(): boolean {
  if (!hasCapacitor()) {
    return false;
  }
  
  // Look for specific URL patterns used in Xcode/iOS simulator environments
  return window.location.href.includes('capacitor://localhost') ||
         window.location.href.includes('capacitor-site://') ||
         window.location.href.includes('localhost:8080') && 
         (window as any).Capacitor.isNative === true;
}

/**
 * Set platform in Capacitor object for better compatibility
 */
export function setCapacitorPlatform(platform: string): void {
  if (hasCapacitor()) {
    (window as any).Capacitor.platform = platform;
  }
}

/**
 * Set simulator flag in Capacitor object
 */
export function setSimulatorFlag(isSimulator: boolean): void {
  if (hasCapacitor()) {
    (window as any).Capacitor.isSimulator = isSimulator;
  }
}

/**
 * Get simulator flag from Capacitor object
 */
export function getSimulatorFlag(): boolean {
  if (!hasCapacitor()) {
    return false;
  }
  
  return !!(window as any).Capacitor.isSimulator;
}

/**
 * Log detailed device detection information
 */
export function logDeviceInfo(prefix: string = ''): void {
  console.log(`${prefix} Device detection info:`, {
    userAgent: getUserAgent(),
    hasCapacitor: hasCapacitor(),
    capacitorPlatform: getCapacitorPlatform(),
    isValidPlatform: isValidPlatform(),
    isIpadSimulator: isIpadSimulator(),
    isIosDevice: isIosDeviceByUserAgent(),
    isIosSimulator: isIosSimulatorByUserAgent(),
    isAndroidWebView: isAndroidWebView(),
    isIosWebView: isIosWebView(),
    isXcodeEnvironment: isXcodeEnvironment(),
    simulatorFlag: getSimulatorFlag()
  });
}