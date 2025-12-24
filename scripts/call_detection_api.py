#!/usr/bin/env python3
"""Call the detection API with a JSON payload."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import os

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default= f"{os.environ['VITE_API_BASE']}/detection")
    parser.add_argument("--device-id", default="en1")
    parser.add_argument("--event", default="detection")
    parser.add_argument("--detail", default="T1078")
    args = parser.parse_args()

    payload = {
        "device_id": args.device_id,
        "event": args.event,
        "detail": args.detail,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        args.url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
