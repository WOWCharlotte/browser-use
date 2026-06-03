"""Task-aware LLM routing with per-call failover."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from enum import StrEnum
from typing import Any, Callable, TypeVar, overload

from browser_use.llm.base import BaseChatModel
from browser_use.llm.exceptions import ModelProviderError
from browser_use.llm.messages import BaseMessage
from browser_use.llm.views import ChatInvokeCompletion
from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
ModelFactory = Callable[["ModelProviderConfig"], BaseChatModel]


class ModelTask(StrEnum):
	"""Backend task categories that can use different model routes."""

	INGESTION = "ingestion"
	EXECUTION = "execution"
	EVALUATION = "evaluation"
	REPLAY = "replay"


class ModelProviderConfig(BaseModel):
	"""Configuration for one concrete model provider candidate."""

	model_config = ConfigDict(extra="forbid")

	provider: str
	model: str
	api_key: str | None = None
	api_key_env: str | None = None
	base_url: str | None = None
	timeout: float | None = None
	temperature: float | None = None
	max_retries: int | None = None

	def resolved_api_key(self) -> str | None:
		"""Return the explicit API key or the value from api_key_env."""
		if self.api_key is not None:
			return self.api_key
		if self.api_key_env:
			return os.getenv(self.api_key_env)
		return None


class ModelRouteConfig(BaseModel):
	"""Provider registry plus task-to-candidate routes."""

	model_config = ConfigDict(extra="forbid")

	providers: dict[str, ModelProviderConfig]
	routes: dict[ModelTask, list[str]]

	@model_validator(mode="after")
	def validate_route_provider_refs(self) -> "ModelRouteConfig":
		missing: dict[str, list[str]] = {}
		for task, provider_ids in self.routes.items():
			unknown = [provider_id for provider_id in provider_ids if provider_id not in self.providers]
			if unknown:
				missing[task.value] = unknown
		if missing:
			raise ValueError(f"Model routes reference unknown providers: {missing}")
		return self


def _format_runtime_config(config: ModelRouteConfig) -> str:
	providers = ", ".join(
		f"{provider_id}={provider.provider}/{provider.model}"
		for provider_id, provider in config.providers.items()
	)
	routes = ", ".join(
		f"{task.value}: {' -> '.join(provider_ids)}"
		for task, provider_ids in config.routes.items()
	)
	return f"providers=[{providers}], routes=[{routes}]"


def _log_runtime_config(config: ModelRouteConfig, source: str) -> None:
	logger.info(
		"Model router config loaded from %s: %s",
		source,
		_format_runtime_config(config),
	)


def load_model_route_config() -> ModelRouteConfig:
	"""Load model routes from MODEL_ROUTES_JSON or legacy LLM_* variables."""
	routes_json = os.getenv("MODEL_ROUTES_JSON")
	if routes_json:
		config = ModelRouteConfig.model_validate_json(routes_json)
		_log_runtime_config(config, "MODEL_ROUTES_JSON")
		return config

	default_model = os.getenv("LLM_MODEL", "qwen-vl-max")
	default_api_key = os.getenv("LLM_API_KEY", "")
	default_base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
	eval_model = os.getenv("EVAL_LLM_MODEL", default_model)
	eval_timeout = float(os.getenv("EVAL_LLM_TIMEOUT", "60"))

	providers = {
		"legacy_default": ModelProviderConfig(
			provider="openai",
			model=default_model,
			api_key=default_api_key,
			base_url=default_base_url,
		),
		"legacy_eval": ModelProviderConfig(
			provider="openai",
			model=eval_model,
			api_key=default_api_key,
			base_url=default_base_url,
			timeout=eval_timeout,
		),
	}
	config = ModelRouteConfig(
		providers=providers,
		routes={
			ModelTask.INGESTION: ["legacy_default"],
			ModelTask.EXECUTION: ["legacy_default"],
			ModelTask.EVALUATION: ["legacy_eval"],
			ModelTask.REPLAY: ["legacy_default"],
		},
	)
	_log_runtime_config(config, "legacy LLM_* env")
	return config


def _model_kwargs(provider: ModelProviderConfig, **overrides: Any) -> dict[str, Any]:
	kwargs: dict[str, Any] = {
		"model": provider.model,
	}
	api_key = provider.resolved_api_key()
	if api_key:
		kwargs["api_key"] = api_key
	if provider.base_url:
		kwargs["base_url"] = provider.base_url
	if provider.timeout is not None:
		kwargs["timeout"] = provider.timeout
	if provider.temperature is not None:
		kwargs["temperature"] = provider.temperature
	if provider.max_retries is not None:
		kwargs["max_retries"] = provider.max_retries
	kwargs.update({key: value for key, value in overrides.items() if value is not None})
	return kwargs


def create_chat_model(provider: ModelProviderConfig, **overrides: Any) -> BaseChatModel:
	"""Create a browser-use chat model from provider config."""
	provider_name = provider.provider.lower().replace("-", "_")
	kwargs = _model_kwargs(provider, **overrides)

	if provider_name == "browser_use":
		from browser_use.llm.browser_use.chat import ChatBrowserUse

		return ChatBrowserUse(**kwargs)
	if provider_name == "openai":
		from browser_use.llm.openai.chat import ChatOpenAI

		return ChatOpenAI(**kwargs)
	if provider_name == "google":
		from browser_use.llm.google.chat import ChatGoogle

		return ChatGoogle(**kwargs)
	if provider_name == "anthropic":
		from browser_use.llm.anthropic.chat import ChatAnthropic

		return ChatAnthropic(**kwargs)

	raise ValueError(f"Unsupported model provider: {provider.provider}")


def warm_up_model_router(model_factory: ModelFactory = create_chat_model) -> None:
	"""Load routing config and import/create all configured model clients at startup."""
	config = load_model_route_config()
	logger.info("Warming up model router with %d configured providers", len(config.providers))
	imported_count = 0

	for provider_id, provider in config.providers.items():
		label = f"{provider_id}={provider.provider}/{provider.model}"
		try:
			model_factory(provider)
			imported_count += 1
			logger.info("Model provider imported: %s", label)
		except Exception:
			logger.exception("Model provider import failed: %s", label)
			raise

	logger.info("Model router warmup completed: imported %d providers", imported_count)


class RoutedChatModel(BaseChatModel):
	"""BaseChatModel wrapper that tries route candidates until one succeeds."""

	def __init__(
		self,
		task: ModelTask,
		config: ModelRouteConfig,
		model_factory: ModelFactory = create_chat_model,
		max_attempts_per_call: int | None = None,
		log_failures: bool | None = None,
		model_overrides: dict[str, Any] | None = None,
	) -> None:
		self.task = task
		self.config = config
		self.model_factory = model_factory
		self.model_overrides = model_overrides or {}
		self.max_attempts_per_call = max_attempts_per_call or int(os.getenv("MODEL_ROUTER_MAX_ATTEMPTS_PER_CALL", "3"))
		self.log_failures = log_failures if log_failures is not None else os.getenv("MODEL_ROUTER_LOG_FAILURES", "true").lower() == "true"
		self.model = f"routed:{task.value}"
		self._verified_api_keys = True

	@property
	def provider(self) -> str:
		return "model-router"

	@property
	def name(self) -> str:
		return self.model

	def _candidate_ids(self) -> list[str]:
		candidates = self.config.routes.get(self.task, [])
		if self.max_attempts_per_call > 0:
			return candidates[: self.max_attempts_per_call]
		return candidates

	def _create_candidate(self, provider: ModelProviderConfig) -> BaseChatModel:
		if self.model_factory is create_chat_model:
			return create_chat_model(provider, **self.model_overrides)
		return self.model_factory(provider)

	@overload
	async def ainvoke(
		self, messages: list[BaseMessage], output_format: None = None, **kwargs: Any
	) -> ChatInvokeCompletion[str]: ...

	@overload
	async def ainvoke(self, messages: list[BaseMessage], output_format: type[T], **kwargs: Any) -> ChatInvokeCompletion[T]: ...

	async def ainvoke(
		self, messages: list[BaseMessage], output_format: type[T] | None = None, **kwargs: Any
	) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
		failures: list[str] = []
		candidate_ids = self._candidate_ids()
		if not candidate_ids:
			raise ModelProviderError(
				message=f"No model candidates configured for task '{self.task.value}'",
				model=self.name,
			)

		for provider_id in candidate_ids:
			provider = self.config.providers[provider_id]
			label = f"{provider_id}({provider.provider}/{provider.model})"
			try:
				model = self._create_candidate(provider)
				response = await model.ainvoke(messages, output_format=output_format, **kwargs)
				logger.info("Model route task=%s selected %s", self.task.value, label)
				return response
			except asyncio.CancelledError:
				raise
			except Exception as exc:
				failures.append(f"{label}: {type(exc).__name__}: {exc}")
				if self.log_failures:
					logger.info("Model route task=%s candidate failed: %s", self.task.value, failures[-1])

		raise ModelProviderError(
			message=(
				f"All model candidates failed for task '{self.task.value}'. "
				f"Attempted: {json.dumps(failures, ensure_ascii=False)}"
			),
			model=self.name,
		)


def get_routed_llm(task: ModelTask, **model_overrides: Any) -> RoutedChatModel:
	"""Create a routed LLM for a backend task."""
	config = load_model_route_config()
	override_keys = sorted(key for key, value in model_overrides.items() if value is not None)
	logger.info(
		"Creating routed LLM for task=%s candidates=%s override_keys=%s",
		task.value,
		" -> ".join(config.routes.get(task, [])),
		override_keys,
	)
	return RoutedChatModel(
		task=task,
		config=config,
		model_overrides=model_overrides,
	)
