import './ClioApp.css';
import './Toolbar.css';
import IconFastForward from "./icons/IconFastForward";
import IconPause from "./icons/IconPause";
import IconPlay from "./icons/IconPlay";
import IconRewind from "./icons/IconRewind";
import IconFullscreen from './icons/IconFullscreen';
import IconCamera from './icons/IconCamera';

type ToolbarProps = {
    toStart: () => void,
    toEnd: () => void,
    toggleIsPlaying: () => void,
    isPlaying: boolean,
    toggleFullScreen: () => void,
    isFullScreen: boolean,
    startCameraCapture: () => void,
    menu: any,
}

export default function Toolbar({
    toStart,
    toEnd,
    toggleIsPlaying,
    isPlaying,
    toggleFullScreen,
    isFullScreen,
    startCameraCapture,
    menu,
}: ToolbarProps) {
    return <>
        <div className="nav">
            <button
                className="navButton"
                onClick={() => {
                    toStart();
                }}
            >
                <IconRewind/>
            </button>
            {
                isPlaying &&
                <button
                    className="navButton"
                    onClick={() => {
                        toggleIsPlaying();
                    }}
                >
                    <IconPause/>
                </button>
            }
            <button
                className="navButton"
                onClick={() => {
                    toEnd();
                }}
            >
                <IconFastForward/>
            </button>
            {
                isFullScreen &&
                <button
                    className="navButton"
                    onClick={() => {
                        toggleFullScreen();
                    }}
                >
                    <IconFullscreen/>
                </button>
            }
            {
                !isPlaying &&
                /*
                Enable camera capture for now only if not playing.
                This avoids a concurrency bug.
                 */
                <button
                    className="navButton"
                    onClick={() => {
                        startCameraCapture();
                    }}
                >
                    <IconCamera/>
                </button>
            }
            {menu}
        </div>
    </>;
}
