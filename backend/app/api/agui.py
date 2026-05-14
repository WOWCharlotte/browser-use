"""
AG-UI Protocol HTTP Agent Endpoint

使用 ag-ui-protocol SDK 实现标准的 AG-UI HTTP Agent 端点。
支持 SSE 流式输出事件。
"""
import asyncio
import json
from typing import Any, AsyncGenerator,List

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    StepStartedEvent,
    StepFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallResultEvent,
    ToolCallEndEvent,
    StateSnapshotEvent,
    BaseEvent,
)
from ag_ui.core.types import InputContent,TextInputContent
from ag_ui.encoder import EventEncoder
from app.utils import uuid7str
# Note: InterruptEvent and ResumeEvent are not in ag_ui.core yet
# Using CustomEvent or raw event fallback for HITL if needed

router = APIRouter()


# ============================================================================
# 事件映射
# ============================================================================

def map_agent_event_to_agui(event: dict[str, Any]) -> BaseEvent | None:
    """将 agent_service 事件映射为 AG-UI 事件"""
    event_type = event.get("type")
    run_id = event.get("run_id")
    thread_id = event.get("thread_id")

    if event_type == "STEP_STARTED":
        return StepStartedEvent(
            step_name=event.get("step_name", "Step"),
        )
    elif event_type == "STEP_FINISHED":
        return StepFinishedEvent(
            step_name=event.get("step_name", "Step"),
        )
    elif event_type == "TEXT_MESSAGE_START":
        return TextMessageStartEvent(
            message_id=event.get("message_id", uuid7str()),
            role=event.get("role", "assistant"),
        )
    elif event_type == "TEXT_MESSAGE_CONTENT":
        return TextMessageContentEvent(
            message_id=event.get("message_id", ""),
            delta=event.get("content", ""),
        )
    elif event_type == "TEXT_MESSAGE_END":
        return TextMessageEndEvent(
            message_id=event.get("message_id", ""),
        )
    elif event_type == "RUN_STARTED":
        return RunStartedEvent(
            thread_id=thread_id or uuid7str(),
            run_id=run_id or uuid7str(),
        )
    elif event_type == "RUN_FINISHED":
        return RunFinishedEvent(
            thread_id=thread_id or uuid7str(),
            run_id=run_id or uuid7str(),
            result=event.get("result"),
        )
    elif event_type == "RUN_ERROR":
        return RunErrorEvent(
            message=event.get("error", "Unknown error"),
            code=event.get("code"),
        )
    elif event_type == "STATE_SNAPSHOT":
        return StateSnapshotEvent(
            snapshot=event.get("state", {}),
        )
    elif event_type == "TOOL_CALL_START":
        return ToolCallStartEvent(
            tool_call_id=event.get("tool_call_id", uuid7str()),
            tool_call_name=event.get("tool_call_name", "unknown"),
        )
    elif event_type == "TOOL_CALL_ARGS":
        return ToolCallArgsEvent(
            tool_call_id=event.get("tool_call_id", ""),
            delta=event.get("delta", ""),
        )
    elif event_type == "TOOL_CALL_END":
        return ToolCallEndEvent(
            tool_call_id=event.get("tool_call_id", ""),
        )
    elif event_type == "TOOL_CALL_RESULT":
        return ToolCallResultEvent(
            tool_call_id=event.get("tool_call_id", ""),
            message_id=event.get("message_id", uuid7str()),
            content=event.get("content", ""),
        )
    elif event_type in ("INTERRUPT", "RESUME"):
        # HITL events - use CustomEvent or skip for now
        print(f"HITL event {event_type} - not yet supported in ag-ui-protocol SDK")
        return None
    elif event_type == "done":
        # 内部完成信号，不生成 AG-UI 事件
        return None
    elif event_type == "heartbeat":
        # 心跳，不生成事件
        return None
    else:
        # 未知事件类型，尝试作为原始事件返回
        print(f"Unknown event type: {event_type}")
        return None


def extract_task(input_data: RunAgentInput) -> str:
    """从 messages 提取用户任务"""
    user_message = ""
    if input_data.messages and len(input_data.messages) > 0:
        last_msg = input_data.messages[-1]
        if hasattr(last_msg, "role") and last_msg.role == "user":
            message = getattr(last_msg, "content", "")
            if not isinstance(message, str):
                for content in message:
                    if isinstance(content,TextInputContent):
                        user_message = content.text
                        break
            else:
                user_message = message
    return user_message


# ============================================================================
# API 端点
# ============================================================================

@router.post("/agui")
async def agui_endpoint(input_data: RunAgentInput, request: Request) -> StreamingResponse:
    """
    AG-UI Protocol HTTP Agent Endpoint

    接收 RunAgentInput，返回 SSE 流式事件。
    """
    from app.services.agent_service import agent_service
    from app.services.browser_service import browser_service

    accept_header = request.headers.get("accept")
    encoder = EventEncoder(accept=accept_header)
    session_id = input_data.thread_id or uuid7str()
    run_id = input_data.run_id or uuid7str()
    user_message = extract_task(input_data)

    async def event_generator() -> AsyncGenerator[str, None]:
        # 发送 RUN_STARTED
        run_started_event = RunStartedEvent(
            thread_id=session_id,
            run_id=run_id,
        )
        yield encoder.encode(run_started_event)

        # 确保浏览器会话存在
        if session_id not in browser_service._sessions:
            await browser_service.create_session(session_id)

        # 使用 asyncio.Queue 进行事件传递
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        agent_task = None

        async def on_event(event: dict[str, Any]) -> None:
            """事件回调 - 线程安全地加入队列"""
            event["run_id"] = run_id
            event["thread_id"] = session_id
            await event_queue.put(event)

        try:
            # 创建 agent 任务
            agent_task = asyncio.create_task(
                agent_service.run_agent(session_id, user_message, on_event)
            )

            # Yield 事件直到完成
            while not agent_task.done():
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=30.0)

                    # 映射为 AG-UI 事件并编码
                    agui_event = map_agent_event_to_agui(event)
                    if agui_event is not None:
                        yield encoder.encode(agui_event)
                except asyncio.TimeoutError:
                    # 发送心跳 - 使用原始事件格式
                    heartbeat = {"type": "heartbeat", "run_id": run_id}
                    yield f"data: {json.dumps(heartbeat)}\n\n"
                    continue

            # 处理剩余事件
            while not event_queue.empty():
                try:
                    event = event_queue.get_nowait()
                    agui_event = map_agent_event_to_agui(event)
                    if agui_event is not None:
                        yield encoder.encode(agui_event)
                except asyncio.QueueEmpty:
                    break

        except Exception as e:
            error_event = RunErrorEvent(
                message=str(e),
            )
            yield encoder.encode(error_event)
        finally:
            if agent_task and not agent_task.done():
                agent_task.cancel()

            # 发送 RUN_FINISHED
            finished_event = RunFinishedEvent(
                thread_id=session_id,
                run_id=run_id,
                result={"outcome": "success"},
            )
            yield encoder.encode(finished_event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )