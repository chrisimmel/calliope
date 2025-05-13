import { useCallback, useRef, useState, useEffect } from "react";
import axios from "axios"
import browserID from "browser-id";

import './ClioApp.css';
import AudioCapture from "./audio/AudioCapture";
import Carousel, { CarouselItem } from "./components/Carousel";
import { Bookmark, BookmarksResponse, Frame, FrameSeedMediaType, Story, Strategy } from './story/storyTypes'; 
import IconChevronLeft from "./icons/IconChevronLeft";
import IconChevronRight from "./icons/IconChevronRight";
import Loader from "./components/Loader";
import PhotoCapture from "./photo/PhotoCapture";
import Toolbar from "./components/Toolbar";

const FRAMES_TIMEOUT = 180_000;
const DEFAULT_TIMEOUT = 30_000;

const audioConstraints = {
    suppressLocalAudioPlayback: true,
    noiseSuppression: true,
};
const thisBrowserID = browserID();

const getDefaultStrategy: () => string | null = () => {
    const queryParameters = new URLSearchParams(window.location.search);
    const urlStrategy = queryParameters.get('strategy');
    const savedStrategy = localStorage.getItem('strategy');

    return urlStrategy || (savedStrategy != "" ? savedStrategy : null);
};
const getDefaultStoryAndFrame: () => [string | null, number | null] = () => {
    const queryParameters = new URLSearchParams(window.location.search);
    const urlStory = queryParameters.get('story');
    const parts = urlStory ? urlStory?.split(':') : [];
    const storyId = parts.length ? parts[0] : null;
    const frameNumber = parts.length > 1 ? parseInt(parts[1]) : (storyId != null ? 0 : null);

    return [storyId, frameNumber];
};
const getAllowExperimental: () => boolean = () => {
    const queryParameters = new URLSearchParams(window.location.search);
    const xParam = queryParameters.get('x');
    return xParam != null && xParam == '1';
};

let getFramesInterval: ReturnType<typeof setTimeout> | null = null;
let hideOverlaysInterval: ReturnType<typeof setTimeout> | null = null;


const renderFrame = (frame: Frame, index: number) => {
    const image_url = (frame.image && frame.image.url) ? `/${frame.image.url}` : '';
    const video_url = (frame.video && frame.video.url) ? `/${frame.video.url}` : '';

    return <CarouselItem key={index}>
        <div className="clio_app">
            <div className="image">
                {video_url ? (
                    <video 
                        autoPlay 
                        loop 
                        muted 
                        playsInline
                        controls={false} 
                        poster={image_url}
                        style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                    >
                        <source src={video_url} type='video/mp4; codecs="avc1.42E01E, mp4a.40.2"' />
                        {image_url && <img src={image_url} />}
                    </video>
                ) : (
                    image_url && <img src={image_url} />
                )}
            </div>
            <div className="textFrame">
                <div className="textContainer">
                    <div className="textInner">
                        <div className="textScroll">
                            {frame.text}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </CarouselItem>;
}


const resetStory = async () => {
    const params: {client_id: string} = {
        client_id: thisBrowserID,
    };

    await axios.put(
        "/v1/story/reset/",
        null,
        {
            headers: {
                "X-Api-Key": "xyzzy",
            },
            params: params,
            timeout: DEFAULT_TIMEOUT,
        },
    );
};


