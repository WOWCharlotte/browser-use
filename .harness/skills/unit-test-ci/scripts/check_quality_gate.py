#!/usr/bin/env python3
"""
Quality Gate Checker for CI Phase
Validates that CI result files are generated: ci_result_v*.md
"""

import sys
import os
from pathlib import Path


def check_outputs(change_dir: str) -> bool:
    """Check if required output files exist in the ci_result directory."""
    change_path = Path(change_dir)
    ci_result_dir = change_path / "ci_result"

    if not ci_result_dir.exists():
        print(f"ERROR: {ci_result_dir} does not exist")
        return False

    # Check for CI result
    results = list(ci_result_dir.glob("ci_result_v*.md"))
    if not results:
        print("ERROR: No CI result found (ci_result_v*.md)")
        return False

    latest = max(results)
    print(f"OK: Latest CI result: {latest.name}")

    # Read and validate content
    content = latest.read_text()
    if "status" not in content.lower():
        print("WARNING: CI result may not contain status information")

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