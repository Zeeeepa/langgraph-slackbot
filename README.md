# Multi-Threaded Agentic Slackbot

A sophisticated multi-agent system for project management and document processing through Slack. The system consists of two primary agents:

1. **AI User Agent** - Initiates requests and manages project requirements
2. **Assistant Agent** - Processes requests and implements solutions

## Important Documentation

Before working on this project, please read the following documents:

- [REQUIREMENTStodo.md](REQUIREMENTStodo.md) - Contains comprehensive instructions and requirements
- [PLANTODO.md](PLANTODO.md) - Detailed implementation plan with tasks and timelines

## Features

- **Multi-Threading Architecture**: Concurrent request handling with thread-safe state management
- **GitHub Integration**: Automated branch management, PR creation, and post-merge analysis
- **Document Processing**: Markdown parsing for requirement extraction and analysis
- **Project Management**: Task tracking, dependency management, and progress monitoring
- **Slack Integration**: Seamless communication between agents and users
- **Multi-Project Support**: Manage multiple GitHub repositories simultaneously
- **MCP Integration**: Tool registry for dynamic capability extension

## Architecture

The system leverages a multi-threaded architecture to handle concurrent development tasks and manage GitHub project features efficiently:

- **AI User Agent**: Analyzes requirements from .md documents, creates implementation plans, monitors project state, and formulates requests
- **Assistant Agent**: Processes requests, implements features using multi-threading, manages GitHub branches, and handles concurrent development
- **Slack Integration**: Connects the agents with Slack, handles message routing and processing

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/langgraph-slackbot.git
   cd langgraph-slackbot
   ```

2. Install dependencies:
   ```bash
   pip install pipenv
   pipenv install
   ```

3. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Edit the `.env` file with your credentials:
   - Slack API credentials (Bot Token, App Token, Bot ID)
   - OpenAI API key
   - GitHub token
   - Application settings

## Usage

1. Start the Slackbot:
   ```bash
   pipenv run python src/main.py
   ```

2. Interact with the bot in Slack:
   - Add a project: `@bot add project name:myproject repo:owner/repo`
   - Initialize a project: `@bot initialize project name:myproject`
   - Implement a feature: `@bot implement feature X`
   - Analyze project state: `@bot analyze project state`
   - Check task status: `@bot what's the status of task task-123?`

## Workflow

1. **Project Initialization**
   - User provides requirements via .md documents
   - AI User Agent analyzes requirements and creates implementation plan
   - Initial project structure is established

2. **Development Cycle**
   - AI User Agent formulates specific implementation requests
   - Requests are sent to Assistant Agent via Slack
   - Assistant Agent processes requests in multi-threaded environment
   - Features are developed in separate branches
   - Pull requests are created for completed features

3. **Project Management**
   - Progress tracking across all development threads
   - Resource allocation based on priority and dependencies
   - Automated testing and validation
   - Documentation generation

4. **Post-Merge Analysis**
   - AI User Agent compares project state with requirements after merges
   - Identifies gaps or additional requirements
   - Formulates new requests to address remaining work
   - Continuous improvement through iterative development

## Project Structure

```
langgraph-slackbot/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── ai_user_agent.py
│   │   ├── assistant_agent.py
│   │   └── slack_integration.py
│   ├── main.py
│   ├── prompts.py
│   └── tools.py
├── .env.example
├── .env.dev
├── Pipfile
├── Pipfile.lock
├── PROJECT.md
└── README.md
```

## Configuration

The application can be configured using environment variables:

- `SLACK_BOT_TOKEN`: Slack bot token for API access
- `SLACK_APP_TOKEN`: Slack app token for Socket Mode
- `SLACK_BOT_ID`: Slack bot user ID
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-4o-mini)
- `GITHUB_TOKEN`: GitHub API token for repository access
- `PROJECT_DIR`: Directory containing project files (default: ".")
- `MAX_WORKERS`: Maximum number of worker threads (default: 5)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.