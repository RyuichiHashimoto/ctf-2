"""攻撃経路予測パイプラインで利用するデータモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from libs.attack_graph_lib.schema import GraphData, parse_graph_payload

from .config import PipelineConfig


@dataclass(frozen=True)
class Vulnerability:
    """脆弱性情報。

    Attributes
    ----------
    id : str
        脆弱性ID。
    node_id : str or None
        脆弱性が存在するノードID。
    severity : float
        深刻度。
    techniques : list of str
        脆弱性から関連付けられる攻撃技術IDの一覧。
    """

    id: str
    node_id: str | None = None
    severity: float = 0.0
    techniques: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Vulnerability":
        """辞書から脆弱性情報を生成する。

        Parameters
        ----------
        data : dict
            脆弱性情報を含む辞書。キー ``id`` または ``cve`` を脆弱性IDとして使う。

        Returns
        -------
        Vulnerability
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
class PipelineInput:
    """パイプライン実行に必要な入力。

    Attributes
    ----------
    system : GraphData
        システム構成グラフ。
    vulnerabilities : list of Vulnerability
        脆弱性情報の一覧。ノード埋め込み形式とトップレベル指定の両方を受け付ける。
    start_nodes : list of str
        探索の開始ノードID。空の場合は entry ノードを既定とする。
    target_nodes : list of str
        探索の終了ノードID。空の場合は asset ノードを既定とする。
    config : PipelineConfig
        パイプライン設定。
    """

    system: GraphData
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    start_nodes: list[str] = field(default_factory=list)
    target_nodes: list[str] = field(default_factory=list)
    config: PipelineConfig = field(default_factory=PipelineConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineInput":
        """辞書からパイプライン入力を生成する。

        ノードに ``vulnerabilities`` キーが含まれる場合はそれを抽出して
        トップレベルの ``vulnerabilities`` リストと合算する。

        Parameters
        ----------
        data : dict
            システム構成、脆弱性、設定を含む辞書。グラフは ``system``
            または ``graph`` のいずれかのキーで渡せる。

        Returns
        -------
        PipelineInput
            生成したパイプライン入力。
        """
        graph_raw = data.get("system") or data.get("graph") or data

        if isinstance(graph_raw, GraphData):
            graph: GraphData = graph_raw
            node_vulns: list[Vulnerability] = []
        else:
            graph, node_vulns = _extract_node_vulnerabilities(graph_raw)

        top_level_vulns = [
            item if isinstance(item, Vulnerability) else Vulnerability.from_dict(item)
            for item in _list(data.get("vulnerabilities"))
        ]

        values = {
            "system": graph,
            "vulnerabilities": node_vulns + top_level_vulns,
            "start_nodes": _text_list(data.get("start_nodes")),
            "target_nodes": _text_list(data.get("target_nodes")),
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

    Attributes
    ----------
    paths : list of dict
        予測された攻撃経路の一覧。
    metrics : dict of {str: Any}
        実行時に収集したメトリクス。
    graph : GraphData
        前処理済みグラフ。
    """

    paths: list[dict[str, Any]]
    metrics: dict[str, Any]
    graph: GraphData

    def asdict(self) -> dict[str, Any]:
        """JSON化しやすい辞書へ変換する。

        Returns
        -------
        dict of {str: Any}
            経路、メトリクス、グラフを含む辞書。
        """
        return {
            "paths": self.paths,
            "metrics": self.metrics,
            "graph": self.graph.asdict(),
        }


def _extract_node_vulnerabilities(
    graph_data: dict[str, Any],
) -> tuple[GraphData, list[Vulnerability]]:
    """グラフデータ内のノードに埋め込まれた脆弱性を抽出する。

    ノードオブジェクトから ``vulnerabilities`` キーを取り出して
    ``Vulnerability`` リストへ変換し、グラフパーサに渡す前にノードから除去する。

    Parameters
    ----------
    graph_data : dict
        ``node`` または ``nodes`` キーを持つグラフ辞書。

    Returns
    -------
    tuple of (GraphData, list of Vulnerability)
        パース済みグラフと、ノード埋め込みから抽出した脆弱性リスト。
    """
    node_key = "node" if "node" in graph_data else "nodes" if "nodes" in graph_data else None
    if node_key is None:
        return parse_graph_payload(graph_data), []

    vulnerabilities: list[Vulnerability] = []
    cleaned_nodes: list[dict[str, Any]] = []

    for node in graph_data[node_key]:
        node_id = str(node.get("id") or "")
        for vuln_data in (node.get("vulnerabilities") or []):
            vulnerabilities.append(Vulnerability.from_dict({**vuln_data, "node_id": node_id}))
        cleaned_nodes.append({k: v for k, v in node.items() if k != "vulnerabilities"})

    graph = parse_graph_payload({**graph_data, node_key: cleaned_nodes})
    return graph, vulnerabilities


def _list(value: Any) -> list[Any]:
    """任意の値をリストへ正規化する。

    Parameters
    ----------
    value : Any
        リストとして扱う値。

    Returns
    -------
    list
        ``None`` や空値の場合は空リスト、それ以外は入力リスト。

    Raises
    ------
    ValueError
        入力がリストでない場合。
    """
    if not value:
        return []
    if not isinstance(value, list):
        raise ValueError("value must be a list")
    return value


def _text_list(value: Any) -> list[str]:
    """文字列または文字列化可能なリストを文字列リストへ正規化する。

    Parameters
    ----------
    value : Any
        文字列、リスト、または空値。

    Returns
    -------
    list of str
        文字列リスト。
    """
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if item]
