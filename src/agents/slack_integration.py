import os
import re
import json
import logging
import asyncio
import threading
import uuid
from typing import Dict, Any, List, Optional, Callable
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from .ai_user_agent import AIUserAgent
from .assistant_agent import AssistantAgent, Task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SlackIntegration:
    """
    Integration between AI User Agent, Assistant Agent, and Slack.
    Handles message routing and processing.
    """
    
    def __init__(self, 
                 slack_bot_token: str,
                 slack_app_token: str,
                 github_token: Optional[str] = None,
                 repo_name: Optional[str] = None,
                 model_name: str = "gpt-4o-mini",
                 project_dir: str = ".",
                 max_workers: int = 5):
        """
        Initialize the Slack integration.
        
        Args:
            slack_bot_token: Slack bot token for API access
            slack_app_token: Slack app token for Socket Mode
            github_token: GitHub API token for repository access
            repo_name: GitHub repository name (format: "owner/repo")
            model_name: LLM model to use
            project_dir: Directory containing project files
            max_workers: Maximum number of worker threads
        """
        self.slack_client = WebClient(token=slack_bot_token)
        self.slack_bot_token = slack_bot_token
        self.slack_app_token = slack_app_token
        
        # Initialize agents
        self.ai_user_agent = AIUserAgent(
            project_dir=project_dir,
            github_token=github_token,
            repo_name=repo_name,
            model_name=model_name
        )
        
        self.assistant_agent = AssistantAgent(
            github_token=github_token,
            repo_name=repo_name,
            model_name=model_name,
            max_workers=max_workers
        )
        
        # Message handling
        self.message_handlers = {}
        self.running = False
        self.message_thread = None
    
    def start(self):
        """Start the Slack integration and agent processing."""
        if self.running:
            logger.warning("Slack integration is already running.")
            return
        
        self.running = True
        
        # Start the Assistant Agent
        self.assistant_agent.start()
        
        # Start message processing thread
        self.message_thread = threading.Thread(
            target=self._message_processing_thread,
            name="SlackMessageProcessor",
            daemon=True
        )
        self.message_thread.start()
        
        logger.info("Slack integration started.")
    
    def stop(self):
        """Stop the Slack integration and agent processing."""
        self.running = False
        
        # Stop the Assistant Agent
        self.assistant_agent.stop()
        
        # Wait for message thread to finish
        if self.message_thread:
            self.message_thread.join(timeout=5.0)
        
        self.message_thread = None
        logger.info("Slack integration stopped.")
    
    def _message_processing_thread(self):
        """Thread for processing messages from Slack."""
        while self.running:
            try:
                # Process any pending tasks
                self.assistant_agent.check_dependencies()
                
                # Sleep to avoid busy waiting
                asyncio.run(asyncio.sleep(1.0))
            
            except Exception as e:
                logger.error(f"Error in message processing thread: {str(e)}", exc_info=True)
    
    def register_message_handler(self, pattern: str, handler: Callable):
        """
        Register a handler for messages matching a pattern.
        
        Args:
            pattern: Regular expression pattern to match messages
            handler: Function to handle matching messages
        """
        self.message_handlers[pattern] = handler
        logger.info(f"Registered message handler for pattern: {pattern}")
    
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
            
            # Get thread history for context
            thread_history = await self._get_thread_history(channel_id, thread_ts)
            
            # Check if this is a project initialization request
            if re.search(r"\b(initialize|init|start|create)\s+project\b", text, re.IGNORECASE):
                await self._handle_project_initialization(channel_id, thread_ts, text)
                return
            
            # Check if this is a task request
            if re.search(r"\b(implement|add|create|develop)\s+(feature|task|component)\b", text, re.IGNORECASE):
                await self._handle_task_request(channel_id, thread_ts, text)
                return
            
            # Check if this is a project state analysis request
            if re.search(r"\b(analyze|check|compare|status)\s+(project|state)\b", text, re.IGNORECASE):
                await self._handle_project_state_analysis(channel_id, thread_ts, text)
                return
            
            # Check if this is a task status request
            if re.search(r"\b(status|progress)\s+(of|for)\s+task\b", text, re.IGNORECASE):
                await self._handle_task_status_request(channel_id, thread_ts, text)
                return
            
            # Check for custom message handlers
            for pattern, handler in self.message_handlers.items():
                if re.search(pattern, text, re.IGNORECASE):
                    await handler(channel_id, thread_ts, text, thread_history)
                    return
            
            # Default handler for unrecognized requests
            await self._send_slack_message(
                channel_id=channel_id,
                text="I'm not sure how to handle that request. You can ask me to:\n"
                     "- Initialize a project\n"
                     "- Implement a feature or task\n"
                     "- Analyze the project state\n"
                     "- Check the status of a task",
                thread_ts=thread_ts
            )
        
        except Exception as e:
            logger.error(f"Error handling app mention: {str(e)}", exc_info=True)
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"An error occurred while processing your request: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def _handle_project_initialization(self, channel_id: str, thread_ts: str, text: str):
        """
        Handle project initialization requests.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            text: Message text
        """
        await self._send_slack_message(
            channel_id=channel_id,
            text="Initializing project... This may take a few minutes.",
            thread_ts=thread_ts
        )
        
        try:
            # Initialize the project
            implementation_plan = await self.ai_user_agent.initialize_project()
            
            if not implementation_plan:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text="Project initialization failed. No requirement documents found.",
                    thread_ts=thread_ts
                )
                return
            
            # Format the implementation plan for Slack
            phases = implementation_plan.get("phases", [])
            components = implementation_plan.get("components", [])
            
            message = "Project initialized successfully! Here's the implementation plan:\n\n"
            
            # Add phases
            message += "*Phases:*\n"
            for i, phase in enumerate(phases):
                message += f"*{i+1}. {phase.get('name')}*: {phase.get('description')}\n"
                
                # Add tasks
                tasks = phase.get("tasks", [])
                for j, task in enumerate(tasks):
                    message += f"   - {task.get('name')} (Priority: {task.get('priority')})\n"
            
            message += "\n*Components:*\n"
            for i, component in enumerate(components):
                message += f"*{i+1}. {component.get('name')}*: {component.get('description')}\n"
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=message,
                thread_ts=thread_ts
            )
        
        except Exception as e:
            logger.error(f"Error initializing project: {str(e)}", exc_info=True)
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"An error occurred during project initialization: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def _handle_task_request(self, channel_id: str, thread_ts: str, text: str):
        """
        Handle task implementation requests.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            text: Message text
        """
        # Extract task information from the message
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        await self._send_slack_message(
            channel_id=channel_id,
            text=f"Processing task request... Task ID: {task_id}",
            thread_ts=thread_ts
        )
        
        try:
            # Formulate a request for the Assistant Agent
            request = await self.ai_user_agent.formulate_assistant_request(text)
            
            if not request:
                # If formulation fails, use the original text as the request
                request = text
            
            # Add the task to the Assistant Agent
            task = self.assistant_agent.add_task(
                task_id=task_id,
                description=request,
                priority="medium"
            )
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"Task added to the queue with ID: {task_id}\n\n"
                     f"*Task Description:*\n{request}\n\n"
                     f"You can check the status of this task by asking: 'What's the status of task {task_id}?'",
                thread_ts=thread_ts
            )
        
        except Exception as e:
            logger.error(f"Error handling task request: {str(e)}", exc_info=True)
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"An error occurred while processing the task request: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def _handle_project_state_analysis(self, channel_id: str, thread_ts: str, text: str):
        """
        Handle project state analysis requests.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            text: Message text
        """
        await self._send_slack_message(
            channel_id=channel_id,
            text="Analyzing project state... This may take a few minutes.",
            thread_ts=thread_ts
        )
        
        try:
            # Analyze the project state
            analysis = await self.ai_user_agent.compare_project_state()
            
            if not analysis:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text="Project state analysis failed. Make sure the project is initialized and GitHub is configured.",
                    thread_ts=thread_ts
                )
                return
            
            # Format the analysis for Slack
            completed = analysis.get("completed", [])
            partial = analysis.get("partial", [])
            missing = analysis.get("missing", [])
            deviations = analysis.get("deviations", [])
            next_steps = analysis.get("next_steps", [])
            
            message = "*Project State Analysis:*\n\n"
            
            # Add completed tasks
            message += "*Completed Tasks:*\n"
            if completed:
                for task_id in completed:
                    message += f"- {task_id}\n"
            else:
                message += "- No completed tasks\n"
            
            # Add partially implemented tasks
            message += "\n*Partially Implemented Tasks:*\n"
            if partial:
                for task_info in partial:
                    task_id = task_info.get("task_id", "")
                    progress = task_info.get("progress", 0)
                    missing_info = task_info.get("missing", "")
                    message += f"- {task_id} (Progress: {progress*100:.0f}%)\n  Missing: {missing_info}\n"
            else:
                message += "- No partially implemented tasks\n"
            
            # Add missing tasks
            message += "\n*Missing Tasks:*\n"
            if missing:
                for task_id in missing:
                    message += f"- {task_id}\n"
            else:
                message += "- No missing tasks\n"
            
            # Add deviations
            if deviations:
                message += "\n*Deviations from Plan:*\n"
                for deviation in deviations:
                    message += f"- {deviation}\n"
            
            # Add next steps
            message += "\n*Recommended Next Steps:*\n"
            if next_steps:
                for step in next_steps:
                    message += f"- {step}\n"
            else:
                message += "- No specific next steps recommended\n"
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=message,
                thread_ts=thread_ts
            )
            
            # Formulate further requests if needed
            if missing or partial:
                further_requests = await self.ai_user_agent.formulate_further_requests(analysis)
                
                if further_requests:
                    message = "*Suggested Further Requests:*\n\n"
                    
                    for i, request in enumerate(further_requests):
                        message += f"*Request {i+1}:*\n{request}\n\n"
                    
                    await self._send_slack_message(
                        channel_id=channel_id,
                        text=message,
                        thread_ts=thread_ts
                    )
        
        except Exception as e:
            logger.error(f"Error analyzing project state: {str(e)}", exc_info=True)
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"An error occurred during project state analysis: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def _handle_task_status_request(self, channel_id: str, thread_ts: str, text: str):
        """
        Handle task status requests.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            text: Message text
        """
        # Extract task ID from the message
        match = re.search(r"\b(task|task-id|id)[:\s]+([a-zA-Z0-9-]+)", text, re.IGNORECASE)
        
        if not match:
            # If no specific task ID, show all tasks
            tasks = self.assistant_agent.get_all_tasks()
            
            if not tasks:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text="No tasks found.",
                    thread_ts=thread_ts
                )
                return
            
            message = "*All Tasks:*\n\n"
            
            for task_info in tasks:
                task_id = task_info.get("task_id", "")
                status = task_info.get("status", "")
                priority = task_info.get("priority", "")
                
                message += f"*Task ID:* {task_id}\n"
                message += f"*Status:* {status}\n"
                message += f"*Priority:* {priority}\n"
                
                if task_info.get("branch_name"):
                    message += f"*Branch:* {task_info.get('branch_name')}\n"
                
                if task_info.get("error"):
                    message += f"*Error:* {task_info.get('error')}\n"
                
                message += "\n"
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=message,
                thread_ts=thread_ts
            )
            return
        
        # Get status of specific task
        task_id = match.group(2)
        task_status = self.assistant_agent.get_task_status(task_id)
        
        if not task_status:
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"Task with ID '{task_id}' not found.",
                thread_ts=thread_ts
            )
            return
        
        # Format the task status for Slack
        message = f"*Task Status:*\n\n"
        message += f"*Task ID:* {task_status.get('task_id')}\n"
        message += f"*Description:* {task_status.get('description')}\n"
        message += f"*Status:* {task_status.get('status')}\n"
        message += f"*Priority:* {task_status.get('priority')}\n"
        
        if task_status.get("dependencies"):
            message += f"*Dependencies:* {', '.join(task_status.get('dependencies'))}\n"
        
        if task_status.get("branch_name"):
            message += f"*Branch:* {task_status.get('branch_name')}\n"
        
        if task_status.get("error"):
            message += f"*Error:* {task_status.get('error')}\n"
        
        # Add result details if available
        if task_status.get("result"):
            result = task_status.get("result", {})
            
            if isinstance(result, dict):
                task_type = result.get("task_type")
                
                if task_type == "implementation":
                    pr_info = result.get("pull_request", {})
                    
                    if pr_info:
                        message += f"\n*Pull Request:* <{pr_info.get('pr_url')}|#{pr_info.get('pr_number')}>\n"
                        message += f"*Title:* {pr_info.get('title')}\n"
                
                elif task_type == "document_processing":
                    processing_result = result.get("processing_result", {})
                    
                    if processing_result:
                        message += f"\n*Processing Summary:* {processing_result.get('summary')}\n"
                
                elif task_type == "analysis":
                    analysis_result = result.get("analysis_result", {})
                    
                    if analysis_result:
                        message += f"\n*Analysis Type:* {analysis_result.get('analysis_type')}\n"
                        
                        findings = analysis_result.get("findings", [])
                        if findings:
                            message += "*Findings:*\n"
                            for finding in findings:
                                message += f"- {finding}\n"
        
        await self._send_slack_message(
            channel_id=channel_id,
            text=message,
            thread_ts=thread_ts
        )
    
    async def _get_thread_history(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """
        Get the history of a Slack thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            
        Returns:
            List of messages in the thread
        """
        try:
            response = self.slack_client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                inclusive=True
            )
            
            return [
                {
                    "user": msg.get("user", ""),
                    "text": msg.get("text", ""),
                    "ts": msg.get("ts", "")
                }
                for msg in response["messages"]
            ]
        
        except SlackApiError as e:
            logger.error(f"Error getting thread history: {str(e)}", exc_info=True)
            return []
    
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