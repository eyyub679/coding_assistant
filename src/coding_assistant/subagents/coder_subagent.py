from typing import TypedDict, Annotated
from coding_assistant.tools import *
from coding_assistant.utils import *
from coding_assistant.config import Config
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage, AIMessage
from langgraph.graph import START,END,StateGraph
from langgraph.types import interrupt

config=Config()

tools=[read_file,write_file,edit_file,run_command,append_to_file]
tools_by_name={tool.name:tool for tool in tools}

llm=get_llm(model=config.model,max_retries=config.max_retries)
llm_with_tools=llm.bind_tools(tools)

class State(TypedDict):
    task: str
    error_count: int
    messages: Annotated[list,add_messages]
def get_coder_agent(checkpointer):
    def agent_node(state: State)->dict:
        """Agent reads the messages and decides whether to make a tool call or not"""
        task=state["task"]
        prompt=[
            SystemMessage(
                content="""
                    You are an autonomous coding assistant.

                    TOOL USAGE:
                        Always inspect the file content using read_file before you attempt to edit a file.
                        When user asks you to create a script, create it using existing tools and then use run_command to check if the script works.

                    RULES:
                        When user asks you something, use tools to execute the task, do not give any explanations, unless they ask you for an explicit explanation.
                        You will be given a task that needs to be done.
                        When you finish, always state:
                            What files you created or modified.
                            Whether you verified the result.
                """
            ),
            HumanMessage(
                content=f"Task: {task}"
            )
        ]
        response=llm_with_tools.invoke(prompt+state["messages"])
        return {
            "messages":response
        }

    def should_continue(state:State)->str:
        """Decides whether to go to END or tool_node or messages_summary_node"""
        if state["error_count"]>=config.max_error_count: # ai can give up and not call any tools
            return "human_intervention_node"
        elif state["messages"][-1].tool_calls:
            return "tool_node"
        else:
            return END

    def tool_node(state:State)->dict:
        """Uses tools to execute tool calls"""
        messages=state["messages"]
        tool_messages=[]
        error=False
        for tool_call in messages[-1].tool_calls:
            tool=tools_by_name[tool_call["name"]]
            args=tool_call["args"]
            print(f"CALLING TOOL: {tool_call["name"]}")
            output=tool.invoke(args)
            if output["status"]=="error":
                error=True
                # we increment error count once even if llm calls 3 tools in one turn
            tool_message=ToolMessage(
                content=output["content"],
                tool_call_id=tool_call["id"],
                status="success" if output["status"]=="success" else "error"
            )
            tool_messages.append(tool_message)
        return {
            "messages":tool_messages,
            "error_count": state["error_count"]+1 if error else 0 # if it fixes the error (no error in output) then reset the counter
        }

    def human_intervention_node(state: State)->dict:
        """Prints out the error and asks user for help"""
        errors=[] # potential errors in tool messages
        for i,msg in enumerate(reversed(state["messages"]),start=1):
            if isinstance(msg,AIMessage):
                break
            elif isinstance(msg,ToolMessage) and msg.status=="error":
                errors.append(f"{i}.{msg.content}")
        errors.reverse()

        errors+=[f"STUCK ON STEP: {state["task"]}"]

        user_hint=interrupt(
            {
                "question":"How should I fix these errors",
                "data":"\n".join(errors)
            }
        )

        return {
            "messages": [HumanMessage(content=user_hint)],
            "error_count":0
        }

    agent_builder=StateGraph(State)

    agent_builder.add_node("agent_node",agent_node)
    agent_builder.add_node("tool_node",tool_node)
    agent_builder.add_node("human_intervention_node",human_intervention_node)

    agent_builder.add_edge(START,"agent_node")
    agent_builder.add_conditional_edges(
        "agent_node",
        should_continue,
        ["tool_node","human_intervention_node",END]
    )
    agent_builder.add_edge("tool_node","agent_node")
    agent_builder.add_edge("human_intervention_node","agent_node")

    # checkpointer=InMemorySaver()
    """we shouldnt redefine checkpointer inside our agent every time
    the checkpointer of the parent graph is enough.
    """
    agent=agent_builder.compile(checkpointer=checkpointer)

    return agent