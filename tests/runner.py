#!/usr/bin/env python3
"""
#exonware/xwchat/tests/runner.py
Main test runner for xwchat (GUIDE_51_TEST).
Usage:
    python tests/runner.py
    python tests/runner.py --core
    python tests/runner.py --unit
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> int:
    test_dir = Path(__file__).resolve().parent
    root = test_dir.parent
    src = root / "src"
    if src.is_dir():
        sys.path.insert(0, str(src))

    cmd = [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=short"]
    if "--core" in sys.argv:
        cmd.extend(["-m", "xwchat_core"])
    elif "--unit" in sys.argv:
        cmd.extend(["-m", "xwchat_unit"])

    print("=" * 80)
    print("xwchat Test Runner")
    print("=" * 80)
    return subprocess.run(cmd, cwd=root).returncode


if __name__ == "__main__":
    raise SystemExit(main())
