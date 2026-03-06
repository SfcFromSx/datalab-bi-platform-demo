# DataLab - Software Design Document (SDD)

**Version**: 1.1  
**Date**: 2026-03-06  
**Based on**: arXiv:2412.02205v3 - "DataLab: A Unified Platform for LLM-Powered Business Intelligence"

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Architecture Design](#3-architecture-design)
4. [Data Models](#4-data-models)
5. [Module Design](#5-module-design)
6. [API Specification](#6-api-specification)
7. [Frontend Design](#7-frontend-design)
8. [Security & Sandboxing](#8-security--sandboxing)
9. [Internationalization](#9-internationalization)
10. [Deployment](#10-deployment)

---

## 1. Introduction

### 1.1 Purpose

DataLab is a unified Business Intelligence (BI) platform that integrates an LLM-based multi-agent framework with an augmented computational notebook interface. It supports the full BI workflow — data preparation, analysis, and visualization — for different data roles (engineers, scientists, analysts) in a single environment.

### 1.2 Scope

This document covers the complete software design for:

- **Backend**: FastAPI server with agent framework, knowledge modules, communication protocols, and execution engines
- **Frontend**: React/TypeScript notebook interface with multi-language cell support, chart builder, and LLM chat panel
- **Infrastructure**: Database schema, vector store, containerization

### 1.3 Key Design Goals

| Goal | Description |
|------|-------------|
| **Unification** | Single platform for SQL, Python, visualization, and markdown |
| **Intelligence** | LLM agents automate BI tasks via natural language |
| **Extensibility** | DAG-based agent workflows, plugin APIs for data connectors |
| **Efficiency** | Cell-based context management reduces token costs by ~60% |
| **Collaboration** | Multi-role notebook with real-time updates |
| **Governance** | Workspace isolation, RBAC, audit logging, and request tracing for enterprise operation |

### 1.4 Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend Runtime | Python 3.11+ / FastAPI | Async, AI/ML ecosystem, type safety |
| Frontend | React 18 + TypeScript + Vite | Complex UI, strong typing, fast builds |
| Database | SQLite (dev) / PostgreSQL (prod) | SQLAlchemy ORM, Alembic migrations |
| Vector Store | ChromaDB | Embedded, Python-native, no infra overhead |
| LLM Gateway | LiteLLM | Unified API: OpenAI, Anthropic, Ollama, Azure |
| SQL Engine | DuckDB | In-process OLAP, zero config, Pandas interop |
| Python Execution | Subprocess sandbox | Secure code execution with timeout/resource limits |
| Charts | ECharts + Vega-Lite | Rich i18n + grammar-based visualization |
| Code Editor | Monaco Editor | VS Code engine, syntax highlighting, autocomplete |
| Styling | Tailwind CSS + shadcn/ui | Utility-first, accessible component library |
| Real-time | WebSocket (FastAPI) | Streaming execution results, agent progress |
| i18n | react-i18next | Bilingual EN/ZH support |

---

## 2. System Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React/TS)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Notebook  │ │ Chat     │ │ Chart    │ │ Data       │ │
│  │ Interface │ │ Panel    │ │ Builder  │ │ Explorer   │ │
│  └─────┬─────┘ └─────┬────┘ └────┬─────┘ └─────┬──────┘ │
│        └──────────────┴──────────┴──────────────┘        │
│                         │ REST + WebSocket                │
└─────────────────────────┼────────────────────────────────┘
                          │
┌─────────────────────────┼────────────────────────────────┐
│                    Backend (FastAPI)                       │
│  ┌──────────────────────┴───────────────────────────┐    │
│  │                   API Layer                       │    │
│  │  /api/notebooks  /api/cells  /api/agents  /ws     │    │
│  └──────────────────────┬───────────────────────────┘    │
│                         │                                 │
│  ┌──────────────────────┴───────────────────────────┐    │
│  │              Agent Framework                      │    │
│  │  ┌───────┐ ┌─────┐ ┌────────┐ ┌───────┐         │    │
│  │  │ Proxy │→│ SQL │ │ Python │ │ Chart │ ...      │    │
│  │  │ Agent │ │Agent│ │ Agent  │ │ Agent │         │    │
│  │  └───┬───┘ └──┬──┘ └───┬────┘ └───┬───┘         │    │
│  │      │        │        │          │              │    │
│  │  ┌───┴────────┴────────┴──────────┴───┐          │    │
│  │  │      Inter-Agent Communication      │          │    │
│  │  │  SharedBuffer │ FSM │ InfoUnits     │          │    │
│  │  └────────────────────────────────────┘          │    │
│  └──────────────────────────────────────────────────┘    │
│                         │                                 │
│  ┌──────────┐ ┌─────────┴──────┐ ┌──────────────────┐   │
│  │ Domain   │ │ Cell Context   │ │ Execution        │   │
│  │Knowledge │ │ Management     │ │ Engines          │   │
│  │ Module   │ │ (DAG)          │ │ Python │ SQL     │   │
│  └────┬─────┘ └────────────────┘ └──────────────────┘   │
│       │                                                   │
│  ┌────┴─────┐ ┌──────────────┐                           │
│  │ ChromaDB │ │ SQLite/PG    │                           │
│  │ (vectors)│ │ (metadata)   │                           │
│  └──────────┘ └──────────────┘                           │
└──────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │    LLM Providers      │
              │ OpenAI│Anthropic│Ollama│
              └───────────────────────┘
```

### 2.2 Component Summary

| Component | Responsibility |
|-----------|---------------|
| **Proxy Agent** | Routes user queries, creates FSM execution plans, orchestrates agents |
| **Specialized Agents** | SQL, Python, Chart, Insight, EDA, Cleaning, Report generation |
| **Domain Knowledge** | Knowledge generation (Map-Reduce), graph storage, coarse-to-fine retrieval |
| **Inter-Agent Comm** | Structured info units for proxy agents plus file-backed inbox/outbox handoff between cell agents |
| **Context Management** | Stateless DAG planning, adaptive context pruning, and per-cell workspace manifests |
| **Execution Engines** | Sandboxed Python execution, DuckDB SQL engine |
| **Notebook UI** | Multi-language cells, Monaco editor, chart GUI, drag-and-drop |
| **Enterprise Control Plane** | Workspace resolution, role checks, auditable mutations, and scoped WebSocket access |

### 2.3 Paper Alignment And Enterprise Delta

Reviewing the local paper `2412.02205v3.pdf` confirms that DataLab's core research value remains centered on three modules:

- **Domain Knowledge Incorporation** for enterprise-specific BI semantics and jargon
- **Inter-Agent Communication** via structured information units and FSM-driven collaboration
- **Cell-based Context Management** for notebook-aware context pruning and token efficiency

The enterprise version extends these research modules rather than replacing them. The added product layer governs who can access a workspace, which resources are visible inside that workspace, and how every mutating action is traced and audited.

---

## 3. Architecture Design

### 3.1 Backend Package Structure

```
backend/app/
├── main.py              # FastAPI application factory
├── config.py            # Pydantic Settings (env-based config)
├── database.py          # SQLAlchemy engine, session factory
├── api/                 # Route handlers
│   ├── __init__.py
│   ├── notebooks.py     # CRUD for notebooks
│   ├── cells.py         # CRUD for cells + execution
│   ├── agents.py        # Agent query endpoint
│   ├── enterprise.py    # Enterprise context + audit endpoints
│   ├── knowledge.py     # Knowledge CRUD + retrieval
│   ├── datasources.py   # Data source connections
│   └── websocket.py     # WebSocket handler
├── models/              # SQLAlchemy ORM
│   ├── __init__.py
│   ├── audit.py
│   ├── notebook.py
│   ├── cell.py
│   ├── datasource.py
│   ├── knowledge.py
│   ├── membership.py
│   ├── user.py
│   └── workspace.py
├── schemas/             # Pydantic schemas
│   ├── __init__.py
│   ├── enterprise.py
│   ├── notebook.py
│   ├── cell.py
│   ├── agent.py
│   └── knowledge.py
├── enterprise/          # Workspace context, RBAC, audit helpers
│   ├── __init__.py
│   ├── auth.py
│   ├── audit.py
│   └── resources.py
├── agents/              # Agent implementations
│   ├── __init__.py
│   ├── base.py          # BaseAgent ABC
│   ├── proxy.py         # ProxyAgent (orchestrator)
│   ├── sql_agent.py
│   ├── python_agent.py
│   ├── chart_agent.py
│   ├── insight_agent.py
│   ├── eda_agent.py
│   ├── report_agent.py
│   └── cleaning_agent.py
├── communication/       # Inter-Agent Communication
│   ├── __init__.py
│   ├── info_unit.py     # InformationUnit dataclass
│   ├── shared_buffer.py # SharedInformationBuffer
│   ├── fsm.py           # FiniteStateMachine
│   └── protocol.py      # CommunicationProtocol
├── cell_agents/         # Stateless cell-agent runtime
│   ├── __init__.py
│   └── runtime.py       # Per-cell workspace orchestration + file-backed IPC
├── knowledge/           # Domain Knowledge
│   ├── __init__.py
│   ├── generator.py     # MapReduceKnowledgeGenerator
│   ├── graph.py         # KnowledgeGraph
│   ├── retriever.py     # KnowledgeRetriever
│   ├── profiler.py      # DataProfiler
│   └── dsl.py           # DSLTranslator
├── context/             # Cell Context Management
│   ├── __init__.py
│   ├── dag.py           # CellDependencyDAG
│   ├── retrieval.py     # ContextRetriever
│   └── tracker.py       # VariableTracker
├── execution/           # Code Execution
│   ├── __init__.py
│   ├── python_executor.py
│   ├── sql_executor.py
│   └── sandbox.py
├── llm/                 # LLM Abstraction
│   ├── __init__.py
│   ├── client.py        # LiteLLM wrapper
│   ├── tools.py         # Function call definitions
│   └── prompts/         # Jinja2 prompt templates
│       ├── system.j2
│       ├── sql_generation.j2
│       ├── python_generation.j2
│       ├── chart_generation.j2
│       ├── insight_generation.j2
│       ├── knowledge_extraction.j2
│       ├── query_rewrite.j2
│       └── dsl_translation.j2
└── utils/
    ├── __init__.py
    └── helpers.py
```

### 3.2 Frontend Package Structure

```
frontend/src/
├── App.tsx              # Root component with router
├── main.tsx             # Entry point
├── index.css            # Tailwind imports
├── i18n/                # Internationalization
│   ├── index.ts         # i18next config
│   ├── en.json          # English translations
│   └── zh.json          # Chinese translations
├── components/
│   ├── notebook/        # Core notebook components
│   │   ├── Notebook.tsx         # Main notebook container
│   │   ├── CellContainer.tsx    # Generic cell wrapper
│   │   ├── SqlCell.tsx          # SQL cell with Monaco + results table
│   │   ├── PythonCell.tsx       # Python cell with Monaco + output
│   │   ├── ChartCell.tsx        # Chart cell with GUI config + preview
│   │   ├── MarkdownCell.tsx     # Markdown cell with preview
│   │   ├── CellToolbar.tsx      # Cell action buttons
│   │   └── AddCellButton.tsx    # Add new cell button
│   ├── editor/
│   │   └── MonacoEditor.tsx     # Monaco wrapper
│   ├── chart/
│   │   ├── ChartRenderer.tsx    # ECharts renderer
│   │   └── ChartConfig.tsx      # Chart configuration panel
│   ├── sidebar/
│   │   ├── Sidebar.tsx          # Main sidebar container
│   │   ├── DataExplorer.tsx     # Database/table/column tree
│   │   ├── KnowledgePanel.tsx   # Knowledge graph viewer
│   │   └── NotebookList.tsx     # Notebook listing
│   ├── chat/
│   │   ├── ChatPanel.tsx        # LLM chat input
│   │   └── ChatMessage.tsx      # Chat message bubble
│   ├── common/
│   │   ├── Header.tsx           # App header with language toggle
│   │   ├── DataTable.tsx        # Tabular data display
│   │   ├── LoadingSpinner.tsx
│   │   └── ErrorBoundary.tsx
│   └── layout/
│       └── MainLayout.tsx       # App layout with sidebar
├── stores/              # Zustand state management
│   ├── notebookStore.ts # Notebook & cell state
│   ├── chatStore.ts     # Chat history state
│   ├── uiStore.ts       # UI preferences
│   └── datasourceStore.ts
├── hooks/
│   ├── useWebSocket.ts  # WebSocket connection hook
│   ├── useNotebook.ts   # Notebook operations hook
│   └── useAgent.ts      # Agent query hook
├── services/
│   ├── api.ts           # Axios HTTP client
│   └── websocket.ts     # WebSocket client
├── types/
│   └── index.ts         # TypeScript type definitions
└── utils/
    └── helpers.ts
```

---

## 4. Data Models

### 4.1 Database Schema (SQLAlchemy)

#### Enterprise Control Plane

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `workspaces` | Top-level tenant boundary | `id`, `slug`, `name`, `status` |
| `users` | Enterprise actor identity | `id`, `email`, `display_name`, `auth_provider` |
| `workspace_memberships` | Role assignment inside a workspace | `workspace_id`, `user_id`, `role` |
| `audit_events` | Immutable audit trail for governed actions | `workspace_id`, `actor_user_id`, `action`, `request_id`, `details` |

All tenant-owned product entities below are now filtered by `workspace_id`.

#### Notebook

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique notebook identifier |
| workspace_id | UUID (FK) | Owning workspace / tenant |
| title | String(256) | Notebook title |
| description | Text | Optional description |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last modification timestamp |

#### Cell

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique cell identifier |
| workspace_id | UUID (FK) | Owning workspace / tenant |
| notebook_id | UUID (FK) | Parent notebook |
| cell_type | Enum | `sql`, `python`, `chart`, `markdown` |
| source | Text | Cell source code/content |
| output | JSON | Execution output (stdout, data, errors) |
| position | Integer | Order within notebook |
| metadata | JSON | Cell-specific metadata (chart config, etc.) |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last modification timestamp |

#### DataSource

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique datasource identifier |
| workspace_id | UUID (FK) | Owning workspace / tenant |
| name | String(128) | Display name |
| ds_type | Enum | `sqlite`, `postgresql`, `mysql`, `csv`, `duckdb` |
| connection_string | Text | Encrypted connection string |
| metadata | JSON | Schema cache, table list |
| created_at | DateTime | Creation timestamp |

#### KnowledgeNode

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique node identifier |
| workspace_id | UUID (FK) | Owning workspace / tenant |
| node_type | Enum | `database`, `table`, `column`, `value`, `jargon`, `alias` |
| name | String(256) | Node name |
| parent_id | UUID (FK, nullable) | Parent node in the tree |
| components | JSON | Knowledge components (description, usage, tags, etc.) |
| embedding_id | String | ChromaDB embedding reference |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last modification timestamp |

### 4.2 In-Memory Models

#### InformationUnit (Inter-Agent Communication)

```python
@dataclass
class InformationUnit:
    id: str                  # UUID
    data_source: str         # Table/dataset identifier
    role: str                # Agent role (e.g., "SQL Agent")
    action: str              # Action performed (e.g., "generate_sql_query")
    description: str         # Summary of the action
    content: Any             # Output (SQL query, Python code, chart spec, etc.)
    timestamp: float         # Unix timestamp
    cell_id: Optional[str]   # Associated notebook cell
```

#### FSMState (Agent State Machine)

```python
@dataclass
class FSMState:
    agent_id: str
    state: Literal["wait", "execution", "finish"]
    transitions: List[str]   # Target agent IDs on edges
```

#### CellDependencyNode (DAG)

```python
@dataclass
class CellDependencyNode:
    cell_id: str
    cell_type: str
    variables_defined: Set[str]   # New variables created
    variables_referenced: Set[str] # External variables used
    ancestors: Set[str]            # Parent cell IDs
    descendants: Set[str]          # Child cell IDs
```

### 4.3 DSL Specification

The Domain-Specific Language for query translation:

```json
{
  "query": "show me the income of TencentBI this year",
  "rewritten_query": "Show the total income of TencentBI product for the year 2026",
  "dsl": {
    "MeasureList": [
      {"column": "shouldincome_after", "aggregation": "SUM", "alias": "total_income"}
    ],
    "DimensionList": [
      {"column": "prod_class4_name"}
    ],
    "ConditionList": [
      {"column": "prod_class4_name", "operator": "=", "value": "TencentBI"},
      {"column": "ftime", "operator": ">=", "value": "2026-01-01"}
    ],
    "OrderBy": [],
    "Limit": null,
    "ChartType": "bar"
  }
}
```

---

## 5. Module Design

### 5.1 Agent Framework

#### 5.1.1 BaseAgent

All agents inherit from `BaseAgent`, which provides:

- LLM client access
- Prompt template rendering
- Structured output parsing
- Error handling with retry logic
- Information unit creation

```
BaseAgent (ABC)
├── execute(query, context) → InformationUnit
├── _build_prompt(template, **kwargs) → str
├── _call_llm(messages) → str
├── _parse_output(raw) → Any
└── _create_info_unit(content) → InformationUnit
```

#### 5.1.2 ProxyAgent

The orchestrator agent that:
1. Receives user queries
2. Determines required tasks (via LLM classification)
3. Creates an FSM execution plan
4. Delegates subtasks to specialized agents
5. Manages inter-agent information flow
6. Assembles final results

#### 5.1.3 Specialized Agents

| Agent | Task | Input | Output |
|-------|------|-------|--------|
| SQLAgent | NL2SQL | NL query + schema + knowledge | SQL query string |
| PythonAgent | NL2DSCode | NL query + context + data | Python code string |
| ChartAgent | NL2VIS | NL query + data + DSL | ECharts/Vega-Lite JSON spec |
| InsightAgent | NL2Insight | NL query + data | Insight text + supporting evidence |
| EDAAgent | Exploratory analysis | Dataset reference | Statistical summary + recommendations |
| CleaningAgent | Data cleaning | Dataset + issues | Cleaning code + cleaned data |
| ReportAgent | Report generation | Analysis results | Markdown report |

### 5.2 Domain Knowledge Module

#### 5.2.1 Knowledge Generation (Map-Reduce)

**Map Phase**: For each historical script associated with a table:
1. Send script + schema + lineage to LLM
2. Extract knowledge components per DB/table/column
3. Self-calibration: LLM scores result (1-5), regenerate if < threshold

**Reduce Phase**: Aggregate all map results:
1. Synthesize into unified DB/table/column knowledge
2. Resolve conflicts, merge descriptions
3. Output final knowledge components

#### 5.2.2 Knowledge Graph

Tree-based structure stored in SQLite with ChromaDB embeddings:

```
Database Node
├── Table Node
│   ├── Column Node
│   │   └── Value Node
│   └── Column Node
│       └── Alias Node
└── Alias Node
```

Each node contains: `name`, `description`, `usage`, `tags`, and type-specific fields.

#### 5.2.3 Knowledge Retrieval (Coarse-to-Fine)

1. **Coarse-Grained**: Lexical search (FTS) + Semantic search (ChromaDB cosine similarity)
2. **Fine-Grained Ordering**: Weighted score = ω₁·lex_score + ω₂·sem_score + ω₃·llm_score
3. **Top-K Selection**: Return highest-scored nodes

#### 5.2.4 DSL Translation

Query → JSON DSL with fields: MeasureList, DimensionList, ConditionList, OrderBy, Limit, ChartType. Validated via JSON Schema.

### 5.3 Inter-Agent Communication

#### 5.3.1 Information Units

Structured 6-field format replacing unstructured NL:
- `data_source`: Dataset identifier
- `role`: Agent identity
- `action`: Behavior performed
- `description`: Action summary
- `content`: Agent output
- `timestamp`: Completion time

#### 5.3.2 Shared Information Buffer

- In-memory dict-based store keyed by agent role + timestamp
- Dynamic capacity expansion (doubles when full)
- TTL-based cleanup for outdated entries
- Thread-safe with asyncio locks

#### 5.3.3 FSM-based Execution Plan

Generated by ProxyAgent based on query analysis:
- Nodes = agents, Edges = information flow directions
- States: Wait → Execution → Finish
- Selective retrieval: each agent only receives relevant info from predecessors in the FSM

#### 5.3.4 Materialized Inter-Agent Handoffs

- The proxy agent now executes SQL-agent outputs when possible and stores a structured payload of `{query, result}` in the shared buffer
- Downstream chart, insight, and report agents receive both the raw SQL and a preview of the tabular result through `predecessor_info`, `data_info`, and `analysis_context`
- Agent-created notebook cells persist the generated source together with any materialized preview output so the notebook stays inspectable after orchestration finishes

### 5.4 Cell-based Context Management

#### 5.4.1 DAG Construction

1. **Identify variables**: Python cells → AST for globals; SQL cells → output DataFrame name
2. **Find references**: For each cell, identify external variables defined in other cells
3. **Build DAG**: Directed edges from defining cell to referencing cell

#### 5.4.2 Context Retrieval

- **Cell-level query**: Traverse ancestors in DAG
- **Notebook-level query**: Find data variable, locate defining cell, include descendants
- **Pruning**: Filter by task type (e.g., NL2DSCode → only Python cells)
- **Buffer retrieval**: Fetch associated info units for agent-generated cells

#### 5.4.3 Notebook Runtime Bundle

- A notebook runtime bundle is built from ordered cells and includes the dependency DAG, typed cell metadata, and adaptive retrieval helpers
- The dependency DAG only links a cell to the latest previous definition of a referenced variable, which preserves notebook execution order and avoids illegal forward references
- SQL cells can publish named notebook outputs with `-- output: variable_name`
- Python execution replays ancestor Python cell sources from cell-agent workspace files and injects upstream tabular outputs as DataFrames before running the active cell
- SQL execution runs in an isolated DuckDB connection seeded from workspace data sources and upstream notebook tables loaded from file-backed IPC payloads
- Chart cells validate `data_source` references against upstream notebook outputs before execution
- Markdown cells resolve placeholders such as `{{ sales_summary.row_count }}`, `{{ product_metrics.columns }}`, and `{{ product_metrics.preview }}`
- AI-edit requests reuse the same runtime bundle to build cell-specific context and preserve linkage contracts such as SQL output aliases, chart `data_source` references, and markdown placeholders

#### 5.4.4 Cell-Agent Runtime

- Every notebook cell is treated as a cell agent with its own workspace directory under `data/cell_agents/<workspace>/<notebook>/<position>-<type>-<id>/`
- Each execution request rebuilds a fresh DAG plan and executes only the target cell plus its ancestors in notebook order
- Every workspace contains `source.*`, `task.json`, `task.md`, `context.json`, `output.json`, and `inbox/` + `outbox/` folders
- Direct dependency messages are written as JSON files and copied from the producer cell's `outbox/` into the consumer cell's `inbox/`
- The frontend surfaces this runtime state through the `Cell Agent Runtime` panel on executed cells and through the right-side AI progress rail

---

## 6. API Specification

### 6.1 REST Endpoints

All REST requests are resolved against an enterprise context using:

- `X-DataLab-Workspace`
- `X-DataLab-User-Email`
- `X-Request-ID` (optional; generated if absent)

#### Enterprise

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/enterprise/context` | Resolve active workspace, user, role, and accessible workspaces |
| GET | `/api/enterprise/audit-events` | List recent audit events for owners/admins in the active workspace |

#### Notebooks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notebooks` | List all notebooks |
| POST | `/api/notebooks` | Create notebook |
| GET | `/api/notebooks/{id}` | Get notebook with cells |
| PUT | `/api/notebooks/{id}` | Update notebook metadata |
| DELETE | `/api/notebooks/{id}` | Delete notebook |

#### Cells

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/notebooks/{id}/cells` | Add cell to notebook |
| PUT | `/api/cells/{id}` | Update cell content |
| DELETE | `/api/cells/{id}` | Delete cell |
| POST | `/api/cells/{id}/execute` | Execute cell code |
| POST | `/api/cells/{id}/edit-with-ai` | Stream an AI rewrite for a specific cell |
| PUT | `/api/cells/{id}/move` | Reorder cell |

#### Agents

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agents/query` | Submit NL query to agent framework |
| GET | `/api/agents/status/{task_id}` | Get agent task status |

#### Knowledge

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/knowledge/generate` | Trigger knowledge generation for a datasource |
| GET | `/api/knowledge/search` | Search knowledge graph |
| GET | `/api/knowledge/graph/{datasource_id}` | Get knowledge graph |

#### Data Sources

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/datasources` | List data sources |
| POST | `/api/datasources` | Add data source |
| GET | `/api/datasources/{id}/schema` | Get schema (tables/columns) |
| POST | `/api/datasources/{id}/query` | Execute raw SQL |

### 6.2 Authorization And Scoping Rules

- Viewer and above: read notebooks, folders, datasources, and knowledge
- Analyst and above: create or mutate notebooks, cells, datasources, knowledge, and agent executions
- Admin and owner: read audit events
- All direct resource lookups (`/cells/{id}`, `/notebooks/{id}`, etc.) are filtered by `workspace_id`

### 6.3 WebSocket Protocol

Endpoint: `ws://host/ws/{notebook_id}`

Enterprise context is supplied through query parameters:

- `workspace`
- `user`

Messages follow the format:

```json
{
  "type": "cell_execute | agent_query | agent_progress | cell_update | error",
  "payload": { ... },
  "timestamp": 1709470800
}
```

**Client → Server**:
- `cell_execute`: `{ "cell_id": "...", "source": "..." }`
- `agent_query`: `{ "query": "...", "notebook_id": "...", "cell_id": "..." }`

**Server → Client**:
- `agent_progress`: `{ "task_id": "...", "status": "...", "agent": "...", "message": "..." }`
- `cell_update`: `{ "cell_id": "...", "output": {...}, "status": "success|error" }`
- `cell_create`: `{ "cell": { "id": "...", "type": "...", "source": "...", "position": N } }`

### 6.4 AI Edit Streaming

Endpoint: `POST /api/cells/{id}/edit-with-ai`

Response type: `text/event-stream`

Event sequence:

- `progress`: context, DAG, IPC, rewrite, generation, and validation progress updates
- `chunk`: incremental model tokens for the right-side draft panel
- `done`: sanitized final cell source plus cell-agent workspace details
- `error`: structured failure state for the cell progress panel

---

## 7. Frontend Design

### 7.1 State Management (Zustand)

#### NotebookStore
- `notebooks: Notebook[]`
- `activeNotebook: Notebook | null`
- `cells: Map<string, Cell>`
- `aiEditStateByCellId: Record<string, CellAIState>`
- Actions: `loadNotebook`, `addCell`, `updateCell`, `deleteCell`, `moveCell`, `executeCell`, `editCellWithAI`, `clearCellAIState`

#### ChatStore
- `messages: ChatMessage[]`
- `isLoading: boolean`
- Actions: `sendQuery`, `addMessage`, `clearHistory`

#### UIStore
- `sidebarOpen: boolean`
- `language: 'en' | 'zh'`
- `theme: 'light' | 'dark'`

#### EnterpriseStore
- `context: EnterpriseContext | null`
- `auditEvents: AuditEvent[]`
- `workspaceKey: string | null`
- Actions: `fetchContext`, `refreshAudit`, `setWorkspaceKey`

### 7.2 Component Hierarchy

```
App
└── MainLayout
    ├── Header (logo, workspace selector, role badge, language toggle, theme toggle)
    ├── Sidebar
    │   ├── NotebookList
    │   ├── DataExplorer (tree: DB → Table → Column)
    │   └── AuditPanel
    └── MainContent
        ├── Notebook
        │   ├── CellContainer (for each cell)
        │   │   ├── CellToolbar (run, delete, move, type badge)
        │   │   ├── SqlCell / PythonCell / ChartCell / MarkdownCell
        │   │   ├── CellOutput (data table, stdout, chart, rendered markdown)
        │   │   └── CellGenerationPanel (right-side AI progress and live draft)
        │   └── AddCellButton
        └── ChatPanel (floating, toggleable)
            ├── ChatMessage (user / assistant bubbles)
            └── ChatInput (text input + send button)
```

### 7.3 Cell Types

| Cell Type | Editor | Output |
|-----------|--------|--------|
| SQL | Monaco (SQL mode) | DataTable component |
| Python | Monaco (Python mode) | stdout + DataTable + images |
| Chart | JSON spec + notebook `data_source` binding | ECharts renderer |
| Markdown | Monaco (Markdown mode) | Rendered preview with resolved notebook placeholders |

---

## 8. Security & Sandboxing

### 8.1 Python Execution Sandbox

- Subprocess-based execution with timeout (default 30s)
- Prefers the project virtualenv interpreter when available to avoid host Python package drift
- Resource limits: memory (512MB), CPU time
- Restricted imports: block `os.system`, `subprocess`, `shutil.rmtree`, etc.
- Temp directory isolation per execution
- Output capture: stdout, stderr, generated files

### 8.2 SQL Execution

- DuckDB in-process for uploaded CSV/Parquet files
- Connection pooling for external databases
- Query timeout enforcement
- Read-only mode for exploration queries

### 8.3 API Security

- CORS configuration for frontend origin
- Rate limiting on agent query endpoints
- Input sanitization for all user-provided content

### 8.4 Enterprise Workspace Governance

- Trusted-header enterprise context resolution for user and workspace identity
- Role-based access control with `owner`, `admin`, `analyst`, and `viewer`
- Workspace scoping across notebooks, cells, folders, datasources, and knowledge nodes
- Governed WebSocket admission based on workspace membership and notebook ownership

### 8.5 Auditability And Traceability

- Every mutating REST action emits an `audit_events` record
- Each request is tagged with an `X-Request-ID` response header
- The admin UI exposes a recent audit feed for operational review
- Audit payloads record resource type, resource id, actor, action, and structured details

---

## 9. Internationalization

### 9.1 Frontend (react-i18next)

All user-facing strings stored in `en.json` and `zh.json`:

```json
{
  "notebook": {
    "title": "Notebook / 笔记本",
    "addCell": "Add Cell / 添加单元格",
    "execute": "Run / 运行"
  },
  "chat": {
    "placeholder": "Ask a question about your data... / 问一个关于数据的问题...",
    "send": "Send / 发送"
  }
}
```

### 9.2 Backend

- Error messages include both EN and ZH versions
- LLM prompts are in English (best LLM performance)
- API responses include a `locale` field for client-side rendering

---

## 10. Deployment

### 10.1 Development

```bash
# Backend
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

### 10.2 Docker Compose

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: ["./data:/app/data"]
    environment:
      - DATABASE_URL=sqlite:///./data/datalab.db
      - LITELLM_MODEL=gpt-4o

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
```

### 10.3 Enterprise Deployment Notes

- Production deployments should terminate identity at a trusted upstream gateway or SSO layer and inject `X-DataLab-Workspace` plus `X-DataLab-User-Email`
- Audit events should be exported to centralized logging or SIEM storage
- SQLite remains suitable for demos; production enterprise deployments should use PostgreSQL

### 10.4 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/datalab.db` | Database connection |
| `LITELLM_MODEL` | `gpt-4o` | Default LLM model |
| `OPENAI_API_KEY` | (required) | OpenAI API key |
| `ANTHROPIC_API_KEY` | (optional) | Anthropic API key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | ChromaDB storage path |
| `SANDBOX_TIMEOUT` | `30` | Python execution timeout (seconds) |
| `SANDBOX_MEMORY_MB` | `512` | Python execution memory limit |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `DEFAULT_WORKSPACE_SLUG` | `demo-hq` | Bootstrapped local workspace slug |
| `DEFAULT_WORKSPACE_NAME` | `Demo HQ` | Bootstrapped local workspace name |
| `DEFAULT_USER_EMAIL` | `admin@datalab.local` | Bootstrapped local enterprise user |
