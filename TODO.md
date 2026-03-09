# DataLab - TODO & Issues List

Generated from comprehensive code review on 2026-03-09. Updated with fixes on 2026-03-09.

**Note**: PythonCell editor is intentionally `readOnly` — this is by design (AI-generated code only).

---

## Critical Bugs

- ~~**SharedBuffer asyncio.Lock is never acquired**~~ **FIXED**: All mutating methods (`store`, `retrieve_*`, `update`, `clear`) are now `async` and properly acquire `self._lock` via `async with`.
- ~~**WebSocket execution skips cell-agent architecture**~~ **FIXED**: `_handle_cell_execute` now uses `CellRuntime.execute_target()` with full DAG resolution, database persistence, and broadcasts results for all executed dependency cells.
- ~~**knowledge/graph.py method signature mismatches**~~ **FIXED**: Added `workspace_id` parameter to `add_node`, `get_tree`, `get_nodes_by_datasource`, `populate_from_knowledge`, `delete_for_datasource` in `graph.py` and `retrieve` in `retriever.py`. Also improved `populate_from_knowledge` to support multi-table knowledge format.
- ~~**Cell source updates trigger no debounce**~~ **FIXED**: `updateCellSource` now applies an optimistic local state update immediately and debounces the API call by 400ms.

---

## Design & Architecture Issues

- ~~**Dual execution paths are inconsistent**~~ **FIXED**: Both REST and WebSocket cell execution now use the same `CellRuntime` with DAG resolution.
- **No authentication or authorization**: Despite the User model existing in the database schema, there are zero authentication checks on any endpoint. Any client can read, modify, or delete any resource.
- **Global singleton abuse**: Many modules use module-level singletons (`sql_executor`, `python_executor`, `chatbi_agent`, `knowledge_graph`, etc.) which makes testing difficult and prevents multi-tenant isolation.
- **No database migrations**: Alembic is configured with `env.py` and `script.py.mako` but there are no actual migration files. The app uses `Base.metadata.create_all` which doesn't support schema evolution.
- **Synchronous DuckDB blocks async event loop**: `sql_executor.execute()` and `execute_isolated()` are synchronous methods called from async FastAPI handlers. Large queries will block the entire event loop.
- **cell_runtime workspace grows unbounded**: The `data/cell_runtime/` directory accumulates workspace files with no cleanup mechanism. There is no TTL, size limit, or garbage collection.
- **FSM/CommunicationProtocol are dead code**: The FSM, CommunicationProtocol, and SharedBuffer are fully implemented but never used in practice since there is no ProxyAgent to orchestrate multi-agent workflows.
- **ChatStore doesn't pass notebook_id in WebSocket messages**: `sendQuery` in `chatStore.ts` sends `agent_query` via WebSocket but doesn't include `notebook_id` in the payload. The WebSocket handler gets it from the URL path instead, which works but is fragile.

---

## SDD vs Implementation Gaps

These items were described in the SDD but do not exist in the codebase:

- **ProxyAgent**: The SDD describes a ProxyAgent that orchestrates specialized agents via FSM. Only ChatBIAgent exists.
- **Specialized agents**: SQLAgent, ChartAgent, InsightAgent, EDAAgent, CleaningAgent, ReportAgent are described in the SDD but not implemented. Only PythonAgent and ChatBIAgent exist.
- **Enterprise modules**: The SDD described `enterprise/` directory with `auth.py`, `audit.py`, `resources.py`, and models like `workspace.py`, `membership.py`, `audit.py`. None exist.
- **Enterprise API endpoints**: `/api/enterprise/context` and `/api/enterprise/audit-events` do not exist.
- **Workspace scoping**: Models should have `workspace_id` columns according to the SDD but don't.
- **RBAC guards**: No role-based access control on any endpoint.
- **Audit logging**: No `audit_events` table or mutation logging.
- **Frontend EnterpriseStore**: Described in SDD but doesn't exist.
- **Frontend datasourceStore**: Described in SDD but doesn't exist.
- **Frontend hooks**: `useWebSocket.ts`, `useNotebook.ts`, `useAgent.ts` described but don't exist.
- **Frontend components**: `ChartConfig.tsx`, `DataExplorer.tsx`, `KnowledgePanel.tsx`, `NotebookList.tsx`, `ChatMessage.tsx` described but don't exist.
- **ChromaDB integration**: Listed as a dependency and configured (`chroma_persist_dir`) but never imported or used anywhere. The `embedding_id` field on KnowledgeNode is unused. Semantic search uses character-set overlap instead.
- **Vega-Lite**: SDD mentions ECharts + Vega-Lite but only ECharts is implemented.
- **shadcn/ui**: SDD mentions shadcn/ui but only Radix primitives and Tailwind are used directly.

