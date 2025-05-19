import '../ClioApp.css';
import './Toolbar.css';
import IconPause from "../icons/IconPause";
import IconFullscreen from '../icons/IconFullscreen';
import IconCamera from '../icons/IconCamera';
import IconPlus from "../icons/IconPlus";
import IconMenu from '../icons/IconMenu';
import IconMicrophone from '../icons/IconMicrophone';
import IconHeartFull from '../icons/IconHeartFull';
import IconHeartEmpty from '../icons/IconHeartEmpty';
import IconShare from '../icons/IconShare';
import MainDrawer from '../components/MainDrawer';
import { Bookmark, Frame, FrameSeedMediaType, Story, Strategy } from '../story/storyTypes';


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
    currentStory: Story | null, // Add currentStory prop
    isReadOnly: boolean,
    setStory: (story_id: string | null) => void,
    jumpToBeginning: () => void,
    jumpToEnd: () => void,
    selectedFrameNumber: number,
    frames: Frame[],

    startAudioCapture: () => void,
    startCameraCapture: () => void,
    addNewFrame: () => void,
    
    toggleBookmark: () => void,
    isCurrentFrameBookmarked: boolean,
    bookmarks: Bookmark[],
    showBookmarksList: boolean,
    setShowBookmarksList: (show: boolean) => void,
    shareCurrentUrl: () => void,
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
    currentStory,
    isReadOnly,
    setStory,
    jumpToBeginning,
    jumpToEnd,
    selectedFrameNumber,
    frames,

    startAudioCapture,
    startCameraCapture,
    addNewFrame,
    
    toggleBookmark,
    isCurrentFrameBookmarked,
    bookmarks,
    showBookmarksList,
    setShowBookmarksList,
    shareCurrentUrl,
}: ToolbarProps) {
    /*
    Enable camera capture for now only if not playing.
    This avoids a concurrency bug.
        */
    // Only allow adding frames if not in read-only mode and not playing
    const allowAddFrame = !isPlaying && !isLoading && !drawerIsOpen && !isReadOnly;
    const allowSocial = !isLoading && !drawerIsOpen && !!story_id && selectedFrameNumber >= 0 && selectedFrameNumber < frames.length;
    return <>
        <div className="nav">
            {/* Disable auto-play for now.
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
            } */}
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
            
            {/* Divider between add frame and social buttons */}
            {(allowAddFrame && (story_id && selectedFrameNumber >= 0 && selectedFrameNumber < frames.length)) && 
                <div className="toolbar-divider"></div>
            }
            
            {
                allowSocial &&
                <button
                    className="navButton"
                    onClick={toggleBookmark}
                >
                    {isCurrentFrameBookmarked ? <IconHeartFull/> : <IconHeartEmpty/>}
                </button>
            }
            {
                allowSocial &&
                <button
                    className="navButton"
                    onClick={shareCurrentUrl}
                    title="Share URL"
                >
                    <IconShare/>
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
            {
                !isLoading &&
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
                    currentStory={currentStory}
                    setStory={setStory}
                    jumpToBeginning={jumpToBeginning}
                    jumpToEnd={jumpToEnd}
                    selectedFrameNumber={selectedFrameNumber}
                    bookmarks={bookmarks}
                    showBookmarksList={showBookmarksList}
                    setShowBookmarksList={setShowBookmarksList}
                />
            }
        </div>
    </>;
}
