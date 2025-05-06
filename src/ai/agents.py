from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Send
from src.common import llm_prompts

from src.models.models import State, WorkerState
from src.ai.llmEngine import LLMEngine

llm = LLMEngine()

def initiator(state: State):
    """Initialising state."""
    return {
        "reviewer_instructions": "",
    }
    
def worker(state: WorkerState):
    """Worker summarizes one file's changes at once."""
    
    # if file was newly created
    if state['diff'].initial_code == None:
        summary = llm.invoke(
            system_message=SystemMessage(
                content=llm_prompts.file_created_prompt
            ),
            human_message=HumanMessage(
                content=llm_prompts.get_human_message_for_content_summary(state['diff'].filename, state['diff'].changed_code)
            )
        )
    # if file was deleted
    elif state['diff'].changed_code == None:
        summary = llm.invoke(
            SystemMessage(
                content=llm_prompts.file_deleted_prompt
            ),
            HumanMessage(
                content=llm_prompts.get_human_message_for_content_summary(state['diff'].filename, state['diff'].initial_code)
            )
        )
    # if file was only updated
    else:
        summary = llm.invoke(
            system_message=SystemMessage(
                content=llm_prompts.file_updated_prompt
            ),
            human_message=HumanMessage(
                content=llm_prompts.get_human_message_for_updates_summary(state['diff'].filename, state["diff"].initial_code, state["diff"].changed_code)
            )
        )
    return {"summarized_files": [state['diff'].filename + "\n" + summary]}

def synthesizer(state: State):
    """Synthesize full report from the individual file summaries."""
    
    summarized_files = state['summarized_files']
    summary = "\n\n---\n\n".join(summarized_files)
    return {
        "summary": summary
    }

def summarizer(state: State):
    """Rephrase and formulate a better concise summary."""
    
    if (instructions:=state['reviewer_instructions']):
        response = llm.invoke(
            #instructions
            system_message=SystemMessage(
                content=instructions
            ),
            human_message=HumanMessage(
                content=f"{state['summary']}"
            )
        )
    else:
        response = llm.invoke(
            system_message=SystemMessage(
                content=llm_prompts.summarizer_initial_prompt
            ),
            human_message=HumanMessage(
                content=f"""
                {state['summary']}
                """
            )
        )
    
    return {
        "response": response
    }
 
def reviewer(state: State):
    """Review the summary made by the summarizer."""
    instructions = llm.invoke(
        SystemMessage(
            content=llm_prompts.reviewer_prompt
        ),
        HumanMessage(
            content=f"{state['response']}"
        )
    )
    return {
        "reviewer_instructions": instructions
    }
    
def code_review_worker(state: WorkerState):
    """Provide feedback for the code."""
    if state['diff'].changed_code:
        review = llm.invoke(
            SystemMessage(
                content=llm_prompts.PROMPT_REVIEW
            ),
            HumanMessage(
                content=f"{state['diff'].changed_code}"
            )
        )
        return {"reviewed_files": [review]}
    else:
        return {"reviewed_files": [""]}

def review_router(state: State):
    if "FINAL ANSWER" in state['reviewer_instructions']:
        return True
    else:
        return False

def assign_workers(state: State):
    """Assign a worker to each individual file."""
    return [Send("worker", {"diff": d}) for d in state["diffs"]]

def assign_reviewers(state: State):
    return [Send("code_review_worker", {"diff": d}) for d in state["diffs"]]

def mode_router(state: State):
    if state['mode'] == 'summary':
        return True
    elif state['mode'] == 'review':
        return False
    else:
        return True #default behaviour for now. can define something else later
    
def code_review_synthesizer(state: State):
    """Synthesize full report from the individual file reviews."""
    
    reviewed_files = state['reviewed_files']
    review = "\n\n---\n\n".join(reviewed_files)
    return {
        "response": review
    }