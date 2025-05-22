/**
 * Utility functions to detect which platform the app is running on
 * Uses the shared device detection utilities for consistent behavior
 */
import * as deviceDetection from './deviceDetection';

// Initialize platform detection on module load
// This ensures consistent platform and simulator flags across the app
(function initPlatformDetection() {
  if (deviceDetection.hasCapacitor()) {
    // Set platform for iPad simulator
    if (deviceDetection.isIpadSimulator()) {
      deviceDetection.setCapacitorPlatform('ios');
      deviceDetection.setSimulatorFlag(true);
      console.log('iPad simulator detected - setting iOS platform and simulator flag');
    }
    // Set platform for iOS device/simulator based on user agent
    else if (deviceDetection.isIosDeviceByUserAgent() || deviceDetection.isIosSimulatorByUserAgent()) {
      deviceDetection.setCapacitorPlatform('ios');
      
      if (deviceDetection.isIosSimulatorByUserAgent()) {
        deviceDetection.setSimulatorFlag(true);
      }
    }
    // Set platform for Android WebView
    else if (deviceDetection.isAndroidWebView()) {
      deviceDetection.setCapacitorPlatform('android');
    }
  }
  
  // Log device info once during initialization
  deviceDetection.logDeviceInfo('Initial platform detection:');
})();

export const isPlatform = {
  /**
   * Check if running in a Capacitor native app
   */
  capacitor: (): boolean => {
    // First check if Capacitor is available and has a valid platform
    if (deviceDetection.hasCapacitor() && deviceDetection.isValidPlatform()) {
      return true;
    }
    
    // If Capacitor exists but platform is 'web', it's not a native app
    const capacitorObj = (window as any)?.Capacitor;
    if (capacitorObj && capacitorObj.platform === 'web') {
      return false;
    }
    
    // Check for special case - iPad simulator
    if (deviceDetection.isIpadSimulator()) {
      return true;
    }
    
    // Check for native WebViews and simulators
    return deviceDetection.isAndroidWebView() || 
           deviceDetection.isIosWebView() || 
           deviceDetection.isIosSimulatorByUserAgent() && deviceDetection.hasCapacitor() || 
           deviceDetection.isXcodeEnvironment();
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
    // Check for iPad simulator special case
    if (deviceDetection.isIpadSimulator()) {
      // Ensure iOS platform is set
      deviceDetection.setCapacitorPlatform('ios');
      return true;
    }
    
    // Check the platform value set by Capacitor
    return deviceDetection.getCapacitorPlatform() === 'ios';
  },
  
  /**
   * Check if running on Android
   */
  android: (): boolean => {
    return deviceDetection.getCapacitorPlatform() === 'android';
  },
  
  /**
   * Check if running in a simulator/emulator
   */
  simulator: (): boolean => {
    // Check if simulator flag is already set
    if (deviceDetection.getSimulatorFlag()) {
      return true;
    }
    
    // Check for iPad simulator special case
    if (deviceDetection.isIpadSimulator()) {
      deviceDetection.setSimulatorFlag(true);
      return true;
    }
    
    // Check user agent for simulator keywords
    const userAgent = deviceDetection.getUserAgent();
    return userAgent.includes('simulator') || userAgent.includes('emulator');
  }
};