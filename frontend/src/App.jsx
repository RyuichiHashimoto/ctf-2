import React, { useEffect, useMemo, useRef, useState } from "react";
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";
import { Graph as MaxGraph, HierarchicalLayout } from "@maxgraph/core";

cytoscape.use(dagre);

const sampleConfig = `{
  "assets": [
    { "id": "srv", "label": "App Server", "type": "asset" },
    { "id": "db", "label": "Database", "type": "asset" }
  ],
  "connections": [
    { "from": "srv", "to": "db", "label": "reads" }
  ]
}`;

export default function App() {
  const [configText, setConfigText] = useState(sampleConfig);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("render");
  const [graphData, setGraphData] = useState(null);
  const [graphError, setGraphError] = useState("");
  const [isRendering, setIsRendering] = useState(false);
  const [entryPoint, setEntryPoint] = useState("");
  const [attackData, setAttackData] = useState("");
  const [attackTactic, setAttackTactic] = useState("");
  const [attackTechnique, setAttackTechnique] = useState("");
  const [mitreTactics, setMitreTactics] = useState([]);
  const [mitreTechniques, setMitreTechniques] = useState([]);
  const [selectedPath, setSelectedPath] = useState(null);
  const [predictedPaths, setPredictedPaths] = useState([]);
  const [predictError, setPredictError] = useState("");
  const [isPredicting, setIsPredicting] = useState(false);

  const cyRef = useRef(null);
  const cyContainerRef = useRef(null);
  const mxGraphRef = useRef(null);
  const mxContainerRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleLoad = () => {
    try {
      const parsed = JSON.parse(configText);
      setConfig(parsed);
      setError("");
    } catch (err) {
      setError("Invalid JSON. Please check the configuration.");
    }
  };

  const apiBase = "http://localhost:8000";

  const handleRender = async () => {
    setIsRendering(true);
    setGraphError("");
    try {
      const apiUrl = `${apiBase}/graph`;
      console.log("[Render] Calling Graph API:", apiUrl);
      const response = await fetch(apiUrl);
      console.log("[Render] Response status:", response.status, response.statusText);
      if (!response.ok) {
        throw new Error("Failed to fetch graph.");
      }
      const data = await response.json();
      console.log("[Render] Graph payload:", data);
      setGraphData(data);
      setActiveTab("render");
    } catch (err) {
      console.error("[Render] Graph API error:", err);
      setGraphError("Graph APIに接続できませんでした。Backendを起動してください。");
    } finally {
      setIsRendering(false);
    }
  };

  const handleLoadGraphClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  };

  const handleGraphFile = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const payload = JSON.parse(String(reader.result || "{}"));
        let normalized = null;
        if (payload.nodes && payload.edges) {
          normalized = payload;
        } else if (payload.graph) {
          const nodes = (payload.graph.node || []).map((node) => ({
            id: node.id,
            label: node.label || node["labe;"] || node.id,
            type: node.type || "unknown",
            techniques: node.techniques || [],
            features: node.features || []
          }));
          const edges = []
            .concat(payload.graph.edge || [])
            .concat(payload.graph.contains || [])
            .map((edge, index) => ({
              id: edge.id || `edge-${index}`,
              source: edge.source,
              target: edge.target,
              prob: edge.prob ?? 0.1,
              technique: edge.technique || ""
            }));
          normalized = { nodes, edges };
        }
        if (!normalized) {
          throw new Error("Invalid graph format");
        }
        setGraphData(normalized);
        setActiveTab("render");
        setGraphError("");
      } catch (err) {
        setGraphError("JSONファイルの読み込みに失敗しました。形式を確認してください。");
      }
    };
    reader.readAsText(file);
  };

  const handleRenderSample = () => {
    const sampleGraph = {
      nodes: [
        { id: "entry", label: "Initial Access", type: "entry" },
        { id: "phish", label: "Phishing", type: "tactic" },
        { id: "cred", label: "Credential Dump", type: "tactic" },
        { id: "vpn", label: "VPN Pivot", type: "pivot" },
        { id: "srv", label: "App Server", type: "asset" },
        { id: "db", label: "Database", type: "asset" },
        { id: "domain", label: "Domain Admin", type: "goal" },
        { id: "exfil", label: "Data Exfiltration", type: "goal" }
      ],
      edges: [
        { id: "e1", source: "entry", target: "phish", prob: 0.7, technique: "T1566" },
        { id: "e2", source: "phish", target: "cred", prob: 0.6, technique: "T1003" },
        { id: "e3", source: "cred", target: "vpn", prob: 0.5, technique: "T1078" },
        { id: "e4", source: "vpn", target: "srv", prob: 0.55, technique: "T1090" },
        { id: "e5", source: "srv", target: "db", prob: 0.4, technique: "T1505" },
        { id: "e6", source: "db", target: "exfil", prob: 0.45, technique: "T1041" },
        { id: "e7", source: "cred", target: "domain", prob: 0.3, technique: "T1068" },
        { id: "e8", source: "srv", target: "domain", prob: 0.2, technique: "T1075" }
      ]
    };
    setGraphData(sampleGraph);
    setActiveTab(activeTab === "maxgraph" ? "maxgraph" : "render");
    setGraphError("");
  };

  const handleRenderSampleMaxGraph = () => {
    handleRenderSample();
    setActiveTab("maxgraph");
  };

  const handleRenderSample2 = () => {
    const sampleGraph = {
      nodes: [
        { id: "en1", label: "Web Server 1", type: "entry","techniques": ["T1078", "T1041"],"features": []},
        { id: "en2", label: "Web Server 2", type: "entry","techniques": ["T1078", "T1041"],"features": []},
        { id: "pi-1", label: "Gateway 1", type: "pivot","techniques": ["T1078", "T1659"],"features": []},
        { id: "pi-2", label: "Gateway 2", type: "pivot","techniques": ["T1078", "T1189"],"features": []},
        { id: "as-1", label: "Payroll DB", type: "asset","techniques": ["T1078", "T1041"],"features": []},
        { id: "as-2", label: "File Server", type: "asset","techniques": ["T1078", "T1041"],"features": ["Asset Locations (File Server)"]},
        { id: "as-3", label: "CI Server", type: "asset","techniques": ["T1078", "T1041"],"features": []}
      ],
      edges: [
        { id: "s2-e1", source: "en1", target: "pi-1", prob: 0.6, technique: "T1566" },
        { id: "s2-e2", source: "en1", target: "pi-2", prob: 0.6, technique: "T1003" },
        { id: "s2-e3", source: "pi-1", target: "as-1", prob: 0.6, technique: "T1078" },
        { id: "s2-e4", source: "pi-1", target: "as-2", prob: 0.6, technique: "T1041" },
        { id: "s2-e5", source: "pi-2", target: "as-3", prob: 0.6, technique: "T1566" },
        { id: "s2-e6", source: "en2", target: "pi-2", prob: 0.6, technique: "T1003" },
      ]
    };
    setGraphData(sampleGraph);
    setActiveTab(activeTab === "maxgraph" ? "maxgraph" : "render");
    setGraphError("");
  };

  useEffect(() => {
    if (!graphData || !cyContainerRef.current) {
      return;
    }
    const nodeColors = {
      entry: "#2563eb",
      tactic: "#7c3aed",
      pivot: "#0f766e",
      asset: "#f59e0b",
      goal: "#dc2626",
      unknown: "#64748b"
    };
    const iconForType = (type, color) => {
      const label = (type || "?").slice(0, 2).toUpperCase();
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">
        <circle cx="32" cy="32" r="30" fill="${color}"/>
        <text x="32" y="38" text-anchor="middle" font-size="20" fill="#ffffff" font-family="Arial" font-weight="700">${label}</text>
      </svg>`;
      return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
    };
    const elements = [
      ...graphData.nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          type: node.type,
          color: nodeColors[node.type] || nodeColors.unknown,
          icon: iconForType(node.type, nodeColors[node.type] || nodeColors.unknown)
        }
      })),
      ...graphData.edges.map((edge) => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          prob: edge.prob,
          technique: edge.technique
        }
      }))
    ];

    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: cyContainerRef.current,
        elements,
        layout: { name: "dagre", rankDir: "LR", nodeSep: 40, rankSep: 120 },
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "background-color": "#ffffff",
              "background-image": "data(icon)",
              "background-fit": "cover",
              "background-clip": "none",
              color: "#0f172a",
              "font-size": "12px",
              "text-wrap": "wrap",
              "text-max-width": 90,
              "text-valign": "bottom",
              "text-halign": "center",
              "text-margin-y": 10,
              "border-width": 2,
              "border-color": "#ffffff",
              width: 42,
              height: 42
            }
          },
          {
            selector: "node.highlighted",
            style: {
              "border-color": "#ef4444",
              "border-width": 3,
              "text-outline-color": "#fee2e2",
              "text-outline-width": 2
            }
          },
          {
            selector: "node.highlighted-start",
            style: {
              "border-color": "#dc2626",
              "border-width": 4
            }
          },
          {
            selector: "edge",
            style: {
              width: 2,
              "line-color": "#94a3b8",
              "target-arrow-shape": "triangle",
              "target-arrow-scale": 1.4,
              "target-arrow-color": "#94a3b8",
              "curve-style": "bezier"
            }
          },
          {
            selector: "edge.highlighted",
            style: {
              width: 3,
              "line-color": "#ef4444",
              "target-arrow-scale": 1.6,
              "target-arrow-color": "#ef4444"
            }
          }
        ]
      });
    } else {
      cyRef.current.elements().remove();
      cyRef.current.add(elements);
      cyRef.current.layout({ name: "dagre", rankDir: "LR", nodeSep: 40, rankSep: 120 }).run();
    }
  }, [graphData]);

  useEffect(() => {
    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!cyRef.current || !graphData) {
      return;
    }
    const cy = cyRef.current;
    cy.elements().removeClass("highlighted highlighted-start");
    const applyPathHighlight = (pathNodes) => {
      pathNodes.forEach((nodeId) => {
        cy.$id(nodeId).addClass("highlighted");
      });
      for (let i = 0; i < pathNodes.length - 1; i += 1) {
        const edge = cy.edges(
          `[source = "${pathNodes[i]}"][target = "${pathNodes[i + 1]}"]`
        );
        edge.addClass("highlighted");
      }
    };

    const pathsToHighlight = selectedPath?.length
      ? [selectedPath]
      : predictedPaths.map((item) => item.nodes);
    if (pathsToHighlight.length === 0) {
      return;
    }
    const uniqueNodes = new Set();
    pathsToHighlight.forEach((path) => {
      applyPathHighlight(path);
      path.forEach((nodeId) => uniqueNodes.add(nodeId));
    });
    if (entryPoint) {
      cy.$id(entryPoint).addClass("highlighted-start");
    }
  }, [entryPoint, graphData, selectedPath, predictedPaths, attackTechnique]);

  useEffect(() => {
    if (activeTab !== "render" || !cyRef.current) {
      return;
    }
    cyRef.current.resize();
    cyRef.current.layout({
      name: "dagre",
      rankDir: "LR",
      nodeSep: 40,
      rankSep: 120
    }).run();
  }, [activeTab]);

  useEffect(() => {
    if (activeTab !== "maxgraph" || !graphData || !mxContainerRef.current) {
      return;
    }
    if (mxGraphRef.current) {
      mxGraphRef.current.destroy();
      mxGraphRef.current = null;
    }
    const container = mxContainerRef.current;
    container.innerHTML = "";

    const graph = new MaxGraph(container);
    mxGraphRef.current = graph;
    graph.setPanning(true);

    const nodeColors = {
      entry: "#2563eb",
      tactic: "#7c3aed",
      pivot: "#0f766e",
      asset: "#f59e0b",
      goal: "#dc2626",
      unknown: "#64748b"
    };
    const parent = graph.getDefaultParent();
    const vertexMap = new Map();

    const model =
      (graph.getDataModel && graph.getDataModel()) ||
      (graph.getModel && graph.getModel()) ||
      graph.model;
    if (model?.beginUpdate) {
      model.beginUpdate();
    }
    try {
      (graphData.nodes ?? []).forEach((node) => {
        const fill = nodeColors[node.type] || nodeColors.unknown;
        const style = `rounded=1;fillColor=${fill};strokeColor=#ffffff;fontColor=#ffffff;`;
        const vertex = graph.insertVertex(
          parent,
          node.id,
          node.label,
          0,
          0,
          140,
          50,
          style
        );
        vertexMap.set(node.id, vertex);
      });
      (graphData.edges ?? []).forEach((edge) => {
        const source = vertexMap.get(edge.source);
        const target = vertexMap.get(edge.target);
        if (!source || !target) {
          return;
        }
        graph.insertEdge(parent, edge.id, "", source, target);
      });
    } finally {
      if (model?.endUpdate) {
        model.endUpdate();
      }
    }

    const layout = new HierarchicalLayout(graph, "east");
    layout.execute(parent);
  }, [activeTab, graphData]);

  useEffect(() => {
    if (!graphData || !entryPoint) {
      setPredictedPaths([]);
      setPredictError("");
      return;
    }
    const controller = new AbortController();
    const runPredict = async () => {
      setIsPredicting(true);
      setPredictError("");
      try {
        const response = await fetch(`${apiBase}/predict/paths`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            start: entryPoint,
            max_len: 8,
            technique: attackTechnique || null,
            feature: attackData || null,
            graph: graphData
          }),
          signal: controller.signal
        });
        if (!response.ok) {
          throw new Error("Predict request failed");
        }
        const data = await response.json();
        setPredictedPaths(data.paths || []);
      } catch (err) {
        if (err.name !== "AbortError") {
          setPredictError("予測経路の取得に失敗しました。");
          setPredictedPaths([]);
        }
      } finally {
        setIsPredicting(false);
      }
    };
    runPredict();
    return () => controller.abort();
  }, [graphData, entryPoint, attackTechnique, attackData, apiBase]);

  const pathRows = useMemo(() => {
    if (!graphData || predictedPaths.length === 0) {
      return [];
    }
    const nodeLabelById = new Map(
      (graphData.nodes ?? []).map((node) => [node.id, node.label || node.id])
    );
    return predictedPaths.map((pathItem, index) => ({
      id: index + 1,
      start: nodeLabelById.get(pathItem.nodes[0]) || pathItem.nodes[0],
      end:
        nodeLabelById.get(pathItem.nodes[pathItem.nodes.length - 1]) ||
        pathItem.nodes[pathItem.nodes.length - 1],
      risk: Number(pathItem.risk ?? 0).toFixed(3),
      path: pathItem.nodes
    }));
  }, [graphData, predictedPaths]);

  useEffect(() => {
    const loadTactics = async () => {
      try {
        const response = await fetch(`${apiBase}/mitre/tactics`);
        const data = await response.json();
        setMitreTactics(data.tactics || []);
      } catch (err) {
        setMitreTactics([]);
      }
    };
    loadTactics();
  }, [apiBase]);

  useEffect(() => {
    if (!attackTactic) {
      setMitreTechniques([]);
      return;
    }
    const loadTechniques = async () => {
      try {
        const response = await fetch(
          `${apiBase}/mitre/techniques?tactic=${encodeURIComponent(attackTactic)}`
        );
        const data = await response.json();
        setMitreTechniques(data.techniques || []);
      } catch (err) {
        setMitreTechniques([]);
      }
    };
    loadTechniques();
  }, [apiBase, attackTactic]);

  const listNodes = graphData?.nodes ?? [];
  const listEdges = graphData?.edges ?? [];
  const selectedEntryLabel = useMemo(() => {
    if (!entryPoint) {
      return "";
    }
    const found = listNodes.find((node) => node.id === entryPoint);
    return found?.label || "";
  }, [entryPoint, listNodes]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Attack Path Visualizer</h1>
      </header>
      <div className="app-body">
        <section className="pane canvas-pane">
          <div className="tabs">
            <button
              type="button"
              className={activeTab === "render" ? "tab active" : "tab"}
              onClick={() => setActiveTab("render")}
            >
              <span className="tab-icon" aria-hidden="true" />
              Attack Path
            </button>
            <button
              type="button"
              className={activeTab === "maxgraph" ? "tab active" : "tab"}
              onClick={() => setActiveTab("maxgraph")}
            >
              <span className="tab-icon" aria-hidden="true" />
              MaxGraph
            </button>
          </div>
          {activeTab === "render" ? (
            <div className="canvas-content">
              {graphData ? (
                <>
                  <div className="cy-shell">
                    <div className="cy-title">Network Configuration Graph</div>
                    <div className="cy-container" ref={cyContainerRef} />
                  </div>
                  <div className="path-table">
                    <div className="path-title">Attack Paths</div>
                    <table>
                      <thead>
                        <tr>
                          <th>No</th>
                          <th>Attacked Node</th>
                          <th>Asset</th>
                          <th>Risk</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pathRows.length > 0 ? (
                          pathRows.map((row) => (
                            <tr
                              key={row.id}
                              onMouseEnter={() => setSelectedPath(row.path)}
                              onMouseLeave={() => setSelectedPath(null)}
                            >
                              <td>{row.id}</td>
                              <td>{row.start}</td>
                              <td>{row.end}</td>
                              <td>{row.risk}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={4}>Select Attack Detected Node.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <div className="placeholder">
                  Renderボタンを押してGraph APIから取得してください。
                </div>
              )}
            </div>
          ) : activeTab === "maxgraph" ? (
            <div className="canvas-content">
              {graphData ? (
                <>
                  <div className="cy-shell">
                    <div className="cy-title">Network Configuration Graph</div>
                    <div className="mx-container" ref={mxContainerRef} />
                  </div>
                  <div className="path-table">
                    <div className="path-title">Attack Paths</div>
                    <table>
                      <thead>
                        <tr>
                          <th>No</th>
                          <th>Attacked Node</th>
                          <th>Asset</th>
                          <th>Risk</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pathRows.length > 0 ? (
                          pathRows.map((row) => (
                            <tr
                              key={row.id}
                              onMouseEnter={() => setSelectedPath(row.path)}
                              onMouseLeave={() => setSelectedPath(null)}
                            >
                              <td>{row.id}</td>
                              <td>{row.start}</td>
                              <td>{row.end}</td>
                              <td>{row.risk}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={4}>Select Attack Detected Node.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <div className="placeholder">
                  Renderボタンを押してGraph APIから取得してください。
                </div>
              )}
            </div>
          ) : null}
        </section>
        <aside className="pane settings-pane">
          <div className="pane-title">Settings</div>
          
          {error ? <div className="error">{error}</div> : null}
          <div className="field-group">
            <div className="field-group-title">Load Graph</div>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json"
              onChange={handleGraphFile}
              className="file-input"
            />
            <div className="button-row">
              <button
                type="button"
                className="secondary"
                onClick={handleLoadGraphClick}
              >
                {isRendering ? "Loading..." : "Load configuration file"}
              </button>
            </div>
            <div className="button-row">
              <button type="button" onClick={handleRenderSample2}>
                load sample configuration 1
              </button>
              <button type="button" onClick={handleRenderSample}>
                load sample configuration 2
              </button>
              <button type="button" onClick={handleRenderSampleMaxGraph}>
                load sample configuration (maxGraph)
              </button>
            </div>
          </div>
          {graphError ? <div className="error">{graphError}</div> : null}
          {predictError ? <div className="error">{predictError}</div> : null}
          <div className="field-group">
            <div className="field-group-header">
              <div className="field-group-title">Attack Inputs</div>
              <button
                type="button"
                className="secondary small"
                onClick={() => {
                  setEntryPoint("");
                  setAttackTactic("");
                  setAttackTechnique("");
                  setAttackData("");
                }}
              >
                Clear
              </button>
            </div>
            <label className="field-label prominent" htmlFor="entry-point">
              Attacked Node
            </label>
            <select
              id="entry-point"
              value={entryPoint}
              onChange={(event) => {
                setEntryPoint(event.target.value);
                setSelectedPath(null);
                setPredictedPaths([]);
              }}
            >
              <option value="">Select node</option>
              {listNodes.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.label}
                </option>
              ))}
            </select>
            <label className="field-label prominent" htmlFor="attack-tactic">
              Attack Tactic
            </label>
            <select
              id="attack-tactic"
              value={attackTactic}
              onChange={(event) => {
                setAttackTactic(event.target.value);
                setAttackTechnique("");
              }}
            >
              <option value="">Select tactic</option>
              {mitreTactics.map((tactic) => (
                <option key={tactic.tactic_id} value={tactic.shortname}>
                  {tactic.name}
                </option>
              ))}
            </select>
            <label className="field-label prominent" htmlFor="attack-technique">
              Attack Technique
            </label>
            <select
              id="attack-technique"
              value={attackTechnique}
              onChange={(event) => setAttackTechnique(event.target.value)}
              disabled={!attackTactic}
            >
              <option value="">Select technique</option>
              {mitreTechniques.map((technique) => (
                <option key={technique.technique_id} value={technique.technique_id}>
                  {technique.name} ({technique.technique_id})
                </option>
              ))}
            </select>
            <label className="field-label prominent" htmlFor="attack-data">
              Attack Acquired Data
            </label>
            <select
              id="attack-data"
              value={attackData}
              onChange={(event) => setAttackData(event.target.value)}
            >
              <option value="">Select Data</option>
              <option value="Asset Locations (File Server)">
                Asset Locations (File Server)
              </option>
            </select>
          </div>
        </aside>
      </div>
    </div>
  );
}
