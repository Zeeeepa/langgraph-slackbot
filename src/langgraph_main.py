"""
Main entry point for the LangGraph-based Multi-Threaded Agentic Slackbot.

This module initializes the Slack app and starts the bot using LangGraph for agent orchestration.
"""

import os
import asyncio
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.langgraph_agents.slack_interface import LangGraphSlackInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Slack app
slack_app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Initialize LangGraph Slack interface
langgraph_slack_interface = LangGraphSlackInterface(
    slack_bot_token=os.environ["SLACK_BOT_TOKEN"],
    slack_app_token=os.environ["SLACK_APP_TOKEN"]
)

@slack_app.event("app_mention")
def handle_app_mention_events(body, say):
    """Handle app mention events from Slack."""
    try:
        event = body["event"]
        
        # Run the async handler in a new event loop
        asyncio.run(langgraph_slack_interface.handle_app_mention(event))
    
    except Exception as e:
        logger.error(f"Error handling app mention: {str(e)}", exc_info=True)
        
        channel_id = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])
        
        # Send error message
        say(
            text="Sorry, an error occurred while processing your request. Please try again.",
            channel=channel_id,
            thread_ts=thread_ts
        )

def start_slack_bot():
    """Start the Slack bot."""
    # Start the Socket Mode handler
    handler = SocketModeHandler(slack_app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

if __name__ == "__main__":
    # Start the Slack bot
    start_slack_bot()
