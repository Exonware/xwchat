#!/usr/bin/env python3
"""
Update a __date__ literal in the version file referenced from pyproject.toml
to today's ISO date (YYYY-MM-DD), when present as a string literal.

This is extracted from the GitHub Actions publish workflow so it can be reused
and tested outside of CI.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path


def main() -> None:
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("No pyproject.toml; skipping __date__ update")
        sys.exit(0)

    pyproject = pyproject_path.read_text(encoding="utf-8")
    m = re.search(
        r"\[tool\.hatch\.version\][^\n]*\n\s*path\s*=\s*[\"']([^\"']+)[\"']",
        pyproject,
        re.DOTALL,
    )
    if not m:
        print("No [tool.hatch.version] path; skipping __date__ update")
        sys.exit(0)

    version_file = Path(m.group(1).strip())
    if not version_file.exists():
        print(f"Version file not found: {version_file}; skipping __date__ update")
        sys.exit(0)

    text = version_file.read_text(encoding="utf-8")
    literal_match = re.search(
        r"__date__\s*=\s*[\"'][^\"']*[\"']",
        text,
    )
    if not literal_match:
        print("__date__ is dynamic or missing; no update needed")
        sys.exit(0)

    today = date.today().isoformat()
    new_text = re.sub(
        r"(__date__\s*=\s*)[\"'][^\"']*[\"']",
        r'\1"' + today + '"',
        text,
    )
    version_file.write_text(new_text, encoding="utf-8")
    print("Set __date__ to", today, "in", version_file)


if __name__ == "__main__":
    main()

