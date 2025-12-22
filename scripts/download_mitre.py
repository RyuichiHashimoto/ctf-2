#!/usr/bin/env python3
"""Download MITRE ATT&CK Enterprise STIX bundle JSON."""
from __future__ import annotations

import argparse
import sys
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default=(
            "https://raw.githubusercontent.com/mitre-attack/"
            "attack-stix-data/master/enterprise-attack/enterprise-attack.json"
        ),
        help="Source URL for enterprise-attack.json",
    )
    parser.add_argument(
        "--out",
        default="data/enterprise-attack.json",
        help="Output path for downloaded JSON",
    )
    args = parser.parse_args()

    try:
        with urllib.request.urlopen(args.url) as response:
            content = response.read()
    except Exception as exc:
        print(f"Failed to download: {exc}", file=sys.stderr)
        return 1

    try:
        with open(args.out, "wb") as handle:
            handle.write(content)
    except OSError as exc:
        print(f"Failed to write {args.out}: {exc}", file=sys.stderr)
        return 1

    print(f"Downloaded to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
