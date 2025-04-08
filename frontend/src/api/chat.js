import axios from 'axios';

const API_URL = '/api/chat';

export const sendChatMessage = async (message, projectId = null, chatHistory = []) => {
  try {
    const response = await axios.post(API_URL, {
      message,
      project_id: projectId,
      chat_history: chatHistory,
    });
    return response.data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

export const uploadFile = async (formData) => {
  try {
    const response = await axios.post(`${API_URL}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading file:', error);
    throw error;
  }
};
