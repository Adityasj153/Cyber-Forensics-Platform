# Cyber Forensics Platform

AI-Based Log Investigation Framework for Digital Forensics.

## Tech Stack

- **Frontend:** Next.js + TypeScript, Tailwind CSS, shadcn/ui, D3.js
- **Backend:** Python FastAPI, Celery + Redis, SQLAlchemy + Alembic
- **Data:** PostgreSQL + TimescaleDB, Elasticsearch, MinIO (S3-compatible)
- **AI/ML:** scikit-learn, XGBoost, NetworkX, SHAP

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Node.js 20+ (for local frontend dev)

### Run with Docker
```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

### Run locally (backend)
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Run locally (frontend)
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
cyber-forensics-platform/
├── frontend/          # Next.js + TypeScript
├── backend/           # FastAPI + Python
├── infra/             # Kubernetes, Terraform
├── datasets/          # Synthetic test datasets
├── docs/              # PRD, architecture, rules, phases
└── docker-compose.yml
```

## Development Phases

| Phase | Focus |
|-------|-------|
| 0 | Project setup & foundations |
| 1 | Log ingestion, parsing & aggregation |
| 2 | Secure storage & AI engine prototype |
| 3 | Graphical representation & dashboard GUI |
| 4 | Reporting engine & benchmarking |
