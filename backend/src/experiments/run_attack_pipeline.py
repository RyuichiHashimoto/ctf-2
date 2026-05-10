"""攻撃経路予測パイプラインを JSON 入力ファイルから実行する。

Usage
-----
基本実行（stdout に出力）::

    PYTHONPATH=src python3 src/experiments/run_attack_pipeline.py \\
        --input src/experiments/sample_input.json \\
        --config src/experiments/sample_config.json

CLI 引数で config を上書きして実験結果を保存::

    PYTHONPATH=src python3 src/experiments/run_attack_pipeline.py \\
        --input src/experiments/sample_input.json \\
        --config src/experiments/sample_config.json \\
        --augmentation-mode full_mesh \\
        --top-k 3 \\
        --experiment-id exp001 \\
        --result-dir ./results

環境変数で保存先を指定::

    PIPELINE_RESULT_DIR=./results PYTHONPATH=src python3 ...
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from libs.attack_pipeline_lib import PipelineInput, run_pipeline
from libs.attack_pipeline_lib.metrics.storage import PIPELINE_RESULT_DIR, save_pipeline_result


def main() -> None:
    """CLI 引数を解析してパイプラインを 1 回実行する。"""
    args = _parse_args()
    payload = _load_json(args.input)
    config = _load_json(args.config) if args.config else {}
    config = _apply_config_overrides(config, args)

    result = run_pipeline(PipelineInput.from_dict({**payload, "config": config})).asdict()

    _save_if_requested(result, args.experiment_id, args.result_dir)
    _write_result(result, args.output)


def _parse_args() -> argparse.Namespace:
    """CLI 引数を定義して解析する。

    Returns
    -------
    argparse.Namespace
        解析済み引数。
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run attack path prediction pipeline from JSON files. "
            "CLI arguments override values in the config file."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # --- 入出力 ---
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Input JSON file (system graph with node-embedded vulnerabilities).",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Config JSON file (augmentation_mode, max_nodes, top_k, ...).",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Write result JSON to this path. Prints to stdout when omitted.",
    )

    # --- 実験 ID・保存先 ---
    parser.add_argument(
        "--experiment-id",
        metavar="ID",
        help=(
            "Experiment identifier. When set, the result is saved as "
            "{result-dir}/{ID}.json."
        ),
    )
    parser.add_argument(
        "--result-dir",
        metavar="PATH",
        help=(
            "Directory to save experiment results. "
            "Overrides the PIPELINE_RESULT_DIR environment variable "
            f"(default: {PIPELINE_RESULT_DIR})."
        ),
    )

    # --- config 上書き ---
    parser.add_argument(
        "--augmentation-mode",
        choices=["none", "full_mesh", "bidirectional"],
        metavar="MODE",
        help="Graph augmentation mode (none / full_mesh / bidirectional). Overrides config.",
    )
    parser.add_argument(
        "--max-nodes",
        type=int,
        metavar="N",
        help="Maximum number of nodes per path. Overrides config.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        metavar="K",
        help="Return top-K paths by risk. Overrides config.",
    )

    return parser.parse_args()


def _load_json(path: str) -> dict[str, Any]:
    """ディスクから JSON オブジェクトを読み込む。

    Parameters
    ----------
    path : str
        入力ファイルのパス。

    Returns
    -------
    dict
        解析済み JSON オブジェクト。

    Raises
    ------
    ValueError
        JSON のトップレベルがオブジェクトでない場合。
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON must be an object")
    return payload


def _apply_config_overrides(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    """CLI 引数で config の値を上書きする。

    Parameters
    ----------
    config : dict
        config ファイルから読み込んだ設定値。
    args : argparse.Namespace
        解析済み CLI 引数。

    Returns
    -------
    dict
        CLI 引数を反映した設定値。
    """
    overrides: dict[str, Any] = {}
    if args.augmentation_mode is not None:
        overrides["augmentation_mode"] = args.augmentation_mode
    if args.max_nodes is not None:
        overrides["max_nodes"] = args.max_nodes
    if args.top_k is not None:
        overrides["top_k"] = args.top_k
    return {**config, **overrides}


def _save_if_requested(
    result: dict[str, Any],
    experiment_id: str | None,
    result_dir: str | None,
) -> None:
    """experiment_id が指定されている場合に結果をファイルへ保存する。

    保存先の優先順位: CLI --result-dir > 環境変数 PIPELINE_RESULT_DIR > デフォルト。

    Parameters
    ----------
    result : dict
        保存する実行結果。
    experiment_id : str or None
        実験 ID。``None`` の場合は何もしない。
    result_dir : str or None
        CLI で指定された保存先ディレクトリ。
    """
    if not experiment_id:
        return
    dir_path = result_dir or os.environ.get("PIPELINE_RESULT_DIR") or str(PIPELINE_RESULT_DIR)
    saved_path = save_pipeline_result(experiment_id, result, dir_path)
    print(f"saved: {saved_path}", file=sys.stderr)


def _write_result(result: dict[str, Any], output_path: str | None) -> None:
    """結果 JSON をファイルまたは stdout へ書き出す。

    Parameters
    ----------
    result : dict
        書き出す実行結果。
    output_path : str or None
        書き出し先ファイルパス。``None`` の場合は stdout へ出力する。
    """
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        Path(output_path).write_text(content + "\n", encoding="utf-8")
        return
    print(content)


if __name__ == "__main__":
    main()
