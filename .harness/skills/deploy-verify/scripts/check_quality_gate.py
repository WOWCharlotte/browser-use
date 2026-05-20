#!/usr/bin/env python3
"""
Quality Gate Checker for Deploy Verify Phase
Validates that deployment report files are generated: deploy_report_v*.md
"""

import sys
import os
from pathlib import Path


def check_outputs(change_dir: str) -> bool:
    """Check if required output files exist in the deployment directory."""
    change_path = Path(change_dir)
    deployment_dir = change_path / "deployment"

    if not deployment_dir.exists():
        print(f"ERROR: {deployment_dir} does not exist")
        return False

    # Check for deployment report
    reports = list(deployment_dir.glob("deploy_report_v*.md"))
    if not reports:
        print("ERROR: No deployment report found (deploy_report_v*.md)")
        return False

    print(f"OK: Latest deployment report: {max(reports).name}")
    print("\n[SUCCESS] All required output files present")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_quality_gate.py <change-id>")
        print("Example: python check_quality_gate.py feat-ai-workspace-20260508")
        sys.exit(1)

    change_id = sys.argv[1]
    base_dir = Path(__file__).parent.parent.parent.parent / "changes" / change_id

    success = check_outputs(base_dir)
    sys.exit(0 if success else 1)