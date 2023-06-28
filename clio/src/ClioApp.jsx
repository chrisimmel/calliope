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

const getStrategy = () => {
    const queryParameters = new URLSearchParams(window.location.search);
    return queryParameters.get('strategy');
};


export default function ClioApp() {
    const bottomRef = useRef(null);

    const [storyText, setStoryText] = useState("")
    const [append_to_prior_frames, setAppendToPriorFrames] = useState(false)
    const [frameData, setFrameData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [image_url, setImageUrl] = useState(null);

    const getPanels = () => {
        /*
        One panel for each frame, including an empty rightmost panel whose selection
        triggers a request for a new frame. When the new rightmost panel contents
        arrive, a _new_ rightmost panel is made available for the same purpose.

        It is also always possible to scroll back through all prior frames of the
        story.
        */
    }

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
        if (append_to_prior_frames) {
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

                let params = {
                    client_id: thisBrowserID,
                    client_type: "clio",
                    input_image: uploadImage,
                    debug: true,
                };
                if (strategy) {
                    params.strategy = strategy
                }
                console.log("Calling Calliope...");
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

                setFrameData(response.data);

                const frame = getFrame(response.data);
                if (frame) {
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
                }

                setError(null);
                getFramesInterval = setInterval(getFrames, 20000);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        // Wait a second before requesting the first frame, giving the
        // Webcam a beat to initialize.
        getFramesInterval = setInterval(getFrames, 1000);

        return () => {
            // Clear the interval when unmounting the component.
            if (getFramesInterval) {
                clearInterval(getFramesInterval);
            }
        };
    },
        []
    );

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
