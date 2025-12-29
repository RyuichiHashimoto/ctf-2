import { Injectable, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, firstValueFrom } from 'rxjs';

export type GraphNode = {
  id: string;
  label?: string;
  type?: string;
  techniques?: string[];
  features?: string[];
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  prob?: number;
  technique?: string;
};

export type GraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type PredictedPath = {
  nodes: string[];
  risk: number;
  target?: string;
};

export type PathRow = {
  id: number;
  start: string;
  end: string;
  risk: string;
  displayFlag: string;
  path: string[];
};

@Injectable({ providedIn: 'root' })
export class AttackPathService {
  readonly graphData$ = new BehaviorSubject<GraphData | null>(null);
  readonly predictedPaths$ = new BehaviorSubject<PredictedPath[]>([]);
  readonly entryPoint$ = new BehaviorSubject<string>('');
  readonly selectedPath$ = new BehaviorSubject<string[] | null>(null);

  graphError = '';
  predictError = '';

  attackData = '';
  attackTactic = '';
  attackTechnique = '';

  mitreTactics: { tactic_id: string; name: string; shortname: string }[] = [];
  mitreTechniques: { technique_id: string; name: string }[] = [];
  uploadedGraphs: { file_id: string; filename: string }[] = [];
  selectedUploadId = '';
  uploadStatus = '';
  isUploading = false;

  detectionAlert: { device_id?: string; event?: string; detail?: string } | null = null;
  wsConnected = false;
  isDebugMode = true;

  readonly riskThreshold = 0.05;

  private ws: WebSocket | null = null;
  private readonly apiBase = (window as any).VITE_API_BASE || 'http://localhost:8000';
  private readonly wsBase = (window as any).VITE_WS_BASE || 'ws://localhost:8000';

  constructor(
    private zone: NgZone,
    private http: HttpClient
  ) {}

  get graphData(): GraphData | null {
    return this.graphData$.value;
  }

  get entryPoint(): string {
    return this.entryPoint$.value;
  }

  get listNodes(): GraphNode[] {
    return this.graphData?.nodes ?? [];
  }

  get pathRows(): PathRow[] {
    if (!this.graphData || this.predictedPaths$.value.length === 0) {
      return [];
    }
    const labelById = new Map(this.listNodes.map((node) => [node.id, node.label || node.id]));
    const filtered = this.isDebugMode
      ? this.predictedPaths$.value
      : this.predictedPaths$.value.filter((item) => Number(item.risk ?? 0) >= this.riskThreshold);
    return filtered.map((item, index) => {
      const startId = item.nodes[0];
      const endId = item.nodes[item.nodes.length - 1];
      const riskValue = Number(item.risk ?? 0);
      return {
        id: index + 1,
        start: labelById.get(startId) || startId,
        end: labelById.get(endId) || endId,
        risk: riskValue.toFixed(3),
        displayFlag: riskValue >= this.riskThreshold ? 'display' : 'hide',
        path: item.nodes
      };
    });
  }

  toggleMode(): void {
    this.isDebugMode = !this.isDebugMode;
  }

