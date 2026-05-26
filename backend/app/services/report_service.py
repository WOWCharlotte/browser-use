"""
Report Service — Generates HTML, PDF, and Excel test reports.
"""

import base64
import json
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.config import Config
from app.db.database import get_db

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class ReportService:
	"""Generates test execution reports in multiple formats."""

	def __init__(self) -> None:
		self._jinja_env = Environment(
			loader=FileSystemLoader(str(TEMPLATES_DIR)),
			autoescape=True,
		)

	async def generate_html(self, run_id: str) -> Path:
		"""Generate HTML report. Returns path to the generated file."""
		report_dir = Config.REPORTS_DIR / run_id
		report_dir.mkdir(parents=True, exist_ok=True)
		report_path = report_dir / "report.html"

		# Use cached if exists
		if report_path.exists():
			return report_path

		data = await self._get_report_data(run_id)
		template = self._jinja_env.get_template("report.html")
		html = template.render(**data)

		report_path.write_text(html, encoding="utf-8")
		return report_path

	async def generate_pdf(self, run_id: str) -> Path:
		"""Generate PDF report via Playwright. Returns path to the generated file."""
		report_dir = Config.REPORTS_DIR / run_id
		report_dir.mkdir(parents=True, exist_ok=True)
		pdf_path = report_dir / "report.pdf"

		if pdf_path.exists():
			return pdf_path

		# Ensure HTML exists first
		html_path = await self.generate_html(run_id)

		# Use Playwright directly for PDF generation
		from playwright.async_api import async_playwright

		async with async_playwright() as p:
			browser = await p.chromium.launch(headless=True)
			page = await browser.new_page()
			await page.goto(f"file:///{html_path.resolve()}")
			await page.pdf(path=str(pdf_path), format="A4", print_background=True)
			await browser.close()

		return pdf_path

	async def generate_excel(self, run_id: str) -> Path:
		"""Generate Excel report with Summary + Details sheets."""
		from openpyxl import Workbook
		from openpyxl.styles import Alignment, Font, PatternFill

		report_dir = Config.REPORTS_DIR / run_id
		report_dir.mkdir(parents=True, exist_ok=True)
		excel_path = report_dir / "report.xlsx"

		if excel_path.exists():
			return excel_path

		data = await self._get_report_data(run_id)

		wb = Workbook()

		# ── Sheet 1: Summary ──
		ws_summary = wb.active
		ws_summary.title = "Summary"

		header_font = Font(bold=True, size=12)
		ws_summary.append(["测试报告摘要"])
		ws_summary["A1"].font = Font(bold=True, size=14)
		ws_summary.append([])
		ws_summary.append(["计划名称", data["plan_name"]])
		ws_summary.append(["运行 ID", data["run_id"]])
		ws_summary.append(["开始时间", data["started_at"]])
		ws_summary.append(["耗时", data["duration"]])
		ws_summary.append([])
		ws_summary.append(["指标", "数值"])
		ws_summary["A8"].font = header_font
		ws_summary["B8"].font = header_font
		ws_summary.append(["总计", data["total"]])
		ws_summary.append(["通过", data["passed"]])
		ws_summary.append(["失败", data["failed"]])
		ws_summary.append(["错误", data["error_count"]])
		ws_summary.append(["通过率", f"{data['pass_rate']}%"])

		ws_summary.column_dimensions["A"].width = 15
		ws_summary.column_dimensions["B"].width = 40

		# ── Sheet 2: Details ──
		ws_details = wb.create_sheet("Details")

		headers = ["用例名称", "状态", "耗时(s)", "评估总结", "错误信息", "覆盖原因"]
		ws_details.append(headers)
		for col in range(1, len(headers) + 1):
			ws_details.cell(row=1, column=col).font = header_font

		status_fills = {
			"passed": PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid"),
			"failed": PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid"),
			"error": PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid"),
		}

		for result in data["results"]:
			row = [
				result["case_name"],
				result["status"],
				f"{result['duration_seconds']:.1f}" if result.get("duration_seconds") else "",
				result.get("evaluation_summary", ""),
				result.get("error_message", ""),
				result.get("override_reason", ""),
			]
			ws_details.append(row)
			row_num = ws_details.max_row
			fill = status_fills.get(result["status"])
			if fill:
				ws_details.cell(row=row_num, column=2).fill = fill

		# Auto-width for details
		for col_letter in ["A", "B", "C", "D", "E", "F"]:
			ws_details.column_dimensions[col_letter].width = 20
		ws_details.column_dimensions["A"].width = 30
		ws_details.column_dimensions["D"].width = 50

		wb.save(str(excel_path))
		return excel_path

	async def invalidate_cache(self, run_id: str) -> None:
		"""Remove cached reports (e.g., after override changes a result)."""
		report_dir = Config.REPORTS_DIR / run_id
		if report_dir.exists():
			import shutil
			shutil.rmtree(report_dir, ignore_errors=True)

	async def _get_report_data(self, run_id: str) -> dict:
		"""Fetch all data needed for report generation."""
		db = await get_db()
		try:
			# Get run info
			async with db.execute(
				"SELECT tr.*, tp.name as plan_name FROM test_runs tr "
				"JOIN test_plans tp ON tr.plan_id = tp.id WHERE tr.id=?",
				(run_id,),
			) as cursor:
				run_row = await cursor.fetchone()
				if not run_row:
					raise ValueError(f"Run {run_id} not found")
				run_cols = [d[0] for d in cursor.description]
				run = dict(zip(run_cols, run_row))

			# Get results with case names
			async with db.execute(
				"SELECT r.*, tc.case_name FROM test_results r "
				"JOIN test_cases tc ON r.case_id = tc.id "
				"WHERE r.run_id=? ORDER BY r.started_at",
				(run_id,),
			) as cursor:
				result_rows = await cursor.fetchall()
				result_cols = [d[0] for d in cursor.description]
				results_raw = [dict(zip(result_cols, row)) for row in result_rows]
		finally:
			await db.close()

		# Process results
		results = []
		for r in results_raw:
			item = {
				"case_name": r["case_name"],
				"status": r["status"],
				"duration_seconds": r.get("duration_seconds"),
				"error_message": r.get("error_message"),
				"evaluation_summary": r.get("actual_result"),
				"original_status": r.get("original_status"),
				"override_reason": r.get("override_reason"),
				"checkpoints": None,
				"failure_screenshot_b64": None,
			}

			# Parse evaluation details for checkpoints
			eval_details = r.get("evaluation_details")
			if eval_details:
				try:
					details = json.loads(eval_details)
					item["checkpoints"] = details.get("checkpoints", [])
				except (json.JSONDecodeError, TypeError):
					pass

			# Load failure screenshot for failed cases
			if r["status"] == "failed" and r.get("trajectory_path"):
				traj_path = Path(r["trajectory_path"])
				ss_dir = traj_path.parent / f"{traj_path.stem}_screenshots"
				if ss_dir.exists():
					# Get last screenshot
					pngs = sorted(ss_dir.glob("step_*.png"))
					if pngs:
						last_png = pngs[-1]
						item["failure_screenshot_b64"] = base64.b64encode(
							last_png.read_bytes()
						).decode()

			results.append(item)

		# Calculate stats
		total = len(results)
		passed = sum(1 for r in results if r["status"] == "passed")
		failed = sum(1 for r in results if r["status"] == "failed")
		error_count = sum(1 for r in results if r["status"] == "error")
		pass_rate = round((passed / total * 100) if total > 0 else 0)

		# Duration
		started_at = run.get("started_at", "")
		completed_at = run.get("completed_at", "")
		duration = ""
		if started_at and completed_at:
			try:
				start = datetime.fromisoformat(started_at)
				end = datetime.fromisoformat(completed_at)
				secs = (end - start).total_seconds()
				mins = int(secs // 60)
				remaining_secs = int(secs % 60)
				duration = f"{mins}m {remaining_secs}s"
			except (ValueError, TypeError):
				duration = "N/A"

		return {
			"run_id": run_id,
			"plan_name": run.get("plan_name", "未命名计划"),
			"started_at": started_at,
			"completed_at": completed_at,
			"duration": duration,
			"total": total,
			"passed": passed,
			"failed": failed,
			"error_count": error_count,
			"pass_rate": pass_rate,
			"results": results,
		}


# Singleton
report_service = ReportService()
