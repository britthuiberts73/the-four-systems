#!/usr/bin/env python3
"""Print the next queued content-queue item as JSON, or exit 2 if nothing queued.

The Content Writer (System 2) calls this at the start of an auto-pilot run to
get the brief. Items are picked in queue order: items[] is treated as a FIFO,
so editors who want to reorder can just rearrange the array by hand.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

QUEUE = Path(__file__).resolve().parent.parent / "state" / "content-queue.json"


def main() -> int:
    if not QUEUE.exists():
        print("ERROR: content-queue.json not found", file=sys.stderr)
        return 1
    data = json.loads(QUEUE.read_text())
    for item in data.get("items", []):
        if item.get("status") == "queued":
            json.dump(item, sys.stdout, indent=2)
            return 0
    print("NO_QUEUED_ITEMS", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
