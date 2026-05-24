"use client";

import { useState, useCallback, useRef } from "react";
import type { TestPlanDetailView, TestCaseView, TestStepView, VariableSetView } from "@/types/testing";
import {
  updateTestCase,
  deleteTestCase,
  confirmTestPlan,
  getVariableSets,
  importVariableSets,
  deleteVariableSet,
  resumeAgentSession,
} from "@/lib/api";

interface Props {
  plan: TestPlanDetailView;
  sessionId: string;
  onConfirm: () => void;
  onPlanUpdate: (plan: TestPlanDetailView) => void;
}

// ── Validation helpers ────────────────────────────────────────────────────────

function extractVars(text: string): Set<string> {
  return new Set([...text.matchAll(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g)].map((m) => m[1]));
}

function stepsVars(c: TestCaseView): Set<string> {
  const all = new Set<string>();
  for (const step of c.steps) {
    for (const v of extractVars(step.action_description)) all.add(v);
    if (step.expected_result) for (const v of extractVars(step.expected_result)) all.add(v);
  }
  return all;
}

interface CaseError {
  missingVarSets: boolean;
  missingVars: string[];
  extraVars: string[];
}

function validateCase(c: TestCaseView, savedSets: VariableSetView[], varCols: string[]): CaseError | null {
  const required = stepsVars(c);
  const cols = new Set(varCols);
  if (required.size === 0 && cols.size === 0) return null;
  const missingVarSets = cols.size > 0 && savedSets.length === 0;
  const missingVars = [...required].filter((v) => !cols.has(v));
  const extraVars = [...cols].filter((v) => !required.has(v));
  if (!missingVarSets && missingVars.length === 0 && extraVars.length === 0) return null;
  return { missingVarSets, missingVars, extraVars };
}

// ── Debounced save hook ───────────────────────────────────────────────────────

function useDebouncedSave(plan: TestPlanDetailView, onPlanUpdate: (p: TestPlanDetailView) => void) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [savingCaseId, setSavingCaseId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const save = useCallback(
    (caseId: string, patch: Parameters<typeof updateTestCase>[1]) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(async () => {
        abortRef.current?.abort();
        const ctrl = new AbortController();
        abortRef.current = ctrl;
        setSavingCaseId(caseId);
        setSaveError(null);
        try {
          const updated = await updateTestCase(caseId, patch);
          if (ctrl.signal.aborted) return;
          onPlanUpdate({
            ...plan,
            cases: plan.cases.map((c) =>
              c.id === caseId ? { ...c, ...updated } : c,
            ),
          });
        } catch (e) {
          if (ctrl.signal.aborted) return;
          setSaveError(`保存失败: ${e instanceof Error ? e.message : String(e)}`);
        } finally {
          if (!ctrl.signal.aborted) setSavingCaseId(null);
        }
      }, 300);
    },
    [plan, onPlanUpdate],
  );

  const cancel = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    abortRef.current?.abort();
    abortRef.current = null;
    setSavingCaseId(null);
  }, []);

  return { save, cancel, savingCaseId, saveError, setSaveError };
}

// ── Main component ────────────────────────────────────────────────────────────

