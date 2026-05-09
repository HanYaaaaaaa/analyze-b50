#!/usr/bin/env python3
from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "assets" / "peer_stats.zip"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download anonymous peer stats for analyze-b50.")
    parser.add_argument("--url", required=True, help="Release asset URL for peer_stats.zip, peer_stats.json, or peer_stats.json.gz")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output path")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(args.url, timeout=args.timeout) as resp:
        out.write_bytes(resp.read())
    print(f"Downloaded peer stats to {out}")


if __name__ == "__main__":
    main()
