import axios from 'axios';

const API_URL = '/api/github';

export const getRepositoryContents = async (owner, repo, path = '') => {
  try {
    const response = await axios.get(`${API_URL}/repos/${owner}/${repo}/contents/${path}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching repository contents for ${owner}/${repo}/${path}:`, error);
    throw error;
  }
};

export const getPullRequests = async (owner, repo, state = 'open') => {
  try {
    const response = await axios.get(`${API_URL}/repos/${owner}/${repo}/pulls?state=${state}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching pull requests for ${owner}/${repo}:`, error);
    throw error;
  }
};

export const getPullRequest = async (owner, repo, prNumber) => {
  try {
    const response = await axios.get(`${API_URL}/repos/${owner}/${repo}/pulls/${prNumber}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching pull request #${prNumber} for ${owner}/${repo}:`, error);
    throw error;
  }
};

export const getPullRequestComments = async (owner, repo, prNumber) => {
  try {
    const response = await axios.get(`${API_URL}/repos/${owner}/${repo}/pulls/${prNumber}/comments`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching comments for PR #${prNumber} in ${owner}/${repo}:`, error);
    throw error;
  }
};

export const createPullRequestComment = async (owner, repo, prNumber, body) => {
  try {
    const response = await axios.post(`${API_URL}/repos/${owner}/${repo}/pulls/${prNumber}/comments`, { body });
    return response.data;
  } catch (error) {
    console.error(`Error creating comment on PR #${prNumber} in ${owner}/${repo}:`, error);
    throw error;
  }
};

export const getBranches = async (owner, repo) => {
  try {
    const response = await axios.get(`${API_URL}/repos/${owner}/${repo}/branches`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching branches for ${owner}/${repo}:`, error);
    throw error;
  }
};

export const getCommits = async (owner, repo, branch = null, path = null) => {
  try {
    let url = `${API_URL}/repos/${owner}/${repo}/commits`;
    const params = {};
    if (branch) params.branch = branch;
    if (path) params.path = path;
    
    const response = await axios.get(url, { params });
    return response.data;
  } catch (error) {
    console.error(`Error fetching commits for ${owner}/${repo}:`, error);
    throw error;
  }
};

export const getRecentMerges = async (owner, repo, days = 7) => {
  try {
    const response = await axios.get(`${API_URL}/repos/${owner}/${repo}/merges?days=${days}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching recent merges for ${owner}/${repo}:`, error);
    throw error;
  }
};
