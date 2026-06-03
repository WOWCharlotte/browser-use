"""
Test Case Ingestion Service.

Provides LLM-powered parsing of test cases from unstructured documents.
One LLM call extracts all cases, steps, variables, and merges similar cases.
Output: TestPlanParsedSchema (list[TestCaseParsedSchema]).
"""

import logging
import re

from app.models.ingestion import TestCaseParsedSchema, TestPlanParsedSchema
from app.services.document_flattening import document_flattener
from app.services.model_router import ModelTask, get_routed_llm
from browser_use.llm.base import BaseChatModel
from browser_use.llm.messages import SystemMessage, UserMessage

logger = logging.getLogger(__name__)


TEST_PLAN_EXTRACTION_PROMPT = """你是一个专业的自动化测试用例分析专家。你的任务是从用户提供的测试用例文档中，一次性完成以下三项工作：
1. **结构化提取**：将每条测试用例拆解为有序步骤，每步包含操作描述和预期结果
2. **变量提取**：识别可变参数并统一转化为花括号占位符（如 `{username}`）
3. **用例合并**：将步骤完全相同、仅变量值不同的用例合并为一条用例 + 多组变量集

## 输出格式

你必须输出一个完全符合以下 JSON Schema 的对象，不包含任何其他文字：

```json
{
  "test_cases": [
    {
      "case_name": "string",         // 能唯一标识该用例的核心业务名称，简洁精准
      "description": "string|null",  // 用例的补充说明，可为 null
      "module": "string|null",       // 所属功能模块（如"登录"、"购物车"），可为 null
      "function_point": "string|null", // 具体功能点（如"手机号登录"），可为 null
      "start_url": "string",         // 测试起始 URL，文档未提供时根据上下文合理推断
      "steps": [
        {
          "step_number": 1,          // 从 1 开始的自增序号
          "action_description": "string", // 浏览器操作指令，可变参数用 {变量名} 替换
          "expected_result": "string|null", // 该步骤完成后的预期状态，无则为 null
          "step_variables": ["string"],     // 本步骤用到的变量名列表（不含花括号）
          "is_visual_checkpoint": false     // 需要截图对比时设为 true（如验证页面布局、图片）
        }
      ],
      "global_variables": ["string"], // 所有步骤变量的去重汇总，不含花括号
      "variable_sets": [              // 每组为一次执行的变量值映射，无变量时为 [{}]
        {"变量名": "值", ...}
      ]
    }
  ]
}
```

## 核心规则

### 变量提取
- **识别范围**：账号、密码、手机号、商品ID、金额、日期、地址等测试数据
- **命名规范**：英文小写下划线，语义明确，如 `{user_phone}`、`{sku_id}`、`{order_amount}`
- **一致性**：同一含义的变量在所有步骤中必须使用完全相同的占位符名称
- **格式要求**：占位符必须完整闭合 `{variable_name}`，禁止 `{variable_name` 或 `{}`

### 用例合并
- **合并条件**：两条用例的步骤结构完全相同（操作描述模板一致），仅变量值不同
- **合并方式**：保留一条用例，将各组变量值分别放入 `variable_sets` 数组
- **不合并条件**：步骤数量不同、操作顺序不同、业务场景不同

### 视觉检查点
- 当步骤的预期结果涉及页面视觉状态（布局、图片、颜色、样式）时，设 `is_visual_checkpoint: true`
- 纯文本断言（如"显示成功提示"、"跳转到首页"）设为 `false`

---

## 示例

### 输入文档

```
## 用例1：手机号登录-正常流程
1. 打开登录页
2. 输入手机号 13800138001，点击获取验证码
3. 输入验证码 123456
4. 点击登录按钮
   预期：跳转到首页，顶部显示用户昵称"测试用户A"

## 用例2：手机号登录-另一账号
1. 打开登录页
2. 输入手机号 13900139002，点击获取验证码
3. 输入验证码 654321
4. 点击登录按钮
   预期：跳转到首页，顶部显示用户昵称"测试用户B"

## 用例3：商品加入购物车
1. 搜索商品"蓝牙耳机"
2. 点击第一个搜索结果
3. 点击"加入购物车"
   预期：购物车图标数量+1，弹出"已加入购物车"提示
```

### 输出

```json
{
  "test_cases": [
    {
      "case_name": "手机号登录",
      "description": "使用手机号+验证码完成登录",
      "module": "登录",
      "function_point": "手机号验证码登录",
      "start_url": "https://example.com/login",
      "steps": [
        {
          "step_number": 1,
          "action_description": "打开登录页",
          "expected_result": null,
          "step_variables": [],
          "is_visual_checkpoint": false
        },
        {
          "step_number": 2,
          "action_description": "在手机号输入框输入 {user_phone}，点击获取验证码按钮",
          "expected_result": null,
          "step_variables": ["user_phone"],
          "is_visual_checkpoint": false
        },
        {
          "step_number": 3,
          "action_description": "在验证码输入框输入 {sms_code}",
          "expected_result": null,
          "step_variables": ["sms_code"],
          "is_visual_checkpoint": false
        },
        {
          "step_number": 4,
          "action_description": "点击登录按钮",
          "expected_result": "跳转到首页，顶部显示用户昵称 {user_nickname}",
          "step_variables": ["user_nickname"],
          "is_visual_checkpoint": false
        }
      ],
      "global_variables": ["user_phone", "sms_code", "user_nickname"],
      "variable_sets": [
        {"user_phone": "13800138001", "sms_code": "123456", "user_nickname": "测试用户A"},
        {"user_phone": "13900139002", "sms_code": "654321", "user_nickname": "测试用户B"}
      ]
    },
    {
      "case_name": "商品加入购物车",
      "description": null,
      "module": "购物车",
      "function_point": "加入购物车",
      "start_url": "https://example.com",
      "steps": [
        {
          "step_number": 1,
          "action_description": "在搜索框输入 {keyword}，点击搜索",
          "expected_result": null,
          "step_variables": ["keyword"],
          "is_visual_checkpoint": false
        },
        {
          "step_number": 2,
          "action_description": "点击第一个搜索结果",
          "expected_result": null,
          "step_variables": [],
          "is_visual_checkpoint": false
        },
        {
          "step_number": 3,
          "action_description": "点击"加入购物车"按钮",
          "expected_result": "购物车图标数量+1，弹出"已加入购物车"提示",
          "step_variables": [],
          "is_visual_checkpoint": false
        }
      ],
      "global_variables": ["keyword"],
      "variable_sets": [
        {"keyword": "蓝牙耳机"}
      ]
    }
  ]
}
```

---

现在请解析用户提供的文档，严格按照上述格式输出。"""


