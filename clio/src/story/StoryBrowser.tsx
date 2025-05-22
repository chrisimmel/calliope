import Button from '@mui/material/Button';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';

import IconClose from '../icons/IconClose';
import { resolveMediaUrl } from "../utils/media";
import { Story } from './storyTypes';


type StoryBrowserProps = {
    storyBrowserIsOpen: boolean,
    setStoryBrowserIsOpen: (open: boolean) => void,
    drawerAnchor: "bottom" | "right",
    stories: Story[],
    story_id: string | null,
    setStory: (story_id: string | null) => void,
}

export default function StoryBrowser({
    storyBrowserIsOpen,
    setStoryBrowserIsOpen,
    drawerAnchor,
    stories,
    story_id,
    setStory,
}: StoryBrowserProps) {
    const toggleStoryBrowser =
      (open: boolean) =>
      (event: React.KeyboardEvent | React.MouseEvent) => {
        if (
          event.type === 'keydown' &&
          ((event as React.KeyboardEvent).key === 'Tab' ||
            (event as React.KeyboardEvent).key === 'Shift')
        ) {
          return;
        }
  
        setStoryBrowserIsOpen(open);
      };

    return (
        <Drawer
            anchor={drawerAnchor}
            open={storyBrowserIsOpen}
            onClose={toggleStoryBrowser(false)}
        >
            <Button
                onClick={() => {
                    setStoryBrowserIsOpen(false);
                }}
                >
                <IconClose/>
            </Button>
            <List>
                {
                    stories.map(
                        (story, index) => {
                            if (story.story_id === story_id) {
                                return null;
                            }

                            const image_url = resolveMediaUrl(
                                (story.thumbnail_image && story.thumbnail_image.url) ? `/${story.thumbnail_image.url}` : ''
                            );

                            return <ListItem disablePadding key={story.story_id}>
                                <ListItemButton
                                    onClick={(e) => {
                                        setStoryBrowserIsOpen(false);
                                        setStory(story.story_id)
                                    }
                                }
                                >
                                    <ListItemIcon>
                                        {
                                            image_url &&
                                            <img src={image_url} width={48} height={48}/>
                                        }
                                    </ListItemIcon>
                                    <ListItemText primary={story.title} />
                                </ListItemButton>
                            </ListItem>
                        }
                    )
                }
            </List>
        </Drawer>
    );
}
