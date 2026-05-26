"use client";

import { useState, useEffect, useMemo } from "react";
import type { TestPlanDetailView, RunHistoryEntry } from "@/types/testing";
import { fetchTestPlans, fetchPlanRuns, getTestPlan } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  confirmed: "bg-blue-100 text-blue-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  aborted: "bg-orange-100 text-orange-700",
};

interface PlanWithRuns {
  plan: TestPlanDetailView;
  runs: RunHistoryEntry[];
}

interface OverviewPanelProps {
  onViewPlan?: (plan: TestPlanDetailView) => void;
  onViewRun?: (runId: string) => void;
}

export function OverviewPanel({ onViewPlan, onViewRun }: OverviewPanelProps) {
  const [data, setData] = useState<PlanWithRuns[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedPlanId, setExpandedPlanId] = useState<string | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8888/api";

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const plans = await fetchTestPlans();
      const results: PlanWithRuns[] = await Promise.all(
        plans.map(async (plan) => {
          try {
            const runs = await fetchPlanRuns(plan.id);
            return { plan, runs };
          } catch {
            return { plan, runs: [] };
          }
        })
      );
      setData(results);
    } catch {
      setData([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(planId: string) {
    try {
      const res = await fetch(`${API_BASE}/test-plans/${planId}`, { method: "DELETE" });
      if (res.ok) {
        setData((prev) => prev.filter(({ plan }) => plan.id !== planId));
      }
    } catch {
      // ignore
    }
  }

  const stats = useMemo(() => {
    let totalPassed = 0;
    let totalFailed = 0;
    let totalError = 0;
    let totalCases = 0;

    for (const { runs } of data) {
      if (runs.length > 0) {
        const latest = runs[0]; // sorted DESC by started_at
        totalPassed += latest.passed_cases;
        totalFailed += latest.failed_cases;
        totalError += latest.error_cases;
        totalCases += latest.total_cases;
      }
    }

    const passRate = totalCases > 0 ? Math.round((totalPassed / totalCases) * 100) : 0;
    return { plans: data.length, totalPassed, totalFailed, totalError, passRate };
  }, [data]);

  const recentRuns = useMemo(() => {
    const all: (RunHistoryEntry & { plan_name: string })[] = [];
    for (const { plan, runs } of data) {
      for (const run of runs.slice(0, 3)) {
        all.push({ ...run, plan_name: plan.name });
      }
    }
    return all
      .sort((a, b) => (b.started_at || "").localeCompare(a.started_at || ""))
      .slice(0, 8);
  }, [data]);

  if (loading) {
    return (
      <div className="flex flex-col h-full bg-white p-4 space-y-4 animate-pulse">
        <div className="h-6 w-24 bg-gray-200 rounded" />
        <div className="grid grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-lg" />
          ))}
        </div>
        <div className="h-4 w-20 bg-gray-200 rounded" />
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 bg-gray-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col h-full items-center justify-center bg-white text-center p-8">
        <div className="text-4xl mb-3">📋</div>
        <p className="text-sm text-gray-600 mb-1">暂无测试计划</p>
        <p className="text-xs text-gray-400">在对话中上传测试用例文件开始</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto bg-white p-4 space-y-5">
      {/* Header */}
      <h2 className="text-sm font-medium text-gray-700">测试概览</h2>

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="计划" value={stats.plans} color="text-gray-700" />
        <StatCard label="通过" value={stats.totalPassed} color="text-green-600" />
        <StatCard label="失败" value={stats.totalFailed + stats.totalError} color="text-red-600" />
        <StatCard label="通过率" value={`${stats.passRate}%`} color="text-blue-600" />
      </div>

      {/* Recent runs */}
      {recentRuns.length > 0 && (
        <section>
          <h3 className="text-xs font-medium text-gray-500 mb-2">最近执行</h3>
          <div className="space-y-1.5">
            {recentRuns.map((run) => (
              <RunRow
                key={run.run_id}
                run={run}
                onClick={onViewRun ? () => onViewRun(run.run_id) : undefined}
              />
            ))}
          </div>
        </section>
      )}

      {/* Plans list */}
      <section>
        <h3 className="text-xs font-medium text-gray-500 mb-2">测试计划</h3>
        <div className="space-y-1.5">
          {data.map(({ plan, runs }) => (
            <PlanRow
              key={plan.id}
              plan={plan}
              runs={runs}
              isExpanded={expandedPlanId === plan.id}
              onToggle={() => setExpandedPlanId(expandedPlanId === plan.id ? null : plan.id)}
              onViewDetail={(() => {
                if (runs.length > 0 && onViewRun) {
                  return () => onViewRun(runs[0].run_id);
                }
                if (onViewPlan) {
                  return async () => {
                    try {
                      const fullPlan = await getTestPlan(plan.id);
                      onViewPlan(fullPlan);
                    } catch {
                      onViewPlan(plan);
                    }
                  };
                }
                return undefined;
              })()}
              onDelete={() => handleDelete(plan.id)}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="border border-gray-200 rounded-lg p-2.5 text-center">
      <div className={`text-lg font-semibold ${color}`}>{value}</div>
      <div className="text-[11px] text-gray-500">{label}</div>
    </div>
  );
}

function RunRow({ run, onClick }: { run: RunHistoryEntry & { plan_name: string }; onClick?: () => void }) {
  const date = run.started_at ? new Date(run.started_at).toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "";
  const statusIcon = run.status === "completed" ? "✓" : run.status === "aborted" ? "⚠" : "●";
  const statusColor = run.status === "completed" ? "text-green-500" : run.status === "aborted" ? "text-orange-500" : "text-blue-500";

  return (
    <div
      onClick={onClick}
      className={`flex items-center justify-between px-3 py-2 rounded border border-gray-100 hover:bg-gray-50 text-xs ${onClick ? "cursor-pointer" : ""}`}
    >
      <div className="flex items-center gap-2 min-w-0">
        <span className={statusColor}>{statusIcon}</span>
        <span className="text-gray-700 truncate">{run.plan_name}</span>
      </div>
      <div className="flex items-center gap-3 text-gray-500 flex-shrink-0">
        <span>{run.passed_cases}/{run.total_cases}</span>
        <span className={run.pass_rate >= 80 ? "text-green-600" : run.pass_rate >= 50 ? "text-yellow-600" : "text-red-600"}>
          {run.pass_rate}%
        </span>
        <span className="text-gray-400">{date}</span>
      </div>
    </div>
  );
}

function PlanRow({
  plan,
  runs,
  isExpanded,
  onToggle,
  onViewDetail,
  onDelete,
}: {
  plan: TestPlanDetailView;
  runs: RunHistoryEntry[];
  isExpanded: boolean;
  onToggle: () => void;
  onViewDetail?: () => void | Promise<void>;
  onDelete?: () => void;
}) {
  const statusClass = STATUS_COLORS[plan.status] || STATUS_COLORS.draft;
  const caseCount = plan.case_count ?? plan.cases?.length ?? 0;
  const latestRun = runs.length > 0 ? runs[0] : null;
  const isRunning = plan.status === "running" || (latestRun?.status === "running");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  return (
    <div className="rounded border border-gray-100 overflow-hidden">
      {/* Header row — clickable */}
      <div
        onClick={onToggle}
        className="flex items-center justify-between px-3 py-2 hover:bg-gray-50 text-xs cursor-pointer"
      >
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-gray-400 text-[10px]">{isExpanded ? "▼" : "▶"}</span>
          <span className="text-gray-700 truncate">{plan.name}</span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-gray-400">{caseCount} 用例</span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${statusClass}`}>
            {plan.status}
          </span>
        </div>
      </div>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="border-t border-gray-100 px-3 py-2 bg-gray-50 space-y-2">
          {/* Latest run result */}
          {latestRun && (
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-gray-500">最近执行:</span>
              <span className="flex items-center gap-2">
                <span className={latestRun.pass_rate >= 80 ? "text-green-600" : latestRun.pass_rate >= 50 ? "text-yellow-600" : "text-red-600"}>
                  通过率 {latestRun.pass_rate}%
                </span>
                <span className="text-gray-400">
                  ({latestRun.passed_cases}/{latestRun.total_cases})
                </span>
              </span>
            </div>
          )}

          {/* Case names (first 5) */}
          {plan.cases && plan.cases.length > 0 && (
            <div className="space-y-0.5">
              <span className="text-[11px] text-gray-500">用例:</span>
              {plan.cases.slice(0, 5).map((c) => (
                <div key={c.id} className="text-[11px] text-gray-600 pl-2 truncate">
                  · {c.case_name}
                </div>
              ))}
              {plan.cases.length > 5 && (
                <div className="text-[11px] text-gray-400 pl-2">
                  ... 还有 {plan.cases.length - 5} 条
                </div>
              )}
            </div>
          )}

          {/* Action button */}
          {onViewDetail && (
            <button
              onClick={(e) => { e.stopPropagation(); onViewDetail(); }}
              className="w-full mt-1 px-2 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded text-center"
            >
              {runs.length > 0 ? "查看执行结果" : "查看用例"}
            </button>
          )}

          {/* Delete button */}
          {onDelete && !showDeleteConfirm && (
            <button
              onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(true); }}
              disabled={isRunning}
              className="w-full px-2 py-1.5 text-xs border border-red-200 text-red-500 rounded hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed text-center"
              title={isRunning ? "执行中的计划无法删除" : ""}
            >
              {isRunning ? "执行中，无法删除" : "删除计划"}
            </button>
          )}
          {showDeleteConfirm && (
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[11px] text-red-600">确认删除？</span>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete?.(); setShowDeleteConfirm(false); }}
                className="px-2 py-0.5 text-xs bg-red-600 hover:bg-red-700 text-white rounded"
              >
                确认
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(false); }}
                className="px-2 py-0.5 text-xs bg-gray-200 hover:bg-gray-300 text-gray-700 rounded"
              >
                取消
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