class IngestionService:
	"""Service for ingesting and parsing test cases from documents."""

	MAX_RETRIES = 2
	MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

	def __init__(self) -> None:
		self._llm: BaseChatModel | None = None

	def _get_llm(self) -> BaseChatModel:
		"""Get or create LLM client."""
		if self._llm is None:
			logger.debug("Initializing LLM client for ingestion service")
			self._llm = get_routed_llm(ModelTask.INGESTION, temperature=0.1)
		return self._llm

	def _validate_placeholders(self, text: str) -> list[str]:
		"""Check for unclosed or empty placeholders. Returns list of error messages."""
		errors = []
		if re.search(r"\{[^}]*$", text):
			errors.append("Unclosed placeholder detected")
		if re.search(r"\{\}", text):
			errors.append("Empty placeholder: {}")
		return errors

	def _validate_plan(self, plan: TestPlanParsedSchema) -> list[str]:
		"""Validate all cases in a parsed plan. Returns list of error messages."""
		errors = []
		for case in plan.test_cases:
			for step in case.steps:
				for err in self._validate_placeholders(step.action_description):
					errors.append(f"[{case.case_name}] Step {step.step_number} action: {err}")
				if step.expected_result:
					for err in self._validate_placeholders(step.expected_result):
						errors.append(f"[{case.case_name}] Step {step.step_number} expected_result: {err}")
		return errors

	def _extract_vars(self, text: str | None) -> list[str]:
		"""Extract variable names from {placeholder} patterns in text."""
		if not text:
			return []
		return list(set(re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', text)))

	def _extract_variables_from_text(self, text: str | None) -> list[str]:
		"""Backward-compatible alias for variable extraction callers."""
		return self._extract_vars(text)

	def _reconcile_variables(self, plan: TestPlanParsedSchema) -> TestPlanParsedSchema:
		"""
		Reconcile global_variables and step_variables with actual placeholders found
		in action_description and expected_result. Source of truth is the text content.
		"""
		reconciled_cases: list[TestCaseParsedSchema] = []
		for case in plan.test_cases:
			all_vars: list[str] = []
			reconciled_steps = []
			for step in case.steps:
				extracted = (
					self._extract_vars(step.action_description)
					+ self._extract_vars(step.expected_result)
				)
				all_vars.extend(extracted)
				reconciled_steps.append(step.model_copy(update={
					"step_variables": sorted(set(extracted)),
				}))
			reconciled_cases.append(case.model_copy(update={
				"steps": reconciled_steps,
				"global_variables": sorted(set(all_vars)),
			}))
		return plan.model_copy(update={"test_cases": reconciled_cases})

	def _filter_empty_variable_sets(self, plan: TestPlanParsedSchema) -> TestPlanParsedSchema:
		"""Filter out empty variable sets (where all values are empty strings)."""
		reconciled_cases: list[TestCaseParsedSchema] = []
		for case in plan.test_cases:
			filtered_sets = [
				vs for vs in case.variable_sets
				if any(v.strip() for v in vs.values())
			]
			reconciled_cases.append(case.model_copy(update={
				"variable_sets": filtered_sets,
			}))
		return plan.model_copy(update={"test_cases": reconciled_cases})

	async def parse_markdown(
		self,
		markdown_content: str,
		skip_validation: bool = False,
	) -> TestPlanParsedSchema:
		"""
		Parse markdown content into a structured test plan using LLM.

		One LLM call handles extraction, variable substitution, and case merging.

		Args:
			markdown_content: Flattened markdown text from document
			skip_validation: Skip placeholder validation (for testing)

		Returns:
			TestPlanParsedSchema with list of TestCaseParsedSchema

		Raises:
			ValueError: If parsing fails after retries
		"""
		llm = self._get_llm()
		preview = markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content
		logger.info(f"Parsing markdown ({len(markdown_content)} chars): {preview}")

		messages = [
			SystemMessage(content=TEST_PLAN_EXTRACTION_PROMPT),
			UserMessage(content=markdown_content),
		]

		last_error: Exception | None = None
		for attempt in range(self.MAX_RETRIES + 1):
			try:
				logger.info(f"LLM attempt {attempt + 1}/{self.MAX_RETRIES + 1}")
				response = await llm.ainvoke(messages, output_format=TestPlanParsedSchema)
				plan = response.completion

				plan = self._filter_empty_variable_sets(plan)

				logger.info(f"LLM returned {len(plan.test_cases)} cases")

				if not skip_validation:
					errors = self._validate_plan(plan)
					if errors:
						logger.warning(f"Validation errors: {errors}")
						if attempt < self.MAX_RETRIES:
							messages = [
								SystemMessage(content=TEST_PLAN_EXTRACTION_PROMPT),
								UserMessage(content=(
									f"上次输出存在以下错误，请修正后重新解析：\n"
									f"{chr(10).join(errors)}\n\n"
									f"原始文档：\n{markdown_content}"
								)),
							]
							continue
						raise ValueError(f"Validation failed after {self.MAX_RETRIES} retries: {errors}")

				plan = self._reconcile_variables(plan)
				logger.info(f"Parsed plan: {[c.case_name for c in plan.test_cases]}")
				return plan

			except Exception as e:
				last_error = e
				logger.warning(f"Attempt {attempt + 1} failed: {e}")
				if attempt < self.MAX_RETRIES:
					continue

		raise ValueError(f"Failed to parse after {self.MAX_RETRIES + 1} attempts: {last_error}")

	async def ingest_file(
		self,
		file_name: str,
		file_content: bytes,
	) -> TestPlanParsedSchema:
		"""
		Ingest a document file and parse into a structured test plan.

		Args:
			file_name: Original file name with extension
			file_content: Raw file bytes

		Returns:
			TestPlanParsedSchema

		Raises:
			ValueError: If file type not supported, too large, or parsing fails
		"""
		logger.info(f"Ingesting file: {file_name}, size={len(file_content)} bytes")

		if len(file_content) > self.MAX_FILE_SIZE:
			raise ValueError(f"File size exceeds maximum of {self.MAX_FILE_SIZE // (1024 * 1024)}MB")

		if not document_flattener.is_supported(file_name):
			raise ValueError(
				f"Unsupported file type: {file_name}. Supported: .xlsx, .xls, .md, .markdown"
			)

		markdown = document_flattener.flatten(file_name, file_content)
		logger.debug(f"Document flattened, markdown length={len(markdown)}")
		return await self.parse_markdown(markdown)

	async def ingest_markdown(self, markdown_content: str) -> TestPlanParsedSchema:
		"""
		Ingest markdown content directly and parse into a structured test plan.

		Args:
			markdown_content: Raw markdown text

		Returns:
			TestPlanParsedSchema
		"""
		logger.info(f"Ingesting markdown, length={len(markdown_content)}")
		return await self.parse_markdown(markdown_content)


# Global singleton instance
ingestion_service = IngestionService()
