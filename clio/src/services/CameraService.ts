import { Camera, CameraResultType, CameraSource, CameraDirection } from '@capacitor/camera';
import { isPlatform } from '../utils/platform';

export interface CameraOptions {
  facingMode?: 'user' | 'environment';
  quality?: number; // 0-100
}

export class CameraService {
  /**
   * Take a photo using either the web camera API or Capacitor Camera plugin
   * @param options Camera options
   */
  static async takePhoto(options: CameraOptions = {}): Promise<string | null> {
    // Using Capacitor on native platforms
    if (isPlatform.capacitor()) {
      try {
        const photo = await Camera.getPhoto({
          quality: options.quality || 90,
          allowEditing: false,
          resultType: CameraResultType.DataUrl,
          source: CameraSource.Camera,
          direction: options.facingMode === 'user' 
            ? CameraDirection.Front 
            : CameraDirection.Rear
        });
        
        return photo.dataUrl || null;
      } catch (error) {
        console.error('Error taking photo with Capacitor', error);
        return null;
      }
    } 
    // Using web camera API
    else {
      // The web implementation will be handled by the existing Camera component
      // Just return null here as we'll use a different approach in the component
      return null;
    }
  }
  
  /**
   * Check if camera is available on this device
   */
  static async checkCameraAvailability(): Promise<boolean> {
    if (isPlatform.capacitor()) {
      try {
        const permission = await Camera.checkPermissions();
        return permission.camera === 'granted' || permission.camera === 'prompt';
      } catch (error) {
        console.error('Error checking camera permissions', error);
        return false;
      }
    } else {
      // Web check
      return !!navigator.mediaDevices;
    }
  }
  
  /**
   * Request camera permissions
   */
  static async requestPermissions(): Promise<boolean> {
    if (isPlatform.capacitor()) {
      try {
        const permission = await Camera.requestPermissions();
        return permission.camera === 'granted';
      } catch (error) {
        console.error('Error requesting camera permissions', error);
        return false;
      }
    } else {
      // Web check - attempt to get camera access
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        // Stop the stream immediately, we're just checking permission
        stream.getTracks().forEach(track => track.stop());
        return true;
      } catch (error) {
        console.error('Error requesting camera permissions', error);
        return false;
      }
    }
  }
}