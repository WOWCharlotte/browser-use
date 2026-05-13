"""
AG-UI 协议集成单元测试

测试内容:
1. RunAgentInput Pydantic 模型验证
2. AG-UI 事件序列化
3. /agui 端点功能测试
4. AgentService 事件映射测试
"""
import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api.agui import (
    AGUI_EVENT_TYPES,
    Message,
    MessageContent,
    RunAgentInput,
    RunAgentInput,
    event_to_sse,
    serialize_event,
)
from app.services.agent_service import (
    EVENT_INTERRUPT,
    EVENT_RESUME,
    EVENT_RUN_ERROR,
    EVENT_RUN_FINISHED,
    EVENT_RUN_STARTED,
    EVENT_STATE_SNAPSHOT,
    EVENT_STEP_FINISHED,
    EVENT_STEP_STARTED,
    EVENT_TEXT_MESSAGE_CONTENT,
    EVENT_TEXT_MESSAGE_END,
    EVENT_TEXT_MESSAGE_START,
    AgentService,
)


# ============================================================================
# 测试 RunAgentInput 模型
# ============================================================================

class TestRunAgentInput:
    """测试 RunAgentInput 模型"""

    def test_valid_input_with_string_content(self):
        """测试有效输入 - 字符串内容"""
        input_data = RunAgentInput(
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            messages=[
                Message(
                    role="user",
                    content="Hello, agent!",
                )
            ],
        )
        assert input_data.thread_id is not None
        assert len(input_data.messages) == 1
        assert input_data.messages[0].content == "Hello, agent!"

    def test_valid_input_with_list_content(self):
        """测试有效输入 - 列表内容"""
        input_data = RunAgentInput(
            messages=[
                Message(
                    role="user",
                    content=[
                        MessageContent(type="text", text="Hello"),
                        MessageContent(type="text", text="World"),
                    ],
                )
            ],
        )
        assert len(input_data.messages) == 1
        assert isinstance(input_data.messages[0].content, list)
        assert len(input_data.messages[0].content) == 2

    def test_empty_messages(self):
        """测试空消息列表"""
        input_data = RunAgentInput(messages=[])
        assert input_data.messages == []

    def test_default_values(self):
        """测试默认值"""
        input_data = RunAgentInput()
        assert input_data.thread_id is None
        assert input_data.run_id is not None  # 自动生成
        assert input_data.messages == []
        assert input_data.tools == []
        assert input_data.context == []
        assert input_data.state == {}
        assert input_data.forwarded_props == {}

    def test_extra_fields_allowed(self):
        """测试额外字段允许"""
        input_data = RunAgentInput(
            extra_field="should be allowed",
            another_field={"nested": True},
        )
        assert input_data.extra_field == "should be allowed"


# ============================================================================
# 测试事件序列化
# ============================================================================

class TestEventSerialization:
    """测试事件序列化函数"""

    def test_event_to_sse_format(self):
        """测试 SSE 格式生成"""
        event = {"type": "RUN_STARTED", "run_id": "test-123"}
        result = event_to_sse(event)
        assert result.startswith("data: ")
        assert result.endswith("\n\n")
        assert "RUN_STARTED" in result
        assert "test-123" in result

    def test_event_to_sse_with_chinese_characters(self):
        """测试中文内容序列化"""
        event = {"type": "TEXT_MESSAGE_CONTENT", "content": "你好，世界！"}
        result = event_to_sse(event)
        parsed = json.loads(result.replace("data: ", "").strip())
        assert parsed["content"] == "你好，世界！"

    def test_serialize_event_with_dict(self):
        """测试序列化字典事件"""
        event = {"type": "RUN_FINISHED", "outcome": "success"}
        result = serialize_event(event)
        assert "data: " in result
        assert "RUN_FINISHED" in result

    def test_serialize_event_with_base_event(self):
        """测试序列化 BaseEvent 子类"""
        from app.api.agui import RunStartedEvent

        event = RunStartedEvent()
        result = serialize_event(event)
        assert "data: " in result
        assert "RUN_STARTED" in result

    def test_multiple_events_serialization(self):
        """测试多个事件序列化"""
        events = [
            {"type": "RUN_STARTED", "run_id": "test-1"},
            {"type": "TEXT_MESSAGE_START", "message_id": "msg-1", "role": "assistant"},
            {"type": "TEXT_MESSAGE_CONTENT", "content": "Hello"},
            {"type": "RUN_FINISHED", "outcome": "success"},
        ]
        results = [event_to_sse(e) for e in events]
        assert len(results) == 4
        for r in results:
            assert r.startswith("data: ")
            assert r.endswith("\n\n")


# ============================================================================
# 测试事件类型常量
# ============================================================================

