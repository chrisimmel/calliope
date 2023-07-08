import './ClioApp.css';
import './Toolbar.css';
import IconFastForward from "./icons/IconFastForward";
import IconPause from "./icons/IconPause";
import IconPlay from "./icons/IconPlay";
import IconCameraReverse from "./icons/IconCameraReverse";
import IconRewind from "./icons/IconRewind";
import IconMenu from "./icons/IconMenu";
import IconFullscreen from './icons/IconFullScreen';

export default function Toolbar({
    toStart,
    toEnd,
    toggleIsPlaying,
    isPlaying,
    switchCamera,
    canSwitchCamera,
    toggleFullscreen,
    menu,
}) {
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
            {
                canSwitchCamera &&
                <button
                    className="navButton"
                    onClick={() => {
                        switchCamera();
                    }}
                >
                    <IconCameraReverse/>
                </button>
            }
            <button
                className="navButton"
                onClick={() => {
                    toggleFullscreen();
                }}
            >
                <IconFullscreen/>
            </button>
            {menu}
        </div>
    </>;
}
