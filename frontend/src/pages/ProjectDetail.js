import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Button,
  CircularProgress,
  Divider,
  TextField,
  IconButton,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  GitHub as GitHubIcon,
  Slack as SlackIcon,
  Settings as SettingsIcon,
  PlayArrow as PlayArrowIcon,
} from '@mui/icons-material';
import { useProjects } from '../context/ProjectContext';
import { analyzeProject, updateTaskStatus } from '../api/projects';
import { sendChatMessage, uploadFile } from '../api/chat';
import ImplementationTree from '../components/ImplementationTree';
import ChatInterface from '../components/ChatInterface';
import ProjectContext from '../components/ProjectContext';

const ProjectDetail = () => {
  const { projectId } = useParams();
  const { loadProject, currentProject, loading, error } = useProjects();
  const [tabValue, setTabValue] = useState(0);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [file, setFile] = useState(null);

  useEffect(() => {
    if (projectId) {
      loadProject(projectId);
    }
  }, [projectId, loadProject]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleChatMessageChange = (e) => {
    setChatMessage(e.target.value);
  };

  const handleSendMessage = async () => {
    if (!chatMessage.trim()) return;

    setIsSending(true);
    try {
      const newMessage = { role: 'user', content: chatMessage };
      const updatedHistory = [...chatHistory, newMessage];
      setChatHistory(updatedHistory);
      setChatMessage('');

      const response = await sendChatMessage(
        chatMessage,
        projectId,
        updatedHistory
      );

      setChatHistory([...updatedHistory, { role: 'assistant', content: response.response }]);
    } catch (err) {
      console.error('Error sending message:', err);
    } finally {
      setIsSending(false);
    }
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleFileUpload = async () => {
    if (!file) return;

    setIsSending(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('project_id', projectId);
      formData.append('message', chatMessage || 'Please analyze this file.');

      const response = await uploadFile(formData);
      setChatHistory([
        ...chatHistory,
        { role: 'system', content: `File uploaded: ${file.name}` },
        { role: 'user', content: chatMessage || 'Please analyze this file.' },
        { role: 'assistant', content: response.response },
      ]);
      setChatMessage('');
      setFile(null);
    } catch (err) {
      console.error('Error uploading file:', err);
    } finally {
      setIsSending(false);
    }
  };

  const handleAnalyzeProject = async () => {
    setIsAnalyzing(true);
    try {
      const result = await analyzeProject(projectId);
      // Update the project with the analysis results
      loadProject(projectId);
      setChatHistory([
        ...chatHistory,
        { role: 'system', content: 'Project analysis completed.' },
        { role: 'assistant', content: 'I\'ve analyzed the project and created an implementation plan. You can view it in the Implementation tab.' },
      ]);
    } catch (err) {
      console.error('Error analyzing project:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleTaskStatusChange = async (taskId, status) => {
    try {
      await updateTaskStatus(projectId, taskId, status);
      // Reload the project to get the updated task status
      loadProject(projectId);
    } catch (err) {
      console.error('Error updating task status:', err);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Typography color="error">{error}</Typography>;
  }

  if (!currentProject) {
    return <Typography>Project not found</Typography>;
  }

  // Calculate project progress
  const calculateProgress = () => {
    if (!currentProject.implementation_plan || !currentProject.implementation_plan.tasks) {
      return 0;
    }

    const tasks = currentProject.implementation_plan.tasks;
    const completedTasks = tasks.filter(task => task.status === 'completed').length;
    return (completedTasks / tasks.length) * 100;
  };

  const progress = calculateProgress();

  return (
    <Box className="project-detail-container">
      <Box>
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h4" component="h1">
              {currentProject.name}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<SettingsIcon />}
              size="small"
            >
              Settings
            </Button>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            {currentProject.git_url && (
              <Chip icon={<GitHubIcon />} label={currentProject.git_url} size="small" />
            )}
            {currentProject.slack_channel && (
              <Chip icon={<SlackIcon />} label={currentProject.slack_channel} size="small" />
            )}
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>
              Progress: {Math.round(progress)}%
            </Typography>
            <LinearProgress variant="determinate" value={progress} sx={{ height: 10, borderRadius: 5 }} />
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              color="primary"
              startIcon={<PlayArrowIcon />}
              onClick={handleAnalyzeProject}
              disabled={isAnalyzing}
            >
              {isAnalyzing ? 'Analyzing...' : 'Analyze Project'}
            </Button>
          </Box>
        </Paper>

        <Paper sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={handleTabChange} variant="fullWidth">
            <Tab label="Requirements" />
            <Tab label="Implementation" />
            <Tab label="GitHub" />
            <Tab label="Slack" />
          </Tabs>
          <Box sx={{ p: 3 }}>
            {tabValue === 0 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Project Requirements
                </Typography>
                {currentProject.documents && currentProject.documents.length > 0 ? (
                  currentProject.documents.map((doc, index) => (
                    <Paper key={index} sx={{ p: 2, mb: 2 }}>
                      <Typography variant="subtitle1">{doc.title || `Document ${index + 1}`}</Typography>
                      <Typography variant="body2">{doc.content || 'No content available'}</Typography>
                    </Paper>
                  ))
                ) : (
                  <Typography>
                    No requirements documents available. Upload documents or use the chat to define requirements.
                  </Typography>
                )}
              </Box>
            )}
            {tabValue === 1 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Implementation Plan
                </Typography>
                {currentProject.implementation_plan && currentProject.implementation_plan.tasks ? (
                  <ImplementationTree
                    tasks={currentProject.implementation_plan.tasks}
                    onTaskStatusChange={handleTaskStatusChange}
                  />
                ) : (
                  <Box>
                    <Typography gutterBottom>
                      No implementation plan available. Click "Analyze Project" to generate a plan.
                    </Typography>
                    <Button
                      variant="contained"
                      color="primary"
                      startIcon={<PlayArrowIcon />}
                      onClick={handleAnalyzeProject}
                      disabled={isAnalyzing}
                    >
                      {isAnalyzing ? 'Analyzing...' : 'Analyze Project'}
                    </Button>
                  </Box>
                )}
              </Box>
            )}
            {tabValue === 2 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  GitHub Integration
                </Typography>
                {currentProject.git_url ? (
                  <Box>
                    <Typography variant="body1" gutterBottom>
                      Repository: {currentProject.git_url}
                    </Typography>
                    {/* GitHub integration components would go here */}
                    <Typography variant="body2" color="text.secondary">
                      GitHub integration features coming soon.
                    </Typography>
                  </Box>
                ) : (
                  <Typography>
                    No GitHub repository linked to this project. Update project settings to add a repository.
                  </Typography>
                )}
              </Box>
            )}
            {tabValue === 3 && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Slack Integration
                </Typography>
                {currentProject.slack_channel ? (
                  <Box>
                    <Typography variant="body1" gutterBottom>
                      Channel: {currentProject.slack_channel}
                    </Typography>
                    {/* Slack integration components would go here */}
                    <Typography variant="body2" color="text.secondary">
                      Slack integration features coming soon.
                    </Typography>
                  </Box>
                ) : (
                  <Typography>
                    No Slack channel linked to this project. Update project settings to add a channel.
                  </Typography>
                )}
              </Box>
            )}
          </Box>
        </Paper>
      </Box>

      <Box>
        <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
          <Typography variant="h6" gutterBottom>
            Project Context
          </Typography>
          <ProjectContext project={currentProject} />
        </Paper>
      </Box>

      <Box sx={{ gridColumn: '1 / -1' }}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Chat with AI Assistant
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          <ChatInterface
            chatHistory={chatHistory}
            message={chatMessage}
            onMessageChange={handleChatMessageChange}
            onSendMessage={handleSendMessage}
            isSending={isSending}
            file={file}
            onFileChange={handleFileChange}
            onFileUpload={handleFileUpload}
          />
        </Paper>
      </Box>
    </Box>
  );
};

export default ProjectDetail;
