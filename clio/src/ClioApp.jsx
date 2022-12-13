import { useState, useEffect } from "react";
import axios from "axios"

import styles from './ClioApp.module.css';

export default function ClioApp() {
    const [frameData, setFrameData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [requestCount, setRequestCount] = useState(0);

    useEffect(() => {
        let getFramesInterval = null;

        const getFrames = async () => {
            setLoading(true)
            try {
                const response = await axios.get(
                    `/v1/frames/?api_key=xyzzy&client_id=chris&input_text=Mirrors%20and%20candles.&strategy=continuous_v0`
                );
                setFrameData(response.data);
                setError(null);

                clearInterval(getFramesInterval);
                getFramesInterval = setInterval(getFrames, 20000);
                setRequestCount(requestCount => requestCount + 1);
                console.log(`requestCount = ${requestCount}`)
            } catch (err) {
                setError(err.message);
                // setFrameData(null);
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

    const frame = (frameData && frameData['frames'].length) ? frameData['frames'][0] : null
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
            <div className={styles.text}>
                {frame ? frame.text : ''}
            </div>
        </div>
    </div >;
}
