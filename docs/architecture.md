# Architecture

```mermaid
flowchart LR
  UI[React dashboard] --> API[Flask REST API]
  API --> AG[Typed deterministic agent modules]
  AG --> REG[Allowlisted tool registry]
  REG --> MOCK[Local support and CRM demo connectors]
  API --> DB[(SQLAlchemy persistence\nSQLite locally / PostgreSQL in Compose)]
  API --> KB[TXT/Markdown keyword knowledge index]
  API --> APR[Approval gate: exact payload hash]
  APR --> REG
  API --> AUD[Persisted audit events]
```

Workflow template preparation runs through an explicit LangGraph validation-to-execution graph. Workflow state is persisted before approval pauses; the approval endpoint resumes the persisted application workflow (it does not restore a LangGraph checkpoint). Approval verifies the exact SHA-256 payload digest, is single use, and records connector confirmation and audit events. This is a local demonstration; authentication and process-backed background queues are not implemented.
