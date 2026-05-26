"use client";

import type { TestingSnapshot } from "@/types/testing";
import type { BrowserState } from "@/types";
import { BrowserPreview } from "@/components/browser/BrowserPreview";
import { TestCaseEditor } from "./TestCaseEditor";
import ExecutionDashboard from "./ExecutionDashboard";
import { OverviewPanel } from "./OverviewPanel";

interface Props {
  snapshot: TestingSnapshot | undefined;
  sessionId: string | null;
  // BrowserPreview props — passed through when panel_mode is 'browser'
  browserState: BrowserState;
  currentIndex?: number;
  totalCount?: number;
  onPrev?: () => void;
  onNext?: () => void;
  onNavigate?: (url: string) => void;
  onBack?: () => void;
  onForward?: () => void;
  onRefresh?: () => void;
  // Testing callbacks
  onConfirm?: () => void;
  onCancel?: () => void;
  onPlanUpdate?: (plan: NonNullable<TestingSnapshot["test_plan"]>) => void;
  onViewPlan?: (plan: NonNullable<TestingSnapshot["test_plan"]>) => void;
  onViewRun?: (runId: string) => void;
}

export function TestingPanel({
  snapshot,
  sessionId,
  browserState,
  currentIndex,
  totalCount,
  onPrev,
  onNext,
  onNavigate,
  onBack,
  onForward,
  onRefresh,
  onConfirm,
  onCancel,
  onPlanUpdate,
  onViewPlan,
  onViewRun,
}: Props) {
  const mode = snapshot?.panel_mode ?? "browser";

  if (mode === "case_editor" && snapshot?.test_plan) {
    return (
      <TestCaseEditor
        plan={snapshot.test_plan}
        sessionId={sessionId || ""}
        onConfirm={onConfirm ?? (() => {})}
        onCancel={onCancel ?? (() => {})}
        onPlanUpdate={onPlanUpdate ?? (() => {})}
        onBack={onCancel}
      />
    );
  }

  if (mode === "execution" && snapshot?.run_progress && snapshot?.case_statuses) {
    return (
      <ExecutionDashboard
        runProgress={snapshot.run_progress}
        caseStatuses={snapshot.case_statuses}
        onBack={onCancel}
      />
    );
  }

  if (mode === "execution") {
    return (
      <div className="flex flex-col h-full items-center justify-center text-sm text-gray-500 bg-white">
        <div className="animate-pulse text-2xl mb-2">⚙️</div>
        <p>执行中...</p>
      </div>
    );
  }

  if (mode === "report") {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8888/api";
    const reportUrl = snapshot?.report_url
      ? `${API_BASE}${snapshot.report_url}`
      : null;

    return (
      <div className="flex flex-col h-full bg-white">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200">
          <div className="flex items-center gap-2">
            {onCancel && (
              <button
                onClick={onCancel}
                className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
              >
                ← 返回
              </button>
            )}
            <span className="text-sm font-medium text-gray-700">测试报告</span>
          </div>
          {reportUrl && (
            <div className="flex gap-2">
              <a
                href={`${reportUrl}/excel`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-2 py-1 text-xs bg-green-50 text-green-600 border border-green-200 rounded hover:bg-green-100"
              >
                Excel
              </a>
            </div>
          )}
        </div>
        {reportUrl ? (
          <iframe
            src={reportUrl}
            className="flex-1 w-full border-0"
            title="Test Report"
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-gray-400">
            报告生成中...
          </div>
        )}
      </div>
    );
  }

  // Default: show overview if no active browser screenshot, otherwise browser
  if (!browserState?.screenshot) {
    return <OverviewPanel onViewPlan={onViewPlan} onViewRun={onViewRun} />;
  }

  return (
    <BrowserPreview
      state={browserState}
      currentIndex={currentIndex}
      totalCount={totalCount}
      onPrev={onPrev}
      onNext={onNext}
      onNavigate={onNavigate}
      onBack={onBack}
      onForward={onForward}
      onRefresh={onRefresh}
    />
  );
}
