# DataLab - Unified LLM-Powered BI Platform

A unified Business Intelligence platform that integrates an LLM-based multi-agent framework with a computational notebook interface. Supports the full BI workflow — data preparation, analysis, and visualization — for different data roles in a single environment.

Based on the research paper: [DataLab: A Unified Platform for LLM-Powered Business Intelligence](https://arxiv.org/abs/2412.02205)

## Features

- **Agent Framework**: ChatBIAgent (unified NL→SQL/Chart) and PythonAgent (NL→DS code) handle natural language queries
- **Computational Notebook**: Multi-language cells (SQL, Python, Chart, Markdown) with Monaco editor
- **Domain Knowledge**: Automated knowledge extraction via Map-Reduce, tree-based knowledge graph, coarse-to-fine retrieval
- **Cell-Agent Runtime**: Every cell is a stateless cell agent with per-cell workspaces and file-backed inbox/outbox IPC
- **DAG Context Management**: Stateless DAG execution rebuilds cell dependencies on every run and resolves context from workspace files
- **Cell Cooperation**: SQL outputs feed Python, Python DataFrames feed SQL, charts resolve `data_source` from upstream cells, markdown placeholders render live notebook values
- **AI Editing**: Cell-specific AI rewrite with SSE streaming, DAG-aware context, and a per-cell generation progress panel
- **Multi-LLM Support**: OpenAI, Anthropic, Ollama, Azure via LiteLLM
- **Bilingual UI**: English / 中文

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

### Seed Demo Data

After the backend and frontend are running, seed the demo notebook:

```bash
bash scripts/init-demo.sh http://127.0.0.1:8000
```

This creates a demo notebook that validates the full linked flow:

- SQL cell defines `sales_summary`
- Python cell transforms it into `product_metrics`
- SQL cell materializes `premium_products` from the Python output
- Chart cell renders from `premium_products` via `data_source`
- Markdown cell resolves live placeholders from notebook outputs
- AI Edit on any cell shows a generation progress panel with DAG and IPC stages
- Every executed cell exposes a Cell Agent Runtime card with workspace details

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
                                    ├── ChatBIAgent (NL→SQL, NL→Chart)
                                    ├── PythonAgent (NL→DS code)
                                    ├── Domain Knowledge (KG + lexical retrieval)
                                    └── DuckDB / Python subprocess execution
```

## Paper Alignment

The research paper (`2412.02205v3.pdf`) highlights three core modules:

- **Domain knowledge incorporation** — Map-Reduce knowledge generation, tree-based knowledge graph, coarse-to-fine retrieval
- **Inter-agent communication** — InformationUnit, SharedBuffer, file-backed inbox/outbox IPC
- **Cell-based context management** — CellDependencyDAG, VariableTracker, ContextRetriever

The notebook runtime treats every cell as a cell agent. Each execution rebuilds a fresh DAG, creates or refreshes a per-cell workspace, writes file-backed task/context manifests, and exchanges direct dependency messages through inbox/outbox files before executing the target cell.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI / SQLAlchemy / Pydantic |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| State | Zustand |
| Database | SQLite (default) / PostgreSQL |
| LLM | LiteLLM (OpenAI, Anthropic, Ollama, Azure) |
| SQL Engine | DuckDB |
| Charts | ECharts |
| Editor | Monaco Editor |
| i18n | react-i18next |

## Project Structure

```
demo/
├── README.md
├── TODO.md
├── Makefile
├── docker-compose.yml
├── walkthrough.md
├── 2412.02205v3.pdf              # Original research paper
│
├── backend/
│   ├── Dockerfile
│   ├── .env.example
│   ├── pyproject.toml
│   ├── alembic/
│   │   └── env.py
│   ├── app/
│   │   ├── main.py               # FastAPI app entry, lifespan, CORS
│   │   ├── config.py             # Pydantic settings, env loading
│   │   ├── database.py           # SQLAlchemy async engine & session
│   │   ├── notebook_runtime.py   # DAG bundle builder, context helpers
│   │   ├── agents/
│   │   │   ├── base.py           # BaseAgent, Jinja2 prompt loader
│   │   │   ├── chatbi_agent.py   # Unified NL→SQL/Chart agent
│   │   │   ├── python_agent.py   # NL→Python (DS code) agent
│   │   │   └── context_builder.py # Notebook query context loader
│   │   ├── api/
│   │   │   ├── agents.py         # /api/agent/query endpoint
│   │   │   ├── cells.py          # CRUD, execute, AI-edit (SSE)
│   │   │   ├── datasources.py    # DataSource CRUD, query, upload
│   │   │   ├── folders.py        # Folder CRUD
│   │   │   ├── knowledge.py      # Knowledge generate, search, graph
│   │   │   ├── notebooks.py      # Notebook CRUD
│   │   │   └── websocket.py      # WebSocket: cell exec, agent query
│   │   ├── communication/
│   │   │   ├── fsm.py            # Agent FSM (designed, not active)
│   │   │   ├── info_unit.py      # InformationUnit data class
│   │   │   ├── protocol.py       # CommunicationProtocol
│   │   │   └── shared_buffer.py  # Async shared buffer with lock
│   │   ├── context/
│   │   │   ├── dag.py            # CellDependencyDAG
│   │   │   ├── retrieval.py      # ContextRetriever
│   │   │   └── tracker.py        # VariableTracker (SQL/Python/Chart/MD)
│   │   ├── execution/
│   │   │   ├── cell_runtime.py   # CellRuntime: DAG plan, workspace IPC
│   │   │   ├── python_executor.py # Python subprocess sandbox
│   │   │   ├── sandbox.py        # ExecutionSandbox (simple dispatcher)
│   │   │   └── sql_executor.py   # DuckDB SQL executor
│   │   ├── knowledge/
│   │   │   ├── dsl.py            # NL→JSON DSL translator
│   │   │   ├── generator.py      # Map-Reduce knowledge generation
│   │   │   ├── graph.py          # Tree-based knowledge graph (SQLite)
│   │   │   ├── profiler.py       # Data profiler
│   │   │   └── retriever.py      # Coarse-to-fine retrieval
│   │   ├── llm/
│   │   │   ├── client.py         # LiteLLM wrapper (complete, stream)
│   │   │   ├── tools.py          # Tool definitions (unused)
│   │   │   └── prompts/          # Jinja2 prompt templates
│   │   │       ├── system.j2
│   │   │       ├── sql_generation.j2
│   │   │       ├── python_generation.j2
│   │   │       ├── chart_generation.j2
│   │   │       ├── knowledge_extraction.j2
│   │   │       ├── insight_generation.j2
│   │   │       ├── query_rewrite.j2
│   │   │       ├── dsl_translation.j2
│   │   │       ├── chat_generation.j2   # unused
│   │   │       └── task_routing.j2      # unused
│   │   ├── models/
│   │   │   ├── cell.py           # Cell (SQL/Python/Chart/Markdown)
│   │   │   ├── datasource.py     # DataSource
│   │   │   ├── folder.py         # Folder
│   │   │   ├── knowledge.py      # KnowledgeNode
│   │   │   ├── notebook.py       # Notebook
│   │   │   └── user.py           # User (schema only, not active)
│   │   ├── schemas/
│   │   │   ├── agent.py
│   │   │   ├── cell.py
│   │   │   ├── folder.py
│   │   │   ├── knowledge.py
│   │   │   └── notebook.py
│   │   └── utils/
│   │       └── helpers.py        # Misc utilities
│   └── tests/
│       ├── conftest.py
│       ├── test_agents_api.py
│       ├── test_ai_edit.py
│       ├── test_context_runtime.py
│       ├── test_executors.py
│       └── test_sql_consistency.py
│
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.tsx              # React entry point
│       ├── App.tsx               # Router, layout shell
│       ├── index.css             # Tailwind + global styles
│       ├── types/
│       │   └── index.ts          # Shared TypeScript types
│       ├── services/
│       │   ├── api.ts            # Axios REST + SSE client
│       │   └── websocket.ts      # WebSocket client with reconnect
│       ├── stores/
│       │   ├── notebookStore.ts  # Notebooks, cells, folders (Zustand)
│       │   ├── chatStore.ts      # Chat messages & agent queries
│       │   └── uiStore.ts        # Sidebar, theme, language
│       ├── i18n/
│       │   ├── index.ts          # i18next config
│       │   ├── en.json
│       │   └── zh.json
│       └── components/
│           ├── common/
│           │   ├── Header.tsx
│           │   ├── DataTable.tsx
│           │   ├── ErrorBoundary.tsx
│           │   └── LoadingSpinner.tsx
│           ├── layout/
│           │   └── MainLayout.tsx
│           ├── sidebar/
│           │   └── Sidebar.tsx
│           ├── chat/
│           │   └── ChatPanel.tsx
│           ├── chart/
│           │   └── ChartRenderer.tsx
│           ├── editor/
│           │   └── MonacoEditor.tsx
│           └── notebook/
│               ├── Notebook.tsx
│               ├── CellContainer.tsx
│               ├── CellToolbar.tsx
│               ├── CellRuntimeCard.tsx
│               ├── CellGenerationPanel.tsx
│               ├── AddCellButton.tsx
│               ├── SqlCell.tsx
│               ├── PythonCell.tsx
│               ├── ChartCell.tsx
│               └── MarkdownCell.tsx
│
├── docs/
│   ├── SDD.md                   # Software Design Document
│   └── SDD_zh.md                # SDD (Chinese)
│
└── scripts/
    └── init-demo.sh             # Demo notebook seeding script
```

## License

MIT
