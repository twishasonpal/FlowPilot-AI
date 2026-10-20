import json
from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from . import Base


class Workflow(Base):
    __tablename__="workflows"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    name: Mapped[str]=mapped_column(String(180))
    template_id: Mapped[str]=mapped_column(String(50))
    original_request: Mapped[str]=mapped_column(Text,default="")
    plan_json: Mapped[str]=mapped_column(Text,default="{}")
    status: Mapped[str]=mapped_column(String(32),index=True)
    steps_json: Mapped[str]=mapped_column(Text,default="[]")
    report_json: Mapped[str]=mapped_column(Text,default="{}")
    created_at: Mapped[str]=mapped_column(String(40),index=True)
    updated_at: Mapped[str]=mapped_column(String(40))
    approvals=relationship("Approval",back_populates="workflow",cascade="all, delete-orphan")
    def as_dict(self):
        return {"id":self.id,"name":self.name,"template_id":self.template_id,"original_request":self.original_request,
                "plan":json.loads(self.plan_json),"status":self.status,"steps":json.loads(self.steps_json),
                "report":json.loads(self.report_json),"created_at":self.created_at,"updated_at":self.updated_at}


class Approval(Base):
    __tablename__="approvals"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    workflow_id: Mapped[str]=mapped_column(ForeignKey("workflows.id",ondelete="CASCADE"),index=True)
    action: Mapped[str]=mapped_column(String(100))
    target: Mapped[str]=mapped_column(String(240))
    payload_json: Mapped[str]=mapped_column(Text)
    payload_hash: Mapped[str]=mapped_column(String(64))
    status: Mapped[str]=mapped_column(String(24),index=True)
    notes: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[str]=mapped_column(String(40))
    decided_at: Mapped[str]=mapped_column(String(40),default="")
    workflow=relationship("Workflow",back_populates="approvals")
    def as_dict(self):
        return {"id":self.id,"workflow_id":self.workflow_id,"action":self.action,"target":self.target,
                "payload":json.loads(self.payload_json),"payload_hash":self.payload_hash,"status":self.status,
                "notes":self.notes,"created_at":self.created_at,"decided_at":self.decided_at}


class KnowledgeDocument(Base):
    __tablename__="knowledge_documents"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    title: Mapped[str]=mapped_column(String(240))
    file_type: Mapped[str]=mapped_column(String(16))
    content_hash: Mapped[str]=mapped_column(String(64),unique=True)
    content: Mapped[str]=mapped_column(Text)
    created_at: Mapped[str]=mapped_column(String(40))
    def as_dict(self):return {"id":self.id,"title":self.title,"file_type":self.file_type,"status":"indexed","created_at":self.created_at}


class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    workflow_id: Mapped[str|None]=mapped_column(ForeignKey("workflows.id",ondelete="SET NULL"),index=True,nullable=True)
    action: Mapped[str]=mapped_column(String(100))
    target: Mapped[str]=mapped_column(String(240))
    outcome: Mapped[str]=mapped_column(String(32))
    metadata_json: Mapped[str]=mapped_column(Text,default="{}")
    created_at: Mapped[str]=mapped_column(String(40),index=True)
    def as_dict(self):return {"id":self.id,"workflow_id":self.workflow_id,"action":self.action,"target":self.target,"outcome":self.outcome,"metadata":json.loads(self.metadata_json),"created_at":self.created_at}


class Connector(Base):
    __tablename__="connectors"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    name: Mapped[str]=mapped_column(String(160))
    connector_type: Mapped[str]=mapped_column(String(40))
    enabled: Mapped[int]=mapped_column(Integer,default=1)
