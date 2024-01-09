import { useCallback, useRef, useState, useEffect } from "react";
import axios from "axios"
import browserID from "browser-id";
import Carousel, { CarouselItem } from "./Carousel";
import IconRefresh from "./icons/IconRefresh";

import './Clio.css';
import './ClioApp.css';

import { DEVICE_ID_DEFAULT, DEVICE_ID_NONE, Frame, MediaDevice } from './Types'; 
import IconChevronLeft from "./icons/IconChevronLeft";
import IconChevronRight from "./icons/IconChevronRight";
import Toolbar from "./Toolbar";
import MainMenu from "./MainMenu";
import PhotoCapture from "./PhotoCapture";
import Loader from "./Loader";


const audioConstraints = {
    suppressLocalAudioPlayback: true,
    noiseSuppression: true,
};
const thisBrowserID = browserID();

const getDefaultStrategy: () => string | null = () => {
    const queryParameters = new URLSearchParams(window.location.search);
    const urlStrategy = queryParameters.get('strategy');
    const savedStrategy = localStorage.getItem('strategy');

    return urlStrategy || (savedStrategy != "" ? savedStrategy : null);
};

let getFramesInterval: ReturnType<typeof setTimeout> | null = null;
let checkMediaDevicesInterval: ReturnType<typeof setTimeout> | null = null;
let hideOverlaysInterval: ReturnType<typeof setTimeout> | null = null;



const renderFrame = (frame: Frame, index: number) => {
    const image_url = (frame.image && frame.image.url) ? `/${frame.image.url}` : '';

    return <CarouselItem key={index}>
        <div className="clio_app">
            <div className="image">
                {image_url && <img src={image_url} />}
            </div>
            <div className="textFrame">
                <div className="textContainer">
                    <div className="textInner">
                        <div className="textScroll">
                            {frame.text}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </CarouselItem>;
}