export function TestCaseEditor({ plan, sessionId, onConfirm, onPlanUpdate }: Props) {
  const [selectedCaseId, setSelectedCaseId] = useState<string>(plan.cases[0]?.id ?? "");
  const [variableSets, setVariableSets] = useState<Record<string, VariableSetView[]>>({});
  const [deletingCaseId, setDeletingCaseId] = useState<string | null>(null);
  const [deletingVsId, setDeletingVsId] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [savingVars, setSavingVars] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingVars, setLoadingVars] = useState<string | null>(null);
  const [pendingVarRows, setPendingVarRows] = useState<Record<string, Array<Record<string, string>>>>({});
  const [customVarCols, setCustomVarCols] = useState<Record<string, string[]>>({});
  const [newColName, setNewColName] = useState<Record<string, string>>({});
  const [invalidCaseIds, setInvalidCaseIds] = useState<Set<string>>(new Set());
  // drag-and-drop step reorder state
  const dragStepIdx = useRef<number | null>(null);

  const { save, cancel, savingCaseId, saveError, setSaveError } = useDebouncedSave(plan, onPlanUpdate);

  const selectedCase = plan.cases.find((c) => c.id === selectedCaseId) ?? plan.cases[0];
  const getVarCols = (c: TestCaseView): string[] =>
    c.global_variables.length > 0 ? c.global_variables : (customVarCols[c.id] ?? []);

  // ── variable sets ──────────────────────────────────────────────────────────

  const loadVariableSets = useCallback(async (caseId: string) => {
    if (variableSets[caseId]) return;
    setLoadingVars(caseId);
    try {
      const sets = await getVariableSets(caseId);
      setVariableSets((prev) => ({ ...prev, [caseId]: sets }));
    } catch { /* silently ignore */ } finally {
      setLoadingVars(null);
    }
  }, [variableSets]);

  const handleSelectCase = (caseId: string) => {
    cancel();
    setSelectedCaseId(caseId);
    loadVariableSets(caseId);
  };

  // ── case meta editing ──────────────────────────────────────────────────────

  const handleMetaChange = (
    caseId: string,
    field: "case_name" | "start_url" | "module" | "function_point",
    value: string,
  ) => {
    onPlanUpdate({
      ...plan,
      cases: plan.cases.map((c) => (c.id === caseId ? { ...c, [field]: value } : c)),
    });
    save(caseId, { [field]: value });
  };

  // ── delete case ────────────────────────────────────────────────────────────

  const handleDeleteCase = async (caseId: string) => {
    if (!window.confirm("确认删除该测试用例？")) return;
    setDeletingCaseId(caseId);
    setError(null);
    try {
      await deleteTestCase(caseId);
      const remaining = plan.cases.filter((c) => c.id !== caseId);
      onPlanUpdate({ ...plan, cases: remaining });
      if (selectedCaseId === caseId) setSelectedCaseId(remaining[0]?.id ?? "");
    } catch (e) {
      setError(`删除失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setDeletingCaseId(null);
    }
  };

  // ── step CRUD ──────────────────────────────────────────────────────────────

  const applySteps = (caseId: string, updatedSteps: TestStepView[]) => {
    // Renumber steps sequentially
    const renumbered = updatedSteps.map((s, i) => ({ ...s, step_number: i + 1 }));
    onPlanUpdate({
      ...plan,
      cases: plan.cases.map((c) => (c.id === caseId ? { ...c, steps: renumbered } : c)),
    });
    save(caseId, { steps: renumbered });
  };

  const handleStepChange = (
    caseId: string,
    stepIndex: number,
    field: keyof TestStepView,
    value: string | boolean,
  ) => {
    const c = plan.cases.find((x) => x.id === caseId);
    if (!c) return;
    applySteps(caseId, c.steps.map((s, i) => (i === stepIndex ? { ...s, [field]: value } : s)));
  };

  const handleAddStep = (caseId: string) => {
    const c = plan.cases.find((x) => x.id === caseId);
    if (!c) return;
    const newStep: TestStepView = {
      step_number: c.steps.length + 1,
      action_description: "",
      expected_result: null,
      step_variables: [],
      is_visual_checkpoint: false,
    };
    applySteps(caseId, [...c.steps, newStep]);
  };

  const handleDeleteStep = (caseId: string, stepIndex: number) => {
    const c = plan.cases.find((x) => x.id === caseId);
    if (!c) return;
    applySteps(caseId, c.steps.filter((_, i) => i !== stepIndex));
  };

  // ── step drag-and-drop reorder ─────────────────────────────────────────────

  const handleDragStart = (idx: number) => { dragStepIdx.current = idx; };

  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (dragStepIdx.current === null || dragStepIdx.current === idx) return;
    if (!selectedCase) return;
    const steps = [...selectedCase.steps];
    const [moved] = steps.splice(dragStepIdx.current, 1);
    steps.splice(idx, 0, moved);
    dragStepIdx.current = idx;
    applySteps(selectedCase.id, steps);
  };

  const handleDragEnd = () => { dragStepIdx.current = null; };

  // ── variable set CRUD ──────────────────────────────────────────────────────

  const currentVarSets = selectedCase ? (variableSets[selectedCase.id] ?? []) : [];
  const varCols = selectedCase ? getVarCols(selectedCase) : [];

  const handleAddVarRow = () => {
    if (!selectedCase) return;
    const cols = getVarCols(selectedCase);
    if (cols.length === 0) return;
    setPendingVarRows((prev) => ({
      ...prev,
      [selectedCase.id]: [...(prev[selectedCase.id] ?? []), Object.fromEntries(cols.map((v) => [v, ""]))],
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

  const handleDeletePendingRow = (rowIndex: number) => {
    if (!selectedCase) return;
    setPendingVarRows((prev) => {
      const rows = [...(prev[selectedCase.id] ?? [])];
      rows.splice(rowIndex, 1);
      return { ...prev, [selectedCase.id]: rows };
    });
  };

  const handleDeleteSavedVarSet = async (vsId: string) => {
    if (!selectedCase) return;
    setDeletingVsId(vsId);
    setError(null);
    try {
      await deleteVariableSet(vsId);
      setVariableSets((prev) => ({
        ...prev,
        [selectedCase.id]: (prev[selectedCase.id] ?? []).filter((vs) => vs.id !== vsId),
      }));
    } catch (e) {
      setError(`删除变量集失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setDeletingVsId(null);
    }
  };

  const handleAddCustomCol = (caseId: string) => {
    const name = (newColName[caseId] ?? "").trim();
    if (!name) return;
    setCustomVarCols((prev) => ({ ...prev, [caseId]: [...(prev[caseId] ?? []), name] }));
    setNewColName((prev) => ({ ...prev, [caseId]: "" }));
    setPendingVarRows((prev) => ({
      ...prev,
      [caseId]: (prev[caseId] ?? []).map((row) => ({ ...row, [name]: "" })),
    }));
  };

  const handleSaveVarRows = async () => {
    if (!selectedCase) return;
    const rows = pendingVarRows[selectedCase.id] ?? [];
    if (rows.length === 0) return;
    setError(null);
    setSavingVars(true);
    try {
      const validKeys = new Set(getVarCols(selectedCase));
      const filtered = rows.map((row) =>
        Object.fromEntries(Object.entries(row).filter(([k]) => validKeys.has(k))),
      );
      const saved = await importVariableSets(selectedCase.id, filtered);
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

  // ── confirm with full validation ───────────────────────────────────────────

  const handleConfirm = async () => {
    const errors: Record<string, CaseError> = {};
    for (const c of plan.cases) {
      const err = validateCase(c, variableSets[c.id] ?? [], getVarCols(c));
      if (err) errors[c.id] = err;
    }
    if (Object.keys(errors).length > 0) {
      setInvalidCaseIds(new Set(Object.keys(errors)));
      const lines = Object.entries(errors).map(([cid, err]) => {
        const name = plan.cases.find((c) => c.id === cid)?.case_name ?? cid;
        const parts: string[] = [];
        if (err.missingVarSets) parts.push("缺少变量集");
        if (err.missingVars.length > 0) parts.push(`步骤变量 {${err.missingVars.join("}, {")}} 未在变量集中定义`);
        if (err.extraVars.length > 0) parts.push(`变量集列 ${err.extraVars.join(", ")} 未在步骤中使用`);
        return `「${name}」：${parts.join("；")}`;
      });
      setError(lines.join("\n"));
      return;
    }
    setInvalidCaseIds(new Set());
    setConfirming(true);
    setError(null);
    try {
      await confirmTestPlan(plan.id);
      await resumeAgentSession(sessionId);
      onConfirm();
    } catch (e) {
      setError(`确认失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setConfirming(false);
    }
  };

  const displayError = error ?? saveError;

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

      {displayError && (
        <div className="mx-4 mt-2 px-3 py-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-md whitespace-pre-line">
          {displayError}
          <button
            type="button"
            onClick={() => { setError(null); setSaveError(null); }}
            className="ml-2 underline"
          >
            关闭
          </button>
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        {/* Case list */}
        <div className="w-48 flex-shrink-0 border-r border-gray-200 overflow-y-auto">
          {plan.cases.map((c) => {
            const isInvalid = invalidCaseIds.has(c.id);
            const isSelected = c.id === selectedCaseId;
            return (
              <div
                key={c.id}
                className={`group relative border-b ${
                  isInvalid
                    ? "border-l-2 border-l-red-500 bg-red-50"
                    : isSelected
                    ? "border-l-2 border-l-blue-500 bg-blue-50"
                    : "border-gray-100"
                }`}
              >
                <button
                  type="button"
                  onClick={() => handleSelectCase(c.id)}
                  className="w-full text-left px-3 py-2.5 hover:bg-gray-50 transition-colors pr-8"
                >
                  <p className={`text-xs font-medium truncate ${isInvalid ? "text-red-700" : "text-gray-800"}`}>
                    {c.case_name}
                  </p>
                  {c.module && <p className="text-xs text-gray-400 truncate">{c.module}</p>}
                  <p className="text-xs text-gray-400">{c.steps.length} 步骤</p>
                  {isInvalid && <p className="text-xs text-red-500 mt-0.5">⚠ 校验未通过</p>}
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteCase(c.id)}
                  disabled={deletingCaseId === c.id}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all disabled:opacity-30"
                  aria-label={`删除用例 ${c.case_name}`}
                >
                  {deletingCaseId === c.id ? "…" : "✕"}
                </button>
              </div>
            );
          })}
          {plan.cases.length === 0 && (
            <p className="px-3 py-4 text-xs text-gray-400 text-center">暂无用例</p>
          )}
        </div>

        {/* Case detail */}
        {selectedCase ? (
          <div className="flex-1 overflow-y-auto">
            <CaseDetail
              testCase={selectedCase}
              varCols={varCols}
              varSets={currentVarSets}
              pendingVarRows={pendingVarRows[selectedCase.id] ?? []}
              loadingVars={loadingVars === selectedCase.id}
              savingSteps={savingCaseId === selectedCase.id}
              savingVars={savingVars}
              deletingVsId={deletingVsId}
              newColName={newColName[selectedCase.id] ?? ""}
              onMetaChange={handleMetaChange}
              onStepChange={handleStepChange}
              onAddStep={handleAddStep}
              onDeleteStep={handleDeleteStep}
              onDragStart={handleDragStart}
              onDragOver={handleDragOver}
              onDragEnd={handleDragEnd}
              onAddVarRow={handleAddVarRow}
              onPendingVarChange={handlePendingVarChange}
              onDeletePendingRow={handleDeletePendingRow}
              onDeleteSavedVarSet={handleDeleteSavedVarSet}
              onSaveVarRows={handleSaveVarRows}
              onAddCustomCol={() => handleAddCustomCol(selectedCase.id)}
              onNewColNameChange={(v) => setNewColName((prev) => ({ ...prev, [selectedCase.id]: v }))}
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
  varCols: string[];
  varSets: VariableSetView[];
  pendingVarRows: Array<Record<string, string>>;
  loadingVars: boolean;
  savingSteps: boolean;
  savingVars: boolean;
  deletingVsId: string | null;
  newColName: string;
  onMetaChange: (caseId: string, field: "case_name" | "start_url" | "module" | "function_point", value: string) => void;
  onStepChange: (caseId: string, stepIndex: number, field: keyof TestStepView, value: string | boolean) => void;
  onAddStep: (caseId: string) => void;
  onDeleteStep: (caseId: string, stepIndex: number) => void;
  onDragStart: (idx: number) => void;
  onDragOver: (e: React.DragEvent, idx: number) => void;
  onDragEnd: () => void;
  onAddVarRow: () => void;
  onPendingVarChange: (rowIndex: number, varName: string, value: string) => void;
  onDeletePendingRow: (rowIndex: number) => void;
  onDeleteSavedVarSet: (vsId: string) => void;
  onSaveVarRows: () => void;
  onAddCustomCol: () => void;
  onNewColNameChange: (v: string) => void;
}

function CaseDetail({
  testCase, varCols, varSets, pendingVarRows, loadingVars, savingSteps, savingVars,
  deletingVsId, newColName, onMetaChange, onStepChange, onAddStep, onDeleteStep,
  onDragStart, onDragOver, onDragEnd, onAddVarRow, onPendingVarChange,
  onDeletePendingRow, onDeleteSavedVarSet, onSaveVarRows, onAddCustomCol, onNewColNameChange,
}: CaseDetailProps) {
  const noVarsFromLLM = testCase.global_variables.length === 0;
  const hasVarCols = varCols.length > 0;

  return (
    <div className="p-4 space-y-5">
      {/* ── Case meta ── */}
      <section className="space-y-2">
        <div className="flex items-center gap-1">
          {savingSteps && <span className="text-xs text-blue-500">保存中...</span>}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">用例名称 *</label>
            <input
              type="text"
              value={testCase.case_name}
              onChange={(e) => onMetaChange(testCase.id, "case_name", e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              aria-label="用例名称"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">起始 URL *</label>
            <input
              type="text"
              value={testCase.start_url}
              onChange={(e) => onMetaChange(testCase.id, "start_url", e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              aria-label="起始 URL"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">模块</label>
            <input
              type="text"
              value={testCase.module ?? ""}
              onChange={(e) => onMetaChange(testCase.id, "module", e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              aria-label="模块"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">功能点</label>
            <input
              type="text"
              value={testCase.function_point ?? ""}
              onChange={(e) => onMetaChange(testCase.id, "function_point", e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              aria-label="功能点"
            />
          </div>
        </div>
      </section>

      {/* ── Steps ── */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
            测试步骤
          </h4>
          <button
            type="button"
            onClick={() => onAddStep(testCase.id)}
            className="text-xs text-blue-600 hover:text-blue-800"
            aria-label="添加步骤"
          >
            + 添加步骤
          </button>
        </div>
        <div className="border border-gray-200 rounded-md overflow-hidden">
          <table className="w-full text-xs" role="table">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-1 py-2 w-5 text-gray-400" title="拖拽排序" />
                <th className="px-2 py-2 text-left text-gray-500 font-medium w-8">#</th>
                <th className="px-2 py-2 text-left text-gray-500 font-medium">操作描述</th>
                <th className="px-2 py-2 text-left text-gray-500 font-medium">预期结果</th>
                <th className="px-2 py-2 text-center text-gray-500 font-medium w-10">视觉</th>
                <th className="w-6" />
              </tr>
            </thead>
            <tbody>
              {testCase.steps.map((step, idx) => (
                <tr
                  key={step.step_number}
                  className="border-t border-gray-100 group"
                  draggable
                  onDragStart={() => onDragStart(idx)}
                  onDragOver={(e) => onDragOver(e, idx)}
                  onDragEnd={onDragEnd}
                >
                  <td className="px-1 py-1.5 text-gray-300 cursor-grab select-none text-center align-top">
                    ⠿
                  </td>
                  <td className="px-2 py-1.5 text-gray-400 align-top">{step.step_number}</td>
                  <td className="px-2 py-1.5 align-top">
                    <textarea
                      className="w-full text-xs text-gray-800 resize-none border-0 focus:outline-none focus:ring-1 focus:ring-blue-300 rounded p-0.5 min-h-[40px]"
                      value={step.action_description}
                      onChange={(e) => onStepChange(testCase.id, idx, "action_description", e.target.value)}
                      aria-label={`步骤 ${step.step_number} 操作描述`}
                    />
                  </td>
                  <td className="px-2 py-1.5 align-top">
                    <textarea
                      className="w-full text-xs text-gray-600 resize-none border-0 focus:outline-none focus:ring-1 focus:ring-blue-300 rounded p-0.5 min-h-[40px]"
                      value={step.expected_result ?? ""}
                      placeholder="无预期结果"
                      onChange={(e) => onStepChange(testCase.id, idx, "expected_result", e.target.value)}
                      aria-label={`步骤 ${step.step_number} 预期结果`}
                    />
                  </td>
                  <td className="px-2 py-1.5 text-center align-top">
                    <input
                      type="checkbox"
                      checked={step.is_visual_checkpoint}
                      onChange={(e) => onStepChange(testCase.id, idx, "is_visual_checkpoint", e.target.checked)}
                      aria-label={`步骤 ${step.step_number} 视觉检查点`}
                      className="rounded"
                    />
                  </td>
                  <td className="px-1 py-1.5 text-center align-top">
                    <button
                      type="button"
                      onClick={() => onDeleteStep(testCase.id, idx)}
                      className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all"
                      aria-label={`删除步骤 ${step.step_number}`}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
              {testCase.steps.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-2 py-3 text-center text-gray-400">
                    暂无步骤，点击"添加步骤"
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Variable sets ── */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
            变量集
            {varCols.length > 0 && (
              <span className="ml-1 text-gray-400 normal-case font-normal">({varCols.join(", ")})</span>
            )}
          </h4>
          {hasVarCols && (
            <button type="button" onClick={onAddVarRow} className="text-xs text-blue-600 hover:text-blue-800" aria-label="添加变量集行">
              + 添加一行
            </button>
          )}
        </div>

        {noVarsFromLLM && (
          <div className="flex items-center gap-2 mb-2">
            <input
              type="text"
              value={newColName}
              onChange={(e) => onNewColNameChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onAddCustomCol()}
              placeholder="变量名（如 username）"
              className="flex-1 text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              aria-label="新变量名"
            />
            <button
              type="button"
              onClick={onAddCustomCol}
              disabled={!newColName.trim()}
              className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-40 transition-colors"
            >
              添加变量
            </button>
          </div>
        )}

        {loadingVars ? (
          <p className="text-xs text-gray-400">加载中...</p>
        ) : !hasVarCols ? (
          <p className="text-xs text-gray-400">该用例无变量，可在上方手动添加变量列</p>
        ) : (
          <div className="border border-gray-200 rounded-md overflow-hidden">
            <table className="w-full text-xs" role="table">
              <thead className="bg-gray-50">
                <tr>
                  {varCols.map((v) => (
                    <th key={v} className="px-2 py-2 text-left text-gray-500 font-medium">{v}</th>
                  ))}
                  <th className="w-6" />
                </tr>
              </thead>
              <tbody>
                {varSets.map((vs) => (
                  <tr key={vs.id} className="border-t border-gray-100 group">
                    {varCols.map((v) => (
                      <td key={v} className="px-2 py-1.5 text-gray-700">{vs.variables[v] ?? ""}</td>
                    ))}
                    <td className="px-1 py-1 text-center">
                      <button
                        type="button"
                        onClick={() => onDeleteSavedVarSet(vs.id)}
                        disabled={deletingVsId === vs.id}
                        className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all disabled:opacity-30"
                        aria-label="删除该变量集"
                      >
                        {deletingVsId === vs.id ? "…" : "✕"}
                      </button>
                    </td>
                  </tr>
                ))}
                {pendingVarRows.map((row, rowIdx) => (
                  <tr key={`pending-${rowIdx}`} className="border-t border-blue-100 bg-blue-50">
                    {varCols.map((v) => (
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
                    <td className="px-1 py-1 text-center">
                      <button
                        type="button"
                        onClick={() => onDeletePendingRow(rowIdx)}
                        className="p-0.5 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                        aria-label="删除该行"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
                {varSets.length === 0 && pendingVarRows.length === 0 && (
                  <tr>
                    <td colSpan={varCols.length + 1} className="px-2 py-3 text-center text-gray-400">
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
