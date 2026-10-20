from typing import Any, TypedDict
from langgraph.graph import END, START, StateGraph

class TemplateState(TypedDict, total=False):
    template_id: str
    inputs: dict[str, Any]
    session_factory: Any
    audit_fn: Any
    workflow: dict[str, Any]

def compile_template_graph(executor):
    """Bounded local template path: validate request shape, then call fixed application executor."""
    def validate(state: TemplateState):
        if not isinstance(state.get("inputs"),dict): raise ValueError("Template inputs must be an object.")
        return {}
    def execute(state: TemplateState):
        result=executor(state["session_factory"],state["audit_fn"],state["template_id"],state["inputs"])
        return {"workflow":result}
    graph=StateGraph(TemplateState)
    graph.add_node("validate",validate)
    graph.add_node("execute_registered_template",execute)
    graph.add_edge(START,"validate")
    graph.add_edge("validate","execute_registered_template")
    graph.add_edge("execute_registered_template",END)
    return graph.compile()
