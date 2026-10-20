def interpret(request: str) -> dict:
    """Extract observable request requirements; never invokes tools."""
    return {"objective": request.strip(), "input_requirements": [], "requested_operations": ["classify", "retrieve", "prepare", "request_approval"],
            "required_tools": ["knowledge.search", "support_ticket.classify", "support_ticket.prepare_update"],
            "expected_outputs": ["classification", "evidence", "draft", "approval"],
            "approval_requirements": ["support_ticket.apply_update"], "missing_information": [],
            "validation_rules": ["Only registered local demo tools may be planned.", "State changes require approval."]}
