if __name__ == "__main__":
    hoge = "./sample.json"

    from libs.attack_graph_lib.schema import load_graph_from_json_path
    from libs.attack_graph_lib.storage import save_graph
    from libs.attack_graph_lib.api import predict_paths_with_risk
    
    path = "/app/src/network-sample-small.json"
    graph_data = load_graph_from_json_path(path)

    attack_scneario = ["T1190", "T1021.002", "T1003.001", "T1021.001", "T1041"]    
    # attack_scneario = None

    rets = predict_paths_with_risk(graph_data, start_node = "en1", attack_scenario=attack_scneario)
    for pa in rets["paths"]:
        print(pa)
