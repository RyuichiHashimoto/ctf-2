"""攻撃経路予測パイプラインで利用するデータモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from libs.attack_graph_lib.schema import GraphData, parse_graph_payload

from .config import PipelineConfig


@dataclass(frozen=True)
class Vulnerability:
    """脆弱性情報。

    Attributes:
        id: 脆弱性ID。
        node_id: 脆弱性が存在するノードID。
        severity: 深刻度。
        techniques: 脆弱性から関連付けられる攻撃技術IDの一覧。
    """

    id: str
    node_id: str | None = None
    severity: float = 0.0
    techniques: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Vulnerability":
        """辞書から脆弱性情報を生成する。

        Args:
            data: 脆弱性情報を含む辞書。

        Returns:
            生成した脆弱性情報。
        """
        values = {
            "id": str(data.get("id") or data.get("cve") or ""),
            "node_id": str(data["node_id"]) if data.get("node_id") else None,
            "severity": float(data.get("severity", 0.0)),
            "techniques": _text_list(data.get("techniques")),
        }
        return cls(**values)


@dataclass(frozen=True)
class Threat:
    """脅威情報。

    Attributes:
        id: 脅威ID。
        start_node: 攻撃開始ノードID。
        target_nodes: 攻撃終了ノードIDの一覧。
        techniques: 脅威が利用する攻撃技術IDの一覧。
    """

    id: str
    start_node: str | None = None
    target_nodes: list[str] = field(default_factory=list)
    techniques: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Threat":
        """辞書から脅威情報を生成する。

        Args:
            data: 脅威情報を含む辞書。

        Returns:
            生成した脅威情報。
        """
        values = {
            "id": str(data.get("id") or data.get("name") or ""),
            "start_node": str(data["start_node"]) if data.get("start_node") else None,
            "target_nodes": _text_list(data.get("target_nodes")),
            "techniques": _text_list(data.get("techniques")),
        }
        return cls(**values)


@dataclass(frozen=True)
class PipelineInput:
    """パイプライン実行に必要な入力。

    Attributes:
        system: システム構成グラフ。
        vulnerabilities: 脆弱性情報の一覧。
        threats: 脅威情報の一覧。
        config: パイプライン設定。
    """

    system: GraphData
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    threats: list[Threat] = field(default_factory=list)
    config: PipelineConfig = field(default_factory=PipelineConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineInput":
        """辞書からパイプライン入力を生成する。

        入れ子の辞書は、パイプラインが利用する dataclass へ変換してから
        `PipelineInput` を生成する。

        Args:
            data: システム構成、脆弱性、脅威、設定を含む辞書。

        Returns:
            生成したパイプライン入力。
    """
        graph_data = data.get("system") or data.get("graph") or data
        values = {
            "system": graph_data if isinstance(graph_data, GraphData) else parse_graph_payload(graph_data),
            "vulnerabilities": [
                item if isinstance(item, Vulnerability) else Vulnerability.from_dict(item)
                for item in _list(data.get("vulnerabilities"))
            ],
            "threats": [
                item if isinstance(item, Threat) else Threat.from_dict(item)
                for item in _list(data.get("threats"))
            ],
            "config": (
                data["config"]
                if isinstance(data.get("config"), PipelineConfig)
                else PipelineConfig.from_dict(data.get("config") or {})
            ),
        }
        return cls(**values)


@dataclass(frozen=True)
class PipelineResult:
    """パイプライン実行結果。

    Attributes:
        paths: 予測された攻撃経路の一覧。
        metrics: 実行時に収集したメトリクス。
        graph: 前処理済みグラフ。
    """

    paths: list[dict[str, Any]]
    metrics: dict[str, Any]
    graph: GraphData

    def asdict(self) -> dict[str, Any]:
        """JSON化しやすい辞書へ変換する。

        Returns:
            経路、メトリクス、グラフを含む辞書。
        """
        return {
            "paths": self.paths,
            "metrics": self.metrics,
            "graph": self.graph.asdict(),
        }


def _list(value: Any) -> list[Any]:
    """任意の値をリストへ正規化する。

    Args:
        value: リストとして扱う値。

    Returns:
        `None` や空値の場合は空リスト、それ以外は入力リスト。

    Raises:
        ValueError: 入力がリストでない場合。
    """
    if not value:
        return []
    if not isinstance(value, list):
        raise ValueError("value must be a list")
    return value


def _text_list(value: Any) -> list[str]:
    """文字列または文字列化可能なリストを文字列リストへ正規化する。

    Args:
        value: 文字列、リスト、または空値。

    Returns:
        文字列リスト。
    """
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if item]
