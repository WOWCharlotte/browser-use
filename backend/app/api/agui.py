"""
AG-UI Protocol HTTP Agent Endpoint

实现符合 Agent-User Interaction (AG-UI) 协议的 HTTP Agent 端点。
支持 SSE 流式输出 BaseEvent 事件。
"""
import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter()


# ============================================================================
# AG-UI Event Types (参考 @ag-ui/core)
# ============================================================================

AGUI_EVENT_TYPES = Literal[
    "RUN_STARTED",
    "RUN_FINISHED",
    "RUN_ERROR",
    "STEP_STARTED",
    "STEP_FINISHED",
    "TEXT_MESSAGE_START",
    "TEXT_MESSAGE_CONTENT",
    "TEXT_MESSAGE_END",
    "TOOL_CALL_START",
    "TOOL_CALL_ARGS",
    "TOOL_CALL_RESULT",
    "TOOL_CALL_END",
    "STATE_SNAPSHOT",
    "STATE_DELTA",
    "INTERRUPT",
    "RESUME",
]


class BaseEvent(BaseModel):
    """AG-UI Base Event"""
    type: str
    run_id: str | None = None

    model_config = {"extra": "allow"}


class RunStartedEvent(BaseEvent):
    """运行开始事件"""
    type: Literal["RUN_STARTED"] = "RUN_STARTED"
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class RunFinishedEvent(BaseEvent):
    """运行结束事件"""
    type: Literal["RUN_FINISHED"] = "RUN_FINISHED"
    outcome: Literal["success", "stopped", "error"] = "success"
    result: Any = None


class RunErrorEvent(BaseEvent):
    """运行错误事件"""
    type: Literal["RUN_ERROR"] = "RUN_ERROR"
    error: str


class StepStartedEvent(BaseEvent):
    """步骤开始事件"""
    type: Literal["STEP_STARTED"] = "STEP_STARTED"
    step_number: int


class StepFinishedEvent(BaseEvent):
    """步骤结束事件"""
    type: Literal["STEP_FINISHED"] = "STEP_FINISHED"
    step_number: int


class TextMessageStartEvent(BaseEvent):
    """文本消息开始事件"""
    type: Literal["TEXT_MESSAGE_START"] = "TEXT_MESSAGE_START"
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Literal["user", "assistant"]


class TextMessageContentEvent(BaseEvent):
    """文本消息内容事件"""
    type: Literal["TEXT_MESSAGE_CONTENT"] = "TEXT_MESSAGE_CONTENT"
    content: str


class TextMessageEndEvent(BaseEvent):
    """文本消息结束事件"""
    type: Literal["TEXT_MESSAGE_END"] = "TEXT_MESSAGE_END"
    message_id: str


class ToolCallStartEvent(BaseEvent):
    """工具调用开始事件"""
    type: Literal["TOOL_CALL_START"] = "TOOL_CALL_START"
    tool_call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str


class ToolCallArgsEvent(BaseEvent):
    """工具参数事件"""
    type: Literal["TOOL_CALL_ARGS"] = "TOOL_CALL_ARGS"
    tool_call_id: str
    args: dict[str, Any] = {}


class ToolCallResultEvent(BaseEvent):
    """工具调用结果事件"""
    type: Literal["TOOL_CALL_RESULT"] = "TOOL_CALL_RESULT"
    tool_call_id: str
    result: str


class ToolCallEndEvent(BaseEvent):
    """工具调用结束事件"""
    type: Literal["TOOL_CALL_END"] = "TOOL_CALL_END"
    tool_call_id: str


class StateSnapshotEvent(BaseEvent):
    """状态快照事件"""
    type: Literal["STATE_SNAPSHOT"] = "STATE_SNAPSHOT"
    state: dict[str, Any] = {}


class InterruptEvent(BaseEvent):
    """中断事件 (HITL)"""
    type: Literal["INTERRUPT"] = "INTERRUPT"
    interrupt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reason: str
    step: int = 0


class ResumeEvent(BaseEvent):
    """恢复事件 (HITL)"""
    type: Literal["RESUME"] = "RESUME"
    step: int = 0


# ============================================================================
# RunAgentInput (参考 @ag-ui/client)
# ============================================================================

