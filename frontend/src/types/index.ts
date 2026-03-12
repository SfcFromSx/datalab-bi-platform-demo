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
  cell_id?: string;
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

export type ChatMode = 'chat' | 'design' | 'agent';

export type ChatStepType =
  | 'thinking'
  | 'sql'
  | 'executing'
  | 'data'
  | 'chart'
  | 'answer'
  | 'error'
  | 'action'
  | 'action_result'
  | 'plan'
  | 'agent_action'
  | 'agent_progress'
  | 'summary';

export interface DesignAction {
  action: 'add_cell' | 'edit_cell' | 'delete_cell' | 'move_cell' | 'execute_cell';
  cell_type?: CellType;
  cell_id?: string;
  source?: string;
  position?: number;
  description?: string;
}

export interface ChatStep {
  type: ChatStepType;
  content: string | TableData | Record<string, unknown> | DesignAction | DesignAction[];
  streaming?: boolean;
  applied?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  steps: ChatStep[];
  status: 'streaming' | 'done' | 'error';
  mode?: ChatMode;
}

export interface WSMessage {
  type: string;
  payload: Record<string, unknown>;
  timestamp?: number;
}

export type AgentTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface AgentTaskPlanStep {
  index: number;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  cell_id?: string;
  source?: string;
  duration_ms?: number;
  output_summary?: string;
  error?: string;
}

export interface AgentTask {
  id: string;
  notebook_id: string | null;
  datasource_id: string | null;
  query: string;
  status: AgentTaskStatus;
  plan: AgentTaskPlanStep[];
  progress: number;
  result: Record<string, unknown> | null;
  error: string | null;
  tokens_used: number;
  queries_executed: number;
  cells_created: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeNode {
  id: string;
  node_type: string;
  name: string;
  parent_id: string | null;
  components: Record<string, unknown> | null;
  children: KnowledgeNode[];
}

export interface ModelInfo {
  id: string;
  name: string;
  model: string;
  active: boolean;
}

export interface ChartConfig {
  chartType: 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap' | 'area';
  title?: string;
  xAxis?: string;
  yAxis?: string;
  series?: unknown[];
  option?: Record<string, unknown>;
}

export interface LLMLog {
  id: string;
  feature: string;
  model: string;
  messages: Array<Record<string, unknown>> | null;
  response: string | null;
  tokens_prompt: number;
  tokens_completion: number;
  duration_ms: number;
  status: 'success' | 'error';
  error: string | null;
  cell_id: string | null;
  notebook_id: string | null;
  created_at: string;
}

export interface LLMLogStats {
  total_calls: number;
  success_count: number;
  error_count: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  avg_duration_ms: number;
  by_feature: Record<string, number>;
  by_model: Record<string, number>;
}

