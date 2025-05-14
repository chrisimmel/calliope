import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Drawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Collapse from '@mui/material/Collapse';
import Typography from '@mui/material/Typography';

import IconClose from '../icons/IconClose';
import IconHeartFull from '../icons/IconHeartFull';
import IconChevronDown from '../icons/IconChevronDown';
import IconChevronRight from '../icons/IconChevronRight';
import { Bookmark, Story } from './storyTypes';

type BookmarksListProps = {
    bookmarksListIsOpen: boolean,
    setBookmarksListIsOpen: (open: boolean) => void,
    drawerAnchor: "left" | "right" | "top" | "bottom",
    stories: Story[],
    story_id: string | null,
    setStory: (story_id: string | null, frame_number?: number) => void,
    bookmarks: Bookmark[],
};

type BookmarksByStory = {
    [key: string]: Bookmark[];
};

export default function BookmarksList({
    bookmarksListIsOpen,
    setBookmarksListIsOpen,
    drawerAnchor,
    stories,
    story_id,
    setStory,
    bookmarks,
}: BookmarksListProps) {
    const [bookmarksByStory, setBookmarksByStory] = useState<BookmarksByStory>({});
    const [expandedStories, setExpandedStories] = useState<{[key: string]: boolean}>({});

    // Group bookmarks by story
    useEffect(() => {
        const grouped: BookmarksByStory = {};

        bookmarks.forEach(bookmark => {
            if (!grouped[bookmark.story_id]) {
                grouped[bookmark.story_id] = [];
            }
            grouped[bookmark.story_id].push(bookmark);
        });

        // Sort bookmarks within each story by frame number
        Object.keys(grouped).forEach(storyId => {
            grouped[storyId].sort((a, b) => a.frame_number - b.frame_number);
        });

        setBookmarksByStory(grouped);

        // Initialize expanded state for each story
        const initialExpandedState: {[key: string]: boolean} = {};
        Object.keys(grouped).forEach(storyId => {
            initialExpandedState[storyId] = storyId === story_id;
        });
        setExpandedStories(initialExpandedState);
    }, [bookmarks, story_id]);

    const getStoryTitle = (storyId: string): string => {
        const story = stories.find(s => s.story_id === storyId);
        return story ? story.title : `Story ${storyId}`;
    };

    const toggleStoryExpanded = (storyId: string) => {
        setExpandedStories({
            ...expandedStories,
            [storyId]: !expandedStories[storyId]
        });
    };

    const navigate = useNavigate();
    
    // Utility function to preserve query parameters
    const preserveQueryParams = (url: string): string => {
        const currentParams = new URLSearchParams(window.location.search);
        
        // If there are no query parameters, return the original URL
        if (!currentParams.toString()) {
            return url;
        }
        
        // Check if the URL already has query parameters
        const hasQuery = url.includes('?');
        const separator = hasQuery ? '&' : '?';
        
        // Append the current query parameters to the URL
        return `${url}${separator}${currentParams.toString()}`;
    };
    
    const handleBookmarkClick = (storyId: string, frameNumber: number) => {
        setBookmarksListIsOpen(false);
        
        // Find the story slug from the story ID
        const story = stories.find(s => s.story_id === storyId);
        if (story && story.slug) {
            // Frame numbers in URL are 1-based
            const frameForUrl = frameNumber + 1;
            
            // Create base URL
            const baseUrl = `/clio/story/${story.slug}/${frameForUrl}`;
            
            // Preserve query parameters
            const urlWithParams = preserveQueryParams(baseUrl);
            
            // Navigate to the story/frame using the new URL pattern
            navigate(urlWithParams);
        } else {
            // Fallback to the setStory function if we can't find a slug
            setStory(storyId, frameNumber);
        }
    };

    return (
        <>
            <Drawer
                anchor={drawerAnchor}
                open={bookmarksListIsOpen}
                onClose={() => setBookmarksListIsOpen(false)}
                PaperProps={{
                    sx: {
                        width: {
                            xs: '100%',
                            sm: '400px',
                            md: '450px'
                        }
                    }
                }}
            >
                <Box sx={{ my: 2 }}>
                    <List dense sx={{ padding: 0 }}>
                        <ListItem 
                            sx={{ 
                                backgroundColor: '#f5f5f5', 
                                borderRadius: '4px',
                                marginBottom: '4px',
                                padding: '6px 12px'
                            }}
                            dense
                        >
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                <IconHeartFull style={{ color: '#ff4081', width: '20px', height: '20px' }} />
                                <Typography variant="subtitle1" fontWeight="bold" style={{ marginLeft: '10px'}}>Bookmarks</Typography>
                            </Box>
                        </ListItem>

                        {Object.keys(bookmarksByStory).length === 0 && (
                            <ListItem dense sx={{ py: 0 }}>
                                <Typography variant="body2">No bookmarks yet</Typography>
                            </ListItem>
                        )}

                        {Object.keys(bookmarksByStory).map(storyId => (
                            <div key={storyId}>
                                <ListItem disablePadding>
                                    <ListItemButton 
                                        onClick={() => toggleStoryExpanded(storyId)}
                                        sx={{ 
                                            backgroundColor: '#f9f9f9', 
                                            '&:hover': { 
                                                backgroundColor: '#f0f0f0',
                                                '& svg': { color: '#444' },
                                                boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                                            },
                                            marginY: '2px',
                                            borderRadius: '4px',
                                            cursor: 'pointer',
                                            transition: 'all 0.2s ease',
                                            boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                                            padding: '4px 8px'
                                        }}
                                    >
                                        <Box sx={{ 
                                            display: 'flex', 
                                            width: '100%', 
                                            alignItems: 'center' 
                                        }}>
                                            <ListItemText 
                                                primary={getStoryTitle(storyId)}
                                                secondary={`${bookmarksByStory[storyId].length} bookmarks`}
                                                primaryTypographyProps={{
                                                    fontWeight: 'medium',
                                                    color: '#333',
                                                    variant: 'body1'
                                                }}
                                                secondaryTypographyProps={{
                                                    variant: 'caption',
                                                    color: '#666'
                                                }}
                                                sx={{ flex: 1, margin: 0 }}
                                            />
                                            <Box
                                                sx={{
                                                    display: 'flex',
                                                    transition: 'transform 0.3s ease',
                                                    transform: expandedStories[storyId] ? 'rotate(0deg)' : 'rotate(-90deg)'
                                                }}
                                            >
                                                <IconChevronDown style={{ color: '#666', width: '24px', height: '24px' }} />
                                            </Box>
                                        </Box>
                                    </ListItemButton>
                                </ListItem>

                                <Collapse in={expandedStories[storyId]} timeout="auto" unmountOnExit>
                                    <List component="div" disablePadding>
                                        {bookmarksByStory[storyId].map(bookmark => (
                                            <ListItem key={bookmark.id} disablePadding>
                                                <ListItemButton 
                                                    sx={{ 
                                                        pl: 4,
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        '&:hover': { 
                                                            backgroundColor: 'rgba(0,0,0,0.04)',
                                                            borderRadius: '4px'
                                                        },
                                                        margin: '1px 0',
                                                        padding: '2px 8px'
                                                    }}
                                                    onClick={() => handleBookmarkClick(bookmark.story_id, bookmark.frame_number)}
                                                >
                                                    <Box sx={{ 
                                                        display: 'flex', 
                                                        width: '100%',
                                                        alignItems: 'center',
                                                        margin: '0 14px'
                                                    }}>
                                                        {bookmark.frame_image_url && (
                                                            <Box sx={{ 
                                                                mr: 2,
                                                                width: '48px',
                                                                height: '48px',
                                                                overflow: 'hidden',
                                                                borderRadius: '4px',
                                                                flexShrink: 0,
                                                                display: 'flex',
                                                                justifyContent: 'center',
                                                                alignItems: 'center'
                                                            }}>
                                                                <img 
                                                                    src={bookmark.frame_image_url} 
                                                                    alt={`Frame ${bookmark.frame_number + 1}`}
                                                                    style={{ 
                                                                        width: '100%',
                                                                        height: '100%',
                                                                        objectFit: 'cover'
                                                                    }}
                                                                />
                                                            </Box>
                                                        )}
                                                        <Box sx={{ flexGrow: 1, margin: 0}}>
                                                            <Box sx={{ display: 'flex', margin: 0 }}>
                                                                <Typography 
                                                                    component="span" 
                                                                    variant="body2" 
                                                                    color="#333"
                                                                    sx={{ mr: 0.5, flexShrink: 0 }}
                                                                >
                                                                    {bookmark.frame_number + 1}:
                                                                </Typography>
                                                                <Typography 
                                                                    variant="caption"
                                                                    color="#666"
                                                                    sx={{
                                                                        fontStyle: 'italic',
                                                                        maxHeight: '3.6em', // approximately 3 lines
                                                                        overflow: 'hidden',
                                                                        textOverflow: 'ellipsis',
                                                                        display: '-webkit-box',
                                                                        WebkitLineClamp: 2,
                                                                        WebkitBoxOrient: 'vertical',
                                                                    }}
                                                                >
                                                                    {bookmark.frame_text || '(No text)'}
                                                                </Typography>
                                                            </Box>
                                                        </Box>
                                                    </Box>
                                                </ListItemButton>
                                            </ListItem>
                                        ))}
                                    </List>
                                </Collapse>
                            </div>
                        ))}
                    </List>
                </Box>
            </Drawer>

            {bookmarksListIsOpen && (
                <button
                    className="navButton menuButton drawerOpen"
                    onClick={() => setBookmarksListIsOpen(false)}
                >
                    <IconClose />
                </button>
            )}
        </>
    );
}
