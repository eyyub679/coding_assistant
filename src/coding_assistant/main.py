from coding_assistant.supervisor_agent import get_agent, State
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from typing import cast
from pathlib import Path
import logging
import uuid
import json

logging.getLogger("google_genai.models").setLevel(logging.ERROR)

def main():
    query=input()
    state=cast(
        State,
        {
            "query":query,
            "steps":[],
            "current_step_idx":0,
            "last_subagent_output":"",
            "codebase_summary":"",
            "router_decision":"",
            "last_subagent":""
        }
    )
    thread=str(uuid.uuid4())
    config=cast(
        RunnableConfig,
        {
            "configurable": {"thread_id":thread}
        }
    )
    checkpointer=InMemorySaver()
    coding_agent=get_agent(checkpointer=checkpointer)
    graph_input=state
    while True: # until all interrupts are finished
        for event in coding_agent.stream(graph_input,config={"configurable":{"thread_id":thread}},stream_mode="updates"):
            for node_name,output in event.items():
                print(f"{node_name} finished")

        snapshot=coding_agent.get_state({"configurable":{"thread_id":thread}})
        if not snapshot.next: # if the graph is finished
            break

        payload=snapshot.tasks[0].interrupts[0].value
        print("AGENT IS STUCK!")
        print(payload["data"])
        user_hint=input(payload["question"]+": ")
        graph_input=Command(resume=user_hint)

    # save thread id and query to a file
    ROOT=Path(__file__).parent.parent.parent
    path=f"{ROOT}/test_results/threads.json"
    os.makedirs(f"{ROOT}/test_results", exist_ok=True)
    try:
        with open(path,"r") as file:
            data=json.load(file)
    except FileNotFoundError:
        data={}
    with open(path,"w") as file:
        data[str(thread)]=query
        json.dump(data,file,indent=4)
if __name__ == "__main__":
    main()
