import { useState } from 'react';

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
import StoryBrowser from '../story/StoryBrowser';
import BookmarksList from '../story/BookmarksList';


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
    strategies ||= [];
    strategies = strategies.filter((strat) => allowExperimental || !strat.is_experimental);
    strategy ||= (strategies.find(strategy => strategy.is_default_for_client) || {slug: null}).slug;
    strategy ||= null;

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

    //const drawerAnchor = document.documentElement.clientHeight > document.documentElement.clientWidth ? "bottom" : "right";
    const drawerAnchor = "right";
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
                            <ListItemText primary="Other" />
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
                strategies={strategies}
                strategy={strategy}
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
