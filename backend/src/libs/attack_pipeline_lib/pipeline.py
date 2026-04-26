"""攻撃経路予測パイプラインの実行制御。"""

from __future__ import annotations

from libs.attack_graph_lib.postprocessing import postprocess_prediction
from libs.attack_graph_lib.prediction import predict_paths_with_risk
from libs.attack_graph_lib.schema import GraphData, NodeType, asset_node_ids

from .augmentation import augment_graph
from .metrics import MetricsCollector
from .preprocessing import integrate_context
from .schema import PipelineInput, PipelineResult
from .storage import save_pipeline_result


def run_pipeline(input_data: PipelineInput) -> PipelineResult:
    """攻撃経路予測パイプラインを実行する。

    グラフ補完、脆弱性・脅威情報の統合、経路探索、後処理、メトリクス収集を
    順番に実行する。脅威情報に開始・終了ノードが含まれる場合はそれを使い、
    未指定の場合は entry ノードから asset ノードへの経路を探索する。

    Args:
        input_data: システム構成、脆弱性、脅威、設定を含む入力。

    Returns:
        予測経路、メトリクス、前処理済みグラフを含む結果。
    """
    # メトリクス収集器を初期化する。
    metrics = MetricsCollector()

    # 入力時点のグラフ規模を記録する。
    metrics.record_graph("input", input_data.system)

    # 設定に従って、実験用のグラフ補完を実行する。
    augmented_graph = augment_graph(input_data.system, input_data.config)

    # 補完後のグラフ規模を記録する。
    metrics.record_graph("augmented", augmented_graph)

    # 脆弱性・脅威情報をグラフへ統合し、攻撃シナリオ候補を導出する。
    prepared_graph, derived_attack_scenario = integrate_context(
        augmented_graph,
        input_data.vulnerabilities,
        input_data.threats,
    )

    # 前処理後のグラフ規模を記録する。
    metrics.record_graph("prepared", prepared_graph)

    # 脅威情報に開始ノードがあれば利用し、なければ既定の開始ノードを選ぶ。
    start_nodes = _threat_starts(input_data) or _default_start_nodes(prepared_graph)

    # 脅威情報に終了ノードがあれば利用し、なければ asset ノードを終了候補にする。
    target_nodes = _threat_targets(input_data) or set(asset_node_ids(prepared_graph))

    # 脅威情報から導出した technique 列を、経路スコアリング用シナリオとして使う。
    attack_scenario = derived_attack_scenario or None

    # 探索に使う開始・終了ノード数を記録する。
    metrics.set("start_node_count", len(start_nodes))
    metrics.set("target_node_count", len(target_nodes))

    # 開始または終了ノードが得られない場合は、空結果として終了する。
    if not start_nodes or not target_nodes:
        result = PipelineResult(paths=[], metrics=metrics.snapshot(), graph=prepared_graph)
        _save_if_requested(input_data, result)
        return result

    # 各開始ノードから終了ノード群への攻撃経路候補を集約する。
    all_paths = []
    for start_node in start_nodes:
        # 低レベルのグラフ探索・リスク計算を実行する。
        prediction = predict_paths_with_risk(
            graph_payload_data=prepared_graph,
            start_node=start_node,
            attack_scenario=attack_scenario,
            max_nodes=input_data.config.max_nodes,
            target_nodes=target_nodes,
        )

        # 開始ノードごとの予測結果を全体の候補リストへ追加する。
        all_paths.extend(prediction.get("paths", []))

    # リスクが高い経路を優先するため、降順に並べる。
    all_paths.sort(key=lambda item: item["risk"], reverse=True)

    # 重複除去や top-k 制限など、グラフ単体の後処理を適用する。
    postprocessed = postprocess_prediction({"paths": all_paths}, limit=input_data.config.top_k)

    # 後処理後に残った経路数を記録する。
    metrics.set("path_count", len(postprocessed["paths"]))

    # 呼び出し元へ返す結果オブジェクトを作成する。
    result = PipelineResult(
        paths=postprocessed["paths"],
        metrics=metrics.snapshot(),
        graph=prepared_graph,
    )

    # 実験IDが指定されている場合は、結果をファイルへ保存する。
    _save_if_requested(input_data, result)

    # 最終結果を返す。
    return result


def _threat_starts(input_data: PipelineInput) -> set[str]:
    """脅威情報から開始ノードを収集する。

    Args:
        input_data: パイプライン入力。

    Returns:
        脅威情報に明示された開始ノードIDの集合。
    """
    starts: set[str] = set()
    for threat in input_data.threats:
        if threat.start_node:
            starts.add(threat.start_node)
    return starts


def _threat_targets(input_data: PipelineInput) -> set[str]:
    """脅威情報から終了ノードを収集する。

    Args:
        input_data: パイプライン入力。

    Returns:
        脅威情報に明示された終了ノードIDの集合。
    """
    targets: set[str] = set()
    for threat in input_data.threats:
        targets.update(threat.target_nodes)
    return targets


def _default_start_nodes(graph: GraphData) -> set[str]:
    """既定の開始ノードを選択する。

    Args:
        graph: 対象グラフ。

    Returns:
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

    Args:
        input_data: パイプライン入力。
        result: 保存対象の実行結果。
    """
    if input_data.config.experiment_id:
        save_pipeline_result(input_data.config.experiment_id, result.asdict())
