/**
 * Utility functions to detect and manage the execution environment
 */
import { isIpadSimulator } from './deviceDetection';

/**
 * Environment types for the application
 */
export enum Environment {
  Development = 'development',
  Production = 'production'
}

/**
 * Storage key for overriding the environment
 */
const ENVIRONMENT_OVERRIDE_KEY = 'calliope_environment';

/**
 * Determines the current environment based on various factors
 * 
 * @returns The current environment (development or production)
 */
export function getEnvironment(): Environment {
  // Check for environment override in localStorage (for testing)
  const override = localStorage.getItem(ENVIRONMENT_OVERRIDE_KEY);
  if (override === Environment.Development || override === Environment.Production) {
    return override as Environment;
  }

  // Check for development URL patterns
  if (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname.includes('.local') ||
    window.location.hostname.includes('ngrok.io') || // Used for tunneling
    window.location.port === '8008' ||
    window.location.port === '3000' ||
    window.location.search.includes('dev=true')
  ) {
    return Environment.Development;
  }

  // Check for development build flags from webpack
  if (
    process.env.NODE_ENV === 'development' ||
    process.env.REACT_APP_ENV === 'development'
  ) {
    return Environment.Development;
  }
  
  // For iPad simulator detection - special case when other detection methods fail
  if (isIpadSimulator()) {
    console.log('iPad simulator detected - forcing development environment');
    return Environment.Development;
  }

  // Default to production for safety
  return Environment.Production;
}

/**
 * Checks if the app is running in development mode
 */
export function isDevelopment(): boolean {
  return getEnvironment() === Environment.Development;
}

/**
 * Checks if the app is running in production mode
 */
export function isProduction(): boolean {
  return getEnvironment() === Environment.Production;
}

/**
 * Force a specific environment (for testing)
 * @param env The environment to set
 */
export function setEnvironmentOverride(env: Environment | null): void {
  if (env === null) {
    localStorage.removeItem(ENVIRONMENT_OVERRIDE_KEY);
  } else {
    localStorage.setItem(ENVIRONMENT_OVERRIDE_KEY, env);
  }
}