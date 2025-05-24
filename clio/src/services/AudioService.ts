// Only import the platform detection utility
import { isPlatform } from '../utils/platform';

// Define types to match the expected voice recorder interface
interface AudioRecordingPermissionResult {
  value: boolean;
}

interface RecordingData {
  value: {
    recordDataBase64: string;
  };
}

interface VoiceRecorderInterface {
  requestAudioRecordingPermission(): Promise<AudioRecordingPermissionResult>;
  hasAudioRecordingPermission(): Promise<AudioRecordingPermissionResult>;
  startRecording(): Promise<void>;
  stopRecording(): Promise<RecordingData>;
}

// Create a fallback implementation for both development and runtime
const fallbackVoiceRecorder: VoiceRecorderInterface = {
  async requestAudioRecordingPermission(): Promise<AudioRecordingPermissionResult> {
    console.log("Using fallback voice recorder - requestAudioRecordingPermission");
    return { value: true };
  },
  
  async hasAudioRecordingPermission(): Promise<AudioRecordingPermissionResult> {
    console.log("Using fallback voice recorder - hasAudioRecordingPermission");
    return { value: true };
  },
  
  async startRecording(): Promise<void> {
    console.log("Using fallback voice recorder - startRecording");
  },
  
  async stopRecording(): Promise<RecordingData> {
    console.log("Using fallback voice recorder - stopRecording");
    return { value: { recordDataBase64: "" } };
  }
};

export class AudioService {
  /**
   * Get the appropriate recorder implementation
   * This is a placeholder for future implementation when the plugin is installed
   * For now, it always returns the fallback
   */
  private static getRecorder(): VoiceRecorderInterface {
    return fallbackVoiceRecorder;
  }

  /**
   * Request permissions for audio recording
   */
  static async requestPermissions(): Promise<boolean> {
    if (isPlatform.capacitor()) {
      try {
        const recorder = this.getRecorder();
        const permission = await recorder.requestAudioRecordingPermission();
        return permission.value;
      } catch (error) {
        console.error('Error requesting audio permissions', error);
        return false;
      }
    } else {
      // Web check
      if (navigator.mediaDevices) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          // Stop the stream immediately as we're just checking permission
          stream.getTracks().forEach(track => track.stop());
          return true;
        } catch (error) {
          console.error('Error checking audio permissions', error);
          return false;
        }
      }
      return false;
    }
  }

  /**
   * Check if audio recording is available and permissions are granted
   */
  static async checkAudioAvailability(): Promise<boolean> {
    if (isPlatform.capacitor()) {
      try {
        const recorder = this.getRecorder();
        const permission = await recorder.hasAudioRecordingPermission();
        return permission.value;
      } catch (error) {
        console.error('Error checking audio permissions', error);
        return false;
      }
    } else {
      // Web check
      return !!navigator.mediaDevices;
    }
  }

  /**
   * Start recording audio
   */
  static async startRecording(): Promise<void> {
    if (isPlatform.capacitor()) {
      try {
        const recorder = this.getRecorder();
        // First check if we have permission
        const hasPermission = await recorder.hasAudioRecordingPermission();
        if (!hasPermission.value) {
          const permission = await recorder.requestAudioRecordingPermission();
          if (!permission.value) {
            throw new Error('Audio recording permission denied');
          }
        }
        
        await recorder.startRecording();
      } catch (error) {
        console.error('Error starting recording with Capacitor', error);
        throw error;
      }
    }
    // Web recording is handled by the existing useAudioRecorder hook
  }

  /**
   * Stop recording audio and get the result
   */
  static async stopRecording(): Promise<string | null> {
    if (isPlatform.capacitor()) {
      try {
        const recorder = this.getRecorder();
        const result = await recorder.stopRecording();
        return `data:audio/wav;base64,${result.value.recordDataBase64}`;
      } catch (error) {
        console.error('Error stopping recording with Capacitor', error);
        return null;
      }
    }
    // Web recording is handled by the existing useAudioRecorder hook
    return null;
  }
  
  /**
   * Note: When the actual voice recorder plugin is installed,
   * you can modify the getRecorder() method to dynamically load and return it:
   * 
   * private static async getRecorder(): Promise<VoiceRecorderInterface> {
   *   if (isPlatform.capacitor()) {
   *     try {
   *       // Try to dynamically load the plugin at runtime
   *       const module = await import('@capacitor-community/voice-recorder');
   *       return module.VoiceRecorder;
   *     } catch (error) {
   *       console.warn('Voice recorder plugin not available, using fallback', error);
   *       return fallbackVoiceRecorder;
   *     }
   *   }
   *   return fallbackVoiceRecorder;
   * }
   */
}