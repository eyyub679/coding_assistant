'''
def messages_summarizer_node(state: State)->dict:
    """Summarizes messages list and moves on to the next step"""
    steps=state["steps"]
    idx=state["current_step_idx"]
    step=steps[idx] if steps else ""
    # LLM is better at reading string than reading raw list of messages
    formatted_messages="\n".join([f"{type(m).__name__}: {m.content}" for m in state["messages"]])
    prompt=[
        SystemMessage(
            content="""
                You are an expert summarizer.
                Your task is to read a list of messages and summarize it.
                You must include any specific file name, path or command so that the agent remembers to keep using them in the next step.
        """
        ),
        HumanMessage(
            content=f"Messages: {formatted_messages}"
        )
    ]
    response=llm.invoke(prompt)
    summary=extract_text(response.content)
    print(f"COMPLETED STEP: {state["steps"][state["current_step_idx"]]}")
    return {
        # LLM can only read langchain message object so we need to wrap our string with SystemMessage
        "messages":[RemoveMessage(m.id) for m in state["messages"]]+[SystemMessage(content=f"Summary of the step '{step}': {summary}")],
        "current_step_idx": state["current_step_idx"]+1
    }

We removed this because when we moved from single agent to multi agent
we no longer need to keep track of messages cuz in our main node - the router node
we just use steps, current step and last agent output, we dont need to store messages.
'''