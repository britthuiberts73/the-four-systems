#!/usr/bin/env python3
"""Publish a markdown post to an Astro repo, if context/publishing.json is configured.

This is a no-op if context/publishing.json does not exist. Most users skip this
and upload markdown by hand. For users on Astro+Cloudflare it commits the post
to a draft branch (or main, per their config) and pushes.

Usage:
  publish-to-astro.py <markdown-path>

Returns:
  exit 0 + prints the published URL on success
  exit 0 + prints "SKIPPED" on no-publishing-config
  exit 1 on error
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = ROOT.parent.parent / "context"  # expects user's context/ at project root


def find_context_dir() -> Path | None:
    """Walk up from script dir looking for a sibling context/ directory."""
    for candidate in [
        ROOT.parent / "context",
        ROOT.parent.parent / "context",
        Path.cwd() / "context",
    ]:
        if candidate.is_dir():
            return candidate
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: publish-to-astro.py <markdown-path>", file=sys.stderr)
        return 1

    md_path = Path(sys.argv[1]).resolve()
    if not md_path.exists():
        print(f"ERROR: markdown file not found: {md_path}", file=sys.stderr)
        return 1

    ctx = find_context_dir()
    if ctx is None:
        print("SKIPPED (no context/ directory found)")
        return 0
    cfg_path = ctx / "publishing.json"
    if not cfg_path.exists():
        print("SKIPPED (no publishing.json, defaulting to markdown-only)")
        return 0

    cfg = json.loads(cfg_path.read_text())
    if cfg.get("mode") != "astro":
        print(f"SKIPPED (publishing mode is '{cfg.get('mode')}', not astro)")
        return 0

    repo_path = Path(cfg["repo_path"]).expanduser()
    content_dir = repo_path / cfg.get("content_dir", "src/content/blog")
    if not content_dir.is_dir():
        print(f"ERROR: content dir does not exist: {content_dir}", file=sys.stderr)
        return 1

    target = content_dir / md_path.name
    target.write_bytes(md_path.read_bytes())
    print(f"Copied: {md_path.name} -> {target}")

    branch_strategy = cfg.get("branch_strategy", "draft")
    branch_prefix = cfg.get("draft_branch_prefix", "claude/post-")
    slug = md_path.stem

    def run(cmd: list[str], check: bool = True) -> str:
        r = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        if check and r.returncode != 0:
            print(f"ERROR ({' '.join(cmd)}): {r.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
        return r.stdout.strip()

    if branch_strategy == "draft":
        branch = f"{branch_prefix}{slug}"
        run(["git", "checkout", "-B", branch])
    else:
        run(["git", "checkout", "main"])

    run(["git", "add", str(target.relative_to(repo_path))])
    run(["git", "commit", "-m", f"post: {slug}"], check=False)
    run(["git", "push", "-u", "origin", "HEAD"], check=False)

    if branch_strategy == "draft":
        print(f"PUBLISHED_DRAFT branch={branch} (open a PR to ship to main)")
    else:
        site = cfg.get("public_url_base", "").rstrip("/")
        url = f"{site}/blog/{slug}/" if site else f"published to main as {slug}"
        print(f"PUBLISHED_LIVE {url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
