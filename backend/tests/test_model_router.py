"""Tests for task-aware model routing and failover."""

import logging
from unittest.mock import AsyncMock, patch

import pytest
from app.services.model_router import (
	ModelProviderConfig,
	ModelRouteConfig,
	ModelTask,
	RoutedChatModel,
	load_model_route_config,
	warm_up_model_router,
)
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError
from browser_use.llm.views import ChatInvokeCompletion
from pydantic import BaseModel


class DummyOutput(BaseModel):
	value: str


class FakeChatModel:
	def __init__(self, name: str, result: str | None = None, error: Exception | None = None):
		self.model = name
		self.name = name
		self.model_name = name
		self.provider = "fake"
		self._verified_api_keys = True
		self.ainvoke = AsyncMock(
			side_effect=error,
			return_value=ChatInvokeCompletion(completion=result or name, usage=None),
		)


def make_route_config() -> ModelRouteConfig:
	return ModelRouteConfig(
		providers={
			"primary": ModelProviderConfig(provider="openai", model="primary-model"),
			"fallback": ModelProviderConfig(provider="openai", model="fallback-model"),
		},
		routes={ModelTask.INGESTION: ["primary", "fallback"]},
	)


def test_load_model_route_config_parses_task_routes_from_json(monkeypatch):
	monkeypatch.setenv(
		"MODEL_ROUTES_JSON",
		"""
		{
			"providers": {
				"text": {"provider": "openai", "model": "qwen-plus"},
				"vision": {"provider": "browser_use", "model": "bu-2-0"}
			},
			"routes": {
				"ingestion": ["text", "vision"],
				"execution": ["vision"]
			}
		}
		""",
	)

	config = load_model_route_config()

	assert config.routes[ModelTask.INGESTION] == ["text", "vision"]
	assert config.routes[ModelTask.EXECUTION] == ["vision"]
	assert config.providers["text"].model == "qwen-plus"


def test_load_model_route_config_logs_sanitized_runtime_config(monkeypatch, caplog):
	monkeypatch.setenv(
		"MODEL_ROUTES_JSON",
		"""
		{
			"providers": {
				"text": {"provider": "openai", "model": "qwen-plus", "api_key": "secret-key"},
				"vision": {"provider": "browser_use", "model": "bu-2-0", "api_key_env": "BROWSER_USE_API_KEY"}
			},
			"routes": {
				"ingestion": ["text"],
				"execution": ["vision"]
			}
		}
		""",
	)

	with caplog.at_level(logging.INFO, logger="app.services.model_router"):
		load_model_route_config()

	log_text = "\n".join(record.getMessage() for record in caplog.records)
	assert "Model router config loaded" in log_text
	assert "text=openai/qwen-plus" in log_text
	assert "vision=browser_use/bu-2-0" in log_text
	assert "ingestion: text" in log_text
	assert "execution: vision" in log_text
	assert "secret-key" not in log_text


def test_warm_up_model_router_imports_configured_models_and_logs_info(monkeypatch, caplog):
	monkeypatch.setenv(
		"MODEL_ROUTES_JSON",
		"""
		{
			"providers": {
				"text": {"provider": "openai", "model": "qwen-plus", "api_key": "secret-key"},
				"vision": {"provider": "google", "model": "gemini-2.0-flash"}
			},
			"routes": {
				"ingestion": ["text"],
				"execution": ["vision"]
			}
		}
		""",
	)
	imported: list[str] = []

	def fake_factory(provider: ModelProviderConfig):
		imported.append(f"{provider.provider}/{provider.model}")
		return FakeChatModel(provider.model)

	with caplog.at_level(logging.INFO, logger="app.services.model_router"):
		warm_up_model_router(model_factory=fake_factory)

	assert imported == ["openai/qwen-plus", "google/gemini-2.0-flash"]
	log_text = "\n".join(record.getMessage() for record in caplog.records)
	assert "Warming up model router" in log_text
	assert "Model provider imported: text=openai/qwen-plus" in log_text
	assert "Model provider imported: vision=google/gemini-2.0-flash" in log_text
	assert "Model router warmup completed" in log_text
	assert "secret-key" not in log_text


def test_load_model_route_config_uses_legacy_llm_env_when_json_missing(monkeypatch):
	monkeypatch.delenv("MODEL_ROUTES_JSON", raising=False)
	monkeypatch.setenv("LLM_MODEL", "qwen-vl-max")
	monkeypatch.setenv("LLM_API_KEY", "legacy-key")
	monkeypatch.setenv("LLM_BASE_URL", "https://dashscope.example/v1")
	monkeypatch.setenv("EVAL_LLM_MODEL", "qwen-plus")

	config = load_model_route_config()

	assert config.providers["legacy_default"].model == "qwen-vl-max"
	assert config.providers["legacy_default"].api_key == "legacy-key"
	assert config.providers["legacy_default"].base_url == "https://dashscope.example/v1"
	assert config.routes[ModelTask.EXECUTION] == ["legacy_default"]
	assert config.routes[ModelTask.EVALUATION] == ["legacy_eval"]
	assert config.providers["legacy_eval"].model == "qwen-plus"


