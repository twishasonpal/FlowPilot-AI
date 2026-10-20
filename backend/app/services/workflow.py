import hashlib, json
from uuid import uuid4
from .. import now
from ..models import Workflow, Approval
from ..agents.summary_agent import summarize

TEMPLATES={
 "support":{"id":"support","name":"AI Support Assistant","description":"Classify a synthetic support ticket, search local knowledge, draft a grounded response, and request approval before applying ticket changes.","inputs":["subject","description"],"approval":"Ticket updates require explicit approval."},
 "document":{"id":"document","name":"Document Information Extraction","description":"Extract structured fields from supplied text and flag missing information.","inputs":["text","fields"],"approval":"No external action is performed."},
 "lead":{"id":"lead","name":"Business Lead Processing","description":"Score a synthetic lead and prepare a CRM update for human approval.","inputs":["name","company","email","interest"],"approval":"CRM changes require explicit approval."}}

def _hash(payload):return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _run_template(Session,audit,template_id,inputs):
    if template_id=="support":
        if not inputs.get("subject") or not inputs.get("description"):raise ValueError("subject and description are required.")
        name="Support: "+inputs["subject"][:100]; request=f"Classify ticket {inputs['subject']}: {inputs['description']}"
        steps=[{"name":"Validate ticket data","status":"completed","result":{"valid":True}},
               {"name":"Classify support ticket","status":"completed","result":{"category":"general","urgency":"normal"}},
               {"name":"Search knowledge base","status":"completed","result":{"evidence":[],"message":"No indexed knowledge documents were found; response is not knowledge-verified."}},
               {"name":"Draft response","status":"completed","result":{"draft":f"Thanks for contacting us about {inputs['subject']}. We have received your request and will follow up after review.","grounded":False}},
               {"name":"Prepare ticket update","status":"waiting_approval","result":{"status":"open","assignment":"support"}}]
        payload={"ticket_subject":inputs["subject"],"ticket_description":inputs["description"],"status":"open","assignment":"support"}; action="support_ticket.apply_update";target=inputs["subject"]
    elif template_id=="lead":
        if not all(inputs.get(k) for k in ("name","company","interest")):raise ValueError("name, company, and interest are required.")
        name="Lead: "+inputs["name"][:100];request=f"Process synthetic lead {inputs['name']} at {inputs['company']} interested in {inputs['interest']}"
        score="high" if len(inputs["interest"])>20 else "medium"
        steps=[{"name":"Validate lead","status":"completed","result":{"valid":True,"synthetic":True}},
               {"name":"Classify lead","status":"completed","result":{"score":score}},
               {"name":"Prepare CRM update","status":"waiting_approval","result":{"stage":"qualified","score":score}}]
        payload={"name":inputs["name"],"company":inputs["company"],"email":inputs.get("email",""),"stage":"qualified","score":score};action="crm.lead.apply_update";target=inputs["company"]
    elif template_id=="document":
        content=inputs.get("text","");fields=inputs.get("fields",["date","amount","vendor"])
        if not content.strip():raise ValueError("text is required.")
        import re
        extracted={}; evidence={}
        for fld in fields:
            m=re.search(rf"(?im)^\s*{re.escape(fld)}\s*[:=]\s*(.+)$",content)
            if m:extracted[fld]=m.group(1).strip()[:250];evidence[fld]=m.group(0).strip()
        missing=[f for f in fields if f not in extracted]
        name="Document extraction";request="Extract fields: "+", ".join(fields)
        steps=[{"name":"Validate source text","status":"completed","result":{"valid":True}},
               {"name":"Extract configured fields","status":"completed","result":{"fields":extracted,"evidence":evidence,"missing":missing}}]
        payload={};action="document.extract";target="local document"
    else:raise ValueError("Unknown workflow template.")
    db=Session();wid=str(uuid4()); pending=template_id in ("support","lead")
    plan={"template_id":template_id,"objective":request,"steps":[{"id":f"step-{i+1}","name":s["name"],"tool_id":"support_ticket.apply_update" if pending and i==len(steps)-1 else "knowledge.search","approval_required":pending and i==len(steps)-1} for i,s in enumerate(steps)]}
    w=Workflow(id=wid,name=name,template_id=template_id,original_request=request,plan_json=json.dumps(plan),status="waiting_approval" if pending else "completed",steps_json=json.dumps(steps),report_json="{}",created_at=now(),updated_at=now())
    db.add(w)
    if pending:
        a=Approval(id=str(uuid4()),workflow_id=wid,action=action,target=target,payload_json=json.dumps(payload,sort_keys=True),payload_hash=_hash(payload),status="pending",notes="",created_at=now(),decided_at="");db.add(a)
    else:a=None
    audit(db,"workflow.created",wid,workflow_id=wid);audit(db,"workflow.executed",wid,workflow_id=wid,metadata={"template":template_id,"steps":len(steps)})
    w.report_json=json.dumps(summarize(request,w.status,steps,[a.id] if a else []));db.commit();result=w.as_dict();result["approvals"]=[a.as_dict()] if a else [];db.close();return result

from ..graph.workflow import compile_template_graph
_TEMPLATE_GRAPH=compile_template_graph(_run_template)

def run_template(Session,audit,template_id,inputs):
    """Run the bounded LangGraph template path; approval resumption uses durable DB records."""
    return _TEMPLATE_GRAPH.invoke({"template_id":template_id,"inputs":inputs,"session_factory":Session,"audit_fn":audit})["workflow"]

def apply_approval(db,w,a,decision,audit,notes):
    a.status="approved" if decision=="approve" else "rejected";a.notes=notes[:500];a.decided_at=now()
    steps=json.loads(w.steps_json)
    step=steps[-1]
    if decision=="approve":
        # Local mock connector confirmation; this exact payload hash was reviewed by the UI.
        step["status"]="completed";step["result"]={"confirmed":True,"connector":"internal-demo","action":a.action,"target":a.target}
        w.status="completed";outcome="success"
    else:
        step["status"]="skipped";step["result"]={"reason":"Approval rejected; no changes applied."};w.status="completed_with_warnings";outcome="rejected"
    w.steps_json=json.dumps(steps);w.updated_at=now();w.report_json=json.dumps(summarize(w.original_request,w.status,steps,[]))
    audit(db,"approval."+decision,a.id,outcome=outcome,metadata={"payload_hash":a.payload_hash},workflow_id=w.id)
    audit(db,"connector.demo_action",a.target,outcome=outcome,metadata={"action":a.action},workflow_id=w.id)
    return w.as_dict()
