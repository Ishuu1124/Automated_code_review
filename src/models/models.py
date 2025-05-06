import operator
from pydantic import BaseModel
from typing_extensions import Annotated
from langgraph.prebuilt.chat_agent_executor import AgentState

class DiffModel(BaseModel):
    filename: str
    diff_url: str | None
    initial_code: str | None
    changed_code: str | None

class InputModel(BaseModel):
    title: str
    diff: list[DiffModel]
    mode: str

class SummaryModel(BaseModel):
    summary: str
    
class TaskOut(BaseModel):
    id: str
    status: str

class State(AgentState):
    url: str
    title: str
    diffs: list[DiffModel]
    summarized_files: Annotated[
        list, operator.add
    ]
    reviewed_files: Annotated[
        list, operator.add
    ]
    summary: str
    review: str
    reviewer_instructions: str
    response: str
    mode: str
    
class WorkerState(AgentState):
    diff: DiffModel
    summarized_files: Annotated[
        list, operator.add
    ]
    reviewed_files: Annotated[
        dict, operator.add
    ]