"use client";

import type { TestingSnapshot } from "@/types/testing";
import type { BrowserState } from "@/types";
import { BrowserPreview } from "@/components/browser/BrowserPreview";
import { TestCaseEditor } from "./TestCaseEditor";

interface Props {
  snapshot: TestingSnapshot | undefined;
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
  onPlanUpdate?: (plan: NonNullable<TestingSnapshot["test_plan"]>) => void;
}

export function TestingPanel({
  snapshot,
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
  onPlanUpdate,
}: Props) {
  const mode = snapshot?.panel_mode ?? "browser";

  if (mode === "case_editor" && snapshot?.test_plan) {
    return (
      <TestCaseEditor
        plan={snapshot.test_plan}
        onConfirm={onConfirm ?? (() => {})}
        onPlanUpdate={onPlanUpdate ?? (() => {})}
      />
    );
  }

  if (mode === "execution") {
    return (
      <div className="flex flex-col h-full items-center justify-center text-sm text-gray-500 bg-white">
        <div className="animate-pulse text-2xl mb-2">⚙️</div>
        <p>执行中...</p>
        <p className="text-xs text-gray-400 mt-1">执行仪表板将在 Phase 8 实现</p>
      </div>
    );
  }

  if (mode === "report") {
    return (
      <div className="flex flex-col h-full items-center justify-center text-sm text-gray-500 bg-white">
        <div className="text-2xl mb-2">📊</div>
        <p>报告生成中...</p>
        <p className="text-xs text-gray-400 mt-1">报告面板将在 Phase 8 实现</p>
      </div>
    );
  }

  // Default: browser mode
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
