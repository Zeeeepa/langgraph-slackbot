import os
import re
import json
import logging
import asyncio
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Tuple, Callable
from enum import Enum
import github
from github import Github
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """Priority levels for tasks."""
    HIGH = 3
    MEDIUM = 2
    LOW = 1

class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task:
    """Represents a task to be processed by the Assistant Agent."""
    
    def __init__(self, 
                 task_id: str,
                 description: str,
                 priority: TaskPriority = TaskPriority.MEDIUM,
                 dependencies: List[str] = None):
        """
        Initialize a task.
        
        Args:
            task_id: Unique identifier for the task
            description: Description of the task
            priority: Priority level of the task
            dependencies: List of task IDs that this task depends on
        """
        self.task_id = task_id
        self.description = description
        self.priority = priority
        self.dependencies = dependencies or []
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.branch_name = None
    
    def __lt__(self, other):
        """Compare tasks based on priority for the priority queue."""
        if not isinstance(other, Task):
            return NotImplemented
        return self.priority.value > other.priority.value

class AssistantAgent:
    """
    Assistant Agent that processes requests from the AI User Agent,
    implements solutions, and manages GitHub branches.
    """
    
    def __init__(self, 
                 github_token: Optional[str] = None,
                 repo_name: Optional[str] = None,
                 model_name: str = "gpt-4o-mini",
                 max_workers: int = 5):
        """
        Initialize the Assistant Agent.
        
        Args:
            github_token: GitHub API token for repository access
            repo_name: GitHub repository name (format: "owner/repo")
            model_name: LLM model to use for implementation
            max_workers: Maximum number of worker threads
        """
        self.model_name = model_name
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.max_workers = max_workers
        
        # GitHub integration
        self.github_token = github_token
        self.github_client = None
        self.repo = None
        
        if github_token and repo_name:
            self.set_repository(repo_name)
        
        # Task queue and processing
        self.task_queue = queue.PriorityQueue()
        self.tasks = {}  # task_id -> Task
        self.task_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.workers = []
        self.running = False
    
    def set_repository(self, repo_name: str):
        """
        Set the GitHub repository for the agent.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
        """
        if not self.github_token:
            logger.error("GitHub token not configured.")
            return False
        
        try:
            self.github_client = Github(self.github_token)
            self.repo = self.github_client.get_repo(repo_name)
            logger.info(f"Set repository to {repo_name}")
            return True
        except Exception as e:
            logger.error(f"Error setting repository: {str(e)}")
            return False
    
    def start(self):
        """Start the Assistant Agent's worker threads."""
        if self.running:
            logger.warning("Assistant Agent is already running.")
            return
        
        self.running = True
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_thread,
                name=f"AssistantWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started {self.max_workers} worker threads.")
    
    def stop(self):
        """Stop the Assistant Agent's worker threads."""
        self.running = False
        
        # Add sentinel tasks to unblock workers
        for _ in range(self.max_workers):
            self.task_queue.put(None)
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5.0)
        
        self.workers = []
        logger.info("Stopped all worker threads.")
    
    def _worker_thread(self):
        """Worker thread function to process tasks from the queue."""
        while self.running:
            try:
                # Get a task from the queue
                task_item = self.task_queue.get(timeout=1.0)
                
                # Check for sentinel value
                if task_item is None:
                    self.task_queue.task_done()
                    break
                
                # Process the task
                task = task_item
                
                # Update task status
                with self.task_lock:
                    task.status = TaskStatus.IN_PROGRESS
                
                try:
                    # Process the task
                    result = asyncio.run(self._process_task(task))
                    
                    # Update task with result
                    with self.task_lock:
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                    
                    logger.info(f"Task {task.task_id} completed successfully.")
                
                except Exception as e:
                    # Update task with error
                    with self.task_lock:
                        task.error = str(e)
                        task.status = TaskStatus.FAILED
                    
                    logger.error(f"Error processing task {task.task_id}: {str(e)}", exc_info=True)
                
                finally:
                    # Mark task as done in the queue
                    self.task_queue.task_done()
            
            except queue.Empty:
                # No tasks in the queue, continue waiting
                continue
            
            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}", exc_info=True)
    
    async def _process_task(self, task: Task) -> Dict[str, Any]:
        """
        Process a task.
        
        Args:
            task: Task to process
            
        Returns:
            Result of the task processing
        """
        logger.info(f"Processing task {task.task_id}: {task.description}")
        
        # Parse the task description to determine the type of task
        task_type = await self._determine_task_type(task.description)
        
        if task_type == "implementation":
            # Create a branch for the implementation
            branch_name = await self._create_branch(task.task_id)
            task.branch_name = branch_name
            
            # Implement the feature
            implementation_result = await self._implement_feature(task.description, branch_name)
            
            # Create a pull request
            pr_result = await self._create_pull_request(branch_name, task.description)
            
            return {
                "task_type": task_type,
                "branch_name": branch_name,
                "implementation_result": implementation_result,
                "pull_request": pr_result
            }
        
        elif task_type == "document_processing":
            # Process documents
            processing_result = await self._process_documents(task.description)
            
            return {
                "task_type": task_type,
                "processing_result": processing_result
            }
        
        elif task_type == "analysis":
            # Perform analysis
            analysis_result = await self._perform_analysis(task.description)
            
            return {
                "task_type": task_type,
                "analysis_result": analysis_result
            }
        
        else:
            # Generic task processing
            generic_result = await self._process_generic_task(task.description)
            
            return {
                "task_type": "generic",
                "result": generic_result
            }
    
    async def _determine_task_type(self, description: str) -> str:
        """
        Determine the type of task based on its description.
        
        Args:
            description: Task description
            
        Returns:
            Task type (implementation, document_processing, analysis, etc.)
        """
        # Create a prompt for task type determination
        type_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert task classifier. Determine the type of task based on its description.
            Task types:
            - implementation: Tasks that involve implementing features, writing code, or making changes to the codebase
            - document_processing: Tasks that involve processing, analyzing, or generating documents
            - analysis: Tasks that involve analyzing code, requirements, or project state
            - generic: Any other type of task
            
            Respond with only the task type, nothing else.
            """),
            ("human", "{description}")
        ])
        
        # Create a chain for task type determination
        type_chain = type_prompt | self.llm | StrOutputParser()
        
        # Determine task type
        task_type = await type_chain.ainvoke({"description": description})
        
        # Normalize the task type
        task_type = task_type.strip().lower()
        if task_type not in ["implementation", "document_processing", "analysis", "generic"]:
            task_type = "generic"
        
        logger.info(f"Determined task type: {task_type}")
        return task_type
    
    async def _create_branch(self, task_id: str) -> str:
        """
        Create a branch for implementing a feature.
        
        Args:
            task_id: Task ID to use in the branch name
            
        Returns:
            Name of the created branch
        """
        if not self.repo:
            logger.error("GitHub repository not configured.")
            raise ValueError("GitHub repository not configured.")
        
        # Generate a branch name
        branch_name = f"feature/{task_id.lower().replace(' ', '-')}-{os.urandom(4).hex()}"
        
        try:
            # Get the default branch
            default_branch = self.repo.default_branch
            
            # Get the reference to the default branch
            ref = self.repo.get_git_ref(f"heads/{default_branch}")
            
            # Create a new branch
            self.repo.create_git_ref(f"refs/heads/{branch_name}", ref.object.sha)
            
            logger.info(f"Created branch: {branch_name}")
            return branch_name
        
        except Exception as e:
            logger.error(f"Error creating branch: {str(e)}", exc_info=True)
            raise
    
    async def _implement_feature(self, description: str, branch_name: str) -> Dict[str, Any]:
        """
        Implement a feature based on the task description.
        
        Args:
            description: Task description
            branch_name: Branch to implement the feature on
            
        Returns:
            Result of the implementation
        """
        if not self.repo:
            logger.error("GitHub repository not configured.")
            raise ValueError("GitHub repository not configured.")
        
        # Create a prompt for implementation planning
        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert software engineer planning the implementation of a feature.
            Based on the task description, identify:
            1. Files that need to be created or modified
            2. Changes to be made to each file
            3. Tests to be added or updated
            
            Format your response as a JSON object with the following structure:
            {
                "files": [
                    {
                        "path": "file/path.py",
                        "action": "create|modify",
                        "content": "Full content for new files or changes to be made for existing files"
                    }
                ],
                "tests": [
                    {
                        "path": "tests/file_path_test.py",
                        "content": "Full content of the test file"
                    }
                ]
            }
            """),
            ("human", "Task Description: {description}")
        ])
        
        # Create a chain for implementation planning
        planning_chain = planning_prompt | self.llm | JsonOutputParser()
        
        # Plan the implementation
        implementation_plan = await planning_chain.ainvoke({"description": description})
        
        # Implement the changes
        implemented_files = []
        
        for file_info in implementation_plan.get("files", []):
            path = file_info.get("path")
            action = file_info.get("action")
            content = file_info.get("content")
            
            if not path or not action or not content:
                logger.warning(f"Incomplete file information: {file_info}")
                continue
            
            try:
                if action == "create":
                    # Create a new file
                    self.repo.create_file(
                        path=path,
                        message=f"Create {path} for {branch_name}",
                        content=content,
                        branch=branch_name
                    )
                    logger.info(f"Created file: {path}")
                
                elif action == "modify":
                    # Get the existing file
                    file = self.repo.get_contents(path, ref=branch_name)
                    
                    # Update the file
                    self.repo.update_file(
                        path=path,
                        message=f"Update {path} for {branch_name}",
                        content=content,
                        sha=file.sha,
                        branch=branch_name
                    )
                    logger.info(f"Updated file: {path}")
                
                implemented_files.append(path)
            
            except Exception as e:
                logger.error(f"Error implementing file {path}: {str(e)}", exc_info=True)
        
        # Implement tests
        for test_info in implementation_plan.get("tests", []):
            path = test_info.get("path")
            content = test_info.get("content")
            
            if not path or not content:
                logger.warning(f"Incomplete test information: {test_info}")
                continue
            
            try:
                # Check if the test file already exists
                try:
                    file = self.repo.get_contents(path, ref=branch_name)
                    
                    # Update the file
                    self.repo.update_file(
                        path=path,
                        message=f"Update test {path} for {branch_name}",
                        content=content,
                        sha=file.sha,
                        branch=branch_name
                    )
                    logger.info(f"Updated test file: {path}")
                
                except Exception:
                    # Create a new file
                    self.repo.create_file(
                        path=path,
                        message=f"Create test {path} for {branch_name}",
                        content=content,
                        branch=branch_name
                    )
                    logger.info(f"Created test file: {path}")
                
                implemented_files.append(path)
            
            except Exception as e:
                logger.error(f"Error implementing test {path}: {str(e)}", exc_info=True)
        
        return {
            "implemented_files": implemented_files,
            "implementation_plan": implementation_plan
        }
    
    async def _create_pull_request(self, branch_name: str, description: str) -> Dict[str, Any]:
        """
        Create a pull request for the implemented feature.
        
        Args:
            branch_name: Branch containing the implementation
            description: Task description
            
        Returns:
            Pull request information
        """
        if not self.repo:
            logger.error("GitHub repository not configured.")
            raise ValueError("GitHub repository not configured.")
        
        # Create a prompt for PR title and body
        pr_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert software engineer creating a pull request.
            Based on the task description, create a clear, concise title and a detailed body for the pull request.
            
            Format your response as a JSON object with the following structure:
            {
                "title": "PR title",
                "body": "PR body with detailed description of changes"
            }
            """),
            ("human", "Task Description: {description}")
        ])
        
        # Create a chain for PR title and body
        pr_chain = pr_prompt | self.llm | JsonOutputParser()
        
        # Generate PR title and body
        pr_info = await pr_chain.ainvoke({"description": description})
        
        try:
            # Create the pull request
            pr = self.repo.create_pull(
                title=pr_info.get("title"),
                body=pr_info.get("body"),
                head=branch_name,
                base=self.repo.default_branch
            )
            
            logger.info(f"Created pull request: {pr.html_url}")
            
            return {
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "title": pr.title,
                "body": pr.body
            }
        
        except Exception as e:
            logger.error(f"Error creating pull request: {str(e)}", exc_info=True)
            raise
    
    async def _process_documents(self, description: str) -> Dict[str, Any]:
        """
        Process documents based on the task description.
        
        Args:
            description: Task description
            
        Returns:
            Result of document processing
        """
        # Create a prompt for document processing
        processing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert document processor.
            Based on the task description, process the documents and generate the required output.
            
            Format your response as a JSON object with the following structure:
            {
                "processed_documents": [
                    {
                        "name": "Document name",
                        "content": "Processed content"
                    }
                ],
                "summary": "Summary of the processing results"
            }
            """),
            ("human", "Task Description: {description}")
        ])
        
        # Create a chain for document processing
        processing_chain = processing_prompt | self.llm | JsonOutputParser()
        
        # Process documents
        processing_result = await processing_chain.ainvoke({"description": description})
        
        logger.info(f"Processed documents: {len(processing_result.get('processed_documents', []))}")
        return processing_result
    
    async def _perform_analysis(self, description: str) -> Dict[str, Any]:
        """
        Perform analysis based on the task description.
        
        Args:
            description: Task description
            
        Returns:
            Result of the analysis
        """
        # Create a prompt for analysis
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert software analyst.
            Based on the task description, perform the required analysis and generate insights.
            
            Format your response as a JSON object with the following structure:
            {
                "analysis_type": "Type of analysis performed",
                "findings": [
                    "Finding 1",
                    "Finding 2"
                ],
                "recommendations": [
                    "Recommendation 1",
                    "Recommendation 2"
                ]
            }
            """),
            ("human", "Task Description: {description}")
        ])
        
        # Create a chain for analysis
        analysis_chain = analysis_prompt | self.llm | JsonOutputParser()
        
        # Perform analysis
        analysis_result = await analysis_chain.ainvoke({"description": description})
        
        logger.info(f"Performed analysis: {analysis_result.get('analysis_type')}")
        return analysis_result
    
    async def _process_generic_task(self, description: str) -> str:
        """
        Process a generic task based on the description.
        
        Args:
            description: Task description
            
        Returns:
            Result of the task processing
        """
        # Create a prompt for generic task processing
        task_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert assistant processing a task.
            Based on the task description, provide a detailed response addressing the requirements.
            """),
            ("human", "Task Description: {description}")
        ])
        
        # Create a chain for generic task processing
        task_chain = task_prompt | self.llm | StrOutputParser()
        
        # Process the task
        result = await task_chain.ainvoke({"description": description})
        
        logger.info("Processed generic task.")
        return result
    
    def add_task(self, task_id: str, description: str, priority: str = "medium", dependencies: List[str] = None) -> Task:
        """
        Add a task to the queue.
        
        Args:
            task_id: Unique identifier for the task
            description: Description of the task
            priority: Priority level of the task (high, medium, low)
            dependencies: List of task IDs that this task depends on
            
        Returns:
            The created task
        """
        # Convert priority string to enum
        priority_enum = TaskPriority.MEDIUM
        if priority.lower() == "high":
            priority_enum = TaskPriority.HIGH
        elif priority.lower() == "low":
            priority_enum = TaskPriority.LOW
        
        # Create the task
        task = Task(
            task_id=task_id,
            description=description,
            priority=priority_enum,
            dependencies=dependencies
        )
        
        # Store the task
        with self.task_lock:
            self.tasks[task_id] = task
        
        # Check if all dependencies are satisfied
        can_queue = True
        if dependencies:
            for dep_id in dependencies:
                if dep_id not in self.tasks or self.tasks[dep_id].status != TaskStatus.COMPLETED:
                    can_queue = False
                    break
        
        # Add to queue if dependencies are satisfied
        if can_queue:
            self.task_queue.put(task)
            logger.info(f"Added task {task_id} to queue with priority {priority}.")
        else:
            logger.info(f"Task {task_id} waiting for dependencies.")
        
        return task
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task status information or None if the task doesn't exist
        """
        with self.task_lock:
            task = self.tasks.get(task_id)
            
            if not task:
                return None
            
            return {
                "task_id": task.task_id,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.name,
                "dependencies": task.dependencies,
                "branch_name": task.branch_name,
                "result": task.result,
                "error": task.error
            }
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Get the status of all tasks.
        
        Returns:
            List of task status information
        """
        with self.task_lock:
            return [
                {
                    "task_id": task.task_id,
                    "description": task.description,
                    "status": task.status.value,
                    "priority": task.priority.name,
                    "dependencies": task.dependencies,
                    "branch_name": task.branch_name,
                    "result": task.result is not None,
                    "error": task.error
                }
                for task in self.tasks.values()
            ]
    
    def check_dependencies(self):
        """Check for tasks with satisfied dependencies and add them to the queue."""
        with self.task_lock:
            for task_id, task in self.tasks.items():
                if task.status == TaskStatus.PENDING:
                    # Check if all dependencies are satisfied
                    can_queue = True
                    for dep_id in task.dependencies:
                        if dep_id not in self.tasks or self.tasks[dep_id].status != TaskStatus.COMPLETED:
                            can_queue = False
                            break
                    
                    # Add to queue if dependencies are satisfied
                    if can_queue:
                        self.task_queue.put(task)
                        logger.info(f"Added task {task_id} to queue after dependencies were satisfied.")