import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=int(os.getenv("MAX_UPLOAD_BYTES", "5000000")))
    if test_config:
        app.config.update(test_config)
    CORS(app, origins=os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(","))
    Limiter(get_remote_address, app=app, default_limits=["120 per minute"], storage_uri="memory://")
    db_url = app.config.get("DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///flowpilot.db"))
    opts = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, connect_args=opts)
    Session = sessionmaker(engine, expire_on_commit=False)
    app.extensions["db_engine"] = engine
    app.extensions["db_session"] = Session

    from .models import Workflow, Approval, KnowledgeDocument, AuditEvent, Connector
    Base.metadata.create_all(engine)

    def audit(db, action, target, outcome="success", metadata=None, workflow_id=None):
        db.add(AuditEvent(id=str(uuid4()), action=action, target=target, outcome=outcome,
                          metadata_json=json.dumps(metadata or {}), workflow_id=workflow_id, created_at=now()))

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error={"code": "upload_too_large", "message": "Request exceeds the configured size limit."}), 413

    @app.get("/api/v1/health")
    def health():
        try:
            with engine.connect() as c: c.execute(text("SELECT 1"))
            return jsonify(status="ok", database="connected", mode="deterministic-local")
        except Exception:
            return jsonify(status="degraded", database="unavailable"), 503

    @app.get("/api/v1/templates")
    def templates():
        from .services.workflow import TEMPLATES
        return jsonify(items=list(TEMPLATES.values()))

    @app.get("/api/v1/dashboard")
    def dashboard():
        db=Session()
        try:
            rows=db.query(Workflow).all()
            pending=db.query(Approval).filter_by(status="pending").count()
            return jsonify(metrics={"total":len(rows),"running":sum(w.status in ("running","waiting_approval") for w in rows),
                "completed":sum(w.status=="completed" for w in rows),"failed":sum(w.status=="failed" for w in rows),"pending_approvals":pending},
                recent=[w.as_dict() for w in sorted(rows,key=lambda r:r.created_at,reverse=True)[:8]],
                templates=["support", "document", "lead"], connectors=[{"name":"Demo support and CRM","status":"ready","type":"mock"}])
        finally: db.close()

    @app.post("/api/v1/workflows/plan")
    def plan():
        body=request.get_json(silent=True) or {}
        prompt=(body.get("request") or "").strip()
        if len(prompt)<8: return jsonify(error={"code":"validation_error","message":"Enter a workflow request of at least 8 characters."}),400
        from .agents.intent_agent import interpret
        from .agents.planner_agent import create_plan
        intent=interpret(prompt); proposed=create_plan(intent)
        return jsonify(intent=intent, plan=proposed, mode="deterministic-local", can_execute=True)

    @app.post("/api/v1/workflows")
    def create_workflow():
        body=request.get_json(silent=True) or {}; title=(body.get("name") or "Custom workflow").strip()
        plan=body.get("plan")
        if not isinstance(plan,dict) or not isinstance(plan.get("steps"),list) or not plan["steps"]:
            return jsonify(error={"code":"validation_error","message":"A plan with at least one step is required."}),400
        from .tools.registry import validate_plan
        error=validate_plan(plan)
        if error: return jsonify(error={"code":"invalid_plan","message":error}),400
        db=Session(); w=Workflow(id=str(uuid4()),name=title,template_id="custom",original_request=body.get("request",""),
            plan_json=json.dumps(plan),status="planned",steps_json=json.dumps([]),created_at=now(),updated_at=now())
        db.add(w); audit(db,"workflow.created",w.id,workflow_id=w.id); db.commit(); result=w.as_dict(); db.close()
        return jsonify(workflow=result),201

    @app.post("/api/v1/templates/<template_id>/run")
    def run_template(template_id):
        body=request.get_json(silent=True) or {}
        from .services.workflow import run_template as execute_template, TEMPLATES
        if template_id not in TEMPLATES: return jsonify(error={"code":"not_found","message":"Unknown workflow template."}),404
        try: result=execute_template(Session, audit, template_id, body)
        except ValueError as e: return jsonify(error={"code":"validation_error","message":str(e)}),400
        return jsonify(workflow=result),201

    @app.get("/api/v1/workflows")
    def list_workflows():
        db=Session()
        try:
            limit=min(max(request.args.get("limit",20,type=int),1),100); offset=max(request.args.get("offset",0,type=int),0)
            q=db.query(Workflow).order_by(Workflow.created_at.desc())
            status=request.args.get("status")
            if status: q=q.filter_by(status=status)
            total=q.count(); return jsonify(items=[w.as_dict() for w in q.offset(offset).limit(limit)],total=total,limit=limit,offset=offset)
        finally: db.close()

    @app.get("/api/v1/workflows/<workflow_id>")
    def workflow_detail(workflow_id):
        db=Session()
        try:
            w=db.get(Workflow,workflow_id)
            if not w: return jsonify(error={"code":"not_found","message":"Workflow not found."}),404
            d=w.as_dict(); d["approvals"]=[a.as_dict() for a in db.query(Approval).filter_by(workflow_id=w.id).all()]
            d["trace"]=[e.as_dict() for e in db.query(AuditEvent).filter_by(workflow_id=w.id).order_by(AuditEvent.created_at).all()]
            return jsonify(workflow=d)
        finally: db.close()

    @app.post("/api/v1/workflows/<workflow_id>/start")
    def start_workflow(workflow_id):
        db=Session()
        try:
            w=db.get(Workflow,workflow_id)
            if not w:return jsonify(error={"code":"not_found","message":"Workflow not found."}),404
            if w.status not in ("planned","queued"): return jsonify(workflow=w.as_dict()),409
            w.status="running"; w.updated_at=now(); audit(db,"workflow.started",w.id,workflow_id=w.id); db.commit()
            return jsonify(workflow=w.as_dict())
        finally:db.close()

    @app.get("/api/v1/approvals")
    def approvals():
        db=Session()
        try:
            vals=db.query(Approval).order_by(Approval.created_at.desc()).all()
            return jsonify(items=[a.as_dict() for a in vals])
        finally:db.close()

    @app.post("/api/v1/approvals/<approval_id>/decision")
    def decide(approval_id):
        body=request.get_json(silent=True) or {}; decision=body.get("decision")
        if decision not in ("approve","reject"):return jsonify(error={"code":"validation_error","message":"decision must be approve or reject."}),400
        db=Session()
        try:
            a=db.get(Approval,approval_id)
            if not a:return jsonify(error={"code":"not_found","message":"Approval not found."}),404
            if a.status!="pending":return jsonify(error={"code":"approval_consumed","message":"This approval is no longer pending."}),409
            if body.get("payload_hash")!=a.payload_hash:return jsonify(error={"code":"payload_mismatch","message":"Reviewed action payload does not match."}),409
            w=db.get(Workflow,a.workflow_id)
            if not w or w.status!="waiting_approval":return jsonify(error={"code":"workflow_ineligible","message":"Workflow is no longer awaiting approval."}),409
            from .services.workflow import apply_approval
            result=apply_approval(db,w,a,decision,audit,body.get("notes","")); db.commit()
            return jsonify(workflow=result,approval=a.as_dict())
        finally:db.close()

    @app.post("/api/v1/workflows/<workflow_id>/cancel")
    def cancel(workflow_id):
        db=Session()
        try:
            w=db.get(Workflow,workflow_id)
            if not w:return jsonify(error={"code":"not_found","message":"Workflow not found."}),404
            if w.status in ("completed","failed","cancelled"):return jsonify(error={"code":"workflow_terminal","message":"Workflow is already finished."}),409
            w.status="cancelled";w.updated_at=now();audit(db,"workflow.cancelled",w.id,workflow_id=w.id);db.commit();return jsonify(workflow=w.as_dict())
        finally:db.close()

    @app.get("/api/v1/audit")
    def audit_list():
        db=Session()
        try:return jsonify(items=[e.as_dict() for e in db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100).all()])
        finally:db.close()

    @app.get("/api/v1/connectors")
    def connectors():
        return jsonify(items=[{"id":"demo-local","name":"Demo CRM and support","type":"mock","enabled":True,"health":"ready"},
                              {"id":"gemini","name":"Gemini","type":"llm","enabled":bool(os.getenv("GEMINI_API_KEY")),"health":"not_configured" if not os.getenv("GEMINI_API_KEY") else "configured"}])

    @app.post("/api/v1/documents")
    def upload_document():
        from .services.knowledge import add_document
        f=request.files.get("file")
        if not f:return jsonify(error={"code":"validation_error","message":"Choose a TXT or Markdown file."}),400
        try:
            data=add_document(db_session=Session(), audit_fn=audit, file=f)
            return jsonify(document=data),201
        except ValueError as e:return jsonify(error={"code":"validation_error","message":str(e)}),400

    @app.get("/api/v1/documents")
    def documents():
        db=Session()
        try:return jsonify(items=[d.as_dict() for d in db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).all()])
        finally:db.close()

    @app.delete("/api/v1/documents/<doc_id>")
    def delete_document(doc_id):
        db=Session(); d=db.get(KnowledgeDocument,doc_id)
        if not d:db.close();return jsonify(error={"code":"not_found","message":"Document not found."}),404
        db.delete(d);db.commit();db.close();return "",204

    @app.post("/api/v1/knowledge/search")
    def knowledge_search():
        from .services.knowledge import search
        body=request.get_json(silent=True) or {}; q=(body.get("query") or "").strip()
        if not q:return jsonify(error={"code":"validation_error","message":"query is required."}),400
        db=Session()
        try:return jsonify(items=search(db,q))
        finally:db.close()

    return app
