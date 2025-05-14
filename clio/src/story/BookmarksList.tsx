import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Drawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Collapse from '@mui/material/Collapse';

import IconClose from '../icons/IconClose';
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
    
    const handleBookmarkClick = (storyId: string, frameNumber: number) => {
        setBookmarksListIsOpen(false);
        
        // Find the story slug from the story ID
        const story = stories.find(s => s.story_id === storyId);
        if (story && story.slug) {
            // Frame numbers in URL are 1-based
            const frameForUrl = frameNumber + 1;
            
            // Navigate to the story/frame using the new URL pattern
            navigate(`/clio/story/${story.slug}/${frameForUrl}`);
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
            >
                <Box sx={{ my: 6 }}>
                    <List>
                        <ListItem>
                            <ListItemText primary="Bookmarks" sx={{ fontWeight: 'bold' }} />
                        </ListItem>
                        
                        {Object.keys(bookmarksByStory).length === 0 && (
                            <ListItem>
                                <ListItemText primary="No bookmarks yet" />
                            </ListItem>
                        )}

                        {Object.keys(bookmarksByStory).map(storyId => (
                            <div key={storyId}>
                                <ListItem disablePadding>
                                    <ListItemButton onClick={() => toggleStoryExpanded(storyId)}>
                                        <ListItemText 
                                            primary={getStoryTitle(storyId)} 
                                            secondary={`${bookmarksByStory[storyId].length} bookmarks`}
                                        />
                                    </ListItemButton>
                                </ListItem>

                                <Collapse in={expandedStories[storyId]} timeout="auto" unmountOnExit>
                                    <List component="div" disablePadding>
                                        {bookmarksByStory[storyId].map(bookmark => (
                                            <ListItem key={bookmark.id} disablePadding>
                                                <ListItemButton 
                                                    sx={{ pl: 4 }}
                                                    onClick={() => handleBookmarkClick(bookmark.story_id, bookmark.frame_number)}
                                                >
                                                    <ListItemText 
                                                        primary={`Frame ${bookmark.frame_number + 1}`} 
                                                        secondary={bookmark.comments || 'No comments'}
                                                    />
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
