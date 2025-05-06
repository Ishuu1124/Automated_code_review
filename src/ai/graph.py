from langgraph.graph import StateGraph, START, END

from src.models.models import State
from src.models.models import DiffModel
from src.ai.agents import initiator, worker, synthesizer, code_review_synthesizer, summarizer, assign_workers, reviewer, review_router, mode_router, code_review_worker, assign_reviewers

orchestrator_worker_builder = StateGraph(State)

orchestrator_worker_builder.add_node("summary_init", initiator)
orchestrator_worker_builder.add_node("code_review_init", initiator)
orchestrator_worker_builder.add_node("worker", worker)
orchestrator_worker_builder.add_node("code_review_worker", code_review_worker)
orchestrator_worker_builder.add_node("synthesizer", synthesizer)
orchestrator_worker_builder.add_node("code_review_synthesizer", code_review_synthesizer)
orchestrator_worker_builder.add_node("summarizer", summarizer)
orchestrator_worker_builder.add_node("reviewer", reviewer)

# orchestrator_worker_builder.add_edge(START, "orchestrator")
orchestrator_worker_builder.add_conditional_edges(START, mode_router, {True: "summary_init", False: "code_review_init"})

#summary workflow
orchestrator_worker_builder.add_conditional_edges("summary_init", assign_workers, ["worker"])
orchestrator_worker_builder.add_edge("worker", "synthesizer")
orchestrator_worker_builder.add_edge("synthesizer", "summarizer")
orchestrator_worker_builder.add_edge("summarizer", "reviewer")
orchestrator_worker_builder.add_conditional_edges("reviewer", review_router, {True: END, False: "summarizer"})

#code review workflow
orchestrator_worker_builder.add_conditional_edges("code_review_init", assign_reviewers, ["code_review_worker"])
orchestrator_worker_builder.add_edge("code_review_worker", "code_review_synthesizer")
orchestrator_worker_builder.add_edge("code_review_synthesizer", END)

orchestrator_worker = orchestrator_worker_builder.compile()

try:
    with open("docs/graph.png", "w+b") as img:
        img.write(orchestrator_worker.get_graph().draw_mermaid_png())
except Exception as e:
    print("Could not generate graph diagram:")
    print(e)
    
def run_graph(title: str, diff: list[DiffModel], mode: str):
    result = orchestrator_worker.invoke(
        {"title": title,
         "diffs": diff,
         "mode": mode},
        {'recursion_limit': 10},
    )
    
    return result['response']