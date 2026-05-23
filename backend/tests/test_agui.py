"""
AG-UI 协议集成单元测试

测试内容:
1. 事件映射函数 map_agent_event_to_agui
2. 任务提取函数 extract_task
3. AG-UI 端点功能测试
"""
import sys
from pathlib import Path

import pytest

# 添加 backend 目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ag_ui.core import (
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
from ag_ui.core.types import TextInputContent, UserMessage
from ag_ui.encoder import EventEncoder
from app.api.agui import extract_task, map_agent_event_to_agui, router

# ============================================================================
# 测试事件映射函数
# ============================================================================

class TestMapAgentEventToAgui:
    """测试 map_agent_event_to_agui 函数"""

    def test_run_started_event_mapping(self):
        """测试 RUN_STARTED 事件映射"""
        event = {
            "type": "RUN_STARTED",
            "run_id": "test-run-123",
            "thread_id": "test-thread-456",
        }
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, RunStartedEvent)
        assert result.run_id == "test-run-123"
        assert result.thread_id == "test-thread-456"

    def test_run_started_without_ids(self):
        """测试 RUN_STARTED 事件自动生成 ID"""
        event = {"type": "RUN_STARTED"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, RunStartedEvent)
        assert result.run_id is not None
        assert result.thread_id is not None

    def test_run_finished_event_mapping(self):
        """测试 RUN_FINISHED 事件映射"""
        event = {
            "type": "RUN_FINISHED",
            "run_id": "test-run",
            "thread_id": "test-thread",
            "result": {"outcome": "success"},
        }
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, RunFinishedEvent)
        assert result.run_id == "test-run"
        assert result.thread_id == "test-thread"
        assert result.result == {"outcome": "success"}

    def test_run_error_event_mapping(self):
        """测试 RUN_ERROR 事件映射"""
        event = {
            "type": "RUN_ERROR",
            "error": "Something went wrong",
            "code": "ERR_001",
        }
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, RunErrorEvent)
        assert result.message == "Something went wrong"
        assert result.code == "ERR_001"

    def test_run_error_with_default_message(self):
        """测试 RUN_ERROR 默认错误消息"""
        event = {"type": "RUN_ERROR"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, RunErrorEvent)
        assert result.message == "Unknown error"

    def test_text_message_start_event_mapping(self):
        """测试 TEXT_MESSAGE_START 事件映射"""
        event = {
            "type": "TEXT_MESSAGE_START",
            "message_id": "msg-123",
            "role": "assistant",
        }
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, TextMessageStartEvent)
        assert result.message_id == "msg-123"
        assert result.role == "assistant"

    def test_text_message_start_auto_generate_message_id(self):
        """测试 TEXT_MESSAGE_START 自动生成 message_id"""
        event = {"type": "TEXT_MESSAGE_START"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, TextMessageStartEvent)
        assert result.message_id is not None
        assert result.role == "assistant"

    def test_text_message_content_event_mapping(self):
        """测试 TEXT_MESSAGE_CONTENT 事件映射"""
        event = {
            "type": "TEXT_MESSAGE_CONTENT",
            "message_id": "msg-123",
            "content": "Hello, world!",
        }
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, TextMessageContentEvent)
        assert result.message_id == "msg-123"
        assert result.delta == "Hello, world!"

    def test_text_message_content_without_message_id(self):
        """测试 TEXT_MESSAGE_CONTENT 没有 message_id"""
        event = {"type": "TEXT_MESSAGE_CONTENT", "content": "Hello"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, TextMessageContentEvent)
        assert result.message_id == ""
        assert result.delta == "Hello"

    def test_text_message_end_event_mapping(self):
        """测试 TEXT_MESSAGE_END 事件映射"""
        event = {
            "type": "TEXT_MESSAGE_END",
            "message_id": "msg-123",
        }
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, TextMessageEndEvent)
        assert result.message_id == "msg-123"

    def test_step_started_event_mapping(self):
        """测试 STEP_STARTED 事件映射"""
        event = {"type": "STEP_STARTED", "step_name": "Step 1"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, StepStartedEvent)
        assert result.step_name == "Step 1"

    def test_step_started_default_name(self):
        """测试 STEP_STARTED 默认步骤名"""
        event = {"type": "STEP_STARTED"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, StepStartedEvent)
        assert result.step_name == "Step"

    def test_step_finished_event_mapping(self):
        """测试 STEP_FINISHED 事件映射"""
        event = {"type": "STEP_FINISHED", "step_name": "Step 1"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, StepFinishedEvent)
        assert result.step_name == "Step 1"

    def test_state_snapshot_event_mapping(self):
        """测试 STATE_SNAPSHOT 事件映射"""
        state_data = {"key": "value", "nested": {"data": True}}
        event = {"type": "STATE_SNAPSHOT", "state": state_data}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, StateSnapshotEvent)
        assert result.snapshot == state_data

    def test_state_snapshot_default_empty_dict(self):
        """测试 STATE_SNAPSHOT 默认空字典"""
        event = {"type": "STATE_SNAPSHOT"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, StateSnapshotEvent)
        assert result.snapshot == {}

    def test_tool_call_start_event_mapping(self):
        """测试 TOOL_CALL_START 事件映射"""
        event = {
            "type": "TOOL_CALL_START",
            "tool_call_id": "tc-123",
            "tool_call_name": "browse_page",
        }
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, ToolCallStartEvent)
        assert result.tool_call_id == "tc-123"
        assert result.tool_call_name == "browse_page"

    def test_tool_call_start_auto_generate_id(self):
        """测试 TOOL_CALL_START 自动生成 ID"""
        event = {"type": "TOOL_CALL_START", "tool_call_name": "test_tool"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, ToolCallStartEvent)
        assert result.tool_call_id is not None
        assert result.tool_call_name == "test_tool"

    def test_tool_call_args_event_mapping(self):
        """测试 TOOL_CALL_ARGS 事件映射"""
        event = {
            "type": "TOOL_CALL_ARGS",
            "tool_call_id": "tc-123",
            "delta": '{"url": "https://example.com"}',
        }
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, ToolCallArgsEvent)
        assert result.tool_call_id == "tc-123"
        assert result.delta == '{"url": "https://example.com"}'

    def test_tool_call_end_event_mapping(self):
        """测试 TOOL_CALL_END 事件映射"""
        event = {"type": "TOOL_CALL_END", "tool_call_id": "tc-123"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, ToolCallEndEvent)
        assert result.tool_call_id == "tc-123"

    def test_tool_call_result_event_mapping(self):
        """测试 TOOL_CALL_RESULT 事件映射"""
        event = {
            "type": "TOOL_CALL_RESULT",
            "tool_call_id": "tc-123",
            "message_id": "msg-456",
            "content": "Tool executed successfully",
        }
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, ToolCallResultEvent)
        assert result.tool_call_id == "tc-123"
        assert result.message_id == "msg-456"
        assert result.content == "Tool executed successfully"

    def test_tool_call_result_auto_generate_ids(self):
        """测试 TOOL_CALL_RESULT 自动生成 ID"""
        event = {"type": "TOOL_CALL_RESULT", "content": "Result"}
        result = map_agent_event_to_agui(event)
        assert result is not None
        assert isinstance(result, ToolCallResultEvent)
        assert result.tool_call_id == ""
        assert result.message_id is not None
        assert result.content == "Result"

    def test_interrupt_event_returns_none(self):
        """测试 INTERRUPT 事件返回 None"""
        event = {"type": "INTERRUPT", "reason": "awaiting_user"}
        result = map_agent_event_to_agui(event)
        assert result is None

    def test_resume_event_returns_none(self):
        """测试 RESUME 事件返回 None"""
        event = {"type": "RESUME", "step": 5}
        result = map_agent_event_to_agui(event)
        assert result is None

    def test_done_event_returns_none(self):
        """测试 done 内部信号返回 None"""
        event = {"type": "done", "step": 5}
        result = map_agent_event_to_agui(event)
        assert result is None

    def test_heartbeat_event_returns_none(self):
        """测试心跳事件返回 None"""
        event = {"type": "heartbeat", "run_id": "test-run"}
        result = map_agent_event_to_agui(event)
        assert result is None

    def test_unknown_event_type_returns_none(self):
        """测试未知事件类型返回 None"""
        event = {"type": "UNKNOWN_EVENT"}
        result = map_agent_event_to_agui(event)
        assert result is None


