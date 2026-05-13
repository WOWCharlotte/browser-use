#!/usr/bin/env python3
"""
Quality Gate Checker for Request Analysis Phase
Validates that required output files are generated: xmind.md, spec.md, tasks.md
"""

import sys
import os
from pathlib import Path

REQUIRED_FILES = ["xmind.md", "spec.md", "tasks.md"]
OPTIONAL_FILES = ["uml.md"]


def check_outputs(change_dir: str) -> bool:
    """Check if required output files exist in the request_analysis directory."""
    change_path = Path(change_dir)
    request_analysis_dir = change_path / "request_analysis"

    if not request_analysis_dir.exists():
        print(f"ERROR: {request_analysis_dir} does not exist")
        return False

    missing = []
    for file in REQUIRED_FILES:
        file_path = request_analysis_dir / file
        if not file_path.exists():
            missing.append(file)
        else:
            print(f"OK: {file} exists")

    if missing:
        print(f"\nERROR: Missing required files: {', '.join(missing)}")
        return False

    # Check optional files
    for file in OPTIONAL_FILES:
        file_path = request_analysis_dir / file
        if file_path.exists():
            print(f"OK: {file} exists (optional)")
        else:
            print(f"SKIP: {file} not found (optional)")

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