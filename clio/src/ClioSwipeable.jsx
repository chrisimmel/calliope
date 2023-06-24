import { useCallback, useRef, useState, useEffect } from "react";
import axios from "axios"
import Webcam from "react-webcam";
import browserID from "browser-id";
import Carousel, { CarouselItem } from "./Carousel";

import styles from './ClioApp.module.css';

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
        <div className={styles.clio_app}>
            <div className={styles.image}>
                {image_url && <img src={image_url} />}
            </div>
            <div className={styles.textFrame}>
                <div className={styles.textContainer}>
                    <div className={styles.textInner}>
                        <div className={styles.textScroll}>
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
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const webcamRef = useRef(null);
    const captureImage = useCallback(
        () => {
            const imageSrc = webcamRef.current.getScreenshot();
            const parts = imageSrc ? imageSrc.split(",") : null;
            uploadImage = (parts && parts.length > 1) ? parts[1] : null;
            console.log(`captureImage, uploadImage=${uploadImage}`);
        },
        [webcamRef]
    );
    const renderEmptyFrame = useCallback(
        () => {
            return <CarouselItem>
                <div className={styles.clio_app}>
                    <Webcam
                        ref={webcamRef}
                        className={styles.webcamVideo}
                        videoConstraints={videoConstraints}
                    />
                </div>
            </CarouselItem>;
        },
        [webcamRef]
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
                    setFrames(response.data?.frames);
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
                    console.log(`I think I see ${caption}.`);
                }

                const newFrames = response.data?.frames;
                if (newFrames) {
                    setFrames(frames => [...frames, ...newFrames]);

                    /*
                    if (frame.image && frame.image.url) {
                        setImageUrl(`/${frame.image.url}`);
                    }
    
                    if (frame && frame.text) {
                        setAppendToPriorFrames(response.data.append_to_prior_frames)
                        if (response.data.append_to_prior_frames) {
                            setStoryText(storyText => storyText + frame.text);
                        }
                        else {
                            setStoryText(frame.text);
                        }
                    }
                    */
                }

                setError(null);
                //getFramesInterval = setInterval(getFrames, 20000);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        },
        [thisBrowserID, frames]
    );

    const onSelectItem = useCallback(
        async (newIndex) => {
            console.log(`New index is ${newIndex}, total frames: ${frames.length}.`);
            if (newIndex >= frames.length) {
                // Wait a half-second before capturing an image, giving the
                // Webcam a beat to initialize.
                getFramesInterval = setInterval(getFrames, 500);
            }
        },
        [frames, getFrames]
    );

    /*
    One panel for each frame, including an empty rightmost panel whose selection
    triggers a request for a new frame. When the new rightmost panel contents
    arrive, a _new_ rightmost panel is made available for the same purpose.

    It is also always possible to scroll back through all prior frames of the
    story.
    */
    return <>
        <Carousel onSelectItem={onSelectItem} defaultIndex={frames.length - 1}>
            {frames.map(renderFrame)}
            {renderEmptyFrame()}
        </Carousel>
    </>;
}