# ============================================================================
# 测试任务提取函数
# ============================================================================

class TestExtractTask:
    """测试 extract_task 函数"""

    def test_extract_from_string_content(self):
        """测试从字符串内容提取任务"""
        msg = UserMessage(id="msg-1", role="user", content="Hello, agent!")
        input_data = RunAgentInput(
            thread_id="thread-1",
            run_id="run-1",
            state={},
            tools=[],
            context=[],
            forwarded_props={},
            messages=[msg],
        )
        result = extract_task(input_data)
        assert result == "Hello, agent!"

    def test_extract_from_list_content(self):
        """测试从列表内容提取任务"""
        msg = UserMessage(
            id="msg-1",
            role="user",
            content=[TextInputContent(type="text", text="List content message")],
        )
        input_data = RunAgentInput(
            thread_id="thread-1",
            run_id="run-1",
            state={},
            tools=[],
            context=[],
            forwarded_props={},
            messages=[msg],
        )
        result = extract_task(input_data)
        assert result == "List content message"

    def test_extract_from_last_message(self):
        """测试从最后一条消息提取任务"""
        msg1 = UserMessage(id="msg-1", role="user", content="First message")
        msg2 = UserMessage(id="msg-2", role="user", content="Second message")
        input_data = RunAgentInput(
            thread_id="thread-1",
            run_id="run-1",
            state={},
            tools=[],
            context=[],
            forwarded_props={},
            messages=[msg1, msg2],
        )
        result = extract_task(input_data)
        assert result == "Second message"

    def test_extract_from_empty_messages(self):
        """测试空消息列表"""
        input_data = RunAgentInput(
            thread_id="thread-1",
            run_id="run-1",
            state={},
            tools=[],
            context=[],
            forwarded_props={},
            messages=[],
        )
        result = extract_task(input_data)
        assert result == ""


