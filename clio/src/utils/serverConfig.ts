/**
 * Configuration for Calliope backend server
 * Supports multiple server environments for different deployment scenarios
 */
import { isPlatform } from './platform';
import { isIpadSimulator } from './deviceDetection';

// Known server configurations
export interface ServerConfig {
  id: string;
  name: string;
  url: string;
  description: string;
}

// Server configurations
export const SERVER_CONFIGS: ServerConfig[] = [
  {
    id: 'local-dev',
    name: 'Local Development',
    url: 'http://localhost:8008',
    description: 'Local development server at localhost:8008'
  },
  {
    id: 'local-network',
    name: 'Local Network',
    url: 'http://192.168.1.58:8008',
    description: 'Local network server accessible to devices on the same network'
  },
  {
    id: 'production',
    name: 'Production',
    url: 'https://calliope.chrisimmel.com',
    description: 'Production server'
  },
  {
    id: 'ios-simulator',
    name: 'iOS Simulator',
    url: 'http://localhost:8008',
    description: 'Special configuration for iOS simulator'
  },
  {
    id: 'android-emulator',
    name: 'Android Emulator',
    url: 'http://10.0.2.2:8008',
    description: 'Special configuration for Android emulator'
  }
];

// Default server ID (can be changed by the user)
const DEFAULT_SERVER_ID = 'local-dev';

// Local storage key for persisting server choice
const SERVER_CHOICE_KEY = 'calliope_server_choice';

/**
 * Gets the best default server ID based on the current platform
 */
export function getDefaultServerForPlatform(): string {
  if (isPlatform.capacitor()) {
    if (isPlatform.ios()) {
      // For real iOS devices, prefer local network
      return 'local-network';
    } else if (isPlatform.android()) {
      // For real Android devices, prefer local network
      return 'local-network';
    }
  }
  
  // For web, always use local-dev as default
  return DEFAULT_SERVER_ID;
}

/**
 * Gets the currently selected server configuration
 * Falls back to a different server based on device type if the stored choice fails
 */
export function getSelectedServerConfig(): ServerConfig {
  // Try to get the stored server choice from localStorage
  const storedServerId = localStorage.getItem(SERVER_CHOICE_KEY) || getDefaultServerForPlatform();
  
  // Get Capacitor platform info for intelligent fallbacks
  const isCapacitor = isPlatform.capacitor();
  const isIOS = isPlatform.ios();
  const isAndroid = isPlatform.android();
  const isSimulator = isPlatform.simulator();
  
  // Log detailed environment information for debugging purposes
  console.log('Platform environment for server selection:', {
    isCapacitor,
    isIOS,
    isAndroid,
    isSimulator,
    userAgent: navigator.userAgent,
    storedServerId
  });
  
  // Handle special cases for native apps vs simulator/emulator
  let targetServerId = storedServerId;

  // Force iPad simulator to use the iOS simulator server config
  if (isIpadSimulator()) {
    console.log('Detected iPad simulator, forcing iOS simulator server config');
    targetServerId = 'ios-simulator';
  }
  // Handle other simulators
  else if (isCapacitor || isSimulator) {
    if (isIOS && isSimulator) {
      console.log('Running in iOS simulator, using iOS simulator server config');
      targetServerId = 'ios-simulator';
    } else if (isAndroid && isSimulator) {
      console.log('Running in Android emulator, using Android emulator server config');
      targetServerId = 'android-emulator';
    }
  }
  
  // Find the matching server config
  const serverConfig = SERVER_CONFIGS.find(config => config.id === targetServerId);
  
  // Log the selected server configuration for debugging
  console.log(`Selected server: ${serverConfig?.name} (${serverConfig?.url})`);
  
  // Return the found config or the default
  return serverConfig || SERVER_CONFIGS[0];
}

/**
 * Save the selected server configuration
 */
export function saveServerChoice(serverId: string): void {
  localStorage.setItem(SERVER_CHOICE_KEY, serverId);
}

/**
 * Reset to default server configuration
 */
export function resetServerChoice(): void {
  localStorage.setItem(SERVER_CHOICE_KEY, getDefaultServerForPlatform());
}