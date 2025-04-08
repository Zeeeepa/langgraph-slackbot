"""
LangGraph implementation for the Multi-Threaded Agentic Slackbot.

This module defines the LangGraph state and nodes for agent orchestration.
"""

import os
import logging
from typing import Dict, List, Any, Optional, TypedDict, Annotated, Literal
from enum import Enum
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint import MemorySaver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define state types
class AgentState(TypedDict):
    """State for the agent graph."""
    messages: List[Dict[str, Any]]  # List of messages in the conversation
    task: Optional[Dict[str, Any]]  # Current task being processed
    status: str  # Status of the current task
    results: List[Dict[str, Any]]  # Results of completed tasks
    errors: List[Dict[str, Any]]  # Errors encountered during processing
    context: Dict[str, Any]  # Additional context for the agent

class TaskStatus(str, Enum):
    """Status of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_HUMAN = "needs_human"

# Define agent nodes
def analyze_request(state: AgentState) -> AgentState:
    """
    Analyze the user request and determine the task type.
    
    Args:
        state: Current state of the agent
        
    Returns:
        Updated state with task information
    """
    logger.info("Analyzing user request")
    
    # Get the latest message
    latest_message = state["messages"][-1]
    
    # Initialize LLM
    llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    
    # Create a prompt for task type determination
    type_prompt = ChatPromptTemplate.from_messages([
        (
            "system", 
            """You are an expert task classifier. Determine the type of task based on the user's request.
            Task types:
            - implementation: Tasks that involve implementing features, writing code, or making changes to the codebase
            - document_processing: Tasks that involve processing, analyzing, or generating documents
            - analysis: Tasks that involve analyzing code, requirements, or project state
            - project_management: Tasks that involve managing projects, tasks, or resources
            - generic: Any other type of task
            
            Format your response as a JSON object with the following structure:
            {
                "task_type": "implementation|document_processing|analysis|project_management|generic",
                "priority": "high|medium|low",
                "description": "Brief description of the task",
                "requires_human": true|false
            }
            """
        ),
        ("human", "{request}")
    ])
    
    # Create a chain for task type determination
    type_chain = type_prompt | llm | JsonOutputParser()
    
    # Determine task type
    task_info = type_chain.invoke({"request": latest_message.get("content", "")})
    
    # Update state with task information
    state["task"] = task_info
    state["status"] = TaskStatus.PENDING.value
    
    logger.info(f"Task type determined: {task_info.get('task_type')}")
    return state

def route_task(state: AgentState) -> Literal["implementation", "document_processing", "analysis", "project_management", "generic", "human_intervention"]:
    """
    Route the task to the appropriate node based on task type and whether it requires human intervention.
    
    Args:
        state: Current state of the agent
        
    Returns:
        Name of the next node to execute
    """
    task = state.get("task", {})
    
    # Check if task requires human intervention
    if task.get("requires_human", False):
        return "human_intervention"
    
    # Route based on task type
    task_type = task.get("task_type", "generic")
    if task_type in ["implementation", "document_processing", "analysis", "project_management", "generic"]:
        return task_type
    
    # Default to generic if task type is not recognized
    return "generic"

def implementation_task(state: AgentState) -> AgentState:
    """
    Process implementation tasks.
    
    Args:
        state: Current state of the agent
        
    Returns:
        Updated state with implementation results
    """
    logger.info("Processing implementation task")
    
    task = state.get("task", {})
    
    # Initialize LLM
    llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    
    # Create a prompt for implementation
    implementation_prompt = ChatPromptTemplate.from_messages([
        (
            "system", 
            """You are an expert software engineer. Implement the requested feature or task.
            Provide a detailed implementation plan, including:
            1. Files that need to be created or modified
            2. Code changes to be made
            3. Tests to be added or updated
            4. Documentation updates
            
            Format your response as a JSON object with the following structure:
            {
                "implementation_plan": {
                    "files": [
                        {
                            "path": "file/path.py",
                            "changes": "Description of changes"
                        }
                    ],
                    "steps": [
                        "Step 1: Description",
                        "Step 2: Description"
                    ]
                },
                "branch_name": "feature/branch-name",
                "pr_title": "Implement feature X",
                "pr_description": "Detailed description of the PR"
            }
            """
        ),
        ("human", "{task_description}")
    ])
    
    # Create a chain for implementation
    implementation_chain = implementation_prompt | llm | JsonOutputParser()
    
    # Process implementation task
    implementation_result = implementation_chain.invoke({"task_description": task.get("description", "")})
    
    # Update state with implementation results
    state["status"] = TaskStatus.COMPLETED.value
    state["results"].append({
        "task_type": "implementation",
        "implementation_result": implementation_result
    })
    
    logger.info("Implementation task completed")
    return state

def document_processing_task(state: AgentState) -> AgentState:
    """
    Process document processing tasks.
    
    Args:
        state: Current state of the agent
        
    Returns:
        Updated state with document processing results
    """
    logger.info("Processing document processing task")
    
    task = state.get("task", {})
    
    # Initialize LLM
    llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    
    # Create a prompt for document processing
    document_prompt = ChatPromptTemplate.from_messages([
        (
            "system", 
            """You are an expert document processor. Process the requested documents.
            Provide a detailed analysis of the documents, including:
            1. Key information extracted
            2. Summary of the documents
            3. Recommendations based on the documents
            
            Format your response as a JSON object with the following structure:
            {
                "document_analysis": {
                    "key_information": [
                        "Key point 1",
                        "Key point 2"
                    ],
                    "summary": "Summary of the documents",
                    "recommendations": [
                        "Recommendation 1",
                        "Recommendation 2"
                    ]
                }
            }
            """
        ),
        ("human", "{task_description}")
    ])
    
    # Create a chain for document processing
    document_chain = document_prompt | llm | JsonOutputParser()
    
    # Process document task
    document_result = document_chain.invoke({"task_description": task.get("description", "")})
    
    # Update state with document processing results
    state["status"] = TaskStatus.COMPLETED.value
    state["results"].append({
        "task_type": "document_processing",
        "document_result": document_result
    })
    
    logger.info("Document processing task completed")
    return state

def analysis_task(state: AgentState) -> AgentState:
    """
    Process analysis tasks.
    
    Args:
        state: Current state of the agent
        
    Returns:
        Updated state with analysis results
    """
    logger.info("Processing analysis task")
    
    task = state.get("task", {})
    
    # Initialize LLM
    llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    
    # Create a prompt for analysis
    analysis_prompt = ChatPromptTemplate.from_messages([
        (
            "system", 
            """You are an expert analyst. Analyze the requested information.
            Provide a detailed analysis, including:
            1. Key findings
            2. Insights
            3. Recommendations
            
            Format your response as a JSON object with the following structure:
            {
                "analysis_result": {
                    "findings": [
                        "Finding 1",
                        "Finding 2"
                    ],
                    "insights": [
                        "Insight 1",
                        "Insight 2"
                    ],
                    "recommendations": [
                        "Recommendation 1",
                        "Recommendation 2"
                    ]
                }
            }
            """
        ),
        ("human", "{task_description}")
    ])
    
    # Create a chain for analysis
    analysis_chain = analysis_prompt | llm | JsonOutputParser()
    
    # Process analysis task
    analysis_result = analysis_chain.invoke({"task_description": task.get("description", "")})
    
    # Update state with analysis results
    state["status"] = TaskStatus.COMPLETED.value
    state["results"].append({
        "task_type": "analysis",
        "analysis_result": analysis_result
    })
    
    logger.info("Analysis task completed")
    return state

def project_management_task(state: AgentState) -> AgentState:
    """
    Process project management tasks.
    
    Args:
        state: Current state of the agent
        
    Returns:
        Updated state with project management results
    """
    logger.info("Processing project management task")
    
    task = state.get("task", {})
    
    # Initialize LLM
    llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    
    # Create a prompt for project management
    project_prompt = ChatPromptTemplate.from_messages([
        (
            "system", 
            """You are an expert project manager. Manage the requested project or task.
            Provide a detailed project management plan, including:
            1. Project timeline
            2. Resource allocation
            3. Task dependencies
            4. Risk assessment
            
            Format your response as a JSON object with the following structure:
            {
                "project_management_plan": {
                    "timeline": [
                        {
                            "phase": "Phase 1",
                            "duration": "2 weeks",
                            "tasks": [
                                "Task 1",
                                "Task 2"
                            ]
                        }
                    ],
                    "resources": [
                        {
                            "role": "Developer",
                            "count": 2
                        }
                    ],
                    "dependencies": [
                        {
                            "task": "Task 2",
                            "depends_on": "Task 1"
                        }
                    ],
                    "risks": [
                        {
                            "risk": "Risk 1",
                            "mitigation": "Mitigation strategy"
                        }
                    ]
                }
            }
            """
        ),
        ("human", "{task_description}")
    ])
    
    # Create a chain for project management
    project_chain = project_prompt | llm | JsonOutputParser()
    
    # Process project management task
    project_result = project_chain.invoke({"task_description": task.get("description", "")})
    
    # Update state with project management results
    state["status"] = TaskStatus.COMPLETED.value
    state["results"].append({
        "task_type": "project_management",
        "project_result": project_result
    })
    
    logger.info("Project management task completed")
    return state

def generic_task(state: AgentState) -> AgentState:
    """
    Process generic tasks.
    
    Args:
        state: Current state of the agent
        
    Returns:
        Updated state with generic task results
    """
    logger.info("Processing generic task")
    
    task = state.get("task", {})
    
    # Initialize LLM
    llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    
    # Create a prompt for generic tasks
    generic_prompt = ChatPromptTemplate.from_messages([
        (
            "system", 
            """You are an expert assistant. Process the requested task.
            Provide a detailed response to the task.
            """
        ),
        ("human", "{task_description}")
    ])
    
    # Create a chain for generic tasks
    generic_chain = generic_prompt | llm | StrOutputParser()
    
    # Process generic task
    generic_result = generic_chain.invoke({"task_description": task.get("description", "")})
    
    # Update state with generic task results
    state["status"] = TaskStatus.COMPLETED.value
    state["results"].append({
        "task_type": "generic",
        "generic_result": generic_result
    })
    
    logger.info("Generic task completed")
    return state

def human_intervention(state: AgentState) -> AgentState:
    """
    Handle tasks that require human intervention.
    
    Args:
        state: Current state of the agent
        
    Returns:
        Updated state with human intervention status
    """
    logger.info("Task requires human intervention")
    
    # Update state to indicate human intervention is needed
    state["status"] = TaskStatus.NEEDS_HUMAN.value
    
    # Add a message to the conversation
    state["messages"].append({
        "role": "assistant",
        "content": "This task requires human intervention. I'll notify a human operator to assist with this request."
    })
    
    logger.info("Human intervention requested")
    return state

def format_response(state: AgentState) -> AgentState:
    """
    Format the response to send back to the user.
    
    Args:
        state: Current state of the agent
        
    Returns:
        Updated state with formatted response
    """
    logger.info("Formatting response")
    
    # Get the latest result
    if state["results"]:
        latest_result = state["results"][-1]
        task_type = latest_result.get("task_type", "generic")
        
        # Initialize LLM
        llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
        
        # Create a prompt for response formatting
        format_prompt = ChatPromptTemplate.from_messages([
            (
                "system", 
                """You are an expert communicator. Format the results of a task into a clear, concise response for the user.
                Make sure to include all relevant information from the results, but present it in a way that is easy to understand.
                """
            ),
            ("human", "Task type: {task_type}\nResults: {results}")
        ])
        
        # Create a chain for response formatting
        format_chain = format_prompt | llm | StrOutputParser()
        
        # Format the response
        formatted_response = format_chain.invoke({
            "task_type": task_type,
            "results": json.dumps(latest_result, indent=2)
        })
        
        # Add the formatted response to the conversation
        state["messages"].append({
            "role": "assistant",
            "content": formatted_response
        })
    else:
        # No results to format
        state["messages"].append({
            "role": "assistant",
            "content": "I've processed your request, but there are no results to report."
        })
    
    logger.info("Response formatted")
    return state

# Create the agent graph
def create_agent_graph():
    """
    Create a LangGraph agent graph for the Multi-Threaded Agentic Slackbot.
    
    Returns:
        StateGraph: The agent graph
    """
    # Create a new graph
    workflow = StateGraph(AgentState)
    
    # Add nodes to the graph
    workflow.add_node("analyze_request", analyze_request)
    workflow.add_node("implementation", implementation_task)
    workflow.add_node("document_processing", document_processing_task)
    workflow.add_node("analysis", analysis_task)
    workflow.add_node("project_management", project_management_task)
    workflow.add_node("generic", generic_task)
    workflow.add_node("human_intervention", human_intervention)
    workflow.add_node("format_response", format_response)
    
    # Add edges to the graph
    workflow.add_edge("analyze_request", route_task)
    workflow.add_edge("implementation", "format_response")
    workflow.add_edge("document_processing", "format_response")
    workflow.add_edge("analysis", "format_response")
    workflow.add_edge("project_management", "format_response")
    workflow.add_edge("generic", "format_response")
    workflow.add_edge("human_intervention", "format_response")
    workflow.add_edge("format_response", END)
    
    # Set the entry point
    workflow.set_entry_point("analyze_request")
    
    # Compile the graph
    return workflow.compile()

# Create a ReAct agent for more complex tasks
def create_react_task_agent(tools=None):
    """
    Create a ReAct agent for more complex tasks that require reasoning and tool use.
    
    Args:
        tools: List of tools available to the agent
        
    Returns:
        The ReAct agent
    """
    # Initialize LLM
    llm = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    
    # Create the ReAct agent
    agent = create_react_agent(llm, tools or [])
    
    return agent
