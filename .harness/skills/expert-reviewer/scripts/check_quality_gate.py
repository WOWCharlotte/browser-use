#!/usr/bin/env python3
"""
Quality Gate Checker for Expert Reviewer Phase
Validates that review files are generated for the appropriate stage
"""

import sys
import os
from pathlib import Path


def check_outputs(change_dir: str, stage: str) -> bool:
    """Check if required review files exist."""
    change_path = Path(change_dir)

    if stage == "request":
        review_dir = change_path / "request_analysis" / "review"
        pattern = "*_review_v*.md"
    elif stage == "coding":
        review_dir = change_path / "coding" / "review"
        pattern = "code_review_v*.md"
    elif stage == "unit_test":
        review_dir = change_path / "unit_test" / "review"
        pattern = "test_review_v*.md"
    else:
        print(f"ERROR: Unknown stage '{stage}'")
        return False

    if not review_dir.exists():
        print(f"ERROR: {review_dir} does not exist")
        return False

    reviews = list(review_dir.glob(pattern))
    if not reviews:
        print(f"ERROR: No review found matching '{pattern}'")
        return False

    print(f"OK: Latest review: {max(reviews).name}")
    print("\n✓ All required output files present")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python check_quality_gate.py <change-id> <stage>")
        print("Stages: request, coding, unit_test")
        print("Example: python check_quality_gate.py feat-ai-workspace-20260508 request")
        sys.exit(1)

    change_id = sys.argv[1]
    stage = sys.argv[2]
    base_dir = Path(__file__).parent.parent.parent / "changes" / change_id

    success = check_outputs(base_dir, stage)
    sys.exit(0 if success else 1)