import { useRef, useState, useEffect } from "react";
import axios from "axios"

import styles from './ClioApp.module.css';

export default function ClioApp() {
    const bottomRef = useRef(null);

    const [storyText, setStoryText] = useState("")
    const [frameData, setFrameData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [requestCount, setRequestCount] = useState(0);

    useEffect(() => {
        // Scroll to bottom when text is added.
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
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

                const response = await axios.get(
                    `/v1/frames/?api_key=xyzzy&client_id=chris&input_text=A prose poem expressing great longing.&strategy=continuous_v0`
                );

                setFrameData(response.data);
                const frame = getFrame(response.data);
                if (frame) {
                    if (frame && frame.text) {
                        setStoryText(storyText => storyText + frame.text);
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

    return <div className={styles.clio_app}>
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
    </div >;
}
