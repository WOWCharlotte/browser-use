#!/usr/bin/env python3
"""
Quality Gate Checker for Code Review Phase
Validates that code review format checks are passed
"""

import sys
import os
from pathlib import Path


def check_outputs(change_dir: str) -> bool:
    """Check if code review output files exist."""
    change_path = Path(change_dir)
    coding_dir = change_path / "coding"

    if not coding_dir.exists():
        print(f"ERROR: {coding_dir} does not exist")
        return False

    # Check that code review was done
    review_dir = coding_dir / "review"
    if not review_dir.exists():
        print("ERROR: review directory does not exist")
        return False

    reviews = list(review_dir.glob("code_review_v*.md"))
    if not reviews:
        print("ERROR: No code review found")
        return False

    latest = max(reviews)
    print(f"OK: Latest code review: {latest.name}")

    # Read content and check for quality gate status
    content = latest.read_text()
    if "MUST FIX" in content:
        must_fix_count = content.count("MUST FIX")
        print(f"WARNING: Found {must_fix_count} MUST FIX items - blocking issues must be resolved")

    print("\n✓ Code review completed")
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