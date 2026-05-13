#!/usr/bin/env python3
"""
Quality Gate Checker for Coding Phase
Validates that coding output files are generated: coding_report_v*.md
"""

import sys
import os
from pathlib import Path
import re


def check_outputs(change_dir: str) -> bool:
    """Check if required output files exist in the coding directory."""
    change_path = Path(change_dir)
    coding_dir = change_path / "coding"

    if not coding_dir.exists():
        print(f"ERROR: {coding_dir} does not exist")
        return False

    # Check for coding report (versioned)
    reports = list(coding_dir.glob("coding_report_v*.md"))
    if not reports:
        print("ERROR: No coding report found (coding_report_v*.md)")
        return False

    latest_report = max(reports)
    print(f"OK: Latest coding report: {latest_report.name}")

    # Check review directory exists
    review_dir = coding_dir / "review"
    if not review_dir.exists():
        print("ERROR: review directory does not exist")
        return False

    # Check for code review report
    reviews = list(review_dir.glob("code_review_v*.md"))
    if not reviews:
        print("ERROR: No code review found (code_review_v*.md)")
        return False

    print(f"OK: Latest code review: {max(reviews).name}")
    print("\n✓ All required output files present")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_quality_gate.py <change-id>")
        print("Example: python check_quality_gate.py feat-ai-workspace-20260508")
        sys.exit(1)

    change_id = sys.argv[1]
    base_dir = Path(__file__).parent.parent.parent / "changes" / change_id

    success = check_outputs(base_dir)
    sys.exit(0 if success else 1)