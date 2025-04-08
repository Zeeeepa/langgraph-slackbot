"""
Slack interface for the LangGraph-based Multi-Threaded Agentic Slackbot.

This module provides the integration between LangGraph agents and Slack.
"""

import os
import logging
import asyncio
import json
from typing import Dict, List, Any, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .agent_graph import create_agent_graph, AgentState, TaskStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class LangGraphSlackInterface:
    """
    Interface between LangGraph agents and Slack.
    """
    
    def __init__(self, slack_bot_token: str, slack_app_token: str):
        """
        Initialize the LangGraph Slack interface.
        
        Args:
            slack_bot_token: Slack bot token for API access
            slack_app_token: Slack app token for Socket Mode
        """
        self.slack_client = WebClient(token=slack_bot_token)
        self.slack_bot_token = slack_bot_token
        self.slack_app_token = slack_app_token
        
        # Create the agent graph
        self.agent_graph = create_agent_graph()
        
        # Conversation state
        self.conversations = {}
        
    async def handle_app_mention(self, event: Dict[str, Any]):
        """
        Handle app mention events from Slack.
        
        Args:
            event: Slack event data
        """
        try:
            channel_id = event["channel"]
            thread_ts = event.get("thread_ts", event["ts"])
            user_id = event["user"]
            text = event["text"]
            
            # Remove the bot mention from the text
            bot_id = os.environ.get("SLACK_BOT_ID", "")
            text = text.replace(f"<@{bot_id}>", "").strip()
            
            logger.info(f"Received app mention: {text}")
            
            # Get or create conversation state
            conversation_id = f"{channel_id}:{thread_ts}"
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = {
                    "messages": [],
                    "task": None,
                    "status": TaskStatus.PENDING.value,
                    "results": [],
                    "errors": [],
                    "context": {
                        "channel_id": channel_id,
                        "thread_ts": thread_ts,
                        "user_id": user_id
                    }
                }
            
            # Add the user message to the conversation
            self.conversations[conversation_id]["messages"].append({
                "role": "user",
                "content": text
            })
            
            # Process the message with the agent graph
            await self._process_message(conversation_id)
            
        except Exception as e:
            logger.error(f"Error handling app mention: {str(e)}", exc_info=True)
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"An error occurred while processing your request: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def _process_message(self, conversation_id: str):
        """
        Process a message with the agent graph.
        
        Args:
            conversation_id: ID of the conversation
        """
        # Get the conversation state
        conversation = self.conversations[conversation_id]
        channel_id = conversation["context"]["channel_id"]
        thread_ts = conversation["context"]["thread_ts"]
        
        try:
            # Send a typing indicator
            await self._send_slack_message(
                channel_id=channel_id,
                text="Thinking...",
                thread_ts=thread_ts
            )
            
            # Process the message with the agent graph
            result = await asyncio.to_thread(
                self.agent_graph.invoke,
                conversation
            )
            
            # Update the conversation state
            self.conversations[conversation_id] = result
            
            # Send the response to Slack
            if result["messages"] and result["messages"][-1]["role"] == "assistant":
                response_text = result["messages"][-1]["content"]
                await self._send_slack_message(
                    channel_id=channel_id,
                    text=response_text,
                    thread_ts=thread_ts
                )
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            
            # Add the error to the conversation
            conversation["errors"].append({
                "error": str(e),
                "traceback": str(e.__traceback__)
            })
            
            # Send an error message to Slack
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"An error occurred while processing your request: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def _send_slack_message(self, channel_id: str, text: str, thread_ts: str = None) -> Dict[str, Any]:
        """
        Send a message to Slack.
        
        Args:
            channel_id: Slack channel ID
            text: Message text
            thread_ts: Thread timestamp (optional)
            
        Returns:
            Response from Slack API
        """
        try:
            response = self.slack_client.chat_postMessage(
                channel=channel_id,
                text=text,
                thread_ts=thread_ts
            )
            
            return response
        
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {str(e)}", exc_info=True)
            raise
