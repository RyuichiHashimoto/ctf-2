"""攻撃経路予測前に実行するグラフ補完処理。"""

from __future__ import annotations

from libs.attack_graph_lib.schema import GraphData, GraphEdge

from ..models.config import AugmentationMode, PipelineConfig


def augment_graph(graph: GraphData, config: PipelineConfig) -> GraphData:
    """設定に応じてグラフ補完を実行する。

    実環境データでは通常 ``AugmentationMode.NONE`` を使い、観測された通信関係を
    そのまま利用する。実験では全結合化や双方向化を使って、通信関係を意図的に
    拡張した状態で予測できる。

    Parameters
    ----------
    graph : GraphData
        補完対象のシステム構成グラフ。
    config : PipelineConfig
        補完方式と補完エッジの既定リスクを含むパイプライン設定。

    Returns
    -------
    GraphData
        補完後のグラフ。補完なしの場合は入力グラフをそのまま返す。
    """
    if config.augmentation_mode == AugmentationMode.NONE:
        return graph
    if config.augmentation_mode == AugmentationMode.FULL_MESH:
        return _full_mesh(graph, config.default_augmented_edge_risk)
    if config.augmentation_mode == AugmentationMode.BIDIRECTIONAL:
        return _bidirectional(graph, config.default_augmented_edge_risk)
    return graph


def _full_mesh(graph: GraphData, risk: float) -> GraphData:
    """全ノード間に有向エッジを追加する。

    Parameters
    ----------
    graph : GraphData
        補完対象のシステム構成グラフ。
    risk : float
        追加エッジに設定するリスク値。

    Returns
    -------
    GraphData
        既存エッジを維持しつつ、未接続の全ノード対を接続したグラフ。
    """
    node_ids = [node.id for node in graph.nodes]
    existing = {(edge.source, edge.target) for edge in graph.edges}
    edges = list(graph.edges)
    for source in node_ids:
        for target in node_ids:
            if source == target or (source, target) in existing:
                continue
            edges.append(
                GraphEdge(
                    id=f"aug-full-mesh-{source}->{target}",
                    source=source,
                    target=target,
                    risk=risk,
                )
            )
            existing.add((source, target))
    return GraphData(nodes=list(graph.nodes), edges=edges, contains=list(graph.contains))


def _bidirectional(graph: GraphData, risk: float) -> GraphData:
    """既存エッジに対応する逆方向エッジを追加する。

    Parameters
    ----------
    graph : GraphData
        補完対象のシステム構成グラフ。
    risk : float
        追加エッジに設定するリスク値。

    Returns
    -------
    GraphData
        片方向の通信関係を双方向化したグラフ。
    """
    existing = {(edge.source, edge.target) for edge in graph.edges}
    edges = list(graph.edges)
    for edge in graph.edges:
        if (edge.target, edge.source) in existing:
            continue
        edges.append(
            GraphEdge(
                id=f"aug-bidirectional-{edge.target}->{edge.source}",
                source=edge.target,
                target=edge.source,
                risk=risk,
            )
        )
        existing.add((edge.target, edge.source))
    return GraphData(nodes=list(graph.nodes), edges=edges, contains=list(graph.contains))
