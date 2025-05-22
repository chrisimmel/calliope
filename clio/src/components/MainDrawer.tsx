import { useState, useEffect } from 'react';

import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';

import AboutPanel from '../story/AboutPanel';
import CreateStoryPanel from '../story/CreateStoryPanel';
import { Bookmark, Frame, FrameSeedMediaType, Story, Strategy } from '../story/storyTypes';
import IconClose from '../icons/IconClose';
import IconFastForward from '../icons/IconFastForward';
import IconFullscreen from '../icons/IconFullscreen';
import IconPause from '../icons/IconPause';
import IconPlay from '../icons/IconPlay';
import IconRewind from '../icons/IconRewind';
import IconHeartEmpty from '../icons/IconHeartEmpty';
import IconServer from '../icons/IconServer';
import StoryBrowser from '../story/StoryBrowser';
import BookmarksList from '../story/BookmarksList';
import ServerSelector from './ServerSelector';
import { ServerConfig } from '../utils/serverConfig';
import apiService from '../services/ApiService';
import { isPlatform } from '../utils/platform';
import { isDevelopment } from '../utils/environment';


type MainDrawerProps = {
    drawerIsOpen: boolean,
    setDrawerIsOpen: (open: boolean) => void,
    allowExperimental: boolean
    strategies: Strategy[],
    strategy: string | null,
    startNewStory: (strategy: string | null, media_type: FrameSeedMediaType) => void,

    toggleIsPlaying: () => void,
    isPlaying: boolean,
    toggleFullScreen: () => void,
    stories: Story[],
    story_id: string | null,
    currentStory: Story | null, // Add currentStory prop
    setStory: (story_id: string | null, frame_number?: number) => void,
    jumpToBeginning: () => void,
    jumpToEnd: () => void,
    selectedFrameNumber: number,
    frames: Frame[],
    
    bookmarks: Bookmark[],
    showBookmarksList: boolean,
    setShowBookmarksList: (show: boolean) => void,
}


