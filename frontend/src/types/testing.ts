// Types for the automated testing tool (Phase 3 + Phase 4)

export type PanelMode = "browser" | "case_editor" | "execution" | "report";

export type CaseStatus = "pending" | "running" | "paused" | "passed" | "failed" | "error";
export type RunStatus = "running" | "completed" | "aborted";

export interface TestStepView {
  step_number: number;
  action_description: string;
  expected_result: string | null;
  step_variables: string[];
  is_visual_checkpoint: boolean;
}

export interface VariableSetView {
  id: string;
  case_id: string;
  set_index: number;
  variables: Record<string, string>;
  status: string;
  created_at: string;
}

export interface TestCaseView {
  id: string;
  plan_id: string;
  case_name: string;
  description: string | null;
  module: string | null;
  function_point: string | null;
  start_url: string;
  steps: TestStepView[];
  global_variables: string[];
  variable_values: Record<string, string>;
  status: string;
  execution_order: number | null;
  created_at: string;
  updated_at: string;
}

export interface TestPlanDetailView {
  id: string;
  name: string;
  description: string | null;
  source_file_name: string | null;
  max_concurrency: number;
  status: string;
  created_at: string;
  updated_at: string;
  cases: TestCaseView[];
  case_count?: number;
}

export interface RunProgress {
  run_id: string;
  total: number;
  completed: number;
  passed: number;
  failed: number;
  error: number;
  started_at: string;
  status: RunStatus;
}

export interface CaseStatusEntry {
  result_id: string;
  case_id: string;
  case_name: string;
  status: CaseStatus;
}

export interface TestReplayView {
  id: string;
  result_id: string;
  variables_json: string | null;
  status: "running" | "passed" | "failed" | "error";
  mode: string;
  fallback_count: number;
  trajectory_path: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface RunHistoryEntry {
  run_id: string;
  status: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  error_cases: number;
  pass_rate: number;
  started_at: string;
  completed_at: string | null;
}

export interface TestingSnapshot {
  panel_mode: PanelMode;
  test_plan?: TestPlanDetailView;
  run_progress?: RunProgress;
  case_statuses?: CaseStatusEntry[];
  report_url?: string;
}
