from ..tools.registry import TOOL_IDS

def create_plan(intent: dict) -> dict:
    steps=[]
    for i, tool in enumerate(intent["required_tools"]):
        if tool not in TOOL_IDS: raise ValueError(f"Unsupported tool: {tool}")
        steps.append({"id":f"step-{i+1}","name":tool.split(".")[-1].replace("_"," ").title(),"tool_id":tool,
                      "depends_on":[] if i==0 else [f"step-{i}"],"approval_required":tool.endswith("apply_update"),
                      "max_retries":1 if tool.startswith("knowledge.") else 0})
    return {"objective":intent["objective"],"steps":steps}