export default function ClioApp() {
    type ClioState = {
        handleFullScreen: () => void,
        getFrames: (image: string | null) => void,
    }

    const stateRef = useRef<ClioState>({handleFullScreen: () => null, getFrames: () => null});
    const [frames, setFrames] = useState<Frame[]>([]);
    const [selectedFrameNumber, setSelectedFrameNumber] = useState<number>(-1);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [captureActive, setCaptureActive] = useState<boolean>(false);
    const [isPlaying, setIsPlaying] = useState<boolean>(false);
    const [cameras, setCameras] = useState<MediaDevice[]>([]);
    const [strategies, setStrategies] = useState([]);
    const [strategy, setStrategy] = useState<string | null>(getDefaultStrategy());
    const [cameraDeviceId, setCameraDeviceId] = useState<string>(DEVICE_ID_DEFAULT);
    const [isFullScreen, setIsFullScreen] = useState<boolean>(false);

    function handleResize() {
        const root: HTMLElement | null = document.querySelector(':root');
        if (root) {
            const vp_height = `${window.innerHeight}px`;
            root.style.setProperty('--vp-height', vp_height);
            console.log(`Set --vp-height to ${vp_height}`)
        }
    };

    useEffect(() => {
            function handleMouseMove(e: any) {
                e.preventDefault();

                //if (isFullScreen && !hideOverlaysInterval) {
                if (!hideOverlaysInterval) {
                    const rootElement: HTMLElement | null = document.getElementById("root");
                    if (rootElement) {
                        rootElement.classList.add("show-overlays");

                        hideOverlaysInterval = setInterval(() => {
                            if (hideOverlaysInterval) {
                                clearInterval(hideOverlaysInterval);
                                hideOverlaysInterval = null;
                            }
                            rootElement.classList.remove('show-overlays');
                        }, 2000);
                    }
                }
            }

            window.addEventListener("mousemove", handleMouseMove);
            return () => {
                window.removeEventListener("mousemove", handleMouseMove);
            };
        },
        [isFullScreen, hideOverlaysInterval]
    );

    const handleMediaDevices = useCallback(
        (mediaDevices: MediaDevice[]) => {
            const cameras = mediaDevices.filter((device: MediaDevice) => device.kind === "videoinput");
            cameras.push({
                kind: "videoinput",
                label: "Camera Off",
                deviceId: DEVICE_ID_NONE,
            });
            setCameras(cameras);
            console.log(`Found ${cameras.length} cameras: ${cameras}`);
            if (cameras) {
                cameras.map((camera) => {
                    console.log(`Camera ${camera.deviceId}, '${camera.label || camera.deviceId}'`)
                });
                if (cameraDeviceId == DEVICE_ID_DEFAULT && cameras.length > 0) {
                    let selectedDeviceId = null;
                    let selectedDeviceLabel = null;
                    for (let i = 0; i < cameras.length && !selectedDeviceId; i++) {
                        const label = cameras[i].label;
                        if (label == "Back Camera") {
                            selectedDeviceId = cameras[i].deviceId;
                            selectedDeviceLabel = label;
                        }
                    }
                    if (!selectedDeviceId) {
                        selectedDeviceId = cameras[0].deviceId;
                        selectedDeviceLabel = cameras[0].label;
                    }
                    console.log(`Initializing camera to ${selectedDeviceLabel}.`);
                    setCameraDeviceId(selectedDeviceId);
                }
            }
        },
        [setCameras, cameraDeviceId, cameras]
    );

    const checkMediaDevices = useCallback(
        () => {
            console.log(`checkMediaDevices()...`);
            navigator.mediaDevices.enumerateDevices().then(handleMediaDevices);
        },
        [handleMediaDevices]
    );

    useEffect(
        () => {
            // Check the media devices once immediately. This seems to be enough
            // in a browser running on a desktop.
            checkMediaDevices();

            // But on an iPhone, we need to wait a few seconds and try again.
            checkMediaDevicesInterval = setInterval(() => {
                if (checkMediaDevicesInterval) {
                    clearInterval(checkMediaDevicesInterval);
                    checkMediaDevicesInterval = null;
                }
                checkMediaDevices();
            }, 3000);
        },
        []
    );

    useEffect(() => {
        handleResize();

        window.addEventListener('resize', handleResize)
        if (window.screen && window.screen.orientation) {
            try {
                window.addEventListener('orientationchange', handleResize);
                window.screen.orientation.onchange = handleResize;
            }
            catch (e) {
                console.error(e);
            }
        }
        return () => {
            window.removeEventListener('resize', handleResize)
            window.removeEventListener('orientationchange', handleResize);
            if (window.screen && window.screen.orientation) {
                window.screen.orientation.onchange = null;
            }
        }

    }, []);

    const toggleFullScreen = useCallback(
        () => {
            const newIsFullScreen = !isFullScreen;
            console.log(`Setting isFullScreen to ${newIsFullScreen}.`);
            setIsFullScreen(newIsFullScreen);
            if (newIsFullScreen) {
                document.documentElement.requestFullscreen();
            }
            else {
                document.exitFullscreen();
            }
        },
        [isFullScreen]
    );
    
    const startCameraCapture = useCallback(
        () => {
            setCaptureActive(true);
        },
        []
    );

    const handleFullScreen = useCallback(
        () => {
            const isCurrentlyFullScreen = !!document.fullscreenElement;
            console.log(`handleFullScreen, isCurrentlyFullScreen=${isCurrentlyFullScreen}`);
            handleResize();

            const rootElement = document.getElementById("root");
            if (isCurrentlyFullScreen) {
                //rootElement.classList.add("fullscreen");
                setIsFullScreen(true);
            }
            else {
                //rootElement.classList.remove('fullscreen');
                setIsFullScreen(false);
            }
        },
        [isFullScreen]
    );

    stateRef.current.handleFullScreen = handleFullScreen;
    useEffect(() => {
        const dynHandleFullScreen = () => stateRef.current.handleFullScreen();

        document.addEventListener('fullscreenchange', dynHandleFullScreen);
        return () => {
            document.removeEventListener('fullscreenchange', dynHandleFullScreen);
        }
    }, []);

    /*
    const renderEmptyFrame = useCallback(
        () => {
            return <CarouselItem>
                <div className="clio_app">
                </div>
            </CarouselItem>;
        },
        [webcamRef, captureActive]
    );
    */

    /*
    const handleStartCaptureClick = useCallback(() => {
        setCapturing(true);
        mediaRecorderRef.current = new MediaRecorder(webcamRef.current.stream, {
            mimeType: "audio/wav",
        });
        mediaRecorderRef.current.addEventListener(
            "dataavailable",
            handleDataAvailable
        );
        mediaRecorderRef.current.start();
    }, [webcamElement, setCapturing, mediaRecorderRef, handleDataAvailable]);

    const handleStopCaptureClick = useCallback(() => {
        mediaRecorderRef.current.stop();
        setCapturing(false);
    }, [mediaRecorderRef, setCapturing]);
    */

    const getFrames = useCallback(
        async (image: string | null) => {
            console.log(`Enter getFrames. isPlaying=${isPlaying}`)
            setLoading(true)
            try {
                if (getFramesInterval) {
                    clearInterval(getFramesInterval);
                    getFramesInterval = null;
                }
                //console.log(`captureImage().`)
                //const uploadImage = captureImage();
    
                let params: {client_id: string, client_type: string, input_image: string | null, debug: boolean, strategy?: string} = {
                    client_id: thisBrowserID,
                    client_type: "clio",
                    input_image: image,
                    debug: true,
                };

                if (strategy) {
                    params.strategy = strategy;
                }
                const imagePrefix = image ? image.substring(0, 20) : "(none)";
                console.log(`Calling Calliope with strategy ${strategy}, image ${imagePrefix}...`);
                setCaptureActive(false);
                //setSelectedFrameNumber(frames ? frames.length: 0);
                const response = await axios.post(
                    "/v1/frames/",
                    params,
                    {
                        headers: {
                            "X-Api-Key": "xyzzy",
                        },
                    },
                );
                setSelectedFrameNumber(frames ? frames.length: 0);
                console.log(response.data);
                const caption = response.data?.debug_data?.i_see;
                if (caption) {
                    console.log(`I think I see: ${caption}.`);
                }

                const newFrames = response.data?.frames;
                if (newFrames) {
                    setFrames(frames => [...frames, ...newFrames]);
                }

                setError(null);
                console.log(`Got frames. isPlaying=${isPlaying}`)
                if (isPlaying) {
                    console.log("Scheduling frames request in 20s.");
                    getFramesInterval = setInterval(() => stateRef.current.getFrames(null), 20000);
                }
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
            setCaptureActive(false);
        },
        [thisBrowserID, frames, setCaptureActive, isPlaying, strategy]
    );
    stateRef.current.getFrames = getFrames;

    useEffect(
        () => {
            const getStory = async () => {
                setLoading(true)
                try {
                    let params = {
                        client_id: thisBrowserID,
                        debug: true,
                    };
                    console.log("Getting story...");
                    const response = await axios.get(
                        "/v1/story/",
                        {
                            headers: {
                                "X-Api-Key": "xyzzy",
                            },
                            params: params,
                        },
                    );
                    console.log(`Got ${response.data?.frames?.length} frames.`);
                    const newFrames = response.data?.frames || [];
                    setFrames(newFrames);
                    setSelectedFrameNumber(newFrames ? newFrames.length - 1 : 0);

                    if (!newFrames.length && !getFramesInterval) {
                        // If the story is empty, get a new frame.
                        setCaptureActive(true);
                        // Wait a moment before capturing an image, giving the
                        // Webcam a beat to initialize.

                        console.log("Scheduling a request for an initial frame.");
                        getFramesInterval = setInterval(() => stateRef.current.getFrames(null), 500);
                    }
                } catch (err: any) {
                    setError(err.message);
                } finally {
                    setLoading(false);
                }
            };

            getStory();
        },
        []
    );

    const selectFrameNumber = useCallback(
        async (newSelectedFrameNumber: number) => {
            const frameCount = frames.length;
            if (newSelectedFrameNumber < 0) {
                newSelectedFrameNumber = 0;
            } else if (newSelectedFrameNumber > frameCount) {
                newSelectedFrameNumber = frameCount;
            }
    
            if (newSelectedFrameNumber != selectedFrameNumber) {
                setSelectedFrameNumber(newSelectedFrameNumber);

                console.log(`New index is ${newSelectedFrameNumber}, total frames: ${frameCount}.`);
                if (newSelectedFrameNumber >= frames.length && !getFramesInterval) {
                    //setCaptureActive(true);
                    // Wait a moment before capturing an image, giving the
                    // Webcam a beat to initialize.
    
                    console.log(`newSelectedFrameNumber=${newSelectedFrameNumber}, frames.length=${frames.length}. Scheduling frames request.`);
                    getFramesInterval = setInterval(() => stateRef.current.getFrames(null), 500);
                }
            }
        },
        [frames, getFrames, selectedFrameNumber, setCaptureActive, setSelectedFrameNumber]
    );

    const toggleIsPlaying = useCallback(
        () => {
            const newIsPlaying = !isPlaying;
            console.log(`Setting isPlaying to ${newIsPlaying}.`);
            setIsPlaying(newIsPlaying);
            if (newIsPlaying) {
                // Kick things off by generating and moving to a new frame.
                selectFrameNumber(frames.length);
            }
            else {
                if (getFramesInterval) {
                    clearInterval(getFramesInterval);
                    getFramesInterval = null;
                }
            }
        },
        [isPlaying, frames, selectFrameNumber]
    );

    useEffect(
        () => {
            const getStrategies = async () => {
                try {
                    let params = {
                        client_id: thisBrowserID,
                    };
                    console.log("Getting strategies...");
                    const response = await axios.get(
                        "/v1/config/strategy/",
                        {
                            headers: {
                                "X-Api-Key": "xyzzy",
                            },
                            params: params,
                        },
                    );
                    const newStrategies = response.data || [];
                    console.log(`Got ${response.data?.length} strategies.`);
                    setStrategies(newStrategies);
                } catch (err: any) {
                    setError(err.message);
                }
            };

            getStrategies();
        },
        []
    );

    const aheadOne = useCallback(
        () => {
            selectFrameNumber(selectedFrameNumber + 1);
        },
        [selectedFrameNumber, selectFrameNumber]
    );
    const backOne = useCallback(
        () => {
            selectFrameNumber(selectedFrameNumber - 1);
        },
        [selectedFrameNumber, selectFrameNumber]
    );
    const toStart = useCallback(
        () => {
            selectFrameNumber(0);
        },
        [selectedFrameNumber, selectFrameNumber]
    );
    const toEnd = useCallback(
        () => {
            selectFrameNumber(frames.length - 1);
        },
        [selectedFrameNumber, selectFrameNumber, frames]
    );
    const sendPhoto = useCallback(
        (image: string | null) => {
            setCaptureActive(false);
            const parts = image ? image.split(",") : null;
            image = (parts && parts.length > 1) ? parts[1] : null;

            console.log("Scheduling frames request.");
            getFramesInterval = setInterval(() => stateRef.current.getFrames(image), 10);
        },
        []
    );
    const closePhotoCapture = useCallback(
        () => {
            setCaptureActive(false);
        },
        []
    );
    const updateStrategy = useCallback(
        (strategy: string | null) => {
            console.log(`Setting strategy to ${strategy}.`);
            localStorage.setItem('strategy', strategy || "");
            setStrategy(strategy);
        },
        []
    );

    type VideoConstraints = {
        width?: number,
        height?: number,
        deviceId?: string,
        facingMode?: string,
    }
    const videoConstraints: VideoConstraints = {
        width: 512,
        height: 512,
        deviceId: undefined,
        facingMode: undefined,
    };
    if (cameraDeviceId != DEVICE_ID_DEFAULT && cameraDeviceId != DEVICE_ID_NONE) {
        videoConstraints.deviceId = cameraDeviceId;
    }
    else {
        videoConstraints.facingMode = "environment";
    }

    /*
    One panel for each frame, including an empty rightmost panel whose selection
    triggers a request for a new frame. When the new rightmost panel contents
    arrive, a _new_ rightmost panel is made available for the same purpose.

    It is also always possible to scroll back through all prior frames of the
    story.
    */
    return <>
        {
            /*!isFullScreen &&*/
            <div className="navLeft">
                <button
                    className="navButton"
                    onClick={() => {
                        backOne();
                    }}
                >
                    <IconChevronLeft/>
                </button>
            </div>
        }
        <div className="clio_app">
            { captureActive &&
                <PhotoCapture
                    sendPhoto={sendPhoto}
                    closePhotoCapture={closePhotoCapture}
                />
            }
        </div>
        <Carousel
            selectedIndex={Math.max(0, Math.min(selectedFrameNumber, frames.length - 1))}
            incrementSelectedIndex={aheadOne}
            decrementSelectedIndex={backOne}
        >
            {frames.map(renderFrame)}
            {/*{renderEmptyFrame()}*/}
        </Carousel>
        {
            /*!isFullScreen &&*/
            <div className="navRight">
                <button
                    className="navButton"
                    onClick={() => {
                        aheadOne();
                    }}
                >
                    <IconChevronRight/>
                </button>
            </div>
        }
        {
            /*!isFullScreen &&*/
            <Toolbar
                toStart={toStart}
                toEnd={toEnd}
                toggleIsPlaying={toggleIsPlaying}
                isPlaying={isPlaying}
                isFullScreen={isFullScreen}
                toggleFullScreen={toggleFullScreen}
                startCameraCapture={startCameraCapture}
                menu={<MainMenu
                    strategies={strategies}
                    strategy={strategy}
                    setStrategy={updateStrategy}
                    cameras={cameras}
                    camera={cameraDeviceId}
                    setCamera={setCameraDeviceId}
                    toggleIsPlaying={toggleIsPlaying}
                    isPlaying={isPlaying}
                    toggleFullScreen={toggleFullScreen}
                />}
            />
        }
        {
            loading &&
            <div className="spinnerFrame">
                {/*
                <IconRefresh style={{
                    animation: 'rotate 2s linear infinite',
                    display: "block",
                    margin: "auto"
                }}/>
                */}
                <Loader/>
            </div>
        }
    </>;
}
