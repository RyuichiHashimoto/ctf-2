import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { combineLatest, Subscription } from 'rxjs';
import { Graph as MaxGraph, HierarchicalLayout } from '@maxgraph/core';
import { AttackPathService } from '../../services/attack-path.service';
import { AttackPathTableComponent } from './attack-path-table.component';

@Component({
  selector: 'app-maxgraph-view',
  imports: [CommonModule, AttackPathTableComponent],
  templateUrl: './maxgraph-view.component.html'
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
      this.service.predictedPaths$
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

    const nodeColors: Record<string, string> = {
      entry: '#2563eb',
      tactic: '#7c3aed',
      pivot: '#0f766e',
      asset: '#f59e0b',
      goal: '#dc2626',
      unknown: '#64748b'
    };
    const parent = graph.getDefaultParent();
    const vertexMap = new Map<string, any>();

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
      (this.service.graphData.nodes ?? []).forEach((node) => {
        const fill = nodeColors[node.type || 'unknown'] || nodeColors['unknown'];
        const style = `rounded=1;fillColor=${fill};strokeColor=#ffffff;fontColor=#ffffff;`;
        const vertex = graph.insertVertex(parent, node.id, node.label, 0, 0, 140, 50, style as any);
        vertexMap.set(node.id, vertex);
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
        const strokeWidth = 1 + norm * 5;
        const edgeStyle = `strokeWidth=${strokeWidth};endArrow=block;endFill=1;strokeColor=#94a3b8;`;
        graph.insertEdge(parent, edge.id, '', source, target, edgeStyle as any);
      });
    } finally {
      if (model?.endUpdate) {
        model.endUpdate();
      }
    }

    const layout = new HierarchicalLayout(graph as any, 'east' as any);
    layout.execute(parent);
  }
}
