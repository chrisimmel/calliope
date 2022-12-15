import { useCallback, useRef, useState, useEffect } from "react";
import axios from "axios"
import Webcam from "react-webcam";
import browserID from "browser-id";

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

const DEFAULT_STRATEGY = 'continuous_v0'

const getStrategy = () => {
    const queryParameters = new URLSearchParams(window.location.search);
    return queryParameters.get('strategy') || DEFAULT_STRATEGY;
};

export default function ClioApp() {
    const bottomRef = useRef(null);

    const [storyText, setStoryText] = useState("")
    const [frameData, setFrameData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [requestCount, setRequestCount] = useState(0);

    const webcamRef = useRef(null);
    let uploadImage = null
    const captureImage = useCallback(
        () => {
            const imageSrc = webcamRef.current.getScreenshot();
            const parts = imageSrc ? imageSrc.split(",") : null;
            uploadImage = (parts && parts.length > 1) ? parts[1] : null;
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


    useEffect(() => {
        const strategy = getStrategy();
        if (strategy == DEFAULT_STRATEGY) {
            // Scroll to bottom when text is added.
            bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, [storyText]);

    const getFrame = (_frameData) => {
        return (_frameData && _frameData['frames'].length) ? _frameData['frames'][0] : null;
    };

    useEffect(() => {
        let getFramesInterval = null;

        const getFrames = async () => {
            setLoading(true)
            try {
                if (getFramesInterval) {
                    clearInterval(getFramesInterval);
                }
                const strategy = getStrategy();

                await captureImage();

                /*
                const formData = new FormData();
                formData.append('client_id', thisBrowserID);
                formData.append('strategy', 'continuous_v0');
                formData.append("input_image", uploadImage);
                */

                const response = await axios.post(
                    "/v1/frames/",
                    {
                        client_id: thisBrowserID,
                        strategy: strategy,
                        input_image: uploadImage,
                        debug: true,
                    },
                    {
                        headers: {
                            "X-Api-Key": "xyzzy",
                        },
                    },
                );
                console.log(response.data);
                const caption = response.data?.debug_data?.i_see;
                if (caption) {
                    console.log(`I see ${caption.trim()}.`);
                }

                setFrameData(response.data);
                const frame = getFrame(response.data);
                if (frame) {
                    if (frame && frame.text) {
                        if (strategy == DEFAULT_STRATEGY) {
                            setStoryText(storyText => storyText + frame.text);
                        }
                        else {
                            setStoryText(frame.text);
                        }
                    }
                }

                setError(null);

                getFramesInterval = setInterval(getFrames, 20000);
                setRequestCount(requestCount => requestCount + 1);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        getFrames()

        return () => {
            // Clear the interval when unmounting the component.
            if (getFramesInterval) {
                clearInterval(getFramesInterval);
            }
        };
    },
        []
    );

    const frame = getFrame(frameData)
    const image = frame ? frame.image : null
    // This unfortunate fizzlebuzz thing is just to force download of a new image. This is
    // because the back end today generally swaps out the image behind the same filename
    // rather than issuing a new filename with each request.  TODO: Fix on back end and
    // remove fizzlebuzz.  
    const image_url = image ? (`/${image.url}?fizzlebuzz=${requestCount}`) : ""

    return <>
        <Webcam
            ref={webcamRef}
            className={styles.webcamVideo}
            videoConstraints={videoConstraints}
        />
        <div className={styles.clio_app}>
            <div className={styles.image}>
                <img src={image_url} />
            </div>
            <div className={styles.textFrame}>
                <div className={styles.textContainer}>
                    <div className={styles.textInner}>
                        <div className={styles.textScroll}>
                            {storyText}
                            <div ref={bottomRef} />
                        </div>
                    </div>
                </div>
            </div>
        </div >
    </>;
}
/*
audio={true}
muted={true}
audioConstraints={audioConstraints}
*/
