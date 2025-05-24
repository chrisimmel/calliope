import { useState, useEffect } from "react";
import { isPlatform } from "../utils/platform";
import { CameraService } from "../services/CameraService";

// Import the original components
import PhotoCapture from "./PhotoCapture";
import IconCameraReverse from '../icons/IconCameraReverse';
import IconClose from '../icons/IconClose';
import IconSend from '../icons/IconSend';
import Loader from "../components/Loader";

type PhotoCaptureAdapterProps = {
    sendPhoto: (photo: string | null) => void,
    closePhotoCapture: () => void,
}

export default function PhotoCaptureAdapter({sendPhoto, closePhotoCapture}: PhotoCaptureAdapterProps) {
    const [isLoading, setIsLoading] = useState(false);
    const [facingMode, setFacingMode] = useState<string>(localStorage.getItem('facingMode') || "environment");
    const [hasPermission, setHasPermission] = useState(false);
    
    // Check permissions on component mount
    useEffect(() => {
        async function checkPermissions() {
            if (isPlatform.capacitor()) {
                const permissionGranted = await CameraService.checkCameraAvailability();
                setHasPermission(permissionGranted);
                
                // If no permission, request it
                if (!permissionGranted) {
                    const requested = await CameraService.requestPermissions();
                    setHasPermission(requested);
                }
            } else {
                setHasPermission(true); // For web, we'll handle this in the original component
            }
        }
        
        checkPermissions();
    }, []);
    
    // If on the web, use the original PhotoCapture component
    if (isPlatform.web()) {
        return <PhotoCapture sendPhoto={sendPhoto} closePhotoCapture={closePhotoCapture} />;
    }
    
    // On native platforms, use Capacitor Camera
    const captureImage = async () => {
        if (!hasPermission) {
            const requested = await CameraService.requestPermissions();
            if (!requested) {
                console.error('Camera permission denied');
                return;
            }
            setHasPermission(requested);
        }
        
        setIsLoading(true);
        try {
            const image = await CameraService.takePhoto({
                facingMode: facingMode === 'user' ? 'user' : 'environment',
                quality: 90
            });
            sendPhoto(image);
        } catch (error) {
            console.error('Error capturing image:', error);
            sendPhoto(null);
        } finally {
            setIsLoading(false);
        }
    };
    
    const toggleCamera = async () => {
        const newFacingMode = facingMode === 'user' ? 'environment' : 'user';
        setFacingMode(newFacingMode);
        localStorage.setItem('facingMode', newFacingMode);
    };
    
    if (!hasPermission) {
        return (
            <div className="photoCapture">
                <div className="photoCaptureInner">
                    <div className="captureErrorMessage">
                        <p>Camera permission is required to take photos.</p>
                        <button onClick={() => CameraService.requestPermissions().then(setHasPermission)}>
                            Grant Permission
                        </button>
                        <button onClick={closePhotoCapture}>Cancel</button>
                    </div>
                </div>
            </div>
        );
    }
    
    return (
        <div className="photoCapture">
            <div className="photoCaptureInner">
                {isLoading && <Loader />}
                <div style={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    height: '100%',
                    width: '100%',
                    background: '#000',
                    position: 'relative',
                    flexDirection: 'column'
                }}>
                    {/* Instructions for the user */}
                    {!isLoading && (
                        <div style={{ color: 'white', marginBottom: '20px', textAlign: 'center' }}>
                            Tap the button below to take a photo
                        </div>
                    )}
                    
                    <button
                        className="captureButton close"
                        onClick={closePhotoCapture}
                        style={{
                            position: 'absolute',
                            top: '20px',
                            left: '20px'
                        }}
                    >
                        <IconClose/>
                    </button>
                    
                    <button
                        className="captureButton send"
                        onClick={captureImage}
                        style={{
                            position: 'relative', 
                            width: '70px',
                            height: '70px',
                            borderRadius: '50%',
                            background: 'white'
                        }}
                    >
                        <IconSend/>
                    </button>
                    
                    <button
                        className="captureButton reverseCamera"
                        onClick={toggleCamera}
                        style={{
                            position: 'absolute',
                            bottom: '20px',
                            right: '20px'
                        }}
                    >
                        <IconCameraReverse/>
                    </button>
                </div>
            </div>
        </div>
    );
}