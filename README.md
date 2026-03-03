# DataLab - Unified LLM-Powered BI Platform

A unified Business Intelligence platform that integrates an LLM-based multi-agent framework with a computational notebook interface. Supports the full BI workflow — data preparation, analysis, and visualization — for different data roles in a single environment.

Based on the research paper: [DataLab: A Unified Platform for LLM-Powered Business Intelligence](https://arxiv.org/abs/2412.02205)

## Features

- **Multi-Agent Framework**: Proxy Agent orchestrates specialized agents (SQL, Python, Chart, Insight, EDA, Cleaning, Report) via FSM-based execution plans
- **Computational Notebook**: Multi-language cells (SQL, Python, Chart GUI, Markdown) with Monaco editor
- **Domain Knowledge**: Automated knowledge extraction, knowledge graph, coarse-to-fine retrieval
- **Inter-Agent Communication**: Structured information units, shared buffer, FSM-based selective retrieval
- **Context Management**: Cell dependency DAG, adaptive context pruning for token efficiency
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

Open http://localhost:5173 in your browser.

### Docker

```bash
docker-compose up --build
```

## Architecture

```
User → Notebook UI → FastAPI → Proxy Agent → [SQL|Python|Chart|Insight] Agents
                                    ↕                      ↕
                          Domain Knowledge          Shared Buffer (FSM)
                          (ChromaDB + KG)        Inter-Agent Communication
```

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
