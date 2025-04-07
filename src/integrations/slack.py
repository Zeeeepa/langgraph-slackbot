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
from src.agents.ai_user_agent import AIUserAgent
from src.agents.assistant_agent import AssistantAgent, Task
from concurrent.futures import ThreadPoolExecutor

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
            repo_name: GitHub repository name (format: "owner/repo") - deprecated, use project_management instead
            model_name: LLM model to use
            project_dir: Directory containing project files
            max_workers: Maximum number of worker threads
        """
        self.slack_client = WebClient(token=slack_bot_token)
        self.slack_bot_token = slack_bot_token
        self.slack_app_token = slack_app_token
        
        # Initialize AI User Agent
        self.ai_user_agent = AIUserAgent(
            project_dir=project_dir,
            github_token=github_token,
            repo_name=repo_name,
            model_name=model_name
        )
        
        # Initialize Assistant Agent
        self.assistant_agent = AssistantAgent(
            project_dir=project_dir,
            github_token=github_token,
            model_name=model_name,
            max_workers=max_workers
        )
        
        # Thread management
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        self.thread = None
        
        # Message queue for processing
        self.message_queue = []
        self.queue_lock = threading.Lock()
        
        # Active conversations
        self.active_conversations = {}
        self.conversation_lock = threading.Lock()
    
    def add_project(self, project_name: str, repo_url: str):
        """
        Add a project for management.
        
        Args:
            project_name: Name of the project
            repo_url: GitHub repository URL or name (format: "owner/repo")
        """
        # Extract owner/repo format if full URL is provided
        if repo_url.startswith("http"):
            parts = repo_url.strip("/").split("/")
            if len(parts) >= 2:
                repo_name = f"{parts[-2]}/{parts[-1]}"
            else:
                logger.error(f"Invalid repository URL: {repo_url}")
                return
        else:
            repo_name = repo_url
        
        self.projects[project_name] = {
            "repo_name": repo_name,
            "tasks": {}
        }
        
        logger.info(f"Added project '{project_name}' with repository '{repo_name}'")
    
    def get_project(self, project_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Get a project by name.
        
        Args:
            project_name: Name of the project (default: first project)
            
        Returns:
            Project information or None if not found
        """
        if not project_name:
            # Return the first project if no name is specified
            if self.projects:
                return next(iter(self.projects.values()))
            return None
        
        return self.projects.get(project_name)
    
    def start(self):
        """Start the Slack integration and agent processing."""
        if self.running:
            logger.warning("Slack integration is already running.")
            return
        
        self.running = True
        
        # Start the Assistant Agent
        self.assistant_agent.start()
        
        # Start message processing thread
        self.thread = threading.Thread(
            target=self._message_processing_thread,
            name="SlackMessageProcessor",
            daemon=True
        )
        self.thread.start()
        
        logger.info("Slack integration started.")
    
    def stop(self):
        """Stop the Slack integration and agent processing."""
        self.running = False
        
        # Stop the Assistant Agent
        self.assistant_agent.stop()
        
        # Wait for message thread to finish
        if self.thread:
            self.thread.join(timeout=5.0)
        
        self.thread = None
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
            
            # Check if this is a project management request
            if re.search(r"\b(add|create|register)\s+project\b", text, re.IGNORECASE):
                await self._handle_project_management(channel_id, thread_ts, text)
                return
            
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
            
            # Check if this is an implementation phases request
            if re.search(r"\b(proceed|execute|run|start)\s+(with|the)?\s*implementation\s+phases\b", text, re.IGNORECASE):
                await self._handle_implementation_phases(channel_id, thread_ts, text)
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
                     "- Add a project\n"
                     "- Initialize a project\n"
                     "- Implement a feature or task\n"
                     "- Analyze the project state\n"
                     "- Check the status of a task\n"
                     "- Proceed with implementation phases",
                thread_ts=thread_ts
            )
        
        except Exception as e:
            logger.error(f"Error handling app mention: {str(e)}", exc_info=True)
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"An error occurred while processing your request: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def _handle_project_management(self, channel_id: str, thread_ts: str, text: str):
        """
        Handle project management requests.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            text: Message text
        """
        # Extract project name and repository URL
        project_match = re.search(r"\b(project|name)[:\s]+([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        repo_match = re.search(r"\b(repo|repository|url)[:\s]+(https?://[^\s]+|[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        
        if not project_match or not repo_match:
            await self._send_slack_message(
                channel_id=channel_id,
                text="Please provide both a project name and repository URL/name.\n"
                     "Example: `@bot add project name:myproject repo:owner/repo`",
                thread_ts=thread_ts
            )
            return
        
        project_name = project_match.group(2)
        repo_url = repo_match.group(2)
        
        # Add the project
        self.add_project(project_name, repo_url)
        
        await self._send_slack_message(
            channel_id=channel_id,
            text=f"Project '{project_name}' added successfully with repository '{repo_url}'.",
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
        # Extract project name if specified
        project_match = re.search(r"\b(project|name)[:\s]+([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        project_name = project_match.group(2) if project_match else None
        
        # Get the project
        project = self.get_project(project_name)
        if not project:
            if project_name:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text=f"Project '{project_name}' not found. Please add it first.",
                    thread_ts=thread_ts
                )
            else:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text="No projects found. Please add a project first.",
                    thread_ts=thread_ts
                )
            return
        
        await self._send_slack_message(
            channel_id=channel_id,
            text="Initializing project... This may take a few minutes.",
            thread_ts=thread_ts
        )
        
        try:
            # Set the repository for the AI User Agent
            self.ai_user_agent.set_repository(project["repo_name"])
            
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
    
    async def _handle_implementation_phases(self, channel_id: str, thread_ts: str, text: str):
        """
        Handle implementation phases requests.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            text: Message text
        """
        # Extract project name if specified
        project_match = re.search(r"\b(project|name)[:\s]+([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        project_name = project_match.group(2) if project_match else None
        
        # Get the project
        project = self.get_project(project_name)
        if not project:
            if project_name:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text=f"Project '{project_name}' not found. Please add it first.",
                    thread_ts=thread_ts
                )
            else:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text="No projects found. Please add a project first.",
                    thread_ts=thread_ts
                )
            return
        
        await self._send_slack_message(
            channel_id=channel_id,
            text="Proceeding with implementation phases... This may take some time.",
            thread_ts=thread_ts
        )
        
        try:
            # Import here to avoid circular imports
            from src.workflows.implementation_phases import ImplementationPhases
            
            # Create implementation phases instance
            implementation_phases = ImplementationPhases(
                ai_user_agent=self.ai_user_agent,
                assistant_agent=self.assistant_agent,
                project_dir=self.ai_user_agent.project_dir
            )
            
            # Execute all phases
            results = await implementation_phases.execute_all_phases(project["repo_name"])
            
            # Format the results for Slack
            message = "Implementation phases completed successfully! Here's a summary:\n\n"
            
            # Phase 1: Project Initialization
            message += "*Phase 1: Project Initialization*\n"
            implementation_plan = results.get("phase1_project_initialization", {})
            phases = implementation_plan.get("phases", [])
            message += f"- Created implementation plan with {len(phases)} phases\n\n"
            
            # Phase 2: Development Cycle
            message += "*Phase 2: Development Cycle*\n"
            task_results = results.get("phase2_development_cycle", [])
            completed_tasks = sum(1 for task in task_results if task.get("status") == "completed")
            failed_tasks = sum(1 for task in task_results if task.get("status") == "failed")
            message += f"- Processed {len(task_results)} tasks\n"
            message += f"- Completed: {completed_tasks}, Failed: {failed_tasks}\n\n"
            
            # Phase 3: Project Management
            message += "*Phase 3: Project Management*\n"
            management_report = results.get("phase3_project_management", {})
            metrics = management_report.get("metrics", {})
            completion_percentage = metrics.get("completion_percentage", 0)
            message += f"- Overall completion: {completion_percentage:.2f}%\n"
            message += f"- Total tasks: {metrics.get('total_tasks', 0)}\n\n"
            
            # Phase 4: Post-Merge Analysis
            message += "*Phase 4: Post-Merge Analysis*\n"
            analysis_results = results.get("phase4_post_merge_analysis", {})
            further_requests = analysis_results.get("further_requests", [])
            message += f"- Identified {len(further_requests)} further requests\n"
            
            # Add link to results file
            message += "\nDetailed results have been saved to implementation_phases_results.json"
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=message,
                thread_ts=thread_ts
            )
        
        except Exception as e:
            logger.error(f"Error executing implementation phases: {str(e)}", exc_info=True)
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"An error occurred during implementation phases: {str(e)}",
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
        # Extract task details
        task_match = re.search(r"\b(implement|add|create|develop)\s+(feature|task|component)\s+(.+?)(?:\s+for\s+project\s+([a-zA-Z0-9_-]+))?$", text, re.IGNORECASE)
        
        if not task_match:
            await self._send_slack_message(
                channel_id=channel_id,
                text="Please specify the task to implement.\n"
                     "Example: `@bot implement feature User Authentication`",
                thread_ts=thread_ts
            )
            return
        
        task_type = task_match.group(2)
        task_description = task_match.group(3).strip()
        project_name = task_match.group(4) if task_match.group(4) else None
        
        # Get the project
        project = self.get_project(project_name)
        if not project:
            if project_name:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text=f"Project '{project_name}' not found. Please add it first.",
                    thread_ts=thread_ts
                )
            else:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text="No projects found. Please add a project first.",
                    thread_ts=thread_ts
                )
            return
        
        # Generate a unique task ID
        task_id = f"{task_type.lower()}-{str(uuid.uuid4())[:8]}"
        
        await self._send_slack_message(
            channel_id=channel_id,
            text=f"Adding task '{task_description}' with ID '{task_id}'...",
            thread_ts=thread_ts
        )
        
        try:
            # Add the task to the assistant agent
            task = self.assistant_agent.add_task(
                task_id=task_id,
                description=f"Implement {task_type}: {task_description}",
                priority="medium"
            )
            
            # Store the task in the project
            project["tasks"][task_id] = {
                "description": task_description,
                "type": task_type,
                "status": task.status.value,
                "channel_id": channel_id,
                "thread_ts": thread_ts
            }
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"Task '{task_id}' added successfully. You can check its status with `@bot what's the status of task {task_id}?`",
                thread_ts=thread_ts
            )
        
        except Exception as e:
            logger.error(f"Error adding task: {str(e)}", exc_info=True)
            
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"An error occurred while adding the task: {str(e)}",
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
        # Extract project name if specified
        project_match = re.search(r"\b(project|name)[:\s]+([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        project_name = project_match.group(2) if project_match else None
        
        # Get the project
        project = self.get_project(project_name)
        if not project:
            if project_name:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text=f"Project '{project_name}' not found. Please add it first.",
                    thread_ts=thread_ts
                )
            else:
                await self._send_slack_message(
                    channel_id=channel_id,
                    text="No projects found. Please add a project first.",
                    thread_ts=thread_ts
                )
            return
        
        await self._send_slack_message(
            channel_id=channel_id,
            text="Analyzing project state... This may take a few minutes.",
            thread_ts=thread_ts
        )
        
        try:
            # Set the repository for the AI User Agent
            self.ai_user_agent.set_repository(project["repo_name"])
            
            # Analyze project state
            analysis = await self.ai_user_agent.compare_project_state()
            
            # Format the analysis for Slack
            message = "Project state analysis complete!\n\n"
            
            # Add completed tasks
            completed_tasks = analysis.get("completed", [])
            message += f"*Completed Tasks ({len(completed_tasks)}):*\n"
            for task_id in completed_tasks:
                message += f"- {task_id}\n"
            
            # Add partially implemented tasks
            partial_tasks = analysis.get("partial", [])
            message += f"\n*Partially Implemented Tasks ({len(partial_tasks)}):*\n"
            for task in partial_tasks:
                message += f"- {task.get('task_id')} (Progress: {task.get('progress')*100:.0f}%)\n"
                message += f"  Missing: {task.get('missing')}\n"
            
            # Add missing tasks
            missing_tasks = analysis.get("missing", [])
            message += f"\n*Missing Tasks ({len(missing_tasks)}):*\n"
            for task_id in missing_tasks:
                message += f"- {task_id}\n"
            
            # Add deviations
            deviations = analysis.get("deviations", [])
            message += f"\n*Deviations ({len(deviations)}):*\n"
            for deviation in deviations:
                message += f"- {deviation}\n"
            
            # Add next steps
            next_steps = analysis.get("next_steps", [])
            message += f"\n*Recommended Next Steps ({len(next_steps)}):*\n"
            for step in next_steps:
                message += f"- {step}\n"
            
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
        # Extract task ID
        task_match = re.search(r"\b(status|progress)\s+(of|for)\s+task\s+([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        
        if not task_match:
            await self._send_slack_message(
                channel_id=channel_id,
                text="Please specify the task ID.\n"
                     "Example: `@bot what's the status of task task-123?`",
                thread_ts=thread_ts
            )
            return
        
        task_id = task_match.group(3)
        
        # Get task status
        task_status = self.assistant_agent.get_task_status(task_id)
        
        if not task_status:
            await self._send_slack_message(
                channel_id=channel_id,
                text=f"Task '{task_id}' not found.",
                thread_ts=thread_ts
            )
            return
        
        # Format the task status for Slack
        message = f"*Status of Task '{task_id}':*\n"
        message += f"- Description: {task_status.get('description')}\n"
        message += f"- Status: {task_status.get('status')}\n"
        message += f"- Priority: {task_status.get('priority')}\n"
        
        # Add dependencies
        dependencies = task_status.get("dependencies", [])
        if dependencies:
            message += f"- Dependencies: {', '.join(dependencies)}\n"
        
        # Add branch name if available
        branch_name = task_status.get("branch_name")
        if branch_name:
            message += f"- Branch: {branch_name}\n"
        
        # Add error if available
        error = task_status.get("error")
        if error:
            message += f"- Error: {error}\n"
        
        # Add result if available
        result = task_status.get("result")
        if result:
            # Check if result has a pull request
            pr_info = result.get("pull_request", {})
            if pr_info:
                message += f"- Pull Request: {pr_info.get('pr_url')}\n"
            
            # Check if result has implementation details
            implementation_result = result.get("implementation_result", {})
            if implementation_result:
                message += f"- Implementation: {len(implementation_result.get('files', []))} files modified\n"
        
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