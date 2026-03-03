# DataLab - Development Task List

## Phase 0: Documentation
- [x] Write Software Design Document (SDD.md)
- [x] Create README.md

## Phase 1: Project Scaffolding
- [x] Backend directory structure
  - [x] FastAPI project layout
  - [x] pyproject.toml with dependencies
  - [x] Alembic migration setup
  - [x] Dockerfile
- [x] Frontend directory structure
  - [x] Vite + React + TypeScript setup
  - [x] Tailwind CSS configuration
  - [x] Package.json with dependencies
  - [x] Dockerfile + nginx config
- [x] Docker Compose configuration
- [x] Makefile with dev commands
- [x] .gitignore

## Phase 2: Backend Core
- [x] Configuration management (Pydantic Settings)
- [x] Database setup (SQLAlchemy async engine)
- [x] ORM Models
  - [x] Notebook model
  - [x] Cell model
  - [x] DataSource model
  - [x] KnowledgeNode model
- [x] Pydantic schemas (request/response)
- [x] LLM client (LiteLLM wrapper)
- [x] Execution engines
  - [x] Python sandbox executor
  - [x] SQL executor (DuckDB)

## Phase 3: Agent Framework
- [x] BaseAgent abstract class
- [x] Prompt template system (Jinja2)
- [x] ProxyAgent (query router + FSM planner)
- [x] SQLAgent (NL2SQL)
- [x] PythonAgent (NL2DSCode)
- [x] ChartAgent (NL2VIS)
- [x] InsightAgent (NL2Insight)
- [x] EDAAgent (Exploratory Data Analysis)
- [x] CleaningAgent (Data Cleaning)
- [x] ReportAgent (Report Generation)

## Phase 4: Domain Knowledge Module
- [x] Knowledge generation (Map-Reduce with self-calibration)
  - [x] Map phase: per-script knowledge extraction
  - [x] Self-calibration scoring loop
  - [x] Reduce phase: knowledge synthesis
- [x] Knowledge graph
  - [x] Tree-based node structure (DB → Table → Column → Value)
  - [x] Alias node support
  - [x] CRUD operations
- [x] Knowledge retrieval
  - [x] Coarse-grained: lexical + semantic search
  - [x] Fine-grained: weighted scoring
  - [x] Top-K selection
- [x] Data profiler (fallback for tables without scripts)
- [x] DSL translation (NL → JSON DSL)

## Phase 5: Inter-Agent Communication
- [x] InformationUnit data structure
- [x] SharedInformationBuffer
  - [x] Store/retrieve operations
  - [x] Dynamic capacity expansion
  - [x] TTL-based cleanup
- [x] FSM execution plan
  - [x] State machine definition (Wait/Execution/Finish)
  - [x] Transition management
  - [x] Agent task orchestration
- [x] Communication protocol
  - [x] Selective information retrieval
  - [x] FSM-based info routing

## Phase 6: Cell-based Context Management
- [x] Variable tracker
  - [x] Python AST parsing for global variables
  - [x] SQL SELECT output tracking
- [x] DAG construction
  - [x] Build dependency graph from variable references
  - [x] Dynamic updates on cell changes
- [x] Context retrieval
  - [x] Cell-level: ancestor traversal
  - [x] Notebook-level: descendant traversal
  - [x] Task-type-based pruning
  - [x] Buffer info unit retrieval

## Phase 7: REST + WebSocket API
- [x] Notebook CRUD endpoints
- [x] Cell CRUD + execution endpoints
- [x] Agent query endpoint
- [x] Knowledge management endpoints
- [x] DataSource endpoints
- [x] WebSocket handler
  - [x] Cell execution streaming
  - [x] Agent progress updates

## Phase 8: Frontend - Notebook UI
- [x] App shell (router, layout)
- [x] Main layout with sidebar
- [x] Notebook container
- [x] Cell components
  - [x] SQL cell with Monaco editor + results table
  - [x] Python cell with Monaco editor + output
  - [x] Chart cell with GUI config + ECharts preview
  - [x] Markdown cell with editor + rendered preview
- [x] Cell toolbar (run, delete, move, type badge)
- [x] Add cell button (type selector)
- [x] Drag-and-drop cell reordering

## Phase 9: Frontend - Features
- [x] LLM Chat panel
  - [x] Chat input with send button
  - [x] Message bubbles (user/assistant)
  - [x] Streaming response display
- [x] Chart builder
  - [x] ECharts renderer component
  - [x] Chart configuration panel (axes, filters, colors)
- [x] Data explorer sidebar
  - [x] Database/table/column tree view
  - [x] Table schema preview
- [x] Notebook list sidebar
- [x] Internationalization (i18n)
  - [x] English translations
  - [x] Chinese translations
  - [x] Language toggle in header
- [x] Dark mode toggle
- [x] State management (Zustand stores)

## Phase 10: Integration & Polish
- [x] Connect frontend API client to backend
- [x] WebSocket integration for real-time updates
- [x] End-to-end query flow testing
- [x] Error handling & user feedback
- [x] Loading states & animations
- [x] Responsive layout adjustments
- [x] SVG logo/favicon
