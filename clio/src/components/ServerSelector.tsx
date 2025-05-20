import { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconServer from '../icons/IconServer';

import { SERVER_CONFIGS, ServerConfig, getSelectedServerConfig, saveServerChoice } from '../utils/serverConfig';

interface ServerSelectorProps {
  onServerChange?: (serverConfig: ServerConfig) => void;
}

export default function ServerSelector({ onServerChange }: ServerSelectorProps) {
  const [selectedServer, setSelectedServer] = useState<string>(getSelectedServerConfig().id);
  const [isDialogOpen, setIsDialogOpen] = useState<boolean>(false);
  const [customServerUrl, setCustomServerUrl] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Reset error message when dialog opens
  useEffect(() => {
    if (isDialogOpen) {
      setErrorMessage('');
    }
  }, [isDialogOpen]);

  const handleChange = (event: SelectChangeEvent) => {
    const serverId = event.target.value;
    setSelectedServer(serverId);
    
    // If "custom" is selected, open the dialog
    if (serverId === 'custom') {
      setIsDialogOpen(true);
      return;
    }

    // Save the server choice
    saveServerChoice(serverId);

    // Find the selected server config
    const serverConfig = SERVER_CONFIGS.find(config => config.id === serverId);
    
    // Notify parent component
    if (serverConfig && onServerChange) {
      onServerChange(serverConfig);
    }
  };

  const handleSaveCustomServer = () => {
    // Basic validation for URL format
    if (!customServerUrl) {
      setErrorMessage('Please enter a server URL');
      return;
    }

    if (!customServerUrl.startsWith('http://') && !customServerUrl.startsWith('https://')) {
      setErrorMessage('URL must start with http:// or https://');
      return;
    }

    // Save the custom server to localStorage
    const customConfig: ServerConfig = {
      id: 'custom',
      name: 'Custom Server',
      url: customServerUrl,
      description: 'Custom server configuration'
    };

    // Add/update the custom server in the config
    SERVER_CONFIGS.forEach((config, index) => {
      if (config.id === 'custom') {
        SERVER_CONFIGS[index] = customConfig;
      }
    });

    // If custom wasn't found, add it
    if (!SERVER_CONFIGS.find(config => config.id === 'custom')) {
      SERVER_CONFIGS.push(customConfig);
    }

    // Save the choice
    saveServerChoice('custom');

    // Notify parent component
    if (onServerChange) {
      onServerChange(customConfig);
    }

    // Close the dialog
    setIsDialogOpen(false);
  };

  return (
    <Box sx={{ minWidth: 120, maxWidth: 300, margin: '8px 0' }}>
      <FormControl fullWidth size="small">
        <InputLabel id="server-select-label">Server</InputLabel>
        <Select
          labelId="server-select-label"
          id="server-select"
          value={selectedServer}
          label="Server"
          onChange={handleChange}
          startAdornment={<IconServer style={{ marginRight: 8 }} />}
        >
          {SERVER_CONFIGS.map((config) => (
            <MenuItem key={config.id} value={config.id}>
              {config.name}
            </MenuItem>
          ))}
          <MenuItem value="custom">Custom Server</MenuItem>
        </Select>
      </FormControl>

      <Dialog open={isDialogOpen} onClose={() => setIsDialogOpen(false)}>
        <DialogTitle>Custom Server Configuration</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            id="server-url"
            label="Server URL"
            type="url"
            fullWidth
            variant="outlined"
            value={customServerUrl}
            onChange={(e) => setCustomServerUrl(e.target.value)}
            placeholder="https://example.com"
            error={!!errorMessage}
            helperText={errorMessage}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveCustomServer} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}