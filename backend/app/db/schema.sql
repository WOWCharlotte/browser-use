CREATE TABLE IF NOT EXISTS sessions (
	id TEXT PRIMARY KEY,
	title TEXT NOT NULL,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
	id TEXT PRIMARY KEY,
	session_id TEXT NOT NULL,
	role TEXT NOT NULL,
	content TEXT NOT NULL,
	attachments TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS browser_states (
	id TEXT PRIMARY KEY,
	session_id TEXT NOT NULL,
	url TEXT,
	title TEXT,
	screenshot TEXT,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_browser_states_session_id ON browser_states(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);

CREATE TABLE IF NOT EXISTS test_plans (
	id TEXT PRIMARY KEY,
	name TEXT NOT NULL,
	description TEXT,
	source_file_name TEXT,
	max_concurrency INTEGER DEFAULT 3,
	status TEXT DEFAULT 'draft',
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_cases (
	id TEXT PRIMARY KEY,
	plan_id TEXT NOT NULL,
	case_name TEXT NOT NULL,
	description TEXT,
	module TEXT,
	function_point TEXT,
	start_url TEXT NOT NULL,
	steps_json TEXT NOT NULL,
	global_variables TEXT,
	variable_values_json TEXT,
	status TEXT DEFAULT 'pending',
	execution_order INTEGER,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (plan_id) REFERENCES test_plans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS test_case_variable_sets (
	id TEXT PRIMARY KEY,
	case_id TEXT NOT NULL,
	set_index INTEGER NOT NULL,
	variables_json TEXT NOT NULL,
	status TEXT DEFAULT 'pending',
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (case_id) REFERENCES test_cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS test_runs (
	id TEXT PRIMARY KEY,
	plan_id TEXT NOT NULL,
	status TEXT DEFAULT 'running',
	max_concurrency INTEGER DEFAULT 3,
	max_retries INTEGER DEFAULT 1,
	case_timeout_seconds INTEGER DEFAULT 600,
	case_ids_filter TEXT,
	rerun_of_run_id TEXT,
	total_cases INTEGER DEFAULT 0,
	passed_cases INTEGER DEFAULT 0,
	failed_cases INTEGER DEFAULT 0,
	error_cases INTEGER DEFAULT 0,
	started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	completed_at DATETIME,
	FOREIGN KEY (plan_id) REFERENCES test_plans(id)
);

CREATE TABLE IF NOT EXISTS test_results (
	id TEXT PRIMARY KEY,
	run_id TEXT NOT NULL,
	case_id TEXT NOT NULL,
	variable_set_id TEXT,
	session_id TEXT,
	status TEXT DEFAULT 'pending',
	actual_result TEXT,
	evaluation TEXT,
	evaluation_details TEXT,
	error_message TEXT,
	duration_seconds REAL,
	retry_count INTEGER DEFAULT 0,
	case_snapshot_json TEXT,
	original_status TEXT,
	override_reason TEXT,
	trajectory_path TEXT,
	started_at DATETIME,
	completed_at DATETIME,
	FOREIGN KEY (run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
	FOREIGN KEY (case_id) REFERENCES test_cases(id)
);

CREATE TABLE IF NOT EXISTS test_replays (
	id TEXT PRIMARY KEY,
	result_id TEXT NOT NULL,
	variables_json TEXT,
	status TEXT DEFAULT 'running',
	mode TEXT DEFAULT 'hybrid',
	fallback_count INTEGER DEFAULT 0,
	trajectory_path TEXT,
	started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
	completed_at DATETIME,
	FOREIGN KEY (result_id) REFERENCES test_results(id)
);

CREATE INDEX IF NOT EXISTS idx_test_cases_plan_id ON test_cases(plan_id);
CREATE INDEX IF NOT EXISTS idx_test_case_variable_sets_case_id ON test_case_variable_sets(case_id);
CREATE INDEX IF NOT EXISTS idx_test_runs_plan_id ON test_runs(plan_id);
CREATE INDEX IF NOT EXISTS idx_test_results_run_id ON test_results(run_id);
CREATE INDEX IF NOT EXISTS idx_test_results_case_id ON test_results(case_id);
CREATE INDEX IF NOT EXISTS idx_test_replays_result_id ON test_replays(result_id);
