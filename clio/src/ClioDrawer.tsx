//import { css } from '@emotion/react'
import Box from '@mui/material/Box';
import CloseIcon from '@mui/icons-material/Close';
import IconButton from '@mui/material/IconButton';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';

import IconClose from './icons/IconClose';
import IconFastForward from './icons/IconFastForward';
import IconFullscreen from './icons/IconFullscreen';
import IconPause from './icons/IconPause';
import IconPlay from './icons/IconPlay';
import IconRewind from './icons/IconRewind';
import AboutPanel from './AboutPanel';
import StoryBrowser from './StoryBrowser';
import { Frame, Story, Strategy } from './Types';
import { useState } from 'react';
import CreateStoryDialog from './CreateStoryPanel';


type ClioDrawerProps = {
    drawerIsOpen: boolean,
    setDrawerIsOpen: (open: boolean) => void,
    allowExperimental: boolean
    strategies: Strategy[],
    strategy: string | null,
    startNewStory: (strategy: string | null) => void,
    startNewStoryWithPhoto: (strategy: string | null) => void,

    toggleIsPlaying: () => void,
    isPlaying: boolean,
    toggleFullScreen: () => void,
    stories: Story[],
    story_id: string | null,
    setStory: (story_id: string | null) => void,
    jumpToBeginning: () => void,
    jumpToEnd: () => void,
    selectedFrameNumber: number,
    frames: Frame[],
}


export default function ClioDrawer({
    allowExperimental,
    strategies,
    strategy,
    startNewStory,
    startNewStoryWithPhoto,
    isPlaying,
    toggleIsPlaying,
    toggleFullScreen,
    stories,
    story_id,
    setStory,
    jumpToBeginning,
    jumpToEnd,
    selectedFrameNumber,
    frames,
    drawerIsOpen,
    setDrawerIsOpen,
}: ClioDrawerProps) {
    const [storyBrowserIsOpen, setStoryBrowserIsOpen] = useState<boolean>(false);
    const [aboutPanelIsOpen, setAboutPanelIsOpen] = useState<boolean>(false);
    const [creatStoryDialogIsOpen, setCreatStoryDialogIsOpen] = useState<boolean>(false);
    const currentStory = stories.find(story => story.story_id === story_id) || null;
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

    /*
    Story
      <icon info> About
      <icon rw> Jump to Beginning
      <icon ff> Jump to End
      -----
      Browse
      Start New
    Other
      <icon fs> Fullscreen
      <icon play> Auto-Play (or Stop Auto-Play, w <icon pause>)
    */
   const drawerAnchor = document.documentElement.clientHeight > document.documentElement.clientWidth ? "bottom" : "right";

    return (
        <>
            <Drawer
                anchor={drawerAnchor}
                open={drawerIsOpen}
                onClose={toggleDrawer(false)}
            >
                <IconButton
                    aria-label="close"
                    onClick={() => {
                        setDrawerIsOpen(false);
                    }}
                    sx={{
                        position: 'absolute',
                        right: 8,
                        top: 8,
                        color: "gray",
                    }}
                >
                    <CloseIcon />
                </IconButton>
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
                                <ListItem disablePadding>
                                    <Divider/>
                                </ListItem>
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
                                        <ListItemText primary="Start New" />
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
                            </List>
                        </ListItem>
                    </List>
                </Box>
            </Drawer>
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
            <CreateStoryDialog
                isOpen={creatStoryDialogIsOpen}
                setIsOpen={setCreatStoryDialogIsOpen}
                allowExperimental={allowExperimental}
                strategies={strategies}
                strategy={strategy}
                startNewStory={startNewStory}
                startNewStoryWithPhoto={startNewStoryWithPhoto}
            />
        </>
    );
}
