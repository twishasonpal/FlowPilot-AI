from ..tools.registry import REGISTRY

def execute(tool_id: str, payload: dict):
    tool=REGISTRY.get(tool_id)
    if tool is None: raise ValueError("Tool is not registered")
    return tool(payload)
