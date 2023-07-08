import { useCallback, useRef, useState, useEffect } from "react";
import axios from "axios"
import Webcam from "react-webcam";
import browserID from "browser-id";
import Carousel, { CarouselItem } from "./Carousel";
import IconRefresh from "./icons/IconRefresh";

import './Clio.css';
import './ClioApp.css';

import IconChevronLeft from "./icons/IconChevronLeft";
import IconChevronRight from "./icons/IconChevronRight";
import Toolbar from "./Toolbar";
import MainMenu from "./MainMenu";


const audioConstraints = {
    suppressLocalAudioPlayback: true,
    noiseSuppression: true,
};
const thisBrowserID = browserID();

const getDefaultStrategy = () => {
    const queryParameters = new URLSearchParams(window.location.search);
    return queryParameters.get('strategy');
};

let getFramesInterval = null;
let checkMediaDevicesInterval = null;
let hideOverlaysInterval = null;


const renderFrame = (frame, index) => {
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
    const stateRef = useRef();
    const [frames, setFrames] = useState([]);
    const [selectedFrameNumber, setSelectedFrameNumber] = useState(-1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [captureActive, setCaptureActive] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const [cameras, setCameras] = useState([]);
    const [strategies, setStrategies] = useState([]);
    const [strategy, setStrategy] = useState(getDefaultStrategy());
    const [cameraDeviceId, setCameraDeviceId] = useState("default");
    const [isFullScreen, setIsFullScreen] = useState(false);

    function handleResize() {
        const root = document.querySelector(':root');
        const vp_height = `${window.innerHeight}px`;
        root.style.setProperty('--vp-height', vp_height);
        console.log(`Set --vp-height to ${vp_height}`)
    };

    useEffect(() => {
            function handleMouseMove(e) {
                e.preventDefault();

                //if (isFullScreen && !hideOverlaysInterval) {
                if (!hideOverlaysInterval) {
                    const rootElement = document.getElementById("root");
                    rootElement.classList.add("show-overlays");

                    hideOverlaysInterval = setInterval(() => {
                        clearInterval(hideOverlaysInterval);
                        hideOverlaysInterval = null;
                        rootElement.classList.remove('show-overlays');
                    }, 2000);
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
        (mediaDevices) => {
            const cameras = mediaDevices.filter(({ kind }) => kind === "videoinput");
            cameras.push({
                label: "Camera Off",
                deviceId: null,
            });
            setCameras(cameras);
            console.log(`Found ${cameras.length} cameras: ${cameras}`);
            if (cameras) {
                cameras.map((camera) => {
                    console.log(`Camera ${camera.deviceId}, '${camera.label || camera.deviceId}'`)
                });
                if (!cameraDeviceId && cameras.length > 0) {
                    console.log(`Initializing cameraDeviceId to ${cameras[0].deviceId}.`);
                    setCameraDeviceId(cameras[0].deviceId);
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
                clearInterval(checkMediaDevicesInterval);
                checkMediaDevicesInterval = null;
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

    const toggleFullscreen = useCallback(
        () => {
            const newIsFullscreen = !isFullScreen;
            console.log(`Setting isFullScreen to ${newIsFullscreen}.`);
            setIsFullScreen(newIsFullscreen);
            if (newIsFullscreen) {
                document.documentElement.requestFullscreen();
            }
            else {
                document.exitFullscreen();
            }
        },
        [isFullScreen]
    );

    const handleFullscreen = useCallback(
        () => {
            const isCurrentlyFullscreen = !!document.fullscreenElement;
            console.log(`handleFullscreen, isCurrentlyFullscreen=${isCurrentlyFullscreen}`);
            handleResize();

            const rootElement = document.getElementById("root");
            if (isCurrentlyFullscreen) {
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

    stateRef.handleFullscreen = handleFullscreen;
    useEffect(() => {
        const dynHandleFullscreen = () => stateRef.handleFullscreen();

        document.addEventListener('fullscreenchange', dynHandleFullscreen);
        return () => {
            document.removeEventListener('fullscreenchange', dynHandleFullscreen);
        }
    }, []);

    const webcamRef = useRef(null);
    const captureImage = useCallback(
        () => {
            const imageSrc = webcamRef.current ? webcamRef.current.getScreenshot() : null;
            const parts = imageSrc ? imageSrc.split(",") : null;
            return (parts && parts.length > 1) ? parts[1] : null;
        },
        [webcamRef]
    );
    const renderEmptyFrame = useCallback(
        () => {
            return <CarouselItem>
                <div className="clio_app">
                </div>
            </CarouselItem>;
        },
        [webcamRef, captureActive]
    );

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
        async () => {
            console.log(`Enter getFrames. isPlaying=${isPlaying}`)
            setLoading(true)
            try {
                if (getFramesInterval) {
                    clearInterval(getFramesInterval);
                    getFramesInterval = null;
                }
                console.log(`captureImage().`)
                const uploadImage = captureImage();
    
                let params = {
                    client_id: thisBrowserID,
                    client_type: "clio",
                    input_image: uploadImage,
                    debug: true,
                };

                if (strategy) {
                    params.strategy = strategy;
                }
                const imagePrefix = uploadImage ? uploadImage.substr(0, 20) : "(none)";
                console.log(`Calling Calliope with strategy ${strategy}, image ${imagePrefix}...`);
                setCaptureActive(false);
                setSelectedFrameNumber(frames ? frames.length: 0);
                const response = await axios.post(
                    "/v1/frames/",
                    params,
                    {
                        headers: {
                            "X-Api-Key": "xyzzy",
                        },
                    },
                );
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
                    getFramesInterval = setInterval(() => stateRef.getFrames(), 20000);
                }
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
            setCaptureActive(false);
        },
        [thisBrowserID, frames, setCaptureActive, isPlaying, strategy]
    );
    stateRef.getFrames = getFrames;

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
                        getFramesInterval = setInterval(() => stateRef.getFrames(), 500);
                    }
                } catch (err) {
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
        async (newSelectedFrameNumber) => {
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
                    setCaptureActive(true);
                    // Wait a moment before capturing an image, giving the
                    // Webcam a beat to initialize.
    
                    console.log(`newSelectedFrameNumber=${newSelectedFrameNumber}, frames.length=${frames.length}. Scheduling frames request.`);
                    getFramesInterval = setInterval(() => stateRef.getFrames(), 500);
                }
            }
        },
        [frames, getFrames, selectedFrameNumber, setCaptureActive, setSelectedFrameNumber]
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
                } catch (err) {
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

    const videoConstraints = {
        width: 512,
        height: 512,
    };
    if (cameraDeviceId != "default") {
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
            { cameraDeviceId &&
                <Webcam
                    ref={webcamRef}
                    className="webcamVideo"
                    videoConstraints={videoConstraints}
                />
            }
        </div>
        <Carousel
            selectedIndex={selectedFrameNumber}
            incrementSelectedIndex={aheadOne}
            decrementSelectedIndex={backOne}
        >
            {frames.map(renderFrame)}
            {renderEmptyFrame()}
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
                toggleFullscreen={toggleFullscreen}
                menu={<MainMenu
                    strategies={strategies}
                    strategy={strategy}
                    setStrategy={setStrategy}
                    cameras={cameras}
                    camera={cameraDeviceId}
                    setCamera={setCameraDeviceId}
                />}
            />
        }
        {
            loading &&
            <div className="spinnerFrame">
                <IconRefresh style={{
                    animation: 'rotate 2s linear infinite',
                    display: "block",
                    margin: "auto"
                }}/>
            </div>
        }
    </>;
}
