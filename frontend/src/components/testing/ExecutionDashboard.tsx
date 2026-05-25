"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { RunProgress, CaseStatusEntry, CaseStatus } from "@/types/testing";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8888/api";

// ── Status color/icon mapping ────────────────────────────────────────────────

const STATUS_CONFIG: Record<CaseStatus, { color: string; icon: string; pulse?: boolean }> = {
  pending: { color: "text-gray-400", icon: "○" },
  running: { color: "text-blue-500", icon: "●", pulse: true },
  paused: { color: "text-yellow-500", icon: "⏸" },
  passed: { color: "text-green-500", icon: "✓" },
  failed: { color: "text-red-500", icon: "✗" },
  error: { color: "text-orange-500", icon: "⚠" },
};

// ── ExecutionSummaryBar ──────────────────────────────────────────────────────

function ExecutionSummaryBar({
  progress,
  onAbort,
}: {
  progress: RunProgress;
  onAbort: () => void;
}) {
  const [elapsed, setElapsed] = useState(0);
  const [showAbortConfirm, setShowAbortConfirm] = useState(false);

  useEffect(() => {
    if (progress.status !== "running") return;
    const start = new Date(progress.started_at).getTime();
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [progress.started_at, progress.status]);

  const pct = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex-shrink-0 p-3 border-b border-gray-200 space-y-2">
      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex gap-3">
          <span className="text-gray-600">{progress.completed}/{progress.total}</span>
          <span className="text-green-600">✓ {progress.passed}</span>
          <span className="text-red-600">✗ {progress.failed}</span>
          <span className="text-orange-600">⚠ {progress.error}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-500 font-mono">{formatTime(elapsed)}</span>
          {progress.status === "running" && (
            <div className="relative">
              <button
                onClick={() => setShowAbortConfirm(true)}
                className="px-2 py-0.5 text-xs bg-red-600 hover:bg-red-700 text-white rounded"
              >
                中止
              </button>
              {showAbortConfirm && (
                <div className="absolute right-0 top-6 z-10 bg-white border border-gray-200 rounded p-2 shadow-lg w-48">
                  <p className="text-xs text-gray-600 mb-2">确认中止？将强制关闭所有浏览器</p>
                  <div className="flex gap-1">
                    <button
                      onClick={() => { onAbort(); setShowAbortConfirm(false); }}
                      className="px-2 py-0.5 text-xs bg-red-600 text-white rounded"
                    >
                      确认
                    </button>
                    <button
                      onClick={() => setShowAbortConfirm(false)}
                      className="px-2 py-0.5 text-xs bg-gray-200 text-gray-700 rounded"
                    >
                      取消
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── LogStream ────────────────────────────────────────────────────────────────

function LogStream({ resultId }: { resultId: string }) {
  const [lines, setLines] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const expandedContainerRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(`${API_BASE}/test-results/${resultId}/logs/stream`);
    eventSourceRef.current = es;
    setConnected(true);

    es.addEventListener("log", (e) => {
      const data = JSON.parse(e.data);
      setLines((prev) => [...prev, ...data.split("\n").filter(Boolean)]);
    });

    es.addEventListener("done", () => {
      es.close();
      setConnected(false);
    });

    es.addEventListener("error", () => {
      setConnected(false);
    });

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [resultId]);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
    if (autoScroll && expandedContainerRef.current) {
      expandedContainerRef.current.scrollTop = expandedContainerRef.current.scrollHeight;
    }
  }, [lines, autoScroll]);

  const handleScroll = (el: HTMLDivElement | null) => {
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 30);
  };

  const getLineColor = (line: string) => {
    if (line.includes("[ERROR]")) return "text-red-600";
    if (line.includes("[WARN")) return "text-yellow-600";
    return "text-gray-700";
  };

  const logContent = (ref: React.RefObject<HTMLDivElement>, maxH: string) => (
    <div
      ref={ref as React.RefObject<HTMLDivElement>}
      onScroll={() => handleScroll(ref.current)}
      className={`${maxH} overflow-y-auto bg-gray-50 border border-gray-200 rounded p-2 font-mono text-xs`}
    >
      {lines.length === 0 && <span className="text-gray-400">等待日志...</span>}
      {lines.map((line, i) => (
        <div key={i} className={getLineColor(line)}>{line}</div>
      ))}
    </div>
  );

  return (
    <>
      <div className="relative">
        {logContent(containerRef, "max-h-[300px]")}
        <div className="absolute top-1 right-1 flex gap-1">
          <button
            onClick={() => setExpanded(true)}
            className="px-1.5 py-0.5 text-[10px] bg-gray-200 hover:bg-gray-300 text-gray-600 rounded"
            title="放大"
          >
            ⛶
          </button>
        </div>
        {!autoScroll && (
          <button
            onClick={() => { setAutoScroll(true); }}
            className="absolute bottom-2 right-2 px-2 py-0.5 text-xs bg-blue-600 text-white rounded"
          >
            跳到最新
          </button>
        )}
        {!connected && lines.length > 0 && (
          <div className="text-xs text-gray-400 mt-1">日志连接已断开</div>
        )}
      </div>

      {/* Expanded fullscreen overlay */}
      {expanded && (
        <div
          className="fixed inset-0 z-50 flex flex-col bg-black/80 p-4"
          onClick={() => setExpanded(false)}
        >
          <div
            className="flex-1 min-h-0 flex flex-col bg-white rounded-lg p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-700 font-mono">
                日志 — {lines.length} 行
                {connected && <span className="ml-2 text-green-500 animate-pulse">● 连接中</span>}
              </span>
              <button
                onClick={() => setExpanded(false)}
                className="px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 text-gray-700 rounded"
              >
                ✕ 关闭
              </button>
            </div>
            {logContent(expandedContainerRef, "flex-1")}
          </div>
        </div>
      )}
    </>
  );
}

// ── CaseScreenshot ───────────────────────────────────────────────────────────

function CaseScreenshot({ resultId, status }: { resultId: string; status: CaseStatus }) {
  const [loading, setLoading] = useState(false);
  const [screenshots, setScreenshots] = useState<{ step: number; screenshot: string }[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  const fetchScreenshots = useCallback(async () => {
    setLoading(true);
    try {
      if (status === "running") {
        // Live screenshot for running cases
        const res = await fetch(`${API_BASE}/test-results/${resultId}/screenshot`);
        const data = await res.json();
        if (data.success && data.data?.screenshot) {
          setScreenshots([{ step: 0, screenshot: data.data.screenshot }]);
        }
      } else {
        // Step screenshots for completed/failed cases
        const res = await fetch(`${API_BASE}/test-results/${resultId}/screenshots`);
        const data = await res.json();
        if (data.success && data.data?.screenshots?.length > 0) {
          setScreenshots(data.data.screenshots);
          setCurrentIndex(data.data.screenshots.length - 1); // Show last step by default
        }
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [resultId, status]);

  useEffect(() => {
    fetchScreenshots();
  }, [fetchScreenshots]);

  // Auto-refresh for running cases
  useEffect(() => {
    if (status !== "running") return;
    const interval = setInterval(fetchScreenshots, 3000);
    return () => clearInterval(interval);
  }, [status, fetchScreenshots]);

  if (loading && screenshots.length === 0) {
    return <div className="text-xs text-gray-500 p-2">加载截图...</div>;
  }
  if (screenshots.length === 0) {
    return <div className="text-xs text-gray-500 p-2">暂无截图</div>;
  }

  const current = screenshots[currentIndex];

  return (
    <div className="space-y-2">
      {/* Screenshot image — click to zoom */}
      <div
        className="relative cursor-zoom-in"
        onClick={() => setLightboxOpen(true)}
      >
        <img
          src={`data:image/png;base64,${current.screenshot}`}
          alt={`Step ${current.step} screenshot`}
          className="w-full rounded border border-gray-200"
        />
        {status === "running" && (
          <div className="absolute top-1 right-1 px-1.5 py-0.5 text-[10px] bg-blue-600 text-white rounded animate-pulse">
            LIVE
          </div>
        )}
      </div>

      {/* Step navigation (only for multi-step) */}
      {screenshots.length > 1 && (
        <div className="flex items-center justify-between text-xs">
          <button
            onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
            disabled={currentIndex === 0}
            className="px-2 py-0.5 rounded bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-30"
          >
            ◀
          </button>
          <span className="text-gray-500">
            Step {current.step} / {screenshots[screenshots.length - 1].step}
          </span>
          <button
            onClick={() => setCurrentIndex(Math.min(screenshots.length - 1, currentIndex + 1))}
            disabled={currentIndex === screenshots.length - 1}
            className="px-2 py-0.5 rounded bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-30"
          >
            ▶
          </button>
        </div>
      )}

      {/* Lightbox overlay */}
      {lightboxOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
          onClick={() => setLightboxOpen(false)}
        >
          <div className="relative max-w-[90vw] max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
            <img
              src={`data:image/png;base64,${current.screenshot}`}
              alt={`Step ${current.step} screenshot (zoomed)`}
              className="max-w-full max-h-[85vh] object-contain rounded"
            />
            <div className="absolute top-2 right-2 flex gap-2">
              {screenshots.length > 1 && (
                <span className="px-2 py-1 text-xs bg-white/90 text-gray-700 rounded shadow">
                  Step {current.step} / {screenshots[screenshots.length - 1].step}
                </span>
              )}
              <button
                onClick={() => setLightboxOpen(false)}
                className="px-2 py-1 text-xs bg-white/90 text-gray-700 rounded shadow hover:bg-white"
              >
                ✕
              </button>
            </div>
            {/* Navigation in lightbox */}
            {screenshots.length > 1 && (
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-3">
                <button
                  onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
                  disabled={currentIndex === 0}
                  className="px-3 py-1 rounded bg-white/90 text-gray-700 shadow disabled:opacity-30"
                >
                  ◀ 上一步
                </button>
                <button
                  onClick={() => setCurrentIndex(Math.min(screenshots.length - 1, currentIndex + 1))}
                  disabled={currentIndex === screenshots.length - 1}
                  className="px-3 py-1 rounded bg-white/90 text-gray-700 shadow disabled:opacity-30"
                >
                  下一步 ▶
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── CaseDetail ───────────────────────────────────────────────────────────────

function CaseDetail({
  resultId,
  status,
  errorMessage,
  onRetry,
  onPause,
  onResume,
  onStop,
}: {
  resultId: string;
  status: CaseStatus;
  errorMessage?: string;
  onRetry: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}) {
  const [tab, setTab] = useState<"logs" | "screenshot">("logs");

  return (
    <div className="border-t border-gray-200 p-2 space-y-2">
      {/* Tabs */}
      <div className="flex gap-2 text-xs">
        <button
          onClick={() => setTab("logs")}
          className={`px-2 py-0.5 rounded ${tab === "logs" ? "bg-gray-200 text-gray-800" : "text-gray-500"}`}
        >
          日志
        </button>
        {status !== "pending" && (
          <button
            onClick={() => setTab("screenshot")}
            className={`px-2 py-0.5 rounded ${tab === "screenshot" ? "bg-gray-200 text-gray-800" : "text-gray-500"}`}
          >
            截图
          </button>
        )}
      </div>

      {/* Content */}
      {tab === "logs" && status !== "pending" && <LogStream resultId={resultId} />}
      {tab === "logs" && status === "pending" && (
        <div className="text-xs text-gray-400 p-2">等待执行...</div>
      )}
      {tab === "screenshot" && <CaseScreenshot resultId={resultId} status={status} />}

      {/* Error message */}
      {errorMessage && (
        <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded p-2">{errorMessage}</div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        {status === "running" && (
          <>
            <button
              onClick={onPause}
              className="px-2 py-1 text-xs bg-yellow-600 hover:bg-yellow-700 text-white rounded"
            >
              暂停
            </button>
            <button
              onClick={onStop}
              className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded"
            >
              停止
            </button>
          </>
        )}
        {status === "paused" && (
          <>
            <button
              onClick={onResume}
              className="px-2 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded"
            >
              恢复
            </button>
            <button
              onClick={onStop}
              className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded"
            >
              停止
            </button>
          </>
        )}
        {(status === "failed" || status === "error") && (
          <button
            onClick={onRetry}
            className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded"
          >
            重试
          </button>
        )}
      </div>
    </div>
  );
}

// ── CaseRow ──────────────────────────────────────────────────────────────────

function CaseRow({
  entry,
  isExpanded,
  onToggle,
  onRetry,
  onPause,
  onResume,
  onStop,
}: {
  entry: CaseStatusEntry;
  isExpanded: boolean;
  onToggle: () => void;
  onRetry: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}) {
  const config = STATUS_CONFIG[entry.status];
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (entry.status === "running") {
      startRef.current = Date.now();
      const interval = setInterval(() => {
        setElapsed(Math.floor((Date.now() - (startRef.current || Date.now())) / 1000));
      }, 1000);
      return () => clearInterval(interval);
    } else if (entry.status === "paused") {
      // Keep showing elapsed but stop counting
      return;
    } else {
      startRef.current = null;
    }
  }, [entry.status]);

  return (
    <div className="border-b border-gray-100">
      <div
        onClick={onToggle}
        className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-50"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className={`${config.color} ${config.pulse ? "animate-pulse" : ""}`}>
            {config.icon}
          </span>
          <span className="text-sm text-gray-700 truncate">{entry.case_name}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 flex-shrink-0">
          {(entry.status === "running" || entry.status === "paused") && (
            <span className="font-mono">{Math.floor(elapsed / 60)}:{(elapsed % 60).toString().padStart(2, "0")}</span>
          )}
          <span className={config.color}>{entry.status}</span>
        </div>
      </div>
      {isExpanded && (
        <CaseDetail
          resultId={entry.result_id}
          status={entry.status}
          onRetry={onRetry}
          onPause={onPause}
          onResume={onResume}
          onStop={onStop}
        />
      )}
    </div>
  );
}

// ── ExecutionComplete ────────────────────────────────────────────────────────

function ExecutionComplete({
  progress,
  onViewReport,
}: {
  progress: RunProgress;
  onViewReport: () => void;
}) {
  const pct = progress.total > 0 ? Math.round((progress.passed / progress.total) * 100) : 0;

  return (
    <div className="flex-shrink-0 p-3 border-t border-gray-200 bg-gray-50">
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-700">
          执行完成 — 通过率 <span className="text-green-600 font-bold">{pct}%</span>
          {" "}({progress.passed}/{progress.total})
        </div>
        <button
          onClick={onViewReport}
          className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded"
        >
          查看报告
        </button>
      </div>
    </div>
  );
}

// ── ExecutionDashboard (main) ────────────────────────────────────────────────

interface ExecutionDashboardProps {
  runProgress: RunProgress;
  caseStatuses: CaseStatusEntry[];
}

export default function ExecutionDashboard({ runProgress, caseStatuses }: ExecutionDashboardProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleAbort = async () => {
    try {
      await fetch(`${API_BASE}/test-runs/${runProgress.run_id}/abort`, { method: "POST" });
    } catch (e) {
      console.error("Abort failed:", e);
    }
  };

  const handleRetry = async (resultId: string) => {
    try {
      await fetch(`${API_BASE}/test-results/${resultId}/retry`, { method: "POST" });
    } catch (e) {
      console.error("Retry failed:", e);
    }
  };

  const handlePause = async (resultId: string) => {
    try {
      await fetch(`${API_BASE}/test-results/${resultId}/pause`, { method: "POST" });
    } catch (e) {
      console.error("Pause failed:", e);
    }
  };

  const handleResume = async (resultId: string) => {
    try {
      await fetch(`${API_BASE}/test-results/${resultId}/resume`, { method: "POST" });
    } catch (e) {
      console.error("Resume failed:", e);
    }
  };

  const handleStop = async (resultId: string) => {
    try {
      await fetch(`${API_BASE}/test-results/${resultId}/stop`, { method: "POST" });
    } catch (e) {
      console.error("Stop failed:", e);
    }
  };

  const handleViewReport = () => {
    window.open(`${API_BASE}/test-runs/${runProgress.run_id}/report`, "_blank");
  };

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden bg-white text-gray-800">
      <ExecutionSummaryBar progress={runProgress} onAbort={handleAbort} />

      {/* Case list */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {caseStatuses.map((entry) => (
          <CaseRow
            key={entry.result_id}
            entry={entry}
            isExpanded={expandedId === entry.result_id}
            onToggle={() => setExpandedId(expandedId === entry.result_id ? null : entry.result_id)}
            onRetry={() => handleRetry(entry.result_id)}
            onPause={() => handlePause(entry.result_id)}
            onResume={() => handleResume(entry.result_id)}
            onStop={() => handleStop(entry.result_id)}
          />
        ))}
      </div>

      {/* Completion bar */}
      {runProgress.status !== "running" && (
        <ExecutionComplete progress={runProgress} onViewReport={handleViewReport} />
      )}
    </div>
  );
}