# ============================================================================
# 测试端点路由
# ============================================================================

class TestAGUIEndpoint:
    """测试 AGUI 端点注册"""

    def test_endpoint_route_registered(self):
        """测试端点已注册"""
        routes = [route.path for route in router.routes]
        assert "/agui" in routes

    def test_endpoint_accepts_post(self):
        """测试端点接受 POST 请求"""
        post_routes = [
            route.path for route in router.routes
            if hasattr(route, "methods") and "POST" in route.methods
        ]
        assert "/agui" in post_routes


# ============================================================================
# 测试事件编码
# ============================================================================

class TestEventEncoder:
    """测试事件编码器"""

    def test_encode_run_started_event(self):
        """测试 RunStartedEvent 编码"""
        event = {"type": "RUN_STARTED", "run_id": "run-123", "thread_id": "thread-456"}
        agui_event = map_agent_event_to_agui(event)
        encoder = EventEncoder()
        encoded = encoder.encode(agui_event)

        assert encoded.startswith("data: ")
        assert "RUN_STARTED" in encoded or "run_started" in encoded.lower()

    def test_encode_text_message_events(self):
        """测试文本消息事件编码"""
        encoder = EventEncoder()

        # Start event
        start_event = {"type": "TEXT_MESSAGE_START", "message_id": "msg-1", "role": "assistant"}
        start_agui = map_agent_event_to_agui(start_event)
        start_encoded = encoder.encode(start_agui)
        assert start_encoded.startswith("data: ")

        # Content event
        content_event = {"type": "TEXT_MESSAGE_CONTENT", "message_id": "msg-1", "content": "Hello"}
        content_agui = map_agent_event_to_agui(content_event)
        content_encoded = encoder.encode(content_agui)
        assert content_encoded.startswith("data: ")

        # End event
        end_event = {"type": "TEXT_MESSAGE_END", "message_id": "msg-1"}
        end_agui = map_agent_event_to_agui(end_event)
        end_encoded = encoder.encode(end_agui)
        assert end_encoded.startswith("data: ")

    def test_encode_tool_call_events(self):
        """测试工具调用事件编码"""
        encoder = EventEncoder()

        # Start event
        start_event = {"type": "TOOL_CALL_START", "tool_call_id": "tc-1", "tool_call_name": "test_tool"}
        start_agui = map_agent_event_to_agui(start_event)
        start_encoded = encoder.encode(start_agui)
        assert start_encoded.startswith("data: ")

        # Args event
        args_event = {"type": "TOOL_CALL_ARGS", "tool_call_id": "tc-1", "delta": '{"arg": 1}'}
        args_agui = map_agent_event_to_agui(args_event)
        args_encoded = encoder.encode(args_agui)
        assert args_encoded.startswith("data: ")

        # End event
        end_event = {"type": "TOOL_CALL_END", "tool_call_id": "tc-1"}
        end_agui = map_agent_event_to_agui(end_event)
        end_encoded = encoder.encode(end_agui)
        assert end_encoded.startswith("data: ")

    def test_encoder_get_content_type(self):
        """测试编码器 content type"""
        encoder = EventEncoder()
        content_type = encoder.get_content_type()
        assert content_type is not None
        assert "text" in content_type.lower() or "event-stream" in content_type.lower()


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])