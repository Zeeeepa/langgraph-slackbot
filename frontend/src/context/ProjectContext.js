import React, { createContext, useState, useContext, useEffect } from 'react';
import { fetchProjects, fetchProject } from '../api/projects';

const ProjectContext = createContext();

export const useProjects = () => useContext(ProjectContext);

export const ProjectProvider = ({ children }) => {
  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadProject = async (projectId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProject(projectId);
      setCurrentProject(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <ProjectContext.Provider
      value={{
        projects,
        currentProject,
        loading,
        error,
        loadProjects,
        loadProject,
        setCurrentProject,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};