export default function MainDrawer({
    allowExperimental,
    strategies,
    strategy,
    startNewStory,
    isPlaying,
    toggleIsPlaying,
    toggleFullScreen,
    stories,
    story_id,
    currentStory,
    setStory,
    jumpToBeginning,
    jumpToEnd,
    selectedFrameNumber,
    frames,
    drawerIsOpen,
    setDrawerIsOpen,
    bookmarks,
    showBookmarksList,
    setShowBookmarksList,
}: MainDrawerProps) {
    const [storyBrowserIsOpen, setStoryBrowserIsOpen] = useState<boolean>(false);
    const [aboutPanelIsOpen, setAboutPanelIsOpen] = useState<boolean>(false);
    const [creatStoryDialogIsOpen, setCreatStoryDialogIsOpen] = useState<boolean>(false);
    // Ensure strategies is always an array even if undefined or null
    const validStrategies = Array.isArray(strategies) ? strategies : [];
    // Safe filtering that checks if strategies is an array first
    const filteredStrategies = validStrategies.filter((strat) => allowExperimental || !strat.is_experimental);
    // Safely find default strategy
    const defaultStrategy = filteredStrategies.find(s => s.is_default_for_client);
    const safeStrategy = strategy || (defaultStrategy ? defaultStrategy.slug : null);

    // Handle server change
    const handleServerChange = (serverConfig: ServerConfig) => {
        // Update the API service with the new server config
        apiService.updateServerConfig(serverConfig);
    };

    const toggleDrawer =
      (open: boolean) =>
      (event: React.KeyboardEvent | React.MouseEvent) => {
        if (
          event.type === 'keydown' &&
          ((event as React.KeyboardEvent).key === 'Tab' ||
            (event as React.KeyboardEvent).key === 'Shift')
        ) {
          return;
        }
  
        setDrawerIsOpen(open);
      };

    const drawerAnchor = "right";
    /*
    // Set up state for dynamic drawer position
    const [drawerAnchor, setDrawerAnchor] = useState<"right" | "bottom">("right");

    // Determine the best anchor position based on screen orientation and platform
    const updateDrawerAnchor = () => {
        const isPortrait = window.innerHeight > window.innerWidth;
        const isMobile = isPlatform.capacitor();
        // Use bottom drawer in portrait orientation on mobile, right drawer otherwise
        setDrawerAnchor((isMobile && isPortrait) ? "bottom" : "right");
    };

    // Initialize anchor position and update on resize
    useEffect(() => {
        // Set initial anchor position
        updateDrawerAnchor();

        // Update on window resize or orientation change
        window.addEventListener('resize', updateDrawerAnchor);
        window.addEventListener('orientationchange', updateDrawerAnchor);

        return () => {
            // Clean up event listeners
            window.removeEventListener('resize', updateDrawerAnchor);
            window.removeEventListener('orientationchange', updateDrawerAnchor);
        };
    }, []);
    */
    return (
        <>
            <Drawer
                anchor={drawerAnchor}
                open={drawerIsOpen}
                onClose={toggleDrawer(false)}
            >
                <Box sx={{ my: 6 }} >
                    <List>
                        <ListItem disablePadding>
                            <Divider/>
                            <ListItemText primary="Story" />
                            <List>
                                <ListItem disablePadding>
                                    <ListItemButton
                                        onClick={(e) => {
                                            setDrawerIsOpen(false);
                                            setAboutPanelIsOpen(true);
                                        }
                                    }
                                    >
                                        <ListItemIcon>
                                        </ListItemIcon>
                                        <ListItemText primary="About" />
                                    </ListItemButton>
                                </ListItem>
                                {
                                    frames.length > 2 && selectedFrameNumber > 0 &&
                                    <ListItem disablePadding>
                                        <ListItemButton
                                            onClick={(e) => {
                                                setDrawerIsOpen(false);
                                                jumpToBeginning()
                                            }
                                        }
                                        >
                                            <ListItemIcon>
                                                <IconRewind />
                                            </ListItemIcon>
                                            <ListItemText primary="Jump to Beginning" />
                                        </ListItemButton>
                                    </ListItem>
                                }
                                {
                                    frames.length > 2 && selectedFrameNumber < frames.length - 1 &&
                                    <ListItem disablePadding>
                                        <ListItemButton
                                            onClick={(e) => {
                                                setDrawerIsOpen(false);
                                                jumpToEnd()
                                            }
                                        }
                                        >
                                            <ListItemIcon>
                                                <IconFastForward />
                                            </ListItemIcon>
                                            <ListItemText primary="Jump to End" />
                                        </ListItemButton>
                                    </ListItem>
                                }
                                <ListItem disablePadding>
                                    <Divider/>
                                </ListItem>
                                {
                                    stories.length > 1 &&
                                    <ListItem disablePadding>
                                        <ListItemButton
                                            onClick={(e) => {
                                                setDrawerIsOpen(false);
                                                setStoryBrowserIsOpen(true)
                                            }
                                        }
                                        >
                                            <ListItemIcon>
                                            </ListItemIcon>
                                            <ListItemText primary="Browse" />
                                        </ListItemButton>
                                    </ListItem>
                                }
                                <ListItem disablePadding>
                                    <ListItemButton
                                        onClick={(e) => {
                                            setDrawerIsOpen(false);
                                            setCreatStoryDialogIsOpen(true)
                                        }
                                    }
                                    >
                                        <ListItemIcon>
                                        </ListItemIcon>
                                        <ListItemText primary="Create New" />
                                    </ListItemButton>
                                </ListItem>
                                <ListItem disablePadding>
                                    <ListItemButton
                                        onClick={(e) => {
                                            setDrawerIsOpen(false);
                                            setShowBookmarksList(true)
                                        }
                                    }
                                    >
                                        <ListItemIcon>
                                            <IconHeartEmpty />
                                        </ListItemIcon>
                                        <ListItemText primary="Bookmarks" />
                                    </ListItemButton>
                                </ListItem>
                            </List>
                        </ListItem>
                        <ListItem disablePadding>
                            <Divider/>
                            <ListItemText primary="Settings" />
                            <List>
                                <ListItem disablePadding>
                                    <ListItemButton
                                        onClick={(e) => {
                                            setDrawerIsOpen(false);
                                            toggleFullScreen()
                                        }
                                    }
                                    >
                                        <ListItemIcon>
                                            <IconFullscreen />
                                        </ListItemIcon>
                                        <ListItemText primary="Fullscreen" />
                                    </ListItemButton>
                                </ListItem>
                                {/* Show server selector only in development environment */}
                                {isDevelopment() && (
                                    <ListItem sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                                        <ListItemText 
                                            primary="Server" 
                                            secondary="Select which server to connect to"
                                            sx={{ mb: 1 }}
                                        />
                                        <ServerSelector onServerChange={handleServerChange} />
                                    </ListItem>
                                )}
                                {/* Disable auto-play option.
                                 <ListItem disablePadding>
                                    <ListItemButton
                                        onClick={(e) => {
                                            setDrawerIsOpen(false);
                                            toggleIsPlaying()
                                        }
                                    }
                                    >
                                        <ListItemIcon>
                                            {isPlaying ? <IconPause/> : <IconPlay/>}                                    
                                        </ListItemIcon>
                                        <ListItemText primary={isPlaying ? "Stop Auto-Play" : "Auto-Play"} />
                                    </ListItemButton>
                                </ListItem>
                                */}
                            </List>
                        </ListItem>
                    </List>
                </Box>
            </Drawer>
            {
                drawerIsOpen &&
                <button
                    className="navButton menuButton drawerOpen"
                    onClick={() => {
                        setDrawerIsOpen(false);
                    }}
                >
                    <IconClose/>
                </button>
            }
            <StoryBrowser
                storyBrowserIsOpen={storyBrowserIsOpen}
                setStoryBrowserIsOpen={setStoryBrowserIsOpen}
                drawerAnchor={drawerAnchor}
                stories={stories}
                story_id={story_id}
                setStory={setStory}
            />
            <AboutPanel
                aboutPanelIsOpen={aboutPanelIsOpen}
                setAboutPanelIsOpen={setAboutPanelIsOpen}
                drawerAnchor={drawerAnchor}
                story={currentStory}
                selectedFrameNumber={selectedFrameNumber}
                frames={frames}
            />
            <CreateStoryPanel
                isOpen={creatStoryDialogIsOpen}
                setIsOpen={setCreatStoryDialogIsOpen}
                allowExperimental={allowExperimental}
                strategies={validStrategies}
                strategy={safeStrategy}
                startNewStory={startNewStory}
            />
            <BookmarksList
                bookmarksListIsOpen={showBookmarksList}
                setBookmarksListIsOpen={setShowBookmarksList}
                drawerAnchor={drawerAnchor}
                stories={stories}
                story_id={story_id}
                setStory={setStory}
                bookmarks={bookmarks}
            />
        </>
    );
}
