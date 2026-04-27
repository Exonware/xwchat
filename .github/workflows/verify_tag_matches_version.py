#!/usr/bin/env python3
"""
Verify that the current Git reference (tag) matches the library version defined
in the version file referenced from pyproject.toml.

This script is extracted from the GitHub Actions publish workflow so it can be
reused and tested outside of CI.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _load_version_from_pyproject() -> str | None:
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("No pyproject.toml; skipping", file=sys.stderr)
        return None

    text = pyproject_path.read_text(encoding="utf-8")
    m = re.search(
        r"\[tool\.hatch\.version\][^\n]*\n\s*path\s*=\s*[\"']([^\"']+)[\"']",
        text,
        re.DOTALL,
    )
    if not m:
        print("No [tool.hatch.version] path; skipping", file=sys.stderr)
        return None

    version_file = Path(m.group(1).strip())
    if not version_file.exists():
        print(f"Version file not found: {version_file}", file=sys.stderr)
        sys.exit(1)

    ns: dict[str, object] = {}
    exec(version_file.read_text(encoding="utf-8"), ns)
    version = ns.get("__version__")
    if not isinstance(version, str) or not version:
        print(f"__version__ missing or empty in {version_file}", file=sys.stderr)
        sys.exit(1)
    return version


def main() -> None:
    file_ver = _load_version_from_pyproject()
    if not file_ver:
        # Nothing to check; treat as non-fatal.
        sys.exit(0)

    ref = os.environ.get("GITHUB_REF", "")
    if not ref.startswith("refs/tags/"):
        print(f"Not a tag build; version: {file_ver}")
        sys.exit(0)

    tag_name = ref.removeprefix("refs/tags/")
    tag_ver = tag_name[1:] if tag_name.startswith("v") else tag_name

    if tag_ver != file_ver:
        print(f"ERROR: Tag {tag_ver} != version.py {file_ver}", file=sys.stderr)
        sys.exit(1)

    print("OK: tag and version match:", file_ver)
    sys.exit(0)


if __name__ == "__main__":
    main()
