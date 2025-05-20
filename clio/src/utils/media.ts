import { isPlatform } from './platform';
import apiService from '../services/ApiService';

/**
 * Utility functions for handling media URLs in the Clio app
 */

/**
 * Resolves a media URL to be used in the app, handling both web and mobile environments
 * 
 * In web environment: Uses relative URLs (/media/image.jpg)
 * In mobile environment: Uses absolute URLs with the API base URL (http://localhost:8008/media/image.jpg)
 * 
 * @param mediaPath - The relative path from the server (e.g. "media/image.jpg")
 * @returns The resolved URL for the current environment
 */
export function resolveMediaUrl(mediaPath: string | null | undefined): string {
  if (!mediaPath) {
    return '';
  }
  
  // Remove any leading slash from the media path
  const cleanPath = mediaPath.startsWith('/') ? mediaPath.substring(1) : mediaPath;
  
  // Check if the path already starts with http (full URL)
  if (cleanPath.startsWith('http')) {
    return cleanPath;
  }
  
  // For mobile environments, we need full URLs with the server from the current config
  if (isPlatform.capacitor()) {
    // Use the current server configuration
    const serverUrl = apiService.getCurrentServerConfig().url;
    return `${serverUrl}/${cleanPath}`;
  } else {
    // For web, we can use relative URLs since we're serving from the same origin
    return `/${cleanPath}`;
  }
}

/**
 * Debugging function to help diagnose image loading issues
 */
export function logMediaUrl(mediaPath: string | null | undefined, description: string): void {
  const resolvedUrl = resolveMediaUrl(mediaPath);
  
  console.log(`Media URL (${description}): ${resolvedUrl}`, {
    original: mediaPath,
    isCapacitor: isPlatform.capacitor(),
    isIOS: isPlatform.ios(),
    isAndroid: isPlatform.android(),
    serverConfig: apiService.getCurrentServerConfig()
  });
}