/**
 * useStateSnapshot — 订阅 Agent 的 StateSnapshotEvent 和 StateDeltaEvent
 *
 * StateSnapshot: 完整状态替换
 * StateDelta: JSON Patch (RFC 6902) 增量更新
 */
"use client";

import { useState, useEffect, useRef } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import type { AgentSubscriber } from "@ag-ui/client";
import type { StateSnapshotEvent } from "@ag-ui/client";
import { applyPatch } from "fast-json-patch";

export interface UseStateSnapshotOptions {
  /** 订阅哪个 agent，默认为 "default" */
  agentId?: string;
}

export interface UseStateSnapshotResult {
  /** 最近一次收到的 StateSnapshotEvent.snapshot，初始为 undefined */
  snapshot: Record<string, unknown> | undefined;
  /** 尚未收到过任何快照时为 true */
  isLoading: boolean;
  /** 所有历史快照列表，按时间顺序排列（最新在最后） */
  history: Record<string, unknown>[];
}

export function useStateSnapshot(
  options: UseStateSnapshotOptions = {},
): UseStateSnapshotResult {
  const { agentId } = options;
  const { agent } = useAgent({ agentId: agentId ?? "default" });

  const [history, setHistory] = useState<Record<string, unknown>[]>([]);
  const hasSnapshot = useRef(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!agent) return;

    const subscriber: AgentSubscriber = {
      onStateSnapshotEvent({ event }) {
        const typedEvent = event as StateSnapshotEvent;
        const state = typedEvent.snapshot as Record<string, unknown> | undefined;
        if (state) {
          hasSnapshot.current = true;
          const eventHistory = state.history as Record<string, unknown>[] | undefined;
          setHistory(eventHistory ?? [state]);
          setIsLoading(false);
        }
      },
      onStateDeltaEvent({ event }) {
        // Apply JSON Patch (RFC 6902) incremental update
        const delta = (event as { delta?: unknown[] }).delta;
        if (!delta || !Array.isArray(delta)) return;

        setHistory((prev) => {
          if (prev.length === 0) return prev;
          const current = prev[prev.length - 1];
          try {
            const patched = applyPatch(
              structuredClone(current),
              delta as Parameters<typeof applyPatch>[1],
            ).newDocument;
            return [...prev.slice(0, -1), patched as Record<string, unknown>];
          } catch (e) {
            console.warn("StateDelta applyPatch failed:", e);
            return prev;
          }
        });
      },
    };

    const { unsubscribe } = agent.subscribe(subscriber);
    return unsubscribe;
  }, [agent]);

  useEffect(() => {
    setHistory([]);
    setIsLoading(true);
    hasSnapshot.current = false;
  }, [agent]);

  return {
    snapshot: history[history.length - 1] ?? undefined,
    isLoading: isLoading && !hasSnapshot.current,
    history,
  };
}