class MessageContent(BaseModel):
    """消息内容"""
    type: Literal["text", "image", "audio", "video", "tool_result", "tool_call"]
    text: str | None = None
    image: str | None = None
    audio: str | None = None
    video: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    args: dict[str, Any] | None = None
    result: str | None = None


class Message(BaseModel):
    """消息"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Literal["user", "assistant", "system", "tool", "activity"]
    content: str | list[MessageContent] = ""
    name: str | None = None


class ToolCall(BaseModel):
    """工具定义"""
    name: str
    description: str | None = None
    input_schema: dict[str, Any] = {}


class ContextEntry(BaseModel):
    """上下文条目"""
    key: str
    value: Any


class State(BaseModel):
    """状态"""
    # AG-UI 使用动态 state，这里用 dict 表示
    pass


class ForwardedProps(BaseModel):
    """透传属性"""
    pass


class RunAgentInput(BaseModel):
    """AG-UI RunAgentInput"""
    thread_id: str | None = None
    run_id: str | None = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[Message] = Field(default_factory=list)
    tools: list[ToolCall] = Field(default_factory=list)
    context: list[ContextEntry] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    forwarded_props: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


# ============================================================================
# 事件序列化辅助
# ============================================================================

def event_to_sse(event: dict[str, Any]) -> str:
    """将事件转换为 SSE 格式"""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def serialize_event(event: BaseEvent | dict[str, Any]) -> str:
    """序列化事件为 SSE 格式"""
    if isinstance(event, BaseEvent):
        return event_to_sse(event.model_dump(exclude_none=True))
    return event_to_sse(event)


# ============================================================================
# API 端点
# ============================================================================

@router.post("/agui")
async def agui_endpoint(input_data: RunAgentInput) -> StreamingResponse:
    """
    AG-UI Protocol HTTP Agent Endpoint

    接收 RunAgentInput，返回 SSE 流式 BaseEvent 事件。
    """
    from app.services.agent_service import agent_service
    from app.services.browser_service import browser_service

    run_id = input_data.run_id or str(uuid.uuid4())
    thread_id = input_data.thread_id or str(uuid.uuid4())

    # 从 messages 获取用户最新消息
    user_message = ""
    if input_data.messages:
        last_msg = input_data.messages[-1]
        if isinstance(last_msg.content, str):
            user_message = last_msg.content
        elif isinstance(last_msg.content, list):
            for content in reversed(last_msg.content):
                if content.type == "text" and content.text:
                    user_message = content.text
                    break

    # 使用 thread_id 作为 session_id
    session_id = thread_id

    async def event_generator() -> AsyncGenerator[str, None]:
        # 使用 asyncio.Queue 进行线程安全的事件传递
        event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        error_occurred = False

        def on_event(event: dict[str, Any]) -> None:
            """事件回调 - 将事件加入队列（线程安全）"""
            event["run_id"] = run_id
            event_queue.put_nowait(event)

        try:
            # 确保浏览器会话存在
            if session_id not in browser_service._sessions:
                await browser_service.create_session(session_id)

            # 发送 RUN_STARTED
            yield serialize_event({
                "type": "RUN_STARTED",
                "run_id": run_id,
            })

            # 创建 agent 任务
            agent_task = asyncio.create_task(
                agent_service.run_agent(session_id, user_message, on_event)
            )

            # Yield 事件直到完成
            while not agent_task.done():
                try:
                    # 等待新事件或超时
                    event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                    yield serialize_event(event)
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield event_to_sse({"type": "heartbeat", "run_id": run_id})
                    continue

            # 处理剩余事件
            while not event_queue.empty():
                try:
                    event = event_queue.get_nowait()
                    yield serialize_event(event)
                except asyncio.QueueEmpty:
                    break

            # 发送 RUN_FINISHED
            yield serialize_event({
                "type": "RUN_FINISHED",
                "run_id": run_id,
                "outcome": "success",
            })

        except Exception as e:
            error_occurred = True
            yield serialize_event({
                "type": "RUN_ERROR",
                "run_id": run_id,
                "error": str(e),
            })
        finally:
            # 取消 agent 任务如果还在运行
            if not agent_task.done():
                agent_task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )