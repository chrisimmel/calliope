import { useCallback, useRef, useState, useEffect } from "react";
import axios from "axios"
import Webcam from "react-webcam";
import browserID from "browser-id";
import Carousel, { CarouselItem } from "./Carousel";
import IconRefresh from "./icons/IconRefresh";

import './Clio.css';
import styles from './ClioApp.css';

import IconChevronLeft from "./icons/IconChevronLeft";
import IconChevronRight from "./icons/IconChevronRight";
import Toolbar from "./Toolbar";

const videoConstraints = {
    width: 512,
    height: 512,
    facingMode: "user",
};
const audioConstraints = {
    suppressLocalAudioPlayback: true,
    noiseSuppression: true,
};
const thisBrowserID = browserID();

const getStrategy = () => {
    const queryParameters = new URLSearchParams(window.location.search);
    return queryParameters.get('strategy');
};

let uploadImage = null;
let getFramesInterval = null;


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
    const [frames, setFrames] = useState([]);
    const [selectedFrameNumber, setSelectedFrameNumber] = useState(-1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [captureActive, setCaptureActive] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const [canSwitchCamera, setCanSwitchCamera] = useState(true);
    const [cameraDeviceId, setCameraDeviceId] = useState(null);
    const [isMenuActive, setIsMenuActive] = useState(false);

    const toggleIsPlaying = useCallback(
        () => {
            setIsPlaying(isPlaying => !isPlaying);
        },
        [isPlaying]
    );
    const switchCamera = useCallback(
        () => {
            // TODO
        },
        [cameraDeviceId]
    );
    const activateMenu = useCallback(
        () => {
            setIsMenuActive(true);
        },
        [isMenuActive]
    );

    const webcamRef = useRef(null);
    const captureImage = useCallback(
        () => {
            const imageSrc = webcamRef.current.getScreenshot();
            const parts = imageSrc ? imageSrc.split(",") : null;
            uploadImage = (parts && parts.length > 1) ? parts[1] : null;
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
    const handleStartCaptureClick = React.useCallback(() => {
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

    const handleStopCaptureClick = React.useCallback(() => {
        mediaRecorderRef.current.stop();
        setCapturing(false);
    }, [mediaRecorderRef, setCapturing]);
    */

    const getFrames = useCallback(
        async () => {
            setLoading(true)
            try {
                if (getFramesInterval) {
                    clearInterval(getFramesInterval);
                }
                const strategy = getStrategy();

                await captureImage();
    
                let params = {
                    client_id: thisBrowserID,
                    client_type: "clio",
                    input_image: uploadImage,
                    debug: true,
                };
                if (strategy) {
                    params.strategy = strategy
                }
                const imagePrefix = uploadImage ? uploadImage.substr(0, 20) : "(none)";
                console.log(`Calling Calliope with image ${imagePrefix}...`);
                setCaptureActive(false);
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
                //getFramesInterval = setInterval(getFrames, 20000);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
            setCaptureActive(false);
        },
        [thisBrowserID, frames, setCaptureActive]
    );

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

                    if (!newFrames.length) {
                        // If the story is empty, get a new frame.
                        setCaptureActive(true);
                        // Wait a moment before capturing an image, giving the
                        // Webcam a beat to initialize.
        
                        getFramesInterval = setInterval(getFrames, 500);
                    }
                } catch (err) {
                    setError(err.message);
                } finally {
                    setLoading(false);
                }
            };

            getStory();
        },
        [setFrames, setSelectedFrameNumber]
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
                if (newSelectedFrameNumber >= frames.length) {
                    setCaptureActive(true);
                    // Wait a moment before capturing an image, giving the
                    // Webcam a beat to initialize.
    
                    getFramesInterval = setInterval(getFrames, 500);
                }
            }
        },
        [frames, getFrames, selectedFrameNumber, setCaptureActive, setSelectedFrameNumber]
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

    /*
    One panel for each frame, including an empty rightmost panel whose selection
    triggers a request for a new frame. When the new rightmost panel contents
    arrive, a _new_ rightmost panel is made available for the same purpose.

    It is also always possible to scroll back through all prior frames of the
    story.
    */
    return <>
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
        <div className="clio_app">
            { true &&
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
        <Toolbar
            toStart={toStart}
            toEnd={toEnd}
            toggleIsPlaying={toggleIsPlaying}
            isPlaying={isPlaying}
            switchCamera={switchCamera}
            canSwitchCamera={canSwitchCamera}
            activateMenu={activateMenu}
        />
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
