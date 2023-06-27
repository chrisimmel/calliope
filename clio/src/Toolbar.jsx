import styles from './Toolbar.module.css';
import IconFastForward from "./icons/IconFastForward";
import IconPause from "./icons/IconPause";
import IconPlay from "./icons/IconPlay";
import IconCameraReverse from "./icons/IconCameraReverse";
import IconRewind from "./icons/IconRewind";
import IconMenu from "./icons/IconMenu";

export default function Toolbar({
    toStart,
    toEnd,
    toggleIsPlaying,
    isPlaying,
    switchCamera,
    canSwitchCamera,
    activateMenu
}) {
    return <>
        <div className={styles.nav}>
            <button
                className={styles.navButton}
                onClick={() => {
                    toStart();
                }}
            >
                <IconRewind/>
            </button>
            <button
                className={styles.navButton}
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
                className={styles.navButton}
                onClick={() => {
                    toEnd();
                }}
            >
                <IconFastForward/>
            </button>
            {
                canSwitchCamera &&
                <button
                    className={styles.navButton}
                    onClick={() => {
                        switchCamera();
                    }}
                >
                    <IconCameraReverse/>
                </button>
            }
            <button
                className={styles.navButton}
                onClick={() => {
                    activateMenu();
                }}
            >
                <IconMenu/>
            </button>
        </div>
    </>;
}
