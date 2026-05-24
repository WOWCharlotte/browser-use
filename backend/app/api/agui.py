"""
AG-UI Protocol HTTP Agent Endpoint

使用 ag-ui-protocol SDK 实现标准的 AG-UI HTTP Agent 端点。
支持 SSE 流式输出事件。
"""
import asyncio
import base64
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from ag_ui.core import (
    BaseEvent,
    CustomEvent,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateSnapshotEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)
from ag_ui.core.types import DocumentInputContent, InputContentDataSource, TextInputContent
from ag_ui.encoder import EventEncoder
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.utils import uuid7str

logger = logging.getLogger(__name__)

# Note: InterruptEvent and ResumeEvent are not in ag_ui.core yet
# Using CustomEvent or raw event fallback for HITL if needed

router = APIRouter()


# ============================================================================
# 附件提取
# ============================================================================

@dataclass
class ExtractedInput:
    text: str
    attachments: list[tuple[str, bytes, str]]  # (filename, content_bytes, mime_type)


def extract_input(input_data: RunAgentInput) -> ExtractedInput:
    """从最后一条 user 消息中提取文本和文件附件。"""
    text = ""
    attachments: list[tuple[str, bytes, str]] = []

    if not input_data.messages:
        return ExtractedInput(text=text, attachments=attachments)

    last_msg = input_data.messages[-1]
    if not (hasattr(last_msg, "role") and last_msg.role == "user"):
        return ExtractedInput(text=text, attachments=attachments)

    content = getattr(last_msg, "content", "")
    if isinstance(content, str):
        return ExtractedInput(text=content, attachments=attachments)

    for part in content:
        if isinstance(part, TextInputContent):
            text = part.text
        elif isinstance(part, DocumentInputContent):
            source = part.source
            if not isinstance(source, InputContentDataSource):
                continue
            # metadata may carry filename from CopilotKit
            meta = part.metadata or {}
            filename: str = (
                meta.get("filename") or meta.get("name") or "upload"
            )
            try:
                file_bytes = base64.b64decode(source.value)
            except Exception as exc:
                logger.warning(f"Failed to decode attachment '{filename}': {exc}")
                continue
            attachments.append((filename, file_bytes, source.mime_type))

    return ExtractedInput(text=text, attachments=attachments)


# ============================================================================
# 事件映射
# ============================================================================


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
    elif event_type in ("PAUSE", "RESUME","STOP"):
        return CustomEvent(
            name=event_type.lower(),
            value=event.get("value", {})
        )
    elif event_type == "DONE":
        return CustomEvent(name="done", value=event.get("value", {}))
    elif event_type == "HEARTBEAT":
        return CustomEvent(name="heartbeat", value=event.get("value", {}))
    elif event_type == "DONE":
        return CustomEvent(
            name="done", 
            value=event.get("value", {})
        )
    elif event_type == "HEARTBEAT":
        return CustomEvent(
            name="heartbeat", 
            value=event.get("value", {})
        )
    else:
        return CustomEvent(name="unknown_event", value={"event_type": event_type})


def extract_task(input_data: RunAgentInput) -> str:
    """从 messages 提取用户任务文本（向后兼容）。"""
    return extract_input(input_data).text


# ============================================================================
# API 端点
# ============================================================================

