import React, { useEffect, useMemo, useRef, useState } from "react";
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";

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
  const [selectedPath, setSelectedPath] = useState(null);

  const cyRef = useRef(null);
  const cyContainerRef = useRef(null);

  const handleLoad = () => {
    try {
      const parsed = JSON.parse(configText);
      setConfig(parsed);
      setError("");
    } catch (err) {
      setError("Invalid JSON. Please check the configuration.");
    }
  };

  const handleRender = async () => {
    setIsRendering(true);
    setGraphError("");
    try {
      const apiUrl = "http://localhost:8000/graph";
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
    setActiveTab("render");
    setGraphError("");
  };

  const handleRenderSample2 = () => {
    const sampleGraph = {
      nodes: [
        { id: "en1", label: "Web Server 1", type: "entry" },
        { id: "en2", label: "Web Server 2", type: "entry" },
        { id: "pi-1", label: "Gateway 1", type: "pivot" },
        { id: "pi-2", label: "Gateway 2", type: "pivot" },
        { id: "as-1", label: "Payroll DB", type: "asset" },
        { id: "as-2", label: "File Server", type: "asset" },
        { id: "as-3", label: "CI Server", type: "asset" }
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
    setActiveTab("render");
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

    if (selectedPath && selectedPath.length > 0) {
      applyPathHighlight(selectedPath);
      return;
    }
    if (!entryPoint) {
      return;
    }

    const edges = graphData.edges ?? [];
    const adjacency = new Map();
    edges.forEach((edge) => {
      if (!adjacency.has(edge.source)) {
        adjacency.set(edge.source, []);
      }
      adjacency.get(edge.source).push(edge.target);
    });

    const queue = [entryPoint];
    const visited = new Set([entryPoint]);
    const parent = new Map();
    while (queue.length > 0) {
      const current = queue.shift();
      const nextNodes = adjacency.get(current) || [];
      for (const next of nextNodes) {
        if (!visited.has(next)) {
          visited.add(next);
          parent.set(next, current);
          queue.push(next);
        }
      }
    }

    visited.forEach((nodeId) => {
      cy.$id(nodeId).addClass("highlighted");
      const parentId = parent.get(nodeId);
      if (parentId) {
        const edge = cy.edges(
          `[source = "${parentId}"][target = "${nodeId}"]`
        );
        edge.addClass("highlighted");
      }
    });
    cy.$id(entryPoint).addClass("highlighted-start");
  }, [entryPoint, graphData, selectedPath]);

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

  const pathRows = useMemo(() => {
    if (!graphData || !entryPoint) {
      return [];
    }
    const nodeLabelById = new Map(
      (graphData.nodes ?? []).map((node) => [node.id, node.label || node.id])
    );
    const edges = graphData.edges ?? [];
    const adjacency = new Map();
    const edgeMeta = new Map();
    edges.forEach((edge) => {
      if (!adjacency.has(edge.source)) {
        adjacency.set(edge.source, []);
      }
      adjacency.get(edge.source).push(edge.target);
      edgeMeta.set(`${edge.source}->${edge.target}`, edge);
    });

    const maxDepth = 8;
    const paths = [];
    const dfs = (current, path, target) => {
      if (path.length > maxDepth) {
        return;
      }
      if (current === target) {
        paths.push([...path]);
        return;
      }
      const nextNodes = adjacency.get(current) || [];
      for (const next of nextNodes) {
        if (path.includes(next)) {
          continue;
        }
        path.push(next);
        dfs(next, path, target);
        path.pop();
      }
    };

    const reachable = new Set([entryPoint]);
    const queue = [entryPoint];
    while (queue.length > 0) {
      const current = queue.shift();
      const nextNodes = adjacency.get(current) || [];
      for (const next of nextNodes) {
        if (!reachable.has(next)) {
          reachable.add(next);
          queue.push(next);
        }
      }
    }
    const assets = (graphData.nodes ?? [])
      .filter((node) => node.type === "asset" && reachable.has(node.id))
      .map((node) => node.id);
    assets.forEach((assetId) => {
      dfs(entryPoint, [entryPoint], assetId);
    });

    return paths.map((path, index) => {
      let risk = 1;
      for (let i = 0; i < path.length - 1; i += 1) {
        const edge = edgeMeta.get(`${path[i]}->${path[i + 1]}`);
        risk *= Number(edge?.prob ?? 0.1);
      }
      return {
        id: index + 1,
        start: nodeLabelById.get(path[0]) || path[0],
        end: nodeLabelById.get(path[path.length - 1]) || path[path.length - 1],
        risk: risk.toFixed(3),
        path
      };
    });
  }, [graphData, entryPoint]);

  const listNodes = graphData?.nodes ?? [];
  const listEdges = graphData?.edges ?? [];

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
                          <th>Start Node</th>
                          <th>End Node</th>
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
          <div className="field-label prominent">Render Graph</div>
          <div className="button-row">
            <button
              type="button"
              className="secondary"
              onClick={handleRender}
              disabled
            >
              {isRendering ? "Rendering..." : "Render Graph"}
            </button>
          </div>
          <div className="button-row">
            <button type="button" onClick={handleRenderSample2}>
              Render Sample
            </button>
            <button type="button" onClick={handleRenderSample}>
              Render Sample 2
            </button>
          </div>
          {graphError ? <div className="error">{graphError}</div> : null}
          <label className="field-label prominent spaced" htmlFor="entry-point">
            Attack Detected Node
          </label>
          <select
            id="entry-point"
            value={entryPoint}
            onChange={(event) => {
              setEntryPoint(event.target.value);
              setSelectedPath(null);
            }}
          >
            <option value="">Select node</option>
            {listNodes
              .map((node) => (
                <option key={node.id} value={node.id}>
                  {node.label}
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
            <option value="">Select asset</option>
            {listNodes
              .filter((node) => node.type === "asset")
              .map((node) => (
                <option key={node.id} value={node.id}>
                  {node.label}
                </option>
              ))}
          </select>
        </aside>
      </div>
    </div>
  );
}
