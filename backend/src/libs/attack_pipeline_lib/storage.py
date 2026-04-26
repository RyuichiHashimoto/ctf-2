"""パイプライン実験結果の保存処理。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path("/app")
DATA_DIR = BASE_DIR / "data"
PIPELINE_RESULT_DIR = DATA_DIR / "pipeline_results"


def save_pipeline_result(
    experiment_id: str,
    result: dict[str, Any],
    result_dir: Path | str = PIPELINE_RESULT_DIR,
) -> Path:
    """パイプライン実行結果をJSONファイルとして保存する。

    Args:
        experiment_id: 実験ID。
        result: 保存する実行結果。
        result_dir: 保存先ディレクトリ。

    Returns:
        保存したJSONファイルのパス。
    """
    target_dir = Path(result_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{experiment_id}.json"
    payload = {
        "experiment_id": experiment_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    target_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_path
