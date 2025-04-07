"""
GitHub integration for the Multi-Threaded Agentic Slackbot.

This module provides GitHub repository integration functionality:
- Repository management
- Branch operations
- Pull request handling
- Commit operations
"""

import os
import logging
from typing import Dict, Any, List, Optional
from github import Github
from github.Repository import Repository
from github.Branch import Branch
from github.PullRequest import PullRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class GitHubIntegration:
    """
    GitHub integration for repository operations.
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the GitHub integration.
        
        Args:
            github_token: GitHub API token for repository access
        """
        self.github_token = github_token
        self.github_client = Github(github_token) if github_token else None
        self.repositories = {}
        
    def set_repository(self, repo_name: str) -> Optional[Repository]:
        """
        Set the active repository.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            
        Returns:
            Repository object or None if not found
        """
        if not self.github_client:
            logger.error("GitHub client not initialized. Please provide a GitHub token.")
            return None
        
        try:
            repo = self.github_client.get_repo(repo_name)
            self.repositories[repo_name] = repo
            logger.info(f"Set active repository: {repo_name}")
            return repo
        
        except Exception as e:
            logger.error(f"Error setting repository {repo_name}: {str(e)}")
            return None
    
    def get_repository(self, repo_name: Optional[str] = None) -> Optional[Repository]:
        """
        Get a repository by name.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            
        Returns:
            Repository object or None if not found
        """
        if not repo_name and self.repositories:
            # Return the first repository if no name is specified
            return next(iter(self.repositories.values()))
        
        if repo_name in self.repositories:
            return self.repositories[repo_name]
        
        # Try to set the repository if not already cached
        return self.set_repository(repo_name)
    
    def create_branch(self, repo_name: str, branch_name: str, base_branch: Optional[str] = None) -> Optional[Branch]:
        """
        Create a new branch in the repository.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            branch_name: Name for the new branch
            base_branch: Base branch to create from (default: repository default branch)
            
        Returns:
            Branch object or None if creation failed
        """
        repo = self.get_repository(repo_name)
        if not repo:
            return None
        
        try:
            # Get the base branch
            if not base_branch:
                base_branch = repo.default_branch
            
            base = repo.get_branch(base_branch)
            
            # Create the new branch
            repo.create_git_ref(f"refs/heads/{branch_name}", base.commit.sha)
            
            # Get and return the new branch
            new_branch = repo.get_branch(branch_name)
            logger.info(f"Created branch {branch_name} in repository {repo_name}")
            return new_branch
        
        except Exception as e:
            logger.error(f"Error creating branch {branch_name} in repository {repo_name}: {str(e)}")
            return None
    
    def create_pull_request(self, repo_name: str, title: str, body: str, head_branch: str, base_branch: Optional[str] = None) -> Optional[PullRequest]:
        """
        Create a pull request in the repository.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            title: Title for the pull request
            body: Description for the pull request
            head_branch: Source branch for the pull request
            base_branch: Target branch for the pull request (default: repository default branch)
            
        Returns:
            PullRequest object or None if creation failed
        """
        repo = self.get_repository(repo_name)
        if not repo:
            return None
        
        try:
            # Get the base branch if not specified
            if not base_branch:
                base_branch = repo.default_branch
            
            # Create the pull request
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            logger.info(f"Created pull request #{pr.number} in repository {repo_name}")
            return pr
        
        except Exception as e:
            logger.error(f"Error creating pull request in repository {repo_name}: {str(e)}")
            return None
    
    def get_pull_requests(self, repo_name: str, state: str = "open") -> List[PullRequest]:
        """
        Get pull requests from the repository.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            state: State of pull requests to get (open, closed, all)
            
        Returns:
            List of PullRequest objects
        """
        repo = self.get_repository(repo_name)
        if not repo:
            return []
        
        try:
            # Get pull requests
            pulls = list(repo.get_pulls(state=state))
            logger.info(f"Retrieved {len(pulls)} {state} pull requests from repository {repo_name}")
            return pulls
        
        except Exception as e:
            logger.error(f"Error getting pull requests from repository {repo_name}: {str(e)}")
            return []
    
    def merge_pull_request(self, repo_name: str, pr_number: int, commit_message: Optional[str] = None) -> bool:
        """
        Merge a pull request.
        
        Args:
            repo_name: GitHub repository name (format: "owner/repo")
            pr_number: Pull request number
            commit_message: Custom commit message for the merge
            
        Returns:
            True if merge was successful, False otherwise
        """
        repo = self.get_repository(repo_name)
        if not repo:
            return False
        
        try:
            # Get the pull request
            pr = repo.get_pull(pr_number)
            
            # Check if the pull request can be merged
            if not pr.mergeable:
                logger.error(f"Pull request #{pr_number} in repository {repo_name} cannot be merged")
                return False
            
            # Merge the pull request
            merge_result = pr.merge(
                commit_message=commit_message or f"Merge pull request #{pr_number}"
            )
            
            logger.info(f"Merged pull request #{pr_number} in repository {repo_name}")
            return merge_result.merged
        
        except Exception as e:
            logger.error(f"Error merging pull request #{pr_number} in repository {repo_name}: {str(e)}")
            return False