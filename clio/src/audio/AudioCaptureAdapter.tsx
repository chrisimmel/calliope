import React, { useState, useEffect } from 'react';
import { isPlatform } from '../utils/platform';
import { AudioService } from '../services/AudioService';

// Import the original component
import AudioCapture from './AudioCapture';
import IconClose from '../icons/IconClose';
import IconSend from '../icons/IconSend';
import "./audio-recorder.css";

type AudioCaptureAdapterProps = {
  setIsOpen: (open: boolean) => void,
  sendAudio: (audio: string) => void,
}

export default function AudioCaptureAdapter({
  setIsOpen,
  sendAudio,
}: AudioCaptureAdapterProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [timerInterval, setTimerInterval] = useState<ReturnType<typeof setInterval>>();
  const [hasPermission, setHasPermission] = useState(false);
  
  // Check permissions on component mount
  useEffect(() => {
    async function checkPermissions() {
      if (isPlatform.capacitor()) {
        const permissionGranted = await AudioService.checkAudioAvailability();
        setHasPermission(permissionGranted);
        
        if (!permissionGranted) {
          const requested = await AudioService.requestPermissions();
          setHasPermission(requested);
        }
      } else {
        setHasPermission(true); // For web, we'll handle this in the original component
      }
    }
    
    checkPermissions();
  }, []);
  
  // If on the web, use the original AudioCapture component
  if (isPlatform.web()) {
    return <AudioCapture setIsOpen={setIsOpen} sendAudio={sendAudio} />;
  }
  
  // Start timer for recording time display
  const startTimer = () => {
    const interval = setInterval(() => {
      setRecordingTime((time) => time + 1);
    }, 1000);
    setTimerInterval(interval);
  };

  // Stop timer
  const stopTimer = () => {
    if (timerInterval) {
      clearInterval(timerInterval);
      setTimerInterval(undefined);
    }
    setRecordingTime(0);
  };
  
  // Start recording with Capacitor
  const startRecording = async () => {
    try {
      if (!hasPermission) {
        const requested = await AudioService.requestPermissions();
        if (!requested) {
          console.error('No permission to record audio');
          return;
        }
        setHasPermission(requested);
      }
      
      await AudioService.startRecording();
      setIsRecording(true);
      startTimer();
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };
  
  // Stop recording and handle the result
  const stopRecording = async (shouldSave: boolean) => {
    try {
      if (isRecording) {
        const audioData = await AudioService.stopRecording();
        stopTimer();
        setIsRecording(false);
        
        if (shouldSave && audioData) {
          sendAudio(audioData);
        }
      }
      setIsOpen(false);
    } catch (error) {
      console.error('Error stopping recording:', error);
      setIsOpen(false);
    }
  };
  
  // Start recording when the component mounts
  useEffect(() => {
    if (hasPermission) {
      startRecording();
    }
    
    return () => {
      // Clean up by stopping recording if component unmounts
      if (isRecording) {
        stopRecording(false);
      }
      
      // And stop the timer
      stopTimer();
    };
  }, [hasPermission]);
  
  // Permission request UI
  if (!hasPermission) {
    return (
      <div className="audioCapture">
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px',
          textAlign: 'center'
        }}>
          <p>Microphone permission is required to record audio.</p>
          <div style={{ marginTop: '20px' }}>
            <button 
              style={{ 
                padding: '10px 20px', 
                marginRight: '10px', 
                background: '#4A90E2', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px' 
              }}
              onClick={() => AudioService.requestPermissions().then(setHasPermission)}
            >
              Grant Permission
            </button>
            <button 
              style={{ 
                padding: '10px 20px', 
                background: '#E2E2E2', 
                border: 'none', 
                borderRadius: '4px' 
              }}
              onClick={() => setIsOpen(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className={`audioCapture audio-recorder ${isRecording ? "recording" : ""}`}>
      <button
        className="captureButton send"
        onClick={() => stopRecording(true)}
      >
        <IconSend/>
      </button>
      
      <span
        className={`audio-recorder-timer ${!isRecording ? "display-none" : ""}`}
        data-testid="ar_timer"
      >
        {Math.floor(recordingTime / 60)}:
        {String(recordingTime % 60).padStart(2, "0")}
      </span>
      
      {/* Visualizer placeholder for native app - we could implement a custom visualizer here */}
      <span
        className={`audio-recorder-visualizer ${!isRecording ? "display-none" : ""}`}
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          width: '140px',
          height: '30px'
        }}
      >
        <div style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          {/* Simple animated bars to indicate recording */}
          {[...Array(10)].map((_, i) => (
            <div key={i} style={{
              width: '2px',
              height: `${Math.sin((Date.now() / 300) + i) * 10 + 15}px`,
              margin: '0 2px',
              background: 'white',
              animation: `pulse 1s ease-in-out ${i * 0.1}s infinite`
            }} />
          ))}
        </div>
      </span>
      
      <button
        className="captureButton close"
        onClick={() => stopRecording(false)}
      >
        <IconClose/>
      </button>
      
      {/* Add a simple CSS animation for the recording indicator */}
      <style>
        {`
          @keyframes pulse {
            0% { height: 5px; }
            50% { height: 20px; }
            100% { height: 5px; }
          }
        `}
      </style>
    </div>
  );
}