---

## Security Issues

- **No authentication**: All endpoints are publicly accessible.
- **Arbitrary SQL execution**: `/api/datasources/{id}/query` accepts and executes any SQL string without sanitization or restrictions.
- **No rate limiting**: Despite SDD mentioning it, no rate limiting is implemented on any endpoint.
- **Connection strings in plaintext**: `DataSource.connection_string` stores credentials in plaintext in the database.
- **Python sandbox has no import restrictions**: Despite SDD claiming `os.system`, `subprocess`, etc. are blocked, the actual executor has no import restrictions.
- **Python sandbox has no resource limits**: `SANDBOX_MEMORY_MB` is configured but never enforced at the OS level. No `ulimit`, `cgroups`, or similar.
- **No CORS restriction enforcement in production**: CORS origins include `localhost:5171`, `localhost:5173`, `localhost:3000` which is fine for dev but not for production.

---

## Backend Code Issues

- `**config.py` loads `.env` twice**: Once via `load_dotenv()` at module level and again via pydantic-settings `env_file` parameter. Remove the redundant `load_dotenv()` call.
- `**_set_sqlite_pragma` listener fires for all databases**: The SQLite WAL pragma listener is unconditionally registered on the engine. It will fail or produce warnings when using PostgreSQL.
- **DuckDB connections are never closed**: `SQLExecutor._connections` dict accumulates connections that are never cleaned up. Only `execute_isolated` properly closes its connections.
- `**python-dotenv` missing from dependencies**: `config.py` imports `from dotenv import load_dotenv` but `python-dotenv` is not listed in `pyproject.toml`.
- `**format_cells_for_llm` uses `cell['cell_id']`**: In `notebook_runtime.py`, this function references `cell['cell_id']` but cells are stored with key `'id'`. This will cause KeyError if a cell dict doesn't have `cell_id`.
- ~~`**knowledge/graph.py:populate_from_knowledge` creates only one table node**~~ **FIXED**: Now supports both single-table `{"table": {...}}` and multi-table `{"tables": [...]}` knowledge formats.
- `**knowledge/retriever.py:_semantic_score` is a placeholder**: Uses character-set overlap (Jaccard on characters) instead of actual semantic/vector similarity. This provides very weak semantic matching.
- `**execute_isolated` loads all datasources into every query**: For each cell execution, all workspace datasources are imported into the isolated DuckDB connection, even if the query doesn't reference them.
- **Missing `__init__.py` in `backend/app/utils/`**: The utils directory has `helpers.py` but no `__init__.py`.
- `**llm/tools.py` definitions are never used**: Tool definitions for `execute_sql`, `execute_python`, `generate_chart`, `create_cell` exist but no agent uses function calling.
- **Prompt templates `task_routing.j2` and `chat_generation.j2` are unused**: These templates exist but no code references them.
- `**knowledge/graph.py:get_tree` can be very slow**: Recursive database queries with no depth limit. Large knowledge graphs will cause N+1 query problems.

---

## Frontend Code Issues

