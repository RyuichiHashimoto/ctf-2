"""Run the attack prediction pipeline from a JSON input file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from libs.attack_pipeline_lib.pipeline import run_pipeline
from libs.attack_pipeline_lib.schema import PipelineInput


def main() -> None:
    """Execute one pipeline run from CLI arguments."""
    args = _parse_args()
    payload = _load_json(args.input)
    result = run_pipeline(PipelineInput.from_dict(payload)).asdict()
    _write_result(result, args.output)


def _parse_args() -> argparse.Namespace:
    """Parse experiment runner arguments."""
    parser = argparse.ArgumentParser(
        description="Run attack path prediction pipeline from a JSON file.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSON file containing system, vulnerabilities, threats, and config.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write the result JSON. Prints to stdout when omitted.",
    )
    return parser.parse_args()


def _load_json(path: str) -> dict[str, Any]:
    """Load a JSON object from disk."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be an object")
    return payload


def _write_result(result: dict[str, Any], output_path: str | None) -> None:
    """Write a result JSON to disk or stdout."""
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        Path(output_path).write_text(content + "\n", encoding="utf-8")
        return
    print(content)


if __name__ == "__main__":
    main()
