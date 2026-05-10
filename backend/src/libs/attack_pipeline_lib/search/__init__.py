"""攻撃経路探索アルゴリズムのインターフェースと実装。

新しい探索アルゴリズムを追加する手順:
  1. このフォルダに新しいファイルを追加する (例: search/topk_shortest.py)
  2. _protocol.PathSearcher を継承したクラスを実装する
  3. pipeline.py の _build_searcher() に選択肢として登録する
"""

from __future__ import annotations

from ._base import PathSearcher
from .exhaustive import ExhaustiveSearcher

__all__ = ["PathSearcher", "ExhaustiveSearcher"]
