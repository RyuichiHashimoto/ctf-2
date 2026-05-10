"""攻撃経路予測パイプラインの実行制御。"""

from __future__ import annotations

import logging

from libs.attack_graph_lib.postprocessing import postprocess_prediction
from libs.attack_graph_lib.schema import GraphData, NodeType, asset_node_ids

from .graph.augmentation import augment_graph
from .graph.preprocessing import integrate_context
from .metrics.collector import MetricsCollector
from .metrics.storage import save_pipeline_result
from .models.schema import PipelineInput, PipelineResult
from .search import ExhaustiveSearcher, PathSearcher

logger = logging.getLogger("uvicorn.error")


def run_pipeline(
    input_data: PipelineInput,
    searcher: PathSearcher | None = None,
) -> PipelineResult:
    """攻撃経路予測パイプラインを実行する。

    グラフ補完、脆弱性情報の統合、経路探索、後処理、メトリクス収集を
    順番に実行する。``start_nodes`` / ``target_nodes`` が指定されている場合は
    それを使い、未指定の場合は entry ノードから asset ノードへの経路を探索する。

    Parameters
    ----------
    input_data : PipelineInput
        システム構成、脆弱性、設定を含む入力。
    searcher : PathSearcher, optional
        経路探索アルゴリズム。未指定の場合は ``ExhaustiveSearcher`` を使う。

    Returns
    -------
    PipelineResult
        予測経路、メトリクス、前処理済みグラフを含む結果。
    """
    # 1. 経路探索アルゴリズムを決定する。
    # テストや実験では searcher を差し替えられるようにし、通常実行では全探索を使う。
    if searcher is None:
        searcher = ExhaustiveSearcher()

    # 2. メトリクス収集を開始し、入力時点のグラフ規模を記録する。
    metrics = MetricsCollector()
    metrics.record_graph("input", input_data.system)

    # 3. 設定に従ってグラフを補完する。
    # ここでは不足しているノードやエッジを実験設定に応じて追加する。
    logger.info("pipeline step=augment mode=%s", input_data.config.augmentation_mode)
    augmented_graph = augment_graph(input_data.system, input_data.config)
    metrics.record_graph("augmented", augmented_graph)
    logger.info("pipeline step=augment done nodes=%d edges=%d", len(augmented_graph.nodes), len(augmented_graph.edges))

    # 4. 脆弱性情報をグラフへ統合する。
    logger.info("pipeline step=integrate_context vulns=%d", len(input_data.vulnerabilities))
    prepared_graph = integrate_context(augmented_graph, input_data.vulnerabilities)
    metrics.record_graph("prepared", prepared_graph)
    logger.info("pipeline step=integrate_context done nodes=%d edges=%d", len(prepared_graph.nodes), len(prepared_graph.edges))

    # 5. 探索の開始ノード・終了ノードを決定する。
    # 入力で明示されていればそれを優先し、未指定なら entry から asset を狙う。
    start_nodes = set(input_data.start_nodes) or _default_start_nodes(prepared_graph)
    target_nodes = set(input_data.target_nodes) or set(asset_node_ids(prepared_graph))

    # 6. 探索条件をメトリクスへ記録する。
    metrics.set("start_node_count", len(start_nodes))
    metrics.set("target_node_count", len(target_nodes))
    logger.info("pipeline step=search start=%s target_count=%d max_nodes=%d", start_nodes, len(target_nodes), input_data.config.max_nodes)

    # 7. 開始または終了候補がない場合は探索できないため、空結果として返す。
    if not start_nodes or not target_nodes:
        logger.warning("pipeline step=search skipped: start_nodes=%s target_nodes=%s", start_nodes, target_nodes)
        result = PipelineResult(paths=[], metrics=metrics.snapshot(), graph=prepared_graph)
        _save_if_requested(input_data, result)
        return result

    # 8. 各開始ノードから終了候補への攻撃経路を探索し、候補を集約する。
    all_paths: list[dict] = []
    for start_node in start_nodes:
        paths = searcher.search(
            graph=prepared_graph,
            start_node=start_node,
            target_nodes=target_nodes,
            attack_scenario=None,
            max_nodes=input_data.config.max_nodes,
        )
        logger.info("pipeline step=search start_node=%s found=%d", start_node, len(paths))
        all_paths.extend(paths)

    # 9. リスク順に並べ、重複除去や top-k 制限などの後処理を適用する。
    all_paths.sort(key=lambda item: item["risk"], reverse=True)
    postprocessed = postprocess_prediction({"paths": all_paths}, limit=input_data.config.top_k)
    metrics.set("path_count", len(postprocessed["paths"]))
    logger.info("pipeline step=postprocess total=%d after_topk=%d", len(all_paths), len(postprocessed["paths"]))

    # 10. 最終結果を組み立て、実験IDがある場合は保存して返す。
    result = PipelineResult(
        paths=postprocessed["paths"],
        metrics=metrics.snapshot(),
        graph=prepared_graph,
    )
    _save_if_requested(input_data, result)
    return result


def _default_start_nodes(graph: GraphData) -> set[str]:
    """既定の開始ノードを選択する。

    Parameters
    ----------
    graph : GraphData
        対象グラフ。

    Returns
    -------
    set of str
        entry ノードがあればそのID集合。entry ノードがなければ asset 以外の
        ノードID集合。
    """
    starts = {node.id for node in graph.nodes if node.type == NodeType.ENTRY}
    if starts:
        return starts
    asset_ids = set(asset_node_ids(graph))
    return {node.id for node in graph.nodes if node.id not in asset_ids}


def _save_if_requested(input_data: PipelineInput, result: PipelineResult) -> None:
    """設定に実験IDがある場合に結果を保存する。

    Parameters
    ----------
    input_data : PipelineInput
        パイプライン入力。
    result : PipelineResult
        保存対象の実行結果。
    """
    if input_data.config.experiment_id:
        save_pipeline_result(input_data.config.experiment_id, result.asdict())
