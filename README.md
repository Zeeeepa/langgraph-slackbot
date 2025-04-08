# Projector

Projector is a comprehensive project management system with AI assistance, designed to help teams plan, track, and execute software development projects efficiently.

## Features

- **Project Management**: Create and manage projects with detailed tracking
- **AI Assistant**: Chat with an AI assistant for project planning and implementation help
- **Implementation Tracking**: Track the progress of project implementation with a hierarchical task view
- **GitHub Integration**: Connect projects to GitHub repositories for code management
- **Slack Integration**: Connect projects to Slack channels for team communication
- **Document Management**: Upload and manage project documents
- **Task Management**: Create, assign, and track tasks with dependencies

## Architecture

The application consists of two main components:

1. **Backend**: A FastAPI-based API server that handles data processing, AI integration, and external service connections
2. **Frontend**: A React-based web application that provides the user interface

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm or yarn
- GitHub account (for GitHub integration)
- Slack workspace (for Slack integration)

### Backend Setup

1. Navigate to the project root directory
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```
5. Run the backend server:
   ```bash
   uvicorn projector.api.main:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```
3. Start the development server:
   ```bash
   npm start
   # or
   yarn start
   ```

## Usage

1. Open your browser and navigate to http://localhost:3000
2. Create a new project with a name, GitHub repository URL, and Slack channel
3. Upload project requirements documents or use the chat to define requirements
4. Click "Analyze Project" to generate an implementation plan
5. Track progress through the implementation tree view
6. Use the chat interface to get help from the AI assistant

## API Documentation

The backend API documentation is available at http://localhost:8000/docs when the backend server is running.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
