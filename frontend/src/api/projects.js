import axios from 'axios';

const API_URL = '/api/projects';

export const fetchProjects = async () => {
  try {
    const response = await axios.get(API_URL);
    return response.data;
  } catch (error) {
    console.error('Error fetching projects:', error);
    throw error;
  }
};

export const fetchProject = async (projectId) => {
  try {
    const response = await axios.get(`${API_URL}/${projectId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching project ${projectId}:`, error);
    throw error;
  }
};

export const createProject = async (projectData) => {
  try {
    const response = await axios.post(API_URL, projectData);
    return response.data;
  } catch (error) {
    console.error('Error creating project:', error);
    throw error;
  }
};

export const updateProject = async (projectId, projectData) => {
  try {
    const response = await axios.put(`${API_URL}/${projectId}`, projectData);
    return response.data;
  } catch (error) {
    console.error(`Error updating project ${projectId}:`, error);
    throw error;
  }
};

export const deleteProject = async (projectId) => {
  try {
    const response = await axios.delete(`${API_URL}/${projectId}`);
    return response.data;
  } catch (error) {
    console.error(`Error deleting project ${projectId}:`, error);
    throw error;
  }
};

export const analyzeProject = async (projectId) => {
  try {
    const response = await axios.post(`${API_URL}/${projectId}/analyze`);
    return response.data;
  } catch (error) {
    console.error(`Error analyzing project ${projectId}:`, error);
    throw error;
  }
};

export const updateTaskStatus = async (projectId, taskId, status) => {
  try {
    const response = await axios.put(`${API_URL}/${projectId}/tasks/${taskId}`, { status });
    return response.data;
  } catch (error) {
    console.error(`Error updating task ${taskId} status:`, error);
    throw error;
  }
};

export const getRecentActivity = async (projectId, days = 7) => {
  try {
    const response = await axios.get(`${API_URL}/${projectId}/recent-activity?days=${days}`);
    return response.data;
  } catch (error) {
    console.error(`Error getting recent activity for project ${projectId}:`, error);
    throw error;
  }
};
