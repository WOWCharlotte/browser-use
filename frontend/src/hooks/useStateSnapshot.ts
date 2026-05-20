/**
 * useStateSnapshot — 订阅 Agent 的 StateSnapshotEvent 并解析状态快照
 *
 * @param agentId  要订阅的 agent id，默认 "default"
 * @example
 * ```tsx
 * function BrowserStateDisplay() {
 *   const { snapshot, isLoading } = useStateSnapshot("default");
 *
 *   if (!snapshot) return null;
 *
 *   // snapshot 的结构取决于后端 agent_service 发出的 StateSnapshotEvent 内容
 *   return (
 *     <div>
 *       <pre>{JSON.stringify(snapshot, null, 2)}</pre>
 *     </div>
 *   );
 * }
 * ```
 */
"use client";

import { useState, useEffect, useRef } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import type { AgentSubscriber } from "@ag-ui/client";
import type { StateSnapshotEvent } from "@ag-ui/client";

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
