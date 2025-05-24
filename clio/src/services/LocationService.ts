import { Geolocation, Position } from '@capacitor/geolocation';
import { isPlatform } from '../utils/platform';

export interface LocationData {
  latitude: number;
  longitude: number;
  accuracy?: number;
  altitude?: number | null;
  altitudeAccuracy?: number | null;
  heading?: number | null;
  speed?: number | null;
  timestamp?: number;
}

export class LocationService {
  /**
   * Get current location using either web or Capacitor Geolocation
   */
  static async getCurrentPosition(): Promise<LocationData> {
    try {
      let position: Position | GeolocationPosition;
      
      if (isPlatform.capacitor()) {
        // Request permissions first
        const status = await Geolocation.requestPermissions();
        if (status.location !== 'granted') {
          throw new Error('Location permission not granted');
        }
        
        position = await Geolocation.getCurrentPosition({
          enableHighAccuracy: true,
          timeout: 10000
        });
      } else {
        // Web API
        if (!navigator.geolocation) {
          throw new Error('Geolocation is not supported by this browser');
        }
        
        position = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 10000
          });
        });
      }
      
      return {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        altitude: position.coords.altitude,
        altitudeAccuracy: position.coords.altitudeAccuracy,
        heading: position.coords.heading,
        speed: position.coords.speed,
        timestamp: position.timestamp
      };
    } catch (error) {
      console.error('Error getting location', error);
      throw error;
    }
  }
  
  /**
   * Check if location services are available
   */
  static async checkLocationAvailability(): Promise<boolean> {
    if (isPlatform.capacitor()) {
      try {
        const permission = await Geolocation.checkPermissions();
        return permission.location === 'granted' || permission.location === 'prompt';
      } catch (error) {
        console.error('Error checking location permissions', error);
        return false;
      }
    } else {
      // Web check
      return !!navigator.geolocation;
    }
  }
  
  /**
   * Request location permissions
   */
  static async requestLocationPermission(): Promise<boolean> {
    if (isPlatform.capacitor()) {
      try {
        const permission = await Geolocation.requestPermissions();
        return permission.location === 'granted';
      } catch (error) {
        console.error('Error requesting location permissions', error);
        return false;
      }
    } else {
      // Web check - attempt to get location access
      try {
        const position = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject);
        });
        return true;
      } catch (error) {
        console.error('Error requesting location permissions', error);
        return false;
      }
    }
  }
  
  /**
   * Watch location changes
   * @param callback Function to call when location changes
   * @returns Function to call to stop watching location
   */
  static watchPosition(callback: (location: LocationData) => void): () => void {
    if (isPlatform.capacitor()) {
      let watchId: string;
      
      Geolocation.watchPosition(
        { enableHighAccuracy: true }, 
        (position) => {
          if (!position) return;
          
          const locationData: LocationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude,
            altitudeAccuracy: position.coords.altitudeAccuracy,
            heading: position.coords.heading,
            speed: position.coords.speed,
            timestamp: position.timestamp
          };
          
          callback(locationData);
        }
      ).then(id => {
        watchId = id;
      });
      
      // Return function to clear watch
      return () => {
        if (watchId) {
          Geolocation.clearWatch({ id: watchId });
        }
      };
    } else {
      // Web API
      if (!navigator.geolocation) {
        console.error('Geolocation is not supported by this browser');
        return () => {}; // Empty cleanup function
      }
      
      const watchId = navigator.geolocation.watchPosition(
        (position) => {
          const locationData: LocationData = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude,
            altitudeAccuracy: position.coords.altitudeAccuracy,
            heading: position.coords.heading,
            speed: position.coords.speed,
            timestamp: position.timestamp
          };
          
          callback(locationData);
        },
        (error) => {
          console.error('Error watching position', error);
        },
        { enableHighAccuracy: true }
      );
      
      // Return function to clear watch
      return () => {
        navigator.geolocation.clearWatch(watchId);
      };
    }
  }
}