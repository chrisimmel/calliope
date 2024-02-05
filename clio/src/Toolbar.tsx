import './ClioApp.css';
import './Toolbar.css';
import IconPause from "./icons/IconPause";
import IconFullscreen from './icons/IconFullscreen';
import IconCamera from './icons/IconCamera';
import IconPlus from "./icons/IconPlus";

type ToolbarProps = {
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
            {menu}
        </div>
    </>;
}
