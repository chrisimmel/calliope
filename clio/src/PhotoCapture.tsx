import { useCallback, useRef, useState, useEffect } from "react";
import {Camera, CameraType} from "react-camera-pro";

import IconCameraReverse from './icons/IconCameraReverse';
import IconClose from './icons/IconClose';
import IconSend from './icons/IconSend';
import Loader from "./Loader";


type PhotoCaptureProps = {
    sendPhoto: (photo: string | null) => void,
    closePhotoCapture: () => void,
}

const errorMessages = {
    noCameraAccessible: 'No camera device accessible. Please connect your camera or try a different browser.',
    permissionDenied: 'Permission denied. Please refresh and give camera permission.',
    switchCamera:
      'It is not possible to switch camera to different one because there is only one video device accessible.',
    canvas: 'Canvas is not supported.',
};


export default function PhotoCapture({sendPhoto, closePhotoCapture}: PhotoCaptureProps) {
    const camera = useRef<CameraType>(null);
    const [facingMode, setFacingMode] = useState<string>(localStorage.getItem('facingMode') || "environment");
    const [numberOfCameras, setNumberOfCameras] = useState<number>(0);
    const captureImage = useCallback(
       (): string | null => {
            if (camera.current) {
                return camera.current.takePhoto();
            }
            return null;
       },
       [camera]
    );

    return (
        <div className="photoCapture">
            <div className="photoCaptureInner">
                {
                    !camera.current &&
                    <Loader/>
                }
                <Camera
                    facingMode={facingMode == "user" ? "user" : "environment"}
                    ref={camera} errorMessages={errorMessages}
                    numberOfCamerasCallback={(i) => setNumberOfCameras(i)}
                />
                <button
                    className="captureButton close"
                    onClick={() => {
                        closePhotoCapture();
                    }}
                >
                    <IconClose/>
                </button>
                <button
                    className="captureButton send"
                    onClick={() => {
                        const image = captureImage();
                        sendPhoto(image);
                    }}
                >
                    <IconSend/>
                </button>
                {
                    numberOfCameras > 1 &&
                    <button
                        className="captureButton reverseCamera"
                        onClick={() => {
                            if (camera.current) {
                                const facingMode = camera.current.switchCamera();
                                console.log(`Facing mode: ${facingMode}`);
                                setFacingMode(facingMode);
                                localStorage.setItem('facingMode', facingMode);
                            }
                        }}
                        >
                        <IconCameraReverse/>
                    </button>
                }
            </div>
        </div>
    );
}
