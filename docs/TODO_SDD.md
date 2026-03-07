# DataLab - Optimization TODO List (SDD)

This document outlines the planned optimizations and future work for the DataLab platform, as defined in the Software Design Document.

## 1. Agent Framework & Communication

- [ ] **Full FSM Orchestration**: Enhance `ProxyAgent` to implement the full Finite State Machine (FSM) logic for routing queries between multiple specialized agents (SQL, Python, Chart, etc.), rather than just calling the chat agent.
- [ ] **Advanced Error Recovery**: Implement self-correction loops where agents can analyze execution errors and retry with modified parameters or code.
- [ ] **Streaming Agent Progress**: Ensure all agents support granular progress updates via WebSockets to the frontend.
- [ ] **Shared Buffer Persistence**: Add an option to persist the `SharedBuffer` to a database for long-running multi-agent sessions.

## 2. Cell Runtime & Context Management

- [ ] **Workspace Lifecycle Management**: Implement a TTL-based or size-limited cleanup worker for the `data/cell_runtime` directory to prevent disk space exhaustion.
- [ ] **Enhanced Variable Tracking**: Improve the `variable_tracker` to handle more complex Python patterns (e.g., `globals()`, dynamic attribute access, and complex imports).
- [ ] **Incremental DAG Rebuilds**: Optimize the DAG builder to only re-analyze changed cells and their immediate dependencies.
- [ ] **Environment Isolation**: Support per-notebook or per-cell virtual environments (using `venv` or `conda`) to manage conflicting dependencies.

## 3. Knowledge Module

- [ ] **Map-Reduce Knowledge Generation**: Fully implement the Map-Reduce pipeline for extracting domain knowledge from historical scripts and schemas.
- [ ] **Coarse-to-Fine Retrieval**: Implement the weighted scoring mechanism (Lexical + Semantic + LLM) in the `KnowledgeRetriever`.
- [ ] **Automated Jargon Extraction**: Use LLMs to automatically identify and define domain-specific jargon from data documentation.

## 4. Execution Engines

- [ ] **Production Sandboxing**: Transition from simple subprocesses to more secure isolation (e.g., `gVisor`, `Firecracker`, or Docker containers) for production environments.
- [ ] **DuckDB Performance Tuning**: Optimize DuckDB configurations for large-scale in-memory OLAP operations.
- [ ] **Async SQL Execution**: Ensure all SQL executions are fully asynchronous to prevent blocking the main FastAPI event loop.

## 5. Frontend & UI/UX

- [ ] **Real-time Collaboration**: Implement CRDT-based or Operational Transformation (OT) synchronization for multi-user notebook editing.
- [ ] **Advanced Chart Builder**: Expand the GUI chart builder to support complex Vega-Lite grammars and more ECharts types.
- [ ] **Cell Hiding & Grouping**: Allow users to collapse or group cells for better notebook organization.
- [ ] **Interactive Data Profiling**: Add a visual data profiling tab for every tabular output (histograms, correlation matrices, etc.).

## 6. Enterprise Features

- [ ] **Full RBAC Implementation**: Solidify the Role-Based Access Control logic across all API endpoints.
- [ ] **Audit Log Visualization**: Create an admin dashboard for viewing and searching audit events.
- [ ] **SSO Integration**: Add support for OIDC/SAML providers for enterprise authentication.
