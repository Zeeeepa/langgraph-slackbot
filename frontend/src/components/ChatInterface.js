import React, { useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  IconButton,
  CircularProgress,
  Paper,
  Divider,
  Avatar,
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  Person as PersonIcon,
  SmartToy as SmartToyIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';

const ChatInterface = ({
  chatHistory,
  message,
  onMessageChange,
  onSendMessage,
  isSending,
  file,
  onFileChange,
  onFileUpload,
}) => {
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Scroll to bottom when chat history changes
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSendMessage();
    }
  };

  const handleFileButtonClick = () => {
    fileInputRef.current.click();
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '500px' }}>
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          mb: 2,
          p: 2,
          backgroundColor: '#f5f5f5',
          borderRadius: 1,
        }}
      >
        {chatHistory.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'text.secondary',
            }}
          >
            <SmartToyIcon sx={{ fontSize: 48, mb: 2 }} />
            <Typography variant="body1">
              Start a conversation with the AI assistant to get help with your project.
            </Typography>
          </Box>
        ) : (
          chatHistory.map((msg, index) => (
            <Box
              key={index}
              sx={{
                display: 'flex',
                mb: 2,
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              }}
            >
              <Avatar
                sx={{
                  bgcolor: msg.role === 'user' ? 'primary.main' : msg.role === 'system' ? 'grey.500' : 'secondary.main',
                  mr: msg.role === 'user' ? 0 : 1,
                  ml: msg.role === 'user' ? 1 : 0,
                }}
              >
                {msg.role === 'user' ? (
                  <PersonIcon />
                ) : msg.role === 'system' ? (
                  <InfoIcon />
                ) : (
                  <SmartToyIcon />
                )}
              </Avatar>
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  maxWidth: '70%',
                  borderRadius: 2,
                  backgroundColor:
                    msg.role === 'user'
                      ? 'primary.light'
                      : msg.role === 'system'
                      ? 'grey.100'
                      : 'secondary.light',
                  color:
                    msg.role === 'user' || msg.role === 'assistant'
                      ? 'white'
                      : 'text.primary',
                }}
              >
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </Paper>
            </Box>
          ))
        )}
        <div ref={chatEndRef} />
      </Box>

      <Divider sx={{ mb: 2 }} />

      <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
        <TextField
          fullWidth
          multiline
          rows={3}
          variant="outlined"
          placeholder="Type your message here..."
          value={message}
          onChange={onMessageChange}
          onKeyPress={handleKeyPress}
          disabled={isSending}
          sx={{ mr: 1 }}
        />
        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
          <input
            type="file"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={onFileChange}
          />
          <IconButton
            color="primary"
            onClick={handleFileButtonClick}
            disabled={isSending}
            sx={{ mb: 1 }}
          >
            <AttachFileIcon />
          </IconButton>
          <Button
            variant="contained"
            color="primary"
            endIcon={isSending ? <CircularProgress size={20} /> : <SendIcon />}
            onClick={file ? onFileUpload : onSendMessage}
            disabled={isSending || (!message.trim() && !file)}
          >
            {file ? 'Upload' : 'Send'}
          </Button>
        </Box>
      </Box>

      {file && (
        <Box sx={{ mt: 1, display: 'flex', alignItems: 'center' }}>
          <AttachFileIcon fontSize="small" sx={{ mr: 1 }} />
          <Typography variant="body2">{file.name}</Typography>
          <IconButton
            size="small"
            onClick={() => onFileChange({ target: { files: [] } })}
          >
            &times;
          </IconButton>
        </Box>
      )}
    </Box>
  );
};

export default ChatInterface;