export default function ClioApp() {
    type ClioState = {
        handleFullScreen: () => void,
        getFrames: (image: string | null, audio: string | null) => void,
    }

    const stateRef = useRef<ClioState>({handleFullScreen: () => null, getFrames: () => null});
    const [frames, setFrames] = useState<Frame[]>([]);
    const [selectedFrameNumber, setSelectedFrameNumber] = useState<number>(-1);
    const [loadingFrames, setLoadingFrames] = useState<boolean>(false);
    const [loadingStrategies, setLoadingStrategies] = useState<boolean>(true);
    const [loadingStory, setLoadingStory] = useState<boolean>(true);
    const [loadingStories, setLoadingStories] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [captureActive, setCaptureActive] = useState<boolean>(false);
    const [captureAudioActive, setCaptureAudioActive] = useState<boolean>(false);
    const [isPlaying, setIsPlaying] = useState<boolean>(false);
    const [strategies, setStrategies] = useState<Strategy[]>([]);
    const [defaultStrategy, setDefaultStrategy] = useState<string | null>(getDefaultStrategy());
    const [allowExperimental, setAllowExperimental] = useState<boolean>(getAllowExperimental());
    const [strategy, setStrategy] = useState<string | null>(defaultStrategy);
    const [isFullScreen, setIsFullScreen] = useState<boolean>(false);
    const [stories, setStories] = useState<Story[]>([]);
    const [storyId, setStoryId] = useState<string | null>(null);
    const [drawerIsOpen, setDrawerIsOpen] = useState<boolean>(false);
    const [showOverlays, setShowOverlays] = useState<boolean>(false);
    const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
    const [loadingBookmarks, setLoadingBookmarks] = useState<boolean>(false);
    const [showBookmarksList, setShowBookmarksList] = useState<boolean>(false);
  
    function handleResize() {
        const root: HTMLElement | null = document.querySelector(':root');
        if (root) {
            const vp_height = `${document.documentElement.clientHeight}px`;
            root.style.setProperty('--vp-height', vp_height);
            console.log(`Set --vp-height to ${vp_height}`)
        }
    };

    useEffect(() => {
            function handleMouseMove(e: any) {
                e.preventDefault();

                if (!hideOverlaysInterval) {
                    const rootElement: HTMLElement | null = document.getElementById("root");
                    if (rootElement) {
                        rootElement.classList.add("show-overlays");
                        setShowOverlays(true);

                        hideOverlaysInterval = setInterval(() => {
                            if (hideOverlaysInterval) {
                                clearInterval(hideOverlaysInterval);
                                hideOverlaysInterval = null;
                            }
                            rootElement.classList.remove('show-overlays');
                            setShowOverlays(false);
                        }, 2000);
                    }
                }
            }

            window.addEventListener("mousemove", handleMouseMove);
            return () => {
                window.removeEventListener("mousemove", handleMouseMove);
            };
        },
        [isFullScreen, hideOverlaysInterval]
    );

    useEffect(() => {
        handleResize();

        window.addEventListener('resize', handleResize)
        if (window.screen && window.screen.orientation) {
            try {
                window.addEventListener('orientationchange', handleResize);
                window.screen.orientation.onchange = handleResize;
            }
            catch (e) {
                console.error(e);
            }
        }
        return () => {
            window.removeEventListener('resize', handleResize)
            window.removeEventListener('orientationchange', handleResize);
            if (window.screen && window.screen.orientation) {
                window.screen.orientation.onchange = null;
            }
        }

    }, []);

    const toggleFullScreen = useCallback(
        () => {
            const newIsFullScreen = !isFullScreen;
            console.log(`Setting isFullScreen to ${newIsFullScreen}.`);
            setIsFullScreen(newIsFullScreen);
            if (newIsFullScreen) {
                document.documentElement.requestFullscreen();
            }
            else {
                document.exitFullscreen();
            }
        },
        [isFullScreen]
    );
    
    const startCameraCapture = useCallback(
        () => {
            setCaptureActive(true);
        },
        []
    );
    const startAudioCapture = useCallback(
        () => {
            setCaptureAudioActive(true);
            console.log("Starting audio capture...");
        },
        []
    );

    const handleFullScreen = useCallback(
        () => {
            const isCurrentlyFullScreen = !!document.fullscreenElement;
            console.log(`handleFullScreen, isCurrentlyFullScreen=${isCurrentlyFullScreen}`);
            handleResize();

            const rootElement = document.getElementById("root");
            if (isCurrentlyFullScreen) {
                setIsFullScreen(true);
            }
            else {
                setIsFullScreen(false);
            }
        },
        [isFullScreen]
    );

    stateRef.current.handleFullScreen = handleFullScreen;
    useEffect(() => {
        const dynHandleFullScreen = () => stateRef.current.handleFullScreen();

        document.addEventListener('fullscreenchange', dynHandleFullScreen);
        return () => {
            document.removeEventListener('fullscreenchange', dynHandleFullScreen);
        }
    }, []);

    const updateStoryWithFrames = useCallback(
        (
            story_id: string,
            newFrames: Frame[],
            story_frame_count: number,
            generationDate: string,
            strategy_name: string,
        ) => {
            console.log(`Updating story ${story_id} with ${frames.length} frames.`);
            let storyFound = false;
            const dateUpdated = generationDate.split(" ")[0];

            let newStories = stories;

            for (let i = 0; i < newStories.length; i++) {
                const story = stories[i];
                if (story.story_id == story_id) {
                    storyFound = true;
                    story.story_frame_count = story_frame_count;
                    story.date_updated = dateUpdated;
                    story.is_current = true;
                } else {
                    story.is_current = false;
                }
            }

            if (!storyFound) {
                const maxLength = 64;
                let title = newFrames[0].text || story_id;
                const lines = title.split("\n");
                title = "";
                for (let i = 0; i < lines.length; i++) {
                    if (title.length) {
                        title += " ";
                    }
                    title += lines[i];
                    if (title.length > maxLength) {
                        break;
                    }
                }
                if (title.length > maxLength) {
                    title = title.substring(0, maxLength) + "...";
                }

                const newStory: Story = {
                    story_id: story_id,
                    title: title,
                    story_frame_count: story_frame_count,
                    is_bookmarked: false,
                    is_current: true,
                    is_read_only: false,
                    strategy_name: strategy_name,
                    created_for_sparrow_id: thisBrowserID,
                    thumbnail_image: newFrames[0].image || null, // We'll use the image for thumbnails even for video frames
                    date_created: dateUpdated,
                    date_updated: dateUpdated
                }
                console.log("(Adding new story.");
                newStories = [...newStories, newStory];
            }
            setStories(newStories);
        },
        [stories]
    );

    const getFrames = useCallback(
        async (image: string | null, audio: string | null) => {
            console.log(`Enter getFrames. isPlaying=${isPlaying}`)
            setLoadingFrames(true)
            try {
                if (getFramesInterval) {
                    clearInterval(getFramesInterval);
                    getFramesInterval = null;
                }

                let params: {client_id: string, client_type: string, input_image: string | null, input_audio: string | null, debug: boolean, strategy?: string, story_id?: string, generate_video: boolean} = {
                    client_id: thisBrowserID,
                    client_type: "clio",
                    input_image: image,
                    input_audio: audio,
                    debug: true,
                    generate_video: false,
                };

                if (strategy) {
                    params.strategy = strategy;
                }
                if (storyId) {
                    params.story_id = storyId;
                }
                if (allowExperimental) {
                    params.generate_video = true;
                }
                const imagePrefix = image ? image.substring(0, 20) : "(none)";
                console.log(`Calling Calliope with strategy ${strategy}, image ${imagePrefix}...`);
                setCaptureActive(false);
                //setSelectedFrameNumber(frames ? frames.length: 0);
                const response = await axios.post(
                    "/v1/frames/",
                    params,
                    {
                        headers: {
                            "X-Api-Key": "xyzzy",
                        },
                        timeout: FRAMES_TIMEOUT,
                    },
                );
                setSelectedFrameNumber(frames ? frames.length: 0);
                console.log(response.data);
                const caption = response.data?.debug_data?.i_see;
                if (caption) {
                    console.log(`I think I see: ${caption}.`);
                }
                const transcript = response.data?.debug_data?.i_hear;
                if (transcript) {
                    console.log(`I think I hear: ${transcript}.`);
                }

                const newFrames = response.data?.frames;
                if (newFrames) {
                    setFrames(frames => [...frames, ...newFrames]);
                    setStoryId(response.data?.story_id || null);
                    if (response.data?.story_id) {
                        updateStoryWithFrames(
                            response.data.story_id,
                            newFrames,
                            response.data.story_frame_count,
                            response.data.generation_date,
                            response.data.strategy,
                        )
                    }
                }

                setError(null);
                console.log(`Got frames. isPlaying=${isPlaying}`)
                if (isPlaying) {
                    console.log("Scheduling frames request in 20s.");
                    getFramesInterval = setInterval(() => stateRef.current.getFrames(null, null), 20000);
                }
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoadingFrames(false);
            }
            setCaptureActive(false);
        },
        [
            thisBrowserID,
            frames, 
            setCaptureActive, 
            isPlaying,
            strategy,
            storyId,
            updateStoryWithFrames,
            setStoryId,
        ]
    );
    stateRef.current.getFrames = getFrames;

    const getStory = useCallback(
        async (story_id: string | null, frame_num: number | null) => {
            setLoadingStory(true)
            if (!story_id) {
                const [defaultStoryId, defaultFrameNum] = getDefaultStoryAndFrame();
                story_id = defaultStoryId; // storyId;
                frame_num = defaultFrameNum;
            }

            try {
                const params = {
                    client_id: thisBrowserID,
                    debug: true,
                    story_id: story_id,
                };
                console.log("Getting story...");
                const response = await axios.get(
                    "/v1/story/",
                    {
                        headers: {
                            "X-Api-Key": "xyzzy",
                        },
                        params: params,
                        timeout: DEFAULT_TIMEOUT,
                    },
                );
                console.log(`Got ${response.data?.frames?.length} frames.`);
                const newFrames = response.data?.frames || [];
                setFrames(newFrames);
                //setStrategy(response.data?.strategy || defaultStrategy);
                setStrategy(defaultStrategy);
                setStoryId(response.data?.story_id || null);
                const maxFrameNum = newFrames ? newFrames.length - 1 : 0;
                if (frame_num != null) {
                    frame_num = Math.min(frame_num, maxFrameNum);
                } else {
                    frame_num = maxFrameNum;
                }
                setSelectedFrameNumber(frame_num);

                console.log(`Got story.`);
                console.log(`${newFrames.length}, ${getFramesInterval}`);

                if (!newFrames.length && !getFramesInterval) {
                    // If the story is empty, display the menu.
                    setDrawerIsOpen(true);
                }
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoadingStory(false);
            }
        },
        []
    );

    useEffect(
        () => {
            // Get the default story and jump to its last frame.
            getStory(null, null);
        },
        [getStory]
    );

    useEffect(
        () => {
            const getStories = async () => {
                setLoadingStories(true)
                try {
                    const params = {
                        client_id: thisBrowserID,
                        debug: true,
                    };
                    console.log("Getting stories...");
                    const response = await axios.get(
                        "/v1/stories/",
                        {
                            headers: {
                                "X-Api-Key": "xyzzy",
                            },
                            params: params,
                            timeout: DEFAULT_TIMEOUT,
                        },
                    );
                    console.log(`Got ${response.data?.stories?.length} frames.`);
                    const newStories = response.data?.stories || [];
                    setStories(newStories);
                } catch (err: any) {
                    setError(err.message);
                } finally {
                    setLoadingStories(false);
                }
            };

            getStories();
        },
        []
    );

 
    const selectFrameNumber = useCallback(
        async (newSelectedFrameNumber: number) => {
            const frameCount = frames.length;
            if (newSelectedFrameNumber < 0) {
                newSelectedFrameNumber = 0;
            } else if (newSelectedFrameNumber >= frameCount) {
                newSelectedFrameNumber = frameCount - 1;
            }

            if (newSelectedFrameNumber != selectedFrameNumber) {
                setSelectedFrameNumber(newSelectedFrameNumber);

                console.log(`New index is ${newSelectedFrameNumber}, total frames: ${frameCount}.`);
                /*
                No more getFrames on navigation!
                if (newSelectedFrameNumber >= frames.length && !getFramesInterval) {
                    console.log(`newSelectedFrameNumber=${newSelectedFrameNumber}, frames.length=${frames.length}. Scheduling frames request.`);
                    getFramesInterval = setInterval(() => stateRef.current.getFrames(null), 500);
                }
                */
            }
        },
        [frames, getFrames, selectedFrameNumber, setCaptureActive, setSelectedFrameNumber]
    );

    const toggleIsPlaying = useCallback(
        () => {
            const newIsPlaying = !isPlaying;
            console.log(`Setting isPlaying to ${newIsPlaying}.`);
            setIsPlaying(newIsPlaying);
            if (newIsPlaying) {
                // Kick things off by generating and moving to a new frame.
                selectFrameNumber(frames.length);
            }
            else {
                if (getFramesInterval) {
                    clearInterval(getFramesInterval);
                    getFramesInterval = null;
                }
            }
        },
        [isPlaying, frames, selectFrameNumber]
    );

    useEffect(
        () => {
            const getStrategies = async () => {
                setLoadingStrategies(true);
                try {
                    const params = {
                        client_id: thisBrowserID,
                    };
                    console.log("Getting strategies...");
                    const response = await axios.get(
                        "/v1/config/strategy/",
                        {
                            headers: {
                                "X-Api-Key": "xyzzy",
                            },
                            params: params,
                            timeout: DEFAULT_TIMEOUT,
                        },
                    );
                    const newStrategies = response.data || [];
                    console.log(`Got ${response.data?.length} strategies.`);
                    setStrategies(newStrategies);
                } catch (err: any) {
                    setError(err.message);
                }
                finally {
                    setLoadingStrategies(false);
                }
            };

            getStrategies();
        },
        []
    );

    const aheadOne = useCallback(
        () => {
            selectFrameNumber(selectedFrameNumber + 1);
        },
        [selectedFrameNumber, selectFrameNumber]
    );
    const backOne = useCallback(
        () => {
            selectFrameNumber(selectedFrameNumber - 1);
        },
        [selectedFrameNumber, selectFrameNumber]
    );
    const toStart = useCallback(
        () => {
            selectFrameNumber(0);
        },
        [selectedFrameNumber, selectFrameNumber]
    );
    const toEnd = useCallback(
        () => {
            selectFrameNumber(frames.length - 1);
        },
        [selectedFrameNumber, selectFrameNumber, frames]
    );
    const sendPhoto = useCallback(
        (image: string | null) => {
            if (!isPlaying) {
                setCaptureActive(false);
            }
            const parts = image ? image.split(",") : null;
            image = (parts && parts.length > 1) ? parts[1] : null;

            console.log("Scheduling frames request with image.");
            getFramesInterval = setInterval(() => stateRef.current.getFrames(image, null), 10);
        },
        []
    );
    const sendAudio = useCallback(
        (audio: string) => {
            setCaptureAudioActive(false);
            const parts = audio ? audio.split(",") : null;
            audio = (parts && parts.length > 1) ? parts[1] : audio;

            console.log(`Scheduling frames request with audio.`);
            getFramesInterval = setInterval(() => stateRef.current.getFrames(null, audio), 10);
        },
        []
    );
    const closePhotoCapture = useCallback(
        () => {
            setCaptureActive(false);
        },
        []
    );
    const startNewStory = useCallback(
        async (strategy: string | null, media_type: FrameSeedMediaType) => {
            console.log(`Starting new story with ${strategy} and media: ${media_type}.`);
            localStorage.setItem('strategy', strategy || "");
            setStrategy(strategy);
            setStoryId(null);
            setFrames([]);
            setSelectedFrameNumber(-1);

            await resetStory();

            if (media_type == "photo") {
                startCameraCapture();
            } else if (media_type == "audio") {
                startAudioCapture();
            } else {
                console.log("Scheduling frames request.");
                getFramesInterval = setInterval(() => stateRef.current.getFrames(null, null), 10);
            }
        },
        [resetStory, startCameraCapture, startAudioCapture]
    );

    const findNearestStrategy = useCallback(
        (strategy_name: string | null) => {
            const matchingPrefixLength = (str1: string, str2: string) => {
                let j = 0;
                for (; j < str1.length && j < str2.length && str1[j] == str2[j]; j++) {
                }
                return j;
            };

            if (strategies && strategy_name) {
                let closestStrategyName: string | null = null;
                let longestPrefixLength = 0;
                if (strategy_name.startsWith("continuous-v0")) {
                    console.log(`Story created by deprecated ${strategy_name}. Resetting to tamarisk.`);
                    closestStrategyName = "tamarisk";
                    longestPrefixLength = 5;
                }
                else {
                    for (let k = 0; k < strategies.length; k++) {
                        const candidateStrategy = strategies[k].slug;
                        const prefixLength = matchingPrefixLength(strategy_name, candidateStrategy);
                        if (prefixLength > longestPrefixLength) {
                            closestStrategyName = candidateStrategy;
                            longestPrefixLength = prefixLength;
                        }
                    }
                }
                if (closestStrategyName && longestPrefixLength > 5) {
                    console.log(`Story created by ${strategy_name}. Nearest current strategy is ${closestStrategyName}.`);
                    strategy_name = closestStrategyName;
                }
                else {
                    console.log(`No match found for strategy ${strategy_name}. Using default strategy: ${defaultStrategy}`);
                    strategy_name = defaultStrategy || "tamarisk";
                }
            }
            if (!strategy_name) {
                strategy_name = defaultStrategy || "tamarisk";
            }

            return strategy_name;
        },
        [strategies, defaultStrategy]
    );

    const updateStory = useCallback(
        (story_id: string | null, frame_number: number = 0) => {
            console.log(`Setting story to ${story_id}, frame ${frame_number}.`);
            setStoryId(story_id);

            // Set the strategy to match the selected story.
            for (let i = 0; i < stories.length; i++) {
                const story = stories[i];
                if (story.story_id == story_id) {
                    const strategy_name = findNearestStrategy(story.strategy_name);
                    console.log(`Setting strategy to ${strategy_name}.`);
                    setStrategy(strategy_name);
                    break;
                }
            }

            // Get the selected story and jump to the specified frame.
            getStory(story_id, frame_number);
        },
        [stories, strategies, getStory, findNearestStrategy]
    );

    const addNewFrame = useCallback(
        () => {
            selectFrameNumber(frames.length - 1);
            console.log("Scheduling frames request.");
            getFramesInterval = setInterval(() => stateRef.current.getFrames(null, null), 10);
        },
        [selectedFrameNumber, selectFrameNumber, frames]
    );

    const fetchBookmarks = useCallback(
        async (specific_story_id: string | null = null) => {
            setLoadingBookmarks(true);
            try {
                const params: {client_id: string, story_id?: string} = {
                    client_id: thisBrowserID,
                };
                
                if (specific_story_id) {
                    params.story_id = specific_story_id;
                }

                console.log("Getting bookmarks...");
                const response = await axios.get<BookmarksResponse>(
                    "/v1/bookmarks/frame/",
                    {
                        headers: {
                            "X-Api-Key": "xyzzy",
                        },
                        params: params,
                        timeout: DEFAULT_TIMEOUT,
                    },
                );
                
                console.log(`Got ${response.data?.bookmarks?.length} bookmarks.`);
                setBookmarks(response.data?.bookmarks || []);
            } catch (err: any) {
                setError(err.message);
                console.error("Error fetching bookmarks:", err);
            } finally {
                setLoadingBookmarks(false);
            }
        },
        []
    );

    const toggleBookmark = useCallback(
        async () => {
            if (!storyId || selectedFrameNumber < 0 || selectedFrameNumber >= frames.length) {
                console.error("Cannot bookmark: invalid story or frame");
                return;
            }

            try {
                // Check if this frame is already bookmarked
                const existingBookmark = bookmarks.find(
                    b => b.story_id === storyId && b.frame_number === selectedFrameNumber
                );

                if (existingBookmark) {
                    // Delete the bookmark
                    await axios.delete(
                        `/v1/bookmarks/frame/${existingBookmark.id}`,
                        {
                            headers: {
                                "X-Api-Key": "xyzzy",
                            },
                            params: {
                                client_id: thisBrowserID,
                            },
                            timeout: DEFAULT_TIMEOUT,
                        },
                    );
                    console.log(`Deleted bookmark for frame ${selectedFrameNumber}`);
                    
                    // Update local state
                    setBookmarks(bookmarks.filter(b => b.id !== existingBookmark.id));
                } else {
                    // Create a new bookmark
                    const response = await axios.post(
                        "/v1/bookmarks/frame",
                        {
                            story_id: storyId,
                            frame_number: selectedFrameNumber,
                            comments: null, // Optional comments could be added in the future
                        },
                        {
                            headers: {
                                "X-Api-Key": "xyzzy",
                            },
                            params: {
                                client_id: thisBrowserID,
                            },
                            timeout: DEFAULT_TIMEOUT,
                        },
                    );
                    
                    console.log(`Created bookmark for frame ${selectedFrameNumber}`);
                    
                    // Update local state
                    if (response.data) {
                        setBookmarks([...bookmarks, response.data]);
                    }
                }
            } catch (err: any) {
                setError(err.message);
                console.error("Error toggling bookmark:", err);
            }
        },
        [storyId, selectedFrameNumber, frames, bookmarks]
    );

    const isCurrentFrameBookmarked = useCallback(
        () => {
            if (!storyId || selectedFrameNumber < 0 || selectedFrameNumber >= frames.length) {
                return false;
            }
            
            return bookmarks.some(
                b => b.story_id === storyId && b.frame_number === selectedFrameNumber
            );
        },
        [storyId, selectedFrameNumber, frames, bookmarks]
    );

    // Load bookmarks when the component mounts
    useEffect(() => {
        fetchBookmarks();
    }, [fetchBookmarks]);

    const loading = loadingStories || loadingStory || loadingStrategies || loadingFrames || loadingBookmarks;

    /*
    One panel for each frame, including an empty rightmost panel whose selection
    triggers a request for a new frame. When the new rightmost panel contents
    arrive, a _new_ rightmost panel is made available for the same purpose.

    It is also always possible to scroll back through all prior frames of the
    story.
    */
    return <>
        {
            (selectedFrameNumber > 0) &&
            <div className="navLeft">
                <button
                    className="navButton"
                    onClick={() => {
                        backOne();
                    }}
                >
                    <IconChevronLeft/>
                </button>
            </div>
        }
        <div className="clio_app">
            { captureActive &&
                <PhotoCapture
                    sendPhoto={sendPhoto}
                    closePhotoCapture={closePhotoCapture}
                />
            }
            {
                !loading && !captureActive && !frames.length &&
                <div className="empty-story">
                    Start by creating a story...
                </div>
            }
        </div>
        <Carousel
            selectedIndex={Math.max(0, Math.min(selectedFrameNumber, frames.length - 1))}
            incrementSelectedIndex={aheadOne}
            decrementSelectedIndex={backOne}
        >
            {frames.map(renderFrame)}
        </Carousel>
        {
            (selectedFrameNumber < frames.length - 1) &&
            <div className="navRight">
                <button
                    className="navButton"
                    onClick={() => {
                        aheadOne();
                    }}
                >
                    <IconChevronRight/>
                </button>
            </div>
        }
        {
            <Toolbar
                toggleIsPlaying={toggleIsPlaying}
                isPlaying={isPlaying}
                isLoading={loading}
                isFullScreen={isFullScreen}
                toggleFullScreen={toggleFullScreen}
                startAudioCapture={startAudioCapture}
                startCameraCapture={startCameraCapture}
                addNewFrame={addNewFrame}
                allowExperimental={allowExperimental}
                strategies={strategies}
                strategy={strategy}
                startNewStory={startNewStory}
                stories={stories}
                story_id={storyId}
                setStory={updateStory}
                jumpToBeginning={toStart}
                jumpToEnd={toEnd}
                selectedFrameNumber={selectedFrameNumber}
                frames={frames}
                drawerIsOpen={drawerIsOpen}
                setDrawerIsOpen={setDrawerIsOpen}
                toggleBookmark={toggleBookmark}
                isCurrentFrameBookmarked={isCurrentFrameBookmarked()}
                bookmarks={bookmarks}
                showBookmarksList={showBookmarksList}
                setShowBookmarksList={setShowBookmarksList}
            />
        }
        {
            captureAudioActive &&
            <AudioCapture
              setIsOpen={setCaptureAudioActive}
              sendAudio={sendAudio}
            />
        }
        {
            loading && !drawerIsOpen && !showOverlays &&
            <div className="spinnerFrame">
                <Loader/>
            </div>
        }
    </>;
}
