#!/usr/bin/env python3
"""Atomically update a queue item's status, written_at, and/or post_url.

Usage:
  mark-queue-item.py <id> --status in_progress
  mark-queue-item.py <id> --status written --post-url ./output/posts/2026-05-06-foo.md
  mark-queue-item.py <id> --status written --post-url https://yoursite.com/blog/foo --published-url https://...

Writes back to content-queue.json with a tmpfile + rename, so concurrent runs
do not corrupt the file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

QUEUE = Path(__file__).resolve().parent.parent / "state" / "content-queue.json"
VALID_STATUSES = {"queued", "in_progress", "written", "needs_review", "skipped"}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("item_id", help="Queue item id to update")
    p.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    p.add_argument("--post-url", default=None, help="Local path or live URL for the post")
    p.add_argument("--published-url", default=None, help="Override post_url with a live URL after publish")
    args = p.parse_args()

    if not QUEUE.exists():
        print(f"ERROR: {QUEUE} not found", file=sys.stderr)
        return 1

    data = json.loads(QUEUE.read_text())
    found = False
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for item in data.get("items", []):
        if item.get("id") == args.item_id:
            item["status"] = args.status
            if args.status == "written":
                item["written_at"] = now
            if args.post_url:
                item["post_url"] = args.post_url
            if args.published_url:
                item["post_url"] = args.published_url
            found = True
            break

    if not found:
        print(f"ERROR: queue item id '{args.item_id}' not found", file=sys.stderr)
        return 1

    # Atomic write
    tmp = tempfile.NamedTemporaryFile(
        mode="w", dir=QUEUE.parent, prefix=".tmp-queue-", suffix=".json", delete=False
    )
    json.dump(data, tmp, indent=2)
    tmp.write("\n")
    tmp.close()
    os.replace(tmp.name, QUEUE)
    print(f"Updated item '{args.item_id}': status={args.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
