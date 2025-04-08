"""
LangGraph workflow implementation for the Multi-Threaded Agentic Slackbot.

This module defines the LangGraph-based workflows that enhance the interconnectivity
between components and provide better state management.
"""

import os
import json
import logging
from typing import Dict, Any, List, Tuple, Optional, TypedDict, Annotated
from enum import Enum
import operator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation

from src.agents.ai_user_agent import AIUserAgent
from src.agents.assistant_agent import AssistantAgent
from src.tools import all_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State for the agent workflow."""
    messages: List[Any]  # List of messages
    sender: str  # Who sent the last message
    task_id: Optional[str]  # Current task ID
    task_status: Optional[str]  # Status of the current task
    project_name: Optional[str]  # Current project name
    repo_name: Optional[str]  # Current repository name
    error: Optional[str]  # Error message if any
    tools_output: Optional[Dict[str, Any]]  # Output from tools

class AgentType(str, Enum):
    """Types of agents in the workflow."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class LangGraphWorkflow:
    """
    LangGraph-based workflow for the Multi-Threaded Agentic Slackbot.
    
    This class provides a graph-based workflow that enhances the interconnectivity
    between components and provides better state management.
    """
    
    def __init__(self, 
                 ai_user_agent: AIUserAgent,
                 assistant_agent: AssistantAgent,
                 model_name: str = "gpt-4o-mini"):
        """
        Initialize the LangGraph workflow.
        
        Args:
            ai_user_agent: AI User Agent instance
            assistant_agent: Assistant Agent instance
            model_name: LLM model to use
        """
        self.ai_user_agent = ai_user_agent
        self.assistant_agent = assistant_agent
        self.model_name = model_name
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        
        # Initialize tools
        self.tools = all_tools
        self.tool_executor = ToolExecutor(self.tools)
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """
        Build the workflow graph.
        
        Returns:
            StateGraph: The workflow graph
        """
        # Define the workflow graph
        workflow = StateGraph(AgentState)
        
        # Add nodes to the graph
        workflow.add_node("user_agent", self._user_agent_node)
        workflow.add_node("assistant_agent", self._assistant_agent_node)
        workflow.add_node("tool_execution", self._tool_execution_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Define the edges
        workflow.add_edge("user_agent", "assistant_agent")
        workflow.add_conditional_edges(
            "assistant_agent",
            self._route_assistant_output,
            {
                "tool": "tool_execution",
                "end": END,
                "error": "error_handler"
            }
        )
        workflow.add_conditional_edges(
            "tool_execution",
            self._route_tool_output,
            {
                "assistant": "assistant_agent",
                "error": "error_handler"
            }
        )
        workflow.add_edge("error_handler", "assistant_agent")
        
        # Set the entry point
        workflow.set_entry_point("user_agent")
        
        return workflow.compile()
    
    async def _user_agent_node(self, state: AgentState) -> AgentState:
        """
        Process user input and update state.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        # Extract the last message
        last_message = state["messages"][-1] if state["messages"] else None
        
        if not last_message or not isinstance(last_message, HumanMessage):
            # No message or not from human, return state unchanged
            return state
        
        try:
            # Process the message with the AI User Agent
            content = last_message.content
            
            # Check if this is a project management request
            if "add project" in content.lower() or "create project" in content.lower():
                # Extract project details
                project_name = None
                repo_name = None
                
                # Simple extraction logic (can be enhanced)
                if "project:" in content:
                    project_name = content.split("project:")[1].split()[0].strip()
                if "repo:" in content:
                    repo_name = content.split("repo:")[1].split()[0].strip()
                
                if project_name and repo_name:
                    state["project_name"] = project_name
                    state["repo_name"] = repo_name
            
            # Add a system message indicating the user agent processed the message
            state["messages"].append(
                SystemMessage(
                    content=f"User message processed by AI User Agent: {content[:50]}..."
                )
            )
            
            # Update sender
            state["sender"] = AgentType.SYSTEM
            
            return state
        
        except Exception as e:
            logger.error(f"Error in user agent node: {str(e)}", exc_info=True)
            state["error"] = str(e)
            return state
    
    async def _assistant_agent_node(self, state: AgentState) -> AgentState:
        """
        Process assistant agent logic and update state.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        try:
            # Get the conversation history
            messages = state["messages"]
            
            # Prepare the messages for the LLM
            llm_messages = []
            
            # Add system message
            llm_messages.append(
                SystemMessage(
                    content="""You are an AI assistant in a multi-threaded agentic slackbot.
                    You can help users with project management, task implementation, and analysis.
                    Use the available tools when needed to accomplish tasks.
                    """
                )
            )
            
            # Add conversation history
            for msg in messages:
                llm_messages.append(msg)
            
            # Get response from LLM
            response = await self.llm.ainvoke(llm_messages)
            
            # Check if the response contains a tool call
            if hasattr(response, "tool_calls") and response.tool_calls:
                # Extract tool calls
                tool_calls = response.tool_calls
                
                # Add the assistant's message to the state
                state["messages"].append(AIMessage(content=response.content))
                
                # Prepare tool invocations
                tool_invocations = []
                for tool_call in tool_calls:
                    tool_invocations.append(
                        ToolInvocation(
                            tool=tool_call.name,
                            tool_input=tool_call.args
                        )
                    )
                
                # Add tool invocations to state
                state["tools_output"] = {"invocations": tool_invocations}
                state["sender"] = AgentType.TOOL
                
                return state
            else:
                # No tool calls, just add the response to the state
                state["messages"].append(AIMessage(content=response.content))
                state["sender"] = AgentType.ASSISTANT
                
                return state
        
        except Exception as e:
            logger.error(f"Error in assistant agent node: {str(e)}", exc_info=True)
            state["error"] = str(e)
            state["sender"] = AgentType.SYSTEM
            return state
    
    async def _tool_execution_node(self, state: AgentState) -> AgentState:
        """
        Execute tools and update state.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        try:
            # Get tool invocations
            tool_invocations = state["tools_output"].get("invocations", [])
            
            if not tool_invocations:
                # No tool invocations, return state unchanged
                return state
            
            # Execute tools
            tool_results = []
            for invocation in tool_invocations:
                result = await self.tool_executor.ainvoke(invocation)
                tool_results.append({
                    "tool": invocation.tool,
                    "input": invocation.tool_input,
                    "output": result
                })
            
            # Add tool results to state
            state["tools_output"]["results"] = tool_results
            
            # Add tool results as system messages
            for result in tool_results:
                state["messages"].append(
                    SystemMessage(
                        content=f"Tool {result['tool']} returned: {json.dumps(result['output'])}"
                    )
                )
            
            # Update sender
            state["sender"] = AgentType.ASSISTANT
            
            return state
        
        except Exception as e:
            logger.error(f"Error in tool execution node: {str(e)}", exc_info=True)
            state["error"] = str(e)
            state["sender"] = AgentType.SYSTEM
            return state
    
    async def _error_handler_node(self, state: AgentState) -> AgentState:
        """
        Handle errors and update state.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        # Get the error message
        error_message = state.get("error", "Unknown error")
        
        # Add error message as system message
        state["messages"].append(
            SystemMessage(
                content=f"Error: {error_message}"
            )
        )
        
        # Clear error
        state["error"] = None
        
        # Update sender
        state["sender"] = AgentType.ASSISTANT
        
        return state
    
    def _route_assistant_output(self, state: AgentState) -> str:
        """
        Route the output from the assistant agent.
        
        Args:
            state: Current state
            
        Returns:
            Next node to execute
        """
        if state.get("error"):
            return "error"
        
        if state.get("tools_output") and state.get("tools_output").get("invocations"):
            return "tool"
        
        return "end"
    
    def _route_tool_output(self, state: AgentState) -> str:
        """
        Route the output from tool execution.
        
        Args:
            state: Current state
            
        Returns:
            Next node to execute
        """
        if state.get("error"):
            return "error"
        
        return "assistant"
    
    async def process_message(self, message: str, task_id: str = None, project_name: str = None, repo_name: str = None) -> Dict[str, Any]:
        """
        Process a message through the workflow.
        
        Args:
            message: Message to process
            task_id: Task ID (optional)
            project_name: Project name (optional)
            repo_name: Repository name (optional)
            
        Returns:
            Result of the workflow execution
        """
        # Initialize state
        state = AgentState(
            messages=[HumanMessage(content=message)],
            sender=AgentType.USER,
            task_id=task_id,
            task_status=None,
            project_name=project_name,
            repo_name=repo_name,
            error=None,
            tools_output=None
        )
        
        # Execute the workflow
        result = await self.workflow.ainvoke(state)
        
        return result
    
    async def execute_task(self, task_id: str, description: str) -> Dict[str, Any]:
        """
        Execute a task through the workflow.
        
        Args:
            task_id: Task ID
            description: Task description
            
        Returns:
            Result of the task execution
        """
        # Initialize state for task execution
        state = AgentState(
            messages=[
                SystemMessage(content=f"Execute task {task_id}"),
                HumanMessage(content=description)
            ],
            sender=AgentType.SYSTEM,
            task_id=task_id,
            task_status="pending",
            project_name=None,
            repo_name=None,
            error=None,
            tools_output=None
        )
        
        # Execute the workflow
        result = await self.workflow.ainvoke(state)
        
        return result