@pytest.mark.asyncio
async def test_routed_chat_model_returns_first_success_without_calling_fallback():
	primary = FakeChatModel("primary", result="ok")
	fallback = FakeChatModel("fallback", result="fallback")
	router = RoutedChatModel(
		task=ModelTask.INGESTION,
		config=make_route_config(),
		model_factory=lambda provider: {"primary-model": primary, "fallback-model": fallback}[provider.model],
	)

	response = await router.ainvoke([])

	assert response.completion == "ok"
	primary.ainvoke.assert_awaited_once()
	fallback.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_routed_chat_model_falls_back_after_provider_error():
	primary = FakeChatModel("primary", error=ModelRateLimitError("rate limited", model="primary"))
	fallback = FakeChatModel("fallback", result="ok")
	router = RoutedChatModel(
		task=ModelTask.INGESTION,
		config=make_route_config(),
		model_factory=lambda provider: {"primary-model": primary, "fallback-model": fallback}[provider.model],
	)

	response = await router.ainvoke([])

	assert response.completion == "ok"
	primary.ainvoke.assert_awaited_once()
	fallback.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_routed_chat_model_logs_candidate_failures_at_info(caplog):
	primary = FakeChatModel("primary", error=ModelRateLimitError("rate limited", model="primary"))
	fallback = FakeChatModel("fallback", result="ok")
	router = RoutedChatModel(
		task=ModelTask.INGESTION,
		config=make_route_config(),
		model_factory=lambda provider: {"primary-model": primary, "fallback-model": fallback}[provider.model],
	)

	with caplog.at_level(logging.INFO, logger="app.services.model_router"):
		await router.ainvoke([])

	failure_records = [
		record
		for record in caplog.records
		if "candidate failed" in record.getMessage()
	]
	assert len(failure_records) == 1
	assert failure_records[0].levelno == logging.INFO


@pytest.mark.asyncio
async def test_routed_chat_model_raises_aggregate_error_after_all_candidates_fail():
	primary = FakeChatModel("primary", error=ModelProviderError("bad gateway", model="primary"))
	fallback = FakeChatModel("fallback", error=TimeoutError("timeout"))
	router = RoutedChatModel(
		task=ModelTask.INGESTION,
		config=make_route_config(),
		model_factory=lambda provider: {"primary-model": primary, "fallback-model": fallback}[provider.model],
	)

	with pytest.raises(ModelProviderError) as exc_info:
		await router.ainvoke([])

	message = exc_info.value.message
	assert "ingestion" in message
	assert "primary-model" in message
	assert "fallback-model" in message


@pytest.mark.asyncio
async def test_routed_chat_model_passes_output_format_to_candidate():
	primary = FakeChatModel("primary", result="ok")
	router = RoutedChatModel(
		task=ModelTask.INGESTION,
		config=make_route_config(),
		model_factory=lambda provider: primary,
	)

	await router.ainvoke([], output_format=DummyOutput)

	primary.ainvoke.assert_awaited_once_with([], output_format=DummyOutput)


def test_ingestion_service_uses_ingestion_route():
	from app.services.ingestion_service import IngestionService

	sentinel = object()
	with patch("app.services.ingestion_service.get_routed_llm", return_value=sentinel, create=True) as get_llm:
		service = IngestionService()

		assert service._get_llm() is sentinel

	get_llm.assert_called_once_with(ModelTask.INGESTION, temperature=0.1)


def test_execution_service_uses_execution_route():
	from app.services.test_execution_service import TestExecutionService

	sentinel = object()
	with patch("app.services.test_execution_service.get_routed_llm", return_value=sentinel, create=True) as get_llm:
		service = TestExecutionService()

		assert service._get_llm() is sentinel

	get_llm.assert_called_once_with(ModelTask.EXECUTION)


def test_evaluation_service_uses_evaluation_route():
	from app.config import Config
	from app.services.test_evaluation_service import TestEvaluationService

	sentinel = object()
	with patch("app.services.test_evaluation_service.get_routed_llm", return_value=sentinel, create=True) as get_llm:
		service = TestEvaluationService()

		assert service._get_llm() is sentinel

	get_llm.assert_called_once_with(ModelTask.EVALUATION, timeout=Config.EVAL_LLM_TIMEOUT)


def test_replay_service_uses_replay_route():
	from app.services.test_replay_service import TestReplayService

	sentinel = object()
	with patch("app.services.test_replay_service.get_routed_llm", return_value=sentinel, create=True) as get_llm:
		service = TestReplayService()

		assert service._get_llm() is sentinel

	get_llm.assert_called_once_with(ModelTask.REPLAY)


@pytest.mark.asyncio
async def test_evaluation_service_preserves_plain_json_fallback_with_routed_llm():
	from app.services.test_evaluation_service import TestEvaluationService

	llm = FakeChatModel("evaluation")
	llm.ainvoke = AsyncMock(
		side_effect=[
			ModelProviderError("structured output failed", model="evaluation"),
			ChatInvokeCompletion(
				completion=(
					'{"overall_status":"passed","checkpoints":[],'
					'"execution_errors":[],"summary":"ok"}'
				),
				usage=None,
			),
		]
	)
	service = TestEvaluationService()
	service._get_llm = lambda: llm  # type: ignore[method-assign]

	result = await service._call_llm([])

	assert result.overall_status == "passed"
	assert result.summary == "ok"
	assert llm.ainvoke.await_args_list[0].kwargs["output_format"] is not None
	assert llm.ainvoke.await_args_list[1].kwargs == {}
