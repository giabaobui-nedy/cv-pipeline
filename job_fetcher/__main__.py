"""Entry point for `python -m job_fetcher <url>`.

Delegates to tools/fetch_job.py so both invocation styles stay in sync.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_tool = Path(__file__).resolve().parent.parent / "tools" / "fetch_job.py"
sys.exit(runpy.run_path(str(_tool), run_name="__main__") or 0)
