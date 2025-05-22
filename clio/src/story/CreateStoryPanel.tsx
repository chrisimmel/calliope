import * as React from 'react';
import { useState } from 'react';

import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CloseIcon from '@mui/icons-material/Close';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Drawer from '@mui/material/Drawer';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormLabel from '@mui/material/FormLabel';
import IconButton from '@mui/material/IconButton';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import Typography from '@mui/material/Typography';
import { styled } from '@mui/material/styles';

import { FrameSeedMediaType, Strategy } from './storyTypes';


const BootstrapDialog = styled(Dialog)(({ theme }) => ({
  '& .MuiDialogContent-root': {
    padding: theme.spacing(2),
  },
  '& .MuiDialogActions-root': {
    padding: theme.spacing(1),
  },
}));

type CreateStoryPanelProps = {
    isOpen: boolean,
    setIsOpen: (open: boolean) => void,

    allowExperimental: boolean
    strategies: Strategy[],
    strategy: string | null,
    startNewStory: (strategy: string | null, media_type: FrameSeedMediaType) => void,
}

export default function CreateStoryPanel({
    isOpen,
    setIsOpen,
    allowExperimental,
    strategies,
    strategy,
    startNewStory,
}: CreateStoryPanelProps) {
  // Ensure strategies is always a valid array
  const validStrategies = Array.isArray(strategies) ? strategies : [];
  
  // Safe filtering of strategies
  const filteredStrategies = validStrategies.filter((strat) => allowExperimental || !strat.is_experimental);
  
  // Safely determine initial strategy
  const defaultStrategy = filteredStrategies.find(s => s.is_default_for_client);
  const safeStrategy = strategy || (defaultStrategy ? defaultStrategy.slug : null) || null;
  const [newStrategy, setNewStrategy] = useState(safeStrategy);
  const [media, setMedia] = useState<FrameSeedMediaType>("photo");

  const handleClose = () => {
    setIsOpen(false);
  };
  const handleStartStory = () => {
    setIsOpen(false);
    startNewStory(newStrategy, media);
  };
  const handleChangeStrategy = (event: SelectChangeEvent) => {
    setNewStrategy(event.target.value);
  };
  const handleChangeMedia = (event: React.ChangeEvent<HTMLInputElement>, value: string) => {
    setMedia(value as FrameSeedMediaType);
  };

  return (
    <React.Fragment>
      <Drawer
          anchor={"right"}
          open={isOpen}
          onClose={handleClose}
          className="create-story-panel"
          PaperProps={{
            sx: {
              width: 350,
             },
          }}
      >
        <Box sx={{ 
              display: 'flex',
              alignItems: 'center',
              bgcolor: '#f5f5f5', 
              borderRadius: '4px',
              padding: '6px 12px',
              marginBottom: '10px',
          }}>
            <Typography variant="subtitle1" style={{fontSize: "1.2rem"}}>Create a New Story</Typography>
        </Box>
        <IconButton
            aria-label="close"
            onClick={handleClose}
            sx={{
                position: 'absolute',
                zIndex: 1000,
                top: 16,
                right: 12,
                color: "#aaa",
            }}
        >
            <CloseIcon />
        </IconButton>
        <DialogContent dividers>
          <FormControl fullWidth>
            <InputLabel id="strategy-select-label">By Storyteller</InputLabel>
            <Select
              labelId="strategy-select-label"
              id="strategy-select"
              value={newStrategy || undefined}
              label="By Storyteller"
              onChange={handleChangeStrategy}
            >
              {
                filteredStrategies.map(
                  (strat, index) => {
                      return <MenuItem key={strat.slug} value={strat.slug}>{strat.slug}</MenuItem>
                  }
                )
              }
            </Select>
          </FormControl>
          {/*<FormGroup>
            <FormControlLabel control={<Checkbox defaultChecked={sendPhoto} onChange={handleChangeSendPhoto} />} label="Send a Photo" />
          </FormGroup>
          */}
        <FormControl>
          <FormLabel id="demo-radio-buttons-group-label" style={{marginTop: "16px"}}>Begin Story From</FormLabel>
          <RadioGroup
            aria-labelledby="demo-radio-buttons-group-label"
            value={media}
            onChange={handleChangeMedia}
            name="radio-buttons-group"
          >
            <FormControlLabel value="photo" control={<Radio />} label="A Photo" />
            <FormControlLabel value="audio" control={<Radio />} label="Spoken Words" />
            <FormControlLabel value="none" control={<Radio />} label="Thin Air" />
          </RadioGroup>
        </FormControl>
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={handleClose}>
            Cancel
          </Button>
          <Button autoFocus variant="contained" onClick={handleStartStory}>
            Begin Story
          </Button>
        </DialogActions>
      </Drawer>
    </React.Fragment>
  );
}
