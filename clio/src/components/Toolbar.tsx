import '../ClioApp.css';
import './Toolbar.css';
import IconPause from "../icons/IconPause";
import IconFullscreen from '../icons/IconFullscreen';
import IconCamera from '../icons/IconCamera';
import IconPlus from "../icons/IconPlus";
import IconMenu from '../icons/IconMenu';
import IconMicrophone from '../icons/IconMicrophone';
import MainDrawer from '../components/MainDrawer';
import { Frame, FrameSeedMediaType, Story, Strategy } from '../story/storyTypes';


type ToolbarProps = {
    drawerIsOpen: boolean,
    setDrawerIsOpen: (drawerIsOpen: boolean) => void,
    allowExperimental: boolean,
    strategies: Strategy[],
    strategy: string | null,
    startNewStory: (strategy: string | null, media_type: FrameSeedMediaType) => void,

    isLoading: boolean,
    isPlaying: boolean,
    toggleIsPlaying: () => void,
    isFullScreen: boolean,
    toggleFullScreen: () => void,
    stories: Story[],
    story_id: string | null,
    setStory: (story_id: string | null) => void,
    jumpToBeginning: () => void,
    jumpToEnd: () => void,
    selectedFrameNumber: number,
    frames: Frame[],

    startAudioCapture: () => void,
    startCameraCapture: () => void,
    addNewFrame: () => void,
}

export default function Toolbar({
    drawerIsOpen,
    setDrawerIsOpen,
    allowExperimental,
    strategies,
    strategy,
    startNewStory,

    isLoading,
    isPlaying,
    toggleIsPlaying,
    isFullScreen,
    toggleFullScreen,
    stories,
    story_id,
    setStory,
    jumpToBeginning,
    jumpToEnd,
    selectedFrameNumber,
    frames,

    startAudioCapture,
    startCameraCapture,
    addNewFrame,
}: ToolbarProps) {
    /*
    Enable camera capture for now only if not playing.
    This avoids a concurrency bug.
        */
    const allowAddFrame = !isPlaying && !isLoading && !drawerIsOpen;
    return <>
        <div className="nav">
            {
                isPlaying && !drawerIsOpen &&
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
                isFullScreen && !drawerIsOpen &&
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
                allowAddFrame &&
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
                allowAddFrame && !!navigator.mediaDevices &&
                <button
                    className="navButton"
                    onClick={() => {
                        startAudioCapture();
                    }}
                >
                    <IconMicrophone/>
                </button>
            }
            {
                allowAddFrame &&
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
                !drawerIsOpen &&
                <button
                    className="navButton menuButton"
                    onClick={() => {
                        setDrawerIsOpen(true);
                    }}
                >
                    <IconMenu/>
                </button>
            }
            <MainDrawer
                drawerIsOpen={drawerIsOpen}
                setDrawerIsOpen={setDrawerIsOpen}
                stories={stories}

                toggleIsPlaying={toggleIsPlaying}
                isPlaying={isPlaying}
                toggleFullScreen={toggleFullScreen}
                allowExperimental={allowExperimental}
                strategies={strategies}
                strategy={strategy}
                startNewStory={startNewStory}
                frames={frames}
                story_id={story_id}
                setStory={setStory}
                jumpToBeginning={jumpToBeginning}
                jumpToEnd={jumpToEnd}
                selectedFrameNumber={selectedFrameNumber}
                />
        </div>
    </>;
}
