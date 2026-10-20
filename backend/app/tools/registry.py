TOOL_IDS={"knowledge.search","support_ticket.classify","support_ticket.prepare_update","support_ticket.apply_update",
          "crm.lead.prepare_update","crm.lead.apply_update","document.extract","email.prepare_draft"}
REGISTRY={}

def register(tool_id, fn): REGISTRY[tool_id]=fn

def validate_plan(plan):
    seen=set()
    for step in plan["steps"]:
        if step.get("tool_id") not in TOOL_IDS:return f"Unregistered tool: {step.get('tool_id')}"
        if not step.get("id") or step["id"] in seen:return "Plan step IDs must be unique and non-empty."
        if not isinstance(step.get("depends_on",[]),list):return "Step dependencies must be a list."
        if not isinstance(step.get("approval_required",False),bool):return "approval_required must be boolean."
        seen.add(step["id"])
    for s in plan["steps"]:
        if any(dep not in seen for dep in s.get("depends_on",[])):return "Plan references an unknown dependency."
    return None

register("knowledge.search",lambda p:{"matches":[]})
register("support_ticket.classify",lambda p:{"category":"general","urgency":"normal"})
register("support_ticket.prepare_update",lambda p:{"prepared":True})
register("support_ticket.apply_update",lambda p:{"applied":True})
register("crm.lead.prepare_update",lambda p:{"prepared":True})
register("crm.lead.apply_update",lambda p:{"applied":True})
register("document.extract",lambda p:{"fields":{}})
register("email.prepare_draft",lambda p:{"drafted":True})
