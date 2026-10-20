def summarize(request, status, steps, approvals):
    return {"original_request":request,"status":status,"completed_actions":[s["name"] for s in steps if s["status"]=="completed"],
            "failed_actions":[s["name"] for s in steps if s["status"]=="failed"],"pending_approvals":approvals,
            "steps":steps,"next_steps":["Review the pending approval." ] if approvals else []}
