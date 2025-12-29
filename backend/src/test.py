if __name__ == "__main__":
    hoge = "./sample.json"

    from libs.attack_graph_lib.schema import load_graph_from_json_path
    from libs.attack_graph_lib.storage import save_graph

    a = load_graph_from_json_path(hoge)

    import os 
    if os.path.exists("sample.db"):
        os.remove("sample.db")
    save_graph(a, "sample.db")
    