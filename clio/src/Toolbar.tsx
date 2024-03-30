import './ClioApp.css';
import './Toolbar.css';
import IconPause from "./icons/IconPause";
import IconFullscreen from './icons/IconFullscreen';
import IconCamera from './icons/IconCamera';
import IconPlus from "./icons/IconPlus";
import IconMenu from './icons/IconMenu';
import ClioDrawer from './ClioDrawer';
import { Frame, Story, Strategy } from './Types';

type ToolbarProps = {
    drawerIsOpen: boolean,
    setDrawerIsOpen: (drawerIsOpen: boolean) => void,
    allowExperimental: boolean,
    strategies: Strategy[],
    strategy: string | null,
    startNewStory: (strategy: string | null) => void,
    startNewStoryWithPhoto: (strategy: string | null) => void,

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
    startNewStoryWithPhoto,

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

    startCameraCapture,
    addNewFrame,
}: ToolbarProps) {
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
                !isPlaying && !isLoading && !drawerIsOpen &&
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
                !isPlaying && !isLoading && !drawerIsOpen &&
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
            <ClioDrawer
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
                startNewStoryWithPhoto={startNewStoryWithPhoto}
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
