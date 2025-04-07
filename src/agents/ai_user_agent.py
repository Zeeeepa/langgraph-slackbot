import os
import re
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any, Optional
import markdown
from bs4 import BeautifulSoup
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

class AIUserAgent:
    """
    AI User Agent that analyzes project requirements, creates implementation plans,
    and sends requests to the Assistant Agent via Slack.
    """
    
    def __init__(self, 
                 project_dir: str = ".",
                 github_token: Optional[str] = None,
                 repo_name: Optional[str] = None,
                 model_name: str = "gpt-4o-mini"):
        """
        Initialize the AI User Agent.
        
        Args:
            project_dir: Directory containing project files and requirements
            github_token: GitHub API token for repository access
            repo_name: GitHub repository name (format: "owner/repo")
            model_name: LLM model to use for analysis and planning
        """
        self.project_dir = Path(project_dir)
        self.model_name = model_name
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # GitHub integration
        self.github_token = github_token
        self.github_client = None
        self.repo = None
        
        if github_token and repo_name:
            self.set_repository(repo_name)
    
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
    
    async def initialize_project(self):
        """Initialize the project by analyzing requirements and creating an implementation plan."""
        logger.info("Initializing project...")
        
        # Find all markdown requirement documents
        requirement_docs = await self._find_requirement_documents()
        if not requirement_docs:
            logger.warning("No requirement documents found.")
            return
        
        # Analyze requirements
        requirements = await self._analyze_requirements(requirement_docs)
        
        # Create implementation plan
        implementation_plan = await self._create_implementation_plan(requirements)
        
        # Save implementation plan
        await self._save_implementation_plan(implementation_plan)
        
        logger.info("Project initialization complete.")
        return implementation_plan
    
    async def _find_requirement_documents(self) -> List[Path]:
        """Find all markdown requirement documents in the project directory."""
        md_files = list(self.project_dir.glob("**/*.md"))
        # Filter out non-requirement documents (implementation details, etc.)
        requirement_docs = []
        
        for file_path in md_files:
            # Skip the PROJECT.md file itself
            if file_path.name == "PROJECT.md":
                continue
                
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Simple heuristic: if the document contains words like "requirement", "feature", "user story"
            if re.search(r"\b(requirement|feature|user story|specification)\b", content, re.IGNORECASE):
                requirement_docs.append(file_path)
        
        logger.info(f"Found {len(requirement_docs)} requirement documents.")
        return requirement_docs
    
    async def _analyze_requirements(self, requirement_docs: List[Path]) -> Dict[str, Any]:
        """
        Analyze requirement documents to extract structured requirements.
        
        Args:
            requirement_docs: List of paths to requirement documents
            
        Returns:
            Structured requirements as a dictionary
        """
        combined_content = ""
        
        for doc_path in requirement_docs:
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Convert markdown to plain text
            html = markdown.markdown(content)
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text()
            
            combined_content += f"\n\n--- Document: {doc_path.name} ---\n\n{text}"
        
        # Create a prompt for requirement analysis
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert requirements analyst. Extract structured requirements from the provided documents.
            Identify:
            1. Functional requirements
            2. Technical requirements
            3. User interface requirements
            4. Integration requirements
            5. Performance requirements
            
            Format your response as a JSON object with these categories as keys, and lists of specific requirements as values.
            """),
            ("human", "{content}")
        ])
        
        # Create a chain for requirement analysis
        analysis_chain = analysis_prompt | self.llm | JsonOutputParser()
        
        # Extract requirements
        requirements = await analysis_chain.ainvoke({"content": combined_content})
        
        logger.info("Requirements analysis complete.")
        return requirements
    
    async def _create_implementation_plan(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a multi-threaded implementation plan based on the analyzed requirements.
        
        Args:
            requirements: Structured requirements dictionary
            
        Returns:
            Implementation plan as a dictionary
        """
        # Create a prompt for implementation planning
        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert software architect specializing in multi-threaded applications.
            Create a detailed implementation plan for a multi-agent system with the following components:
            
            1. AI User Agent - Analyzes requirements and sends requests to the Assistant Agent
            2. Assistant Agent - Processes requests and implements solutions
            
            The implementation should support:
            - Multi-threading for concurrent request handling
            - GitHub branch management for feature isolation
            - Document processing for requirement analysis
            
            Format your response as a JSON object with the following structure:
            {
                "phases": [
                    {
                        "name": "Phase name",
                        "description": "Phase description",
                        "tasks": [
                            {
                                "name": "Task name",
                                "description": "Task description",
                                "priority": "high|medium|low",
                                "dependencies": ["task_id1", "task_id2"],
                                "estimated_effort": "hours"
                            }
                        ]
                    }
                ],
                "components": [
                    {
                        "name": "Component name",
                        "description": "Component description",
                        "files": [
                            {
                                "path": "file/path.py",
                                "purpose": "File purpose"
                            }
                        ]
                    }
                ]
            }
            """),
            ("human", "Requirements: {requirements}")
        ])
        
        # Create a chain for implementation planning
        planning_chain = planning_prompt | self.llm | JsonOutputParser()
        
        # Create implementation plan
        implementation_plan = await planning_chain.ainvoke({"requirements": json.dumps(requirements)})
        
        logger.info("Implementation plan created.")
        return implementation_plan
    
    async def _save_implementation_plan(self, implementation_plan: Dict[str, Any]):
        """Save the implementation plan to a file."""
        plan_path = self.project_dir / "implementation_plan.json"
        
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(implementation_plan, f, indent=2)
        
        logger.info(f"Implementation plan saved to {plan_path}")
    
    async def formulate_assistant_request(self, task_id: str) -> str:
        """
        Formulate a request to send to the Assistant Agent based on a specific task.
        
        Args:
            task_id: ID of the task to implement
            
        Returns:
            Formatted request message
        """
        # Load implementation plan
        plan_path = self.project_dir / "implementation_plan.json"
        if not plan_path.exists():
            logger.error("Implementation plan not found. Run initialize_project first.")
            return ""
        
        with open(plan_path, "r", encoding="utf-8") as f:
            implementation_plan = json.load(f)
        
        # Find the task in the implementation plan
        task = None
        for phase in implementation_plan.get("phases", []):
            for t in phase.get("tasks", []):
                if t.get("id") == task_id or t.get("name") == task_id:
                    task = t
                    break
            if task:
                break
        
        if not task:
            logger.error(f"Task {task_id} not found in implementation plan.")
            return ""
        
        # Create a prompt for request formulation
        request_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the AI User Agent formulating a request to the Assistant Agent.
            Create a clear, detailed request that specifies:
            1. The task to be implemented
            2. Technical requirements and constraints
            3. Expected deliverables
            4. Any dependencies or prerequisites
            
            Format the request in a way that is easy for the Assistant Agent to understand and implement.
            """),
            ("human", "Task: {task}")
        ])
        
        # Create a chain for request formulation
        request_chain = request_prompt | self.llm | StrOutputParser()
        
        # Formulate request
        request = await request_chain.ainvoke({"task": json.dumps(task)})
        
        logger.info(f"Request formulated for task {task_id}.")
        return request
    
    async def compare_project_state(self) -> Dict[str, Any]:
        """
        Compare the current project state with requirements after a merge.
        
        Returns:
            Analysis of project state and remaining work
        """
        if not self.repo:
            logger.error("GitHub repository not configured.")
            return {}
        
        # Load implementation plan
        plan_path = self.project_dir / "implementation_plan.json"
        if not plan_path.exists():
            logger.error("Implementation plan not found. Run initialize_project first.")
            return {}
        
        with open(plan_path, "r", encoding="utf-8") as f:
            implementation_plan = json.load(f)
        
        # Get current project files
        project_files = []
        for root, _, files in os.walk(self.project_dir):
            for file in files:
                if file.endswith((".py", ".md", ".json")):
                    rel_path = os.path.relpath(os.path.join(root, file), self.project_dir)
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        content = f.read()
                    project_files.append({"path": rel_path, "content": content})
        
        # Create a prompt for project state analysis
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert software analyst comparing the current project state with the implementation plan.
            Identify:
            1. Completed tasks and components
            2. Partially implemented features
            3. Missing or incomplete implementations
            4. Any deviations from the plan
            
            Format your response as a JSON object with the following structure:
            {
                "completed": ["task_id1", "task_id2"],
                "partial": [{"task_id": "task_id3", "progress": 0.5, "missing": "description"}],
                "missing": ["task_id4", "task_id5"],
                "deviations": ["description of deviation"],
                "next_steps": ["recommended next step 1", "recommended next step 2"]
            }
            """),
            ("human", "Implementation Plan: {plan}\n\nProject Files: {files}")
        ])
        
        # Create a chain for project state analysis
        analysis_chain = analysis_prompt | self.llm | JsonOutputParser()
        
        # Analyze project state
        analysis = await analysis_chain.ainvoke({
            "plan": json.dumps(implementation_plan),
            "files": json.dumps(project_files)
        })
        
        logger.info("Project state analysis complete.")
        return analysis
    
    async def formulate_further_requests(self, analysis: Dict[str, Any]) -> List[str]:
        """
        Formulate further requests based on project state analysis.
        
        Args:
            analysis: Analysis of project state and remaining work
            
        Returns:
            List of formatted request messages
        """
        # Create a prompt for further request formulation
        request_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the AI User Agent formulating further requests to the Assistant Agent based on project state analysis.
            For each missing or partially implemented task, create a clear, detailed request that specifies:
            1. The task to be implemented or completed
            2. Technical requirements and constraints
            3. Expected deliverables
            4. Any dependencies or prerequisites
            
            Format each request in a way that is easy for the Assistant Agent to understand and implement.
            """),
            ("human", "Project State Analysis: {analysis}")
        ])
        
        # Create a chain for further request formulation
        request_chain = request_prompt | self.llm | StrOutputParser()
        
        # Formulate further requests
        requests_text = await request_chain.ainvoke({"analysis": json.dumps(analysis)})
        
        # Split the text into individual requests
        requests = [req.strip() for req in requests_text.split("---") if req.strip()]
        
        logger.info(f"Formulated {len(requests)} further requests.")
        return requests