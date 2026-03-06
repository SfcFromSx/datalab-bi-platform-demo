export type CellType = 'sql' | 'python' | 'chart' | 'markdown';

export interface Cell {
  id: string;
  notebook_id: string;
  cell_type: CellType;
  source: string;
  output: CellOutput | null;
  position: number;
  metadata_: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CellOutput {
  status: 'success' | 'error';
  stdout?: string;
  stderr?: string;
  data?: TableData | null;
  error?: string | null;
  columns?: string[];
  rows?: unknown[][];
  row_count?: number;
  html?: string;
  chart?: {
    data_source?: string | null;
    columns?: string[];
    row_count?: number;
  };
  bindings?: string[];
  agent?: CellAgentRuntimeInfo | null;
}

export interface CellAIState {
  status: 'idle' | 'generating' | 'completed' | 'error';
  stage: string;
  message: string;
  progress: number;
  draft: string;
  prompt?: string;
  details?: CellAgentRuntimeInfo | null;
  error?: string | null;
}

export interface CellAgentRuntimeInfo {
  mode: string;
  run_id?: string;
  workspace_dir: string;
  source_file?: string;
  task_file?: string;
  context_file?: string;
  bootstrap_file?: string | null;
  output_file?: string;
  inbox_dir?: string;
  outbox_dir?: string;
  dependencies: string[];
  ancestors: string[];
  plan: string[];
  fingerprint?: string;
  input_messages?: number;
  published_messages?: number;
}

export interface CellExecuteResult {
  cell_id: string;
  status: string;
  output: CellOutput;
  executed_cells: Array<{
    cell_id: string;
    output: CellOutput;
  }>;
}

export interface TableData {
  columns: string[];
  rows: unknown[][];
  shape?: number[];
  variable?: string;
}

export interface Notebook {
  id: string;
  title: string;
  description: string;
  folder_id: string | null;
  created_at: string;
  updated_at: string;
  cells: Cell[];
}

export interface NotebookListItem {
  id: string;
  title: string;
  description: string;
  folder_id: string | null;
  created_at: string;
  updated_at: string;
  cell_count: number;
}

export interface Folder {
  id: string;
  name: string;
  position: number;
  created_at: string;
}

export interface DataSource {
  id: string;
  name: string;
  ds_type: string;
  metadata: Record<string, unknown> | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  cells_created?: CellCreated[];
}

export interface CellCreated {
  id?: string;
  cell_type: CellType;
  source: string;
  position?: number;
}

export interface AgentQueryResponse {
  task_id: string;
  status: string;
  message: string;
  cells_created: CellCreated[];
  cells_modified: CellCreated[];
}

export interface WSMessage {
  type: string;
  payload: Record<string, unknown>;
  timestamp?: number;
}

export interface KnowledgeNode {
  id: string;
  node_type: string;
  name: string;
  parent_id: string | null;
  components: Record<string, unknown> | null;
  children: KnowledgeNode[];
}

export interface ChartConfig {
  chartType: 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap' | 'area';
  title?: string;
  xAxis?: string;
  yAxis?: string;
  series?: unknown[];
  option?: Record<string, unknown>;
}

