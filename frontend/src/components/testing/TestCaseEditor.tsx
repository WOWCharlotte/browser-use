"use client";

import { useState, useCallback, useRef } from "react";
import type { TestPlanDetailView, TestCaseView, TestStepView, VariableSetView } from "@/types/testing";
import { updateTestCase, confirmTestPlan, getVariableSets, importVariableSets } from "@/lib/api";

interface Props {
  plan: TestPlanDetailView;
  onConfirm: () => void;
  onPlanUpdate: (plan: TestPlanDetailView) => void;
}

export function TestCaseEditor({ plan, onConfirm, onPlanUpdate }: Props) {
  const [selectedCaseId, setSelectedCaseId] = useState<string>(plan.cases[0]?.id ?? "");
  const [variableSets, setVariableSets] = useState<Record<string, VariableSetView[]>>({});
  const [savingCaseId, setSavingCaseId] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [savingVars, setSavingVars] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingVars, setLoadingVars] = useState<string | null>(null);
  // Track pending variable set rows being edited (before save)
  const [pendingVarRows, setPendingVarRows] = useState<Record<string, Array<Record<string, string>>>>({});
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // AbortController to cancel in-flight step-save requests on case switch
  const saveAbortRef = useRef<AbortController | null>(null);

  const selectedCase = plan.cases.find((c) => c.id === selectedCaseId) ?? plan.cases[0];

  // ── variable sets ──────────────────────────────────────────────────────────

  const loadVariableSets = useCallback(async (caseId: string) => {
    if (variableSets[caseId]) return;
    setLoadingVars(caseId);
    try {
      const sets = await getVariableSets(caseId);
      setVariableSets((prev) => ({ ...prev, [caseId]: sets }));
    } catch {
      // silently ignore — table will show empty
    } finally {
      setLoadingVars(null);
    }
  }, [variableSets]);

  const handleSelectCase = (caseId: string) => {
    // Cancel any in-flight save for the previous case to avoid stale updates
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveAbortRef.current?.abort();
    saveAbortRef.current = null;
    setSavingCaseId(null);
    setSelectedCaseId(caseId);
    loadVariableSets(caseId);
  };

  // ── step editing ───────────────────────────────────────────────────────────

  const scheduleStepSave = useCallback(
    (caseId: string, updatedSteps: TestStepView[]) => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(async () => {
        // Abort any previous in-flight request
        saveAbortRef.current?.abort();
        const controller = new AbortController();
        saveAbortRef.current = controller;

        setSavingCaseId(caseId);
        setError(null);
        try {
          const updated = await updateTestCase(caseId, { steps: updatedSteps });
          // Discard response if this request was superseded
          if (controller.signal.aborted) return;
          onPlanUpdate({
            ...plan,
            cases: plan.cases.map((c) => (c.id === caseId ? { ...c, steps: updated.steps } : c)),
          });
        } catch (e) {
          if (controller.signal.aborted) return;
          setError(`保存失败: ${e instanceof Error ? e.message : String(e)}`);
        } finally {
          if (!controller.signal.aborted) setSavingCaseId(null);
        }
      }, 300);
    },
    [plan, onPlanUpdate],
  );

  const handleStepChange = (
    caseId: string,
    stepIndex: number,
    field: keyof TestStepView,
    value: string | boolean,
  ) => {
    const currentCase = plan.cases.find((c) => c.id === caseId);
    if (!currentCase) return;
    const updatedSteps = currentCase.steps.map((s, i) =>
      i === stepIndex ? { ...s, [field]: value } : s,
    );
    // Optimistic update
    onPlanUpdate({
      ...plan,
      cases: plan.cases.map((c) => (c.id === caseId ? { ...c, steps: updatedSteps } : c)),
    });
    scheduleStepSave(caseId, updatedSteps);
  };

  // ── variable set form ──────────────────────────────────────────────────────

  const currentVarSets = selectedCase ? (variableSets[selectedCase.id] ?? []) : [];
  const globalVars = selectedCase?.global_variables ?? [];

  const handleAddVarRow = () => {
    if (!selectedCase) return;
    const empty = Object.fromEntries(globalVars.map((v) => [v, ""]));
    setPendingVarRows((prev) => ({
      ...prev,
      [selectedCase.id]: [...(prev[selectedCase.id] ?? []), empty],
    }));
  };

  const handlePendingVarChange = (rowIndex: number, varName: string, value: string) => {
    if (!selectedCase) return;
    setPendingVarRows((prev) => {
      const rows = [...(prev[selectedCase.id] ?? [])];
      rows[rowIndex] = { ...rows[rowIndex], [varName]: value };
      return { ...prev, [selectedCase.id]: rows };
    });
  };

  const handleSaveVarRows = async () => {
    if (!selectedCase) return;
    const rows = pendingVarRows[selectedCase.id] ?? [];
    if (rows.length === 0) return;
    setError(null);
    setSavingVars(true);
    try {
      // Filter each row to only include keys that are in global_variables
      const validKeys = new Set(selectedCase.global_variables);
      const filteredRows = rows.map((row) =>
        Object.fromEntries(
          Object.entries(row).filter(([k]) => validKeys.has(k)),
        ),
      );
      const saved = await importVariableSets(selectedCase.id, filteredRows);
      setVariableSets((prev) => ({
        ...prev,
        [selectedCase.id]: [...(prev[selectedCase.id] ?? []), ...saved],
      }));
      setPendingVarRows((prev) => ({ ...prev, [selectedCase.id]: [] }));
    } catch (e) {
      setError(`保存变量集失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSavingVars(false);
    }
  };

  // ── confirm ────────────────────────────────────────────────────────────────

  const handleConfirm = async () => {
    setConfirming(true);
    setError(null);
    try {
      await confirmTestPlan(plan.id);
      onConfirm();
    } catch (e) {
      setError(`确认失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setConfirming(false);
    }
  };

  // ── render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">{plan.name}</h2>
          <p className="text-xs text-gray-500">{plan.cases.length} 个用例</p>
        </div>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={confirming || plan.status !== "draft"}
          className="px-3 py-1.5 text-xs font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="确认测试计划"
        >
          {confirming ? "确认中..." : plan.status === "draft" ? "确认计划" : "已确认"}
        </button>
      </div>

      {error && (
        <div className="mx-4 mt-2 px-3 py-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-md">
          {error}
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        {/* Case list */}
        <div className="w-48 flex-shrink-0 border-r border-gray-200 overflow-y-auto">
          {plan.cases.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => handleSelectCase(c.id)}
              className={`w-full text-left px-3 py-2.5 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                c.id === selectedCaseId ? "bg-blue-50 border-l-2 border-l-blue-500" : ""
              }`}
            >
              <p className="text-xs font-medium text-gray-800 truncate">{c.case_name}</p>
              {c.module && <p className="text-xs text-gray-400 truncate">{c.module}</p>}
              <p className="text-xs text-gray-400">{c.steps.length} 步骤</p>
            </button>
          ))}
        </div>

        {/* Case detail */}
        {selectedCase ? (
          <div className="flex-1 overflow-y-auto">
            <CaseDetail
              testCase={selectedCase}
              varSets={currentVarSets}
              pendingVarRows={pendingVarRows[selectedCase.id] ?? []}
              loadingVars={loadingVars === selectedCase.id}
              savingSteps={savingCaseId === selectedCase.id}
              savingVars={savingVars}
              onStepChange={handleStepChange}
              onAddVarRow={handleAddVarRow}
              onPendingVarChange={handlePendingVarChange}
              onSaveVarRows={handleSaveVarRows}
            />
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-gray-400">
            暂无用例
          </div>
        )}
      </div>
    </div>
  );
}

