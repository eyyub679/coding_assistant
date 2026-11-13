from langgraph.graph import START, END, StateGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from typing import TypedDict, cast
from coding_assistant.utils import extract_text, get_llm
from coding_assistant.config import Config
from coding_assistant.schemas import PlannerOutput, RouterOutput
from coding_assistant.ast_extractor import get_file_summary
from coding_assistant.subagents.coder_subagent import get_coder_agent
from coding_assistant.subagents.reviewer_subagent import get_reviewer_agent
import os
import uuid

class State(TypedDict):
    query: str
    steps: list[str]
    current_step_idx: int
    last_subagent: str # who spoke last
    last_subagent_output: str # what they told
    codebase_summary: str
    router_decision: str
    # messages: Annotated[list,add_messages] we dont need messages in this multi-agent app

config=Config()

llm=get_llm(model=config.model,max_retries=config.max_retries)
llm_with_structured_output_planner=llm.with_structured_output(PlannerOutput)
llm_with_structured_output_router=llm.with_structured_output(RouterOutput)

def get_agent(checkpointer): # we dont need to pass config as a param cuz we can use langgraph's special method of passing config as a param to subagents
    coder_subagent=get_coder_agent(checkpointer)
    reviewer_subagent=get_reviewer_agent(checkpointer)
    # defined these inside cuz we passed checkpointer from main and we need it for these subagents
    def codebase_summarizer_node(state: State)->dict:
        """Summarizes all the files in the project folder"""
        summaries=[]
        for root,dirs,files in os.walk("."):
            dirs[:]=[d for d in dirs if not d.startswith(".") and d!="venv" and d!="__pycache__"]
            for file in files:
                if file.startswith("."):
                    continue
                full_path=os.path.join(root,file)
                summaries.append(get_file_summary(full_path))
        summary="\n".join(summaries)
        return {
            "codebase_summary":summary
        }

    def planner_node(state: State)->dict:
        """Takes user query and breaks it down into independent steps"""
        prompt=[
            SystemMessage(
                content="""
                You are a planner expert.
                You task is to analyze user's query and break it down into independent steps.
                
                RULES:
                    Do not give any explanations or any extra text, just give the steps.
                    If user asks for a project, explicitly define file name in every step. Tell the agent to edit or append to the file rather than creating a new file every single time.
            """
            ),
            HumanMessage(
                content=f"User Query: {state["query"]}\nCodebase Summary: {state["codebase_summary"]}"
            )
        ]
        response=cast(PlannerOutput,llm_with_structured_output_planner.invoke(prompt))
        return {
            "steps":response.steps
        }

    def router_node(state: State)->dict:
        """Decides which subagent to use, move to the next step or just go to END"""
        steps=state.get("steps",[])
        idx=state.get("current_step_idx",0)
        if idx>=len(steps):
            return {
                "router_decision":"end"
            }
        step=steps[idx]
        response=cast(RouterOutput,llm_with_structured_output_router.invoke(
            [
                SystemMessage(
                    content="""
                        You are an expert router. Your job is to analyze current step
                        and the message of the last subagent to decide where to route next.

                        NOTES:
                            If the last subagent is "coder", you MUST route to "reviewer node" next, never skip it.
                            If the last subagent is "reviewer", and it contain bugs, route to "coder node".
                            If the last subagent is"reviewer", but it doesn't contain any bugs then route to "next step".
                            If all the steps are completed, route to "end".                    
                """
                ),
                HumanMessage(
                    content=f"All steps: {state["steps"]}\nCurrent step: {step}\nLast subagent: {state["last_subagent"]}\nLast agent message: {state["last_subagent_output"]}"
                )
            ]
        )
        )
        route=response.next
        return {
            "router_decision":route
        }

    def go_to(state: State)->str:
        """Based on router decision chooses which node to go"""
        route=state["router_decision"]
        if route=="coder":
            return "coder_node"
        elif route=="reviewer":
            return "reviewer_node"
        elif route=="next_step":
            return "next_step_node"
        else:
            return END

    def coder_node(state: State, config: RunnableConfig)->dict:
        """Invokes coder subagent"""
        steps=state.get("steps",[])
        idx=state.get("current_step_idx",0)
        step=steps[idx] if steps else ""
        parent_config=config.get("configurable",{}).get("thread_id","default")
        coder_config={"configurable":{"thread_id":f"{parent_config}-coder-{idx}"}}
        coder_config=cast(RunnableConfig,coder_config)
        '''
            We need to use different configs for our subagents otherwise they will overwrite each other's state.
            And also we need to use idx cuz we are using coder agent repeatedly for every step. 
            If we dont use idx, once it hits END it will refuse to start from the START for other tasks. 
        '''
        if state["last_subagent"]=="reviewer":
            input_state={
                "messages":[HumanMessage(content=f"You need to fix the issue on step: {step} based on reviewers's output: {state['last_subagent_output']}")]
            }
            ''' when we run the subagent with the same config we will just update state cuz
                if we dont update the state, when it finshes the first time it ends with an AIMessage and gemini requires HumanMessage to answer.
            '''
        else:
            input_state={
                "task": step,
                "error_count":0,
                "messages":[]
            }
        coder_state=coder_subagent.invoke(
            input_state, # this is not an error, typechecker doesnt understand the update rule (only passing messages in the second run with the same config)
            config=coder_config
        )
        last_message=coder_state["messages"][-1]
        coder_message=extract_text(last_message.content)
        print(f"CODER SAYS: {coder_message}")
        return {
            "last_subagent_output": coder_message,
            "last_subagent":"coder"
        }

    def reviewer_node(state: State, config: RunnableConfig)->dict:
        """Invokes reviewer subagent"""
        steps=state.get("steps",[])
        idx=state.get("current_step_idx",0)
        step=steps[idx] if steps else ""
        # we wont add anything here like we did in router node cuz never idx>=len(steps), if this was the case we would be at end after router node
        reviewer_config={"configurable":{"thread_id":str(uuid.uuid4())}}
        reviewer_config=cast(RunnableConfig,reviewer_config)
        # every review is independent so we can just create a unique thread for each review
        if state["last_subagent"]=="coder":
            task=f"You need to analyze what coder did on step: {step} based on its output: {state["last_subagent_output"]}"
        else:
            task=step
        reviewer_state=reviewer_subagent.invoke(
            {
                "task": task,
                "messages":[]
            },
            config=reviewer_config
        )
        last_message=reviewer_state["messages"][-1]
        reviewer_message=extract_text(last_message.content)
        print(f"REVIEWER SAYS: {reviewer_message}")
        return {
            "last_subagent_output": reviewer_message,
            "last_subagent":"reviewer"
        }

    def next_step_node(state: State)->dict:
        """Move on to the next step and clears last_subagent_output because it is unique for each step"""
        return {
            "current_step_idx": state["current_step_idx"]+1,
            "last_subagent_output":"",
            "last_subagent":""
        }

    agent_builder=StateGraph(State)

    agent_builder.add_node("codebase_summarizer_node",codebase_summarizer_node)
    agent_builder.add_node("planner_node",planner_node)
    agent_builder.add_node("router_node",router_node)
    agent_builder.add_node("coder_node",coder_node)
    agent_builder.add_node("reviewer_node",reviewer_node)
    agent_builder.add_node("next_step_node",next_step_node)

    agent_builder.add_edge(START,"codebase_summarizer_node")
    agent_builder.add_edge("codebase_summarizer_node","planner_node")
    agent_builder.add_edge("planner_node","router_node")
    agent_builder.add_conditional_edges(
        "router_node",
        go_to,
        ["coder_node","reviewer_node","next_step_node",END]
    )
    agent_builder.add_edge("coder_node","router_node")
    agent_builder.add_edge("reviewer_node","router_node")
    agent_builder.add_edge("next_step_node","router_node")

    agent=agent_builder.compile(checkpointer=checkpointer)

    return agent