  connectWebSocket(): void {
    if (this.ws) {
      return;
    }
    this.ws = new WebSocket(`${this.wsBase}/ws/detection`);
    this.ws.onopen = () => {
      this.zone.run(() => {
        this.wsConnected = true;
      });
    };
    this.ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        this.zone.run(() => {
          this.detectionAlert = payload;
        });
      } catch {
        this.zone.run(() => {
          this.detectionAlert = {
            device_id: 'unknown',
            event: 'detection',
            detail: 'Invalid websocket payload'
          };
        });
      }
    };
    this.ws.onclose = () => {
      this.zone.run(() => {
        this.wsConnected = false;
      });
    };
    this.ws.onerror = () => {
      this.zone.run(() => {
        this.wsConnected = false;
      });
    };
  }

  closeAlert(): void {
    if (this.detectionAlert?.device_id) {
      this.setEntryPoint(this.detectionAlert.device_id);
    }
    this.detectionAlert = null;
  }

  getNodeLabel(deviceId?: string): string {
    if (!deviceId) {
      return 'unknown';
    }
    const found = this.listNodes.find((node) => node.id === deviceId);
    return found?.label || deviceId;
  }

  setEntryPoint(value: string): void {
    this.entryPoint$.next(value);
    this.selectedPath$.next(null);
    this.fetchPredictedPaths();
  }

  setAttackTactic(value: string): void {
    this.attackTactic = value;
    this.attackTechnique = '';
    this.loadTechniques();
  }

  setAttackTechnique(value: string): void {
    this.attackTechnique = value;
    this.fetchPredictedPaths();
  }

  setAttackData(value: string): void {
    this.attackData = value;
    this.fetchPredictedPaths();
  }

  setSelectedPath(path: string[] | null): void {
    this.selectedPath$.next(path);
  }

  clearAttackInputs(): void {
    this.entryPoint$.next('');
    this.attackTactic = '';
    this.attackTechnique = '';
    this.attackData = '';
    this.selectedPath$.next(null);
    this.predictedPaths$.next([]);
  }

  async loadUploadedGraphs(): Promise<void> {
    try {
      const data = await firstValueFrom(
        this.http.get<{ files?: { file_id: string; filename: string }[] }>(
          `${this.apiBase}/graph/uploads`
        )
      );
      this.zone.run(() => {
        this.uploadedGraphs = data.files || [];
      });
    } catch {
      this.zone.run(() => {
        this.uploadedGraphs = [];
      });
    }
  }

  async loadUploadedGraph(fileId: string): Promise<void> {
    if (!fileId) {
      this.zone.run(() => {
        this.selectedUploadId = '';
      });
      return;
    }
    try {
      const data = await firstValueFrom(
        this.http.get<{ graph?: GraphData }>(`${this.apiBase}/graph/uploads/${fileId}`)
      );
      if (!data.graph) {
        throw new Error('Invalid graph payload');
      }
      this.zone.run(() => {
        this.selectedUploadId = fileId;
        this.graphData$.next(data.graph || null);
        this.graphError = '';
      });
      this.fetchPredictedPaths();
    } catch (err) {
      const message = err instanceof Error ? err.message : '';
      this.zone.run(() => {
        this.graphError =
          message || 'JSONファイルの読み込みに失敗しました。形式を確認してください。';
      });
    }
  }

  async clearUploadedGraphs(): Promise<void> {
    try {
      await firstValueFrom(
        this.http.delete(`${this.apiBase}/graph/uploads/clear`)
      );
      this.zone.run(() => {
        this.uploadedGraphs = [];
        this.selectedUploadId = '';
        this.uploadStatus = 'Uploads cleared.';
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : '';
      this.zone.run(() => {
        this.uploadStatus = message || 'Failed to clear uploads.';
      });
    }
  }

  async handleGraphFile(file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);
    this.zone.run(() => {
      this.isUploading = true;
      this.uploadStatus = 'Uploading...';
    });
    try {
      const data = await firstValueFrom(
        this.http.post<{ file_id?: string; message?: string }>(
          `${this.apiBase}/graph/upload`,
          formData
        )
      );
      this.zone.run(() => {
        this.graphError = '';
        this.uploadStatus = data.message || 'Upload successful.';
      });
      await this.loadUploadedGraphs();
      this.zone.run(() => {
        this.selectedUploadId = data.file_id || '';
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : '';
      this.zone.run(() => {
        this.graphError =
          message || 'JSONファイルの読み込みに失敗しました。形式を確認してください。';
        this.uploadStatus = message || 'Upload failed.';
      });
    } finally {
      this.zone.run(() => {
        this.isUploading = false;
      });
    }
  }

  async loadGraphFromBackend(): Promise<void> {
    try {
      const data = await firstValueFrom(
        this.http.get<GraphData>(`${this.apiBase}/graph`)
      );
      this.zone.run(() => {
        this.graphData$.next(data);
        this.graphError = '';
      });
      this.fetchPredictedPaths();
    } catch {
      this.zone.run(() => {
        this.graphError = 'Graphの取得に失敗しました。';
      });
    }
  }

  async loadTactics(): Promise<void> {
    try {
      const data = await firstValueFrom(
        this.http.get<{ tactics?: { tactic_id: string; name: string; shortname: string }[] }>(
          `${this.apiBase}/mitre/tactics`
        )
      );
      this.zone.run(() => {
        this.mitreTactics = data.tactics || [];
      });
    } catch {
      this.zone.run(() => {
        this.mitreTactics = [];
      });
    }
  }

  async loadTechniques(): Promise<void> {
    if (!this.attackTactic) {
      this.mitreTechniques = [];
      return;
    }
    try {
      const data = await firstValueFrom(
        this.http.get<{ techniques?: { technique_id: string; name: string }[] }>(
          `${this.apiBase}/mitre/techniques?tactic=${encodeURIComponent(this.attackTactic)}`
        )
      );
      this.mitreTechniques = data.techniques || [];
    } catch {
      this.mitreTechniques = [];
    }
  }

  async fetchPredictedPaths(): Promise<void> {
    if (!this.graphData || !this.entryPoint) {
      this.predictedPaths$.next([]);
      this.predictError = '';
      return;
    }
    this.predictError = '';
    try {
      const data = await firstValueFrom(
        this.http.post<{ paths?: PredictedPath[] }>(`${this.apiBase}/predict/paths`, {
          start: this.entryPoint,
          max_len: 8,
          technique: this.attackTechnique || null,
          feature: this.attackData || null,
          graph: this.graphData
        })
      );
      this.zone.run(() => {
        this.predictedPaths$.next(data.paths || []);
      });
    } catch {
      this.zone.run(() => {
        this.predictError = '予測経路の取得に失敗しました。';
        this.predictedPaths$.next([]);
      });
    }
  }
}
