import React from 'react';
import {
  Box,
  Typography,
  Checkbox,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Tooltip,
  Collapse,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as RadioButtonUncheckedIcon,
  PlayCircleOutline as PlayCircleOutlineIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

const ImplementationTree = ({ tasks, onTaskStatusChange }) => {
  const [expanded, setExpanded] = React.useState({});

  const toggleExpand = (taskId) => {
    setExpanded({
      ...expanded,
      [taskId]: !expanded[taskId],
    });
  };

  const handleStatusChange = (taskId, status) => {
    onTaskStatusChange(taskId, status === 'completed' ? 'in_progress' : 'completed');
  };

  const renderTask = (task, level = 0) => {
    const hasSubtasks = task.subtasks && task.subtasks.length > 0;
    const isExpanded = expanded[task.id];
    const isCompleted = task.status === 'completed';
    const isInProgress = task.status === 'in_progress';

    return (
      <React.Fragment key={task.id}>
        <ListItem
          sx={{
            pl: level * 4,
            backgroundColor: isCompleted
              ? 'rgba(76, 175, 80, 0.1)'
              : isInProgress
              ? 'rgba(255, 152, 0, 0.1)'
              : 'transparent',
          }}
        >
          {hasSubtasks && (
            <IconButton size="small" onClick={() => toggleExpand(task.id)}>
              {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          )}
          <ListItemIcon>
            <Checkbox
              edge="start"
              checked={isCompleted}
              onChange={() => handleStatusChange(task.id, task.status)}
              icon={isInProgress ? <PlayCircleOutlineIcon color="warning" /> : <RadioButtonUncheckedIcon />}
              checkedIcon={<CheckCircleIcon color="success" />}
            />
          </ListItemIcon>
          <ListItemText
            primary={task.title}
            secondary={task.description}
            primaryTypographyProps={{
              style: {
                textDecoration: isCompleted ? 'line-through' : 'none',
                color: isCompleted ? '#4caf50' : isInProgress ? '#ff9800' : 'inherit',
              },
            }}
          />
          <ListItemSecondaryAction>
            <Tooltip title="Task Details">
              <IconButton edge="end" aria-label="details">
                <InfoIcon />
              </IconButton>
            </Tooltip>
          </ListItemSecondaryAction>
        </ListItem>
        {hasSubtasks && (
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {task.subtasks.map((subtask) => renderTask(subtask, level + 1))}
            </List>
          </Collapse>
        )}
      </React.Fragment>
    );
  };

  // Group tasks by module
  const groupTasksByModule = () => {
    const modules = {};
    
    tasks.forEach(task => {
      const module = task.module || 'General';
      if (!modules[module]) {
        modules[module] = [];
      }
      modules[module].push(task);
    });
    
    return modules;
  };

  const modules = groupTasksByModule();

  return (
    <Box className="implementation-tree">
      {Object.entries(modules).map(([moduleName, moduleTasks]) => (
        <Box key={moduleName} sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            {moduleName}
          </Typography>
          <List>
            {moduleTasks.map(task => renderTask(task))}
          </List>
        </Box>
      ))}
    </Box>
  );
};

export default ImplementationTree;
