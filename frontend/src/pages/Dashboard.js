import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  GitHub as GitHubIcon,
  Slack as SlackIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { useProjects } from '../context/ProjectContext';
import { createProject, deleteProject } from '../api/projects';

const Dashboard = () => {
  const { projects, loading, error, loadProjects } = useProjects();
  const [openDialog, setOpenDialog] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    git_url: '',
    slack_channel: '',
    max_parallel_tasks: 3,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleOpenDialog = () => {
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setNewProject({
      name: '',
      git_url: '',
      slack_channel: '',
      max_parallel_tasks: 3,
    });
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewProject({
      ...newProject,
      [name]: value,
    });
  };

  const handleCreateProject = async () => {
    setIsSubmitting(true);
    try {
      await createProject(newProject);
      await loadProjects();
      handleCloseDialog();
    } catch (err) {
      console.error('Error creating project:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteProject = async (projectId) => {
    if (window.confirm('Are you sure you want to delete this project?')) {
      try {
        await deleteProject(projectId);
        await loadProjects();
      } catch (err) {
        console.error('Error deleting project:', err);
      }
    }
  };

  const handleProjectClick = (projectId) => {
    navigate(`/projects/${projectId}`);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Dashboard
        </Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={handleOpenDialog}
        >
          Add Project
        </Button>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Typography color="error">{error}</Typography>
      ) : (
        <Grid container spacing={3}>
          {projects.map((project) => (
            <Grid item xs={12} sm={6} md={4} key={project.id}>
              <Card className="project-card">
                <CardContent>
                  <Typography variant="h5" component="div" gutterBottom>
                    {project.name}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    {project.git_url && (
                      <Tooltip title={project.git_url}>
                        <Chip icon={<GitHubIcon />} label="GitHub" size="small" />
                      </Tooltip>
                    )}
                    {project.slack_channel && (
                      <Tooltip title={project.slack_channel}>
                        <Chip icon={<SlackIcon />} label="Slack" size="small" />
                      </Tooltip>
                    )}
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Created: {new Date(project.created_at).toLocaleDateString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Updated: {new Date(project.updated_at).toLocaleDateString()}
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button size="small" onClick={() => handleProjectClick(project.id)}>
                    View Details
                  </Button>
                  <Box sx={{ flexGrow: 1 }} />
                  <IconButton size="small" onClick={(e) => {
                    e.stopPropagation();
                    // Handle edit project
                  }}>
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteProject(project.id);
                  }}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={openDialog} onClose={handleCloseDialog}>
        <DialogTitle>Create New Project</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            name="name"
            label="Project Name"
            type="text"
            fullWidth
            variant="outlined"
            value={newProject.name}
            onChange={handleInputChange}
            required
          />
          <TextField
            margin="dense"
            name="git_url"
            label="GitHub Repository URL"
            type="text"
            fullWidth
            variant="outlined"
            value={newProject.git_url}
            onChange={handleInputChange}
            placeholder="https://github.com/username/repo"
          />
          <TextField
            margin="dense"
            name="slack_channel"
            label="Slack Channel"
            type="text"
            fullWidth
            variant="outlined"
            value={newProject.slack_channel}
            onChange={handleInputChange}
            placeholder="#channel-name"
          />
          <TextField
            margin="dense"
            name="max_parallel_tasks"
            label="Max Parallel Tasks"
            type="number"
            fullWidth
            variant="outlined"
            value={newProject.max_parallel_tasks}
            onChange={handleInputChange}
            InputProps={{ inputProps: { min: 1, max: 10 } }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleCreateProject}
            variant="contained"
            color="primary"
            disabled={!newProject.name || isSubmitting}
          >
            {isSubmitting ? <CircularProgress size={24} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Dashboard;
