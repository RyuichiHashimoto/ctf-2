import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { combineLatest, Subscription } from 'rxjs';
import { Graph as MaxGraph, HierarchicalLayout, CellOverlay, ImageBox, Point } from '@maxgraph/core';
import { AttackPathService } from '../../services/attack-path.service';
import { AttackPathTableComponent } from './attack-path-table.component';

@Component({
  selector: 'app-maxgraph-view',
  imports: [CommonModule, AttackPathTableComponent],
  templateUrl: './maxgraph-view.component.html',
  styleUrls: ['./maxgraph-view.component.css']
})
export class MaxGraphViewComponent implements AfterViewInit, OnDestroy {
  @ViewChild('mxContainer') mxContainer?: ElementRef<HTMLDivElement>;
  private mxGraphRef: MaxGraph | null = null;
  private subscription?: Subscription;
  private pendingRender = false;

  constructor(public readonly service: AttackPathService) {}

  ngAfterViewInit(): void {
    this.subscription = combineLatest([
      this.service.graphData$,
      this.service.predictedPaths$,
      this.service.entryPoint$,
      this.service.selectedPath$
    ]).subscribe(() => {
      this.refreshMaxGraph();
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
    if (this.mxGraphRef) {
      this.mxGraphRef.destroy();
      this.mxGraphRef = null;
    }
  }

  private refreshMaxGraph(): void {
    if (!this.service.graphData) {
      return;
    }
    if (!this.mxContainer?.nativeElement) {
      if (!this.pendingRender) {
        this.pendingRender = true;
        requestAnimationFrame(() => {
          this.pendingRender = false;
          this.refreshMaxGraph();
        });
      }
      return;
    }
    if (this.mxGraphRef) {
      this.mxGraphRef.destroy();
      this.mxGraphRef = null;
    }
    const container = this.mxContainer.nativeElement;
    container.innerHTML = '';

    const graph = new MaxGraph(container);
    this.mxGraphRef = graph;
    graph.setPanning(true);
    graph.setResizeContainer(true);

    const nodeColors: Record<string, string> = {
      entry: this.getCssVar('--mx-node-entry', '#2563eb'),
      tactic: this.getCssVar('--mx-node-tactic', '#7c3aed'),
      pivot: this.getCssVar('--mx-node-pivot', '#0f766e'),
      asset: this.getCssVar('--mx-node-asset', '#f59e0b'),
      goal: this.getCssVar('--mx-node-goal', '#dc2626'),
      unknown: this.getCssVar('--mx-node-unknown', '#64748b')
    };
    const defaultBorder = this.getCssVar('--mx-node-border', '#ffffff');
    const parent = graph.getDefaultParent();
    const vertexMap = new Map<string, any>();

    const highlightThreshold = 0.21;
    const highlightedNodes = new Set<string>();
    const highlightedEdges = new Set<string>();
    const selectedPath = this.service.selectedPath$.value;
    const predictedPaths = this.service.predictedPaths$.value;
    const pathsToHighlight = selectedPath?.length
      ? (() => {
          const match = predictedPaths.find(
            (item) =>
              item.nodes.length === selectedPath.length &&
              item.nodes.every((v, i) => v === selectedPath[i])
          );
          return match && Number(match.risk ?? 0) > highlightThreshold ? [selectedPath] : [];
        })()
      : predictedPaths
          .filter((item) => Number(item.risk ?? 0) > highlightThreshold)
          .map((item) => item.nodes);
    pathsToHighlight.forEach((path) => {
      path.forEach((nodeId) => highlightedNodes.add(nodeId));
      for (let i = 0; i < path.length - 1; i += 1) {
        highlightedEdges.add(`${path[i]}->${path[i + 1]}`);
      }
    });

    const edgeRiskSum = new Map<string, number>();
    this.service.predictedPaths$.value.forEach((pathItem) => {
      const risk = Number(pathItem.risk ?? 0);
      const nodes = pathItem.nodes || [];
      for (let i = 0; i < nodes.length - 1; i += 1) {
        const key = `${nodes[i]}->${nodes[i + 1]}`;
        edgeRiskSum.set(key, (edgeRiskSum.get(key) || 0) + risk);
      }
    });
    const maxRisk = Math.max(0, ...edgeRiskSum.values());

    const model: any = (graph as any).getDataModel?.() || (graph as any).getModel?.() || (graph as any).model;
    if (model?.beginUpdate) {
      model.beginUpdate();
    }
    try {
      const highlightedVertices: any[] = [];
      const startVertices: any[] = [];
      const highlightedEdgesCells: any[] = [];
      (this.service.graphData.nodes ?? []).forEach((node) => {
        const fill = nodeColors[node.type || 'unknown'] || nodeColors['unknown'];
        const isHighlighted = highlightedNodes.has(node.id);
        const isStart = this.service.entryPoint === node.id;
        const strokeColor = isStart ? '#dc2626' : isHighlighted ? '#ef4444' : defaultBorder;
        const strokeWidth = isStart ? 10 : isHighlighted ? 10 : 1;
        const style = `rounded=1;fillColor=${fill};strokeColor=${strokeColor};strokeWidth=${strokeWidth};fontColor=#ffffff;`;
        const vertex = graph.insertVertex(parent, node.id, node.label, 0, 0, 140, 50, style as any);
        vertexMap.set(node.id, vertex);
        if (isHighlighted) {
          highlightedVertices.push(vertex);
        }
        if (isStart) {
          startVertices.push(vertex);
        }
      });
      (this.service.graphData.edges ?? []).forEach((edge) => {
        const source = vertexMap.get(edge.source);
        const target = vertexMap.get(edge.target);
        if (!source || !target) {
          return;
        }
        const key = `${edge.source}->${edge.target}`;
        const sum = edgeRiskSum.get(key) || 0;
        const norm = maxRisk > 0 ? sum / maxRisk : 0;
        const isHighlighted = highlightedEdges.has(key);
        const strokeWidth = (isHighlighted ? 3 : 2) + norm * (isHighlighted ? 8 : 6);
        const strokeColor = isHighlighted ? '#ef4444' : this.getCssVar('--mx-edge-default', '#94a3b8');
        const edgeStyle = `strokeWidth=${strokeWidth};endArrow=block;endFill=1;strokeColor=${strokeColor};`;
        const edgeCell = graph.insertEdge(parent, edge.id, '', source, target, edgeStyle as any);
        if (isHighlighted) {
          highlightedEdgesCells.push(edgeCell);
        }
      });
      if (highlightedVertices.length) {
        graph.setCellStyles('strokeColor', '#ef4444', highlightedVertices);
        graph.setCellStyles('strokeWidth', '3', highlightedVertices);
      }
      if (startVertices.length) {
        graph.setCellStyles('strokeColor', '#dc2626', startVertices);
        graph.setCellStyles('strokeWidth', '4', startVertices);
        startVertices.forEach((cell) => {
          graph.addCellOverlay(cell, this.createAttackedOverlay());
        });
      }
      if (highlightedEdgesCells.length) {
        graph.setCellStyles('strokeColor', '#ef4444', highlightedEdgesCells);
      }
    } finally {
      if (model?.endUpdate) {
        model.endUpdate();
      }
    }

    const layout = new HierarchicalLayout(graph as any, 'west' as any);
    layout.execute(parent);
    graph.getView().refresh();
    graph.fit();
  }

  private createAttackedOverlay(): CellOverlay {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="86" height="22">
      <rect x="0.5" y="0.5" width="85" height="21" rx="10" fill="#fee2e2" stroke="#fecaca"/>
      <text x="43" y="15" text-anchor="middle" font-size="11" font-family="Arial" font-weight="700" fill="#b91c1c">ATTACKED</text>
    </svg>`;
    const image = new ImageBox(`data:image/svg+xml;utf8,${encodeURIComponent(svg)}`, 86, 22);
    return new CellOverlay(image, 'ATTACKED', 'center', 'top', new Point(0, -8));
  }

  private getCssVar(name: string, fallback: string): string {
    const container = this.mxContainer?.nativeElement;
    if (!container) {
      return fallback;
    }
    const host = container.closest('app-maxgraph-view') as HTMLElement | null;
    const hostValue = host
      ? getComputedStyle(host).getPropertyValue(name).trim()
      : '';
    if (hostValue) {
      return hostValue;
    }
    const containerValue = getComputedStyle(container).getPropertyValue(name).trim();
    if (containerValue) {
      return containerValue;
    }
    const rootValue = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return rootValue || fallback;
  }
}