@router.post("/agui")
async def agui_endpoint(input_data: RunAgentInput, request: Request) -> StreamingResponse:
    """
    AG-UI Protocol HTTP Agent Endpoint

    接收 RunAgentInput，返回 SSE 流式事件。
    当消息携带文件附件（Excel/Markdown）时，触发测试用例解析流程。
    """
    from app.services.agent_service import agent_service
    from app.services.browser_service import browser_service

    accept_header = request.headers.get("accept", "*/*")
    encoder = EventEncoder(accept=accept_header)
    session_id = input_data.thread_id or uuid7str()
    run_id = input_data.run_id or uuid7str()

    extracted = extract_input(input_data)
    user_message = extracted.text
    attachments = extracted.attachments

    # Ensure session and user message are persisted in DB
    from app.services.session_service import session_service
    session = await session_service.get_session(session_id)
    if not session:
        await session_service.create_session(title=user_message[:30] or "Conversation", session_id=session_id)
    else:
        if session.title == "New conversation" and user_message:
            await session_service.update_session(session_id, user_message[:30])

    if user_message:
        existing_msgs = await session_service.get_messages(session_id)
        if not any(m.role == "user" and m.content == user_message for m in existing_msgs):
            await session_service.add_message(session_id, "user", user_message)

    async def event_generator() -> AsyncGenerator[str, None]:
        yield encoder.encode(RunStartedEvent(thread_id=session_id, run_id=run_id))

        # ── 文件附件：触发测试用例解析流程 ──────────────────────────────────
        if attachments:
            for chunk in _encode_text(encoder, run_id, "正在解析测试用例文件，请稍候..."):
                yield chunk
            try:
                plan_detail = await _handle_attachments(
                    attachments=attachments,
                    plan_name=user_message or attachments[0][0],
                )
                case_count = len(plan_detail.cases)
                for chunk in _encode_text(
                    encoder, run_id,
                    f"解析完成，共提取 {case_count} 个测试用例。请在右侧面板确认并编辑后点击「确认计划」。",
                ):
                    yield chunk
                yield encoder.encode(StateSnapshotEvent(
                    snapshot={
                        "panel_mode": "case_editor",
                        "test_plan": plan_detail.model_dump(),
                    }
                ))
            except ValueError as exc:
                for chunk in _encode_text(encoder, run_id, f"解析失败：{exc}"):
                    yield chunk
            except Exception as exc:
                logger.exception("Unexpected error during attachment ingestion")
                for chunk in _encode_text(encoder, run_id, "解析时发生内部错误，请重试。"):
                    yield chunk

            yield encoder.encode(RunFinishedEvent(
                thread_id=session_id, run_id=run_id, result={"outcome": "ingestion"}
            ))
            return

        # ── 普通消息：走 Agent 执行流程 ──────────────────────────────────────
        if session_id not in browser_service._sessions:
            await browser_service.create_session(session_id)

        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        agent_task = None

        async def on_event(event: dict[str, Any]) -> None:
            event["run_id"] = run_id
            event["thread_id"] = session_id
            await event_queue.put(event)

        try:
            agent_task = asyncio.create_task(
                agent_service.run_agent(session_id, user_message, on_event)
            )

            while not agent_task.done():
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                    agui_event = map_agent_event_to_agui(event)
                    if agui_event is not None:
                        yield encoder.encode(agui_event)
                except asyncio.TimeoutError:
                    heartbeat_event = {"type": "HEARTBEAT", "value": {"run_id": run_id}}
                    agui_event = map_agent_event_to_agui(heartbeat_event)
                    if agui_event is not None:
                        yield encoder.encode(agui_event)
                    continue

            while not event_queue.empty():
                try:
                    event = event_queue.get_nowait()
                    agui_event = map_agent_event_to_agui(event)
                    if agui_event is not None:
                        yield encoder.encode(agui_event)
                except asyncio.QueueEmpty:
                    break

        except Exception as e:
            yield encoder.encode(RunErrorEvent(message=str(e)))
        finally:
            if agent_task and not agent_task.done():
                agent_task.cancel()
            yield encoder.encode(RunFinishedEvent(
                thread_id=session_id, run_id=run_id, result={"outcome": "success"}
            ))

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# 附件处理辅助函数
# ============================================================================

async def _handle_attachments(
    attachments: list[tuple[str, bytes, str]],
    plan_name: str,
) -> Any:
    """解析第一个支持的文件附件，创建测试计划并返回 TestPlanDetailView。"""
    from app.services.ingestion_service import ingestion_service
    from app.services.test_plan_service import test_plan_service

    filename, file_bytes, _mime = attachments[0]
    logger.info(f"Ingesting attachment: {filename} ({len(file_bytes)} bytes)")

    parsed_plan = await ingestion_service.ingest_file(filename, file_bytes)
    plan_detail = await test_plan_service.import_parsed_plan(
        parsed=parsed_plan,
        name=plan_name or filename,
        source_file_name=filename,
    )
    return plan_detail


def _encode_text(encoder: EventEncoder, run_id: str, text: str) -> list[str]:
    """生成一条完整的 assistant 文本消息事件序列（start + content + end）。"""
    msg_id = uuid7str()
    return [
        encoder.encode(TextMessageStartEvent(message_id=msg_id, role="assistant")),
        encoder.encode(TextMessageContentEvent(message_id=msg_id, delta=text)),
        encoder.encode(TextMessageEndEvent(message_id=msg_id)),
    ]