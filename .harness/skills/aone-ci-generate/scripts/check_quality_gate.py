#!/usr/bin/env python3
"""
Quality Gate Checker for Aone CI Generate Phase
Validates that CI configuration files are generated
"""

import sys
import os
from pathlib import Path


def check_outputs(output_dir: str) -> bool:
    """Check if CI configuration files exist."""
    output_path = Path(output_dir)

    # Check for CI config files
    ci_files = list(output_path.glob("*.yaml")) + list(output_path.glob("*.yml"))

    if not ci_files:
        print(f"ERROR: No CI configuration files found in {output_path}")
        return False

    print(f"OK: Found {len(ci_files)} CI configuration file(s):")
    for f in ci_files:
        print(f"  - {f.name}")

    print("\n✓ CI configuration generated")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_quality_gate.py <output-dir>")
        print("Example: python check_quality_gate.py ./ci-config")
        sys.exit(1)

    output_dir = sys.argv[1]

    success = check_outputs(output_dir)
    sys.exit(0 if success else 1)