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
    StateDeltaEvent,
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

# ── HITL resume 状态 ──────────────────────────────────────────────────────────
# session_id → asyncio.Event，解析完成后挂起等待用户确认
_resume_events: dict[str, asyncio.Event] = {}
# session_id → resume action ("confirm" | "cancel")
_resume_actions: dict[str, str] = {}


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
    """将内部事件映射为 AG-UI 协议事件"""
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
    elif event_type == "STATE_DELTA":
        return StateDeltaEvent(
            delta=event.get("delta", []),
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

                if case_count == 0:
                    # 解析成功但未提取到用例 — 文件内容无效
                    for chunk in _encode_text(
                        encoder, run_id,
                        "未能从上传的文件中提取到有效的测试用例。\n\n"
                        "有效的测试用例文件应包含以下内容：\n"
                        "• 用例名称（必填）\n"
                        "• 起始 URL（必填）\n"
                        "• 操作步骤（至少一步，描述具体的用户操作）\n"
                        "• 预期结果（可选，用于自动评估）\n\n"
                        "支持的格式：Excel（.xlsx）或 Markdown（.md）。\n"
                        "请检查文件内容后重新上传。",
                    ):
                        yield chunk
                    # 删除空计划
                    try:
                        from app.services.test_plan_service import test_plan_service
                        await test_plan_service.delete_plan(plan_detail.id)
                    except Exception:
                        pass
                    yield encoder.encode(RunFinishedEvent(
                        thread_id=session_id, run_id=run_id, result={"outcome": "empty_plan"}
                    ))
                    return

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

                # ── HITL：挂起等待用户确认，每 20s 发心跳保活 ──────────────
                resume_event = asyncio.Event()
                _resume_events[session_id] = resume_event
                try:
                    while not resume_event.is_set():
                        try:
                            await asyncio.wait_for(
                                asyncio.shield(resume_event.wait()),
                                timeout=20.0,
                            )
                        except asyncio.TimeoutError:
                            yield encoder.encode(
                                CustomEvent(name="heartbeat", value={"run_id": run_id})
                            )
                finally:
                    _resume_events.pop(session_id, None)

                # 读取用户动作：confirm 或 cancel
                resume_action = _resume_actions.pop(session_id, "confirm")

                if resume_action == "cancel":
                    # 用户取消计划 — 删除 draft 计划并终止
                    for chunk in _encode_text(encoder, run_id, "测试计划已取消。"):
                        yield chunk
                    try:
                        from app.services.test_plan_service import test_plan_service
                        await test_plan_service.delete_plan(plan_detail.id)
                    except Exception as e:
                        logger.warning(f"Failed to delete cancelled plan: {e}")
                    yield encoder.encode(RunFinishedEvent(
                        thread_id=session_id, run_id=run_id, result={"outcome": "cancelled"}
                    ))
                    return

                # 确认 → 自动启动执行
                for chunk in _encode_text(encoder, run_id, "测试计划已确认，正在启动执行..."):
                    yield chunk

                # 启动执行引擎
                from app.services.test_execution_service import test_execution_service

                exec_event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

                async def on_exec_event_from_ingestion(event: dict[str, Any]) -> None:
                    event["run_id"] = run_id
                    event["thread_id"] = session_id
                    await exec_event_queue.put(event)

                test_run_id = await test_execution_service.start_run(
                    plan_id=plan_detail.id,
                    max_concurrency=plan_detail.max_concurrency,
                    on_event=on_exec_event_from_ingestion,
                )

                for chunk in _encode_text(encoder, run_id, f"测试执行已启动 (run_id: {test_run_id})"):
                    yield chunk

                # 转发执行事件直到完成
                while True:
                    try:
                        event = await asyncio.wait_for(exec_event_queue.get(), timeout=30.0)
                        agui_event = map_agent_event_to_agui(event)
                        if agui_event is not None:
                            yield encoder.encode(agui_event)
                        # 检测执行完成
                        if event.get("type") == "STATE_DELTA":
                            delta = event.get("delta", [])
                            for op in delta:
                                if op.get("path") == "/run_progress/status" and op.get("value") in ("completed", "aborted"):
                                    for chunk in _encode_text(encoder, run_id, "测试执行完成。"):
                                        yield chunk
                                    yield encoder.encode(RunFinishedEvent(
                                        thread_id=session_id, run_id=run_id, result={"outcome": "execution_done"}
                                    ))
                                    return
                    except asyncio.TimeoutError:
                        yield encoder.encode(CustomEvent(name="heartbeat", value={"run_id": run_id}))
                        continue

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

        # ── 无附件：提示用户上传测试用例 ──────────────────────────────────────
        for chunk in _encode_text(
            encoder, run_id,
            "请先上传测试用例文件（Excel 或 Markdown），我会解析并生成测试计划供您确认后执行。"
        ):
            yield chunk

        yield encoder.encode(RunFinishedEvent(
            thread_id=session_id, run_id=run_id, result={"outcome": "awaiting_upload"}
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


@router.post("/agui/resume/{session_id}", status_code=200)
async def resume_endpoint(session_id: str, request: Request):
    """
    HITL Resume 端点。

    用户在前端确认或取消测试计划后调用此端点，唤醒挂起的 event_generator。
    body: {"action": "confirm"} 或 {"action": "cancel"}，默认 "confirm"。
    """
    event = _resume_events.get(session_id)
    if event is None:
        return {"ok": False, "reason": "no pending session"}
    # Parse action from body
    try:
        body = await request.json()
    except Exception:
        body = {}
    action = body.get("action", "confirm") if isinstance(body, dict) else "confirm"
    _resume_actions[session_id] = action
    event.set()
    return {"ok": True, "action": action}


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