# DataLab - Unified LLM-Powered BI Platform

A unified Business Intelligence platform that integrates an LLM-based multi-agent framework with a computational notebook interface. Supports the full BI workflow — data preparation, analysis, and visualization — for different data roles in a single environment.

Based on the research paper: [DataLab: A Unified Platform for LLM-Powered Business Intelligence](https://arxiv.org/abs/2412.02205)

This codebase now extends the paper-aligned notebook and agent architecture with an enterprise governance layer: workspace isolation, role-based access control, audit logging, request tracing, and governed WebSocket access.

## Features

- **Multi-Agent Framework**: Proxy Agent orchestrates specialized agents (SQL, Python, Chart, Insight, EDA, Cleaning, Report) via FSM-based execution plans
- **Computational Notebook**: Multi-language cells (SQL, Python, Chart GUI, Markdown) with Monaco editor
- **Domain Knowledge**: Automated knowledge extraction, knowledge graph, coarse-to-fine retrieval
- **Inter-Agent Communication**: Notebook cells now act as cell agents with per-cell workspaces and file-backed inbox/outbox handoff
- **Context Management**: Stateless DAG execution rebuilds cell dependencies on every run and reads execution context back from workspace files
- **Cell Cooperation**: SQL outputs feed Python, Python data frames feed SQL, charts resolve `data_source` from upstream cells, and markdown placeholders render live notebook values
- **AI Editing UX**: Cell-specific AI rewrite contracts plus a right-side per-cell generation progress panel with DAG and IPC stages
- **Multi-LLM Support**: OpenAI, Anthropic, Ollama, Azure via LiteLLM
- **Bilingual UI**: English / 中文
- **Enterprise Governance**: Workspace-scoped notebooks, cells, data sources, and knowledge nodes with owner/admin/analyst/viewer roles
- **Operational Auditability**: Request IDs, auditable mutations, and an in-product audit feed for admins

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- An LLM API key (OpenAI, Anthropic, or local Ollama)

### Backend

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env  # Edit with your API keys
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5171 to explore!

### Seed The Enterprise Runtime Demo

After the backend and frontend are running, seed the demo workspace:

```bash
bash scripts/init-demo.sh http://127.0.0.1:8000
```

This creates an `Enterprise Runtime Demo` notebook that validates the full linked flow:

- SQL cell defines `sales_summary`
- Python cell transforms it into `product_metrics`
- SQL cell materializes `premium_products` from the Python output
- Chart cell renders from `premium_products` via `data_source`
- Markdown cell resolves live placeholders from notebook outputs
- AI Edit on any cell shows a right-side generation progress rail with DAG and IPC stages
- Every executed cell exposes a `Cell Agent Runtime` panel with workspace and message details

### Enterprise Local Defaults

The backend bootstraps a default enterprise workspace and owner for local development:

- Workspace: `demo-hq`
- User: `admin@datalab.local`
- Role: `owner`

The frontend automatically uses this context. If you call the API directly, send:

```bash
curl http://localhost:8000/api/enterprise/context \
  -H 'X-DataLab-Workspace: demo-hq' \
  -H 'X-DataLab-User-Email: admin@datalab.local'
```

### Docker

```bash
docker-compose up --build
```

## Architecture

```
User → Notebook UI → FastAPI → Stateless Cell-Agent Runtime → Cell Workspaces
                                    │                           │
                                    │                           ├── source / task / context / output
                                    │                           └── inbox / outbox (file-backed IPC)
                                    │
                                    ├── Proxy Agent → [SQL|Python|Chart|Insight] Agents
                                    ├── Domain Knowledge (ChromaDB + KG)
                                    └── Enterprise Control Plane (Workspace / RBAC / Audit / Request IDs)
```

## Paper Review Notes

The local paper `2412.02205v3.pdf` highlights three modules as the core of DataLab:

- **Domain knowledge incorporation**
- **Inter-agent communication**
- **Cell-based context management**

This iteration keeps those research modules intact and hardens the product layer around them so the platform can be operated with clearer tenant boundaries and governance controls in enterprise settings.

The notebook runtime now treats every cell as a cell agent. Each execution rebuilds a fresh DAG, creates or refreshes a per-cell workspace, writes file-backed task/context manifests, and exchanges direct dependency messages through inbox/outbox files before executing the target cell. That keeps the architecture simple, inspectable, and stable.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | React 18 + TypeScript + Vite |
| Database | SQLite / PostgreSQL |
| Vector Store | ChromaDB |
| LLM | LiteLLM (OpenAI, Anthropic, Ollama) |
| SQL Engine | DuckDB |
| Charts | ECharts + Vega-Lite |
| Editor | Monaco Editor |

## Project Structure

```
datalab/
├── backend/          # FastAPI server
│   ├── app/
│   │   ├── agents/        # LLM agent framework
│   │   ├── communication/ # Inter-agent communication
│   │   ├── knowledge/     # Domain knowledge module
│   │   ├── context/       # Cell-based context management
│   │   ├── execution/     # Code execution engines
│   │   ├── llm/           # LLM abstraction layer
│   │   ├── api/           # REST + WebSocket routes
│   │   ├── models/        # Database ORM models
│   │   └── schemas/       # Pydantic schemas
│   └── tests/
├── frontend/         # React/TypeScript UI
│   └── src/
│       ├── components/    # UI components
│       ├── stores/        # State management
│       └── services/      # API clients
└── docs/             # Documentation
    └── SDD.md        # Software Design Document
```

## License

MIT
