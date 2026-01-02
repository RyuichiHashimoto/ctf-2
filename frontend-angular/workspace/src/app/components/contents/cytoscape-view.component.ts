import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild
} from '@angular/core';
import { CommonModule } from '@angular/common';
import cytoscape, { Core } from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { combineLatest, Subscription } from 'rxjs';
import { AttackPathService } from '../../services/attack-path.service';
import { AttackPathTableComponent } from './attack-path-table.component';

cytoscape.use(dagre);

@Component({
  selector: 'app-cytoscape-view',
  imports: [CommonModule, AttackPathTableComponent],
  templateUrl: './cytoscape-view.component.html',
  styleUrls: ['./cytoscape-view.component.css']
})
export class CytoscapeViewComponent implements AfterViewInit, OnDestroy {
  @ViewChild('cyContainer') cyContainer?: ElementRef<HTMLDivElement>;
  private cyRef: Core | null = null;
  private subscription?: Subscription;
  private pendingRender = false;
  private readonly minPaneHeight = 420;
  private readonly maxPaneHeight = 820;

  constructor(public readonly service: AttackPathService) {}

  ngAfterViewInit(): void {
    this.subscription = combineLatest([
      this.service.graphData$,
      this.service.predictedPaths$,
      this.service.entryPoint$,
      this.service.selectedPath$
    ]).subscribe(() => {
      this.refreshCytoscape();
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
    if (this.cyRef) {
      this.cyRef.destroy();
      this.cyRef = null;
    }
  }

  private refreshCytoscape(): void {
    if (!this.service.graphData) {
      return;
    }
    if (!this.cyContainer?.nativeElement) {
      if (!this.pendingRender) {
        this.pendingRender = true;
        requestAnimationFrame(() => {
          this.pendingRender = false;
          this.refreshCytoscape();
        });
      }
      return;
    }

    const nodeColors: Record<string, string> = {
      entry: this.getCssVar('--cy-node-entry', '#2563eb'),
      tactic: this.getCssVar('--cy-node-tactic', '#7c3aed'),
      pivot: this.getCssVar('--cy-node-pivot', '#0f766e'),
      asset: this.getCssVar('--cy-node-asset', '#f59e0b'),
      goal: this.getCssVar('--cy-node-goal', '#dc2626'),
      unknown: this.getCssVar('--cy-node-unknown', '#64748b')
    };

    const iconForType = (type: string | undefined, color: string) => {
      const label = (type || '?').slice(0, 2).toUpperCase();
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">
        <circle cx="32" cy="32" r="30" fill="${color}"/>
        <text x="32" y="38" text-anchor="middle" font-size="20" fill="#ffffff" font-family="Arial" font-weight="700">${label}</text>
      </svg>`;
      return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
    };

    const elements = [
      ...this.service.graphData.nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          type: node.type,
          color: nodeColors[node.type || 'unknown'] || nodeColors['unknown'],
          icon: iconForType(node.type, nodeColors[node.type || 'unknown'] || nodeColors['unknown'])
        }
      })),
      ...this.service.graphData.edges.map((edge) => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          prob: edge.prob,
          technique: edge.technique,
          riskNorm: 0
        }
      }))
    ];

    const layoutOptions: any = { name: 'dagre', rankDir: 'LR', nodeSep: 40, rankSep: 120 };
    const cyStyles: any = [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'background-color': '#ffffff',
          'background-image': 'data(icon)',
          'background-fit': 'cover',
          'background-clip': 'none',
          color: '#0f172a',
          'font-size': '12px',
          'text-wrap': 'wrap',
          'text-max-width': 90,
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 10,
          'border-width': 2,
          'border-color': '#ffffff',
          width: 42,
          height: 42
        }
      },
      {
        selector: 'node.highlighted',
        style: {
          'border-color': '#ef4444',
          'border-width': 3,
          'text-outline-color': '#fee2e2',
          'text-outline-width': 2
        }
      },
      {
        selector: 'node.highlighted-start',
        style: {
          'border-color': '#dc2626',
          'border-width': 4
        }
      },
      {
        selector: 'node.highlighted-start::after',
        style: {
          content: '"ATTACKED"',
          'text-valign': 'top',
          'text-halign': 'center',
          'text-margin-y': -12,
          'font-size': '11px',
          color: '#b91c1c',
          'text-background-color': '#fee2e2',
          'text-background-opacity': 0.95,
          'text-background-padding': 2
        }
      },
      {
        selector: 'edge',
        style: {
          width: 'mapData(riskNorm, 0, 1, 1, 6)',
          'line-color': '#94a3b8',
          'target-arrow-shape': 'triangle',
          'target-arrow-scale': 1.4,
          'target-arrow-color': '#94a3b8',
          'curve-style': 'bezier'
        }
      },
      {
        selector: 'edge.highlighted',
        style: {
          width: 'mapData(riskNorm, 0, 1, 2, 8)',
          'line-color': '#ef4444',
          'target-arrow-scale': 1.6,
          'target-arrow-color': '#ef4444'
        }
      }
    ];

    const nodesCount = this.service.graphData.nodes?.length ?? 0;
    this.applyPaneHeight(nodesCount);

    if (!this.cyRef) {
      this.cyRef = cytoscape({
        container: this.cyContainer.nativeElement,
        elements,
        layout: layoutOptions,
        style: cyStyles
      });
    } else {
      this.cyRef.elements().remove();
      this.cyRef.add(elements);
      this.cyRef.layout(layoutOptions).run();
    }

    this.updateEdgeRisk();
    this.updateHighlights();

    this.cyRef.resize();
    this.cyRef.layout(layoutOptions).run();
  }

  private applyPaneHeight(nodesCount: number): void {
    const container = this.cyContainer?.nativeElement;
    if (!container) {
      return;
    }
    const panel = container.closest('.cy-shell') as HTMLElement | null;
    if (!panel) {
      return;
    }
    const target = Math.min(this.maxPaneHeight, this.minPaneHeight + nodesCount * 6);
    panel.style.maxHeight = `${target}px`;
    panel.style.overflow = target >= this.maxPaneHeight ? 'auto' : 'hidden';
  }

  private updateHighlights(): void {
    if (!this.cyRef || !this.service.graphData) {
      return;
    }
    const cy = this.cyRef;
    cy.elements().removeClass('highlighted highlighted-start');

    const highlightThreshold = 0.21;
    const predictedPaths = this.service.predictedPaths$.value;
    const pathsToHighlight = predictedPaths
      .filter((item) => Number(item.risk ?? 0) > highlightThreshold)
      .map((item) => item.nodes);
    const selected = this.service.selectedPath$.value;

    if (selected?.length) {
      const match = predictedPaths.find((item) =>
        item.nodes.length === selected.length && item.nodes.every((v, i) => v === selected[i])
      );
      if (match && Number(match.risk ?? 0) > highlightThreshold) {
        this.applyPathHighlight(selected);
      }
    } else {
      pathsToHighlight.forEach((path) => this.applyPathHighlight(path));
    }

    if (this.service.entryPoint) {
      cy.$id(this.service.entryPoint).addClass('highlighted-start');
    }
  }

  private applyPathHighlight(pathNodes: string[]): void {
    if (!this.cyRef) {
      return;
    }
    pathNodes.forEach((nodeId) => {
      this.cyRef?.$id(nodeId).addClass('highlighted');
    });
    for (let i = 0; i < pathNodes.length - 1; i += 1) {
      const edge = this.cyRef?.edges(`[source = "${pathNodes[i]}"][target = "${pathNodes[i + 1]}"]`);
      edge?.addClass('highlighted');
    }
  }

  private updateEdgeRisk(): void {
    if (!this.cyRef) {
      return;
    }
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
    this.cyRef.edges().forEach((edge: any) => {
      const key = `${edge.data('source')}->${edge.data('target')}`;
      const sum = edgeRiskSum.get(key) || 0;
      const norm = maxRisk > 0 ? sum / maxRisk : 0;
      edge.data('riskNorm', norm);
    });
  }

  private getCssVar(name: string, fallback: string): string {
    const container = this.cyContainer?.nativeElement;
    if (!container) {
      return fallback;
    }
    const host = container.closest('app-cytoscape-view') as HTMLElement | null;
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
