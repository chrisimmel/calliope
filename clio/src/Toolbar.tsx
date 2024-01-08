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
    toggleFullscreen: () => void,
    startCameraCapture: () => void,
    menu: any,
}

export default function Toolbar({
    toStart,
    toEnd,
    toggleIsPlaying,
    isPlaying,
    toggleFullscreen,
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
            <button
                className="navButton"
                onClick={() => {
                    toggleIsPlaying();
                }}
            >
                {
                    isPlaying &&
                    <IconPause/>
                }
                {
                    !isPlaying &&
                    <IconPlay/>
                }
            </button>
            <button
                className="navButton"
                onClick={() => {
                    toEnd();
                }}
            >
                <IconFastForward/>
            </button>
            <button
                className="navButton"
                onClick={() => {
                    toggleFullscreen();
                }}
            >
                <IconFullscreen/>
            </button>
            <button
                className="navButton"
                onClick={() => {
                    startCameraCapture();
                }}
            >
                <IconCamera/>
            </button>
            {menu}
        </div>
    </>;
}
