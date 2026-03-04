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
