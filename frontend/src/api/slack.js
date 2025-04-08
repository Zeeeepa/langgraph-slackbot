import axios from 'axios';

const API_URL = '/api/slack';

export const sendMessage = async (channel, text, blocks = null, threadTs = null) => {
  try {
    const response = await axios.post(`${API_URL}/messages`, {
      channel,
      text,
      blocks,
      thread_ts: threadTs,
    });
    return response.data;
  } catch (error) {
    console.error('Error sending Slack message:', error);
    throw error;
  }
};

export const listChannels = async () => {
  try {
    const response = await axios.get(`${API_URL}/channels`);
    return response.data.channels;
  } catch (error) {
    console.error('Error listing Slack channels:', error);
    throw error;
  }
};

export const listUsers = async () => {
  try {
    const response = await axios.get(`${API_URL}/users`);
    return response.data.users;
  } catch (error) {
    console.error('Error listing Slack users:', error);
    throw error;
  }
};

export const getMessages = async (channel, limit = 100) => {
  try {
    const response = await axios.get(`${API_URL}/messages/${channel}?limit=${limit}`);
    return response.data.messages;
  } catch (error) {
    console.error(`Error getting messages from channel ${channel}:`, error);
    throw error;
  }
};

export const uploadFile = async (channel, filename, content, title = null, threadTs = null) => {
  try {
    const response = await axios.post(`${API_URL}/upload`, {
      channel,
      filename,
      content,
      title,
      thread_ts: threadTs,
    });
    return response.data.file;
  } catch (error) {
    console.error('Error uploading file to Slack:', error);
    throw error;
  }
};
