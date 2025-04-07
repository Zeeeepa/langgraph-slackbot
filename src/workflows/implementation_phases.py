"""
Implementation phases for the Multi-Threaded Agentic Slackbot.

This module defines the implementation phases for the project as described in PROJECT.md:
1. Project Initialization
2. Development Cycle
3. Project Management
4. Post-Merge Analysis

Each phase has specific methods and utilities to support its functionality.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.agents.ai_user_agent import AIUserAgent
from src.agents.assistant_agent import AssistantAgent, Task, TaskPriority

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class ImplementationPhases:
    """
    Implementation phases for the Multi-Threaded Agentic Slackbot.
    
    This class provides methods for executing each phase of the implementation
    as described in PROJECT.md.
    """
    
    def __init__(self, 
                 ai_user_agent: AIUserAgent,
                 assistant_agent: AssistantAgent,
                 project_dir: str = "."):
        """
        Initialize the implementation phases.
        
        Args:
            ai_user_agent: AI User Agent instance
            assistant_agent: Assistant Agent instance
            project_dir: Directory containing project files
        """
        self.ai_user_agent = ai_user_agent
        self.assistant_agent = assistant_agent
        self.project_dir = Path(project_dir)
        self.implementation_plan = None
        
    async def phase1_project_initialization(self, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute Phase 1: Project Initialization.
        
        This phase:
        - Analyzes requirements from .md documents
        - Creates an implementation plan
        - Establishes initial project structure
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            
        Returns:
            Implementation plan as a dictionary
        """
        logger.info("Starting Phase 1: Project Initialization")
        
        # Set repository if provided
        if repo_name:
            self.ai_user_agent.set_repository(repo_name)
        
        # Initialize the project
        implementation_plan = await self.ai_user_agent.initialize_project()
        self.implementation_plan = implementation_plan
        
        logger.info("Completed Phase 1: Project Initialization")
        return implementation_plan
    
    async def phase2_development_cycle(self, task_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Execute Phase 2: Development Cycle.
        
        This phase:
        - Formulates specific implementation requests
        - Processes requests in multi-threaded environment
        - Develops features in separate branches
        - Creates pull requests for completed features
        
        Args:
            task_ids: List of task IDs to implement (if None, uses all tasks from phase 1)
            
        Returns:
            List of task results
        """
        logger.info("Starting Phase 2: Development Cycle")
        
        # Load implementation plan if not already loaded
        if not self.implementation_plan:
            plan_path = self.project_dir / "implementation_plan.json"
            if not plan_path.exists():
                logger.error("Implementation plan not found. Run phase1_project_initialization first.")
                return []
            
            with open(plan_path, "r", encoding="utf-8") as f:
                self.implementation_plan = json.load(f)
        
        # Get tasks from implementation plan
        all_tasks = []
        for phase in self.implementation_plan.get("phases", []):
            all_tasks.extend(phase.get("tasks", []))
        
        # Filter tasks if task_ids is provided
        if task_ids:
            tasks_to_implement = [
                task for task in all_tasks 
                if task.get("id") == task_id or task.get("name") == task_id
                for task_id in task_ids
            ]
        else:
            tasks_to_implement = all_tasks
        
        # Formulate requests and add tasks to the assistant agent
        task_results = []
        for task in tasks_to_implement:
            # Formulate request
            request = await self.ai_user_agent.formulate_assistant_request(task.get("name"))
            
            # Add task to assistant agent
            priority = task.get("priority", "medium").lower()
            dependencies = task.get("dependencies", [])
            
            assistant_task = self.assistant_agent.add_task(
                task_id=task.get("name"),
                description=request,
                priority=priority,
                dependencies=dependencies
            )
            
            # Wait for task to complete
            while assistant_task.status.value != "completed" and assistant_task.status.value != "failed":
                await asyncio.sleep(1.0)
                self.assistant_agent.check_dependencies()
            
            # Get task result
            task_result = self.assistant_agent.get_task_status(task.get("name"))
            task_results.append(task_result)
        
        logger.info(f"Completed Phase 2: Development Cycle - {len(task_results)} tasks processed")
        return task_results
    
    async def phase3_project_management(self) -> Dict[str, Any]:
        """
        Execute Phase 3: Project Management.
        
        This phase:
        - Tracks progress across all development threads
        - Allocates resources based on priority and dependencies
        - Performs automated testing and validation
        - Generates documentation
        
        Returns:
            Project management status and metrics
        """
        logger.info("Starting Phase 3: Project Management")
        
        # Get all tasks
        all_tasks = self.assistant_agent.get_all_tasks()
        
        # Calculate metrics
        total_tasks = len(all_tasks)
        completed_tasks = sum(1 for task in all_tasks if task.get("status") == "completed")
        failed_tasks = sum(1 for task in all_tasks if task.get("status") == "failed")
        pending_tasks = sum(1 for task in all_tasks if task.get("status") == "pending")
        in_progress_tasks = sum(1 for task in all_tasks if task.get("status") == "in_progress")
        
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Group tasks by priority
        tasks_by_priority = {
            "high": [task for task in all_tasks if task.get("priority") == "HIGH"],
            "medium": [task for task in all_tasks if task.get("priority") == "MEDIUM"],
            "low": [task for task in all_tasks if task.get("priority") == "LOW"]
        }
        
        # Identify blocked tasks
        blocked_tasks = []
        for task in all_tasks:
            if task.get("status") == "pending" and task.get("dependencies"):
                for dep_id in task.get("dependencies"):
                    dep_task = next((t for t in all_tasks if t.get("task_id") == dep_id), None)
                    if dep_task and dep_task.get("status") != "completed":
                        blocked_tasks.append({
                            "task_id": task.get("task_id"),
                            "blocked_by": dep_id
                        })
                        break
        
        # Generate project management report
        report = {
            "metrics": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "pending_tasks": pending_tasks,
                "in_progress_tasks": in_progress_tasks,
                "completion_percentage": completion_percentage
            },
            "tasks_by_priority": tasks_by_priority,
            "blocked_tasks": blocked_tasks,
            "all_tasks": all_tasks
        }
        
        # Save report
        report_path = self.project_dir / "project_management_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Completed Phase 3: Project Management - {completion_percentage:.2f}% complete")
        return report
    
    async def phase4_post_merge_analysis(self) -> Dict[str, Any]:
        """
        Execute Phase 4: Post-Merge Analysis.
        
        This phase:
        - Compares project state with requirements after merges
        - Identifies gaps or additional requirements
        - Formulates new requests to address remaining work
        - Supports continuous improvement through iterative development
        
        Returns:
            Analysis results and further requests
        """
        logger.info("Starting Phase 4: Post-Merge Analysis")
        
        # Compare project state with requirements
        analysis = await self.ai_user_agent.compare_project_state()
        
        # Formulate further requests
        further_requests = await self.ai_user_agent.formulate_further_requests(analysis)
        
        # Save analysis and further requests
        analysis_path = self.project_dir / "post_merge_analysis.json"
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump({
                "analysis": analysis,
                "further_requests": further_requests
            }, f, indent=2)
        
        logger.info(f"Completed Phase 4: Post-Merge Analysis - {len(further_requests)} further requests identified")
        return {
            "analysis": analysis,
            "further_requests": further_requests
        }
    
    async def execute_all_phases(self, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute all implementation phases in sequence.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            
        Returns:
            Results from all phases
        """
        logger.info("Starting execution of all implementation phases")
        
        # Phase 1: Project Initialization
        implementation_plan = await self.phase1_project_initialization(repo_name)
        
        # Phase 2: Development Cycle
        task_results = await self.phase2_development_cycle()
        
        # Phase 3: Project Management
        management_report = await self.phase3_project_management()
        
        # Phase 4: Post-Merge Analysis
        analysis_results = await self.phase4_post_merge_analysis()
        
        # Compile results
        results = {
            "phase1_project_initialization": implementation_plan,
            "phase2_development_cycle": task_results,
            "phase3_project_management": management_report,
            "phase4_post_merge_analysis": analysis_results
        }
        
        # Save overall results
        results_path = self.project_dir / "implementation_phases_results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        
        logger.info("Completed execution of all implementation phases")
        return results