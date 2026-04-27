#!/usr/bin/env python3
"""
Verify that the version configured in pyproject.toml ultimately comes from a
single source-of-truth version location (file or attribute) and print it.

This is extracted from the GitHub Actions check-versions workflow so it can be
tested and reused outside of CI.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path


def _read_pyproject() -> str:
    path = Path("pyproject.toml")
    if not path.exists():
        print("No pyproject.toml", file=sys.stderr)
        sys.exit(2)
    return path.read_text(encoding="utf-8")


def _read_attr_from_module_source(
    project_root: Path,
    module_name: str,
    attr_name: str,
) -> str | None:
    """
    Resolve module source under ./src and read a simple string assignment
    like: __version__ = "1.2.3"
    This avoids import side effects from package-level dependencies.
    """
    module_rel = Path(*module_name.split("."))
    candidates = [
        project_root / "src" / (str(module_rel) + ".py"),
        project_root / "src" / module_rel / "__init__.py",
    ]
    pattern = re.compile(
        rf"^\s*{re.escape(attr_name)}\s*=\s*['\"]([^'\"]+)['\"]\s*$",
        re.MULTILINE,
    )
    for candidate in candidates:
        if not candidate.exists():
            continue
        text = candidate.read_text(encoding="utf-8")
        m = pattern.search(text)
        if m:
            return m.group(1)
    return None


def main() -> None:
    text = _read_pyproject()

    # 1) Hatchling: [tool.hatch.version] path = ".../version.py"
    m = re.search(
        r"\[tool\.hatch\.version\][^\n]*\n\s*path\s*=\s*[\"']([^\"']+)[\"']",
        text,
        re.DOTALL,
    )
    if m:
        version_file = Path(m.group(1).strip())
        if not version_file.exists():
            print(f"Version file not found: {version_file}", file=sys.stderr)
            sys.exit(2)
        ns: dict[str, object] = {}
        exec(version_file.read_text(encoding="utf-8"), ns)
        version = ns.get("__version__")
        if not isinstance(version, str) or not version:
            print(f"__version__ missing or empty in {version_file}", file=sys.stderr)
            sys.exit(2)
        print("Current version:", version)
        sys.exit(0)

    # 2) Setuptools dynamic inline table (file=...) -> open version file and exec
    m = re.search(
        r'version\s*=\s*\{\s*file\s*=\s*["\']([^"\']+)["\']',
        text,
        re.DOTALL,
    )
    if not m:
        # 2b) Setuptools dynamic table style:
        # [tool.setuptools.dynamic.version]
        # attr = "pkg.module.__version__" OR file = "..."
        m = re.search(
            r"\[tool\.setuptools\.dynamic\.version\][^\n]*\n\s*file\s*=\s*[\"']([^\"']+)[\"']",
            text,
            re.DOTALL,
        )
    if m:
        version_file = Path(m.group(1).strip())
        if not version_file.exists():
            print(f"Version file not found: {version_file}", file=sys.stderr)
            sys.exit(2)
        ns: dict[str, object] = {}
        exec(version_file.read_text(encoding="utf-8"), ns)
        version = ns.get("__version__")
        if not isinstance(version, str) or not version:
            print(f"__version__ missing or empty in {version_file}", file=sys.stderr)
            sys.exit(2)
        print("Current version:", version)
        sys.exit(0)

    # 3) Setuptools dynamic inline table (attr="pkg.module.__version__")
    m = re.search(
        r'version\s*=\s*\{\s*attr\s*=\s*["\']([^"\']+)["\']',
        text,
        re.DOTALL,
    )
    if not m:
        # 3b) Setuptools dynamic table style:
        # [tool.setuptools.dynamic.version]
        # attr = "pkg.module.__version__"
        m = re.search(
            r"\[tool\.setuptools\.dynamic\.version\][^\n]*\n\s*attr\s*=\s*[\"']([^\"']+)[\"']",
            text,
            re.DOTALL,
        )
    if m:
        attr_path = m.group(1).strip()
        module_name, _, attr = attr_path.rpartition(".")
        if not module_name or not attr:
            sys.exit(2)
        version = _read_attr_from_module_source(Path("."), module_name, attr)
        if version is None:
            # Fallback to import for unusual dynamic cases.
            mod = importlib.import_module(module_name)
            version = getattr(mod, attr, None)
        if not isinstance(version, str) or not version:
            print(
                f"Attribute {attr_path} is missing or empty",
                file=sys.stderr,
            )
            sys.exit(2)
        print("Current version:", version)
        sys.exit(0)

    # If none of the patterns matched, exit with a non-success status expected by CI.
    sys.exit(2)


if __name__ == "__main__":
    main()

