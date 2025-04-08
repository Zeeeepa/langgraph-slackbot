# Projector Frontend

This is the frontend for the Projector application, a project management tool with AI assistance.

## Features

- Project management dashboard
- Implementation plan tracking
- Chat interface with AI assistant
- GitHub and Slack integration
- Document management
- Task tracking and status updates

## Getting Started

### Prerequisites

- Node.js (v14 or later)
- npm or yarn

### Installation

1. Clone the repository
2. Navigate to the frontend directory
3. Install dependencies:

```bash
npm install
# or
yarn install
```

### Running the Development Server

```bash
npm start
# or
yarn start
```

This will start the development server at [http://localhost:3000](http://localhost:3000).

### Building for Production

```bash
npm run build
# or
yarn build
```

This will create a production-ready build in the `build` directory.

## Project Structure

- `src/api`: API service functions
- `src/components`: Reusable UI components
- `src/context`: React context providers
- `src/pages`: Page components
- `src/styles`: CSS styles
- `public`: Static assets

## Backend Integration

The frontend is designed to work with the Projector backend API. Make sure the backend server is running at the URL specified in the `proxy` field in `package.json`.

## Technologies Used

- React
- React Router
- Material-UI
- Axios
- React Markdown
