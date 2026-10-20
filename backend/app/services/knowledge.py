import hashlib
import re
from uuid import uuid4
from . import __name__ as _pkg
from .. import now
from ..models import KnowledgeDocument

def add_document(db_session, audit_fn, file):
    name=(file.filename or "").replace("\\","/").split("/")[-1]
    ext=name.rsplit(".",1)[-1].lower() if "." in name else ""
    if ext not in ("txt","md"): raise ValueError("Only TXT and Markdown files are supported in this local build.")
    raw=file.stream.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError("Document is larger than 2 MB.")
    try: content=raw.decode("utf-8")
    except UnicodeDecodeError:raise ValueError("Document must be valid UTF-8 text.")
    if not content.strip():raise ValueError("Document is empty.")
    db=db_session(); digest=hashlib.sha256(raw).hexdigest()
    if db.query(KnowledgeDocument).filter_by(content_hash=digest).first():db.close();raise ValueError("This document is already indexed.")
    doc=KnowledgeDocument(id=str(uuid4()),title=name[:240],file_type=ext,content_hash=digest,content=content,created_at=now())
    db.add(doc);audit_fn(db,"knowledge.document.indexed",doc.id,metadata={"title":doc.title});db.commit();result=doc.as_dict();db.close();return result

def search(db, query):
    terms={x.lower() for x in re.findall(r"[\w'-]+",query) if len(x)>2}; hits=[]
    for doc in db.query(KnowledgeDocument).all():
        for i,chunk in enumerate(re.split(r"\n\s*\n",doc.content)):
            overlap=terms & {x.lower() for x in re.findall(r"[\w'-]+",chunk)}
            if overlap:hits.append({"document_id":doc.id,"title":doc.title,"chunk_id":f"{doc.id}:{i}","excerpt":chunk.strip()[:700],"score":round(len(overlap)/max(len(terms),1),3),"metadata":{"type":doc.file_type}})
    return sorted(hits,key=lambda h:h["score"],reverse=True)[:8]
