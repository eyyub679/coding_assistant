from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage
from typing import TypedDict, Annotated
from coding_assistant.utils import get_llm
from coding_assistant.config import Config
from coding_assistant.tools import read_file,run_command

tools=[read_file,run_command]
tools_by_name={tool.name:tool for tool in tools}

config=Config()

llm=get_llm(model=config.model,max_retries=config.max_retries)
llm_with_tools=llm.bind_tools(tools)

class State(TypedDict):
    task: str
    messages: Annotated[list,add_messages]

def get_reviewer_agent(checkpointer):
    def agent_node(state: State)->dict:
        """Reads the task, and decides whether to call a tool"""
        response=llm_with_tools.invoke(
            [
                SystemMessage(
                    content="""
                        You are a senior code reviewer. Your job is to find bugs,
                        syntax errors, and style violations. Never modify files.
                        Use run_command only for linters like "ruff check" or "python -m py_compile".
                        Report your findings as a structured list.
                    """
                ),
                HumanMessage(
                    content=f"Task: {state["task"]}"
                )
            ]+state["messages"]
        )
        return {
            "messages":response
        }

    def tool_node(state: State)->dict:
        """Uses tools to execute tool calls"""
        tool_calls=state["messages"][-1].tool_calls
        tool_messages=[]
        for tool_call in tool_calls:
            tool_name=tool_call["name"]
            args=tool_call["args"]
            tool=tools_by_name[tool_name]
            output=tool.invoke(args)
            tool_message=ToolMessage(
                content=output["content"], # because our tools return a dict containing status and content
                tool_call_id=tool_call["id"]
            )
            tool_messages.append(tool_message)
        return {
            "messages":tool_messages
        }
    def should_continue(state: State)->str:
        """Decides whether to go to END or tool_node"""
        if state["messages"][-1].tool_calls:
            return "tool_node"
        else:
            return END

    agent_builder=StateGraph(State)

    agent_builder.add_node("agent_node",agent_node)
    agent_builder.add_node("tool_node",tool_node)

    agent_builder.add_edge(START,"agent_node")
    agent_builder.add_conditional_edges(
        "agent_node",
        should_continue,
        ["tool_node",END]
    )
    agent_builder.add_edge("tool_node","agent_node")

    agent=agent_builder.compile(checkpointer=checkpointer)

    return agent
    