- **No error recovery on WebSocket disconnect**: The WebSocket client auto-reconnects but doesn't re-fetch state or notify the user of missed updates.
- ~~**No debouncing on cell source updates**~~ **FIXED**: Cell source updates now debounce API calls by 400ms with optimistic local state.
- **Chat panel doesn't work without active notebook**: The send button is disabled but the UX doesn't clearly communicate why.
- **No loading indicator for notebook list**: When notebooks are being fetched, there's no visual loading state in the sidebar.
- **Missing type safety in ChartCell**: `resolveNotebookChartOption` uses `Record<string, unknown>` and type assertions extensively. Better typing would prevent runtime errors.
- **Large notebook performance**: All cells render simultaneously with no virtualization. Notebooks with many cells will be slow.
- **No keyboard shortcuts**: No Ctrl+Enter to run a cell, no Ctrl+S to save, etc.
- **Markdown cell renders `output.html` fallback**: `MarkdownCell.tsx` checks `(cell.output as any)?.html` with unsafe type assertion.
- **Chat messages accumulate without limit**: No pagination or cleanup for the chat message list.

---

## Testing Gaps

- **No tests for knowledge module**: Knowledge generation, graph, retrieval, profiler, and DSL are untested.
- **No tests for WebSocket handler**: Chat and real-time cell execution over WebSocket have no test coverage.
- **No tests for AI edit streaming**: The SSE-based AI edit endpoint has no test coverage.
- **No frontend tests**: Zero test files for React components, stores, or services.
- **No integration tests**: No end-to-end tests for the full query flow (NL -> SQL -> execution -> chart).

---

## Infrastructure & DevOps

- **Docker Compose uses deprecated `version: "3.9"`**: Docker Compose v2 ignores the version field; remove it.
- **No health check in Docker Compose**: Backend service has no health check defined. Frontend depends on backend but can start before backend is ready.
- **No `.dockerignore` files**: Build contexts may include unnecessary files (node_modules, data, .git).
- **Frontend Dockerfile not verified**: No nginx config or multi-stage build visible in the project, but the SDD references one.
- `**vite.config.ts` has hardcoded `allowedHosts`**: Contains `bi-datalab.cpolar.top` which is environment-specific and shouldn't be in version control.
- **No CI/CD configuration**: No GitHub Actions, GitLab CI, or similar pipeline defined.
- **No Makefile**: The TODO.md Phase 1 marks "Makefile with dev commands" as complete but no Makefile exists.
- **No `.gitignore`**: The TODO.md Phase 1 marks ".gitignore" as complete but it should be verified.

---

## Future Enhancements (from original TODO_SDD.md)

### Agent Framework

- Implement full FSM orchestration with ProxyAgent routing to specialized agents
- Add advanced error recovery with self-correction loops
- Add shared buffer persistence for long-running sessions

### Cell Runtime

- Implement workspace lifecycle management (TTL-based cleanup)
- Enhance variable tracking for complex Python patterns (globals(), dynamic attributes)
- Add incremental DAG rebuilds (only re-analyze changed cells)
- Support per-notebook virtual environments

### Knowledge Module

- Integrate ChromaDB embeddings for actual semantic search
- Implement coarse-to-fine retrieval with real vector similarity
- Add automated jargon extraction from documentation

### Execution Engines

- Transition to production-grade sandboxing (gVisor, Firecracker, or Docker)
- Optimize DuckDB for large-scale OLAP
- Make all SQL execution async to prevent event loop blocking

### Frontend & UX

- Add real-time collaboration (CRDT/OT)
- Expand chart builder with GUI configuration panel
- Add cell hiding and grouping
- Add interactive data profiling
- Add keyboard shortcuts (Ctrl+Enter, Ctrl+S, etc.)
- Add cell output virtualization for large notebooks

### Enterprise Features

- Implement RBAC with workspace, user, membership models
- Add audit logging for all mutations
- Add SSO/OIDC integration
- Add workspace administration APIs
- Add rate limiting and usage metering

