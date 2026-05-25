"use client";

import { useState, useCallback, useRef } from "react";
import type { TestPlanDetailView, TestCaseView, TestStepView, VariableSetView } from "@/types/testing";
import {
  createTestCase,
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
  onCancel: () => void;
  onPlanUpdate: (plan: TestPlanDetailView) => void;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const VAR_NAME_RE = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
const VAR_NAME_MAX = 30;

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
  emptyName?: boolean;
  emptyUrl?: boolean;
  invalidUrl?: boolean;
  noSteps?: boolean;
  emptyStepDescriptions?: number[];  // step indices with empty action_description
  missingVarSets: boolean;
  missingVarCols?: boolean;  // steps reference vars but no columns defined at all
  missingVars: string[];
  extraVars: string[];
  emptyVarValues: string[];  // variable names that have empty values in saved sets
}

/** Validate port is 1-65535 */
function isValidPort(portStr: string): boolean {
  const n = Number(portStr);
  return Number.isInteger(n) && n >= 1 && n <= 65535;
}

const URL_RE = /^https?:\/\/[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*(\:(\d{1,5}))?(\/.*)?$/;

function validateCase(c: TestCaseView, savedSets: VariableSetView[], varCols: string[]): CaseError | null {
  const required = stepsVars(c);
  const cols = new Set(varCols);
  const emptyName = !c.case_name.trim();
  const emptyUrl = !c.start_url.trim();

  // URL validation: regex + port range check
  let invalidUrl = false;
  if (!emptyUrl) {
    const match = URL_RE.exec(c.start_url.trim());
    if (!match) {
      invalidUrl = true;
    } else if (match[5]) {
      // match[5] is the port digits
      invalidUrl = !isValidPort(match[5]);
    }
  }

  // Steps validation
  const noSteps = c.steps.length === 0;
  const emptyStepDescriptions = c.steps
    .map((s, i) => (!s.action_description.trim() ? i : -1))
    .filter((i) => i >= 0);

  // Variable validation
  const missingVarCols = required.size > 0 && cols.size === 0;
  const missingVarSets = cols.size > 0 && savedSets.length === 0;
  const missingVars = [...required].filter((v) => !cols.has(v));
  const extraVars = [...cols].filter((v) => !required.has(v));

  // Check for empty values in saved variable sets
  const emptyVarValues: string[] = [];
  if (savedSets.length > 0) {
    for (const col of varCols) {
      const hasEmpty = savedSets.some((vs) => !(vs.variables[col] ?? "").trim());
      if (hasEmpty) emptyVarValues.push(col);
    }
  }

  const hasError = emptyName || emptyUrl || invalidUrl || noSteps ||
    emptyStepDescriptions.length > 0 || missingVarCols || missingVarSets ||
    (missingVars.length > 0 && !missingVarCols) || extraVars.length > 0 || emptyVarValues.length > 0;

  if (!hasError) return null;
  return { emptyName, emptyUrl, invalidUrl, noSteps, emptyStepDescriptions, missingVarCols, missingVarSets, missingVars, extraVars, emptyVarValues };
}

function validateVarName(name: string): string | null {
  if (!name.trim()) return "变量名不能为空";
  if (!VAR_NAME_RE.test(name)) return "变量名只能包含英文字母、数字和下划线，且不能以数字开头";
  if (name.length > VAR_NAME_MAX) return `变量名长度不能超过 ${VAR_NAME_MAX} 个字符`;
  return null;
}

// ── Debounced save hook ───────────────────────────────────────────────────────

function useDebouncedSave(plan: TestPlanDetailView, onPlanUpdate: (p: TestPlanDetailView) => void) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [savingCaseId, setSavingCaseId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Always hold the latest plan/onPlanUpdate in refs so the async callback
  // never closes over a stale snapshot.
  const planRef = useRef(plan);
  planRef.current = plan;
  const onPlanUpdateRef = useRef(onPlanUpdate);
  onPlanUpdateRef.current = onPlanUpdate;

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
          // No need to call onPlanUpdate — localPlan is the source of truth.
          // Just log success silently.
        } catch (e) {
          if (ctrl.signal.aborted) return;
          setSaveError(`保存失败: ${e instanceof Error ? e.message : String(e)}`);
        } finally {
          if (!ctrl.signal.aborted) setSavingCaseId(null);
        }
      }, 300);
    },
    [], // stable — reads latest values via refs
  );

  const cancel = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    abortRef.current?.abort();
    abortRef.current = null;
    setSavingCaseId(null);
  }, []);

  return { save, cancel, savingCaseId, saveError, setSaveError, planRef, onPlanUpdateRef };
}

