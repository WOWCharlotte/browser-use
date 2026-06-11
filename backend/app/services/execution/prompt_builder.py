import json
from typing import Any


class TestPromptBuilder:
	"""Build Browser Use agent prompts for executable test cases."""

	def build(self, case: dict[str, Any]) -> str:
		"""Build the Agent task prompt with variable substitution."""
		steps_raw = case.get("steps_json", "[]")
		if isinstance(steps_raw, str):
			steps = json.loads(steps_raw)
		else:
			steps = steps_raw

		variables = case.get("variables", {})
		start_url = case.get("start_url", "")

		for var_name, var_value in variables.items():
			start_url = start_url.replace(f"{{{var_name}}}", var_value)

		parts = [f"Execute this test case: {case['case_name']}"]
		parts.append(f"\nStart URL: {start_url}")

		if variables:
			parts.append("\nTest data:")
			for key, value in variables.items():
				parts.append(f"  - {key} = {value}")

		parts.append("\nSteps:")
		for step in steps:
			step_num = step.get("step_number", 0)
			action = step.get("action_description", "")
			expected = step.get("expected_result", "")
			for var_name, var_value in variables.items():
				action = action.replace(f"{{{var_name}}}", var_value)
				if expected:
					expected = expected.replace(f"{{{var_name}}}", var_value)
			line = f"  {step_num}. {action}"
			if expected:
				line += f" -> expected: {expected}"
			parts.append(line)

		parts.append("\nCompletion criteria:")
		parts.append("  - Call done immediately after all steps are complete.")
		parts.append("  - If the expected result is visible, call done even if the exact interaction differed.")
		parts.append("  - Do not retry the same failing action more than 3 times before calling done.")

		return "\n".join(parts)
