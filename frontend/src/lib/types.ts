export interface DocumentRecord {
  id: string;
  filename: string;
  status: 'completed' | 'processing' | 'failed';
  page_count: number | null;
  error: string | null;
  created_at: string;
  progress_percent: number;
  progress_stage: string | null;
  elapsed_seconds: number | null;
}

export interface OllamaStatusResponse {
  status: string;
  models?: string[];
  detail?: string;
}

export interface OllamaModelsResponse {
  status: string;
  default_model: string;
  models: string[];
  detail?: string;
}

export interface TreeNode {
  node_id: string;
  title: string;
  start_page: number;
  end_page: number;
  summary: string;
  nodes: TreeNode[];
  flags: Record<string, boolean>;
}

export interface TreeJSON {
  nodes: TreeNode[];
}

export interface TraceStep {
  step_index: number;
  action: string;
  node_id: string | null;
  pages: string | number[] | null;
  reason: string;
  created_at: string;
}

export interface ChatRecord {
  id: string;
  session_id: string;
  question: string;
  answer: string;
  created_at: string;
  trace_steps: TraceStep[];
}

export interface ChatSession {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface McpTool {
  name: string;
  description: string;
}

export interface McpTransportStdio {
  command: string;
  args: string[];
  cwd: string;
}

export interface McpTransportHttp {
  host: string;
  port: number;
  url: string;
  auth_required: boolean;
}

export interface McpInfo {
  installed: boolean;
  project_root: string;
  python_executable: string;
  stdio: McpTransportStdio;
  http: McpTransportHttp;
  inbox_dir: string;
  tools: McpTool[];
}

export interface McpHttpStatus {
  running: boolean;
  url: string;
  detail: string;
}
