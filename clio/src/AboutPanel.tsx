import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Icon from '@mui/material/Icon';
import CloseIcon from '@mui/icons-material/Close';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Link from '@mui/material/Link';

import Drawer from '@mui/material/Drawer';

import { Frame, Story } from './Types';
import { IconButton } from '@mui/material';
import { Fragment } from 'react';

function Copyright() {
  return (
    <Typography variant="body2" color="text.secondary" align="center">
      {'Calliope and Clio copyright © '}
      <Link color="inherit" href="https://chrisimmel.com/">
        Chris Immel
      </Link>{' '}
      2022-{new Date().getFullYear()}
    </Typography>
  );
}


type AboutPanelProps = {
    aboutPanelIsOpen: boolean,
    setAboutPanelIsOpen: (open: boolean) => void,
    drawerAnchor: "bottom" | "right",
    story: Story | null,
    selectedFrameNumber: number,
    frames: Frame[],
}

export default function AboutPanel({
    aboutPanelIsOpen,
    setAboutPanelIsOpen,
    drawerAnchor,
    story,
    selectedFrameNumber,
    frames,
}: AboutPanelProps) {
    const toggleAboutPanel =
      (open: boolean) =>
      (event: React.KeyboardEvent | React.MouseEvent) => {
        if (
          event.type === 'keydown' &&
          ((event as React.KeyboardEvent).key === 'Tab' ||
            (event as React.KeyboardEvent).key === 'Shift')
        ) {
          return;
        }
  
        setAboutPanelIsOpen(open);
      };

    const image_url = (story && story.thumbnail_image && story.thumbnail_image.url) ? `/${story.thumbnail_image.url}` : '';
    const situation = (frames && frames[0]) ? (frames[0].metadata?.situation || "") : "";
    const locationAndTail = situation.startsWith("Location\n") ? situation.slice("Location\n".length) : null;
    const endLocationIndex = locationAndTail?.indexOf("\n\n") || locationAndTail?.length;
    const location = locationAndTail?.slice(0, endLocationIndex);

    return (
        <Drawer
            anchor={drawerAnchor}
            open={aboutPanelIsOpen}
            onClose={toggleAboutPanel(false)}
        >
            <IconButton
                aria-label="close"
                onClick={() => {
                    setAboutPanelIsOpen(false);
                }}
                sx={{
                    position: 'absolute',
                    right: 8,
                    top: 8,
                    color: "#aaa",
                }}
            >
                <CloseIcon />
            </IconButton>
            <Container maxWidth="sm">
            {
                story &&
                <Box sx={{ my: 4 }} >
                    <Typography variant="h6" sx={{ mb: 2 }}>
                        {
                            image_url &&
                            <img src={image_url} width={64} height={64}/>
                        }
                        &nbsp;&nbsp;
                        {story.title}
                    </Typography>
                    <Typography variant="subtitle1">
                        Story created on {story.date_created} by storyteller {story.strategy_name}
                    </Typography>
                    {
                        location &&
                        <Typography variant="subtitle1">
                            in {location}.
                        </Typography>
                    }
                </Box>
            }
            {
                story &&
                <Box sx={{ my: 4 }} >
                    <Typography variant="subtitle1">
                        Last updated {story.date_updated}.
                    </Typography>
                    <Typography variant="subtitle1">
                        Viewing frame {selectedFrameNumber + 1} of {frames.length}.
                    </Typography>
                </Box>
            }
            <Box sx={{ my: 4 }}>
                <Copyright />
            </Box>
            </Container>
        </Drawer>
    );
}