class TestEventTypes:
    """测试事件类型常量定义"""

    def test_all_event_types_defined(self):
        """测试所有事件类型都已定义"""
        expected_events = [
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
        for event_type in expected_events:
            assert hasattr(__import__("app.services.agent_service", fromlist=["EVENT_RUN_STARTED"]), f"EVENT_{event_type}")

    def test_event_type_constants_match_literal(self):
        """测试事件类型常量与 Literal 类型匹配"""
        # AG-UI 事件类型应该与 Literal 类型定义一致
        from app.api.agui import AGUI_EVENT_TYPES

        # 这个测试验证两种定义的一致性
        assert "RUN_STARTED" in AGUI_EVENT_TYPES.__args__
        assert "RUN_FINISHED" in AGUI_EVENT_TYPES.__args__


# ============================================================================
# 测试 AgentService 事件映射
# ============================================================================

class TestAgentServiceEvents:
    """测试 AgentService 事件映射逻辑"""

    def test_service_initialization(self):
        """测试服务初始化"""
        service = AgentService()
        assert service._agents == {}
        assert service._paused == {}
        assert service._resume_events == {}

    def test_get_status_stopped(self):
        """测试获取停止状态"""
        service = AgentService()
        status = service.get_status("non-existent-session")
        assert status == "stopped"

    @pytest.mark.asyncio
    async def test_pause_resume_agent(self):
        """测试暂停和恢复 agent"""
        service = AgentService()

        # 创建 mock agent
        mock_agent = MagicMock()
        mock_agent.pause = MagicMock()
        mock_agent.resume = MagicMock()
        mock_agent.state = MagicMock()
        mock_agent.state.paused = False
        mock_agent.state.stopped = False

        service._agents["test-session"] = mock_agent
        service._paused["test-session"] = False

        # 暂停
        service.pause_agent("test-session")
        assert service._paused["test-session"] is True
        mock_agent.pause.assert_called_once()

        # 恢复
        service.resume_agent("test-session")
        assert service._paused["test-session"] is False
        mock_agent.resume.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_agent(self):
        """测试停止 agent"""
        service = AgentService()

        mock_agent = MagicMock()
        mock_agent.stop = MagicMock()
        mock_agent.state = MagicMock()
        mock_agent.state.stopped = False

        service._agents["test-session"] = mock_agent
        service._resume_events["test-session"] = asyncio.Event()

        service.stop_agent("test-session")

        mock_agent.stop.assert_called_once()
        assert service._paused["test-session"] is False


# ============================================================================
# 测试事件映射关系
# ============================================================================

class TestEventMapping:
    """测试事件映射关系"""

    def test_step_start_maps_to_step_started(self):
        """验证 step_start 映射到 STEP_STARTED"""
        # 根据 agent_service.py 中的实现
        # on_step_start 回调发送 EVENT_STEP_STARTED
        assert EVENT_STEP_STARTED == "STEP_STARTED"

    def test_step_end_maps_to_step_finished(self):
        """验证 step_end 映射到 STEP_FINISHED"""
        # on_step_end 回调发送 EVENT_STEP_FINISHED
        assert EVENT_STEP_FINISHED == "STEP_FINISHED"

    def test_message_content_maps_to_text_message(self):
        """验证消息内容映射到 TEXT_MESSAGE_*"""
        assert EVENT_TEXT_MESSAGE_START == "TEXT_MESSAGE_START"
        assert EVENT_TEXT_MESSAGE_CONTENT == "TEXT_MESSAGE_CONTENT"
        assert EVENT_TEXT_MESSAGE_END == "TEXT_MESSAGE_END"

    def test_browser_state_maps_to_state_snapshot(self):
        """验证 browser_state 映射到 STATE_SNAPSHOT"""
        # on_step_end 中发送 browser_state 作为 STATE_SNAPSHOT
        assert EVENT_STATE_SNAPSHOT == "STATE_SNAPSHOT"

    def test_interrupt_resume_events(self):
        """验证 HITL 中断事件"""
        assert EVENT_INTERRUPT == "INTERRUPT"
        assert EVENT_RESUME == "RESUME"

    def test_lifecycle_events(self):
        """验证生命周期事件"""
        assert EVENT_RUN_STARTED == "RUN_STARTED"
        assert EVENT_RUN_FINISHED == "RUN_FINISHED"
        assert EVENT_RUN_ERROR == "RUN_ERROR"


# ============================================================================
# 测试端点路由注册
# ============================================================================

class TestAGUIEndpoint:
    """测试 AGUI 端点"""

    def test_endpoint_route_registered(self):
        """测试端点已注册"""
        from app.api.agui import router

        routes = [route.path for route in router.routes]
        assert "/agui" in routes

    def test_endpoint_accepts_post(self):
        """测试端点接受 POST 请求"""
        from app.api.agui import router

        post_routes = [
            route.path for route in router.routes
            if hasattr(route, "methods") and "POST" in route.methods
        ]
        assert "/agui" in post_routes


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])