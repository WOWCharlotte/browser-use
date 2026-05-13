#!/usr/bin/env python3
"""
Quality Gate Checker for Project Analysis Phase
Validates that project analysis outputs are generated
"""

import sys
import os
from pathlib import Path


def check_outputs(analysis_dir: str) -> bool:
    """Check if project analysis output files exist."""
    analysis_path = Path(analysis_dir)

    # For project analysis, we check if any analysis files exist
    md_files = list(analysis_path.glob("*.md"))

    if not md_files:
        print(f"ERROR: No analysis files found in {analysis_path}")
        return False

    print(f"OK: Found {len(md_files)} analysis file(s):")
    for f in md_files:
        print(f"  - {f.name}")

    print("\n✓ Project analysis completed")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_quality_gate.py <analysis-dir>")
        print("Example: python check_quality_gate.py ./analysis")
        sys.exit(1)

    analysis_dir = sys.argv[1]

    success = check_outputs(analysis_dir)
    sys.exit(0 if success else 1)