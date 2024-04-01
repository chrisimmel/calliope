import React, { Suspense, useEffect, useState } from 'react';
import IconClose from './icons/IconClose';
import IconSend from './icons/IconSend';
import useAudioRecorder from './audio/useAudioRecorder';

import "./audio/audio-recorder.css";

const LiveAudioVisualizer = React.lazy(async () => {
  const { LiveAudioVisualizer } = await import("react-audio-visualize");
  return { default: LiveAudioVisualizer };
});

type AudioCaptureProps = {
  setIsOpen: (open: boolean) => void,
  sendAudio: (audio: string) => void,
}

export default function AudioCapture({
  setIsOpen,
  sendAudio,
}: AudioCaptureProps) {
  const audioTrackConstraints = {
    // noiseSuppression: true,
    // echoCancellation: true,
    autoGainControl: true,
    // channelCount,
    // deviceId,
    // groupId,
    // sampleRate,
    // sampleSize,
  };

  const {
    canRecord,
    startRecording,
    stopRecording,
    togglePauseResume,
    recordingBlob,
    isRecording,
    isPaused,
    recordingTime,
    mediaRecorder,
  } =
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useAudioRecorder(audioTrackConstraints);

  useEffect(() => {
    startRecording();
  }, []);

  const [shouldSave, setShouldSave] = useState(false);

  useEffect(() => {
    if (recordingBlob != null && sendAudio != null) {
      if (shouldSave) {
        var reader = new FileReader();
        reader.onloadend = function() {
          const base64data = reader.result || "";
          sendAudio(base64data as string);
        }
        reader.readAsDataURL(recordingBlob);
      }
      setIsOpen(false);
    }
}, [recordingBlob]);

  return (
    <div className={`audioCapture audio-recorder ${isRecording ? "recording" : ""}`}>
      {
        canRecord &&
        <>
          <button
              className="captureButton send"
              onClick={() => {
                setShouldSave(true);
                stopRecording();
              }}
          >
              <IconSend/>
          </button>
          <span
            className={`audio-recorder-timer ${
              !isRecording ? "display-none" : ""
            }`}
            data-testid="ar_timer"
          >
            {Math.floor(recordingTime / 60)}:
            {String(recordingTime % 60).padStart(2, "0")}
          </span>
          <span
            className={`audio-recorder-visualizer ${
              !isRecording ? "display-none" : ""
            }`}
          >
            {mediaRecorder && (
              <Suspense fallback={<></>}>
                <LiveAudioVisualizer
                  mediaRecorder={mediaRecorder}
                  barWidth={2}
                  gap={2}
                  width={140}
                  height={30}
                  fftSize={512}
                  maxDecibels={-10}
                  minDecibels={-80}
                  smoothingTimeConstant={0.4}
                />
              </Suspense>
            )}
          </span>
        </>
      }
      {
        !canRecord &&
        <span>Cannot record audio</span>
      }

      <button
          className="captureButton close"
          onClick={() => {
            setShouldSave(false);
            stopRecording();
            if (!canRecord) {
              setIsOpen(false);
            }
          }}
      >
          <IconClose/>
      </button>
    </div>
  );
}
