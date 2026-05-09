#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://www.diving-fish.com/api/maimaidxprober/query/player"


def fetch_b50(qq: str, timeout: int = 30) -> dict:
    payload = json.dumps({"qq": int(qq), "b50": True}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            raise SystemExit(f"User not found or B50 is unavailable for QQ {qq}") from exc
        if exc.code == 403:
            raise SystemExit(f"User disabled public query for QQ {qq}") from exc
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch maimai DX B50 from Diving-Fish by QQ.")
    parser.add_argument("--qq", required=True, help="QQ number")
    parser.add_argument("--out", help="Output JSON path. Prints to stdout when omitted.")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    data = fetch_b50(args.qq, args.timeout)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
