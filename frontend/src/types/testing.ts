// Types for the automated testing tool (Phase 3)

export type PanelMode = "browser" | "case_editor" | "execution" | "report";

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
}

export interface TestingSnapshot {
  panel_mode: PanelMode;
  test_plan?: TestPlanDetailView;
  run_progress?: {
    run_id: string;
    total: number;
    completed: number;
    passed: number;
    failed: number;
  };
  case_statuses?: Array<{
    result_id: string;
    case_id: string;
    case_name: string;
    status: "pending" | "running" | "passed" | "failed" | "error";
  }>;
  report_url?: string;
}