// ── Main component ────────────────────────────────────────────────────────────

export function TestCaseEditor({ plan, sessionId, onConfirm, onCancel, onPlanUpdate }: Props) {
  // Local copy of plan — textarea values are driven from here, not from props.
  // This prevents parent re-renders from resetting cursor position.
  const [localPlan, setLocalPlan] = useState(plan);
  // Sync from parent only when plan.id changes (new plan loaded)
  if (plan.id !== localPlan.id) {
    setLocalPlan(plan);
  }

  const [selectedCaseId, setSelectedCaseId] = useState<string>(localPlan.cases[0]?.id ?? "");
  const [variableSets, setVariableSets] = useState<Record<string, VariableSetView[]>>({});
  const [deletingCaseId, setDeletingCaseId] = useState<string | null>(null);
  const [deletingVsId, setDeletingVsId] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [savingVars, setSavingVars] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingVars, setLoadingVars] = useState<string | null>(null);
  const [pendingVarRows, setPendingVarRows] = useState<Record<string, Array<Record<string, string>>>>({});
  // customVarCols: for cases where LLM found no variables
  const [customVarCols, setCustomVarCols] = useState<Record<string, string[]>>({});
  const [newColName, setNewColName] = useState<Record<string, string>>({});
  const [newColError, setNewColError] = useState<string | null>(null);
  // editingColIdx: {caseId, colIndex} for renaming a column
  const [editingCol, setEditingCol] = useState<{ caseId: string; idx: number; value: string } | null>(null);
  const [editColError, setEditColError] = useState<string | null>(null);
  const [invalidCaseIds, setInvalidCaseIds] = useState<Set<string>>(new Set());
  const dragStepIdx = useRef<number | null>(null);

  const { save, cancel, savingCaseId, saveError, setSaveError, planRef, onPlanUpdateRef } = useDebouncedSave(localPlan, onPlanUpdate);

  const selectedCase = localPlan.cases.find((c) => c.id === selectedCaseId) ?? localPlan.cases[0];

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

  // ── case meta ─────────────────────────────────────────────────────────────

  const handleMetaChange = (
    caseId: string,
    field: "case_name" | "start_url" | "module" | "function_point",
    value: string,
  ) => {
    setLocalPlan((prev) => ({ ...prev, cases: prev.cases.map((c) => (c.id === caseId ? { ...c, [field]: value } : c)) }));
    save(caseId, { [field]: value });
  };

  // ── delete case ────────────────────────────────────────────────────────────

  const handleDeleteCase = async (caseId: string) => {
    if (!window.confirm("确认删除该测试用例？")) return;
    setDeletingCaseId(caseId);
    setError(null);
    try {
      await deleteTestCase(caseId);
      setLocalPlan((prev) => ({ ...prev, cases: prev.cases.filter((c) => c.id !== caseId) }));
      if (selectedCaseId === caseId) {
        const remaining = localPlan.cases.filter((c) => c.id !== caseId);
        setSelectedCaseId(remaining[0]?.id ?? "");
      }
    } catch (e) {
      setError(`删除失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setDeletingCaseId(null);
    }
  };

  // ── add case ──────────────────────────────────────────────────────────────

  const [addingCase, setAddingCase] = useState(false);

  const handleAddCase = async () => {
    setAddingCase(true);
    setError(null);
    try {
      const newCase = await createTestCase(localPlan.id, {
        case_name: "新测试用例",
        start_url: "https://",
        steps: [{ step_number: 1, action_description: "", expected_result: null, step_variables: [], is_visual_checkpoint: false }],
      });
      setLocalPlan((prev) => ({ ...prev, cases: [...prev.cases, newCase] }));
      setSelectedCaseId(newCase.id);
    } catch (e) {
      setError(`添加用例失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setAddingCase(false);
    }
  };

  // ── steps ─────────────────────────────────────────────────────────────────

  const applySteps = (caseId: string, steps: TestStepView[]) => {
    const renumbered = steps.map((s, i) => ({ ...s, step_number: i + 1 }));
    setLocalPlan((prev) => ({ ...prev, cases: prev.cases.map((c) => (c.id === caseId ? { ...c, steps: renumbered } : c)) }));
    save(caseId, { steps: renumbered });
  };

  const handleStepChange = (caseId: string, idx: number, field: keyof TestStepView, value: string | boolean) => {
    let updatedSteps: TestStepView[] = [];
    setLocalPlan((prev) => {
      const c = prev.cases.find((x) => x.id === caseId);
      if (!c) return prev;
      updatedSteps = c.steps.map((s, i) => (i === idx ? { ...s, [field]: value } : s))
        .map((s, i) => ({ ...s, step_number: i + 1 }));
      return { ...prev, cases: prev.cases.map((c2) => (c2.id === caseId ? { ...c2, steps: updatedSteps } : c2)) };
    });
    // Use setTimeout(0) to ensure setLocalPlan has committed before save reads planRef
    setTimeout(() => save(caseId, { steps: updatedSteps }), 0);
  };

  const handleAddStep = (caseId: string) => {
    const c = localPlan.cases.find((x) => x.id === caseId);
    if (!c) return;
    applySteps(caseId, [...c.steps, { step_number: c.steps.length + 1, action_description: "", expected_result: null, step_variables: [], is_visual_checkpoint: false }]);
  };

  const handleDeleteStep = (caseId: string, idx: number) => {
    const c = localPlan.cases.find((x) => x.id === caseId);
    if (!c) return;
    applySteps(caseId, c.steps.filter((_, i) => i !== idx));
  };

  const handleDragStart = (idx: number) => { dragStepIdx.current = idx; };
  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (dragStepIdx.current === null || dragStepIdx.current === idx || !selectedCase) return;
    const steps = [...selectedCase.steps];
    const [moved] = steps.splice(dragStepIdx.current, 1);
    steps.splice(idx, 0, moved);
    dragStepIdx.current = idx;
    const renumbered = steps.map((s, i) => ({ ...s, step_number: i + 1 }));
    setLocalPlan((prev) => ({ ...prev, cases: prev.cases.map((c) => (c.id === selectedCase.id ? { ...c, steps: renumbered } : c)) }));
    save(selectedCase.id, { steps: renumbered });
  };
  const handleDragEnd = () => { dragStepIdx.current = null; };

  // ── variable columns ───────────────────────────────────────────────────────

  const handleAddCustomCol = (caseId: string) => {
    const name = (newColName[caseId] ?? "").trim();
    const err = validateVarName(name);
    if (err) { setNewColError(err); return; }
    const existing = getVarCols(localPlan.cases.find((c) => c.id === caseId)!);
    if (existing.includes(name)) { setNewColError("变量名已存在"); return; }
    setNewColError(null);
    setCustomVarCols((prev) => ({ ...prev, [caseId]: [...(prev[caseId] ?? []), name] }));
    setNewColName((prev) => ({ ...prev, [caseId]: "" }));
    setPendingVarRows((prev) => ({ ...prev, [caseId]: (prev[caseId] ?? []).map((row) => ({ ...row, [name]: "" })) }));
  };

  const handleStartEditCol = (caseId: string, idx: number, currentName: string) => {
    setEditingCol({ caseId, idx, value: currentName });
    setEditColError(null);
  };

  const handleDeleteCustomCol = (caseId: string, idx: number) => {
    const cols = [...(customVarCols[caseId] ?? [])];
    const removed = cols[idx];
    cols.splice(idx, 1);
    setCustomVarCols((prev) => ({ ...prev, [caseId]: cols }));
    // Remove the column key from all pending rows
    setPendingVarRows((prev) => ({
      ...prev,
      [caseId]: (prev[caseId] ?? []).map((row) => {
        const { [removed]: _, ...rest } = row;
        return rest;
      }),
    }));
  };

  const handleCommitEditCol = () => {
    if (!editingCol) return;
    const { caseId, idx, value } = editingCol;
    const newName = value.trim();
    const err = validateVarName(newName);
    if (err) { setEditColError(err); return; }
    const cols = [...(customVarCols[caseId] ?? [])];
    const oldName = cols[idx];
    if (newName === oldName) { setEditingCol(null); return; }
    if (cols.includes(newName)) { setEditColError("变量名已存在"); return; }
    cols[idx] = newName;
    setCustomVarCols((prev) => ({ ...prev, [caseId]: cols }));
    // Rename key in pending rows
    setPendingVarRows((prev) => ({
      ...prev,
      [caseId]: (prev[caseId] ?? []).map((row) => {
        const { [oldName]: val, ...rest } = row;
        return { ...rest, [newName]: val ?? "" };
      }),
    }));
    // #8: Rename key in saved variable sets cache
    setVariableSets((prev) => {
      const sets = prev[caseId];
      if (!sets || sets.length === 0) return prev;
      return {
        ...prev,
        [caseId]: sets.map((vs) => {
          const { [oldName]: val, ...rest } = vs.variables;
          return { ...vs, variables: { ...rest, [newName]: val ?? "" } };
        }),
      };
    });
    setEditingCol(null);
    setEditColError(null);
  };

  // ── variable set rows ──────────────────────────────────────────────────────

  const currentVarSets = selectedCase ? (variableSets[selectedCase.id] ?? []) : [];
  const varCols = selectedCase ? getVarCols(selectedCase) : [];

  const handleAddVarRow = () => {
    if (!selectedCase || varCols.length === 0) return;
    setPendingVarRows((prev) => ({
      ...prev,
      [selectedCase.id]: [...(prev[selectedCase.id] ?? []), Object.fromEntries(varCols.map((v) => [v, ""]))],
    }));
  };

  const handlePendingVarChange = (rowIdx: number, varName: string, value: string) => {
    if (!selectedCase) return;
    setPendingVarRows((prev) => {
      const rows = [...(prev[selectedCase.id] ?? [])];
      rows[rowIdx] = { ...rows[rowIdx], [varName]: value };
      return { ...prev, [selectedCase.id]: rows };
    });
  };

  const handleDeletePendingRow = (rowIdx: number) => {
    if (!selectedCase) return;
    setPendingVarRows((prev) => {
      const rows = [...(prev[selectedCase.id] ?? [])];
      rows.splice(rowIdx, 1);
      return { ...prev, [selectedCase.id]: rows };
    });
  };

  const handleDeleteSavedVarSet = async (vsId: string) => {
    if (!selectedCase) return;
    setDeletingVsId(vsId);
    setError(null);
    try {
      await deleteVariableSet(vsId);
      setVariableSets((prev) => ({ ...prev, [selectedCase.id]: (prev[selectedCase.id] ?? []).filter((vs) => vs.id !== vsId) }));
    } catch (e) {
      setError(`删除变量集失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setDeletingVsId(null);
    }
  };

  const handleSaveVarRows = async () => {
    if (!selectedCase) return;
    const rows = pendingVarRows[selectedCase.id] ?? [];
    if (rows.length === 0) return;

    // Reject rows where every value is empty
    const allEmptyRows = rows.filter((row) => Object.values(row).every((v) => !v.trim()));
    if (allEmptyRows.length > 0) {
      setError(`存在 ${allEmptyRows.length} 行变量值全部为空，请填写后再保存`);
      return;
    }

    // #9: Reject rows with any individual empty value
    const partialEmptyRows: number[] = [];
    rows.forEach((row, idx) => {
      const hasEmpty = Object.values(row).some((v) => !v.trim());
      if (hasEmpty) partialEmptyRows.push(idx);
    });
    if (partialEmptyRows.length > 0) {
      setError(`第 ${partialEmptyRows.map((i) => i + 1).join(", ")} 行存在空值，请填写完整后再保存`);
      return;
    }

    setError(null);
    setSavingVars(true);
    try {
      const validKeys = new Set(getVarCols(selectedCase));
      const filtered = rows.map((row) => Object.fromEntries(Object.entries(row).filter(([k]) => validKeys.has(k))));
      const saved = await importVariableSets(selectedCase.id, filtered);
      setVariableSets((prev) => ({ ...prev, [selectedCase.id]: [...(prev[selectedCase.id] ?? []), ...saved] }));
      setPendingVarRows((prev) => ({ ...prev, [selectedCase.id]: [] }));
    } catch (e) {
      setError(`保存变量集失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSavingVars(false);
    }
  };

  // ── confirm / cancel ───────────────────────────────────────────────────────

  const handleConfirm = async () => {
    // #1: Empty plan guard
    if (localPlan.cases.length === 0) {
      setError("测试计划中没有用例，请至少添加一个用例后再确认");
      return;
    }
    // #11: sessionId guard
    if (!sessionId) {
      setError("会话 ID 无效，无法确认计划");
      return;
    }

    // #5: Load variable sets for any cases not yet fetched
    const unloadedCaseIds = localPlan.cases
      .filter((c) => variableSets[c.id] === undefined)
      .map((c) => c.id);
    if (unloadedCaseIds.length > 0) {
      try {
        const loaded: Record<string, VariableSetView[]> = {};
        await Promise.all(unloadedCaseIds.map(async (cid) => {
          const sets = await getVariableSets(cid);
          loaded[cid] = sets;
        }));
        setVariableSets((prev) => ({ ...prev, ...loaded }));
        // Use merged data for validation below
        const mergedVarSets = { ...variableSets, ...loaded };
        return doValidateAndConfirm(mergedVarSets);
      } catch (e) {
        setError(`加载变量集失败: ${e instanceof Error ? e.message : String(e)}`);
        return;
      }
    }

    return doValidateAndConfirm(variableSets);
  };

  const doValidateAndConfirm = async (allVarSets: Record<string, VariableSetView[]>) => {
    const errors: Record<string, CaseError> = {};
    for (const c of localPlan.cases) {
      const err = validateCase(c, allVarSets[c.id] ?? [], getVarCols(c));
      if (err) errors[c.id] = err;
    }
    if (Object.keys(errors).length > 0) {
      setInvalidCaseIds(new Set(Object.keys(errors)));
      const lines = Object.entries(errors).map(([cid, err]) => {
        const name = localPlan.cases.find((c) => c.id === cid)?.case_name || cid;
        const parts: string[] = [];
        if (err.emptyName) parts.push("用例名称不能为空");
        if (err.emptyUrl) parts.push("起始 URL 不能为空");
        if (err.invalidUrl) parts.push("起始 URL 格式无效（需为合法的 http(s)://域名 格式，端口范围 1-65535）");
        if (err.noSteps) parts.push("至少需要一个测试步骤");
        if (err.emptyStepDescriptions && err.emptyStepDescriptions.length > 0) parts.push(`步骤 ${err.emptyStepDescriptions.map((i) => i + 1).join(", ")} 的操作描述不能为空`);
        if (err.missingVarCols) parts.push("步骤中引用了变量但未定义变量列，请先添加变量列");
        if (err.missingVarSets) parts.push("已定义变量列但缺少变量集数据");
        if (err.missingVars.length > 0 && !err.missingVarCols) parts.push(`步骤变量 {${err.missingVars.join("}, {")}} 未在变量集中定义`);
        if (err.extraVars.length > 0) parts.push(`变量集列 ${err.extraVars.join(", ")} 未在步骤中使用`);
        if (err.emptyVarValues.length > 0) parts.push(`变量 ${err.emptyVarValues.join(", ")} 存在空值`);
        return `「${name}」：${parts.join("；")}`;
      });
      setError(lines.join("\n"));
      return;
    }
    setInvalidCaseIds(new Set());
    setConfirming(true);
    setError(null);
    try {
      await confirmTestPlan(localPlan.id);
      await resumeAgentSession(sessionId, "confirm");
      onConfirm();
    } catch (e) {
      setError(`确认失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setConfirming(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm("取消后测试计划将被丢弃，确认取消？")) return;
    setCancelling(true);
    try {
      // Resume with cancel action so the backend terminates gracefully
      await resumeAgentSession(sessionId, "cancel").catch(() => {});
      onCancel();
    } finally {
      setCancelling(false);
    }
  };

  const displayError = error ?? saveError;

  // ── render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">{localPlan.name}</h2>
          <p className="text-xs text-gray-500">{localPlan.cases.length} 个用例</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCancel}
            disabled={cancelling || plan.status !== "draft"}
            className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="取消测试计划"
          >
            {cancelling ? "取消中..." : "取消"}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={confirming || localPlan.status !== "draft"}
            className="px-3 py-1.5 text-xs font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="确认测试计划"
          >
            {confirming ? "确认中..." : plan.status === "draft" ? "确认计划" : "已确认"}
          </button>
        </div>
      </div>

      {displayError && (
        <div className="mx-4 mt-2 px-3 py-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-md whitespace-pre-line">
          {displayError}
          <button type="button" onClick={() => { setError(null); setSaveError(null); }} className="ml-2 underline">关闭</button>
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        {/* Case list */}
        <div className="w-48 flex-shrink-0 border-r border-gray-200 overflow-y-auto">
          {localPlan.cases.map((c) => {
            const isInvalid = invalidCaseIds.has(c.id);
            const isSelected = c.id === selectedCaseId;
            return (
              <div key={c.id} className={`group relative border-b ${isInvalid ? "border-l-2 border-l-red-500 bg-red-50" : isSelected ? "border-l-2 border-l-blue-500 bg-blue-50" : "border-gray-100"}`}>
                <button type="button" onClick={() => handleSelectCase(c.id)} className="w-full text-left px-3 py-2.5 hover:bg-gray-50 transition-colors pr-8">
                  <p className={`text-xs font-medium truncate ${isInvalid ? "text-red-700" : "text-gray-800"}`}>{c.case_name || <span className="italic text-gray-400">未命名</span>}</p>
                  {c.module && <p className="text-xs text-gray-400 truncate">{c.module}</p>}
                  <p className="text-xs text-gray-400">{c.steps.length} 步骤</p>
                  {isInvalid && <p className="text-xs text-red-500 mt-0.5">⚠ 校验未通过</p>}
                </button>
                <button type="button" onClick={() => handleDeleteCase(c.id)} disabled={deletingCaseId === c.id}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all disabled:opacity-30"
                  aria-label={`删除用例 ${c.case_name}`}>
                  {deletingCaseId === c.id ? "…" : "✕"}
                </button>
              </div>
            );
          })}
          {localPlan.cases.length === 0 && <p className="px-3 py-4 text-xs text-gray-400 text-center">暂无用例</p>}
          <button
            type="button"
            onClick={handleAddCase}
            disabled={addingCase}
            className="w-full px-3 py-2.5 text-xs text-blue-600 hover:bg-blue-50 border-t border-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {addingCase ? "添加中…" : "+ 添加用例"}
          </button>
        </div>

        {/* Case detail */}
        {selectedCase ? (
          <div className="flex-1 min-h-0 overflow-y-auto">
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
              newColError={newColError}
              editingCol={editingCol?.caseId === selectedCase.id ? editingCol : null}
              editColError={editColError}
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
              onNewColNameChange={(v) => { setNewColName((prev) => ({ ...prev, [selectedCase.id]: v })); setNewColError(null); }}
              onStartEditCol={(idx, name) => handleStartEditCol(selectedCase.id, idx, name)}
              onDeleteCustomCol={(idx) => handleDeleteCustomCol(selectedCase.id, idx)}
              onEditColChange={(v) => setEditingCol((prev) => prev ? { ...prev, value: v } : null)}
              onCommitEditCol={handleCommitEditCol}
              onCancelEditCol={() => { setEditingCol(null); setEditColError(null); }}
            />
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-gray-400">暂无用例</div>
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
  newColError: string | null;
  editingCol: { caseId: string; idx: number; value: string } | null;
  editColError: string | null;
  onMetaChange: (caseId: string, field: "case_name" | "start_url" | "module" | "function_point", value: string) => void;
  onStepChange: (caseId: string, idx: number, field: keyof TestStepView, value: string | boolean) => void;
  onAddStep: (caseId: string) => void;
  onDeleteStep: (caseId: string, idx: number) => void;
  onDragStart: (idx: number) => void;
  onDragOver: (e: React.DragEvent, idx: number) => void;
  onDragEnd: () => void;
  onAddVarRow: () => void;
  onPendingVarChange: (rowIdx: number, varName: string, value: string) => void;
  onDeletePendingRow: (rowIdx: number) => void;
  onDeleteSavedVarSet: (vsId: string) => void;
  onSaveVarRows: () => void;
  onAddCustomCol: () => void;
  onNewColNameChange: (v: string) => void;
  onStartEditCol: (idx: number, name: string) => void;
  onDeleteCustomCol: (idx: number) => void;
  onEditColChange: (v: string) => void;
  onCommitEditCol: () => void;
  onCancelEditCol: () => void;
}

function CaseDetail({
  testCase, varCols, varSets, pendingVarRows, loadingVars, savingSteps, savingVars,
  deletingVsId, newColName, newColError, editingCol, editColError,
  onMetaChange, onStepChange, onAddStep, onDeleteStep,
  onDragStart, onDragOver, onDragEnd,
  onAddVarRow, onPendingVarChange, onDeletePendingRow, onDeleteSavedVarSet, onSaveVarRows,
  onAddCustomCol, onNewColNameChange, onStartEditCol, onDeleteCustomCol, onEditColChange, onCommitEditCol, onCancelEditCol,
}: CaseDetailProps) {
  const noVarsFromLLM = testCase.global_variables.length === 0;
  const hasVarCols = varCols.length > 0;

  return (
    <div className="p-4 space-y-5">
      {/* ── Meta ── */}
      <section className="space-y-2">
        {savingSteps && <p className="text-xs text-blue-500">保存中...</p>}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">用例名称 *</label>
            <input type="text" value={testCase.case_name}
              onChange={(e) => onMetaChange(testCase.id, "case_name", e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              aria-label="用例名称" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">起始 URL *</label>
            <input type="text" value={testCase.start_url}
              onChange={(e) => onMetaChange(testCase.id, "start_url", e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              aria-label="起始 URL" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">模块</label>
            <input type="text" value={testCase.module ?? ""}
              onChange={(e) => onMetaChange(testCase.id, "module", e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              aria-label="模块" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-0.5">功能点</label>
            <input type="text" value={testCase.function_point ?? ""}
              onChange={(e) => onMetaChange(testCase.id, "function_point", e.target.value)}
              className="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
              aria-label="功能点" />
          </div>
        </div>
      </section>

      {/* ── Steps ── */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide">测试步骤</h4>
          <button type="button" onClick={() => onAddStep(testCase.id)} className="text-xs text-blue-600 hover:text-blue-800" aria-label="添加步骤">
            + 添加步骤
          </button>
        </div>
        <div className="border border-gray-200 rounded-md overflow-hidden">
          <table className="w-full text-xs table-fixed" role="table">
            <colgroup>
              <col className="w-5" />
              <col className="w-7" />
              <col className="w-[40%]" />
              <col className="w-[40%]" />
              <col className="w-10" />
              <col className="w-6" />
            </colgroup>
            <thead className="bg-gray-50">
              <tr>
                <th className="px-1 py-2 text-gray-400 w-5" title="拖拽排序" />
                <th className="px-2 py-2 text-left text-gray-500 font-medium">#</th>
                <th className="px-2 py-2 text-left text-gray-500 font-medium">操作描述</th>
                <th className="px-2 py-2 text-left text-gray-500 font-medium">预期结果</th>
                <th className="px-2 py-2 text-center text-gray-500 font-medium">视觉</th>
                <th className="w-6" />
              </tr>
            </thead>
            <tbody>
              {testCase.steps.map((step, idx) => (
                <tr key={step.step_number} className="border-t border-gray-100 group align-top"
                  onDragOver={(e) => onDragOver(e, idx)} onDragEnd={onDragEnd}>
                  <td className="px-1 py-2 text-gray-300 cursor-grab select-none text-center"
                    draggable onDragStart={() => onDragStart(idx)}>⠿</td>
                  <td className="px-2 py-2 text-gray-400">{step.step_number}</td>
                  <td className="px-2 py-1.5">
                    <StepTextarea
                      value={step.action_description}
                      placeholder="操作描述"
                      onChange={(v) => onStepChange(testCase.id, idx, "action_description", v)}
                      ariaLabel={`步骤 ${step.step_number} 操作描述`}
                    />
                  </td>
                  <td className="px-2 py-1.5">
                    <StepTextarea
                      value={step.expected_result ?? ""}
                      placeholder="无预期结果"
                      onChange={(v) => onStepChange(testCase.id, idx, "expected_result", v)}
                      ariaLabel={`步骤 ${step.step_number} 预期结果`}
                      muted
                    />
                  </td>
                  <td className="px-2 py-2 text-center">
                    <input type="checkbox" checked={step.is_visual_checkpoint}
                      onChange={(e) => onStepChange(testCase.id, idx, "is_visual_checkpoint", e.target.checked)}
                      aria-label={`步骤 ${step.step_number} 视觉检查点`} className="rounded" />
                  </td>
                  <td className="px-1 py-2 text-center">
                    <button type="button" onClick={() => onDeleteStep(testCase.id, idx)}
                      className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all"
                      aria-label={`删除步骤 ${step.step_number}`}>✕</button>
                  </td>
                </tr>
              ))}
              {testCase.steps.length === 0 && (
                <tr><td colSpan={6} className="px-2 py-3 text-center text-gray-400">暂无步骤，点击"添加步骤"</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Variable sets ── */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide">变量集</h4>
          {hasVarCols && (
            <button type="button" onClick={onAddVarRow} className="text-xs text-blue-600 hover:text-blue-800" aria-label="添加变量集行">
              + 添加一行
            </button>
          )}
        </div>

        {/* Add / rename custom column */}
        {noVarsFromLLM && (
          <div className="mb-2 space-y-1">
            <div className="flex items-center gap-2">
              <input type="text" value={newColName} onChange={(e) => onNewColNameChange(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && onAddCustomCol()}
                placeholder="变量名（英文，如 username）"
                maxLength={VAR_NAME_MAX}
                className="flex-1 text-xs border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300"
                aria-label="新变量名" />
              <button type="button" onClick={onAddCustomCol} disabled={!newColName.trim()}
                className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-40 transition-colors">
                添加变量
              </button>
            </div>
            {newColError && <p className="text-xs text-red-600">{newColError}</p>}
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
                  {varCols.map((v, colIdx) => (
                    <th key={v} className="px-2 py-2 text-left text-gray-500 font-medium">
                      {noVarsFromLLM ? (
                        editingCol?.idx === colIdx ? (
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-1">
                              <input type="text" value={editingCol.value} onChange={(e) => onEditColChange(e.target.value)}
                                onKeyDown={(e) => { if (e.key === "Enter") onCommitEditCol(); if (e.key === "Escape") onCancelEditCol(); }}
                                maxLength={VAR_NAME_MAX}
                                className="w-full text-xs border border-blue-300 rounded px-1 py-0.5 focus:outline-none"
                                autoFocus aria-label={`重命名变量 ${v}`} />
                              <button type="button" onClick={onCommitEditCol} className="text-blue-600 hover:text-blue-800 text-xs">✓</button>
                              <button type="button" onClick={onCancelEditCol} className="text-gray-400 hover:text-gray-600 text-xs">✕</button>
                            </div>
                            {editColError && <p className="text-xs text-red-600">{editColError}</p>}
                          </div>
                        ) : (
                          <span className="flex items-center gap-1 group/col">
                            <span>{v}</span>
                            <button type="button" onClick={() => onStartEditCol(colIdx, v)}
                              className="opacity-0 group-hover/col:opacity-100 text-gray-400 hover:text-blue-600 transition-all" title="重命名">
                              ✎
                            </button>
                            <button type="button" onClick={() => onDeleteCustomCol(colIdx)}
                              className="opacity-0 group-hover/col:opacity-100 text-gray-400 hover:text-red-500 transition-all" title="删除该变量列">
                              ✕
                            </button>
                          </span>
                        )
                      ) : v}
                    </th>
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
                      <button type="button" onClick={() => onDeleteSavedVarSet(vs.id)} disabled={deletingVsId === vs.id}
                        className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all disabled:opacity-30"
                        aria-label="删除该变量集">
                        {deletingVsId === vs.id ? "…" : "✕"}
                      </button>
                    </td>
                  </tr>
                ))}
                {pendingVarRows.map((row, rowIdx) => (
                  <tr key={`pending-${rowIdx}`} className="border-t border-blue-100 bg-blue-50">
                    {varCols.map((v) => (
                      <td key={v} className="px-1 py-1">
                        <input type="text" value={row[v] ?? ""} onChange={(e) => onPendingVarChange(rowIdx, v, e.target.value)}
                          className="w-full text-xs border border-gray-200 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-300"
                          aria-label={`变量 ${v} 第 ${rowIdx + 1} 行`} />
                      </td>
                    ))}
                    <td className="px-1 py-1 text-center">
                      <button type="button" onClick={() => onDeletePendingRow(rowIdx)}
                        className="p-0.5 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors" aria-label="删除该行">✕</button>
                    </td>
                  </tr>
                ))}
                {varSets.length === 0 && pendingVarRows.length === 0 && (
                  <tr><td colSpan={varCols.length + 1} className="px-2 py-3 text-center text-gray-400">暂无变量集，点击"添加一行"填写</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {pendingVarRows.length > 0 && (
          <button type="button" onClick={onSaveVarRows} disabled={savingVars}
            className="mt-2 px-3 py-1 text-xs font-medium rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            {savingVars ? "保存中..." : "保存变量集"}
          </button>
        )}
      </section>
    </div>
  );
}

// ── StepTextarea: plain textarea (no cursor issues) + highlight preview below ─

interface StepTextareaProps {
  value: string;
  placeholder: string;
  onChange: (v: string) => void;
  ariaLabel: string;
  muted?: boolean;
}

function toHighlightHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>")
    .replace(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g, '<span class="text-blue-600 font-medium">{$1}</span>');
}

function StepTextarea({ value, placeholder, onChange, ariaLabel, muted }: StepTextareaProps) {
  return (
    <div className="space-y-0.5">
      <textarea
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        aria-label={ariaLabel}
        rows={2}
        className={`w-full text-xs leading-relaxed resize-y border border-gray-200 rounded px-1.5 py-1 focus:outline-none focus:ring-1 focus:ring-blue-300 min-h-[40px] ${muted ? "text-gray-600" : "text-gray-800"}`}
      />
      {/* Variable highlight preview (only shown when text contains {var}) */}
      {/\{[a-zA-Z_][a-zA-Z0-9_]*\}/.test(value) && (
        <div
          className="text-xs leading-relaxed px-1.5 text-gray-500"
          dangerouslySetInnerHTML={{ __html: toHighlightHtml(value) }}
        />
      )}
    </div>
  );
}
