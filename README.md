# LangGraph Slackbot

A multi-threaded agentic Slackbot powered by LangGraph for sophisticated agent orchestration.

## Overview

This project implements a Slack bot that uses LangGraph to orchestrate AI agents for handling various tasks. The bot can:

- Analyze user requests and determine the appropriate task type
- Route tasks to specialized agents based on their type
- Process implementation, document processing, analysis, and project management tasks
- Handle tasks that require human intervention
- Maintain conversation state across interactions

## Architecture

The system is built with the following components:

### LangGraph Agents

- **Agent Graph**: A directed graph that defines the flow of task processing
- **Agent Nodes**: Specialized functions for handling different types of tasks
- **State Management**: Maintains conversation and task state throughout the processing flow

### Slack Integration

- **Slack Interface**: Handles communication between LangGraph agents and Slack
- **Event Handling**: Processes app mention events from Slack
- **Message Routing**: Routes messages to the appropriate agent based on content

## Getting Started

### Prerequisites

- Python 3.9+
- Slack Bot Token and App Token
- OpenAI API Key (or other LLM provider)

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set environment variables:
   ```
   export SLACK_BOT_TOKEN=your-slack-bot-token
   export SLACK_APP_TOKEN=your-slack-app-token
   export OPENAI_API_KEY=your-openai-api-key
   ```

### Running the Bot

```
python src/langgraph_main.py
```

## Usage

Mention the bot in a Slack channel or thread with your request. The bot will:

1. Analyze your request to determine the task type
2. Process the task using the appropriate agent
3. Format and send the response back to the Slack thread

Example requests:
- "Can you implement a feature to..."
- "Please analyze this document..."
- "Create a project plan for..."
- "What do you think about..."

## Development

### Adding New Agent Nodes

To add a new agent node:

1. Define a new function in `agent_graph.py` that takes and returns an `AgentState`
2. Add the node to the graph in the `create_agent_graph` function
3. Update the `route_task` function to route to your new node

### Extending the Slack Interface

To add new Slack functionality:

1. Add new methods to the `LangGraphSlackInterface` class in `slack_interface.py`
2. Register new event handlers in `langgraph_main.py` if needed

## License

[MIT License](LICENSE)
