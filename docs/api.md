# API

The API is served at `/api/v1`; Flask routes validate required input and return JSON errors. `GET /api/v1/health`, `GET /api/v1/dashboard`, `GET /api/v1/templates`, `POST /api/v1/templates/{support|document|lead}/run`, `POST /api/v1/workflows/plan`, `POST /api/v1/workflows`, `GET /api/v1/workflows`, `GET /api/v1/workflows/{id}`, `POST /api/v1/approvals/{id}/decision`, `GET /api/v1/approvals`, `POST /api/v1/documents`, `POST /api/v1/knowledge/search`, `GET /api/v1/connectors`, and `GET /api/v1/audit` are available. Workflow listing accepts `limit`, `offset`, and `status`.
