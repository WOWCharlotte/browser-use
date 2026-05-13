#!/usr/bin/env python3
"""
Quality Gate Checker for Unit Test Write Phase
Validates that test files are generated
"""

import sys
import os
from pathlib import Path


def check_outputs(change_dir: str) -> bool:
    """Check if required output files exist in the unit_test directory."""
    change_path = Path(change_dir)
    unit_test_dir = change_path / "unit_test"

    if not unit_test_dir.exists():
        print(f"ERROR: {unit_test_dir} does not exist")
        return False

    # Check for test report
    reports = list(unit_test_dir.glob("test_report_v*.md"))
    if not reports:
        print("ERROR: No test report found (test_report_v*.md)")
        return False

    print(f"OK: Latest test report: {max(reports).name}")

    # Check review subdirectory if exists
    review_dir = unit_test_dir / "review"
    if review_dir.exists():
        reviews = list(review_dir.glob("test_review_v*.md"))
        if reviews:
            print(f"OK: Latest test review: {max(reviews).name}")

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