// ── CaseDetail sub-component ──────────────────────────────────────────────────

interface CaseDetailProps {
  testCase: TestCaseView;
  varSets: VariableSetView[];
  pendingVarRows: Array<Record<string, string>>;
  loadingVars: boolean;
  savingSteps: boolean;
  savingVars: boolean;
  onStepChange: (caseId: string, stepIndex: number, field: keyof TestStepView, value: string | boolean) => void;
  onAddVarRow: () => void;
  onPendingVarChange: (rowIndex: number, varName: string, value: string) => void;
  onSaveVarRows: () => void;
}

function CaseDetail({
  testCase,
  varSets,
  pendingVarRows,
  loadingVars,
  savingSteps,
  savingVars,
  onStepChange,
  onAddVarRow,
  onPendingVarChange,
  onSaveVarRows,
}: CaseDetailProps) {
  const globalVars = testCase.global_variables;

  return (
    <div className="p-4 space-y-5">
      {/* Case meta */}
      <div>
        <h3 className="text-sm font-semibold text-gray-800">{testCase.case_name}</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          {testCase.start_url}
          {testCase.module && ` · ${testCase.module}`}
        </p>
        {savingSteps && <p className="text-xs text-blue-500 mt-1">保存中...</p>}
      </div>

      {/* Steps table */}
      <section>
        <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
          测试步骤
        </h4>
        <div className="border border-gray-200 rounded-md overflow-hidden">
          <table className="w-full text-xs" role="table">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-2 py-2 text-left text-gray-500 font-medium w-8">#</th>
                <th className="px-2 py-2 text-left text-gray-500 font-medium">操作描述</th>
                <th className="px-2 py-2 text-left text-gray-500 font-medium">预期结果</th>
                <th className="px-2 py-2 text-center text-gray-500 font-medium w-12">视觉</th>
              </tr>
            </thead>
            <tbody>
              {testCase.steps.map((step, idx) => (
                <tr key={step.step_number} className="border-t border-gray-100">
                  <td className="px-2 py-1.5 text-gray-400 align-top">{step.step_number}</td>
                  <td className="px-2 py-1.5 align-top">
                    <textarea
                      className="w-full text-xs text-gray-800 resize-none border-0 focus:outline-none focus:ring-1 focus:ring-blue-300 rounded p-0.5 min-h-[40px]"
                      value={step.action_description}
                      onChange={(e) =>
                        onStepChange(testCase.id, idx, "action_description", e.target.value)
                      }
                      aria-label={`步骤 ${step.step_number} 操作描述`}
                    />
                  </td>
                  <td className="px-2 py-1.5 align-top">
                    <textarea
                      className="w-full text-xs text-gray-600 resize-none border-0 focus:outline-none focus:ring-1 focus:ring-blue-300 rounded p-0.5 min-h-[40px]"
                      value={step.expected_result ?? ""}
                      placeholder="无预期结果"
                      onChange={(e) =>
                        onStepChange(testCase.id, idx, "expected_result", e.target.value)
                      }
                      aria-label={`步骤 ${step.step_number} 预期结果`}
                    />
                  </td>
                  <td className="px-2 py-1.5 text-center align-top">
                    <input
                      type="checkbox"
                      checked={step.is_visual_checkpoint}
                      onChange={(e) =>
                        onStepChange(testCase.id, idx, "is_visual_checkpoint", e.target.checked)
                      }
                      aria-label={`步骤 ${step.step_number} 视觉检查点`}
                      className="rounded"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Variable sets */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
            变量集
            {globalVars.length > 0 && (
              <span className="ml-1 text-gray-400 normal-case font-normal">
                ({globalVars.join(", ")})
              </span>
            )}
          </h4>
          {globalVars.length > 0 && (
            <button
              type="button"
              onClick={onAddVarRow}
              className="text-xs text-blue-600 hover:text-blue-800"
              aria-label="添加变量集行"
            >
              + 添加一行
            </button>
          )}
        </div>

        {globalVars.length === 0 ? (
          <p className="text-xs text-gray-400">该用例无变量</p>
        ) : loadingVars ? (
          <p className="text-xs text-gray-400">加载中...</p>
        ) : (
          <div className="border border-gray-200 rounded-md overflow-hidden">
            <table className="w-full text-xs" role="table">
              <thead className="bg-gray-50">
                <tr>
                  {globalVars.map((v) => (
                    <th key={v} className="px-2 py-2 text-left text-gray-500 font-medium">
                      {v}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* Saved rows */}
                {varSets.map((vs) => (
                  <tr key={vs.id} className="border-t border-gray-100">
                    {globalVars.map((v) => (
                      <td key={v} className="px-2 py-1.5 text-gray-700">
                        {vs.variables[v] ?? ""}
                      </td>
                    ))}
                  </tr>
                ))}
                {/* Pending (unsaved) rows */}
                {pendingVarRows.map((row, rowIdx) => (
                  <tr key={`pending-${rowIdx}`} className="border-t border-blue-100 bg-blue-50">
                    {globalVars.map((v) => (
                      <td key={v} className="px-1 py-1">
                        <input
                          type="text"
                          value={row[v] ?? ""}
                          onChange={(e) => onPendingVarChange(rowIdx, v, e.target.value)}
                          className="w-full text-xs border border-gray-200 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-300"
                          aria-label={`变量 ${v} 第 ${rowIdx + 1} 行`}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
                {/* Empty state */}
                {varSets.length === 0 && pendingVarRows.length === 0 && (
                  <tr>
                    <td
                      colSpan={globalVars.length}
                      className="px-2 py-3 text-center text-gray-400"
                    >
                      暂无变量集，点击"添加一行"填写
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {pendingVarRows.length > 0 && (
          <button
            type="button"
            onClick={onSaveVarRows}
            disabled={savingVars}
            className="mt-2 px-3 py-1 text-xs font-medium rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {savingVars ? "保存中..." : "保存变量集"}
          </button>
        )}
      </section>
    </div>
  );
}
