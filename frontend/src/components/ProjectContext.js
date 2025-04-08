import React from 'react';
import {
  Box,
  Typography,
  Divider,
  List,
  ListItem,
  ListItemText,
  Paper,
  Chip,
} from '@mui/material';
import ReactMarkdown from 'react-markdown';

const ProjectContext = ({ project }) => {
  if (!project) {
    return <Typography>No project selected</Typography>;
  }

  // Extract features from the project
  const features = project.features || [];

  // Extract implementation plan
  const implementationPlan = project.implementation_plan || {};
  const tasks = implementationPlan.tasks || [];

  // Calculate progress
  const calculateProgress = () => {
    if (!tasks.length) return 0;
    const completedTasks = tasks.filter(task => task.status === 'completed').length;
    return Math.round((completedTasks / tasks.length) * 100);
  };

  const progress = calculateProgress();

  return (
    <Box sx={{ height: '100%', overflowY: 'auto' }}>
      <Typography variant="subtitle1" gutterBottom>
        Project Overview
      </Typography>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="body2" gutterBottom>
          <strong>Name:</strong> {project.name}
        </Typography>
        {project.git_url && (
          <Typography variant="body2" gutterBottom>
            <strong>Repository:</strong> {project.git_url}
          </Typography>
        )}
        {project.slack_channel && (
          <Typography variant="body2" gutterBottom>
            <strong>Slack Channel:</strong> {project.slack_channel}
          </Typography>
        )}
        <Typography variant="body2">
          <strong>Progress:</strong> {progress}%
        </Typography>
      </Paper>

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle1" gutterBottom>
        Features
      </Typography>
      {features.length > 0 ? (
        <List dense>
          {features.map((feature, index) => (
            <ListItem key={index}>
              <ListItemText
                primary={feature.name || `Feature ${index + 1}`}
                secondary={feature.description || 'No description available'}
              />
            </ListItem>
          ))}
        </List>
      ) : (
        <Typography variant="body2" color="text.secondary">
          No features defined yet. Use the chat to define project features.
        </Typography>
      )}

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle1" gutterBottom>
        Recent Activity
      </Typography>
      <List dense>
        {tasks.slice(0, 5).map((task, index) => (
          <ListItem key={index}>
            <ListItemText
              primary={task.title}
              secondary={
                <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                  <Chip
                    label={task.status}
                    size="small"
                    color={
                      task.status === 'completed'
                        ? 'success'
                        : task.status === 'in_progress'
                        ? 'warning'
                        : 'default'
                    }
                    sx={{ mr: 1 }}
                  />
                  {task.updated_at && (
                    <Typography variant="caption" color="text.secondary">
                      {new Date(task.updated_at).toLocaleDateString()}
                    </Typography>
                  )}
                </Box>
              }
            />
          </ListItem>
        ))}
      </List>

      {project.documents && project.documents.length > 0 && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle1" gutterBottom>
            Documentation
          </Typography>
          <List dense>
            {project.documents.map((doc, index) => (
              <ListItem key={index} button>
                <ListItemText
                  primary={doc.title || `Document ${index + 1}`}
                  secondary={doc.description || 'View document'}
                />
              </ListItem>
            ))}
          </List>
        </>
      )}
    </Box>
  );
};

export default ProjectContext;
