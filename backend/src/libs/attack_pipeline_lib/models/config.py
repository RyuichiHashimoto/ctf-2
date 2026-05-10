"""攻撃経路予測パイプラインの設定モデル。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AugmentationMode(str, Enum):
    """グラフ補完方式。

    Attributes
    ----------
    NONE : str
        補完を行わない。
    FULL_MESH : str
        全ノード間を有向エッジで接続する。
    BIDIRECTIONAL : str
        既存エッジの逆方向エッジを追加する。
    """

    NONE = "none"
    FULL_MESH = "full_mesh"
    BIDIRECTIONAL = "bidirectional"

    @classmethod
    def from_value(cls, value: str | None) -> "AugmentationMode":
        """文字列から補完方式へ変換する。

        Parameters
        ----------
        value : str or None
            補完方式を表す文字列。

        Returns
        -------
        AugmentationMode
            対応する補完方式。未指定または不明な値の場合は ``NONE``。
        """
        if not value:
            return cls.NONE
        try:
            return cls(value)
        except ValueError:
            return cls.NONE


@dataclass(frozen=True)
class PipelineConfig:
    """パイプライン実行時の設定。

    Web API 固有の予測方式名やリクエスト検証は含めない。API固有の値は
    ルーティング層で解釈し、ライブラリにはこの設定モデルとして渡す。

    Attributes
    ----------
    augmentation_mode : AugmentationMode
        グラフ補完方式。
    default_augmented_edge_risk : float
        補完で追加したエッジに設定する既定リスク。
    max_nodes : int
        探索する経路の最大ノード数。
    top_k : int or None
        返却する上位経路数。未指定の場合は制限しない。
    experiment_id : str or None
        実験結果を保存する場合の識別子。
    """

    augmentation_mode: AugmentationMode = AugmentationMode.NONE
    default_augmented_edge_risk: float = 0.1
    max_nodes: int = 8
    top_k: int | None = None
    experiment_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PipelineConfig":
        """辞書から設定を生成する。

        Parameters
        ----------
        data : dict or None
            設定値を含む辞書。``None`` の場合は既定値を使う。

        Returns
        -------
        PipelineConfig
            生成したパイプライン設定。
        """
        raw = data or {}
        top_k = raw.get("top_k")
        values = {
            "augmentation_mode": AugmentationMode.from_value(raw.get("augmentation_mode")),
            "default_augmented_edge_risk": float(raw.get("default_augmented_edge_risk", 0.1)),
            "max_nodes": int(raw.get("max_nodes", 8)),
            "top_k": int(top_k) if top_k else None,
            "experiment_id": str(raw["experiment_id"]) if raw.get("experiment_id") else None,
        }
        return cls(**values)
