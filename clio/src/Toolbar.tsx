import './ClioApp.css';
import './Toolbar.css';
import IconFastForward from "./icons/IconFastForward";
import IconPause from "./icons/IconPause";
import IconRewind from "./icons/IconRewind";
import IconFullscreen from './icons/IconFullscreen';
import IconCamera from './icons/IconCamera';
import IconPlus from "./icons/IconPlus";

type ToolbarProps = {
    toStart: () => void,
    toEnd: () => void,
    toggleIsPlaying: () => void,
    isPlaying: boolean,
    isLoading: boolean,
    toggleFullScreen: () => void,
    isFullScreen: boolean,
    startCameraCapture: () => void,
    addNewFrame: () => void,
    menu: any,
}

export default function Toolbar({
    toStart,
    toEnd,
    toggleIsPlaying,
    isPlaying,
    isLoading,
    toggleFullScreen,
    isFullScreen,
    startCameraCapture,
    addNewFrame,
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
                !isPlaying && !isLoading &&
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
            {
                !isPlaying && !isLoading &&
                /*
                Enable add new frame for now only if not playing.
                This avoids a concurrency bug.
                 */
                <button
                    className="navButton"
                    onClick={() => {
                        addNewFrame();
                    }}
                >
                    <IconPlus/>
                </button>
            }
            {menu}
        </div>
    </>;
}
